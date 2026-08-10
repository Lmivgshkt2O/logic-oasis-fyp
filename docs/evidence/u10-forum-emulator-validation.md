# U10 Forum Emulator Validation

Initial mechanics run: 2026-07-31
U3 reliability rerun: 2026-08-03
U6 controlled-release closure run: 2026-08-09
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

## Historical synthetic mechanics boundary

The initial mechanics run used `functions/forum_model.joblib`, built from the
de-identified fixture at
`ai_pipeline/logic_oasis_ai/forum_ai/data/emulator_reviewed_examples.jsonl`.
At that time its manifest declared:

- model version: `forum-explanation-nb-v1`
- rows: 6 (3 per label)
- provenance: `synthetic_test`
- calibration: `not_calibrated`
- evidence state: `emulator_fixture_only`

That historical `synthetic_test` run validates mechanics only; it is not the
current bundled release and is not U6 controlled-activation evidence.

## U6 controlled-release rehearsal

The 2026-08-09 run used Firebase CLI `15.22.2`, Node `24.18.0`, Temurin Java
`21.0.11`, CPython `3.12.13`, Flutter `3.35.6`/Dart `3.9.2`, the Firestore
Emulator standard edition, Auth Emulator, and Python Functions Emulator. The
Functions runtime loaded release
`forum-controlled-demo-nb-v1-release-2` with revision
`937204cbdd672d1350cf4a05bf3887feb50bab41e7c97c16d716932948b0957d`.
No service-account key was used and no cloud seed or cloud deployment command
was run.

The rehearsal verified:

1. two authenticated students could ask, answer, revise, mark helpful, accept,
   report, and block through the implemented contracts;
2. the genuine released `MultinomialNB` produced `completed` feedback and two
   immutable revision-bound runs;
3. each run bound model `forum-controlled-demo-nb-v1`, artifact
   `8307a480b5d5e61612b878653b2182d609ae594024ecae192e3677ace99a0049`,
   and `claimLevel: controlled_demonstration_only`;
4. all four count-only participation counters converged once despite duplicate
   helpful and acceptance calls;
5. an active linked parent read the count-only projection and was denied seven
   raw question, answer, report, block, job, run, and registry reads;
6. revocation changed the next inference to safe `fallback` without modifying
   the prior completed run; and
7. the controlled corpus aggregate remained
   `0d83a44bbca58b57d3545c69ba277f227317a6fdf6baf0270b8a96f786a2a44a`
   before and after inference.

Captured Emulator output contained no submitted fictional text. The retained,
sanitized [machine-readable result](u10-forum-emulator-result.json) contains
only states, counters, release/model identities, hashes, and denial outcomes;
its SHA-256 is
`ea5fd2b7288a94161ede14326f0befac5390a8c138b904599a11e804f3c03152`.
The controlled evidence supports scenario fit, reproducibility,
artifact integrity, and prototype integration readiness only. A future
`real_evaluated` release still requires approved provenance, de-identification,
reviewer evidence, author-grouped evaluation where feasible, and recorded
precision/recall/F1/confusion-matrix/calibration evidence before any learner or
performance claim.
