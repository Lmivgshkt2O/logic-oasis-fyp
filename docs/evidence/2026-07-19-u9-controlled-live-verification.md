# U9 controlled live verification — 2026-07-19

## Scope

This verification used only temporary Firebase Authentication accounts created
by `tools/verify_u9_parent_live.py`. It did not use any real student, parent,
supervisor, or production-learning identity.

The controlled test created one temporary parent, one linked temporary student,
and one unrelated temporary parent. It seeded only these safe projections for
the linked student:

- `studentAiStatuses`
- `subtopicMastery`
- `adaptiveAssignments`
- `forumParticipationSummaries`

It did not seed or read a real raw attempt, answer response, forum text, AI job,
AI model run, SHAP detail, or model artifact.

## Deployed boundary

- Firestore Rules were deployed to `logic-oasis-fyp`.
- `getLinkedChildren`, `manageParentLink`, and `revokeParentLink` are deployed
  in `asia-southeast1` under the narrow parent-link runtime identity.
- The Cloud Run transport permits Firebase callable delivery; each handler
  verifies the Firebase ID token and applies its own authorization policy.
- The parent-link runtime identity has only Firebase Auth viewer, Firestore
  user, and logging writer permissions required for this flow.

## Live result

The controlled verifier completed successfully with:

```json
{
  "contextSelection": "passed",
  "grantAuditRecorded": true,
  "linkGrantAuditRecorded": true,
  "linkRevokeAuditRecorded": true,
  "linkedSafeProjectionReads": 4,
  "parentLinksDenied": true,
  "protectedReadsDenied": 5,
  "revokeAuditRecorded": true,
  "revokedDenied": true,
  "status": "passed",
  "unrelatedDenied": true
}
```

The five denied protected reads covered raw quiz attempts, forum text, AI jobs,
raw AI model-run/SHAP data, and model registry data. A direct `parentLinks`
read was separately denied. Both an unrelated parent and the revoked parent
received an empty linked-child callable context and were denied the safe status
projection. The controlled grant and revocation each wrote a dedicated immutable
parent-link audit record with a `TEST-U9-LIVE-*` approval reference.

## Cleanup

The verifier deleted all temporary Auth accounts, temporary `users` profiles,
and seeded safe projection documents in its cleanup path. It intentionally
retained the immutable supervised grant/revoke audit records and the revoked
link record required by U9 auditing. The developer's temporary
`roles/iam.serviceAccountTokenCreator` binding on
`logic-oasis-identity-admin` was removed immediately after the run; the normal
`roles/iam.serviceAccountUser` deployment binding remains.

## Focused automated evidence

- Python U9 contracts: 10 tests passed.
- Python compilation for the callable context and live verifier: passed.
- Dart format validation for the U9 Dart files: passed.
- Flutter focused widget tests could not be accepted as passing in this Codex
  environment: `flutter test` produced no output and hung twice. The orphaned
  test processes were terminated without touching active editor tooling. The
  test files remain ready to run locally:
  `test/linked_child_context_test.dart` and
  `test/parent_dashboard_linked_child_test.dart`.
- The Flutter test runner and `flutter analyze` both hung without output in
  this Codex environment; neither was recorded as passing. The isolated Dart
  processes they left behind were terminated without touching editor tooling.
