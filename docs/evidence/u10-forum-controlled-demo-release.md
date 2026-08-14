# U10 Forum Controlled-Demonstration Release

Release `forum-controlled-demo-nb-v1-release-4` publishes the U4-selected
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
at U5 commit `8e93e4d3937a00d50b0680f7d6f555936bb242df`. Release 2 remains preserved at
U6 commit `150b7d19524012df27f2f175bdf3af6005804312` with its local Emulator
evidence. Neither historical release was promoted to the cloud registry.
Release 4 reconciles the immutable payload with the newer `main` Functions
bundle, therefore has no active cloud predecessor, and keeps
`supersedesReleaseId` unset. Any replacement after cloud promotion must use
transactional supersession.

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

## Main integration reconciliation — 2026-08-11

Merging the later policy-evaluation runtime changed the authoritative Functions
package and bundle hashes without changing the selected forum artifact. The
candidate was therefore republished instead of rewriting release 2. Release 3,
preserved at integration commit `0b6d545`, exposed a stale policy-manifest
source hash during the full Functions gate and was withheld before push,
Emulator activation, or cloud deployment. Release 4 corrects that binding. The
artifact SHA-256 remains
`8307a480b5d5e61612b878653b2182d609ae594024ecae192e3677ace99a0049`,
the bounded source revision is
`01e74fe579a81a3b3f39c675297b6f4791f5fb2f2c9b7bb62d028da9e3225d1f`,
and the bundle-manifest SHA-256 is
`cd1c07d23dcb472776381c7d6af43e9357922fe882cfb879ef88267edb2ed14f`.
Focused release, bundle-parity, promotion, and runtime tests validate these
bindings. The retained full Emulator rehearsal remains release-2 evidence; a
fresh release-4 Emulator or authorized cloud rehearsal is required before
claiming deployment verification for this payload.

## Post-manual-verification follow-up release — 2026-08-14

Manual verification surfaced three product gaps that required runtime
changes: linked discussions now count once per student in the parent
count-only summary, authors can delete their own free-form question threads
and answers (immutable runs preserved), and linked discussion prompts render
their stored Bahasa Melayu snapshot when the app language is Malay. Because
`forum_runtime.py` and `main.py` changed, the immutable successor
`forum-controlled-demo-nb-v1-release-6` was published under CPython 3.11.9
with the same model artifacts (reasoning `6081fd60…`, relevance `8df2fea5…`),
code revision
`8886c767c39ce13adb49994e05c3d6eafff5cdadfec51f8feb9f1b384fdf95f2`,
and `supersedesReleaseId` release 5. It was promoted in the Firestore Emulator
registry with a local deployment attestation; release 5 remains preserved as
`superseded`. The authoritative forum function inventory grew to eleven
entries with the two author-delete callables.

A follow-up runtime change (same day) let students also remove a canonical
linked thread from their own forum list: a per-student
`forumQuestionDeletions` marker hides the shared discussion for that student
while the canonical thread and other students' answers stay intact. The
immutable successor `forum-controlled-demo-nb-v1-release-7` was published
under CPython 3.11.9 with the same model artifacts, code revision
`5cb68d79a5f235309d583140eb8ce2b5079fbd623f2f1846969be4645ca7b223`,
superseding release 6, and promoted in the Firestore Emulator registry.
