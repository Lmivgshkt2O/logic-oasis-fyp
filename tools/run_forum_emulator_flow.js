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
  'ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_candidate_manifest.json',
  'ai_pipeline/reports/forum_controlled_demo_report.json',
  'ai_pipeline/reports/forum_controlled_demo_report.md',
];

function controlledEvidenceSha256() {
  const digest = crypto.createHash('sha256');
  for (const relative of controlledEvidenceFiles) {
    digest.update(relative);
    digest.update(fs.readFileSync(path.join(repositoryRoot, relative)));
  }
  return digest.digest('hex');
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
  currentStep = 'seed controlled release';
  const corpusSha256Before = controlledEvidenceSha256();
  await adminDb.collection('modelRegistry').doc(releaseManifest.releaseId).set(releaseManifest);
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
  ];
  currentStep = 'await first controlled inference';
  const result = await eventually(
    async () => {
      const snapshots = await Promise.all(resultRefs.map((ref) => ref.get()));
      const [answer, question, questionSummary, answerSummary, report, block, job] =
        snapshots.map((snapshot) => snapshot.data());
      const runSnapshot = job?.logicalInferenceId
        ? await adminDb.collection('forumAiRuns').doc(job.logicalInferenceId).get()
        : null;
      const run = runSnapshot?.data();
      return {answer, question, questionSummary, answerSummary, report, block, job, run};
    },
    (value) => value.answer?.aiFeedback?.state === 'completed' &&
      value.questionSummary?.questionsPostedCount === 1 &&
      value.answerSummary?.answersSubmittedCount === 1 &&
      value.answerSummary?.helpfulReceivedCount === 1 &&
      value.report?.status === 'active' &&
      value.report?.reason === 'Please review this updated explanation.' &&
      value.block?.blockedStudentId === answerAuthor &&
      value.job?.state === 'completed' &&
      value.run?.state === 'completed' &&
      value.run?.modelVersion === releaseManifest.modelVersion &&
      value.run?.artifactIdentity === releaseManifest.artifactSha256 &&
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
      const [answer, job, runs] = await Promise.all([
        adminDb.collection('forumAnswers').doc(answerId).get(),
        adminDb.collection('forumAiJobs').doc(answerId).get(),
        adminDb.collection('forumAiRuns').where('answerId', '==', answerId).get(),
      ]);
      return {answer: answer.data(), job: job.data(), runCount: runs.size};
    },
    (value) => value.answer?.aiFeedback?.state === 'completed' &&
      value.answer?.aiFeedback?.revision === 2 &&
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
    ['model registry', 'modelRegistry', releaseManifest.releaseId],
  ];
  await Promise.all(deniedParentReads.map(([label, collection, identifier]) =>
    expectDenied(() => getDoc(doc(parent.db, collection, identifier)), label),
  ));

  currentStep = 'revoke release and verify fallback';
  const controlledRunBeforeRevocation = result.run;
  await adminDb.collection('modelRegistry').doc(releaseManifest.releaseId).update({
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
      const [answer, job] = await Promise.all([
        adminDb.collection('forumAnswers').doc(fallbackAnswerId).get(),
        adminDb.collection('forumAiJobs').doc(fallbackAnswerId).get(),
      ]);
      return {answer: answer.data(), job: job.data()};
    },
    (value) => value.answer?.aiFeedback?.state === 'fallback' &&
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
    feedbackState: result.answer.aiFeedback.state,
    jobState: result.job.state,
    runState: result.run.state,
    releaseId: releaseManifest.releaseId,
    modelVersion: result.run.modelVersion,
    artifactIdentity: result.run.artifactIdentity,
    claimLevel: result.run.claimLevel,
    revisedFeedbackRevision: revised.answer.aiFeedback.revision,
    immutableRunCount: revised.runCount,
    reportStatus: result.report.status,
    blockedStudentId: result.block.blockedStudentId,
    linkedParentSummaryRead: true,
    linkedParentRawReadsDenied: deniedParentReads.length,
    revokedReleaseFallbackState: fallback.answer.aiFeedback.state,
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
  }));
  await cleanup();
  process.exitCode = 1;
});
