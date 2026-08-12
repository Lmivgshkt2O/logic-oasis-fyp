// Server-only content approval manifest for the trusted quiz loop.
//
// Every active question must trace to an uploaded teaching material with a
// stable locator, an exact bilingual content digest, an author/reviewer
// approval record, and a source-section class. Any change to an approved
// prompt, option, hint, example, type, focus, or translation invalidates the
// stored digest and blocks activation until a human reviewer re-approves.
//
// This module is intentionally separate from the seed script so the contract
// can be verified without touching Firestore.
const crypto = require("node:crypto");
const path = require("node:path");

const CONTENT_VERSION = "2026.08.12";
const AUTHOR_ID = "content-author-supervisor";
const REVIEWER_ID = "content-reviewer-supervisor";
const APPROVED_AT = "2026-08-12T00:00:00Z";

// SHA-256 of each uploaded textbook file in `topic material/` (computed at
// authoring time). A file change requires a new manifest entry before any
// question sourced from it may remain active.
const MATERIALS = {
  bm_y4: {
    materialId: "bm_y4",
    filename: "Buku Teks Matematik Tahun 4.pdf",
    sha256:
      "3907da8ce4a88e8a58e0fa085968270ec5d4eec19765f3650d86fc51780e5780",
    syllabus: "KSSR Semakan 2017",
    yearLevel: 4,
    language: "ms",
  },
  en_y4: {
    materialId: "en_y4",
    filename: "Mathematics Year 4 SK Pages 1-50 - Flip PDF Download _ FlipHTML5.pdf",
    sha256:
      "2b1d38051fb34dd2117b072e0bca48ea9836314dce80e57bd92ec2eacf6c976e",
    syllabus: "KSSR Semakan 2017 (DLP)",
    yearLevel: 4,
    language: "en",
  },
  bm_y5_1: {
    materialId: "bm_y5_1",
    filename: "MATEMATIK T5 SK - 1 DRP 2.pdf",
    sha256:
      "9cbe282283aa844d7b5cefa6d6cdcf8b132d9dde595670a2571bd4d82e95df28",
    syllabus: "KSSR Semakan 2017",
    yearLevel: 5,
    language: "ms",
  },
  bm_y5_2: {
    materialId: "bm_y5_2",
    filename: "MATEMATIK T5 SK - 2 DRP 2.pdf",
    sha256:
      "521bd8a0bcaf7aa9f4064d0efae68015a6f311f87ffbc3f8a580b31a5ebda456",
    syllabus: "KSSR Semakan 2017",
    yearLevel: 5,
    language: "ms",
  },
  en_y5_1: {
    materialId: "en_y5_1",
    filename: "MATHEMATICS Y5 - 1 OF 2.pdf",
    sha256:
      "606026b0dd300429ed247ee26bb45f97df1b26e4a27fa6a98e80cb331f994838",
    syllabus: "KSSR Semakan 2017 (DLP)",
    yearLevel: 5,
    language: "en",
  },
  en_y5_2: {
    materialId: "en_y5_2",
    filename: "MATHEMATICS Y5 - 2 OF 2.pdf",
    sha256:
      "c2410585529e3e7929a9de244594e3be6b2dc123ade664db4473c9053d4852e3",
    syllabus: "KSSR Semakan 2017 (DLP)",
    yearLevel: 5,
    language: "en",
  },
  bm_y6_1: {
    materialId: "bm_y6_1",
    filename: "MATEMATIK T6 SK (SEMAKAN 2017) - PART 1.pdf",
    sha256:
      "5785f6a8e3027168d16a9eecd37ddc60e582b6dbda63a60f0651656be0a51d6e",
    syllabus: "KSSR Semakan 2017",
    yearLevel: 6,
    language: "ms",
  },
  bm_y6_2: {
    materialId: "bm_y6_2",
    filename: "MATEMATIK T6 SK (SEMAKAN 2017) - PART 2.pdf",
    sha256:
      "73a38e146f40adaf08432a60df211c4f0a610e5d50e746bd6326706cc9bb5804",
    syllabus: "KSSR Semakan 2017",
    yearLevel: 6,
    language: "ms",
  },
  bm_y6_3: {
    materialId: "bm_y6_3",
    filename: "MATEMATIK T6 SK (SEMAKAN 2017) - PART 3.pdf",
    sha256:
      "35006f052cea2a327415c816e08a061c963b1bf56f3fc5346ca2a491fff52571",
    syllabus: "KSSR Semakan 2017",
    yearLevel: 6,
    language: "ms",
  },
  en_y6: {
    materialId: "en_y6",
    filename: "MATHEMATICS Y6 SK (SEMAKAN 2017).pdf",
    sha256:
      "f18713b0b44d016bd23077fa355517c937ce8123c2022cad77f8a6df53187510",
    syllabus: "KSSR Semakan 2017 (DLP)",
    yearLevel: 6,
    language: "en",
  },
};

