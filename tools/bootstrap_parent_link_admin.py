"""Protected grant/revoke procedure for the U9 parentLinkAdmin claim.

Run this only with Application Default Credentials for
logic-oasis-identity-admin@logic-oasis-fyp.iam.gserviceaccount.com after a
supervisor-approved request. It writes an immutable audit record before the
claim mutation, and revocation invalidates existing refresh tokens.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

import firebase_admin
from firebase_admin import auth, firestore

IDENTITY_ADMIN_SERVICE_ACCOUNT = "logic-oasis-identity-admin@logic-oasis-fyp.iam.gserviceaccount.com"
PARENT_LINK_ADMIN_CLAIM = "parentLinkAdmin"


def audit_id(*, uid: str, action: str, approval_id: str) -> str:
    digest = sha256(f"{uid}:{action}:{approval_id}".encode("utf-8")).hexdigest()[:20]
    return f"parent_link_admin_{digest}"


def apply_claim_change(
    *,
    database: Any,
    uid: str,
    action: str,
    supervisor_approval_id: str,
    rationale: str,
    actor: str,
    get_user: Any = auth.get_user,
    set_custom_user_claims: Any = auth.set_custom_user_claims,
    revoke_refresh_tokens: Any = auth.revoke_refresh_tokens,
    now: datetime | None = None,
) -> str:
    if action not in {"grant", "revoke"}:
        raise ValueError("action must be grant or revoke")
    if not uid or not supervisor_approval_id or not rationale.strip():
        raise ValueError("uid, supervisor approval ID, and rationale are required")
    user = get_user(uid)
    audit_ref = database.collection("adminRoleAudits").document(
        audit_id(uid=uid, action=action, approval_id=supervisor_approval_id)
    )
    timestamp = now or datetime.now(timezone.utc)
    audit = {
        "auditType": "parent_link_admin_claim",
        "subjectUid": uid,
        "action": action,
        "supervisorApprovalId": supervisor_approval_id,
        "rationale": rationale.strip(),
        "actorServiceAccount": actor,
        "identityAdminServiceAccount": IDENTITY_ADMIN_SERVICE_ACCOUNT,
        "createdAt": timestamp,
    }
    # Create first: an accidental duplicate cannot silently change claims.
    audit_ref.create(audit)
    claims = dict(getattr(user, "custom_claims", None) or {})
    if action == "grant":
        claims[PARENT_LINK_ADMIN_CLAIM] = True
    else:
        claims.pop(PARENT_LINK_ADMIN_CLAIM, None)
    set_custom_user_claims(uid, claims)
    if action == "revoke":
        revoke_refresh_tokens(uid)
    return audit_ref.id


def main() -> None:
    parser = argparse.ArgumentParser(description="Audited U9 parent-link administrator claim procedure")
    parser.add_argument("--project", required=True)
    parser.add_argument("--uid", required=True)
    parser.add_argument("--action", choices=("grant", "revoke"), required=True)
    parser.add_argument("--supervisor-approval-id", required=True)
    parser.add_argument("--rationale", required=True)
    parser.add_argument("--actor-service-account", required=True)
    args = parser.parse_args()
    if args.actor_service_account != IDENTITY_ADMIN_SERVICE_ACCOUNT:
        raise SystemExit("This procedure must run as the declared identity-admin service account.")
    app = firebase_admin.initialize_app(options={"projectId": args.project})
    database = firestore.client(app)
    created = apply_claim_change(
        database=database,
        uid=args.uid,
        action=args.action,
        supervisor_approval_id=args.supervisor_approval_id,
        rationale=args.rationale,
        actor=args.actor_service_account,
    )
    print(f"Recorded immutable admin role audit: {created}")


if __name__ == "__main__":
    main()
