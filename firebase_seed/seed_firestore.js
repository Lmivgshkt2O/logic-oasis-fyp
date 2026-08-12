const fs = require("node:fs");
const path = require("node:path");
const admin = require("firebase-admin");
const {
  questionBanks: readWriteQuestionBanks,
  questions: bankQuestions,
  validateQuestionBankSeed,
} = require("./year4_read_write_question_banks");
const {
  questionBanks: additionalQuestionBanks,
  questions: additionalBankQuestions,
  validateAdditionalQuestionBanks,
} = require("./year4_whole_numbers_additional_banks");
const {
  DIFFICULTY_BANDS,
  buildContentSourceManifest,
  verifyApprovedContent,
} = require("./content_source_manifest");

const questionBanks = { ...readWriteQuestionBanks, ...additionalQuestionBanks };
const allBankQuestions = [...bankQuestions, ...additionalBankQuestions];

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
      collectionName === "questionAnswerKeys" ||
      collectionName === "contentSourceManifest";
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

/// Removes curriculum documents that no longer belong to the current seed.
/// The supervisor refinements renamed Year 4 topics and merged Fractions,
/// Decimals, and Percentages into one textbook topic; without this step, old
/// topic documents would keep appearing beside the new ones after a merge seed.
async function reconcileCurrentTopicsAndSubtopics(db, topics, subtopics) {
  const expectedTopicIds = new Set(Object.keys(topics));
  const topicSnapshot = await db.collection('topics').get();
  const obsoleteTopics = topicSnapshot.docs.filter(
    (doc) => !expectedTopicIds.has(doc.id),
  );
  for (let start = 0; start < obsoleteTopics.length; start += 450) {
    const batch = db.batch();
    for (const document of obsoleteTopics.slice(start, start + 450)) {
      batch.delete(document.ref);
    }
    await batch.commit();
  }
  if (obsoleteTopics.length > 0) {
    console.log(
      `Removed ${obsoleteTopics.length} obsolete topic document(s).`,
    );
  }

  const expectedSubtopicIds = new Set(Object.keys(subtopics));
  const subtopicSnapshot = await db.collection('subtopics').get();
  const obsoleteSubtopics = subtopicSnapshot.docs.filter(
    (doc) => !expectedSubtopicIds.has(doc.id),
  );
  for (let start = 0; start < obsoleteSubtopics.length; start += 450) {
    const batch = db.batch();
    for (const document of obsoleteSubtopics.slice(start, start + 450)) {
      batch.delete(document.ref);
    }
    await batch.commit();
  }
  if (obsoleteSubtopics.length > 0) {
    console.log(
      `Removed ${obsoleteSubtopics.length} obsolete subtopic document(s).`,
    );
  }
}

function clientSafeLegacyQuestion(documentData) {
  const {
    answerIndex,
    explanation,
    explanationBm,
    guidedSteps,
    guidedStepsBm,
    feedbackByOption,
    difficultyReview,
    authorId,
    reviewerId,
    approvedAt,
    ...clientFields
  } = documentData;
  return {
    ...clientFields,
    isActive: false,
    contentStatus: "legacy_migration_fixture",
  };
}

