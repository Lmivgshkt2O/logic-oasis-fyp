"""Controlled live U9 parent-link and safe-projection verification.

Creates only temporary Firebase Auth accounts, proves the protected callable and
Rules boundaries, then deletes the temporary accounts and safe projection data.
The revoked parent link and immutable grant/revoke audit records are retained by
design as the security evidence required by U9.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from typing import Any
from urllib import error, request

import firebase_admin
from firebase_admin import auth, credentials, firestore
from google.auth import impersonated_credentials
from google.oauth2.credentials import Credentials


ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS = ROOT / "functions"
if str(FUNCTIONS) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS))

from bootstrap_parent_link_admin import IDENTITY_ADMIN_SERVICE_ACCOUNT, apply_claim_change
from parent_link_admin import PARENT_LINK_ADMIN_CLAIM, VerifiedAdmin, revoke_parent_link


PROJECT_ID = "logic-oasis-fyp"
FUNCTION_REGION = "asia-southeast1"
SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)


class VerificationError(RuntimeError):
    pass


class _ImpersonatedFirebaseCredential(credentials.Base):
    def __init__(self, credential: Any) -> None:
        self._credential = credential

    def get_credential(self) -> Any:
        return self._credential


def _http_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    bearer_token: str | None = None,
) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    call = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(call, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except error.HTTPError as failure:
        raw = failure.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {}
        return failure.code, parsed


def _sign_up(api_key: str, email: str, password: str) -> dict[str, str]:
    status, body = _http_json(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}",
        method="POST",
        payload={"email": email, "password": password, "returnSecureToken": True},
    )
    if status != 200:
        raise VerificationError(f"Temporary Firebase Auth account creation failed ({status}).")
    return {key: str(body[key]) for key in ("localId", "idToken")}


def _sign_in(api_key: str, email: str, password: str) -> str:
    status, body = _http_json(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}",
        method="POST",
        payload={"email": email, "password": password, "returnSecureToken": True},
    )
    if status != 200 or not isinstance(body.get("idToken"), str):
        raise VerificationError(f"Temporary Firebase Auth sign-in failed ({status}).")
    return body["idToken"]


def _firebase_document_url(collection: str, document_id: str) -> str:
    return (
        f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)"
        f"/documents/{collection}/{document_id}"
    )


def _assert_status(actual: int, expected: int, label: str) -> None:
    if actual != expected:
        raise VerificationError(f"{label}: expected HTTP {expected}, received {actual}.")


def _gcloud_access_token(gcloud_bin: str) -> str:
    return subprocess.check_output(
        [gcloud_bin, "auth", "print-access-token"], text=True
    ).strip()


def _identity_admin_app(gcloud_bin: str) -> firebase_admin.App:
    source = Credentials(
        token=_gcloud_access_token(gcloud_bin),
        # google-auth's impersonated credential currently compares this source
        # expiry with a naive UTC value on Windows. Keep the two values in the
        # same form so the temporary verification can refresh its token.
        expiry=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=45),
    )
    target = impersonated_credentials.Credentials(
        source_credentials=source,
        target_principal=IDENTITY_ADMIN_SERVICE_ACCOUNT,
        target_scopes=SCOPES,
        lifetime=1800,
    )
    return firebase_admin.initialize_app(
        _ImpersonatedFirebaseCredential(target),
        options={"projectId": PROJECT_ID},
        name="u9-live-verification",
    )


def _callable(function_url: str, token: str, data: dict[str, str]) -> dict[str, Any]:
    status, body = _http_json(
        function_url,
        method="POST",
        payload={"data": data},
        bearer_token=token,
    )
    if status != 200:
        raise VerificationError(f"Callable verification failed ({status}).")
    result = body.get("result")
    if not isinstance(result, dict):
        raise VerificationError("Callable response is malformed.")
    return result


def _verification_admin() -> VerifiedAdmin:
    return VerifiedAdmin(
        uid=IDENTITY_ADMIN_SERVICE_ACCOUNT,
        claims={PARENT_LINK_ADMIN_CLAIM: True},
    )


def _remove_stale_test_accounts(*, database: Any, app: firebase_admin.App) -> None:
    """Remove only accounts from an interrupted run of this exact verifier."""
    page = auth.list_users(app=app)
    while page is not None:
        for user in page.users:
            email = user.email or ""
            if email.startswith("u9-live-") and email.endswith("@example.invalid"):
                for collection in (
                    "studentAiStatuses",
                    "subtopicMastery",
                    "adaptiveAssignments",
                ):
                    for snapshot in database.collection(collection).where(
                        "studentId", "==", user.uid
                    ).stream():
                        snapshot.reference.delete()
                database.collection("forumParticipationSummaries").document(user.uid).delete()
                for snapshot in database.collection("parentLinks").where(
                    "parentId", "==", user.uid
                ).stream():
                    link = dict(snapshot.to_dict() or {})
                    if link.get("status") == "active" and isinstance(link.get("studentId"), str):
                        revoke_parent_link(
                            {
                                "parentId": user.uid,
                                "studentId": link["studentId"],
                                "supervisorApprovalId": f"TEST-U9-STALE-{user.uid}-REVOKE",
                                "rationale": "Controlled U9 verifier stale-run cleanup.",
                            },
                            _verification_admin(),
                            database,
                        )
                database.collection("users").document(user.uid).delete()
                auth.delete_user(user.uid, app=app)
        page = page.get_next_page()


def verify(*, api_key: str, manage_url: str, revoke_url: str, context_url: str, gcloud_bin: str) -> dict[str, Any]:
    nonce = secrets.token_hex(8)
    password = f"U9!{secrets.token_urlsafe(18)}"
    parent_email = f"u9-live-parent-{nonce}@example.invalid"
    student_email = f"u9-live-student-{nonce}@example.invalid"
    unrelated_email = f"u9-live-unrelated-{nonce}@example.invalid"
    app = _identity_admin_app(gcloud_bin)
    database = firestore.client(app)
    _remove_stale_test_accounts(database=database, app=app)
    created_uids: list[str] = []
    safe_refs: list[Any] = []
    parent_id = student_id = unrelated_id = ""
    link_created = False
    link_revoked = False
    link_grant_audit_id = link_revoke_audit_id = ""
    grant_audit_id = revoke_audit_id = ""
    try:
        parent = _sign_up(api_key, parent_email, password)
        student = _sign_up(api_key, student_email, password)
        unrelated = _sign_up(api_key, unrelated_email, password)
        parent_id, student_id, unrelated_id = (
            parent["localId"],
            student["localId"],
            unrelated["localId"],
        )
        created_uids.extend((parent_id, student_id, unrelated_id))
        now = datetime.now(timezone.utc)
        database.collection("users").document(parent_id).set(
            {"displayName": "U9 Test Parent", "yearLevel": 4, "role": "parent", "createdAt": now}
        )
        database.collection("users").document(student_id).set(
            {"displayName": "U9 Test Student", "yearLevel": 4, "role": "student", "createdAt": now}
        )
        grant_audit_id = apply_claim_change(
            database=database,
            uid=parent_id,
            action="grant",
            supervisor_approval_id=f"TEST-U9-LIVE-{nonce}-GRANT",
            rationale="User-authorized temporary U9 live verification; no real account is involved.",
            actor=IDENTITY_ADMIN_SERVICE_ACCOUNT,
            get_user=lambda uid: auth.get_user(uid, app=app),
            set_custom_user_claims=lambda uid, claims: auth.set_custom_user_claims(uid, claims, app=app),
            revoke_refresh_tokens=lambda uid: auth.revoke_refresh_tokens(uid, app=app),
        )
        parent_token = _sign_in(api_key, parent_email, password)
        linked = _callable(
            manage_url,
            parent_token,
            {
                "parentId": parent_id,
                "studentId": student_id,
                "supervisorApprovalId": f"TEST-U9-LIVE-{nonce}-LINK-GRANT",
                "rationale": "User-authorized temporary U9 parent-link verification.",
            },
        )
        link_created = True
        link_grant_audit_id = str(linked.get("auditId") or "")
        attempt_id = f"u9_live_attempt_{nonce}"
        safe_documents = {
            "studentAiStatuses": {
                attempt_id: {
                    "studentId": student_id,
                    "sourceAttemptSequence": 1,
                    "analysisState": "completed",
                    "displayCode": "analysis_complete",
                    "updatedAt": now,
                }
            },
            "subtopicMastery": {
                f"{student_id}_y4_whole_numbers_read_write": {
                    "studentId": student_id,
                    "yearLevel": 4,
                    "topicId": "whole_numbers",
                    "subtopicId": "read_write",
                    "lastSourceAttemptId": attempt_id,
                    "masteryProbability": 0.6,
                    "weakTopicPriorityScore": 0.4,
                    "evidenceLevel": "preliminary",
                    "observationCount": 1,
                    "rankingVersion": "weak-topic-ranking-v1",
                    "updatedAt": now,
                }
            },
            "adaptiveAssignments": {
                f"u9_live_assignment_{nonce}": {
                    "studentId": student_id,
                    "sourceAttemptId": attempt_id,
                    "subtopicId": "read_write",
                    "bankId": "whole_numbers_read_write_moderate_v1",
                    "difficultyLevel": "Moderate",
                    "policyVersion": "adaptive-policy-v1",
                    "reasonCode": "u9_live_test",
                    "reasonText": "Try one calm number-reading practice next.",
                    "evidenceCount": 1,
                    "usedBktFallback": True,
                    "createdAt": now,
                }
            },
            "forumParticipationSummaries": {
                student_id: {
                    "studentId": student_id,
                    "questionsPostedCount": 2,
                    "answersSubmittedCount": 1,
                    "acceptedAnswersCount": 0,
                    "helpfulReceivedCount": 3,
                    "updatedAt": now,
                }
            },
        }
        for collection, documents in safe_documents.items():
            for identifier, data in documents.items():
                reference = database.collection(collection).document(identifier)
                reference.set(data)
                safe_refs.append(reference)

        context = _callable(context_url, parent_token, {})
        children = context.get("children")
        if children != [{"studentId": student_id, "displayName": "U9 Test Student", "yearLevel": 4}]:
            raise VerificationError("Linked-child context did not return exactly the active child.")

        safe_statuses = [
            _http_json(_firebase_document_url("studentAiStatuses", attempt_id), bearer_token=parent_token)[0],
            _http_json(
                _firebase_document_url("subtopicMastery", f"{student_id}_y4_whole_numbers_read_write"),
                bearer_token=parent_token,
            )[0],
            _http_json(_firebase_document_url("adaptiveAssignments", f"u9_live_assignment_{nonce}"), bearer_token=parent_token)[0],
            _http_json(_firebase_document_url("forumParticipationSummaries", student_id), bearer_token=parent_token)[0],
        ]
        for index, status in enumerate(safe_statuses, start=1):
            _assert_status(status, 200, f"linked parent safe projection {index}")
        _assert_status(
            _http_json(_firebase_document_url("parentLinks", f"{parent_id}_{student_id}"), bearer_token=parent_token)[0],
            403,
            "parent link document",
        )
        protected_reads = {
            "raw quiz attempt": ("quizAttempts", "not-a-real-attempt"),
            "forum text": ("forumQuestions", "not-a-real-question"),
            "AI job": ("aiJobs", "not-a-real-job"),
            "raw AI model run and SHAP": ("aiModelRuns", "not-a-real-run"),
            "model data": ("modelRegistry", "not-a-real-model"),
        }
        for label, (collection, identifier) in protected_reads.items():
            _assert_status(
                _http_json(
                    _firebase_document_url(collection, identifier),
                    bearer_token=parent_token,
                )[0],
                403,
                label,
            )
        unrelated_token = _sign_in(api_key, unrelated_email, password)
        if _callable(context_url, unrelated_token, {}).get("children") != []:
            raise VerificationError("Unrelated parent unexpectedly received linked-child context.")
        _assert_status(
            _http_json(_firebase_document_url("studentAiStatuses", attempt_id), bearer_token=unrelated_token)[0],
            403,
            "unrelated parent safe projection",
        )
        revoked = _callable(
            revoke_url,
            parent_token,
            {
                "parentId": parent_id,
                "studentId": student_id,
                "supervisorApprovalId": f"TEST-U9-LIVE-{nonce}-LINK-REVOKE",
                "rationale": "User-authorized temporary U9 parent-link cleanup.",
            },
        )
        link_revoked = True
        link_revoke_audit_id = str(revoked.get("auditId") or "")
        _assert_status(
            _http_json(_firebase_document_url("studentAiStatuses", attempt_id), bearer_token=parent_token)[0],
            403,
            "revoked parent safe projection",
        )
        if _callable(context_url, parent_token, {}).get("children") != []:
            raise VerificationError("Revoked parent unexpectedly received linked-child context.")
        revoke_audit_id = apply_claim_change(
            database=database,
            uid=parent_id,
            action="revoke",
            supervisor_approval_id=f"TEST-U9-LIVE-{nonce}-REVOKE",
            rationale="Temporary U9 live verification cleanup; revoke the test administrator claim.",
            actor=IDENTITY_ADMIN_SERVICE_ACCOUNT,
            get_user=lambda uid: auth.get_user(uid, app=app),
            set_custom_user_claims=lambda uid, claims: auth.set_custom_user_claims(uid, claims, app=app),
            revoke_refresh_tokens=lambda uid: auth.revoke_refresh_tokens(uid, app=app),
        )
        return {
            "status": "passed",
            "linkedSafeProjectionReads": 4,
            "contextSelection": "passed",
            "unrelatedDenied": True,
            "revokedDenied": True,
            "protectedReadsDenied": len(protected_reads),
            "parentLinksDenied": True,
            "linkGrantAuditRecorded": bool(link_grant_audit_id),
            "linkRevokeAuditRecorded": bool(link_revoke_audit_id),
            "grantAuditRecorded": bool(grant_audit_id),
            "revokeAuditRecorded": bool(revoke_audit_id),
        }
    finally:
        cleanup_errors: list[str] = []
        if link_created and not link_revoked:
            try:
                revoke_parent_link(
                    {
                        "parentId": parent_id,
                        "studentId": student_id,
                        "supervisorApprovalId": f"TEST-U9-LIVE-{nonce}-EMERGENCY-REVOKE",
                        "rationale": "Controlled U9 verifier emergency cleanup.",
                    },
                    _verification_admin(),
                    database,
                )
            except Exception as failure:
                cleanup_errors.append(f"parent link revocation cleanup failed: {failure}")
        for reference in safe_refs:
            try:
                reference.delete()
            except Exception as failure:
                cleanup_errors.append(f"safe projection cleanup failed: {failure}")
        for uid in (parent_id, student_id, unrelated_id):
            if uid:
                try:
                    database.collection("users").document(uid).delete()
                except Exception as failure:
                    cleanup_errors.append(f"profile cleanup failed: {failure}")
        for uid in created_uids:
            try:
                auth.delete_user(uid, app=app)
            except Exception as failure:
                cleanup_errors.append(f"Auth cleanup failed: {failure}")
        firebase_admin.delete_app(app)
        if cleanup_errors:
            raise VerificationError("; ".join(cleanup_errors))


def main() -> None:
    parser = argparse.ArgumentParser(description="Controlled U9 parent verification")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--web-api-key", required=True)
    parser.add_argument("--manage-url", required=True)
    parser.add_argument("--revoke-url", required=True)
    parser.add_argument("--context-url", required=True)
    parser.add_argument("--gcloud-bin", default=os.environ.get("GCLOUD_BIN", "gcloud"))
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("Refusing to create temporary accounts without --apply.")
    print(json.dumps(verify(
        api_key=args.web_api_key,
        manage_url=args.manage_url,
        revoke_url=args.revoke_url,
        context_url=args.context_url,
        gcloud_bin=args.gcloud_bin,
    ), sort_keys=True))


if __name__ == "__main__":
    main()
