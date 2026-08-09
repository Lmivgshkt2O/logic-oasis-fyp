# U10 Forum Controlled-Demonstration Release

Release `forum-controlled-demo-nb-v1-release-1` publishes the U4-selected
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

The controlled-scenario report records
`baselineComparisonResult: naive_bayes_advantage_demonstrated`. This statement
is limited to the fixed fictional U4 catalogue and does not establish an
advantage on real learner responses.

The immutable release record is [the bundled manifest](../../functions/forum_model_manifest.json).
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
