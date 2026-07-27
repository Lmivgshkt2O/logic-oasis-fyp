---
artifact_contract: logic-oasis-controlled-demo-release-evidence/v1
release_status: release_candidate
live_activation_status: pending
mechanism_approval_reference: supervisor-review-cdm-catalog-v1
model_activation_approval_status: pending
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
  packageSha256: 6499f8d4679d47ce87a2c2b8a25892acd316acc3a38887f4104dc22bd27c5425
  artifactSha256: 9a32079d95a37dc1d3eeecc52f5e7723e12ac1ee3dd8f6eb9dc609a3fa11f39a
  publicationManifestSha256: c7f29d46afbfab7509550e8a301b56bc89a713fd3e4685519ede6e0ed4c1a98e
  deploymentManifestSha256: 5e672f56933dd0a2575ebf97639594c7be21c7ac73cd082df7e8dd82154a46bb
  trainingDatasetVersion: controlled-demo-dataset-v1
  trainingDatasetSha256: 4f41f2cb3438ca4632235354980f51f8f36b88ede8846b89ac2d6714dbd02ec2
  scenarioCatalogueSha256: 0e984d84afd6ffcb8feef8340f73d6bcb74270bfe160bbdb27090627627237a8
  controlledDemoConfigSha256: d18cc9017e121885741c7fbdbb4aff0ffb9310202e6f4d5dc82c27185032f668
  evaluationReportSha256: 7c269eb0212b6a9196ee61de6f4a1169dbe4119aaef4250727959c2f8668c614
  featureSchemaVersion: quiz-attempt-features-v2
  featureSchemaSha256: 541d95732fb3ad3f0fc2e55e216057a0a89437994f0e06997f16363ff35d2293
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
---

# Controlled-demonstration XGBoost release evidence — 2026-07-24

## Release status and claim boundary

This is a reproducible **controlled-demonstration release candidate**. It proves
the training, native XGBoost UBJ inference, Tree SHAP, registry, adaptive
assignment, and safe projection mechanisms using supervisor-reviewed fictional
trajectories. It does not establish real-student accuracy, calibration, learning
improvement, or superiority over Decision Tree or MLP.

The catalogue mechanism approval reference is
`supervisor-review-cdm-catalog-v1`. The separate model-specific activation
approval is pending and is deliberately not fabricated in this repository. An
operator must supply the immutable `approvalId`, `approvedBy`, `approvedAt`, and
a rationale containing `not real-world validated` when running
`tools/deploy_controlled_demo_model.py`. Until that privileged transaction and
its resulting registry snapshot are reviewed, this document is candidate
evidence and must not be described as proof of a live activation.

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
3. Obtain the separate model-specific supervisor approval. Its rationale must
   state that the bundle is not real-world validated.
4. Run `tools/deploy_controlled_demo_model.py` with the approved bucket and
   approval fields. It uploads byte-verified immutable objects and performs the
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
compatible previously approved model is not available, remain in fail-closed
fallback while a new immutable candidate is evaluated and approved.

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
5. Obtain a new model-specific approval with `evidenceLevel: real_evaluated`
   and a real-data deployment scope. Controlled-demo approval cannot be reused.
6. Upload a new immutable artifact/manifest and perform one privileged
   one-active-record registry transaction. Never overwrite the demo objects.
7. Deploy the runtime in `real_evaluated_only` mode and verify the selected
   registry/package/schema/policy/target/label bindings.
8. Regenerate safe status and assignment projections only from a new trusted
   finalized attempt or an explicitly approved deterministic replay. Do not
   relabel existing controlled-demonstration projections as real evaluated.

No Flutter architecture change is required: the bounded safe projection field
already distinguishes `controlled_demonstration` from `real_evaluated`.

## Automated verification record

Verified locally on 2026-07-27:

- AI pipeline unit suite: 77 tests passed.
- Functions modules: 60 tests passed when isolated to avoid the known duplicate
  Firebase parameter registration caused by importing both entry-point names
  in one Python process.
- Tooling suite: 26 tests passed, including deterministic candidate/evidence
  binding, source/vendor parity, stale-file cleanup, registry, and deployment
  configuration checks.
- Focused controlled-demo Flutter projection/disclosure suite: 11 tests passed.
- Python compilation and staged-diff checks passed.

The unrelated full Flutter baseline still contains two independently
reproducible widget-test setup failures and seven existing analyzer
warning/info findings. They do not affect the native model, registry, bundle,
or bounded projection tests, but remain visible project cleanup rather than
being represented as a green full-suite result.
