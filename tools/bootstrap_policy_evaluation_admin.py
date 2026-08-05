"""Protected grant/revoke procedure for the AQC-4 policyEvaluationAdmin claim.

Run this only with Application Default Credentials for the declared identity
administrator after a developer release decision.  It writes an immutable
audit record before the claim mutation, and revocation invalidates existing
refresh tokens.  It never reuses the parent-link administration claim.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

import firebase_admin
from firebase_admin import auth, firestore


IDENTITY_ADMIN_SERVICE_ACCOUNT = (
    "logic-oasis-identity-admin@logic-oasis-fyp.iam.gserviceaccount.com"
)
POLICY_EVALUATION_ADMIN_CLAIM = "policyEvaluationAdmin"


def audit_id(*, uid: str, action: str, release_id: str) -> str:
    digest = sha256(f"{uid}:{action}:{release_id}".encode("utf-8")).hexdigest()[:20]
    return f"policy_evaluation_admin_{digest}"


def apply_claim_change(
    *,
    database: Any,
    uid: str,
    action: str,
    release_id: str,
    rationale: str,
    actor: str,
    get_user: Any = auth.get_user,
    set_custom_user_claims: Any = auth.set_custom_user_claims,
    revoke_refresh_tokens: Any = auth.revoke_refresh_tokens,
    now: datetime | None = None,
) -> str:
    if action not in {"grant", "revoke"}:
        raise ValueError("action must be grant or revoke")
    if not uid or not release_id or not rationale.strip():
        raise ValueError("uid, developer release ID, and rationale are required")
    user = get_user(uid)
    audit_ref = database.collection("adminRoleAudits").document(
        audit_id(uid=uid, action=action, release_id=release_id)
    )
    timestamp = now or datetime.now(timezone.utc)
    audit = {
        "auditType": "policy_evaluation_admin_claim",
        "subjectUid": uid,
        "action": action,
        "releaseRef": release_id,
        "rationale": rationale.strip(),
        "actorServiceAccount": actor,
        "identityAdminServiceAccount": IDENTITY_ADMIN_SERVICE_ACCOUNT,
        "createdAt": timestamp,
    }
    # Create first: an accidental duplicate cannot silently change claims.
    audit_ref.create(audit)
    claims = dict(getattr(user, "custom_claims", None) or {})
    if action == "grant":
        claims[POLICY_EVALUATION_ADMIN_CLAIM] = True
    else:
        claims.pop(POLICY_EVALUATION_ADMIN_CLAIM, None)
    set_custom_user_claims(uid, claims)
    if action == "revoke":
        revoke_refresh_tokens(uid)
    return audit_ref.id


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audited AQC-4 policyEvaluationAdmin claim procedure"
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--uid", required=True)
    parser.add_argument("--action", choices=("grant", "revoke"), required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--rationale", required=True)
    parser.add_argument("--actor-service-account", required=True)
    args = parser.parse_args()
    firebase_admin.initialize_app()
    audit_id = apply_claim_change(
        database=firestore.client(),
        uid=args.uid,
        action=args.action,
        release_id=args.release_id,
        rationale=args.rationale,
        actor=args.actor_service_account,
    )
    print(f"auditId={audit_id}")


if __name__ == "__main__":
    main()

