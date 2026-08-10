---
artifact_contract: logic-oasis-controlled-demo-release-evidence/v1
release_status: developer_released
live_activation_status: verified
object_publication_status: verified
registry_activation_status: active
runtime_activation_status: deployed_verified
live_quiz_verification_status: passed_and_cleaned_up
catalogue_declaration_reference: developer-declaration-cdm-catalog-v1
release_declaration:
  releaseId: CDM-2026-001
  releasedBy: zyonn
  releasedAt: 2026-07-27T00:00:00+08:00
  releaseRationale: "Developer-released FYP1 controlled-demonstration XGBoost model trained on fictional trajectories; not real-world validated."
  releaseScope: fyp1_controlled_demo
  trainingDataProvenance: expert_authored_controlled_demo
  evidenceLevel: controlled_demonstration
  deploymentScope: controlled_demo
claim_level: controlled_demonstration_only
contains_scenario_content: false
runtime:
  evidence_mode: controlled_demo
  model_bucket: logic-oasis-models
  artifact_uri: gs://logic-oasis-models/controlled-demo/controlled-demo-xgboost-v1/model.ubj
  manifest_uri: gs://logic-oasis-models/controlled-demo/controlled-demo-xgboost-v1/manifest.json
bindings:
  bundleVersion: u8-ai-runtime-v1
  modelVersion: controlled-demo-xgboost-v1
  packageSha256: 0955871b3c35b0ec4eb61043f92bb8bbf6bef1a0ba544e83ec3d170d82c3fff3
  artifactSha256: 9a32079d95a37dc1d3eeecc52f5e7723e12ac1ee3dd8f6eb9dc609a3fa11f39a
  publicationManifestSha256: 470f7dca79f14035d910aae45958d6f21f85423b44d01c6bc5830ffbb914ed4e
  deploymentManifestSha256: 459222fb89750da8196e3573b4343e8390e914e52bf51b032765257860d1059b
  trainingDatasetVersion: controlled-demo-dataset-v1
  trainingDatasetSha256: adb666f4a497044c6e908b1f57048da564b965fca8795234471ec13b8285b2c6
  scenarioCatalogueSha256: 5a19431be1188ddc8df32fbfa4c610c5b3d912811984c861d79029ec15606af0
  controlledDemoConfigSha256: 7e47adae0d00a84bd7cff39686029221255d9f096240c70263eacb03f3a1fdc7
  evaluationReportSha256: 7c269eb0212b6a9196ee61de6f4a1169dbe4119aaef4250727959c2f8668c614
  featureSchemaVersion: quiz-attempt-features-v2
  featureSchemaSha256: e9eb98fb23badfcf68618af737662a7efc9dbc1b17d91dc0a32004aad26865d6
  weakTopicRankingPolicySha256: 37164e70e6bbae4b821e58bb03587acef65457f0d2800b4aa1da4e3ed5244848
  adaptivePolicySha256: 1b53aef77a8027b4256f915663ee894225c17efe4f876bff2e23a38ed17eef16
  predictionTarget: next_attempt_support_needed
  labelVersion: next-attempt-support-needed-v1
  evidenceLevel: controlled_demonstration
  deploymentScope: controlled_demo
toolchain:
  python: 3.11.9
  platform: Windows-10-10.0.26200-SP0
  xgboost: 3.2.0
  scikit-learn: 1.9.0
  numpy: 2.4.6
  shap: 0.51.0
  joblib: 1.5.3
  pandas: 3.0.3
  PyYAML: 6.0.3
shap_samples:
  - riskTier: low
    supportRisk: 0.14796571
    reconstructedRisk: 0.14796570
    absoluteError: 0.0000000142
  - riskTier: medium
    supportRisk: 0.87733501
    reconstructedRisk: 0.87733496
    absoluteError: 0.0000000502
  - riskTier: high
    supportRisk: 0.89040530
    reconstructedRisk: 0.89040529
    absoluteError: 0.0000000092
