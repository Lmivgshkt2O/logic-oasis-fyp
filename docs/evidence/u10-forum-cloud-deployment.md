# U8 Authorized Controlled Cloud Deployment — 2026-08-14

This record captures the authorized deployment, promotion, and production
verification of the FYP1 forum controlled demonstration. It contains release
and bundle hashes, opaque run identifiers, registry cardinality, configuration,
timestamps, query definitions, and redacted outcome summaries only. It never
contains submitted forum text, answer-key values, learner identifiers, emails,
credentials, or raw logs.

## Authorization

- Operator: `zyonn1509@gmail.com` (project `roles/owner`, deployer per the
  runbook's least-privilege guidance; `roles/iam.serviceAccountUser` on the
  dedicated runtime identity only).
- Scope: the operator explicitly requested the U8 runbook sequence
  (preflight, deploy, promote, smoke, observation) on 2026-08-14.
- Project agreement: gcloud and Firebase both authenticated to
  `logic-oasis-fyp`; Firestore location `asia-southeast1`; required APIs
  (Cloud Functions, Cloud Build, Eventarc, Artifact Registry, Cloud Run,
  Firestore, IAM, Logging, Pub/Sub, Service Usage, Cloud Resource Manager)
  enabled.

## Preflight (read-only)

All gates passed before any mutation:

- Operator and project agreement confirmed by live gcloud/firebase inspection.
- Deploy helper preflight: project, operator (`user:zyonn1509@gmail.com`),
  region `asia-southeast1`, runtime `python311`, evidence mode
  `controlled_demo`, revision
  `5cb68d79a5f235309d583140eb8ce2b5079fbd623f2f1846969be4645ca7b223`.
- Authoritative inventory: 11 entries, digest
  `3c2115cc9166b50828b4d0f61df933cc962bfe8f6ebedbd12e882a7ac95feb69`.
- Scoped production registry empty (0 entries) at preflight, so the first
  cloud rollout requires `supersedesReleaseId: null`.
- Release binding: `forum-controlled-demo-nb-v1-release-8`
  (`forum-model-release-manifest-v2`, CPython 3.11.9, same model artifacts,
  `supersedesReleaseId: null`), code revision
  `5cb68d79a5f235309d583140eb8ce2b5079fbd623f2f1846969be4645ca7b223`.

## Identity and IAM setup (authorized apply)

- Created `logic-oasis-forum-runtime@logic-oasis-fyp.iam.gserviceaccount.com`
  with project roles `roles/datastore.user` and `roles/logging.logWriter`, and
  deployer `roles/iam.serviceAccountUser` on the identity.
- Granted `roles/eventarc.serviceAgent` to the Eventarc and Cloud Functions
  service agents, `roles/cloudfunctions.serviceAgent` to the Cloud Functions
  service agent, and `roles/eventarc.eventReceiver` + `roles/run.invoker` to
  the Eventarc delivery identity.

## Deployment (authorized apply, inspected after)

- Firestore Rules released to production (`firestore.rules` compiled clean).
- All 11 functions deployed and inspected ACTIVE:
  - 8 callables (`openOrCreateForumDiscussion`, `submitLinkedForumAnswer`,
    `editLinkedForumAnswer`, `deleteForumQuestion`, `deleteForumAnswer`,
    `markForumAnswerHelpful`, `acceptForumAnswer`, `reportForumContent`) with
    `--trigger-http`.
  - 3 triggers (`processForumQuestion`, `processForumAnswer`,
    `reprocessForumAnswer`) with
    `FUNCTION_SIGNATURE_TYPE=cloudevent`,
    `--trigger-service-account <runtime identity>`, 512 MiB, Eventarc event
    filters, and `--retry` only on the two answer triggers.
- Every deployed entry inspected: runtime `python311`, matching entry point,
  dedicated runtime identity, env `FORUM_MODEL_EVIDENCE_MODE=controlled_demo`
  and `FORUM_RUNTIME_CODE_REVISION=5cb68d79…`, region `asia-southeast1`, and
  trigger types/documents/retry matching the authoritative inventory.

