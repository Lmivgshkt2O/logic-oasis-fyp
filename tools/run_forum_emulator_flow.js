/* Authenticated U10 smoke: two students, one parent, four idempotent counters. */
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
  getFirestore,
  serverTimestamp,
  setDoc,
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
const clientApps = [];

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
  let latest;
  while (Date.now() < deadline) {
    latest = await read();
    if (predicate(latest)) return latest;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Timed out waiting for ${label}: ${JSON.stringify(latest)}`);
}

(async () => {
  const author = client(`question-author-${stamp}`);
  const peer = client(`answer-author-${stamp}`);
  const parent = client(`parent-${stamp}`);
  const [questionAuthor, answerAuthor] = await Promise.all([
    register(author, 'student'),
    register(peer, 'student'),
    register(parent, 'parent'),
  ]);

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
  await markHelpful({answerId});
  await markHelpful({answerId});
  await acceptAnswer({answerId});
  await acceptAnswer({answerId});
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
    adminDb.collection('forumAiRuns').doc(answerId),
  ];
  const result = await eventually(
    async () => {
      const snapshots = await Promise.all(resultRefs.map((ref) => ref.get()));
      const [answer, question, questionSummary, answerSummary, report, block, job, run] =
        snapshots.map((snapshot) => snapshot.data());
      return {answer, question, questionSummary, answerSummary, report, block, job, run};
    },
    (value) => value.answer?.aiFeedback?.state === 'completed' &&
      value.question?.acceptedAnswerId === answerId &&
      value.questionSummary?.questionsPostedCount === 1 &&
      value.answerSummary?.answersSubmittedCount === 1 &&
      value.answerSummary?.acceptedAnswersCount === 1 &&
      value.answerSummary?.helpfulReceivedCount === 1 &&
      value.report?.status === 'active' &&
      value.report?.reason === 'Please review this updated explanation.' &&
      value.block?.blockedStudentId === answerAuthor &&
      value.job?.state === 'completed' &&
      value.run?.state === 'completed',
    'authenticated collaboration and four counters',
  );
  console.log(JSON.stringify({
    parentDenied,
    acceptedAnswerId: result.question.acceptedAnswerId,
    counters: {
      questionsPostedCount: result.questionSummary.questionsPostedCount,
      answersSubmittedCount: result.answerSummary.answersSubmittedCount,
      acceptedAnswersCount: result.answerSummary.acceptedAnswersCount,
      helpfulReceivedCount: result.answerSummary.helpfulReceivedCount,
    },
    feedbackState: result.answer.aiFeedback.state,
    jobState: result.job.state,
    runState: result.run.state,
    reportStatus: result.report.status,
    blockedStudentId: result.block.blockedStudentId,
  }, null, 2));
  await cleanup();
})().catch(async (error) => {
  console.error(error.stack || error);
  await cleanup();
  process.exitCode = 1;
});
