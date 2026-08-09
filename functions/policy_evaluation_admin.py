"""AQC-4 protected callable handlers for policy-evaluation study control."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping

from firebase_admin import auth

from policy_evaluation import (
    POLICY_EVALUATION_ADMIN_CLAIM,
    PolicyEvaluationError,
    VerifiedPolicyEvaluationAdmin,
    apply_consent_update,
    apply_study_update,
    create_enrollment,
    revoke_enrollment,
)


def verify_policy_evaluation_admin(
    request: Any,
    *,
    verify_token: Callable[..., Mapping[str, Any]] = auth.verify_id_token,
) -> VerifiedPolicyEvaluationAdmin:
    """Check callable authentication, claim, and revocation state."""
    auth_context = getattr(request, "auth", None)
    uid = getattr(auth_context, "uid", None)
    raw_request = getattr(request, "raw_request", None)
    headers = getattr(raw_request, "headers", {}) if raw_request is not None else {}
    authorization = headers.get("Authorization") if headers else None
    if not isinstance(uid, str) or not uid or not isinstance(authorization, str):
        raise PolicyEvaluationError(
            "unauthenticated", "Sign in with an approved administrator account."
        )
    prefix, _, token = authorization.partition(" ")
    if prefix.lower() != "bearer" or not token:
        raise PolicyEvaluationError(
            "unauthenticated", "A Firebase ID token is required."
        )
    try:
        claims = verify_token(token, check_revoked=True)
    except Exception as error:
        raise PolicyEvaluationError(
            "unauthenticated", "Administrator credentials are no longer active."
        ) from error
    if claims.get("uid") != uid or claims.get(POLICY_EVALUATION_ADMIN_CLAIM) is not True:
        raise PolicyEvaluationError(
            "permission-denied",
            "Policy-evaluation administrator permission is required.",
        )
    return VerifiedPolicyEvaluationAdmin(uid=uid, claims=claims)


def manage_policy_evaluation_study(
    data: Mapping[str, Any],
    admin: VerifiedPolicyEvaluationAdmin,
    database: Any,
    *,
    allocation_key: str | None = None,
    now: datetime | None = None,
) -> dict[str, str]:
    study_version = _required_string(data, "studyVersion")
    return apply_study_update(
        database,
        study_version=study_version,
        data=data,
        admin=admin,
        release_ref=_required_string(data, "releaseRef"),
        rationale=_required_string(data, "rationale"),
        now=now,
    )


def record_policy_evaluation_consent(
    data: Mapping[str, Any],
    admin: VerifiedPolicyEvaluationAdmin,
    database: Any,
    *,
    allocation_key: str | None = None,
    now: datetime | None = None,
) -> dict[str, str]:
    return apply_consent_update(
        database,
        student_id=_required_string(data, "studentId"),
        study_version=_required_string(data, "studyVersion"),
        data=data,
        admin=admin,
        release_ref=_required_string(data, "releaseRef"),
        rationale=_required_string(data, "rationale"),
        now=now,
    )


def manage_policy_evaluation_enrollment(
    data: Mapping[str, Any],
    admin: VerifiedPolicyEvaluationAdmin,
    database: Any,
    *,
    allocation_key: str | None = None,
    now: datetime | None = None,
) -> dict[str, str]:
    if not allocation_key:
        raise PolicyEvaluationError(
            "failed-precondition", "The allocation secret is unavailable."
        )
    action = data.get("action")
    if action == "enroll":
        return create_enrollment(
            database,
            student_id=_required_string(data, "studentId"),
            year_level=_required_int(data, "yearLevel"),
            topic_id=_required_string(data, "topicId"),
            subtopic_id=_required_string(data, "subtopicId"),
            starting_difficulty=_required_string(data, "startingDifficulty"),
            study_version=_required_string(data, "studyVersion"),
            allocation_key=allocation_key,
            admin=admin,
            release_ref=_required_string(data, "releaseRef"),
            rationale=_required_string(data, "rationale"),
            context_version=_optional_string(data, "contextVersion", ""),
            now=now,
        )
    if action == "revoke":
        return revoke_enrollment(
            database,
            student_id=_required_string(data, "studentId"),
            year_level=_required_int(data, "yearLevel"),
            topic_id=_required_string(data, "topicId"),
            subtopic_id=_required_string(data, "subtopicId"),
            study_version=_required_string(data, "studyVersion"),
            admin=admin,
            release_ref=_required_string(data, "releaseRef"),
            rationale=_required_string(data, "rationale"),
            now=now,
        )
    raise PolicyEvaluationError(
        "invalid-argument", "Enrollment action must be enroll or revoke."
    )


def _required_string(data: Mapping[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PolicyEvaluationError("invalid-argument", f"{field} is required.")
    return value.strip()


def _optional_string(data: Mapping[str, Any], field: str, default: str) -> str:
    value = data.get(field)
    if value is None:
        return default
    return _required_string(data, field)


def _required_int(data: Mapping[str, Any], field: str) -> int:
    value = data.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PolicyEvaluationError(
            "invalid-argument", f"{field} must be a positive integer."
        )
    return value

