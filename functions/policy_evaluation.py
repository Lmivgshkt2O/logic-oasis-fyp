"""AQC-4 server-owned study, consent, and enrollment contract.

The control plane owns the policy-evaluation study lifecycle.  Enrollment is a
blocked-randomised, lowest-count allocation whose tie-break uses a dedicated
HMAC key that is never exposed to clients, reports, or logs.  Every mutation
also writes an append-only administrator audit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import hmac
from typing import Any, Mapping

from firebase_admin import firestore


POLICY_EVALUATION_ADMIN_SERVICE_ACCOUNT = (
    "logic-oasis-policy-evaluation-admin@logic-oasis-fyp.iam.gserviceaccount.com"
)
POLICY_EVALUATION_ADMIN_CLAIM = "policyEvaluationAdmin"
DEFAULT_POLICY_ARMS = ("P1", "P2", "P3a")

STUDY_STATUSES = ("draft", "enrolling", "active", "closed", "archived")
CONSENT_STATUSES = ("active", "revoked", "expired")
ENROLLMENT_STATUSES = ("active", "revoked")
ALLOWED_DIFFICULTIES = ("Easy", "Moderate", "Hard")
ALLOWED_ARMS = frozenset({"P1", "P2", "P3a", "P3b"})


class PolicyEvaluationError(ValueError):
    """A safe, client-safe failure with a canonical reason code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class VerifiedPolicyEvaluationAdmin:
    uid: str
    claims: Mapping[str, Any]


def study_document_id(study_version: str) -> str:
    return study_version


def consent_document_id(student_id: str, study_version: str) -> str:
    return f"{student_id}_{study_version}"


def enrollment_document_id(
    student_id: str,
    year_level: int,
    topic_id: str,
    subtopic_id: str,
    study_version: str,
) -> str:
    return f"{student_id}_y{year_level}_{topic_id}_{subtopic_id}_{study_version}"


def allocation_block_document_id(
    study_version: str,
    year_level: int,
    topic_id: str,
    subtopic_id: str,
    starting_difficulty: str,
) -> str:
    return (
        f"{study_version}_{year_level}_{topic_id}_{subtopic_id}_"
        f"{starting_difficulty}"
    )


def admin_audit_document_id(*, subject: str, action: str, release_ref: str) -> str:
    digest = sha256(f"{subject}:{action}:{release_ref}".encode("utf-8")).hexdigest()[:20]
    return f"policy_evaluation_{digest}"


def allocate_arm(
    counts: Mapping[str, int],
    payload: str,
    allocation_key: str,
    arms: tuple[str, ...] = DEFAULT_POLICY_ARMS,
) -> str:
    """Select the lowest-count arm, breaking ties with a dedicated HMAC key."""
    if not allocation_key:
        raise PolicyEvaluationError(
            "failed-precondition", "The allocation secret is unavailable."
        )
    if not payload:
        raise PolicyEvaluationError("invalid-argument", "Allocation payload is required.")
    unknown = sorted(set(arms) - ALLOWED_ARMS)
    if unknown:
        raise PolicyEvaluationError("invalid-argument", f"Unknown policy arm: {unknown[0]}")
    minimum = min((counts.get(arm, 0) for arm in arms), default=0)
    candidates = [arm for arm in arms if counts.get(arm, 0) == minimum]
    if len(candidates) == 1:
        return candidates[0]
    return min(
        candidates,
        key=lambda arm: (_hmac_rank(allocation_key, f"{arm}:{payload}"), arm),
    )


