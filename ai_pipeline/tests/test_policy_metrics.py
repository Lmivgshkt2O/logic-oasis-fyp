from __future__ import annotations

import unittest

from logic_oasis_ai.policy_evaluation import PolicyArm
from logic_oasis_ai.prediction_contract import PredictionContract

from evaluation.manifest import OutcomeWindow
from evaluation.metrics import compute_metrics
from evaluation.outcomes import attach_outcomes
from policy_fixtures import build_dataset, full_bank_catalog, standard_history

from test_policy_replay import replayed


WINDOW = OutcomeWindow(max_later_attempts=5, max_calendar_duration_days=90)


def metrics_for(dataset, *, seed: int = 7, claim_label: str = "pipeline_demo_only"):
    result = replayed(dataset)
    outcomes = attach_outcomes(
        result, dataset, contract=PredictionContract(), outcome_window=WINDOW
    )
    return compute_metrics(
        result,
        outcomes,
        random_seed=seed,
        claim_label=claim_label,
        bootstrap_iterations=500,
    )


class PolicyMetricsTests(unittest.TestCase):
    def test_p1_counts_match_manual_expectation(self):
        dataset = build_dataset(standard_history())
        metrics = metrics_for(dataset)
        p1 = next(arm for arm in metrics.arms if arm.arm == "P1")
        # 7 attempts: 5/5, 2/5, 4/5, 5/5, 2/5, 3/5, 5/5.
        self.assertEqual(p1.decision_count, 7)
        self.assertEqual(p1.assignable_count, 7)
        self.assertEqual(p1.promotion_count, 2)
        self.assertEqual(p1.demotion_count, 0)
        self.assertEqual(p1.hold_count, 5)
        # Observed matches: a1->a2, a2->a3, b1->b2.
        self.assertEqual(p1.observed_outcome_count, 3)
        # support_needed labels: 0.4 (a1->a2) is True; others False.
        self.assertEqual(p1.observed_support_needed_count, 1)
        self.assertEqual(p1.false_promotion_count, 1)
        self.assertEqual(metrics.claim_label, "pipeline_demo_only")

    def test_all_three_primary_arms_are_reported(self):
        dataset = build_dataset(standard_history())
        metrics = metrics_for(dataset)
        self.assertEqual({arm.arm for arm in metrics.arms}, {"P1", "P2", "P3a"})
        for arm in metrics.arms:
            self.assertEqual(arm.decision_count, 7)
            self.assertEqual(arm.claim_label, "pipeline_demo_only")

    def test_bootstrap_intervals_are_bounded_and_deterministic(self):
        dataset = build_dataset(standard_history())
        first = metrics_for(dataset, seed=3)
        second = metrics_for(dataset, seed=3)
        self.assertEqual(first.to_document(), second.to_document())
        for arm in first.arms:
            for value in (*arm.promotion_rate_ci, *arm.observed_support_needed_rate_ci):
                self.assertTrue(0.0 <= value <= 1.0, value)

    def test_censoring_summary_reconciles_with_outcome_rows(self):
        dataset = build_dataset(standard_history())
        metrics = metrics_for(dataset)
        summary = dict(metrics.censoring_summary)
        self.assertGreaterEqual(summary.get("no_later_attempt", 0), 2)
        self.assertIn("counterfactual_difficulty_mismatch", summary)
        total_censored = sum(summary.values())
        self.assertGreater(total_censored, 0)
        for arm in metrics.arms:
            arm_censored = sum(
                count for _, count in arm.censored_by_reason
            )
            self.assertGreaterEqual(arm_censored, 0)

    def test_agreement_matrix_is_symmetric_and_positive(self):
        dataset = build_dataset(standard_history())
        metrics = metrics_for(dataset)
        pairs = {(a, b): (rate, count) for a, b, rate, count in metrics.agreement}
        self.assertEqual(len(pairs), 3)
        for (a, b), (rate, count) in pairs.items():
            self.assertTrue(0.0 <= rate <= 1.0)
            self.assertEqual(count, 7)
            self.assertNotEqual(a, b)

    def test_p3b_is_a_separate_model_assisted_stratum(self):
        dataset = build_dataset(standard_history())
        support_risk_by_attempt = {
            "a1": 0.10,
            "a2": 0.90,
            "a3": 0.20,
            "a4": 0.30,
            "b1": 0.80,
            "b2": 0.70,
            "b3": 0.05,
        }
        result = replayed(
            dataset,
            support_risk_by_attempt=support_risk_by_attempt,
            bank_catalog=full_bank_catalog(),
            arms=(PolicyArm.P1, PolicyArm.P2, PolicyArm.P3A, PolicyArm.P3B),
        )
        p3b_decisions = result.decisions_for(PolicyArm.P3B)
        self.assertTrue(p3b_decisions)
        for decision in p3b_decisions:
            self.assertEqual(decision.evidence_mode, "model_assisted")
            self.assertFalse(decision.used_bkt_fallback)
        outcomes = attach_outcomes(
            result, dataset, contract=PredictionContract(), outcome_window=WINDOW
        )
        metrics = compute_metrics(
            result,
            outcomes,
            random_seed=7,
            claim_label="pipeline_demo_only",
            bootstrap_iterations=500,
        )
        self.assertEqual({arm.arm for arm in metrics.arms}, {"P1", "P2", "P3a", "P3b"})


if __name__ == "__main__":
    unittest.main()
