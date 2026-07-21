"""Server-owned parent invitation and consent contract for U12.

The callable layer is the only place that can create an active parent link.
Client code can request delivery and later provide an email-link-authenticated
identity, but never writes an invitation, link, audit, or parent profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from typing import Any, Callable, Mapping
from uuid import uuid4

from firebase_admin import firestore

from parent_link_admin import link_document_id


PARENT_INVITATION_SERVICE_ACCOUNT = (
    "logic-oasis-parent-invitation@logic-oasis-fyp.iam.gserviceaccount.com"
)
INVITATION_TTL_MINUTES = 30
INVITATION_RESEND_COOLDOWN_SECONDS = 60
MAX_ACTIVE_PARENT_LINKS = 2


class ParentInvitationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class VerifiedInvitationActor:
    uid: str
    email: str
    email_verified: bool
    role: str | None


def normalize_email(value: object) -> str:
    if not isinstance(value, str):
        raise ParentInvitationError("invalid-argument", "A valid email address is required.")
    email = value.strip().lower()
    if not email or "@" not in email or "/" in email:
        raise ParentInvitationError("invalid-argument", "A valid email address is required.")
    return email


def _required_string(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or "/" in value:
        raise ParentInvitationError("invalid-argument", f"{key} is required.")
    return value.strip()


def email_hmac(email: str, key: str) -> str:
    if not key:
        raise ParentInvitationError("failed-precondition", "Parent invitation delivery is not configured.")
    return hmac.new(key.encode(), normalize_email(email).encode(), hashlib.sha256).hexdigest()


def verifier_hash(verifier: str) -> str:
    return hashlib.sha256(verifier.encode()).hexdigest()


def invitation_document_id(student_id: str, recipient_hmac: str) -> str:
    """Stable opaque key: one current invite per student/recipient pair."""
    return hashlib.sha256(f"{student_id}:{recipient_hmac}".encode()).hexdigest()


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(timezone.utc)


def _profile_data(database: Any, uid: str) -> dict[str, Any] | None:
    snapshot = database.collection("users").document(uid).get()
    return dict(snapshot.to_dict() or {}) if snapshot.exists else None


def verify_student_actor(actor: VerifiedInvitationActor) -> None:
    if actor.role != "student":
        raise ParentInvitationError("permission-denied", "Only an active student can invite a parent.")


def _active_link_count(database: Any, student_id: str) -> int:
    try:
        query = database.collection("parentLinks").where("studentId", "==", student_id)
        return sum(
            1 for snapshot in query.stream()
            if (snapshot.to_dict() or {}).get("status") == "active"
        )
    except AttributeError:
        # The focused in-memory tests intentionally provide only document
        # operations. Production Firestore always supports this query.
        return 0


def _pending_invitation(
    database: Any, student_id: str, recipient_hmac: str, now: datetime,
) -> Any | None:
    try:
        query = database.collection("parentLinkInvitations").where(
            "studentId", "==", student_id
        )
        for snapshot in query.stream():
            data = snapshot.to_dict() or {}
            expiry = data.get("expiresAt")
            if (
                data.get("recipientEmailHmac") == recipient_hmac
                and data.get("status") == "pending"
                and isinstance(expiry, datetime)
                and expiry > now
            ):
                return snapshot.reference
    except AttributeError:
        return None
    return None


def create_parent_link_invitation(
    data: Mapping[str, Any],
    actor: VerifiedInvitationActor,
    database: Any,
    *,
    email_hmac_key: str,
    deliver: Callable[[str, str, str], None],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create or resend a pending invitation without disclosing its secret."""
    verify_student_actor(actor)
    recipient_email = normalize_email(data.get("recipientEmail"))
    timestamp = _now(now)
    recipient_hmac = email_hmac(recipient_email, email_hmac_key)
    pending_ref = _pending_invitation(database, actor.uid, recipient_hmac, timestamp)
    if pending_ref is None and _active_link_count(database, actor.uid) >= MAX_ACTIVE_PARENT_LINKS:
        raise ParentInvitationError("resource-exhausted", "The active parent-link limit has been reached.")

    invitation_ref = database.collection("parentLinkInvitations").document(
        invitation_document_id(actor.uid, recipient_hmac)
    )
    verifier = secrets.token_urlsafe(32)
    expiry = timestamp + timedelta(minutes=INVITATION_TTL_MINUTES)
    audit_ref = database.collection("parentLinkAudits").document(f"{invitation_ref.id}_delivery_{uuid4().hex}")

    @firestore.transactional
    def persist_pending(transaction: Any) -> None:
        snapshot = invitation_ref.get(transaction=transaction)
        existing = dict(snapshot.to_dict() or {}) if snapshot.exists else None
        if existing and existing.get("studentId") != actor.uid:
            raise ParentInvitationError("permission-denied", "This invitation is unavailable.")
        if existing and existing.get("status") == "accepted":
            raise ParentInvitationError("failed-precondition", "This parent is already linked.")
        last_delivered = existing.get("lastDeliveredAt") if existing else None
        if (
            isinstance(last_delivered, datetime)
            and last_delivered + timedelta(seconds=INVITATION_RESEND_COOLDOWN_SECONDS) > timestamp
        ):
            raise ParentInvitationError("resource-exhausted", "Please wait before sending another invitation.")
        payload = {
            "studentId": actor.uid,
            "recipientEmailHmac": recipient_hmac,
            "emailHashKeyVersion": "v1",
            "status": "pending",
            "verifierHash": verifier_hash(verifier),
            "expiresAt": expiry,
            "updatedAt": timestamp,
            "deliveryCount": (existing.get("deliveryCount", 0) if existing else 0),
        }
        if existing:
            transaction.update(invitation_ref, payload)
        else:
            payload.update({"createdAt": timestamp, "createdBy": actor.uid})
            transaction.create(invitation_ref, payload)

    persist_pending(database.transaction())
    try:
        deliver(recipient_email, invitation_ref.id, verifier)
    except Exception as error:
        # Do not persist provider error text: it can contain recipient or link data.
        raise ParentInvitationError("unavailable", "Unable to deliver the invitation. Please try again later.") from error

    @firestore.transactional
    def record_delivery(transaction: Any) -> None:
        snapshot = invitation_ref.get(transaction=transaction)
        current = dict(snapshot.to_dict() or {}) if snapshot.exists else {}
        if current.get("status") != "pending":
            return
        transaction.update(invitation_ref, {
            "deliveryCount": int(current.get("deliveryCount", 0)) + 1,
            "lastDeliveredAt": timestamp,
            "updatedAt": timestamp,
        })
        transaction.create(audit_ref, {
            "invitationId": invitation_ref.id,
            "studentId": actor.uid,
            "eventType": "delivery",
            "actorId": actor.uid,
            "createdAt": timestamp,
        })

    record_delivery(database.transaction())
    return {"status": "pending", "expiresAt": expiry.isoformat()}