deployment_observation:
  temporaryPublisher:
    member: zyonn1509@gmail.com
    roles: [roles/storage.objectCreator, roles/storage.objectViewer]
    scope: gs://logic-oasis-models
    bindingsRemoved: true
    effectiveDenialCheck: passed
  bucketControls:
    location: ASIA-SOUTHEAST1
    uniformBucketLevelAccess: true
    publicAccessPrevention: enforced
  bucketIamPolicies:
    before:
      etag: CAI=
      objectViewer: [serviceAccount:logic-oasis-ai-runtime@logic-oasis-fyp.iam.gserviceaccount.com]
    temporaryPublisher:
      etag: CAQ=
      objectCreator: [user:zyonn1509@gmail.com]
      objectViewer: [serviceAccount:logic-oasis-ai-runtime@logic-oasis-fyp.iam.gserviceaccount.com, user:zyonn1509@gmail.com]
    final:
      etag: CAY=
      objectViewer: [serviceAccount:logic-oasis-ai-runtime@logic-oasis-fyp.iam.gserviceaccount.com]
  artifactObject:
    generation: 1785157604327827
    size: 31211
    sha256: 9a32079d95a37dc1d3eeecc52f5e7723e12ac1ee3dd8f6eb9dc609a3fa11f39a
  manifestObject:
    generation: 1785157604827655
    size: 3440
    sha256: 26796bd788df25b0c9cff015a49a5de2295457b6a4180e80beccbd3ade7cff02
  activeRegistryCount: 1
  deploymentResult: successful_update
  deployedRevision: processfinalizedquizattempt-00012-nax
  deployedFunctionState: ACTIVE
  deployedServiceAccount: logic-oasis-ai-runtime@logic-oasis-fyp.iam.gserviceaccount.com
  deployedAiEnvironment:
    AI_MODEL_EVIDENCE_MODE: controlled_demo
    AI_MODEL_BUCKET: logic-oasis-models
  postDeploymentVerification: passed
  disposableQuiz:
    attemptId: cdm-live-attempt-20260728-002
    jobStatus: completed
    jobAttemptCount: 1
    statusCode: model_completed
    releaseId: CDM-2026-001
    modelVersion: controlled-demo-xgboost-v1
    modelEvidenceState: controlled_demonstration
    shapFeatureCount: 2
    masteryProjectionPresent: true
    snapshotProjectionPresent: true
    assignmentProjectionPresent: true
    unsafeProjectionFields: []
    cleanupVerified: true
  temporaryIamAudit:
    serviceAccount: logic-oasis-iam-audit@logic-oasis-fyp.iam.gserviceaccount.com
    customPermission: storage.buckets.getIamPolicy
    conditionTitle: temporary_cdm_bucket_iam_audit
    result: impersonation_denied
    bindingsRemoved: true
    serviceAccountDeleted: true
    customRoleDeleted: true
  storageIamDiagnosis:
    checkedAt: 2026-07-28
    activeAccount: zyonn1509@gmail.com
    activeProject: logic-oasis-fyp
    projectParent: null
    projectOwnerBinding: unconditional
    ownerIncludesGetIamPolicy: false
    ownerIncludesSetIamPolicy: false
    projectDenyPolicies: []
    projectPabBindings: []
    organizationPabBindings: []
    cause: missing_allow_binding
    recovery: temporary_bucket_resource_conditioned_storage_admin
    troubleshooterErrorId: CiQwMTlmYTRiMS1mNTNmLTdlOWUtOGE3NC1hMDFhM2Y3Zjc2OWQSJXByb2plY3RzL18vYnVja2V0cy9sb2dpYy1vYXNpcy1tb2RlbHM=
    blockingPolicy: none
    blockingResourceLevel: none
    requiredAdministratorAction: temporary_conditioned_allow_on_target_bucket_only
    temporaryAdminConditionTitle: temporary_cdm_bucket_iam_recovery
    temporaryAdminBindingRemoved: true
    postCleanupStoragePermissions: []
---

# Controlled-demonstration XGBoost release evidence — 2026-07-24

## Release status and claim boundary

This is a reproducible **developer-released controlled-demonstration candidate**. It proves
the training, native XGBoost UBJ inference, Tree SHAP, registry, adaptive
assignment, and safe projection mechanisms using developer-authored fictional
trajectories. It does not establish real-student accuracy, calibration, learning
improvement, or superiority over Decision Tree or MLP.

