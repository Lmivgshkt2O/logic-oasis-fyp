"""U9's auditable, server-owned parent-link administration contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from firebase_admin import auth, firestore


PARENT_LINK_ADMIN_SERVICE_ACCOUNT = (
    "logic-oasis-parent-link-admin@logic-oasis-fyp.iam.gserviceaccount.com"
)
IDENTITY_ADMIN_SERVICE_ACCOUNT = (
    "logic-oasis-identity-admin@logic-oasis-fyp.iam.gserviceaccount.com"
)
PARENT_LINK_ADMIN_CLAIM = "parentLinkAdmin"


class ParentLinkAdminError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class VerifiedAdmin:
    uid: str
    claims: Mapping[str, Any]


def link_document_id(parent_id: str, student_id: str) -> str:
    return f"{parent_id}_{student_id}"


def _required_uid(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or "/" in value:
        raise ParentLinkAdminError("invalid-argument", f"{key} is required.")
    return value.strip()


def verify_parent_link_admin(
    request: Any,
    *,
    verify_token: Callable[..., Mapping[str, Any]] = auth.verify_id_token,
) -> VerifiedAdmin:
    """Check both callable authentication and Firebase revocation state."""
    auth_context = getattr(request, "auth", None)
    uid = getattr(auth_context, "uid", None)
    raw_request = getattr(request, "raw_request", None)
    headers = getattr(raw_request, "headers", {}) if raw_request is not None else {}
    authorization = headers.get("Authorization") if headers else None
    if not isinstance(uid, str) or not uid or not isinstance(authorization, str):
        raise ParentLinkAdminError("unauthenticated", "Sign in with an approved administrator account.")
    prefix, _, token = authorization.partition(" ")
    if prefix.lower() != "bearer" or not token:
        raise ParentLinkAdminError("unauthenticated", "A Firebase ID token is required.")
    try:
        claims = verify_token(token, check_revoked=True)
    except Exception as error:
        raise ParentLinkAdminError("unauthenticated", "Administrator credentials are no longer active.") from error
    if claims.get("uid") != uid or claims.get(PARENT_LINK_ADMIN_CLAIM) is not True:
        raise ParentLinkAdminError("permission-denied", "Parent-link administrator permission is required.")
    return VerifiedAdmin(uid=uid, claims=claims)


def _verify_user(uid: str, *, get_user: Callable[[str], Any] = auth.get_user) -> None:
    try:
        get_user(uid)
    except Exception as error:
        raise ParentLinkAdminError("not-found", "The requested account does not exist.") from error


def manage_parent_link(
    data: Mapping[str, Any],
    admin: VerifiedAdmin,
    database: Any,
    *,
    get_user: Callable[[str], Any] = auth.get_user,
    now: datetime | None = None,
) -> dict[str, str]:
    parent_id = _required_uid(data, "parentId")
    student_id = _required_uid(data, "studentId")
    if parent_id == student_id:
        raise ParentLinkAdminError("invalid-argument", "Parent and student accounts must be different.")
    _verify_user(parent_id, get_user=get_user)
    _verify_user(student_id, get_user=get_user)
    link_ref = database.collection("parentLinks").document(link_document_id(parent_id, student_id))
    timestamp = now or datetime.now(timezone.utc)

    @firestore.transactional
    def create_link(transaction: Any) -> dict[str, str]:
        snapshot = link_ref.get(transaction=transaction)
        existing = dict(snapshot.to_dict() or {}) if snapshot.exists else None
        if existing and existing.get("status") == "active":
            return {"linkId": link_ref.id, "status": "active"}
        if existing:
            # A revocation is retained for audit and deliberately cannot be
            # silently turned back into access by a client retry.
            raise ParentLinkAdminError(
                "failed-precondition",
                "A revoked link requires a new supervisor-approved administration request.",
            )
        transaction.create(
            link_ref,
            {
                "parentId": parent_id,
                "studentId": student_id,
                "status": "active",
                "linkVersion": 1,
                "createdAt": timestamp,
                "linkedBy": admin.uid,
                "updatedAt": timestamp,
            },
        )
        return {"linkId": link_ref.id, "status": "active"}

    return create_link(database.transaction())


def revoke_parent_link(
    data: Mapping[str, Any],
    admin: VerifiedAdmin,
    database: Any,
    *,
    now: datetime | None = None,
) -> dict[str, str]:
    parent_id = _required_uid(data, "parentId")
    student_id = _required_uid(data, "studentId")
    link_ref = database.collection("parentLinks").document(link_document_id(parent_id, student_id))
    timestamp = now or datetime.now(timezone.utc)

    @firestore.transactional
    def revoke_link(transaction: Any) -> dict[str, str]:
        snapshot = link_ref.get(transaction=transaction)
        if not snapshot.exists:
            raise ParentLinkAdminError("not-found", "The parent link does not exist.")
        existing = dict(snapshot.to_dict() or {})
        if existing.get("parentId") != parent_id or existing.get("studentId") != student_id:
            raise ParentLinkAdminError("failed-precondition", "Parent link identity is invalid.")
        if existing.get("status") != "revoked":
            version = existing.get("linkVersion")
            next_version = version + 1 if isinstance(version, int) and version >= 1 else 2
            transaction.update(
                link_ref,
                {
                    "status": "revoked",
                    "linkVersion": next_version,
                    "revokedAt": timestamp,
                    "revokedBy": admin.uid,
                    "updatedAt": timestamp,
                },
            )
        return {"linkId": link_ref.id, "status": "revoked"}

    return revoke_link(database.transaction())