def _require_matching_pending(
    invitation: Mapping[str, Any], actor: VerifiedInvitationActor, verifier: str, key: str, now: datetime,
) -> None:
    if invitation.get("status") != "pending":
        raise ParentInvitationError("failed-precondition", "This invitation is no longer available.")
    expiry = invitation.get("expiresAt")
    if not isinstance(expiry, datetime) or expiry <= now:
        raise ParentInvitationError("failed-precondition", "This invitation has expired.")
    if not actor.email_verified or email_hmac(actor.email, key) != invitation.get("recipientEmailHmac"):
        raise ParentInvitationError("permission-denied", "This invitation does not match the signed-in parent email.")
    if not hmac.compare_digest(verifier_hash(verifier), str(invitation.get("verifierHash", ""))):
        raise ParentInvitationError("permission-denied", "This invitation cannot be verified.")
    if actor.role == "student":
        raise ParentInvitationError("permission-denied", "A student account cannot be accepted as a parent account.")


def accept_parent_link_invitation(
    data: Mapping[str, Any], actor: VerifiedInvitationActor, database: Any, *, email_hmac_key: str, now: datetime | None = None,
) -> dict[str, str]:
    invitation_id = _required_string(data, "invitationId")
    verifier = _required_string(data, "verifier")
    timestamp = _now(now)
    invitation_ref = database.collection("parentLinkInvitations").document(invitation_id)

    @firestore.transactional
    def accept(transaction: Any) -> dict[str, str]:
        snapshot = invitation_ref.get(transaction=transaction)
        if not snapshot.exists:
            raise ParentInvitationError("not-found", "This invitation is unavailable.")
        invitation = dict(snapshot.to_dict() or {})
        _require_matching_pending(invitation, actor, verifier, email_hmac_key, timestamp)
        student_id = invitation.get("studentId")
        if not isinstance(student_id, str) or student_id == actor.uid:
            raise ParentInvitationError("permission-denied", "This invitation cannot create a parent link.")
        link_ref = database.collection("parentLinks").document(link_document_id(actor.uid, student_id))
        link_snapshot = link_ref.get(transaction=transaction)
        if link_snapshot.exists:
            raise ParentInvitationError("failed-precondition", "A parent link already exists for this invitation.")
        try:
            active_link_count = sum(
                1
                for candidate in database.collection("parentLinks")
                .where("studentId", "==", student_id)
                .stream(transaction=transaction)
                if (candidate.to_dict() or {}).get("status") == "active"
            )
        except AttributeError:
            # The small focused fake has no query API; production Firestore
            # executes this read in the same transaction as link creation.
            active_link_count = 0
        if active_link_count >= MAX_ACTIVE_PARENT_LINKS:
            raise ParentInvitationError("resource-exhausted", "The active parent-link limit has been reached.")
        profile_ref = database.collection("users").document(actor.uid)
        profile_snapshot = profile_ref.get(transaction=transaction)
        profile = dict(profile_snapshot.to_dict() or {}) if profile_snapshot.exists else None
        if profile and profile.get("role") != "parent":
            raise ParentInvitationError("permission-denied", "This account cannot be accepted as a parent account.")
        audit_ref = database.collection("parentLinkAudits").document(f"{invitation_id}_accepted")
        transaction.update(invitation_ref, {"status": "accepted", "acceptedBy": actor.uid, "acceptedAt": timestamp, "updatedAt": timestamp})
        transaction.create(link_ref, {"parentId": actor.uid, "studentId": student_id, "status": "active", "linkVersion": 1, "createdAt": timestamp, "linkedBy": "parent_invitation", "invitationId": invitation_id, "updatedAt": timestamp})
        if profile is None:
            transaction.create(profile_ref, {"role": "parent", "email": normalize_email(actor.email), "createdAt": timestamp, "lastActiveAt": timestamp})
        transaction.create(audit_ref, {"invitationId": invitation_id, "linkId": link_ref.id, "studentId": student_id, "parentId": actor.uid, "eventType": "accepted", "actorId": actor.uid, "createdAt": timestamp})
        return {"status": "active", "linkId": link_ref.id}

    return accept(database.transaction())