The catalogue declaration reference is
`developer-declaration-cdm-catalog-v1`. The immutable model release declaration
is `CDM-2026-001`, released by `zyonn` at `2026-07-27T00:00:00+08:00` for
`fyp1_controlled_demo`. It was created only after the CDM-2 catalogue,
evaluation, artifact, and SHAP evidence passed. The controlled-demo runtime was
then activated and verified with one disposable live quiz; this remains
mechanics evidence only, not evidence about real learners or model quality.

No scenario rows, fictional profile identifiers, question identifiers, or
learner records are reproduced here.

## Selected candidate and immutable evidence

The machine-readable front matter is the release source of truth for the
selected model, artifact objects, dataset/report/catalogue/configuration
lineage, Functions package, feature schema, policies, target, label, evidence
level, and deployment scope. The generated Functions bundle is
`u8-ai-runtime-v1`.

`tools/tests/test_function_bundle_parity.py` compares every authoritative
`ai_pipeline/logic_oasis_ai` source byte with its vendored Functions copy,
rejects stale package/config files, and independently recalculates these
manifest hashes. The deploy tool then adds the selected artifact, manifest,
target, and policy bindings before uploading immutable objects.

## Tree SHAP integrity samples

The samples below contain only bounded mechanics evidence from the committed
report. They contain no scenario content or learner identity.

| Risk tier | Support risk | Reconstructed risk | Absolute error |
| --- | ---: | ---: | ---: |
| Low | 0.14796571 | 0.14796570 | 0.0000000142 |
| Medium | 0.87733501 | 0.87733496 | 0.0000000502 |
| High | 0.89040530 | 0.89040529 | 0.0000000092 |

All three reconstructions are within `1e-5`. Native runtime tests also reject
missing target classes, invalid probabilities, malformed or non-finite SHAP
output, explainer failure, and reconstruction mismatch.

## Deployment configuration and release sequence

The candidate hashes above were reproduced with the exact toolchain recorded in
front matter. Reproduction on another operating system or dependency set is a
new candidate until its artifact and manifests are independently verified.

The controlled demonstration is enabled only with both explicit bindings:
`AI_MODEL_EVIDENCE_MODE=controlled_demo` and
`AI_MODEL_BUCKET=logic-oasis-models`. The fail-closed parameter default remains
`real_evaluated_only` with an empty model bucket.

Release order:

1. Run `py -3.11 tools/build_function_bundle.py`, then the parity and runtime
   identity tests. Do not hand-edit `functions/vendor`.
2. Reproduce the candidate bundle and verify the hashes above against its UBJ
   artifact, publication manifest, configuration, and mechanics report.
3. Confirm the immutable developer release declaration above, including the
   rationale that the bundle is not real-world validated.
4. Run `tools/deploy_controlled_demo_model.py` with the declared bucket and
   developer-release fields. It uploads byte-verified immutable objects and performs the
   one-active-record registry switch in one privileged transaction.
5. After the one-time identity bootstrap, deploy the Functions runtime using
   `tools/deploy_u8_runtime_iam.py --model-bucket gs://logic-oasis-models
   --runtime-only --evidence-mode
   controlled_demo`. Review the resulting command before adding `--apply`.
6. Finalize one disposable controlled-demo quiz and verify a `completed` raw
   run, bounded `modelEvidenceState: controlled_demonstration` status and
   assignment projections, and no client access to raw features or SHAP data.

## Disable and rollback route

The immediate safe rollback is configuration-only: redeploy with
`tools/deploy_u8_runtime_iam.py --model-bucket gs://logic-oasis-models
--runtime-only --evidence-mode real_evaluated_only --apply`. Runtime-only mode
skips the non-idempotent service-account bootstrap, so an existing deployment
cannot prevent the configuration change. A controlled-demo registry record then
fails the runtime evidence gate and the established BKT/rule fallback remains
functional; the runtime never loads the legacy pickle or hard-coded model
weights. Keep the immutable artifact and registry audit record for review.

Replacing or reactivating a model is an explicit privileged registry change,
never an artifact overwrite. The transaction must deactivate the current
record and activate exactly one complete, compatible approved record. If a
compatible previously released model is not available, remain in fail-closed
fallback while a new immutable candidate is evaluated and released.

## Real-data replacement checklist

A future `real_evaluated` candidate is a separate evidence lineage and must not
retune or relabel this controlled-demo artifact in place.

1. Record approved consent/ethics, stewardship, retention, and deletion
   governance for a protected release.
