from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import parent_link_admin as links


class _Ref:
    def __init__(self, identifier: str) -> None:
        self.id = identifier
        self.data: dict | None = None

    def create(self, data: dict) -> None:
        if self.data is not None:
            raise ValueError("already exists")
        self.data = data

    def get(self, transaction=None):
        return SimpleNamespace(
            exists=self.data is not None,
            to_dict=lambda: self.data,
        )

    def update(self, data: dict) -> None:
        if self.data is None:
            raise ValueError("missing")
        self.data.update(data)


class _Collection:
    def __init__(self) -> None:
        self.refs: dict[str, _Ref] = {}

    def document(self, identifier: str) -> _Ref:
        return self.refs.setdefault(identifier, _Ref(identifier))


class _Db:
    def __init__(self) -> None:
        self.collections: dict[str, _Collection] = {}

    def collection(self, name: str) -> _Collection:
        return self.collections.setdefault(name, _Collection())

    def transaction(self):
        return _Transaction()


class _Transaction:
    def create(self, ref: _Ref, data: dict) -> None:
        ref.create(data)

    def update(self, ref: _Ref, data: dict) -> None:
        ref.update(data)


class ParentLinkAdminTests(unittest.TestCase):
    def test_bootstrap_grant_and_revoke_write_immutable_audit_and_revoke_tokens(self) -> None:
        database = _Db()
        user = SimpleNamespace(custom_claims={"other": "kept"})
        calls: list[tuple[str, object]] = []

        from pathlib import Path as _Path
        tools_root = _Path(__file__).resolve().parents[2] / "tools"
        sys.path.insert(0, str(tools_root))
        import bootstrap_parent_link_admin as bootstrap

        bootstrap.apply_claim_change(
            database=database,
            uid="admin_uid",
            action="grant",
            supervisor_approval_id="SUP-01",
            rationale="Supervisor approved pilot access.",
            actor=bootstrap.IDENTITY_ADMIN_SERVICE_ACCOUNT,
            get_user=lambda _: user,
            set_custom_user_claims=lambda uid, claims: calls.append((uid, claims)),
            revoke_refresh_tokens=lambda uid: calls.append(("revoked", uid)),
            now=datetime(2026, 7, 18, tzinfo=timezone.utc),
        )
        self.assertTrue(calls[0][1][links.PARENT_LINK_ADMIN_CLAIM])
        self.assertEqual(len(database.collection("adminRoleAudits").refs), 1)

        bootstrap.apply_claim_change(
            database=database,
            uid="admin_uid",
            action="revoke",
            supervisor_approval_id="SUP-02",
            rationale="Pilot role ended.",
            actor=bootstrap.IDENTITY_ADMIN_SERVICE_ACCOUNT,
            get_user=lambda _: SimpleNamespace(custom_claims={links.PARENT_LINK_ADMIN_CLAIM: True}),
            set_custom_user_claims=lambda uid, claims: calls.append((uid, claims)),
            revoke_refresh_tokens=lambda uid: calls.append(("revoked", uid)),
        )
        self.assertEqual(calls[-1], ("revoked", "admin_uid"))

    def test_admin_verification_rejects_missing_claim_or_revoked_token(self) -> None:
        request = SimpleNamespace(
            auth=SimpleNamespace(uid="admin_uid"),
            raw_request=SimpleNamespace(headers={"Authorization": "Bearer test-token"}),
        )
        with self.assertRaisesRegex(links.ParentLinkAdminError, "permission"):
            links.verify_parent_link_admin(
                request,
                verify_token=lambda *_args, **_kwargs: {"uid": "admin_uid"},
            )
        with self.assertRaisesRegex(links.ParentLinkAdminError, "no longer active"):
            links.verify_parent_link_admin(
                request,
                verify_token=lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("revoked")),
            )

    def test_link_id_is_deterministic(self) -> None:
        self.assertEqual(
            links.link_document_id("parent_uid", "student_uid"),
            "parent_uid_student_uid",
        )

    def test_manage_then_revoke_preserves_link_audit_fields(self) -> None:
        database = _Db()
        admin = links.VerifiedAdmin(uid="admin_uid", claims={links.PARENT_LINK_ADMIN_CLAIM: True})
        get_user = lambda _: SimpleNamespace(uid="present")
        with patch.object(links.firestore, "transactional", lambda function: function):
            created = links.manage_parent_link(
                {
                    "parentId": "parent_uid",
                    "studentId": "student_uid",
                    "supervisorApprovalId": "SUP-LINK-01",
                    "rationale": "Approved temporary link.",
                },
                admin,
                database,
                get_user=get_user,
                now=datetime(2026, 7, 18, tzinfo=timezone.utc),
            )
            revoked = links.revoke_parent_link(
                {
                    "parentId": "parent_uid",
                    "studentId": "student_uid",
                    "supervisorApprovalId": "SUP-LINK-02",
                    "rationale": "Approved temporary unlink.",
                },
                admin,
                database,
                now=datetime(2026, 7, 19, tzinfo=timezone.utc),
            )
        link = database.collection("parentLinks").document(created["linkId"]).data
        self.assertEqual(created["status"], "active")
        self.assertEqual(revoked["status"], "revoked")
        self.assertEqual(link["status"], "revoked")
        self.assertEqual(link["linkedBy"], "admin_uid")
        self.assertEqual(link["revokedBy"], "admin_uid")
        self.assertEqual(link["supervisorApprovalRef"], "SUP-LINK-01")
        self.assertEqual(len(database.collection("parentLinkAudits").refs), 2)

    def test_manage_rejects_an_ambiguous_existing_link_identity(self) -> None:
        database = _Db()
        admin = links.VerifiedAdmin(uid="admin_uid", claims={links.PARENT_LINK_ADMIN_CLAIM: True})
        get_user = lambda _: SimpleNamespace(uid="present")
        payload = {
            "parentId": "a_b",
            "studentId": "c",
            "supervisorApprovalId": "SUP-LINK-03",
            "rationale": "Approved collision test link.",
        }
        with patch.object(links.firestore, "transactional", lambda function: function):
            links.manage_parent_link(payload, admin, database, get_user=get_user)
            with self.assertRaisesRegex(links.ParentLinkAdminError, "identity is invalid"):
                links.manage_parent_link(
                    {
                        "parentId": "a",
                        "studentId": "b_c",
                        "supervisorApprovalId": "SUP-LINK-04",
                        "rationale": "Must not reuse an ambiguous link ID.",
                    },
                    admin,
                    database,
                    get_user=get_user,
                )


if __name__ == "__main__":
    unittest.main()
