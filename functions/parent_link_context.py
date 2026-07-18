"""Safe, authenticated parent-child dashboard context for U9."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from firebase_admin import auth


class ParentLinkContextError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class VerifiedParent:
    uid: str


def verify_authenticated_parent(
    request: Any,
    *,
    verify_token: Callable[..., Mapping[str, Any]] = auth.verify_id_token,
) -> VerifiedParent:
    """Require a non-revoked Firebase token, without granting admin powers."""
    auth_context = getattr(request, "auth", None)
    uid = getattr(auth_context, "uid", None)
    raw_request = getattr(request, "raw_request", None)
    headers = getattr(raw_request, "headers", {}) if raw_request is not None else {}
    authorization = headers.get("Authorization") if headers else None
    if not isinstance(uid, str) or not uid or not isinstance(authorization, str):
        raise ParentLinkContextError("unauthenticated", "Sign in to view linked learner updates.")
    prefix, _, token = authorization.partition(" ")
    if prefix.lower() != "bearer" or not token:
        raise ParentLinkContextError("unauthenticated", "A Firebase ID token is required.")
    try:
        claims = verify_token(token, check_revoked=True)
    except Exception as error:
        raise ParentLinkContextError("unauthenticated", "Parent credentials are no longer active.") from error
    if claims.get("uid") != uid:
        raise ParentLinkContextError("unauthenticated", "Parent credentials do not match this session.")
    return VerifiedParent(uid=uid)


def _safe_display_name(profile: Mapping[str, Any]) -> str:
    value = profile.get("displayName")
    return value.strip() if isinstance(value, str) and value.strip() else "Linked learner"


def _safe_year_level(profile: Mapping[str, Any]) -> int:
    value = profile.get("yearLevel")
    if isinstance(value, int) and 4 <= value <= 6:
        return value
    return 4


def list_active_linked_children(
    _data: Mapping[str, Any],
    parent: VerifiedParent,
    database: Any,
) -> dict[str, list[dict[str, Any]]]:
    """Return only the bounded display context for this parent's active links."""
    links = (
        database.collection("parentLinks")
        .where("parentId", "==", parent.uid)
        .stream()
    )
    children: list[dict[str, Any]] = []
    for snapshot in links:
        link = dict(snapshot.to_dict() or {})
        student_id = link.get("studentId")
        if link.get("status") != "active" or not isinstance(student_id, str) or not student_id:
            continue
        profile_snapshot = database.collection("users").document(student_id).get()
        profile = dict(profile_snapshot.to_dict() or {}) if profile_snapshot.exists else {}
        children.append(
            {
                "studentId": student_id,
                "displayName": _safe_display_name(profile),
                "yearLevel": _safe_year_level(profile),
            }
        )
    children.sort(key=lambda child: (child["displayName"].lower(), child["studentId"]))
    return {"children": children}
