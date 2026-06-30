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
- `questions`
- `quizAttempts`
- `topicMastery`
- `oasisProgress`
- `forumPosts`
- `forumReplies`
- `moderationLogs`
- `helperReputation`
- `studyBuddyRecommendations`
- `parentReports`
