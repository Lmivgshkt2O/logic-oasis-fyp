import unittest

from logic_oasis_ai.adaptive_policy import (
    ADAPTIVE_POLICY_VERSION,
    AssignmentContext,
    Difficulty,
    EligibleBank,
    select_next_bank,
)


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
    def test_cold_start_selects_least_exposed_easy_bank(self):
        decision = select_next_bank(
            context(current_difficulty=None, mastery_probability=None),
            BANKS,
        )

        self.assertEqual(decision.bank_id, "easy-fresh")
        self.assertEqual(decision.reason_code, "cold_start_easy")
        self.assertTrue(decision.used_bkt_fallback)

    def test_strong_evidence_moves_up_one_level(self):
        decision = select_next_bank(
            context(mastery_probability=0.80, support_risk=0.20),
            BANKS,
        )

        self.assertEqual(decision.difficulty, Difficulty.MODERATE)
        self.assertEqual(decision.reason_code, "move_up_mastery")
        self.assertEqual(decision.policy_version, ADAPTIVE_POLICY_VERSION)

    def test_hard_requires_minimum_evidence(self):
        decision = select_next_bank(
            context(
                current_difficulty=Difficulty.MODERATE,
                mastery_probability=0.85,
                evidence_count=3,
                support_risk=0.20,
            ),
            BANKS,
        )

        self.assertEqual(decision.difficulty, Difficulty.MODERATE)
        self.assertEqual(decision.reason_code, "hard_requires_more_evidence")

    def test_high_support_risk_moves_down_once(self):
        decision = select_next_bank(
            context(
                current_difficulty=Difficulty.MODERATE,
                mastery_probability=0.60,
                support_risk=0.80,
            ),
            BANKS,
        )

        self.assertEqual(decision.difficulty, Difficulty.EASY)
        self.assertEqual(decision.reason_code, "move_down_support")
        self.assertEqual(decision.bank_id, "easy-fresh")

    def test_mixed_evidence_stays_at_current_level(self):
        decision = select_next_bank(context(), BANKS)

        self.assertEqual(decision.difficulty, Difficulty.EASY)
        self.assertEqual(decision.reason_code, "stay_target_zone")

    def test_immediate_move_back_up_is_blocked(self):
        decision = select_next_bank(
            context(
                mastery_probability=0.90,
                support_risk=0.10,
                last_transition="move_down",
            ),
            BANKS,
        )

        self.assertEqual(decision.difficulty, Difficulty.EASY)
        self.assertEqual(decision.reason_code, "anti_oscillation_stay")

    def test_immediate_moderate_to_hard_reversal_is_blocked(self):
        decision = select_next_bank(
            context(
                current_difficulty=Difficulty.MODERATE,
                mastery_probability=0.90,
                evidence_count=8,
                support_risk=0.10,
                last_transition="move_down",
            ),
            BANKS,
        )

        self.assertEqual(decision.difficulty, Difficulty.MODERATE)
        self.assertEqual(decision.reason_code, "anti_oscillation_stay")

    def test_difficulty_boundaries_stay_with_accurate_explanations(self):
        easy = select_next_bank(
            context(mastery_probability=0.20, support_risk=0.90),
            BANKS,
        )
        hard = select_next_bank(
            context(
                current_difficulty=Difficulty.HARD,
                mastery_probability=0.90,
                evidence_count=8,
                support_risk=0.10,
            ),
            BANKS,
        )

        self.assertEqual(easy.reason_code, "stay_easy_support")
        self.assertEqual(hard.reason_code, "stay_hard_mastery")

    def test_missing_model_uses_bkt_fallback(self):
        decision = select_next_bank(
            context(mastery_probability=0.80, support_risk=None),
            BANKS,
        )

        self.assertEqual(decision.reason_code, "move_up_bkt_fallback")
        self.assertTrue(decision.used_bkt_fallback)

    def test_no_eligible_bank_returns_transparent_unavailable_state(self):
        decision = select_next_bank(context(), ())

        self.assertFalse(decision.is_assignable)
        self.assertEqual(decision.reason_code, "no_eligible_bank")
        self.assertIn("try again", decision.child_friendly_explanation.lower())


if __name__ == "__main__":
    unittest.main()
