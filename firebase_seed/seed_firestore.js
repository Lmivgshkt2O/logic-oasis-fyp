const fs = require("node:fs");
const path = require("node:path");
const admin = require("firebase-admin");
const {
  questionBanks,
  questions: bankQuestions,
  validateQuestionBankSeed,
} = require("./year4_read_write_question_banks");

const seedPath = path.join(__dirname, "seed_data.json");
const credentialCandidates = [
  path.join(__dirname, "serviceAccountKey.json"),
  path.join(__dirname, "serviceAccountKey.json.json"),
];

function findCredentialPath() {
  return credentialCandidates.find((candidate) => fs.existsSync(candidate));
}

function convertSpecialValues(value) {
  if (value === "__SERVER_TIMESTAMP__") {
    return admin.firestore.FieldValue.serverTimestamp();
  }

  if (Array.isArray(value)) {
    return value.map(convertSpecialValues);
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, nestedValue]) => [
        key,
        convertSpecialValues(nestedValue),
      ]),
    );
  }

  return value;
}

async function seedCollection(db, collectionName, documents) {
  const entries = Object.entries(documents);
  if (entries.length === 0) return;

  let batch = db.batch();
  let writes = 0;
  let total = 0;

  for (const [documentId, documentData] of entries) {
    const ref = db.collection(collectionName).doc(documentId);
    const replaceDocument =
      collectionName === "questions" ||
      collectionName === "questionBanks" ||
      collectionName === "questionAnswerKeys";
    batch.set(ref, convertSpecialValues(documentData), {
      merge: !replaceDocument,
    });
    writes += 1;
    total += 1;

    if (writes === 450) {
      await batch.commit();
      batch = db.batch();
      writes = 0;
    }
  }

  if (writes > 0) {
    await batch.commit();
  }

  console.log(`Seeded ${total} document(s) into ${collectionName}`);
}

/// Removes keys that no longer belong to a reseeded current content version.
/// Older content versions remain intact for an explicit migration, and clients
/// cannot read either set because `questionAnswerKeys` is server-only.
async function reconcileCurrentQuestionAnswerKeys(db, answerKeys) {
  const expectedIds = new Set(Object.keys(answerKeys));
  const currentVersions = new Set(
    Object.values(answerKeys).map((answerKey) => answerKey.contentVersion),
  );

  for (const contentVersion of currentVersions) {
    const snapshot = await db
      .collection('questionAnswerKeys')
      .where('contentVersion', '==', contentVersion)
      .get();
    const obsoleteDocs = snapshot.docs.filter((doc) => !expectedIds.has(doc.id));

    for (let start = 0; start < obsoleteDocs.length; start += 500) {
      const batch = db.batch();
      for (const document of obsoleteDocs.slice(start, start + 500)) {
        batch.delete(document.ref);
      }
      await batch.commit();
    }

    if (obsoleteDocs.length > 0) {
      console.log(
        `Removed ${obsoleteDocs.length} obsolete answer key(s) for ${contentVersion}`,
      );
    }
  }
}

function clientSafeLegacyQuestion(documentData) {
  const {
    answerIndex,
    explanation,
    explanationBm,
    ...clientFields
  } = documentData;
  return {
    ...clientFields,
    isActive: false,
    contentStatus: "legacy_migration_fixture",
  };
}

function buildSecureQuestionSeed(seedData) {
  validateQuestionBankSeed();
  const legacyQuestions = Object.fromEntries(
    Object.entries(seedData.questions ?? {}).map(([id, data]) => [
      id,
      clientSafeLegacyQuestion(data),
    ]),
  );
  const activeQuestions = Object.fromEntries(
    bankQuestions.map((item) => [item.id, item.client]),
  );
  const answerKeys = Object.fromEntries(
    bankQuestions.map((item) => [item.id, item.answerKey]),
  );
  const adaptiveSubtopicDocumentId = 'whole_numbers_y4_read_write_numbers';
  const adaptiveSubtopic = seedData.subtopics?.[adaptiveSubtopicDocumentId];
  const firstBank = Object.values(questionBanks)[0];
  return {
    ...seedData,
    subtopics: {
      ...seedData.subtopics,
      [adaptiveSubtopicDocumentId]: {
        ...adaptiveSubtopic,
        skillIds: [firstBank.skillId],
        contentVersion: firstBank.version,
        activeBankCount: Object.keys(questionBanks).length,
      },
    },
    questions: { ...legacyQuestions, ...activeQuestions },
    questionBanks,
    questionAnswerKeys: answerKeys,
  };
}

async function main() {
  const credentialPath = findCredentialPath();
  if (!credentialPath) {
    throw new Error(
      "Missing Firebase service account. Place serviceAccountKey.json in firebase_seed.",
    );
  }

  if (!fs.existsSync(seedPath)) {
    throw new Error(`Missing seed data file: ${seedPath}`);
  }

  const serviceAccount = require(credentialPath);
  admin.initializeApp({
    credential: admin.credential.cert(serviceAccount),
  });

  const db = admin.firestore();
  const seedData = JSON.parse(fs.readFileSync(seedPath, "utf8"));
  delete seedData._seedMetadata;
  const secureSeedData = buildSecureQuestionSeed(seedData);

  for (const [collectionName, documents] of Object.entries(secureSeedData)) {
    await seedCollection(db, collectionName, documents);
  }
  await reconcileCurrentQuestionAnswerKeys(
    db,
    secureSeedData.questionAnswerKeys,
  );

  console.log("Logic Oasis FYP1 Firestore demo seed completed.");
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}

module.exports = { buildSecureQuestionSeed };
