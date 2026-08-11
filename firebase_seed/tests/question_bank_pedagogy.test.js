// U15 pedagogy contract tests.
//
// These tests verify the authoring contract without touching Firestore:
//   1. Approved bilingual questions with valid locators and per-option
//      feedback pass.
//   2. Missing option feedback, reviewer state, source locator, or BM parity
//      fails.
//   3. Hints that reveal the correct live option or worked examples that
//      reuse live values fail.
//   4. Difficulty metadata must match the labelled Easy/Moderate/Hard bands;
//      relabeling without matching reviewed metadata fails.
//   5. A question duplicated across active difficulty banks fails.
//   6. Changing any approved prompt, option, hint, example, type, focus, or
//      translation changes the digest and blocks activation.
const assert = require("node:assert/strict");
const {
  buildContentSourceManifest,
  canonicalQuestionDigest,
  verifyApprovedContent,
} = require("../content_source_manifest");
const {
  questions: readWriteQuestions,
} = require("../year4_read_write_question_banks");
const {
  questions: additionalQuestions,
} = require("../year4_whole_numbers_additional_banks");

const allQuestions = [...readWriteQuestions, ...additionalQuestions];

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function manifestFor(questions) {
  return buildContentSourceManifest(questions);
}

function verificationErrors(questions, manifest) {
  return verifyApprovedContent(questions, manifest);
}

function questionById(questions, questionId) {
  const found = questions.find((item) => item.client.questionId === questionId);
  assert.ok(found, `fixture question ${questionId} not found`);
  return found;
}