def apply_study_update(
    database: Any,
    *,
    study_version: str,
    data: Mapping[str, Any],
    admin: VerifiedPolicyEvaluationAdmin,
    release_ref: str,
    rationale: str,
    now: datetime | None = None,
) -> dict[str, str]:
    """Create or update a study under the developer release convention."""
    if not study_version or not release_ref.strip() or not rationale.strip():
        raise PolicyEvaluationError(
            "invalid-argument", "Study version, release reference, and rationale are required."
        )
    status = _required_string(data, "status")
    if status not in STUDY_STATUSES:
        raise PolicyEvaluationError("invalid-argument", f"Unknown study status: {status}")
    timestamp = now or datetime.now(timezone.utc)
    study_ref = database.collection("policyEvaluationStudies").document(
        study_document_id(study_version)
    )
    audit_ref = database.collection("policyEvaluationAdminAudits").document(
        admin_audit_document_id(
            subject=study_version, action=f"study_{status}", release_ref=release_ref
        )
    )

    @firestore.transactional
    def update_study(transaction: Any) -> dict[str, str]:
        snapshot = study_ref.get(transaction=transaction)
        existing = dict(snapshot.to_dict() or {}) if snapshot.exists else None
        if existing is None:
            if status != "draft":
                raise PolicyEvaluationError(
                    "failed-precondition", "A study must be created in draft."
                )
            document = _frozen_study_fields(data)
            document.update(
                {
                    "studyVersion": study_version,
                    "status": status,
                    "releaseRef": release_ref,
                    "releaseRationale": rationale.strip(),
                    "updatedBy": admin.uid,
                    "createdAt": timestamp,
                    "updatedAt": timestamp,
                }
            )
            transaction.create(study_ref, document)
            transaction.create(
                audit_ref,
                _audit_document(
                    admin=admin,
                    action=f"study_create_{status}",
                    subject=study_version,
                    release_ref=release_ref,
                    rationale=rationale,
                    timestamp=timestamp,
                ),
            )
            return {"studyVersion": study_version, "status": status}

        previous_status = existing.get("status")
        if previous_status not in STUDY_STATUSES:
            raise PolicyEvaluationError(
                "failed-precondition", "Stored study status is invalid."
            )
        if not _valid_study_transition(previous_status, status):
            raise PolicyEvaluationError(
                "failed-precondition",
                f"Study cannot move from {previous_status} to {status}.",
            )
        if previous_status == "active" and status not in {"closed", "archived"}:
            raise PolicyEvaluationError(
                "failed-precondition", "An active study is frozen except for closure."
            )
        updates: dict[str, Any] = {"status": status, "updatedBy": admin.uid, "updatedAt": timestamp}
        if status == "active":
            updates.update(_frozen_study_fields(data))
            updates["activatedAt"] = timestamp
        transaction.update(study_ref, updates)
        transaction.create(
            audit_ref,
            _audit_document(
                admin=admin,
                action=f"study_update_{status}",
                subject=study_version,
                release_ref=release_ref,
                rationale=rationale,
                timestamp=timestamp,
            ),
        )
        return {"studyVersion": study_version, "status": status}

    return update_study(database.transaction())


def apply_consent_update(
    database: Any,
    *,
    student_id: str,
    study_version: str,
    data: Mapping[str, Any],
    admin: VerifiedPolicyEvaluationAdmin,
    release_ref: str,
    rationale: str,
    now: datetime | None = None,
) -> dict[str, str]:
    """Record only documented active/revoked/expired consent states."""
    if not student_id or not study_version:
        raise PolicyEvaluationError("invalid-argument", "Student and study are required.")
    status = _required_string(data, "status")
    if status not in CONSENT_STATUSES:
        raise PolicyEvaluationError("invalid-argument", f"Unknown consent status: {status}")
    consent_record_ref = _required_string(data, "consentRecordRef")
    expires_at = _required_datetime(data, "expiresAt")
    timestamp = now or datetime.now(timezone.utc)
    consent_ref = database.collection("policyEvaluationConsents").document(
        consent_document_id(student_id, study_version)
    )
    audit_ref = database.collection("policyEvaluationAdminAudits").document(
        admin_audit_document_id(
            subject=consent_ref.id, action=f"consent_{status}", release_ref=release_ref
        )
    )

    @firestore.transactional
    def update_consent(transaction: Any) -> dict[str, str]:
        snapshot = consent_ref.get(transaction=transaction)
        existing = dict(snapshot.to_dict() or {}) if snapshot.exists else None
        if existing is not None:
            previous = existing.get("status")
            if previous == status:
                return {"consentId": consent_ref.id, "status": status}
            if previous == "active" and status in {"revoked", "expired"}:
                transaction.update(
                    consent_ref,
                    {
                        "status": status,
                        "updatedBy": admin.uid,
                        "updatedAt": timestamp,
                    },
                )
                transaction.create(
                    audit_ref,
                    _audit_document(
                        admin=admin,
                        action=f"consent_{status}",
                        subject=consent_ref.id,
                        release_ref=release_ref,
                        rationale=rationale,
                        timestamp=timestamp,
                    ),
                )
                return {"consentId": consent_ref.id, "status": status}
            raise PolicyEvaluationError(
                "failed-precondition",
                f"Consent cannot move from {previous} to {status}.",
            )
        transaction.create(
            consent_ref,
            {
                "studentId": student_id,
                "studyVersion": study_version,
                "status": status,
                "consentRecordRef": consent_record_ref,
                "expiresAt": expires_at,
                "recordedBy": admin.uid,
                "releaseRef": release_ref,
                "updatedBy": admin.uid,
                "createdAt": timestamp,
                "updatedAt": timestamp,
            },
        )
        transaction.create(
            audit_ref,
            _audit_document(
                admin=admin,
                action=f"consent_{status}",
                subject=consent_ref.id,
                release_ref=release_ref,
                rationale=rationale,
                timestamp=timestamp,
            ),
        )
        return {"consentId": consent_ref.id, "status": status}

    return update_consent(database.transaction())