function validateSecureQuestionSeed(secure) {
  const banks = Object.values(secure.questionBanks);
  if (banks.length !== 7) {
    throw new Error('Expected the three read/write banks and four follow-on Easy banks.');
  }
  for (const bank of banks) {
    if (bank.questionIds.length !== 5) {
      throw new Error(`Invalid question count for ${bank.bankId}.`);
    }
  }

  const activeQuestions = Object.values(secure.questions).filter(
    (question) => question.isActive === true,
  );
  for (const question of Object.values(secure.questions)) {
    if (
      'answerIndex' in question ||
      'explanation' in question ||
      'explanationBm' in question ||
      'guidedSteps' in question ||
      'guidedStepsBm' in question ||
      'feedbackByOption' in question ||
      'difficultyReview' in question ||
      'authorId' in question ||
      'reviewerId' in question ||
      'approvedAt' in question
    ) {
      throw new Error('Client-readable questions must not contain answer keys.');
    }
    if (question.isActive === true) {
      if (
        !('sourceReference' in question) ||
        typeof question.sourceReference !== 'string' ||
        question.sourceReference.trim() === ''
      ) {
        throw new Error(
          `Client-readable question ${question.questionId} is missing sourceReference.`,
        );
      }
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
      key.contentVersion !== question.contentVersion ||
      key.isActive !== question.isActive
    ) {
      throw new Error(`Server-only answer key is incomplete for ${question.questionId}.`);
    }
    const feedback = key.feedbackByOption;
    if (!feedback || typeof feedback !== 'object') {
      throw new Error(`Option feedback is missing for ${question.questionId}.`);
    }
    const wrongIndexes = question.options
      .map((_, index) => index)
      .filter((index) => index !== key.answerIndex);
    for (const index of wrongIndexes) {
      const entry = feedback[String(index)];
      if (
        !entry ||
        typeof entry !== 'object' ||
        !entry.misconceptionCode ||
        !entry.hint ||
        !entry.hintBm ||
        !entry.reviewFocus ||
        !entry.reviewFocusBm
      ) {
        throw new Error(`Incomplete option feedback for ${question.questionId} option ${index}.`);
      }
    }
    const band = DIFFICULTY_BANDS[question.difficultyLevel];
    const review = key.difficultyReview ?? {};
    if (
      !band ||
      !band.cognitiveDemand.has(review.cognitiveDemand) ||
      review.reasoningStepCount !== band.reasoningStepCount ||
      review.transferRequired !== band.transferRequired
    ) {
      throw new Error(`Difficulty metadata mismatch for ${question.questionId}.`);
    }
  }
}

function buildSecureQuestionSeed(seedData) {
  validateQuestionBankSeed();
  validateAdditionalQuestionBanks();
  const legacyQuestions = Object.fromEntries(
    Object.entries(seedData.questions ?? {}).map(([id, data]) => [
      id,
      clientSafeLegacyQuestion(data),
    ]),
  );
  const activeQuestions = Object.fromEntries(
    allBankQuestions.map((item) => [
      item.id,
      // The Flutter client projection keeps the legacy `sourceReference`
      // display field; the server-side contract stores the richer bilingual
      // locators separately on `sourceLocator`/`sourceLocatorBm`.
      { ...item.client, sourceReference: item.client.sourceLocator },
    ]),
  );
  const answerKeys = Object.fromEntries(
    allBankQuestions.map((item) => [item.id, item.answerKey]),
  );
  const contentSourceManifest = buildContentSourceManifest(allBankQuestions);
  const banksBySubtopic = Object.values(questionBanks).reduce((result, bank) => {
    const documentId = `${bank.topicId}_${bank.subtopicId}`;
    (result[documentId] ??= []).push(bank);
    return result;
  }, {});
  const subtopicUpdates = Object.entries(banksBySubtopic).reduce((result, [documentId, matchingBanks]) => {
    const current = seedData.subtopics?.[documentId] ?? {};
    result[documentId] = {
      ...current,
      skillIds: [...new Set(matchingBanks.map((candidate) => candidate.skillId))],
      contentVersion: matchingBanks[0].version,
      activeBankCount: matchingBanks.length,
    };
    return result;
  }, {});
  const secure = {
    ...seedData,
    subtopics: {
      ...seedData.subtopics,
      ...subtopicUpdates,
    },
    questions: { ...legacyQuestions, ...activeQuestions },
    questionBanks,
    questionAnswerKeys: answerKeys,
    contentSourceManifest,
  };
  validateSecureQuestionSeed(secure);
  const contentErrors = verifyApprovedContent(
    allBankQuestions,
    contentSourceManifest,
  );
  if (contentErrors.length > 0) {
    throw new Error(`Content approval verification failed:\n${contentErrors.join('\n')}`);
  }
  return secure;
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
  await reconcileCurrentTopicsAndSubtopics(
    db,
    secureSeedData.topics,
    secureSeedData.subtopics,
  );
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

module.exports = { buildSecureQuestionSeed, validateSecureQuestionSeed };
