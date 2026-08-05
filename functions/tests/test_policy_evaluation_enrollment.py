from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import policy_evaluation as evaluation


UTC = timezone.utc
NOW = datetime(2026, 8, 5, tzinfo=UTC)
EXPIRE_FUTURE = datetime(2027, 1, 1, tzinfo=UTC)
EXPIRE_PAST = datetime(2026, 1, 1, tzinfo=UTC)


class _Ref:
    def __init__(self, identifier: str) -> None:
        self.id = identifier
        self.data: dict | None = None

    def get(self, transaction=None):
        return SimpleNamespace(
            exists=self.data is not None,
            to_dict=lambda: self.data,
        )

    def create(self, data: dict) -> None:
        if self.data is not None:
            raise ValueError("already exists")
        self.data = dict(data)

    def set(self, data: dict) -> None:
        self.data = dict(data)

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
    def get(self, ref: _Ref):
        return ref.get()

    def create(self, ref: _Ref, data: dict) -> None:
        ref.create(data)

    def set(self, ref: _Ref, data: dict) -> None:
        ref.set(data)

    def update(self, ref: _Ref, data: dict) -> None:
        ref.update(data)


def admin():
    return evaluation.VerifiedPolicyEvaluationAdmin(
        uid="admin-1", claims={"policyEvaluationAdmin": True}
    )


def study_data(status: str = "draft", **overrides) -> dict:
    data = {
        "status": status,
        "manifestHash": "a" * 64,
        "policyVersions": {"P1": "score-threshold-v1", "P2": "bkt-score-agreement-v1"},
        "outcomeProtocolVersion": "policy-outcomes-v1",
        "deltaFD": 0.05,
        "randomizationVersion": "blocked-random-v1",
    }
    data.update(overrides)
    return data


class PolicyEvaluationEnrollmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = _Db()

    def create_study(self, status: str = "draft", **overrides) -> dict[str, str]:
        with patch.object(evaluation.firestore, "transactional", lambda fn: fn):
            return evaluation.apply_study_update(
                self.database,
                study_version="study-v1",
                data=study_data(status, **overrides),
                admin=admin(),
                release_ref="PES-GATE-2026-001",
                rationale="recorded developer release",
                now=NOW,
            )

    def record_consent(
        self,
        status: str = "active",
        expires_at=EXPIRE_FUTURE,
        student_id: str = "student-1",
    ) -> dict[str, str]:
        with patch.object(evaluation.firestore, "transactional", lambda fn: fn):
            return evaluation.apply_consent_update(
                self.database,
                student_id=student_id,
                study_version="study-v1",
                data={"status": status, "consentRecordRef": "consent-record-1", "expiresAt": expires_at},
                admin=admin(),
                release_ref="PES-GATE-2026-001",
                rationale="recorded consent",
                now=NOW,
            )

    def enroll(self, **overrides) -> dict[str, str]:
        values = {
            "student_id": "student-1",
            "year_level": 4,
            "topic_id": "topic-numbers",
            "subtopic_id": "read_write_numbers",
            "starting_difficulty": "Easy",
            "study_version": "study-v1",
            "allocation_key": "allocation-secret",
            "admin": admin(),
            "release_ref": "PES-GATE-2026-001",
            "rationale": "recorded enrollment",
            "now": NOW,
        }
        values.update(overrides)
        with patch.object(evaluation.firestore, "transactional", lambda fn: fn):
            return evaluation.create_enrollment(self.database, **values)

    def test_study_lifecycle_transitions_and_frozen_active_manifest(self) -> None:
        self.assertEqual("draft", self.create_study()["status"])
        self.assertEqual("enrolling", self.create_study("enrolling")["status"])
        active = self.create_study("active")
        self.assertEqual("active", active["status"])
        stored = self.database.collections["policyEvaluationStudies"].refs[
            "study-v1"
        ].data
        self.assertEqual("a" * 64, stored["manifestHash"])
        with self.assertRaises(evaluation.PolicyEvaluationError):
            self.create_study("draft")
        with self.assertRaises(evaluation.PolicyEvaluationError):
            self.create_study("enrolling")
        self.assertEqual("closed", self.create_study("closed")["status"])
        self.assertEqual("archived", self.create_study("archived")["status"])

    def test_study_must_be_created_in_draft(self) -> None:
        with self.assertRaisesRegex(evaluation.PolicyEvaluationError, "created in draft"):
            with patch.object(evaluation.firestore, "transactional", lambda fn: fn):
                evaluation.apply_study_update(
                    self.database,
                    study_version="study-other",
                    data=study_data("active"),
                    admin=admin(),
                    release_ref="ref",
                    rationale="why",
                    now=NOW,
                )

    def test_consent_records_only_declared_states_and_is_idempotent(self) -> None:
        self.assertEqual("active", self.record_consent()["status"])
        self.assertEqual("active", self.record_consent()["status"])
        self.assertEqual("revoked", self.record_consent("revoked")["status"])
        with self.assertRaises(evaluation.PolicyEvaluationError):
            self.record_consent("unknown")

    def test_enrollment_requires_open_study_active_consent_and_secret(self) -> None:
        with self.assertRaisesRegex(evaluation.PolicyEvaluationError, "study"):
            self.enroll()
        self.create_study("draft")
        self.create_study("enrolling")
        with self.assertRaisesRegex(evaluation.PolicyEvaluationError, "consent"):
            self.enroll()
        self.record_consent()
        block = self.database.collection("policyEvaluationAllocationBlocks").document(
            "study-v1_4_topic-numbers_read_write_numbers_Easy"
        )
        block.data = {"P1": 0, "P2": 5, "P3a": 5, "updatedAt": NOW}
        self.assertEqual("P1", self.enroll()["assignedArm"])
        with self.assertRaisesRegex(evaluation.PolicyEvaluationError, "allocation secret"):
            self.enroll(student_id="student-2", allocation_key="")
        self.record_consent("revoked", student_id="student-2")
        with self.assertRaisesRegex(evaluation.PolicyEvaluationError, "Consent is not active"):
            self.enroll(student_id="student-2")

    def test_expired_consent_fails_safely(self) -> None:
        self.create_study("draft")
        self.create_study("enrolling")
        self.create_study("active")
        self.record_consent("active", expires_at=EXPIRE_PAST)
        with self.assertRaisesRegex(evaluation.PolicyEvaluationError, "expired"):
            self.enroll()

    def test_closed_study_fails_enrollment(self) -> None:
        self.create_study("draft")
        self.create_study("enrolling")
        self.create_study("active")
        self.record_consent()
        self.create_study("closed")
        with self.assertRaisesRegex(evaluation.PolicyEvaluationError, "not open"):
            self.enroll(student_id="student-2")

    def test_enrollment_allocates_lowest_count_arm_and_duplicate_is_idempotent(self) -> None:
        self.create_study("draft")
        self.create_study("enrolling")
        self.record_consent()
        block = self.database.collection("policyEvaluationAllocationBlocks").document(
            "study-v1_4_topic-numbers_read_write_numbers_Easy"
        )
        block.data = {"P1": 1, "P2": 1, "P3a": 0, "updatedAt": NOW}

        first = self.enroll()
        self.assertEqual("P3a", first["assignedArm"])
        duplicate = self.enroll()
        self.assertEqual(first, duplicate)
        self.assertEqual(1, block.data["P3a"])

    def test_hmac_allocation_is_deterministic_and_spreads_ties(self) -> None:
        payload = "study-v1:student-1:4:topic-numbers:read_write_numbers:Easy"
        self.assertEqual(
            evaluation.allocate_arm({}, payload, "secret"),
            evaluation.allocate_arm({}, payload, "secret"),
        )
        chosen = {
            evaluation.allocate_arm({}, f"{payload}:{index}", "secret")
            for index in range(24)
        }
        self.assertGreaterEqual(len(chosen), 2)

    def test_revoke_stops_future_decisions_without_rewriting_history(self) -> None:
        self.create_study("draft")
        self.create_study("enrolling")
        self.record_consent()
        enrolled = self.enroll()
        enrollment_id = enrolled["enrollmentId"]
        with patch.object(evaluation.firestore, "transactional", lambda fn: fn):
            revoked = evaluation.revoke_enrollment(
                self.database,
                student_id="student-1",
                year_level=4,
                topic_id="topic-numbers",
                subtopic_id="read_write_numbers",
                study_version="study-v1",
                admin=admin(),
                release_ref="PES-GATE-2026-001",
                rationale="revoked by release decision",
                now=NOW,
            )
        self.assertEqual("revoked", revoked["status"])
        self.assertIsNone(
            evaluation.active_enrollment_for(
                self.database,
                student_id="student-1",
                year_level=4,
                topic_id="topic-numbers",
                subtopic_id="read_write_numbers",
                study_version="study-v1",
            )
        )
        stored = self.database.collections["policyEvaluationEnrollments"].refs[
            enrollment_id
        ].data
        self.assertEqual("student-1", stored["studentId"])
        self.assertEqual("revoked", stored["status"])

    def test_active_enrollment_is_readable_by_start_boundary(self) -> None:
        self.create_study("draft")
        self.create_study("enrolling")
        self.create_study("active")
        self.record_consent()
        self.database.collection("policyEvaluationAllocationBlocks").document(
            "study-v1_4_topic-numbers_read_write_numbers_Easy"
        ).data = {"P1": 0, "P2": 5, "P3a": 5, "updatedAt": NOW}
        self.enroll()
        document = evaluation.active_enrollment_for(
            self.database,
            student_id="student-1",
            year_level=4,
            topic_id="topic-numbers",
            subtopic_id="read_write_numbers",
            study_version="study-v1",
        )
        self.assertIsNotNone(document)
        self.assertEqual("P1", document["assignedArm"])

    def test_bootstrap_grant_and_revoke_write_immutable_audit_and_revoke_tokens(self) -> None:
        tools_root = Path(__file__).resolve().parents[2] / "tools"
        sys.path.insert(0, str(tools_root))
        import bootstrap_policy_evaluation_admin as bootstrap

        user = SimpleNamespace(custom_claims={"other": "kept"})
        calls: list[tuple[str, object]] = []

        def set_claims(uid, claims):
            calls.append(("set", (uid, claims)))
            user.custom_claims = claims

        revoke_tokens = lambda uid: calls.append(("revoke", uid))

        audit_id = bootstrap.apply_claim_change(
            database=self.database,
            uid="admin_uid",
            action="grant",
            release_id="PES-GATE-2026-001",
            rationale="recorded developer release",
            actor="logic-oasis-identity-admin@logic-oasis-fyp.iam.gserviceaccount.com",
            get_user=lambda uid: user,
            set_custom_user_claims=set_claims,
            revoke_refresh_tokens=revoke_tokens,
            now=NOW,
        )
        audit = self.database.collections["adminRoleAudits"].refs[audit_id].data
        self.assertEqual("policy_evaluation_admin_claim", audit["auditType"])
        self.assertEqual("PES-GATE-2026-001", audit["releaseRef"])
        self.assertTrue(user.custom_claims["policyEvaluationAdmin"])
        self.assertEqual("kept", user.custom_claims["other"])

        bootstrap.apply_claim_change(
            database=self.database,
            uid="admin_uid",
            action="revoke",
            release_id="PES-GATE-2026-001",
            rationale="recorded developer release",
            actor="logic-oasis-identity-admin@logic-oasis-fyp.iam.gserviceaccount.com",
            get_user=lambda uid: user,
            set_custom_user_claims=set_claims,
            revoke_refresh_tokens=revoke_tokens,
            now=NOW,
        )
        self.assertNotIn("policyEvaluationAdmin", user.custom_claims)
        self.assertIn(("revoke", "admin_uid"), calls)

    def test_admin_verification_requires_claim_and_revocation_check(self) -> None:
        from policy_evaluation_admin import verify_policy_evaluation_admin

        def request_for(auth_context, token="token"):
            return SimpleNamespace(
                auth=SimpleNamespace(uid=auth_context),
                raw_request=SimpleNamespace(headers={"Authorization": f"Bearer {token}"}),
            )

        def claims_verify(claims):
            return lambda token, check_revoked=False: claims

        verified = verify_policy_evaluation_admin(
            request_for("admin-1"),
            verify_token=claims_verify(
                {"uid": "admin-1", "policyEvaluationAdmin": True}
            ),
        )
        self.assertEqual("admin-1", verified.uid)

        with self.assertRaisesRegex(evaluation.PolicyEvaluationError, "permission"):
            verify_policy_evaluation_admin(
                request_for("admin-1"),
                verify_token=claims_verify({"uid": "admin-1"}),
            )

        def raise_revoked(*_args, **_kwargs):
            raise RuntimeError("revoked")

        with self.assertRaisesRegex(evaluation.PolicyEvaluationError, "no longer active"):
            verify_policy_evaluation_admin(
                request_for("admin-1"), verify_token=raise_revoked
            )

        with self.assertRaisesRegex(evaluation.PolicyEvaluationError, "Sign in"):
            verify_policy_evaluation_admin(SimpleNamespace(auth=None, raw_request=None))


if __name__ == "__main__":
    unittest.main()
