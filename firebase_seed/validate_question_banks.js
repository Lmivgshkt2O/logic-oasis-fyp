const fs = require('node:fs');
const path = require('node:path');
const { buildSecureQuestionSeed, validateSecureQuestionSeed } = require('./seed_firestore');
const { verifyApprovedContent } = require('./content_source_manifest');

const seedPath = path.join(__dirname, 'seed_data.json');
const source = JSON.parse(fs.readFileSync(seedPath, 'utf8'));
delete source._seedMetadata;
const secure = buildSecureQuestionSeed(source);

validateSecureQuestionSeed(secure);

const manifest = secure.contentSourceManifest;
const approvedCount = Object.values(manifest).reduce(
  (total, material) => total + Object.keys(material.questions ?? {}).length,
  0,
);
const materials = Object.values(manifest).filter(
  (material) => Object.keys(material.questions ?? {}).length > 0,
);
console.log(
  `Question-bank seed is client-safe and valid: ${approvedCount} approved ` +
    `question(s) across ${materials.length} source material(s).`,
);
