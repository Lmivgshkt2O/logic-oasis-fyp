from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "ai_pipeline") not in sys.path:
    sys.path.insert(0, str(ROOT / "ai_pipeline"))
if str(ROOT / "functions") not in sys.path:
    sys.path.insert(0, str(ROOT / "functions"))

import ai_runtime
from logic_oasis_ai.adaptive_policy import Difficulty, EligibleBank, load_adaptive_policy_config
from logic_oasis_ai.policy_evaluation import (
    PolicyArm,
    PolicyDecisionContext,
    load_policy_evaluation_manifest,
    select_policy_decision,
)


CONFIGS = ROOT / "ai_pipeline" / "configs"
ADAPTIVE_POLICY_PATH = CONFIGS / "adaptive_policy_v1.yaml"
MANIFEST_PATH = CONFIGS / "policy_evaluation_v1.yaml"
NEUTRAL_VALUES = {"advance_ready", "build_evidence", "practice_support", "no_eligible_bank"}
BANKS = (
    EligibleBank("easy-1", Difficulty.EASY),
    EligibleBank("easy-2", Difficulty.EASY),
    EligibleBank("moderate-1", Difficulty.MODERATE),
    EligibleBank("moderate-2", Difficulty.MODERATE),
    EligibleBank("hard-1", Difficulty.HARD),
)


def context(**overrides) -> PolicyDecisionContext:
    values = {
        "source_attempt_id": "attempt-1",
        "student_id": "student-1",
        "subtopic_id": "read_write_numbers",
        "current_difficulty": Difficulty.EASY,
        "correct_count": 3,
        "total_questions": 5,
        "mastery_probability": 0.6,
        "evidence_count": 5,
        "support_risk": None,
        "compatible_model_available": False,
        "last_transition": None,
    }
    values.update(overrides)
    return PolicyDecisionContext(**values)


class PolicyEvaluationRuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adaptive_policy = load_adaptive_policy_config(ADAPTIVE_POLICY_PATH)
        cls.manifest = load_policy_evaluation_manifest(
            MANIFEST_PATH, adaptive_policy=cls.adaptive_policy
        )

    def choose(self, arm, decision_context, banks=BANKS):
        return select_policy_decision(
            arm,
            decision_context,
            banks,
            manifest=self.manifest,
            adaptive_policy=self.adaptive_policy,
        )

    def test_neutral_mapping_covers_every_declared_selector_reason(self) -> None:
        declared = set(self.manifest.reason_codes)
        mapped = set(ai_runtime.NEUTRAL_REASON_CODES)
        self.assertLessEqual(declared, mapped)
        for value in ai_runtime.NEUTRAL_REASON_CODES.values():
            self.assertIn(value, NEUTRAL_VALUES)
        self.assertEqual(ai_runtime.POLICY_ASSIGNMENT_DELIVERY_VERSION, "assignment-delivery-v1")

    def test_unknown_reason_fails_closed_to_the_safe_fallback(self) -> None:
        with self.assertRaises(ai_runtime.RuntimeFailure):
            ai_runtime.neutral_reason_code("undeclared_reason")

    def test_p1_promote_maps_to_advance_ready(self) -> None:
        decision = self.choose(PolicyArm.P1, context(correct_count=4))
        self.assertEqual("p1_score_promote", decision.reason_code)
        self.assertEqual("advance_ready", ai_runtime.neutral_reason_code(decision.reason_code))

    def test_p1_hold_maps_to_build_evidence(self) -> None:
        decision = self.choose(PolicyArm.P1, context(correct_count=3))
        self.assertEqual("p1_score_hold", decision.reason_code)
        self.assertEqual("build_evidence", ai_runtime.neutral_reason_code(decision.reason_code))

    def test_p2_disagreement_hold_maps_to_build_evidence(self) -> None:
        decision = self.choose(
            PolicyArm.P2, context(correct_count=3, mastery_probability=0.8)
        )
        self.assertEqual("p2_disagreement_hold", decision.reason_code)
        self.assertEqual("build_evidence", ai_runtime.neutral_reason_code(decision.reason_code))

    def test_p2_agreement_demote_maps_to_practice_support(self) -> None:
        decision = self.choose(
            PolicyArm.P2,
            context(
                current_difficulty=Difficulty.MODERATE,
                correct_count=2,
                mastery_probability=0.4,
            ),
        )
        self.assertEqual("p2_agreement_demote", decision.reason_code)
        self.assertEqual("practice_support", ai_runtime.neutral_reason_code(decision.reason_code))

    def test_p3a_uses_bkt_fallback_and_maps_mastery_up_to_advance_ready(self) -> None:
        decision = self.choose(
            PolicyArm.P3A,
            context(correct_count=5, mastery_probability=0.9),
        )
        self.assertEqual("p3_move_up_bkt_fallback", decision.reason_code)
        self.assertTrue(decision.used_bkt_fallback)
        self.assertEqual("advance_ready", ai_runtime.neutral_reason_code(decision.reason_code))

    def test_no_eligible_bank_maps_to_no_eligible_bank(self) -> None:
        easy_only = tuple(bank for bank in BANKS if bank.difficulty is Difficulty.EASY)
        decision = self.choose(PolicyArm.P1, context(correct_count=5), easy_only)
        self.assertEqual("no_eligible_bank", decision.reason_code)
        self.assertEqual("no_eligible_bank", ai_runtime.neutral_reason_code(decision.reason_code))


if __name__ == "__main__":
    unittest.main()

