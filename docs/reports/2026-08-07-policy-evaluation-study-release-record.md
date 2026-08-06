---
artifact_contract: logic-oasis-policy-evaluation-study-release-record/v1
release_status: developer_released
deployment_verification_status: emulator_and_ci_verified
developer_release:
  releaseId: PES-DEPLOY-2026-001
  releasedBy: zyonn
  releasedAt: 2026-08-07T00:00:00+08:00
  releaseRationale: "AQC-7 study-boundary release record. Bundle, Rules, IAM, callable secret binding, disposable study flow, non-participant regression, and cleanup contracts are verified; live cloud deployment remains a declared follow-up step."
  releaseScope: fyp1_policy_evaluation_study_boundary
  evidenceLevel: emulator_verified_demonstration
claim_level: mechanics_and_descriptive_only
---

# Policy Evaluation Study Release Record (AQC-7)

This record captures the AQC-7 deployment verification for the policy-evaluation
study boundary. It follows the developer-released convention (commit `6080cc8`)
and does not require further confirmation.

## Deployment revision and bundle

- Branch: `codex/feat-policy-evaluation-aqc`
- Revision before this record: `cd5a7e2`
- Functions bundle: `u8-ai-runtime-v1`
- `packageSha256`: `6641a757868f826484ac1e1063a1c4da92f467bbd7c34e68e8e3a788b3ffdfbd`
- `policyEvaluationSha256`: `a12d251e5910a034c081950a8bede8dc7753329db0e9c540af108143e9a43a61`
- Full manifest: `functions/vendor/bundle_manifest.json`

## Verified contracts

| Gate | Evidence | Result |
| --- | --- | --- |
| Bundle carries evaluation contract | Deployment-contract tests assert `policyEvaluationSha256` in the manifest, vendor `policy_evaluation.py`/config presence, and hash equality with the authoritative config | Pass |
| Allocation secret binding | `managePolicyEvaluationEnrollment` is the only callable with `POLICY_EVALUATION_ALLOCATION_KEY`; study/consent callables and the U8 runtime receive no secret | Pass |
| Admin IAM least privilege | IAM contract tests assert the evaluation-admin identity alone holds the allocation-secret accessor, the U8 runtime identity never does, broad/signing/model-scoped bindings are rejected, and rendered commands contain no secret material | Pass |
| Firestore Rules | Emulator-contract tests assert terminal denies for all eight `policyEvaluation*` collections plus the default deny; `firebase.json` wires `firestore.rules` and the `functions` source | Pass |
| Disposable enrolled-learner flow | Study-flow test: admin creates study -> records consent -> blocked enrollment allocates P1 -> runtime delivers blinded `assignment-delivery-v1` assignment, create-only decision audit (arm P1), and scheduled arm-neutral probe | Pass |
| Non-participant regression | Same flow without enrollment delivers the unchanged production P3 (`adaptive-policy-v1`) assignment and writes no audit/probe | Pass |
| Duplicate-delivery idempotency | Repeated finalization returns the same terminal state with one audit and one probe | Pass |
| Export/cleanup custody | AQC-6 release-governance tests prove deterministic pseudonymous releases, dedicated key separation, deletion certificates preceding key destruction, and unpublished-release cleanup | Pass |
| Revoked-enrollment boundary | Live-verify contract rejects audits after revocation and orphan audits; historical pre-revocation audits remain accepted | Pass |

## Suite results at this revision

- `ai_pipeline`: 137 tests OK
- `tools`: 45 tests OK
- `functions`: 97 tests OK

## Cleanup evidence

- Disposable flow data in the study-flow test is in-memory only and removed with
  the test process; no participant-level export is committed.
- The AQC-6 cleanup contract requires the dedicated retention identity and a
  deletion certificate before any key-version destruction; unpublished partial
  exports are removable only without a manifest.

## Declared limitation and follow-up

Live cloud deployment (IAM application, `firebase deploy`, and an authenticated
disposable-account smoke test against the deployed project) is deferred in this
record and remains the deployment step for the project owner, consistent with
the canonical FYP1 plan's allowance to demonstrate the automatic path through
the Firebase Emulator and disclose the limitation. No real participant is
enrolled and no comparison report is produced from disposable data.
