/* Authenticated U10 smoke: two students, one parent, four idempotent counters. */
const crypto = require('crypto');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const admin = require('../firebase_seed/node_modules/firebase-admin');
const {deleteApp, initializeApp} = require('../firebase_seed/node_modules/firebase/app');
const {
  connectAuthEmulator,
  createUserWithEmailAndPassword,
  getAuth,
} = require('../firebase_seed/node_modules/firebase/auth');
const {
  connectFirestoreEmulator,
  deleteDoc,
  doc,
  getDoc,
  getFirestore,
  serverTimestamp,
  setDoc,
  updateDoc,
} = require('../firebase_seed/node_modules/firebase/firestore');
const {
  connectFunctionsEmulator,
  getFunctions,
  httpsCallable,
} = require('../firebase_seed/node_modules/firebase/functions');

const projectId = process.env.GCLOUD_PROJECT || 'logic-oasis-fyp';
admin.initializeApp({projectId});
const adminDb = admin.firestore();
const stamp = `${Date.now()}`;
const questionId = `emulator-question-${stamp}`;
const answerId = `emulator-answer-${stamp}`;
const fallbackAnswerId = `emulator-fallback-answer-${stamp}`;
const clientApps = [];
const artifactBackups = [];
let currentStep = 'startup';
const repositoryRoot = path.resolve(__dirname, '..');
const releaseManifest = JSON.parse(
  fs.readFileSync(path.join(repositoryRoot, 'functions', 'forum_model_manifest.json'), 'utf8'),
);
const controlledEvidenceFiles = [
  'ai_pipeline/forum_controlled_demo/forum_verification_catalog_v1.yaml',
  'ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_v1.jsonl',
  'ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_v1_manifest.json',
  'ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_split_manifest.json',
  'ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_candidate.joblib',
  'ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_relevance_candidate.joblib',
  'ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_candidate_manifest.json',
  'ai_pipeline/reports/forum_controlled_demo_report.json',
  'ai_pipeline/reports/forum_controlled_demo_report.md',
];

function controlledEvidenceSha256() {
  const digest = crypto.createHash('sha256');
  for (const relative of controlledEvidenceFiles) {
    digest.update(relative);
    digest.update(fs.readFileSync(evidencePath(relative)));
  }
  return digest.digest('hex');
}

