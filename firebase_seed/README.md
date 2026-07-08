# Logic Oasis Firebase Seed

This folder seeds the FYP1 demo Firestore database.

## Files

- `seed_data.json`: demo data for the Logic Oasis AI-driven FYP1 prototype.
- `seed_firestore.js`: script that uploads the demo data to Cloud Firestore.
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

The script uses `merge: true`, so rerunning it updates the same demo documents instead of creating random duplicates.

## Demo Collections

- `users`
- `parentLinks`
- `topics`
- `subtopics`
- `questions`
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

The current Year 4 seed mirrors the app's local Chapter 1 content:

- Topic: `whole_numbers_y4` / Whole Numbers up to 100 000.
- Subtopics: 5 bilingual KSSR-aligned subtopics.
- Questions: 50 bilingual quiz questions, 10 per subtopic.
- Bloom order per subtopic: Remember, Remember, Understand, Understand, Apply, Apply, Analyze, Analyze, Evaluate, Create.
- Attempts and mastery: 3 seeded attempts for `whole_numbers_y4`, with 2 of 5 subtopics completed and subtopic mastery documents for the attempted subtopics.
- Oasis persistence: one `oasisProgress` document with repaired area progress and saved settings fields.
- Parent/AI evidence: one active parent link, one parent report, and one AI model run aligned to the same Whole Numbers topic.

Follow-up Year 4 topics are included as ordered placeholder topic documents so
the app can keep them locked until the previous topic is completed.

## Readiness Checks

After editing seed data, run:

```powershell
node -e "const fs=require('fs'); JSON.parse(fs.readFileSync('firebase_seed/seed_data.json','utf8')); console.log('seed json ok')"
flutter analyze --no-pub
```
