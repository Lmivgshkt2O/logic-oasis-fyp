import tempfile
import unittest
from pathlib import Path

from logic_oasis_ai.adaptive_policy import (
    ADAPTIVE_POLICY_VERSION,
    AssignmentContext,
    Difficulty,
    EligibleBank,
    PolicyConfigurationError,
    deterministic_assignment_id,
    load_adaptive_policy_config,
    select_next_bank,
    select_next_bank_fixture,
)


POLICY_PATH = Path(__file__).parents[1] / "configs" / "adaptive_policy_v1.yaml"

BANKS = (
    EligibleBank("easy-seen", Difficulty.EASY, exposure_count=4),
    EligibleBank("easy-fresh", Difficulty.EASY, exposure_count=0),
    EligibleBank("moderate", Difficulty.MODERATE, exposure_count=1),
    EligibleBank("hard", Difficulty.HARD, exposure_count=0),
)


def context(**overrides):
    values = {
        "student_id": "student-1",
        "subtopic_id": "read_write_numbers",
        "current_difficulty": Difficulty.EASY,
        "mastery_probability": 0.60,
        "evidence_count": 3,
        "support_risk": 0.50,
        "last_transition": None,
    }
    values.update(overrides)
    return AssignmentContext(**values)


class AdaptivePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_adaptive_policy_config(POLICY_PATH)

    def choose(self, decision_context, banks=BANKS):
        return select_next_bank(decision_context, banks, policy=self.policy)

    def test_yaml_config_has_version_hash_and_all_required_explanations(self):
        self.assertEqual(self.policy.policy_version, ADAPTIVE_POLICY_VERSION)
        self.assertEqual(len(self.policy.source_sha256), 64)
        self.assertEqual(self.policy.cold_start_difficulty, Difficulty.EASY)
        self.assertIn("move_up_mastery", self.policy.reason_texts)
        with self.assertRaises(TypeError):
            self.policy.reason_texts["move_up_mastery"] = "changed"  # type: ignore[index]

    def test_cold_start_selects_least_exposed_easy_bank(self):
        decision = self.choose(context(current_difficulty=None, mastery_probability=None))

        self.assertEqual(decision.bank_id, "easy-fresh")
        self.assertEqual(decision.reason_code, "cold_start_easy")
        self.assertTrue(decision.used_bkt_fallback)
        self.assertEqual(decision.outcome_status, "assigned")

    def test_strong_evidence_moves_up_one_level(self):
        decision = self.choose(context(mastery_probability=0.80, support_risk=0.20))

        self.assertEqual(decision.difficulty, Difficulty.MODERATE)
        self.assertEqual(decision.reason_code, "move_up_mastery")
        self.assertEqual(decision.policy_version, ADAPTIVE_POLICY_VERSION)
        self.assertTrue(decision.child_friendly_explanation)

    def test_hard_requires_minimum_evidence(self):
        decision = self.choose(
            context(
                current_difficulty=Difficulty.MODERATE,
                mastery_probability=0.85,
                evidence_count=3,
                support_risk=0.20,
            )
        )

        self.assertEqual(decision.difficulty, Difficulty.MODERATE)
        self.assertEqual(decision.reason_code, "hard_requires_more_evidence")

    def test_existing_hard_assignment_steps_down_without_hard_evidence(self):
        decision = self.choose(
            context(
                current_difficulty=Difficulty.HARD,
                mastery_probability=0.90,
                evidence_count=3,
                support_risk=0.10,
            )
        )

        self.assertEqual(decision.difficulty, Difficulty.MODERATE)
        self.assertEqual(decision.reason_code, "hard_requires_more_evidence")

    def test_high_support_risk_moves_down_once(self):
        decision = self.choose(
            context(
                current_difficulty=Difficulty.MODERATE,
                mastery_probability=0.60,
                support_risk=0.80,
            )
        )

        self.assertEqual(decision.difficulty, Difficulty.EASY)
        self.assertEqual(decision.reason_code, "move_down_support")
        self.assertEqual(decision.bank_id, "easy-fresh")

    def test_mixed_evidence_stays_at_current_level(self):
        decision = self.choose(context())

        self.assertEqual(decision.difficulty, Difficulty.EASY)
        self.assertEqual(decision.reason_code, "stay_target_zone")

    def test_immediate_move_back_up_is_blocked(self):
        decision = self.choose(
            context(
                mastery_probability=0.90,
                support_risk=0.10,
                last_transition="move_down_support",
            )
        )

        self.assertEqual(decision.difficulty, Difficulty.EASY)
        self.assertEqual(decision.reason_code, "anti_oscillation_stay")

    def test_immediate_move_back_down_is_blocked(self):
        decision = self.choose(
            context(
                current_difficulty=Difficulty.MODERATE,
                mastery_probability=0.20,
                support_risk=0.90,
                last_transition="move_up_mastery",
            )
        )

        self.assertEqual(decision.difficulty, Difficulty.MODERATE)
        self.assertEqual(decision.reason_code, "anti_oscillation_stay")

    def test_difficulty_boundaries_stay_with_accurate_explanations(self):
        easy = self.choose(context(mastery_probability=0.20, support_risk=0.90))
        hard = self.choose(
            context(
                current_difficulty=Difficulty.HARD,
                mastery_probability=0.90,
                evidence_count=8,
                support_risk=0.10,
            )
        )

        self.assertEqual(easy.reason_code, "stay_easy_support")
        self.assertEqual(hard.reason_code, "stay_hard_mastery")

    def test_missing_promoted_model_uses_bkt_rule_fallback(self):
        decision = self.choose(context(mastery_probability=0.80, support_risk=None))

        self.assertEqual(decision.reason_code, "move_up_bkt_fallback")
        self.assertTrue(decision.used_bkt_fallback)

    def test_no_eligible_bank_returns_explicit_fallback_state(self):
        decision = self.choose(context(), ())

        self.assertFalse(decision.is_assignable)
        self.assertEqual(decision.reason_code, "no_eligible_bank")
        self.assertEqual(decision.outcome_status, "fallback")
        self.assertIn("try again", decision.child_friendly_explanation.lower())
        with self.assertRaises(ValueError):
            decision.to_firestore_document()

    def test_runtime_cannot_silently_use_defaults_for_missing_or_invalid_yaml(self):
        with self.assertRaises(PolicyConfigurationError):
            load_adaptive_policy_config(POLICY_PATH.with_name("missing.yaml"))
        with tempfile.TemporaryDirectory() as temporary_directory:
            invalid_path = Path(temporary_directory) / "invalid.yaml"
            invalid_path.write_text(
                "policyVersion: adaptive-policy-v1\n"
                "thresholds: {}\n",
                encoding="utf-8",
            )
            with self.assertRaises(PolicyConfigurationError):
                load_adaptive_policy_config(invalid_path)
        with self.assertRaises(TypeError):
            select_next_bank(context(), BANKS)  # type: ignore[call-arg]
        fixture_decision = select_next_bank_fixture(context(), BANKS)
        self.assertEqual(fixture_decision.policy_version, ADAPTIVE_POLICY_VERSION)

    def test_same_source_attempt_has_same_assignment_id_across_retries(self):
        self.assertEqual(
            deterministic_assignment_id("attempt-123"),
            deterministic_assignment_id("attempt-123"),
        )
        self.assertNotEqual(
            deterministic_assignment_id("attempt-123"),
            deterministic_assignment_id("attempt-124"),
        )
        with self.assertRaises(ValueError):
            deterministic_assignment_id("")


if __name__ == "__main__":
    unittest.main()