function sha256hex(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function readJson(relative) {
  return JSON.parse(fs.readFileSync(path.join(repositoryRoot, relative), 'utf8'));
}

function evidencePath(relative) {
  /* Some sandboxed environments deny the emulator's Node process direct reads
   * of the generated evidence directory. FORUM_EVIDENCE_STAGING points at a
   * pre-staged copy that preserves the `ai_pipeline/` relative layout. */
  const staging = process.env.FORUM_EVIDENCE_STAGING;
  if (!staging) return path.join(repositoryRoot, relative);
  return path.join(
    path.resolve(repositoryRoot, staging),
    relative.replace(/^ai_pipeline\//, ''),
  );
}

function emulatorEnvValue(name) {
  /* The Functions emulator loads functions/.env and .env.logic-oasis-fyp over
   * the shell environment; the release manifest must bind the same revision. */
  for (const file of ['.env.logic-oasis-fyp', '.env']) {
    const pathToEnv = path.join(repositoryRoot, 'functions', file);
    if (!fs.existsSync(pathToEnv)) continue;
    for (const line of fs.readFileSync(pathToEnv, 'utf8').split(/\r?\n/)) {
      const match = line.match(new RegExp(`^${name}=(.*)$`));
      if (match) return match[1].trim();
    }
  }
  return process.env[name] || '';
}

function prepareV2Release() {
  /* Build the immutable dual-component release in the deployed Functions root
   * so the emulator exercises the real composite path (deterministic
   * correctness + relevance NB + reasoning NB) instead of a stub. */
  const functionsRoot = path.join(repositoryRoot, 'functions');
  if (!artifactBackups.length) {
    for (const name of ['forum_model.joblib', 'forum_model_manifest.json']) {
      const artifact = path.join(functionsRoot, name);
      artifactBackups.push({path: artifact, bytes: fs.readFileSync(artifact)});
    }
    const bundle = path.join(functionsRoot, 'vendor/bundle_manifest.json');
    artifactBackups.push({path: bundle, bytes: fs.readFileSync(bundle)});
  }
  const reasoningBytes = fs.readFileSync(
    evidencePath(
      'ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_candidate.joblib',
    ),
  );
  const relevanceBytes = fs.readFileSync(
    evidencePath(
      'ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_relevance_candidate.joblib',
    ),
  );
  const reasoningArtifact = path.join(functionsRoot, 'forum_model.joblib');
  const relevanceArtifact = path.join(functionsRoot, 'forum_relevance_model.joblib');
  fs.writeFileSync(reasoningArtifact, reasoningBytes);
  fs.writeFileSync(relevanceArtifact, relevanceBytes);

  const vendorRoot = path.join(
    functionsRoot,
    'vendor/logic_oasis_ai/forum_ai',
  );
  const vendorHashes = {};
  for (const name of ['__init__.py', 'classifier.py', 'relevance.py']) {
    vendorHashes[name] = sha256hex(fs.readFileSync(path.join(vendorRoot, name)));
  }
  const bundleManifestPath = path.join(
    functionsRoot,
    'vendor/bundle_manifest.json',
  );
  const bundle = readJson('functions/vendor/bundle_manifest.json');
  bundle.forumRuntimeBundle = {
    bundleSchemaVersion: 'forum-runtime-bundle-v1',
    files: vendorHashes,
  };
  fs.writeFileSync(
    bundleManifestPath,
    `${JSON.stringify(bundle, null, 2)}\n`,
    'utf8',
  );

  const candidate = JSON.parse(
    fs.readFileSync(
      evidencePath(
        'ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_candidate_manifest.json',
      ),
      'utf8',
    ),
  );
  const report = JSON.parse(
    fs.readFileSync(
      evidencePath('ai_pipeline/reports/forum_controlled_demo_report.json'),
      'utf8',
    ),
  );
  const codeRevision = emulatorEnvValue('FORUM_RUNTIME_CODE_REVISION');
  const evidenceMode = emulatorEnvValue('FORUM_MODEL_EVIDENCE_MODE');
  if (evidenceMode !== 'controlled_demo') {
    throw new Error(
      'The emulator FORUM_MODEL_EVIDENCE_MODE must be controlled_demo ' +
        `(found ${evidenceMode || 'unset'}).`,
    );
  }
  if (!codeRevision) {
    throw new Error(
      'Set FORUM_RUNTIME_CODE_REVISION in the emulator env before running ' +
        'the composite rehearsal.',
    );
  }
  const manifest = {
    manifestSchemaVersion: 'forum-model-release-manifest-v2',
    releaseId: 'forum-controlled-demo-nb-v1-release-5',
    releasedBy: 'developer',
    releasedAt: '2026-08-13T00:00:00Z',
    lifecycleStatus: 'released',
    isActive: true,
    releaseRationale:
      'Developer-released FYP1 controlled-demonstration model. ' +
      'Not evaluated on real learner forum responses.',
    supersedesReleaseId: null,
    trainingDataProvenance: 'expert_authored_controlled_demo',
    evidenceLevel: 'controlled_demonstration',
    releaseScope: 'fyp1_forum_controlled_demo',
    deploymentScope: 'controlled_demo',
    claimLevel: 'controlled_demonstration_only',
    candidateGateStatus: 'passed',
    failedGates: [],
    reasoningModelType: report.selectedNaiveBayesVariant,
    relevanceModelType: report.selectedRelevanceNaiveBayesVariant,
    reasoningModelVersion: candidate.modelVersion,
    relevanceModelVersion: candidate.relevanceModelVersion,
    reasoningArtifactSha256: sha256hex(reasoningBytes),
    relevanceArtifactSha256: sha256hex(relevanceBytes),
    reasoningArtifactSizeBytes: reasoningBytes.length,
    relevanceArtifactSizeBytes: relevanceBytes.length,
    catalogueSha256: candidate.catalogueSha256,
    datasetSha256: candidate.datasetSha256,
    datasetManifestSha256: sha256hex(
      fs.readFileSync(
        evidencePath(
          'ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_v1_manifest.json',
        ),
      ),
    ),
    splitManifestSha256: candidate.splitManifestSha256,
    rubricSha256: candidate.rubricSha256,
    evaluationReportSha256: candidate.evaluationReportSha256,
    candidateManifestSha256: sha256hex(
      fs.readFileSync(
        evidencePath(
          'ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_candidate_manifest.json',
        ),
      ),
    ),
    bundleManifestSha256: sha256hex(fs.readFileSync(bundleManifestPath)),
    dependencyLockSha256: sha256hex(
      fs.readFileSync(
        path.join(functionsRoot, 'forum-runtime-requirements.lock.txt'),
      ),
    ),
    codeRevision,
    codeRevisionKind: 'sha256_bounded_release_sources_v1',
    dependencies: releaseManifest.dependencies,
    semanticReproducibilityStatus: 'verified_same_runtime_contract',
    baselineComparisonResult: report.baselineComparisonResult,
    compositePolicy: {
      policyVersion: 'forum-composite-policy-v1',
      correctness: 'deterministic_protected_answer_key_v1',
      relevancePositiveThreshold: 0.65,
      relevanceNegativeThreshold: 0.8,
      reasoningAbstentionThreshold: 0.6,
      freeFormNeverVerified: true,
      withholdOnAnyAbstention: true,
      noPublicNegativeCorrectnessLabel: true,
    },
    vectorizerContract: candidate.vectorizerContract,
    relevanceVectorizerContract: candidate.relevanceVectorizerContract,
    sourceRuntimeHashes: vendorHashes,
    vendorRuntimeHashes: vendorHashes,
    deploymentRuntimeHashes: {
      'forum_runtime.py': sha256hex(
        fs.readFileSync(path.join(functionsRoot, 'forum_runtime.py')),
      ),
      'main.py': sha256hex(fs.readFileSync(path.join(functionsRoot, 'main.py'))),
    },
  };
  fs.writeFileSync(
    path.join(functionsRoot, 'forum_model_manifest.json'),
    `${JSON.stringify(manifest, null, 2)}\n`,
    'utf8',
  );
  return manifest;
}

function client(name) {
  const app = initializeApp({projectId, apiKey: 'demo-key'}, name);
  clientApps.push(app);
  const auth = getAuth(app);
  connectAuthEmulator(auth, 'http://127.0.0.1:9099', {disableWarnings: true});
  const db = getFirestore(app);
  connectFirestoreEmulator(db, '127.0.0.1', 8080);
  const functions = getFunctions(app, 'asia-southeast1');
  connectFunctionsEmulator(functions, '127.0.0.1', 5001);
  return {auth, db, functions};
}

async function cleanup() {
  for (const backup of artifactBackups) {
    fs.writeFileSync(backup.path, backup.bytes);
  }
  const stagedRelevance = path.join(
    repositoryRoot,
    'functions/forum_relevance_model.joblib',
  );
  if (fs.existsSync(stagedRelevance)) fs.unlinkSync(stagedRelevance);
  await Promise.all(clientApps.map((app) => deleteApp(app)));
  if (admin.apps.length) await admin.app().delete();
}

async function register(clientState, role) {
  const credential = await createUserWithEmailAndPassword(
    clientState.auth,
    `${role}-${stamp}-${Math.random().toString(16).slice(2)}@example.test`,
    'forum-test-password',
  );
  await adminDb.collection('users').doc(credential.user.uid).set({role});
  await credential.user.getIdToken(true);
  return credential.user.uid;
}

async function eventually(read, predicate, label) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    const latest = await read();
    if (predicate(latest)) return latest;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Timed out waiting for ${label}`);
}

async function expectDenied(read, label) {
  try {
    await read();
  } catch (error) {
    if (`${error.code}`.includes('permission-denied')) return;
    throw error;
  }
  throw new Error(`Linked parent unexpectedly read ${label}`);
}

(async () => {
  currentStep = 'prepare and seed v2 controlled release';
  const corpusSha256Before = controlledEvidenceSha256();
  const v2Manifest = prepareV2Release();
  await adminDb.collection('modelRegistry').doc(v2Manifest.releaseId).set(v2Manifest);
  await adminDb.collection('questions').doc('bank_q1').set({
    questionId: 'bank_q1',
    questionText: 'What is 46 + 27? Show your working.',
    questionTextBm: 'Berapakah 46 + 27? Tunjukkan jalan kerja anda.',
    options: ['20 004', '24 000', '20 400', '20 040'],
    optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    contentVersion: 'v1',
    isActive: true,
  });
  await adminDb.collection('questionAnswerKeys').doc('bank_q1').set({
    questionId: 'bank_q1',
    contentVersion: 'v1',
    isActive: true,
    answerIndex: 2,
  });
  const author = client(`question-author-${stamp}`);
  const peer = client(`answer-author-${stamp}`);
  const parent = client(`parent-${stamp}`);
  currentStep = 'register emulator users';
  const [questionAuthor, answerAuthor, parentUid] = await Promise.all([
    register(author, 'student'),
    register(peer, 'student'),
    register(parent, 'parent'),
  ]);
  await adminDb.collection('parentLinks').doc(`${parentUid}_${questionAuthor}`).set({
    parentId: parentUid,
    studentId: questionAuthor,
    status: 'active',
  });

  currentStep = 'create question and answer';
  await setDoc(doc(author.db, 'forumQuestions', questionId), {
    authorId: questionAuthor,
    title: 'How can I check this addition?',
    text: 'I have tried adding the tens, but I want to understand how to check my answer.',
    createdAt: serverTimestamp(),
    updatedAt: serverTimestamp(),
  });
  await setDoc(doc(peer.db, 'forumAnswers', answerId), {
    questionId,
    authorId: answerAuthor,
    text: 'I add the tens first and then the ones. I check by subtracting the total afterwards.',
    revision: 1,
    createdAt: serverTimestamp(),
    updatedAt: serverTimestamp(),
  });

  const markHelpful = httpsCallable(author.functions, 'markForumAnswerHelpful');
  const acceptAnswer = httpsCallable(author.functions, 'acceptForumAnswer');
  const reportContent = httpsCallable(author.functions, 'reportForumContent');
  currentStep = 'invoke collaboration callables';
  await markHelpful({answerId});
  await markHelpful({answerId});
  await reportContent({targetType: 'answer', targetId: answerId, reason: 'Please review this explanation.'});
  await reportContent({targetType: 'answer', targetId: answerId, reason: 'Please review this updated explanation.'});
  await setDoc(doc(author.db, 'forumBlocks', `${questionAuthor}_${answerAuthor}`), {
    studentId: questionAuthor,
    blockedStudentId: answerAuthor,
    createdAt: serverTimestamp(),
  });
  currentStep = 'unblock student';
  await deleteDoc(doc(author.db, 'forumBlocks', `${questionAuthor}_${answerAuthor}`));

  let parentDenied = false;
  try {
    await httpsCallable(parent.functions, 'markForumAnswerHelpful')({answerId});
  } catch (error) {
    parentDenied = error.code === 'functions/permission-denied';
  }
  if (!parentDenied) throw new Error('Parent callable was not denied');

  const resultRefs = [
    adminDb.collection('forumAnswers').doc(answerId),
    adminDb.collection('forumQuestions').doc(questionId),
    adminDb.collection('forumParticipationSummaries').doc(questionAuthor),
    adminDb.collection('forumParticipationSummaries').doc(answerAuthor),
    adminDb.collection('forumReports').doc(`${questionAuthor}_answer_${answerId}`),
    adminDb.collection('forumBlocks').doc(`${questionAuthor}_${answerAuthor}`),
    adminDb.collection('forumAiJobs').doc(answerId),
    adminDb.collection('forumAiFeedback').doc(answerId),
  ];
  currentStep = 'await first controlled inference';
  const result = await eventually(
    async () => {
      const snapshots = await Promise.all(resultRefs.map((ref) => ref.get()));
      const [answer, question, questionSummary, answerSummary, report, block, job, feedback] =
        snapshots.map((snapshot) => snapshot.data());
      const runSnapshot = job?.logicalInferenceId
        ? await adminDb.collection('forumAiRuns').doc(job.logicalInferenceId).get()
        : null;
      const run = runSnapshot?.data();
      return {answer, question, questionSummary, answerSummary, report, block, job, run, feedback};
    },
    (value) => value.feedback?.state === 'completed' &&
      value.answer?.aiPublicState === 'none' &&
      value.questionSummary?.questionsPostedCount === 1 &&
      value.answerSummary?.answersSubmittedCount === 1 &&
      value.answerSummary?.helpfulReceivedCount === 1 &&
      value.report?.status === 'active' &&
      value.report?.reason === 'Please review this updated explanation.' &&
      value.block?.blockedStudentId === answerAuthor &&
      value.job?.state === 'completed' &&
      value.run?.state === 'completed' &&
      value.run?.modelVersion === v2Manifest.reasoningModelVersion &&
      value.run?.relevanceModelVersion === v2Manifest.relevanceModelVersion &&
      value.run?.composite?.correctness === 'not_applicable' &&
      value.run?.artifactIdentity === v2Manifest.reasoningArtifactSha256 &&
      value.run?.claimLevel === 'controlled_demonstration_only',
    'authenticated collaboration and four counters',
  );

  currentStep = 'revise answer';
  await updateDoc(doc(peer.db, 'forumAnswers', answerId), {
    text: 'I regrouped the tens and ones, then checked the total by subtracting.',
    revision: 2,
    aiFeedback: {
      state: 'pending',
      label: 'uncertain',
      message: 'Your revised answer is being reviewed.',
      revision: 2,
    },
    updatedAt: serverTimestamp(),
  });
  const revised = await eventually(
    async () => {
      const [answer, job, runs, feedback] = await Promise.all([
        adminDb.collection('forumAnswers').doc(answerId).get(),
        adminDb.collection('forumAiJobs').doc(answerId).get(),
        adminDb.collection('forumAiRuns').where('answerId', '==', answerId).get(),
        adminDb.collection('forumAiFeedback').doc(answerId).get(),
      ]);
      return {
        answer: answer.data(),
        job: job.data(),
        runCount: runs.size,
        feedback: feedback.data(),
      };
    },
    (value) => value.feedback?.state === 'completed' &&
      value.feedback?.revision === 2 &&
      value.answer?.aiRevision === 2 &&
      value.job?.state === 'completed' &&
      value.job?.revision === 2 &&
      value.runCount === 2,
    'revision-fenced reclassification and immutable runs',
  );
  await acceptAnswer({answerId});
  await acceptAnswer({answerId});
  const accepted = await eventually(
    async () => {
      const [question, answerSummary] = await Promise.all([
        adminDb.collection('forumQuestions').doc(questionId).get(),
        adminDb.collection('forumParticipationSummaries').doc(answerAuthor).get(),
      ]);
      return {question: question.data(), answerSummary: answerSummary.data()};
    },
    (value) => value.question?.acceptedAnswerId === answerId &&
      value.answerSummary?.acceptedAnswersCount === 1,
    'idempotent acceptance after revision reclassification',
  );
  currentStep = 'open canonical linked discussion';
  const openDiscussion = httpsCallable(
    peer.functions,
    'openOrCreateForumDiscussion',
  );
  const submitLinked = httpsCallable(peer.functions, 'submitLinkedForumAnswer');
  const linked = await openDiscussion({questionId: 'bank_q1'});
  const linkedDiscussionId = linked.data.discussionId;
  const linkedAnswerId = (
    await submitLinked({
      discussionId: linkedDiscussionId,
      selectedOption: 2,
      explanation:
        'I regrouped the ones into one ten and added the tens, then checked by subtraction.',
    })
  ).data.answerId;
  const linkedVerified = await eventually(
    async () => {
      const [answer, feedback, job] = await Promise.all([
        adminDb.collection('forumAnswers').doc(linkedAnswerId).get(),
        adminDb.collection('forumAiFeedback').doc(linkedAnswerId).get(),
        adminDb.collection('forumAiJobs').doc(linkedAnswerId).get(),
      ]);
      const run = job?.data()?.logicalInferenceId
        ? (
            await adminDb
              .collection('forumAiRuns')
              .doc(job.data().logicalInferenceId)
              .get()
          ).data()
        : null;
      return {answer: answer.data(), feedback: feedback.data(), run};
    },
    (value) =>
      value.feedback?.state === 'completed' &&
      value.answer?.aiPublicState === 'verified' &&
      value.feedback?.correctness === 'correct' &&
      value.feedback?.label === 'verified' &&
      value.run?.composite?.publicState === 'verified' &&
      value.run?.sourceQuestionId === 'bank_q1',
    'composite verified linked answer',
  );
  const wrongLinkedAnswerId = (
    await submitLinked({
      discussionId: linkedDiscussionId,
      selectedOption: 1,
      explanation:
        'I regrouped the ones and added the tens, then checked the total.',
    })
  ).data.answerId;
  const linkedIncorrect = await eventually(
    async () => {
      const [answer, feedback] = await Promise.all([
        adminDb.collection('forumAnswers').doc(wrongLinkedAnswerId).get(),
        adminDb.collection('forumAiFeedback').doc(wrongLinkedAnswerId).get(),
      ]);
      return {answer: answer.data(), feedback: feedback.data()};
    },
    (value) =>
      value.feedback?.state === 'completed' &&
      value.answer?.aiPublicState === 'none' &&
      value.feedback?.correctness === 'incorrect' &&
      value.feedback?.label === 'correction_needed',
    'composite incorrect option with no public negative',
  );
  currentStep = 'verify linked-parent projection';
  const linkedParentSummary = await getDoc(
    doc(parent.db, 'forumParticipationSummaries', questionAuthor),
  );
  if (linkedParentSummary.data()?.questionsPostedCount !== 1) {
    throw new Error('Linked parent did not receive the count-only forum summary');
  }
  const deniedParentReads = [
    ['question', 'forumQuestions', questionId],
    ['answer', 'forumAnswers', answerId],
    ['report', 'forumReports', `${questionAuthor}_answer_${answerId}`],
    ['block', 'forumBlocks', `${questionAuthor}_${answerAuthor}`],
    ['AI job', 'forumAiJobs', answerId],
    ['AI run', 'forumAiRuns', result.job.logicalInferenceId],
    ['AI feedback', 'forumAiFeedback', answerId],
    ['linked discussion', 'forumQuestions', linkedDiscussionId],
    ['linked answer', 'forumAnswers', linkedAnswerId],
    ['model registry', 'modelRegistry', v2Manifest.releaseId],
  ];
  await Promise.all(deniedParentReads.map(([label, collection, identifier]) =>
    expectDenied(() => getDoc(doc(parent.db, collection, identifier)), label),
  ));

  currentStep = 'revoke release and verify fallback';
  const controlledRunBeforeRevocation = result.run;
  await adminDb.collection('modelRegistry').doc(v2Manifest.releaseId).update({
    isActive: false,
    lifecycleStatus: 'revoked',
  });
  await setDoc(doc(peer.db, 'forumAnswers', fallbackAnswerId), {
    questionId,
    authorId: answerAuthor,
    text: 'I used another worked step and checked the total again.',
    revision: 1,
    createdAt: serverTimestamp(),
    updatedAt: serverTimestamp(),
  });
  const fallback = await eventually(
    async () => {
      const [answer, job, feedback] = await Promise.all([
        adminDb.collection('forumAnswers').doc(fallbackAnswerId).get(),
        adminDb.collection('forumAiJobs').doc(fallbackAnswerId).get(),
        adminDb.collection('forumAiFeedback').doc(fallbackAnswerId).get(),
      ]);
      return {answer: answer.data(), job: job.data(), feedback: feedback.data()};
    },
    (value) => value.feedback?.state === 'fallback' &&
      value.answer?.aiPublicState === 'none' &&
      value.job?.state === 'fallback' &&
      value.job?.modelVersion === 'safe-fallback-v1' &&
      value.job?.artifactIdentity === 'safe-fallback-v1' &&
      value.job?.claimLevel === 'safe_fallback_only' &&
      /^[0-9a-f]{64}$/.test(value.job?.logicalInferenceId || ''),
    'safe fallback after controlled release revocation',
  );
  const preservedRun = (
    await adminDb.collection('forumAiRuns').doc(result.job.logicalInferenceId).get()
  ).data();
  assert.deepStrictEqual(
    preservedRun,
    controlledRunBeforeRevocation,
    'Controlled run changed after release revocation',
  );
  const corpusSha256After = controlledEvidenceSha256();
  if (corpusSha256After !== corpusSha256Before) {
    throw new Error('Controlled evidence corpus changed during inference rehearsal');
  }
  console.log(JSON.stringify({
    parentDenied,
    acceptedAnswerId: accepted.question.acceptedAnswerId,
    counters: {
      questionsPostedCount: result.questionSummary.questionsPostedCount,
      answersSubmittedCount: result.answerSummary.answersSubmittedCount,
      acceptedAnswersCount: accepted.answerSummary.acceptedAnswersCount,
      helpfulReceivedCount: result.answerSummary.helpfulReceivedCount,
    },
    feedbackState: result.feedback.state,
    freeFormPublicState: result.answer.aiPublicState,
    jobState: result.job.state,
    runState: result.run.state,
    releaseId: v2Manifest.releaseId,
    modelVersion: result.run.modelVersion,
    artifactIdentity: result.run.artifactIdentity,
    claimLevel: result.run.claimLevel,
    revisedFeedbackRevision: revised.feedback.revision,
    immutableRunCount: revised.runCount,
    linkedDiscussionId,
    linkedVerifiedPublicState: linkedVerified.answer.aiPublicState,
    linkedVerifiedCorrectness: linkedVerified.feedback.correctness,
    linkedIncorrectPublicState: linkedIncorrect.answer.aiPublicState,
    linkedIncorrectCorrectness: linkedIncorrect.feedback.correctness,
    reportStatus: result.report.status,
    blockedStudentId: result.block.blockedStudentId,
    linkedParentSummaryRead: true,
    linkedParentRawReadsDenied: deniedParentReads.length,
    revokedReleaseFallbackState: fallback.feedback.state,
    fallbackModelVersion: fallback.job.modelVersion,
    fallbackArtifactIdentity: fallback.job.artifactIdentity,
    fallbackClaimLevel: fallback.job.claimLevel,
    fallbackLogicalInferenceIdPresent: /^[0-9a-f]{64}$/.test(fallback.job.logicalInferenceId),
    preservedControlledRunState: preservedRun.state,
    corpusSha256Before,
    corpusSha256After,
  }, null, 2));
  await cleanup();
})().catch(async (error) => {
  console.error(JSON.stringify({
    step: currentStep,
    code: error.code || null,
    errorType: error.name || 'Error',
    message: error.message || String(error),
  }));
  await cleanup();
  process.exitCode = 1;
});