def create_enrollment(
    database: Any,
    *,
    student_id: str,
    year_level: int,
    topic_id: str,
    subtopic_id: str,
    starting_difficulty: str,
    study_version: str,
    allocation_key: str,
    admin: VerifiedPolicyEvaluationAdmin,
    release_ref: str,
    rationale: str,
    context_version: str = "",
    now: datetime | None = None,
    arms: tuple[str, ...] = DEFAULT_POLICY_ARMS,
) -> dict[str, str]:
    """Allocate one stable arm for a learner/context sequence, idempotently."""
    if starting_difficulty not in ALLOWED_DIFFICULTIES:
        raise PolicyEvaluationError(
            "invalid-argument", f"Unknown starting difficulty: {starting_difficulty}"
        )
    if year_level < 1 or not topic_id or not subtopic_id:
        raise PolicyEvaluationError(
            "invalid-argument", "Year level, topic, and subtopic are required."
        )
    if not allocation_key:
        raise PolicyEvaluationError(
            "failed-precondition", "The allocation secret is unavailable."
        )
    timestamp = now or datetime.now(timezone.utc)
    enrollment_ref = database.collection("policyEvaluationEnrollments").document(
        enrollment_document_id(
            student_id, year_level, topic_id, subtopic_id, study_version
        )
    )
    study_ref = database.collection("policyEvaluationStudies").document(
        study_document_id(study_version)
    )
    consent_ref = database.collection("policyEvaluationConsents").document(
        consent_document_id(student_id, study_version)
    )
    block_ref = database.collection("policyEvaluationAllocationBlocks").document(
        allocation_block_document_id(
            study_version, year_level, topic_id, subtopic_id, starting_difficulty
        )
    )
    audit_ref = database.collection("policyEvaluationAdminAudits").document(
        admin_audit_document_id(
            subject=enrollment_ref.id, action="enroll", release_ref=release_ref
        )
    )

    @firestore.transactional
    def enroll(transaction: Any) -> dict[str, str]:
        existing_snapshot = enrollment_ref.get(transaction=transaction)
        if existing_snapshot.exists:
            existing = dict(existing_snapshot.to_dict() or {})
            return {
                "enrollmentId": enrollment_ref.id,
                "status": str(existing.get("status")),
                "assignedArm": str(existing.get("assignedArm")),
            }

        study_snapshot = study_ref.get(transaction=transaction)
        if not study_snapshot.exists:
            raise PolicyEvaluationError("not-found", "The study does not exist.")
        study = dict(study_snapshot.to_dict() or {})
        if study.get("status") not in {"enrolling", "active"}:
            raise PolicyEvaluationError(
                "failed-precondition", "The study is not open for enrollment."
            )
        consent_snapshot = consent_ref.get(transaction=transaction)
        if not consent_snapshot.exists:
            raise PolicyEvaluationError(
                "failed-precondition", "Recorded consent is required before enrollment."
            )
        consent = dict(consent_snapshot.to_dict() or {})
        if consent.get("status") != "active":
            raise PolicyEvaluationError(
                "failed-precondition", "Consent is not active."
            )
        expires_at = consent.get("expiresAt")
        if expires_at is not None and expires_at <= timestamp:
            raise PolicyEvaluationError(
                "failed-precondition", "Consent has expired."
            )

        block_snapshot = block_ref.get(transaction=transaction)
        counts = dict(block_snapshot.to_dict() or {}) if block_snapshot.exists else {}
        counts = {
            key: int(value)
            for key, value in counts.items()
            if key in arms and isinstance(value, int) and not isinstance(value, bool)
        }
        payload = (
            f"{study_version}:{student_id}:{year_level}:{topic_id}:"
            f"{subtopic_id}:{starting_difficulty}"
        )
        arm = allocate_arm(counts, payload, allocation_key, arms=arms)
        next_counts = {**counts, arm: counts.get(arm, 0) + 1}
        transaction.set(
            block_ref,
            {
                "studyVersion": study_version,
                "yearLevel": year_level,
                "topicId": topic_id,
                "subtopicId": subtopic_id,
                "startingDifficulty": starting_difficulty,
                **next_counts,
                "updatedAt": timestamp,
            },
        )
        transaction.set(
            enrollment_ref,
            {
                "enrollmentId": enrollment_ref.id,
                "studentId": student_id,
                "yearLevel": year_level,
                "topicId": topic_id,
                "subtopicId": subtopic_id,
                "startingDifficulty": starting_difficulty,
                "contextVersion": context_version,
                "studyVersion": study_version,
                "assignedArm": arm,
                "allocationBlockId": block_ref.id,
                "allocationVersion": "blocked-random-v1",
                "consentRef": consent_ref.id,
                "releaseRef": release_ref,
                "status": "active",
                "assignedAt": timestamp,
                "assignedBy": admin.uid,
            },
        )
        transaction.create(
            audit_ref,
            _audit_document(
                admin=admin,
                action="enroll",
                subject=enrollment_ref.id,
                release_ref=release_ref,
                rationale=rationale,
                timestamp=timestamp,
            ),
        )
        return {
            "enrollmentId": enrollment_ref.id,
            "status": "active",
            "assignedArm": arm,
        }

    return enroll(database.transaction())


