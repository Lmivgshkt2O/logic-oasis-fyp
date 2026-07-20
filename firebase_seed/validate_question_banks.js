const fs = require('node:fs');
const path = require('node:path');
const { buildSecureQuestionSeed } = require('./seed_firestore');

const seedPath = path.join(__dirname, 'seed_data.json');
const source = JSON.parse(fs.readFileSync(seedPath, 'utf8'));
delete source._seedMetadata;
const secure = buildSecureQuestionSeed(source);

const banks = Object.values(secure.questionBanks);
if (banks.length !== 7) {
  throw new Error('Expected the three read/write banks and four follow-on Easy banks.');
}
for (const bank of banks) {
  if (bank.questionIds.length < 8 || bank.questionIds.length > 10) {
    throw new Error(`Invalid question count for ${bank.bankId}.`);
  }
}
const activeQuestions = Object.values(secure.questions).filter(
  (question) => question.isActive === true,
);
for (const question of Object.values(secure.questions)) {
  if ('answerIndex' in question || 'explanation' in question || 'explanationBm' in question) {
    throw new Error('Client-readable questions must not contain answer keys.');
  }
}
if (Object.keys(secure.questionAnswerKeys).length !== activeQuestions.length) {
  throw new Error('Every active question must have exactly one answer key.');
}
for (const question of activeQuestions) {
  const key = secure.questionAnswerKeys[question.questionId];
  if (
    !key ||
    key.questionId !== question.questionId ||
    !Number.isInteger(key.answerIndex) ||
    key.answerIndex < 0 ||
    key.answerIndex >= question.options.length ||
    typeof key.explanation !== 'string' ||
    key.explanation.trim() === '' ||
    typeof key.explanationBm !== 'string' ||
    key.explanationBm.trim() === '' ||
    key.contentVersion !== question.contentVersion ||
    key.isActive !== question.isActive
  ) {
    throw new Error(`Server-only answer key is incomplete for ${question.questionId}.`);
  }
}

console.log('Question-bank seed is client-safe and valid.');