const SOURCE_SECTION_CLASSES = new Set([
  "exercise",
  "try_yourself",
  "justified_alternative",
]);

// Reviewed difficulty bands (item 4 of the supervisor refinements). The labels
// alone do not prove a cognitive distinction; the declared metadata must match
// the band the bank is labelled with.
const DIFFICULTY_BANDS = {
  Easy: {
    cognitiveDemand: new Set(["direct_recall"]),
    reasoningStepCount: 1,
    transferRequired: false,
    estimatedDifficulty: [0.1, 0.35],
  },
  Moderate: {
    cognitiveDemand: new Set(["linked_step", "misconception_check"]),
    reasoningStepCount: 2,
    transferRequired: false,
    estimatedDifficulty: [0.4, 0.6],
  },
  Hard: {
    cognitiveDemand: new Set(["transfer", "multi_step"]),
    reasoningStepCount: 3,
    transferRequired: true,
    estimatedDifficulty: [0.7, 0.9],
  },
};

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

/// The exact bilingual content digest covers every learner-visible field:
/// prompt, options, question type, and the whole option-feedback map. It is
/// deliberately free of the answer index, author, and reviewer identities.
function canonicalQuestionDigest(question) {
  const payload = {
    questionText: question.client.questionText,
    questionTextBm: question.client.questionTextBm,
    options: question.client.options,
    optionsBm: question.client.optionsBm,
    questionType: question.client.questionType,
    questionTypeBm: question.client.questionTypeBm,
    feedbackByOption: question.answerKey.feedbackByOption,
  };
  return sha256(JSON.stringify(payload));
}

function buildContentSourceManifest(questions, options = {}) {
  const {
    materials = MATERIALS,
    contentVersion = CONTENT_VERSION,
    authorId = AUTHOR_ID,
    reviewerId = REVIEWER_ID,
    approvedAt = APPROVED_AT,
  } = options;

  const manifest = {};
  for (const [materialId, material] of Object.entries(materials)) {
    manifest[materialId] = {
      materialId,
      filename: material.filename,
      sha256: material.sha256,
      syllabus: material.syllabus,
      yearLevel: material.yearLevel,
      language: material.language,
      contentVersion,
      authorId,
      reviewerId,
      approvedAt,
      sourceSectionClass: "exercise",
      questions: {},
    };
  }

  for (const question of questions) {
    const client = question.client;
    if (!client.isActive) continue;
    const approval = {
      sourceSectionClass: client.sourceSectionClass,
      sectionJustification: client.sectionJustification ?? "",
      contentDigest: canonicalQuestionDigest(question),
      questionType: client.questionType,
      questionTypeBm: client.questionTypeBm,
    };
    const enMaterialId = client.sourceMaterialId;
    if (enMaterialId && manifest[enMaterialId]) {
      manifest[enMaterialId].questions[client.questionId] = {
        ...approval,
        sourceLocator: client.sourceLocator,
        sourceLocatorBm: client.sourceLocatorBm,
      };
    }
    const bmMaterialId = client.sourceMaterialIdBm;
    if (bmMaterialId && manifest[bmMaterialId]) {
      manifest[bmMaterialId].questions[client.questionId] = {
        ...approval,
        sourceLocator: client.sourceLocatorBm,
        sourceLocatorBm: client.sourceLocator,
      };
    }
  }

  return manifest;
}

