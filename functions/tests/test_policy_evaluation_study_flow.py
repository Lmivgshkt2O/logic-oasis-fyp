from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "ai_pipeline") not in sys.path:
    sys.path.insert(0, str(ROOT / "ai_pipeline"))
if str(ROOT / "functions") not in sys.path:
    sys.path.insert(0, str(ROOT / "functions"))

import ai_runtime
import policy_evaluation as evaluation
from ai_runtime import RuntimeBundle, process_finalized_attempt
from test_ai_runtime import MemoryGateway, trusted_attempt, trusted_responses
from test_policy_evaluation_enrollment import (
    EXPIRE_FUTURE,
    NOW,
    _Db,
    admin,
    study_data,
)


class PolicyEvaluationStudyFlowTests(unittest.TestCase):
    """AQC-7 disposable-account smoke flow at the unit boundary."""

    def setUp(self) -> None:
        ai_runtime._clear_controlled_demo_native_cache()
        self.database = _Db()
        self.gateway = MemoryGateway(trusted_attempt(), trusted_responses())
        self.bundle = RuntimeBundle.from_runtime_root(
            ROOT / "ai_pipeline",
            evidence_mode="real_evaluated_only",
            model_bucket="logic-oasis-models",
        )

    def _with_transaction(self, call):
        with patch.object(evaluation.firestore, "transactional", lambda fn: fn):
            return call()

    def _open_study_and_consent(self) -> None:
        self._with_transaction(
            lambda: evaluation.apply_study_update(
                self.database,
                study_version="study-v1",
                data=study_data("draft"),
                admin=admin(),
                release_ref="PES-GATE-2026-001",
                rationale="recorded developer release",
                now=NOW,
            )
        )
        self._with_transaction(
            lambda: evaluation.apply_study_update(
                self.database,
                study_version="study-v1",
                data=study_data("enrolling"),
                admin=admin(),
                release_ref="PES-GATE-2026-001",
                rationale="recorded developer release",
                now=NOW,
            )
        )
        self._with_transaction(
            lambda: evaluation.apply_consent_update(
                self.database,
                student_id="student-1",
                study_version="study-v1",
                data={
                    "status": "active",
                    "consentRecordRef": "consent-record-1",
                    "expiresAt": EXPIRE_FUTURE,
                },
                admin=admin(),
                release_ref="PES-GATE-2026-001",
                rationale="recorded consent",
                now=NOW,
            )
        )

    def test_disposable_enrolled_learner_gets_the_allocated_arm_and_audit(self) -> None:
        self._open_study_and_consent()
        self.database.collection("policyEvaluationAllocationBlocks").document(
            "study-v1_4_topic-1_subtopic-1_Easy"
        ).data = {"P1": 0, "P2": 5, "P3a": 5, "updatedAt": NOW}
        enrolled = self._with_transaction(
            lambda: evaluation.create_enrollment(
                self.database,
                student_id="student-1",
                year_level=4,
                topic_id="topic-1",
                subtopic_id="subtopic-1",
                starting_difficulty="Easy",
                study_version="study-v1",
                allocation_key="disposable-allocation-secret",
                admin=admin(),
                release_ref="PES-GATE-2026-001",
                rationale="recorded enrollment",
                now=NOW,
            )
        )
        self.assertEqual("P1", enrolled["assignedArm"])
        self.gateway.enrollment_doc = {
            "enrollmentId": enrolled["enrollmentId"],
            "studyVersion": "study-v1",
            "assignedArm": "P1",
            "status": "active",
        }

        process_finalized_attempt(
            "attempt-1", gateway=self.gateway, bundle=self.bundle, provenance="real"
        )
        assignment = self.gateway.finalized[-1]["assignment"]
        self.assertEqual("assignment-delivery-v1", assignment["policyVersion"])
        self.assertIn(assignment["reasonCode"], {"advance_ready", "build_evidence", "practice_support", "no_eligible_bank"})
        audit = next(iter(self.gateway.policy_audits.values()))
        self.assertEqual("P1", audit["assignedArm"])
        self.assertEqual("study-v1", audit["studyVersion"])
        self.assertEqual(1, len(self.gateway.policy_probes))

        duplicate = process_finalized_attempt(
            "attempt-1", gateway=self.gateway, bundle=self.bundle, provenance="real"
        )
        self.assertEqual(duplicate, self.gateway.finalized[-1]["state"])
        self.assertEqual(1, len(self.gateway.policy_audits))
        self.assertEqual(1, len(self.gateway.policy_probes))

    def test_disposable_non_participant_keeps_the_production_p3_path(self) -> None:
        process_finalized_attempt(
            "attempt-1", gateway=self.gateway, bundle=self.bundle, provenance="real"
        )
        assignment = self.gateway.finalized[-1]["assignment"]
        self.assertEqual("adaptive-policy-v1", assignment["policyVersion"])
        self.assertEqual({}, self.gateway.policy_audits)
        self.assertEqual({}, self.gateway.policy_probes)


if __name__ == "__main__":
    unittest.main()

