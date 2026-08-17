const admin = require('firebase-admin');
const fs = require('fs');
const path = require('path');
process.env.FIRESTORE_EMULATOR_HOST = '127.0.0.1:8080';
admin.initializeApp({ projectId: 'logic-oasis-fyp' });
const db = admin.firestore();
const manifest = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', 'functions', 'forum_model_manifest.json'), 'utf8'),
);

(async () => {
  await db.collection('modelRegistry').doc(manifest.releaseId).set(manifest);
  await db.collection('questions').doc('bank_q1').set({
    questionId: 'bank_q1', contentVersion: 'v1', isActive: true,
    questionText: 'What is 46 + 27? Show your working.',
    questionTextBm: 'Berapakah 46 + 27? Tunjukkan jalan kerja anda.',
    options: ['20 004', '24 000', '20 400', '20 040'],
    optionsBm: ['20 004', '24 000', '20 400', '20 040'],
  });
  await db.collection('questionAnswerKeys').doc('bank_q1').set({
    questionId: 'bank_q1', contentVersion: 'v1', isActive: true, answerIndex: 2,
  });
  await db.collection('forumQuestions').doc('linked_bank_q1_v1').set({
    mode: 'linked', sourceQuestionId: 'bank_q1', sourceContentVersion: 'v1',
    promptSnapshot: {
      questionText: 'What is 46 + 27? Show your working.',
      options: ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    },
    title: 'What is 46 + 27?', text: 'What is 46 + 27? Show your working.',
    createdAt: new Date(), updatedAt: new Date(),
  });
  for (let i = 0; i < 25; i++) {
    await db.collection('forumQuestions').doc(`free_q${i}`).set({
      authorId: 'student_a_uid', title: `Free question ${i}`,
      text: `Body for free question ${i} with enough detail.`,
      createdAt: new Date(), updatedAt: new Date(),
    });
  }
  console.log('seeded');
})();