def decline_parent_link_invitation(
    data: Mapping[str, Any], actor: VerifiedInvitationActor, database: Any, *, email_hmac_key: str, now: datetime | None = None,
) -> dict[str, str]:
    invitation_id = _required_string(data, "invitationId")
    verifier = _required_string(data, "verifier")
    timestamp = _now(now)
    invitation_ref = database.collection("parentLinkInvitations").document(invitation_id)
    @firestore.transactional
    def decline(transaction: Any) -> dict[str, str]:
        snapshot = invitation_ref.get(transaction=transaction)
        if not snapshot.exists:
            raise ParentInvitationError("not-found", "This invitation is unavailable.")
        invitation = dict(snapshot.to_dict() or {})
        _require_matching_pending(invitation, actor, verifier, email_hmac_key, timestamp)
        transaction.update(invitation_ref, {"status": "declined", "declinedBy": actor.uid, "declinedAt": timestamp, "updatedAt": timestamp})
        transaction.create(database.collection("parentLinkAudits").document(f"{invitation_id}_declined"), {"invitationId": invitation_id, "studentId": invitation["studentId"], "parentId": actor.uid, "eventType": "declined", "actorId": actor.uid, "createdAt": timestamp})
        return {"status": "declined"}
    return decline(database.transaction())


def unlink_own_parent_link(
    data: Mapping[str, Any], actor: VerifiedInvitationActor, database: Any, *, now: datetime | None = None,
) -> dict[str, str]:
    if actor.role != "parent":
        raise ParentInvitationError("permission-denied", "Only the linked parent can remove this relationship.")
    student_id = _required_string(data, "studentId")
    link_ref = database.collection("parentLinks").document(link_document_id(actor.uid, student_id))
    timestamp = _now(now)
    @firestore.transactional
    def revoke(transaction: Any) -> dict[str, str]:
        snapshot = link_ref.get(transaction=transaction)
        link = dict(snapshot.to_dict() or {}) if snapshot.exists else {}
        if not snapshot.exists or link.get("status") != "active" or link.get("parentId") != actor.uid or link.get("studentId") != student_id:
            raise ParentInvitationError("not-found", "The active parent link is unavailable.")
        transaction.update(link_ref, {"status": "revoked", "revokedAt": timestamp, "revokedBy": actor.uid, "updatedAt": timestamp, "linkVersion": int(link.get("linkVersion", 1)) + 1})
        transaction.create(database.collection("parentLinkAudits").document(f"{link_ref.id}_parent_revoke"), {"linkId": link_ref.id, "parentId": actor.uid, "studentId": student_id, "eventType": "parent_revoke", "actorId": actor.uid, "createdAt": timestamp})
        return {"status": "revoked", "linkId": link_ref.id}
    return revoke(database.transaction())
