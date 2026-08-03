# U10 Forum Emulator Validation

Initial mechanics run: 2026-07-31
U3 reliability rerun: 2026-08-03
Environment: Firebase Firestore + Python Functions Emulator (`logic-oasis-fyp`)

## Result

The command below completed successfully after an automatic Firestore event
triggered the forum runtime:

```powershell
$env:FUNCTIONS_DISCOVERY_TIMEOUT='60000'
firebase.cmd emulators:exec --only auth,firestore,functions "node tools/run_forum_emulator_flow.js"
```

The smoke test writes one question and one reasoning-based answer, then waits
for all of the following server-owned records:

1. `forumAnswers/{answerId}.aiFeedback.state == completed`
2. `forumAiJobs/{answerId}.state == completed`
3. `forumAiRuns/{logicalInferenceId}.state == completed`, where the logical
   identity binds the answer revision, text hash, model, and advisory policy
4. a question-author `forumParticipationSummaries` document with one current
   Malaysia-week question count
5. an answer-author `forumParticipationSummaries` document with one current
   Malaysia-week answer count

The reliability smoke then edits that answer to revision `2` through the normal
student write path. The update trigger must create a second immutable logical
run, leave the revision `1` run audit-only, and publish feedback only when the
job lease generation, revision, text hash, model, and policy still match. The
smoke also exercises duplicate helpful and acceptance calls; their immutable
action timestamps repair the originating weekly aggregate without duplicating
or regressing the current Malaysia-week parent projection.

Focused Functions tests inject concurrent duplicate claims, expired leases,
stale fencing generations, out-of-order revisions, partial run-before-job
failure, transient retry exhaustion, permanent failure, and delayed historical
counter events. Verified model loading is cached only after manifest/artifact
validation succeeds; a missing or rejected artifact is not retained in the
warm-instance cache.

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