def revoke_enrollment(
    database: Any,
    *,
    student_id: str,
    year_level: int,
    topic_id: str,
    subtopic_id: str,
    study_version: str,
    admin: VerifiedPolicyEvaluationAdmin,
    release_ref: str,
    rationale: str,
    now: datetime | None = None,
) -> dict[str, str]:
    """Stop future experimental decisions without rewriting historical evidence."""
    timestamp = now or datetime.now(timezone.utc)
    enrollment_ref = database.collection("policyEvaluationEnrollments").document(
        enrollment_document_id(
            student_id, year_level, topic_id, subtopic_id, study_version
        )
    )
    audit_ref = database.collection("policyEvaluationAdminAudits").document(
        admin_audit_document_id(
            subject=enrollment_ref.id, action="revoke", release_ref=release_ref
        )
    )

    @firestore.transactional
    def revoke(transaction: Any) -> dict[str, str]:
        snapshot = enrollment_ref.get(transaction=transaction)
        if not snapshot.exists:
            raise PolicyEvaluationError("not-found", "The enrollment does not exist.")
        existing = dict(snapshot.to_dict() or {})
        if existing.get("status") != "revoked":
            transaction.update(
                enrollment_ref,
                {
                    "status": "revoked",
                    "revokedAt": timestamp,
                    "revokedBy": admin.uid,
                    "updatedAt": timestamp,
                },
            )
            transaction.create(
                audit_ref,
                _audit_document(
                    admin=admin,
                    action="revoke",
                    subject=enrollment_ref.id,
                    release_ref=release_ref,
                    rationale=rationale,
                    timestamp=timestamp,
                ),
            )
        return {"enrollmentId": enrollment_ref.id, "status": "revoked"}

    return revoke(database.transaction())


def active_enrollment_for(
    database: Any,
    *,
    student_id: str,
    year_level: int,
    topic_id: str,
    subtopic_id: str,
    study_version: str,
) -> dict[str, Any] | None:
    """Read-only immutable enrollment lookup for the quiz-start boundary."""
    snapshot = database.collection("policyEvaluationEnrollments").document(
        enrollment_document_id(
            student_id, year_level, topic_id, subtopic_id, study_version
        )
    ).get()
    if not snapshot.exists:
        return None
    document = dict(snapshot.to_dict() or {})
    if document.get("status") != "active":
        return None
    return document


def _valid_study_transition(previous: str, next_status: str) -> bool:
    transitions = {
        "draft": {"draft", "enrolling"},
        "enrolling": {"enrolling", "active"},
        "active": {"closed"},
        "closed": {"archived"},
        "archived": set(),
    }
    return next_status in transitions.get(previous, set())


def _frozen_study_fields(data: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "manifestHash",
        "policyVersions",
        "outcomeProtocolVersion",
        "deltaFD",
        "randomizationVersion",
    )
    for field in required:
        if not data.get(field):
            raise PolicyEvaluationError(
                "invalid-argument", f"{field} is required to freeze the study manifest."
            )
    return {
        "manifestHash": _required_string(data, "manifestHash"),
        "policyVersions": data["policyVersions"],
        "outcomeProtocolVersion": _required_string(data, "outcomeProtocolVersion"),
        "deltaFD": data["deltaFD"],
        "randomizationVersion": _required_string(data, "randomizationVersion"),
    }


def _audit_document(
    *,
    admin: VerifiedPolicyEvaluationAdmin,
    action: str,
    subject: str,
    release_ref: str,
    rationale: str,
    timestamp: datetime,
) -> dict[str, Any]:
    return {
        "actorUid": admin.uid,
        "action": action,
        "subjectRef": subject,
        "releaseRef": release_ref,
        "rationale": rationale.strip(),
        "createdAt": timestamp,
    }


def _required_string(data: Mapping[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PolicyEvaluationError("invalid-argument", f"{field} is required.")
    return value.strip()


def _required_datetime(data: Mapping[str, Any], field: str) -> datetime:
    value = data.get(field)
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise PolicyEvaluationError("invalid-argument", f"{field} must be a timezone-aware date.")
    return value


def _hmac_rank(allocation_key: str, payload: str) -> int:
    digest = hmac.new(
        allocation_key.encode("utf-8"),
        payload.encode("utf-8"),
        sha256,
    ).hexdigest()
    return int(digest[:8], 16)