2. Produce the pseudonymized export through the approved real-data identity;
   retain its manifest and key version without raw learner identifiers or key
   material.
3. Build next-attempt labels from compatible later attempts and evaluate with a
   student-grouped split containing the required classes.
4. Produce a real-data report covering data sufficiency, calibration,
   false-negative trade-offs, operational slices, fallback rate, and limits.
5. Create a separately governed release declaration with
   `evidenceLevel: real_evaluated` and a real-data deployment scope. The
   controlled-demo declaration cannot be reused.
6. Upload a new immutable artifact/manifest and perform one privileged
   one-active-record registry transaction. Never overwrite the demo objects.
7. Deploy the runtime in `real_evaluated_only` mode and verify the selected
   registry/package/schema/policy/target/label bindings.
8. Regenerate safe status and assignment projections only from a new trusted
   finalized attempt or an explicitly approved deterministic replay. Do not
   relabel existing controlled-demonstration projections as real evaluated.

No Flutter architecture change is required: the bounded safe projection field
already distinguishes `controlled_demonstration` from `real_evaluated`.

## Cloud activation observation — 2026-07-27

The `logic-oasis-models` bucket was created in `asia-southeast1` with uniform
bucket-level access and enforced public-access prevention. A temporary
conditional grant gave `zyonn1509@gmail.com` only
`roles/storage.objectCreator` and `roles/storage.objectViewer` for this bucket.
No project-wide Storage role was granted.

Both unique versioned objects were absent before publication. They were uploaded
with `ifGenerationMatch=0`, downloaded again, compared byte-for-byte, and
independently SHA-256 verified before the registry transaction. The generations,
sizes, and hashes are recorded in front matter. Firestore then contained exactly
one active registry record, `xgboost-controlled-demo-xgboost-v1`, with release
`CDM-2026-001` and all declared package, schema, artifact, policy, dataset,
catalogue, configuration, report, evidence, and deployment bindings.

The first deployment attempts exposed three independent preparation failures:
the isolated worktree lacked `functions/venv`, Cloud Runtime Config was
temporarily unavailable, and two non-secret parent-invitation values were
missing from the ignored deployment `.env`. The virtual environment and values
were restored, Firebase analytics was disabled only for each deployment
session, and the exact single-function dry run passed before deployment. No
parent-invitation secret value was added to source control or printed in this
evidence.

The first successful target deployment produced revision
`processfinalizedquizattempt-00011-hin`. Its first disposable quiz exposed a
runtime compatibility fault before job claim: the installed Firebase Functions
SDK represents `StringParam.value` as a string property, while the handler
called it as a method. Eventarc delivery was working and the logs consistently
reported `TypeError: 'str' object is not callable` at the evidence-mode lookup.
The attempt timed out with no `aiJobs` record and every uniquely named input and
output document was deleted and re-read as absent.

Parameter resolution was made compatible with both property- and method-based
SDK shapes and covered by regression tests. The unchanged exact target passed a
new dry run and was redeployed as active revision
`processfinalizedquizattempt-00012-nax`. The readback confirmed the dedicated
`logic-oasis-ai-runtime` service account,
`AI_MODEL_EVIDENCE_MODE=controlled_demo`, `AI_MODEL_BUCKET=logic-oasis-models`,
the Firestore-created event type, and retry enabled. Project IAM readback showed
no temporary Storage Admin condition and no project Storage role for the
publisher.

The fresh disposable attempt `cdm-live-attempt-20260728-002` completed on its
first claim with `model_completed`, release `CDM-2026-001`, model version
`controlled-demo-xgboost-v1`, and evidence state
`controlled_demonstration`. Native inference returned a bounded support-risk
value and Tree SHAP returned two feature contributions. Mastery, snapshot, and
assignment projections were present; the client-facing projections contained
no raw feature values, SHAP values, artifact paths, or artifact/package hashes.
All exact disposable input and output documents were deleted and independently
re-read as absent. This verifies deployment mechanics only and makes no claim
about real-student accuracy, calibration, learning improvement, or superiority.

A temporary audit service account and custom role had been attempted during an
earlier diagnosis, but impersonation failed and both were deleted with their
bindings. They were not recreated during the successful recovery.

## Storage IAM denial diagnosis — 2026-07-28

