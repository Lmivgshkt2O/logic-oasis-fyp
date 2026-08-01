/* End-to-end U10 smoke test: Firestore write -> Function trigger -> safe docs. */
const admin = require('../firebase_seed/node_modules/firebase-admin');

const projectId = process.env.GCLOUD_PROJECT || 'logic-oasis-fyp';
admin.initializeApp({projectId});
const db = admin.firestore();
const stamp = `${Date.now()}`;
const questionId = `emulator-question-${stamp}`;
const answerId = `emulator-answer-${stamp}`;
const questionAuthor = `emulator-question-author-${stamp}`;
const answerAuthor = `emulator-answer-author-${stamp}`;

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
  await db.collection('forumQuestions').doc(questionId).set({
    authorId: questionAuthor,
    title: 'How can I check this addition?',
    text: 'I have tried adding the tens, but I want to understand how to check my answer.',
    createdAt: admin.firestore.FieldValue.serverTimestamp(),
    updatedAt: admin.firestore.FieldValue.serverTimestamp(),
  });
  await db.collection('forumAnswers').doc(answerId).set({
    questionId,
    authorId: answerAuthor,
    text: 'I add the tens first and then the ones. I check by subtracting the total afterwards.',
    createdAt: admin.firestore.FieldValue.serverTimestamp(),
    updatedAt: admin.firestore.FieldValue.serverTimestamp(),
  });
  const answer = await eventually(
    async () => (await db.collection('forumAnswers').doc(answerId).get()).data(),
    (value) => value && value.aiFeedback && value.aiFeedback.state === 'completed',
    'completed Naive Bayes feedback',
  );
  const summaries = await eventually(
    async () => ({
      question: (await db.collection('forumParticipationSummaries').doc(questionAuthor).get()).data(),
      answer: (await db.collection('forumParticipationSummaries').doc(answerAuthor).get()).data(),
    }),
    (value) => value.question?.questionsPostedCount === 1 && value.question.weekStart &&
      value.answer?.answersSubmittedCount === 1 && value.answer.weekStart,
    'weekly count projections',
  );
  const {question: questionSummary, answer: answerSummary} = summaries;
  const job = (await db.collection('forumAiJobs').doc(answerId).get()).data();
  const run = (await db.collection('forumAiRuns').doc(answerId).get()).data();
  if (job?.state !== 'completed' || run?.state !== 'completed') {
    throw new Error('AI job/run did not reach completed state');
  }
  console.log(JSON.stringify({
    answerFeedback: answer.aiFeedback,
    questionSummary: {
      weekStart: questionSummary.weekStart.toDate().toISOString(),
      questionsPostedCount: questionSummary.questionsPostedCount,
    },
    answerSummary: {
      weekStart: answerSummary.weekStart.toDate().toISOString(),
      answersSubmittedCount: answerSummary.answersSubmittedCount,
    },
    jobState: job.state,
    runState: run.state,
  }, null, 2));
  await admin.app().delete();
})().catch(async (error) => {
  console.error(error.stack || error);
  await admin.app().delete();
  process.exitCode = 1;
});
