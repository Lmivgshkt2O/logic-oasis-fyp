# Forum Controlled Cloud Runbook

Read-only by default. Every mutation below is a separately authorized, explicit
apply step. No service-account key file is created or committed; credentials
use the authenticated operator's user account or approved impersonation.

## Identity, project, and region

- Project: `logic-oasis-fyp`
- Region: `asia-southeast1` (Firestore, Eventarc, Functions)
- Runtime: Cloud Run functions (Gen 2), `python311`
- Dedicated runtime identity:
  `logic-oasis-forum-runtime@logic-oasis-fyp.iam.gserviceaccount.com`
  (runtime roles: `roles/datastore.user`, `roles/logging.logWriter`)
- Deployer: your authenticated account with function-deployment permissions
  plus `roles/iam.serviceAccountUser` on the dedicated runtime identity only.
  The runtime/default-compute identity is never a release operator.

Verify the authenticated Firebase and gcloud projects both equal
`logic-oasis-fyp`; verify `firebase.json`, the Gen 2 function region, Eventarc
trigger location, and Firestore database location agree.

## Release and evidence mode source

The release revision and evidence mode come from the selected immutable
manifest, never from stale committed files:

1. Copy `functions/.env.logic-oasis-fyp.example` to
   `functions/.env.logic-oasis-fyp` (gitignored) and set:
   - `FORUM_MODEL_EVIDENCE_MODE=controlled_demo`
   - `FORUM_RUNTIME_CODE_REVISION=<manifest.codeRevision>`
2. Confirm `functions/forum_model_manifest.json` is
   `forum-model-release-manifest-v2` with `pythonVersion 3.11.x`, the
   dependency-lock digest, and both component artifacts.

## Function inventory (eleven entries)

The authoritative inventory lives in
`tools/forum_function_inventory.py` (`forum-function-inventory-v1`). Every
entry uses `asia-southeast1`, `python311`, and the dedicated runtime identity;
only the answer create/update triggers enable retry.

| Kind | Function | Trigger / entry point |
|---|---|---|
| Callable | openOrCreateForumDiscussion | `openOrCreateForumDiscussion` |
| Callable | submitLinkedForumAnswer | `submitLinkedForumAnswer` |
| Callable | editLinkedForumAnswer | `editLinkedForumAnswer` |
| Callable | deleteForumQuestion | `deleteForumQuestion` |
| Callable | deleteForumAnswer | `deleteForumAnswer` |
| Callable | markForumAnswerHelpful | `markForumAnswerHelpful` |
| Callable | acceptForumAnswer | `acceptForumAnswer` |
| Callable | reportForumContent | `reportForumContent` |
| Trigger | processForumQuestion | forumQuestions created |
| Trigger | processForumAnswer | forumAnswers created (retry) |
| Trigger | reprocessForumAnswer | forumAnswers updated (retry) |

## One-time IAM and Eventarc setup (observed 2026-08-14)

- Create the dedicated runtime service account
  `logic-oasis-forum-runtime@logic-oasis-fyp.iam.gserviceaccount.com` and bind
  `roles/datastore.user` and `roles/logging.logWriter` on the project.
- Grant the deployer `roles/iam.serviceAccountUser` on the runtime identity.
- Grant `roles/eventarc.serviceAgent` to `service-<project>@gcp-sa-eventarc.iam.gserviceaccount.com`
  and to `service-<project>@gcf-admin-robot.iam.gserviceaccount.com`, plus
  `roles/cloudfunctions.serviceAgent` to the Cloud Functions service agent.
- Grant `roles/eventarc.eventReceiver` and `roles/run.invoker` to the identity
  used for Eventarc delivery (the dedicated runtime service account when
  `--trigger-service-account` is used).

## Deploy flags (observed working contract)

- Callables deploy with `--trigger-http`.
- Triggers deploy with `--memory=512MiB` (the scikit-learn bundle exceeds the
  256 MiB default), `FUNCTION_SIGNATURE_TYPE=cloudevent` in the env vars
  (Firebase Python handlers receive a single CloudEvent argument),
  `--trigger-service-account <runtime-identity>`, the Eventarc event filters,
  and `--retry` only for the answer create/update triggers.
- `tools/deploy_forum_runtime_iam.py` emits these exact commands; run its
  dry-run preflight first and apply each emitted command.

## Deploy-before-promote order

1. **Preflight (read-only):** run the deploy helper's preflight with the
   operator account, evidence mode, and revision. Wrong project, operator,
   region, runtime, revision, or an unsafe operator identity aborts.
2. **Deploy Firestore Rules**, then the full eleven-entry forum inventory
   (dry-run first; apply only after explicit authorization).
3. **Inspect every deployed entry** (`gcloud functions describe ... --format
   json`): region, runtime, service account, entry point, trigger, and
   `--set-env-vars` values must match the selected manifest and inventory. Any
   missing, failed, or mismatched entry records a partial deployment and
   prohibits promotion; complete the same revision or redeploy the prior known
   revision while the registry remains unchanged (fail-closed).
4. **Pre-promotion fallback smoke:** submit a developer-authored fictional
   answer; with no compatible active release the runtime must persist the
   answer, fall back to advisory, and emit no verification badge.
5. **Live deployment attestation:** `deployment_attestation` accepts only the
   observed nine-function inventory with matching revision/region/identity and
   emits `live_deployment_attestation_v1` (`deploymentState: deployed`).
6. **Promote** exactly one scoped immutable release, bound to the attestation
   and to the authoritative inventory digest. First rollout requires an empty
   scoped registry and `supersedesReleaseId: null`; replacement must name the
   actual active release; unrelated registry scopes are never touched.
7. **Post-promotion smoke:** run the controlled smoke matrix (verified,
   incorrect, may-be-irrelevant, free-form advisory, stale edit, fallback) and
   record expected public/private/run states, function revision, release ID,
   and retry expectations. Canary text and answer keys must be absent from
   logs and evidence.
8. **Observe for 24 hours** with sanitized aggregate telemetry: function
   errors, retries, fallback rate, registry cardinality, runtime identity, and
   text-free logs. Any registry/identity/integrity/key/privacy/log-canary
   failure is zero-tolerance; controlled-smoke execution errors are zero;
   an operational error rate above 1% or three consecutive errors triggers an
   incident/rollback. Zero traffic is reported as no denominator, not as
   traffic validation.

## Abort conditions

Stop immediately when: the authenticated project is not `logic-oasis-fyp`;
the operator lacks explicit authority; the deployed runtime cannot match the
release dependencies and revision; the registry contains ambiguous active
records; the controlled candidate fails any precision/integrity gate; or any
deployed entry drifts from the selected revision.

## Rollback and restoration

- Non-destructive live dry-run is the default; destructive cloud revocation
  requires separate authorization with a predeclared terminal state.
- Revoke the exact active registry record without deleting it; new answers
  safely lose `AI-verified` (advisory fallback) while existing content, jobs,
  and runs remain immutable and the revoked record stays auditable.
- Restore service only through a rebuilt/redeployed immutable successor release
  that supersedes the revoked record; never reactivate or mutate a revoked ID.

## Evidence

Record only release/bundle hashes, opaque run IDs, registry cardinality,
configuration, timestamps, query definitions, and redacted summaries - never
content hashes, submitted text, answer keys, or raw logs. Include sections for
authorization, preflight, deployment attestation, registry transition, smoke
matrix, privacy/key/log scan, rollback decision/result, observation, final
state, redaction review, and reviewer sign-off.