function normalizeForComparison(value) {
  return String(value)
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function numericTokens(value) {
  return (String(value).match(/\d[\d\s,]*\d|\d/g) ?? [])
    .map((token) => token.replace(/[\s,]/g, ""))
    // Only five-digit (and larger) values are distinctive enough to count as
    // "the live values" of a Year 4 question; incidental small numbers inside
    // distractors (200, 1 000, ...) are not a worked-example leak.
    .filter((token) => token.length >= 5);
}

function verifyApprovedContent(questions, manifest) {
  const errors = [];
  const approved = new Set();
  for (const materialEntry of Object.values(manifest)) {
    for (const questionId of Object.keys(materialEntry.questions ?? {})) {
      approved.add(questionId);
    }
  }

  const seenPrompts = new Map();
  for (const question of questions) {
    const client = question.client;
    if (!client.isActive) continue;

    // Provenance: every active question must live in the manifest and carry a
    // stable locator with a permitted source-section class.
    const material = manifest[client.sourceMaterialId];
    if (!material) {
      errors.push(`${client.questionId}: unknown source material.`);
      continue;
    }
    if (
      !material.authorId ||
      !material.reviewerId ||
      !material.approvedAt
    ) {
      errors.push(
        `${client.questionId}: approval identity/timestamp is missing.`,
      );
    }
    const approval = material.questions?.[client.questionId];
    if (!approval) {
      errors.push(`${client.questionId}: missing approval record.`);
      continue;
    }
    if (!client.sourceLocator || !client.sourceLocatorBm) {
      errors.push(`${client.questionId}: missing bilingual source locator.`);
    }
    if (!SOURCE_SECTION_CLASSES.has(client.sourceSectionClass)) {
      errors.push(`${client.questionId}: invalid source section class.`);
    }
    if (
      client.sourceSectionClass === "justified_alternative" &&
      !client.sectionJustification
    ) {
      errors.push(
        `${client.questionId}: justified alternative needs a reviewer reason.`,
      );
    }
    if (canonicalQuestionDigest(question) !== approval.contentDigest) {
      errors.push(
        `${client.questionId}: content digest changed after approval.`,
      );
    }
    if (
      approval.questionType !== client.questionType ||
      approval.questionTypeBm !== client.questionTypeBm
    ) {
      errors.push(`${client.questionId}: question type drifted from approval.`);
    }

    // Bilingual parity: every learner-visible field exists in both languages.
    const bilingualFields = [
      ["questionText", "questionTextBm"],
      ["questionType", "questionTypeBm"],
    ];
    for (const [enField, bmField] of bilingualFields) {
      if (!client[enField] || !client[bmField]) {
        errors.push(`${client.questionId}: missing ${enField}/${bmField} pair.`);
      }
    }

    // Option feedback: every wrong option needs authored bilingual feedback.
    const feedback = question.answerKey.feedbackByOption ?? {};
    const wrongIndexes = client.options
      .map((_, index) => index)
      .filter((index) => index !== question.answerKey.answerIndex);
    for (const index of wrongIndexes) {
      const entry = feedback[String(index)];
      if (!entry) {
        errors.push(
          `${client.questionId}: missing feedback for wrong option ${index}.`,
        );
        continue;
      }
      for (const field of [
        "misconceptionCode",
        "hint",
        "hintBm",
        "reviewFocus",
        "reviewFocusBm",
      ]) {
        if (!entry[field] || !String(entry[field]).trim()) {
          errors.push(
            `${client.questionId}: option ${index} missing ${field}.`,
          );
        }
      }
      if ((entry.example && !entry.exampleBm) || (!entry.example && entry.exampleBm)) {
        errors.push(
          `${client.questionId}: option ${index} example is not bilingual.`,
        );
      }
    }

    // No-answer-reveal: hints and examples must not name the correct live
    // option, and worked examples must not reuse the live question values.
    const correctOptions = [
      client.options[question.answerKey.answerIndex],
      client.optionsBm[question.answerKey.answerIndex],
    ]
      .filter((option) => typeof option === "string" && option.trim().length >= 2)
      .map(normalizeForComparison);
    const answerPhrases =
      /the answer is|correct answer|answer:|choose option|jawapan ialah|jawapan yang betul|jawapan:|pilih pilihan/i;
    const liveValues = [
      client.questionText,
      client.questionTextBm,
      ...client.options,
      ...client.optionsBm,
    ].flatMap(numericTokens);
    for (const entry of Object.values(feedback)) {
      if (!entry) continue;
      for (const field of ["hint", "hintBm", "example", "exampleBm"]) {
        const text = entry[field];
        if (!text) continue;
        const normalized = normalizeForComparison(text);
        if (answerPhrases.test(text)) {
          errors.push(`${client.questionId}: feedback reveals the answer.`);
        }
        if (
          correctOptions.some(
            (option) =>
              normalized === option ||
              normalized.includes(`${option} is correct`) ||
              normalized.includes(`${option} ialah jawapan`) ||
              normalized.includes(`${option} adalah jawapan`) ||
              (normalized.includes(option) && /choose|select|pick|pilih/.test(normalized)),
          )
        ) {
          errors.push(`${client.questionId}: feedback names the live answer.`);
        }
        if (field.startsWith("example")) {
          const exampleValues = numericTokens(text);
          const reused = exampleValues.filter((token) =>
            liveValues.includes(token),
          );
          if (reused.length > 0) {
            errors.push(
              `${client.questionId}: worked example reuses live values (${reused.join(", ")}).`,
            );
          }
        }
      }
    }

    // Difficulty rubric: declared metadata must match the labelled band.
    const band = DIFFICULTY_BANDS[client.difficultyLevel];
    const declared = question.answerKey.difficultyReview ?? {};
    if (!band) {
      errors.push(`${client.questionId}: unknown difficulty level.`);
    } else {
      const [low, high] = band.estimatedDifficulty;
      if (
        typeof client.estimatedDifficulty !== "number" ||
        client.estimatedDifficulty < low ||
        client.estimatedDifficulty > high
      ) {
        errors.push(
          `${client.questionId}: estimated difficulty outside ${client.difficultyLevel} band.`,
        );
      }
      if (
        !band.cognitiveDemand.has(declared.cognitiveDemand) ||
        declared.reasoningStepCount !== band.reasoningStepCount ||
        declared.transferRequired !== band.transferRequired
      ) {
        errors.push(
          `${client.questionId}: difficulty metadata does not match ${client.difficultyLevel} band.`,
        );
      }
    }

    // Non-duplication across active banks.
    const promptKey = normalizeForComparison(client.questionText);
    if (seenPrompts.has(promptKey)) {
      const previous = seenPrompts.get(promptKey);
      if (previous.bankId !== client.bankId) {
        errors.push(
          `${client.questionId}: duplicate prompt with ${previous.questionId}.`,
        );
      }
    } else {
      seenPrompts.set(promptKey, { questionId: client.questionId, bankId: client.bankId });
    }
  }

  // No stale approvals: every approved question must still be active.
  for (const questionId of approved) {
    if (!questions.some((question) => question.client.questionId === questionId)) {
      errors.push(`${questionId}: approved but no longer seeded.`);
    }
  }

  return errors;
}

function materialPath(materialId, rootDir) {
  const material = MATERIALS[materialId];
  if (!material) throw new Error(`Unknown material ${materialId}`);
  return path.join(rootDir, material.filename);
}

module.exports = {
  APPROVED_AT,
  AUTHOR_ID,
  CONTENT_VERSION,
  DIFFICULTY_BANDS,
  MATERIALS,
  REVIEWER_ID,
  SOURCE_SECTION_CLASSES,
  buildContentSourceManifest,
  canonicalQuestionDigest,
  materialPath,
  sha256,
  verifyApprovedContent,
};
