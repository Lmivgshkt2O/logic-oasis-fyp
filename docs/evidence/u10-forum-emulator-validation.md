# U10 Forum Emulator Validation

Date: 2026-07-31  
Environment: Firebase Firestore + Python Functions Emulator (`logic-oasis-fyp`)

## Result

The command below completed successfully after an automatic Firestore event
triggered the forum runtime:

```powershell
firebase.cmd emulators:exec --only firestore,functions "node tools/run_forum_emulator_flow.js"
```

The smoke test writes one question and one reasoning-based answer, then waits
for all of the following server-owned records:

1. `forumAnswers/{answerId}.aiFeedback.state == completed`
2. `forumAiJobs/{answerId}.state == completed`
3. `forumAiRuns/{answerId}.state == completed`
4. a question-author `forumParticipationSummaries` document with one current
   Malaysia-week question count
5. an answer-author `forumParticipationSummaries` document with one current
   Malaysia-week answer count

The run also exposed an Admin SDK transaction-read iterator difference. U10 now
normalises that response before reading Firestore snapshots; the regression test
is `functions/tests/test_forum_runtime.py`.

## Artifact and evidence boundary

The emulator model is `functions/forum_model.joblib`, built from the
de-identified fixture at
`ai_pipeline/logic_oasis_ai/forum_ai/data/emulator_reviewed_examples.jsonl`.
Its manifest is `functions/forum_model_manifest.json`:

- model version: `forum-explanation-nb-v1`
- rows: 6 (3 per label)
- provenance: `synthetic_test`
- calibration: `not_calibrated`
- evidence state: `emulator_fixture_only`

This validates the technical flow only. It does not establish accuracy,
calibration, bilingual performance, or learner benefit. A future real-data
release must use the documented de-identified schema, approved provenance, a
reviewer reference, an author-grouped split where feasible, and recorded
precision/recall/F1/confusion-matrix/calibration evidence before any model
performance claim.
