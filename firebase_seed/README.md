# Logic Oasis Firebase Seed

This folder seeds the FYP1 demo Firestore database.

## Files

- `seed_data.json`: demo data for the Logic Oasis AI-driven FYP1 prototype.
- `seed_firestore.js`: script that uploads the demo data to Cloud Firestore.
- `year4_read_write_question_banks.js`: trusted seed source for the three
  FYP1 read/write-number banks and their server-only answer keys.
- `year4_whole_numbers_additional_banks.js`: source-grounded Easy banks for the
  four follow-on Whole Numbers subtopics.
- `content_source_manifest.js`: server-only approval manifest that records
  material checksums, bilingual locators, content digests, and reviewer state
  for every active question.
- `package.json`: Node dependency setup for `firebase-admin`.
- `serviceAccountKey.json`: your private Firebase key. Keep this local only.

## Setup

1. Put your Firebase service account file in this folder.
2. Rename it to `serviceAccountKey.json`.
3. Install the seed dependency:

```powershell
npm install
```

4. Run the seed:

```powershell
npm run seed
```

Before seeding, validate the client/server content split:

```powershell
npm run validate:question-banks
```

Run the full contract test suite (pedagogy + Firestore rules):

```powershell
firebase emulators:exec "npm test"
```

The script uses `merge: true`, so rerunning it updates the same demo documents instead of creating random duplicates.

## Demo Collections

- `users`
- `parentLinks`
- `topics`
- `subtopics`
- `questions`
- `questionBanks`
- `questionAnswerKeys` (server-only; Firestore rules deny every client read)
- `quizAttempts`
- `topicMastery`
- `subtopicMastery`
- `oasisProgress`
- `forumPosts`
- `forumReplies`
- `moderationLogs`
- `helperReputation`
- `studyBuddyRecommendations`
- `aiModelRuns`
- `parentReports`

## Current Learning Seed

The current Year 4 adaptive evidence slice is grounded in the uploaded
textbooks under `topic material/` (Year 4-6 KSSR Semakan 2017, BM and DLP
English copies). The app's topic/subtopic page follows the textbook structure:
eight topics per year for Years 4, 5, and 6, with only Year 4 Whole Numbers
currently playable.

- Topic: `whole_numbers_y4` / Numbers and Operations (Nombor dan Operasi),
  whole numbers up to 100 000.
- Exactly three bilingual banks: Easy, Moderate, and Hard.
- Exactly five active prompts per bank (five per subtopic, per the supervisor
  refinements); the quiz uses all five in each form.
- Firestore `questions` documents contain prompts/options only. The seed script writes answer indexes and explanations separately to `questionAnswerKeys`.
- Every active question carries a source material ID, bilingual locator,
  authored question type, per-option misconception feedback, and reviewed
  difficulty metadata. The server-only `contentSourceManifest` collection
  records the approval digest for each question.
- Attempts and mastery: 3 seeded attempts for `whole_numbers_y4`, with 2 of 5 subtopics completed and subtopic mastery documents for the attempted subtopics.
- Oasis persistence: one `oasisProgress` document with repaired area progress and saved settings fields.
- Parent/AI evidence: one active parent link, one parent report, and one AI model run aligned to the same Whole Numbers topic.

Follow-up Year 4-6 textbook topics are included as ordered placeholder topic
documents so the app can keep them locked until the previous topic is
completed. Authoring banks for those topics is rollout work.

## Readiness Checks

After editing seed data, run:

```powershell
node -e "const fs=require('fs'); JSON.parse(fs.readFileSync('firebase_seed/seed_data.json','utf8')); console.log('seed json ok')"
flutter analyze --no-pub
```

## Supervisor Refinements Verification

The supervisor quiz-learning-loop evidence is recorded in
`docs/evidence/2026-08-11-supervisor-quiz-refinements-verification.md`.
The automated seed gates are:

```powershell
# Content provenance, difficulty rubric, per-option feedback, no answer reveal
firebase emulators:exec "npm test"
node validate_question_banks.js
```

Expected output: the pedagogy contract passes for the 65 source-grounded
bilingual questions across Year 4, 5, and 6 (130 approved entries across the
six textbook materials), and the rules test proves students cannot read
`questionAnswerKeys` or
`contentSourceManifest`.