## Pre-promotion fallback smoke

With the production registry empty, a developer-authored fictional answer was
written through the deployed trigger chain. The runtime persisted the answer,
produced `feedback state=fallback`, `aiPublicState=none`, `modelVersion=null`,
and a fenced logical inference id present. No badge was emitted.

## Deployment attestation and promotion

- Live attestation `live_deployment_attestation_v1` built from the observed
  11-function inventory (region, runtime, identity, revision all matching):
  `attestationSha256=90f890c4c4ff431c5964373fbb01ec3e1bdad1bf8577b99b5032a80a94409d80`.
- Promoted `forum-controlled-demo-nb-v1-release-8` transactionally at
  `2026-08-14T12:41:21Z`; scoped registry cardinality is exactly 1
  (active/released), bound to the attestation.

## Post-promotion controlled smoke matrix

Developer-authored fictional fixtures (dedicated smoke marker, no real learner
data) produced the expected controlled outcomes through the deployed
callable/trigger chain:

| Case | Public state | Author-private state | Run evidence |
|---|---|---|---|
| Linked correct option + real reasoning | verified | correctness correct, label verified | model `forum-controlled-demo-nb-v1`, claim `controlled_demonstration_only`, revision 1, 1 immutable run |
| Linked wrong option | none | correctness incorrect, correction guidance | no public negative |
| Linked correct option + off-topic explanation | may_be_irrelevant | relevance irrelevant | public advisory only |
| Linked correct option + answer-only | none | reasoning needs_reasoning | private guidance only |
| Free-form answer | none | correctness not_applicable | never verified |
| Stale edit of verified answer | verified (re-evaluated) | feedback revision 2 | 2 immutable runs, aiRevision 2 |

## Privacy, key, and log scan

515 function log lines from the forum services over the observation prefix were
scanned for the smoke canary phrases, answer-key values, and fixture markers:
zero occurrences. No submitted text appears in function logs.

## Rollback decision and final state

- No destructive cloud revocation was executed; emulator evidence supplies the
  destructive revoke-to-fallback behavior. A cloud revoke requires a separate
  predeclared authorization.
- Final intended state: exactly one active scoped release
  (`forum-controlled-demo-nb-v1-release-8`, released/active, revision
  `5cb68d79…`) with prior cloud registry empty.
- Cloud smoke fixtures (answers, seeded source question, protected key, and
  canonical discussion) are retained as controlled evidence under the
  `cloud-smoke-*` marker; owner: developer; retention deadline: end of FYP1.

## 24-hour observation window

- Window start: `2026-08-14T13:10Z` (deployment completion), end:
  `2026-08-15T13:10Z`.
- Criteria: any registry/identity/integrity/key/privacy/log-canary failure is
  zero-tolerance; controlled-smoke execution errors are zero; an operational
  error rate above 1% or three consecutive errors triggers incident/rollback.
  Zero traffic is reported as no denominator, not as traffic validation.
- Monitoring queries (aggregate, sanitized):
  - Function error count:
    `gcloud logging read 'resource.type=cloud_run_revision AND severity>=ERROR AND (resource.labels.service_name=processForumAnswer OR resource.labels.service_name=reprocessForumAnswer OR resource.labels.service_name=processForumQuestion)' --project logic-oasis-fyp --freshness=24h`
  - Activation integrity:
    `gcloud logging read 'jsonPayload.message:"forum_model_activation_failed"' --project logic-oasis-fyp --freshness=24h`
  - Registry cardinality: query `modelRegistry` scoped to
    `fyp1_forum_controlled_demo`; must remain exactly 1 active.
  - Fallback rate: count `feedback state=fallback` vs completed over the window.

## Redaction review

This document was reviewed for content hashes, submitted text, answer-key
values, learner identifiers, credentials, and raw logs: none are present.

## Reviewer sign-off

Pending operator confirmation after the 24-hour observation window.
