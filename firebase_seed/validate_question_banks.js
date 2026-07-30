const fs = require('node:fs');
const path = require('node:path');
const { buildSecureQuestionSeed, validateSecureQuestionSeed } = require('./seed_firestore');

const seedPath = path.join(__dirname, 'seed_data.json');
const source = JSON.parse(fs.readFileSync(seedPath, 'utf8'));
delete source._seedMetadata;
const secure = buildSecureQuestionSeed(source);

validateSecureQuestionSeed(secure);

console.log('Question-bank seed is client-safe and valid.');
