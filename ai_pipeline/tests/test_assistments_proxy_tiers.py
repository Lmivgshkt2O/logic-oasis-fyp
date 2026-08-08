"""AQC-E2 within-skill proxy tier tests (frozen E1 methodology).

Tier assignment is tested on problem counts divisible by three, where every
stable-rank tertile convention agrees and the frozen ordering (p_correct
descending, then externalProblemKey ascending) fully determines the result.
The E1 contract does not yet freeze the non-divisible boundary rule; that gap
is recorded in the E2 report and the real-data run does not apply it.
"""

from __future__ import annotations

import unittest

from external_data.assistments.adaptive.proxy_tiers import (
    SKILL_CATALOG_MINIMUM_PER_TIER,
    SKILL_CATALOG_MINIMUM_PROBLEMS,
    CalibratedProblem,
    ProxyTierError,
    assign_within_skill_tiers,
    evaluate_skill_catalog,
    summarize_skill_catalogs,
    tier_counts_by_tier,
)


def problem(key: str, skill: str, p_correct: float) -> CalibratedProblem:
    return CalibratedProblem(
        external_problem_key=key,
        source_skill_code=skill,
        p_correct=p_correct,
    )


class WithinSkillTierTests(unittest.TestCase):
    def test_tier_assignment_occurs_within_skill_only(self) -> None:
        problems = [
            problem("p1", "skill-a", 0.9),
            problem("p2", "skill-a", 0.5),
            problem("p3", "skill-a", 0.1),
            problem("q1", "skill-b", 0.9),
            problem("q2", "skill-b", 0.5),
            problem("q3", "skill-b", 0.1),
        ]
        assigned = assign_within_skill_tiers(problems)
        self.assertEqual(assigned["p1"], "proxy_easy")
        self.assertEqual(assigned["p2"], "proxy_moderate")
        self.assertEqual(assigned["p3"], "proxy_hard")
        self.assertEqual(assigned["q1"], "proxy_easy")
        self.assertEqual(assigned["q2"], "proxy_moderate")
        self.assertEqual(assigned["q3"], "proxy_hard")

    def test_different_skills_cannot_affect_each_others_ranking(self) -> None:
        baseline = [
            problem("a1", "skill-x", 0.99),
            problem("a2", "skill-x", 0.98),
            problem("a3", "skill-x", 0.01),
        ]
        alone = assign_within_skill_tiers(baseline)
        with_other = assign_within_skill_tiers(
            baseline
            + [
                problem("b1", "skill-y", 0.95),
                problem("b2", "skill-y", 0.94),
                problem("b3", "skill-y", 0.02),
            ]
        )
        self.assertEqual(alone, {key: with_other[key] for key in alone})

    def test_deterministic_ties_reproduce_the_same_tier(self) -> None:
        tied = [
            problem("p-a", "skill-t", 0.5),
            problem("p-b", "skill-t", 0.5),
            problem("p-c", "skill-t", 0.5),
            problem("p-d", "skill-t", 0.5),
            problem("p-e", "skill-t", 0.5),
            problem("p-f", "skill-t", 0.5),
            problem("p-g", "skill-t", 0.5),
            problem("p-h", "skill-t", 0.5),
            problem("p-i", "skill-t", 0.5),
        ]
        first = assign_within_skill_tiers(tied)
        second = assign_within_skill_tiers(tied)
        self.assertEqual(first, second)
        counts = tier_counts_by_tier(first)
        self.assertEqual(counts, {"proxy_easy": 3, "proxy_moderate": 3, "proxy_hard": 3})

    def test_key_ordering_breaks_p_correct_ties(self) -> None:
        tied = [
            problem("p-2", "skill-t", 0.5),
            problem("p-1", "skill-t", 0.5),
            problem("p-3", "skill-t", 0.5),
            problem("p-5", "skill-t", 0.5),
            problem("p-4", "skill-t", 0.5),
            problem("p-6", "skill-t", 0.5),
            problem("p-8", "skill-t", 0.5),
            problem("p-7", "skill-t", 0.5),
            problem("p-9", "skill-t", 0.5),
        ]
        assigned = assign_within_skill_tiers(tied)
        self.assertEqual(assigned["p-1"], "proxy_easy")
        self.assertEqual(assigned["p-2"], "proxy_easy")
        self.assertEqual(assigned["p-3"], "proxy_easy")
        self.assertEqual(assigned["p-4"], "proxy_moderate")
        self.assertEqual(assigned["p-9"], "proxy_hard")

    def test_no_cross_skill_pooling_occurs(self) -> None:
        assigned = assign_within_skill_tiers(
            [
                problem("a1", "skill-a", 0.9),
                problem("a2", "skill-a", 0.8),
                problem("a3", "skill-a", 0.2),
                problem("b1", "skill-b", 0.6),
                problem("b2", "skill-b", 0.5),
                problem("b3", "skill-b", 0.4),
            ]
        )
        # skill-a's middle problem is proxy_moderate even though its p_correct
        # (0.8) would be proxy_easy if ranked against skill-b's problems.
        self.assertEqual(assigned["a2"], "proxy_moderate")
        self.assertEqual(assigned["b1"], "proxy_easy")

    def test_fewer_than_three_problems_is_rejected(self) -> None:
        with self.assertRaises(ProxyTierError):
            assign_within_skill_tiers(
                [problem("p1", "skill-a", 0.9), problem("p2", "skill-a", 0.5)]
            )


class SkillCatalogGateTests(unittest.TestCase):
    def test_skill_with_under_nine_calibrated_problems_fails(self) -> None:
        result = evaluate_skill_catalog(
            "skill-a",
            {"proxy_easy": 2, "proxy_moderate": 2, "proxy_hard": 2},
        )
        self.assertEqual(result.calibrated_problem_count, 6)
        self.assertEqual(result.skill_proxy_status, "insufficient_skill_catalog")

    def test_skill_with_under_three_in_a_tier_fails(self) -> None:
        result = evaluate_skill_catalog(
            "skill-a",
            {"proxy_easy": 8, "proxy_moderate": 2, "proxy_hard": 2},
        )
        self.assertGreaterEqual(result.calibrated_problem_count, SKILL_CATALOG_MINIMUM_PROBLEMS)
        self.assertEqual(result.skill_proxy_status, "insufficient_skill_catalog")

    def test_full_three_tier_catalog_passes(self) -> None:
        result = evaluate_skill_catalog(
            "skill-a",
            {"proxy_easy": 3, "proxy_moderate": 3, "proxy_hard": 3},
        )
        self.assertEqual(result.calibrated_problem_count, 9)
        self.assertEqual(result.skill_proxy_status, "sufficient_skill_catalog")

    def test_gate_constants_match_the_frozen_contract(self) -> None:
        self.assertEqual(SKILL_CATALOG_MINIMUM_PROBLEMS, 9)
        self.assertEqual(SKILL_CATALOG_MINIMUM_PER_TIER, 3)

    def test_summary_counts_catalog_statuses(self) -> None:
        results = [
            evaluate_skill_catalog(
                "skill-a", {"proxy_easy": 3, "proxy_moderate": 3, "proxy_hard": 3}
            ),
            evaluate_skill_catalog(
                "skill-b", {"proxy_easy": 1, "proxy_moderate": 1, "proxy_hard": 1}
            ),
        ]
        summary = summarize_skill_catalogs(results)
        self.assertEqual(summary["skillsWithCalibratedProblems"], 2)
        self.assertEqual(summary["skillsFullThreeTierEligible"], 1)
        self.assertEqual(summary["skillsInsufficientCatalog"], 1)


if __name__ == "__main__":
    unittest.main()
