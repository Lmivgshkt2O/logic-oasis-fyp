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

## Flutter UI smoke â€” 2026-07-19

A separate disposable parent/student pair was created for one Flutter Web UI
smoke test. The parent was authenticated through the local Flutter app, opened
**Settings â†’ Parent Dashboard**, and the deployed callable returned exactly the
linked disposable child. The screen displayed only that child's safe
projections: one safe update, one mastery record, preliminary 60% mastery, and
the assigned next practice. It did not display raw attempts, response text, AI
jobs, model runs, SHAP detail, artifacts, or a parent-link document.

The smoke link was revoked immediately after the check. Both disposable Auth
accounts, both temporary `users` profiles, and all four safe projection
documents were deleted. Its immutable grant/revoke audit records and revoked
link remain as U9 audit evidence. The setup used the existing project-owner
credential with the project quota attached; it did not restore the removed
temporary service-account impersonation grant.

## Focused automated evidence

- Python U9 contracts: 10 tests passed.
- Python compilation for the callable context and live verifier: passed.
- Dart format validation for the U9 Dart files: passed.
- A stale Flutter SDK cache lock was cleared after confirming no active Flutter
  CLI process held it. Flutter 3.35.6 then started normally.
- Focused U9 widget tests passed: `flutter test --no-pub --reporter expanded
  --concurrency=1 test/linked_child_context_test.dart
  test/parent_dashboard_linked_child_test.dart` completed with **5 tests
  passed**. The dashboard's linked-child selector was also exercised through
  its pending-load race case.