The active Cloud SDK account and project were confirmed as
`zyonn1509@gmail.com` and `logic-oasis-fyp`. Policy Troubleshooter requests for
the exact bucket resource reproduced `storage.buckets.getIamPolicy` denial and
issued error IDs, but could not expose the bucket policy to this caller.

The effective allow-policy diagnosis is nevertheless conclusive. Project
`559775119210` has no organization or folder parent, its `roles/owner` binding
for this user is unconditional, and the current predefined Owner role contains
neither `storage.buckets.getIamPolicy` nor `storage.buckets.setIamPolicy`.
Project Deny policies and project PAB bindings are empty. The visible
`zyonn1509-org` has no principal-set PAB binding for this account; because this
project is not its descendant, organization Deny policy inheritance cannot
govern the bucket resource. The cause is therefore a missing effective allow
binding after the bucket policy was narrowed, not a Deny policy, PAB, conditional
Owner binding, unavailable bucket, or mis-owned project.

The denied post-cleanup `getIamPolicy` request is traceable by Troubleshooter
error ID
`CiQwMTlmYTRiMS1mNTNmLTdlOWUtOGE3NC1hMDFhM2Y3Zjc2OWQSJXByb2plY3RzL18vYnVja2V0cy9sb2dpYy1vYXNpcy1tb2RlbHM=`.
There is no blocking policy or blocking ancestor resource level; the required
administrator action was a minimal temporary allow on the target bucket.

The authorized recovery used a temporary project IAM binding of
`roles/storage.admin` with title `temporary_cdm_bucket_iam_recovery`, whose
condition required both
`resource.type == "storage.googleapis.com/Bucket"` and
`resource.name == "projects/_/buckets/logic-oasis-models"`. It must be removed
immediately after the bucket-level policy is restored and verified. The binding
made both `storage.buckets.getIamPolicy` and
`storage.buckets.setIamPolicy` effective without granting unconditioned project
Storage administration.

The preserved bucket policy had etag `CAI=` and only the dedicated runtime
service account in `roles/storage.objectViewer`. Temporary bucket-level
`roles/storage.objectCreator` and `roles/storage.objectViewer` grants for
`zyonn1509@gmail.com` produced etag `CAQ=`. The two existing immutable objects
were not overwritten: their generations, byte lengths, and SHA-256 values were
downloaded and verified against the generated manifest before the single active
developer-release registry record was accepted. The controlled-demo gate
accepted it and `real_evaluated_only` returned
`model_evidence_incompatible`.

Both publisher roles were removed. The authoritative final bucket policy,
captured after that removal and before removal of the project condition, had
etag `CAY=` and exactly one binding:
`roles/storage.objectViewer` for
`logic-oasis-ai-runtime@logic-oasis-fyp.iam.gserviceaccount.com`. No bucket
mutation followed this capture. The project condition was then removed; after
IAM propagation, the publisher's effective bucket IAM and object create/read
permission set was empty. A later direct bucket-policy read was therefore
expected to be denied. A redundant Cloud Asset inventory route was not enabled
solely for this audit because the API was disabled; the preserved final policy,
project-policy cleanup readback, and successful live model object read provide
the final evidence chain.

## Automated verification record

Verified locally on 2026-07-28:

- AI pipeline unit suite: 78 tests and 6 subtests passed under the recorded
  Python 3.11 controlled-demo toolchain.
- Functions modules: 62 tests passed across 10 isolated modules to avoid the known duplicate
  Firebase parameter registration caused by importing both entry-point names
  in one Python process.
- Tooling suite: 26 tests passed, including deterministic candidate/evidence
  binding, source/vendor parity, stale-file cleanup, registry, and deployment
  configuration checks.
- Focused controlled-demo Flutter projection/disclosure suite: 11 tests passed
  across `ai_diagnosis_test.dart`, `ai_result_page_status_test.dart`, and
  `parent_dashboard_linked_child_test.dart`. Earlier sandboxed invocations
  stalled before Flutter startup because the SDK is installed outside the
  workspace; the same exact suite passed after narrowly scoped SDK access was
  granted.
- Python compilation and staged-diff checks passed.

The unrelated full Flutter baseline still contains two independently
reproducible widget-test setup failures and seven existing analyzer
warning/info findings. They do not affect the native model, registry, bundle,
or bounded projection tests, but remain visible project cleanup rather than
being represented as a green full-suite result.
