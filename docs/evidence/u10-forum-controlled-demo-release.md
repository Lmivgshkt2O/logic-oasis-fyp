# U10 Forum Controlled-Demonstration Release

Release `forum-controlled-demo-nb-v1-release-2` publishes the U4-selected
`MultinomialNB` TF-IDF pipeline for the bounded FYP1 forum demonstration. The
release is active only when `FORUM_MODEL_EVIDENCE_MODE=controlled_demo` and the
deployed `FORUM_RUNTIME_CODE_REVISION` equals the immutable release binding.
`real_evaluated_only`, missing configuration, invalid evidence, unsupported
dependencies, source/vendor drift, and artifact or bundle drift fail closed to
the existing deterministic advisory fallback.

This is a developer-released FYP1 controlled-demonstration model. It has not
been evaluated on real learner forum responses. Its training examples are
developer-authored fictional scenarios and are not silently expanded by forum
answers submitted at runtime. The release makes no production-validity,
learner-validity, calibration, or general Naive Bayes superiority claim.

The earlier `forum-controlled-demo-nb-v1-release-1` payload remains preserved
at U5 commit `8e93e4d3937a00d50b0680f7d6f555936bb242df`. It was withdrawn before any
cloud registry promotion after U6 detected stale runtime bindings. Release 2
therefore has no active registry predecessor and keeps `supersedesReleaseId`
unset; any future replacement of release 2 must use transactional supersession.

The controlled-scenario report records
`baselineComparisonResult: naive_bayes_advantage_demonstrated` from the
selection-stage validation comparison only. On the four-row untouched
fictional final test, MultinomialNB scored accuracy `0.75` and macro F1
`0.73333333`, while the deterministic comparison baseline scored `1.0` for
both. Therefore no general or final-test Naive Bayes superiority claim is
made.

The immutable release payload and activation contract is [the bundled manifest](../../functions/forum_model_manifest.json).
It binds the catalogue, generated dataset and manifests, rubric, evaluation
report, preprocessing and vectorizer contract, abstention policy, exact Python
dependencies, runtime fingerprint, bounded release-source revision, artifact bytes,
source/vendor runtime parity, and bundle manifest. The selected release has
`lifecycleStatus: released` and `isActive: true`; replacement must name it in
`supersedesReleaseId` and switch lifecycle state in one privileged transaction.
Revocation and supersession preserve prior records rather than deleting or
relabeling controlled evidence.

The privileged promotion and deactivation entry points are
`tools/promote_controlled_demo_model.py::promote_forum_controlled_demo_model`
and `revoke_forum_controlled_demo_model`.
It writes the bundled manifest under its immutable `releaseId` in the existing
`modelRegistry` collection. A replacement is created in the same transaction
that marks the previously active forum-scoped record inactive and superseded.
The Functions runtime re-reads active registry records for every event, while
the verified classifier cache is fenced by the canonical registry payload, so
revocation or supersession takes effect without reusing a stale warm model.

Cloud deployment is intentionally recorded as `pending_cloud_deployment`.
`tools/deploy_forum_runtime_iam.py` declares the dedicated
`logic-oasis-forum-runtime` identity and narrow datastore/log-writer roles.
Its deployment commands bind both the created-answer and updated-answer model
triggers to the same Functions source, controlled evidence mode, 64-character
release-source revision, Firestore path, region, retry policy, and identity.
Local/emulator verification is the U5 evidence boundary until those commands
are applied and captured by an authorized operator.

## Post-Deploy Monitoring and Validation

The deploying operator must validate the release for one controlled
demonstration session before widening access. Search structured Cloud Function
logs by release ID and failure code only; learner question or answer text must
not be logged. Healthy operation requires the configured release to load once,
forum-answer processing to complete without integrity or dependency failures,
and abstentions to continue through the deterministic advisory fallback.

Rollback immediately by restoring `FORUM_MODEL_EVIDENCE_MODE` to
`real_evaluated_only` if any artifact, bundle, source/vendor, dependency, code
revision, or one-active-release validation fails; if the release itself is
invalid, revoke it through the privileged registry transaction and preserve the
immutable audit record. The deployment owner must capture the release ID,
deployed revision, validation window, success/failure counts, fallback counts,
and rollback decision in the U10 evidence before cloud activation is considered
complete.

A compatible replacement is published with `--supersedes-release-id` and then
promoted transactionally. Direct mode-disable or revocation is the immediate
safe rollback; restoring automatic classification requires a new immutable
release ID that supersedes the currently active compatible record.

## U6 local activation evidence — 2026-08-09

U6 republished the same candidate artifact after establishing LF checkout
semantics for hash-bound text and reconciling the source/vendor/runtime bundle.
The artifact SHA-256 remained
`8307a480b5d5e61612b878653b2182d609ae594024ecae192e3677ace99a0049`;
the bounded source revision is now
`937204cbdd672d1350cf4a05bf3887feb50bab41e7c97c16d716932948b0957d`.

An Auth + Firestore + Functions Emulator rehearsal seeded the payload as
`modelRegistry/forum-controlled-demo-nb-v1-release-2`. A student answer and
revision each produced an immutable completed run bound to model
`forum-controlled-demo-nb-v1`, the artifact hash above, and
`claimLevel: controlled_demonstration_only`. The linked parent could read the
count-only summary and was denied seven raw forum, moderation, AI, and registry
reads. Revoking the registry record made the next answer fail closed to
`fallback` while the prior completed run remained unchanged.

The controlled-evidence aggregate SHA-256 was
`0d83a44bbca58b57d3545c69ba277f227317a6fdf6baf0270b8a96f786a2a44a`
before and after both rehearsals. The retained, sanitized
[Emulator result](u10-forum-emulator-result.json) has SHA-256
`ea5fd2b7288a94161ede14326f0befac5390a8c138b904599a11e804f3c03152`
and records zero matches for the submitted fictional question, answer,
revision, report reason, or fallback text. This proves local packaged payload,
promotion/revocation mechanics, and controlled runtime activation only. No
cloud registry record or cloud deployment was created; cloud status remains
`pending_cloud_deployment`.