async function main() {
  // Scenario 1: every approved bilingual question with a valid locator and
  // full per-option feedback passes verification.
  const manifest = manifestFor(allQuestions);
  assert.equal(
    verificationErrors(allQuestions, manifest).length,
    0,
    "the full approved set must pass",
  );
  assert.ok(
    Object.keys(manifest.en_y4.questions).length >= 15,
    "English Year 4 material must cover the read/write banks",
  );
  assert.ok(
    Object.keys(manifest.bm_y4.questions).length >= 15,
    "Malay Year 4 material must cover the read/write banks",
  );

  // Scenario 2: missing option feedback fails.
  {
    const tampered = clone(allQuestions);
    const target = questionById(tampered, "q_y4_whole_read_write_easy_01");
    delete target.answerKey.feedbackByOption["0"];
    const errors = verificationErrors(tampered, manifestFor(tampered));
    assert.ok(
      errors.some((error) => error.includes("missing feedback for wrong option 0")),
      "missing option feedback must fail",
    );
  }

  // Scenario 2: missing reviewer state fails.
  {
    const tamperedManifest = clone(manifest);
    delete tamperedManifest.en_y4.reviewerId;
    const errors = verificationErrors(allQuestions, tamperedManifest);
    assert.ok(
      errors.some((error) => error.includes("approval identity/timestamp is missing")),
      "missing reviewer state must fail",
    );
  }

  // Scenario 2: missing source locator fails.
  {
    const tampered = clone(allQuestions);
    const target = questionById(tampered, "q_y4_whole_read_write_easy_02");
    target.client.sourceLocator = "";
    const errors = verificationErrors(tampered, manifestFor(tampered));
    assert.ok(
      errors.some((error) => error.includes("missing bilingual source locator")),
      "missing source locator must fail",
    );
  }

  // Scenario 2: missing BM parity fails.
  {
    const tampered = clone(allQuestions);
    const target = questionById(tampered, "q_y4_whole_read_write_easy_03");
    target.client.questionTextBm = "";
    const errors = verificationErrors(tampered, manifestFor(tampered));
    assert.ok(
      errors.some((error) => error.includes("missing questionText/questionTextBm pair")),
      "missing BM prompt must fail",
    );
  }
  {
    const tampered = clone(allQuestions);
    const target = questionById(tampered, "q_y4_whole_read_write_easy_03");
    target.answerKey.feedbackByOption["0"].hintBm = "";
    const errors = verificationErrors(tampered, manifestFor(tampered));
    assert.ok(
      errors.some((error) => error.includes("option 0 missing hintBm")),
      "missing BM hint must fail",
    );
  }

  // Scenario 3: a hint that names the correct live option fails.
  {
    const tampered = clone(allQuestions);
    const target = questionById(tampered, "q_y4_whole_read_write_easy_01");
    target.answerKey.feedbackByOption["0"].hint =
      "Choose 20 004 because it is the numeral for twenty thousand four.";
    const errors = verificationErrors(tampered, manifestFor(tampered));
    assert.ok(
      errors.some((error) => error.includes("feedback names the live answer")),
      "a hint naming the correct option must fail",
    );
  }

  // Scenario 3: a worked example reusing the live values fails.
  {
    const tampered = clone(allQuestions);
    const target = questionById(tampered, "q_y4_whole_read_write_easy_01");
    target.answerKey.feedbackByOption["0"].example =
      "Compare 20 004 with 21 004 to see the thousands group.";
    const errors = verificationErrors(tampered, manifestFor(tampered));
    assert.ok(
      errors.some((error) => error.includes("worked example reuses live values")),
      "an example reusing live values must fail",
    );
  }

  // Scenario 4: declared difficulty metadata must match the labelled band.
  {
    const tampered = clone(allQuestions);
    const target = questionById(tampered, "q_y4_whole_read_write_easy_01");
    target.client.difficultyLevel = "Moderate";
    const errors = verificationErrors(tampered, manifestFor(tampered));
    assert.ok(
      errors.some((error) => error.includes("difficulty metadata does not match Moderate band")),
      "relabeling Easy as Moderate without matching metadata must fail",
    );
  }
  {
    const tampered = clone(allQuestions);
    const target = questionById(tampered, "q_y4_whole_read_write_moderate_01");
    target.client.difficultyLevel = "Easy";
    const errors = verificationErrors(tampered, manifestFor(tampered));
    assert.ok(
      errors.some((error) => error.includes("difficulty metadata does not match Easy band")),
      "relabeling Moderate as Easy without matching metadata must fail",
    );
  }
  {
    const tampered = clone(allQuestions);
    const target = questionById(tampered, "q_y4_whole_read_write_hard_01");
    target.client.difficultyLevel = "Moderate";
    const errors = verificationErrors(tampered, manifestFor(tampered));
    assert.ok(
      errors.some((error) => error.includes("difficulty metadata does not match Moderate band")),
      "relabeling Hard as Moderate without matching metadata must fail",
    );
  }

  // Scenario 5: a question duplicated across active difficulty banks fails.
  {
    const tampered = clone(allQuestions);
    const duplicate = clone(
      questionById(tampered, "q_y4_whole_read_write_easy_01"),
    );
    duplicate.id = "q_y4_whole_read_write_moderate_99";
    duplicate.client.questionId = duplicate.id;
    duplicate.client.bankId = "y4_whole_read_write_moderate_v1";
    duplicate.answerKey.questionId = duplicate.id;
    tampered.push(duplicate);
    const errors = verificationErrors(tampered, manifestFor(tampered));
    assert.ok(
      errors.some((error) => error.includes("duplicate prompt")),
      "a duplicate across active banks must fail",
    );
  }

  // Scenario 6: changing any approved content changes the digest and blocks
  // activation, for prompts, translations, options, hints, examples, types,
  // and review focuses.
  const digestCases = [
    ["prompt", (target) => { target.client.questionText = "Which numeral shows twenty thousand and four?"; }],
    ["translation", (target) => { target.client.questionTextBm = "Angka manakah menunjukkan dua puluh ribu lima?"; }],
    ["option", (target) => { target.client.options[3] = "204 004"; }],
    ["option translation", (target) => { target.client.optionsBm[3] = "204 004"; }],
    ["hint", (target) => { target.answerKey.feedbackByOption["0"].hint = "Think about the thousands group again."; }],
    ["hint translation", (target) => { target.answerKey.feedbackByOption["0"].hintBm = "Fikirkan kumpulan ribu sekali lagi."; }],
    ["example", (target) => { target.answerKey.feedbackByOption["0"].example = "In 31 006, the 31 shows 31 thousands."; }],
    ["example translation", (target) => { target.answerKey.feedbackByOption["0"].exampleBm = "Dalam 31 006, angka 31 menunjukkan 31 ribu."; }],
    ["question type", (target) => { target.client.questionType = "Read a number"; }],
    ["question type translation", (target) => { target.client.questionTypeBm = "Baca nombor"; }],
    ["review focus", (target) => { target.answerKey.feedbackByOption["0"].reviewFocus = "Read the thousands group first."; }],
    ["review focus translation", (target) => { target.answerKey.feedbackByOption["0"].reviewFocusBm = "Baca kumpulan ribu dahulu."; }],
  ];
  for (const [label, mutate] of digestCases) {
    const tampered = clone(allQuestions);
    const target = questionById(tampered, "q_y4_whole_read_write_easy_01");
    mutate(target);
    // Compare against the original approval snapshot: the stored digest no
    // longer matches the changed content, so activation must be blocked.
    const errors = verificationErrors(tampered, manifest);
    assert.ok(
      errors.some((error) => error.includes("content digest changed after approval")),
      `changing ${label} must block activation`,
    );
  }

  // The digest itself must be stable for identical content.
  const original = questionById(allQuestions, "q_y4_whole_read_write_easy_01");
  assert.equal(
    canonicalQuestionDigest(original),
    canonicalQuestionDigest(clone(original)),
    "identical content must produce the same digest",
  );

  console.log(
    "PASS: question bank pedagogy contract holds for " +
      `${allQuestions.length} source-grounded bilingual questions.`,
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
