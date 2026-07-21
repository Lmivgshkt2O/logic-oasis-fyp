from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import parent_link_invitation as invitations


class _Ref:
    def __init__(self, identifier: str) -> None:
        self.id = identifier
        self.data: dict | None = None

    def get(self, transaction=None):
        return SimpleNamespace(exists=self.data is not None, to_dict=lambda: self.data)

    def create(self, data: dict) -> None:
        if self.data is not None:
            raise ValueError("already exists")
        self.data = dict(data)

    def update(self, data: dict) -> None:
        if self.data is None:
            raise ValueError("missing")
        self.data.update(data)


class _Collection:
    def __init__(self) -> None:
        self.refs: dict[str, _Ref] = {}

    def document(self, identifier: str | None = None) -> _Ref:
        identifier = identifier or f"generated_{len(self.refs)}"
        return self.refs.setdefault(identifier, _Ref(identifier))


class _Transaction:
    def create(self, ref: _Ref, data: dict) -> None:
        ref.create(data)

    def update(self, ref: _Ref, data: dict) -> None:
        ref.update(data)


class _Database:
    def __init__(self) -> None:
        self.collections: dict[str, _Collection] = {}

    def collection(self, name: str) -> _Collection:
        return self.collections.setdefault(name, _Collection())

    def transaction(self) -> _Transaction:
        return _Transaction()


class ParentLinkInvitationTests(unittest.TestCase):
    key = "test-parent-email-hmac-key"
    now = datetime(2026, 7, 21, tzinfo=timezone.utc)

    def setUp(self) -> None:
        self.database = _Database()
        self.student = invitations.VerifiedInvitationActor(
            uid="student_uid", email="student@example.com", email_verified=True, role="student"
        )
        self.parent = invitations.VerifiedInvitationActor(
            uid="parent_uid", email="parent@example.com", email_verified=True, role=None
        )

    def _create(self) -> tuple[dict, list[tuple[str, str, str]]]:
        sent: list[tuple[str, str, str]] = []
        with patch.object(invitations.firestore, "transactional", lambda function: function):
            result = invitations.create_parent_link_invitation(
                {"recipientEmail": "Parent@example.com"}, self.student, self.database,
                email_hmac_key=self.key, deliver=lambda *args: sent.append(args), now=self.now,
            )
        return result, sent

    def test_student_request_delivers_secret_only_to_parent_and_accepts_once(self) -> None:
        result, sent = self._create()
        self.assertEqual(result["status"], "pending")
        self.assertEqual(len(sent), 1)
        recipient, invitation_id, verifier = sent[0]
        self.assertEqual(recipient, "parent@example.com")
        invitation = self.database.collection("parentLinkInvitations").document(invitation_id).data
        self.assertNotIn(verifier, str(invitation))
        self.assertNotIn("parent@example.com", str(invitation))

        with patch.object(invitations.firestore, "transactional", lambda function: function):
            accepted = invitations.accept_parent_link_invitation(
                {"invitationId": invitation_id, "verifier": verifier}, self.parent, self.database,
                email_hmac_key=self.key, now=self.now,
            )
        self.assertEqual(accepted["status"], "active")
        self.assertEqual(self.database.collection("users").document("parent_uid").data["role"], "parent")
        with self.assertRaisesRegex(invitations.ParentInvitationError, "no longer available"):
            with patch.object(invitations.firestore, "transactional", lambda function: function):
                invitations.accept_parent_link_invitation(
                    {"invitationId": invitation_id, "verifier": verifier}, self.parent, self.database,
                    email_hmac_key=self.key, now=self.now,
                )

    def test_wrong_email_student_identity_and_wrong_verifier_are_denied(self) -> None:
        _, sent = self._create()
        _, invitation_id, verifier = sent[0]
        wrong_email = invitations.VerifiedInvitationActor(
            uid="other_parent", email="other@example.com", email_verified=True, role=None
        )
        with patch.object(invitations.firestore, "transactional", lambda function: function):
            for actor, token in ((wrong_email, verifier), (self.student, verifier), (self.parent, "wrong")):
                with self.assertRaises(invitations.ParentInvitationError):
                    invitations.accept_parent_link_invitation(
                        {"invitationId": invitation_id, "verifier": token}, actor, self.database,
                        email_hmac_key=self.key, now=self.now,
                    )

    def test_delivery_failure_keeps_no_raw_email_or_verifier_in_firestore(self) -> None:
        with patch.object(invitations.firestore, "transactional", lambda function: function):
            with self.assertRaisesRegex(invitations.ParentInvitationError, "Unable to deliver"):
                invitations.create_parent_link_invitation(
                    {"recipientEmail": "parent@example.com"}, self.student, self.database,
                    email_hmac_key=self.key,
                    deliver=lambda *_: (_ for _ in ()).throw(RuntimeError("provider failed")),
                    now=self.now,
                )
        data = next(iter(self.database.collection("parentLinkInvitations").refs.values())).data
        self.assertNotIn("parent@example.com", str(data))
        self.assertNotIn("provider failed", str(data))

    def test_resend_reuses_opaque_invitation_id_and_obeys_cooldown(self) -> None:
        _, sent = self._create()
        _, invitation_id, _ = sent[0]
        with patch.object(invitations.firestore, "transactional", lambda function: function):
            with self.assertRaisesRegex(invitations.ParentInvitationError, "Please wait"):
                invitations.create_parent_link_invitation(
                    {"recipientEmail": "parent@example.com"}, self.student, self.database,
                    email_hmac_key=self.key, deliver=lambda *_: None, now=self.now,
                )
            resent: list[tuple[str, str, str]] = []
            invitations.create_parent_link_invitation(
                {"recipientEmail": "parent@example.com"}, self.student, self.database,
                email_hmac_key=self.key, deliver=lambda *args: resent.append(args),
                now=self.now + timedelta(seconds=61),
            )
        self.assertEqual(resent[0][1], invitation_id)
        self.assertEqual(len(self.database.collection("parentLinkInvitations").refs), 1)


if __name__ == "__main__":
    unittest.main()
