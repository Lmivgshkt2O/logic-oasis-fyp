"""AQC-E2.1 contract-amendment tests (assistments-adaptive-contract-v1.1).

The amendment freezes ONLY the deterministic discrete within-skill tertile
boundary rule (b1 = floor(n/3), b2 = floor(2n/3)).  These tests prove the
boundary partition for non-divisible counts, deterministic ordering and ties,
per-skill independence, v1 predecessor preservation, unchanged non-boundary
rules, and the no-policy boundary of the amended E2 path.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import yaml

from external_data.assistments.adaptive.external_policy_contract import (
    EXTERNAL_ADAPTIVE_CONTRACT_V1_1_VERSION,
    EXTERNAL_ADAPTIVE_CONTRACT_VERSION,
    ExternalContractError,
    load_external_adaptive_contract,
)
from external_data.assistments.adaptive.proxy_tiers import (
    CalibratedProblem,
    TERTILE_BOUNDARY_RULE,
    evaluate_skill_catalog,
    assign_within_skill_tiers,
    tertile_boundaries,
    tier_counts_by_tier,
)


AI_PIPELINE = Path(__file__).resolve().parents[1]
ADAPTIVE_DIR = AI_PIPELINE / "external_data" / "assistments" / "adaptive"
V1_PATH = ADAPTIVE_DIR / "assistments_adaptive_contract_v1.yaml"
V1_1_PATH = ADAPTIVE_DIR / "assistments_adaptive_contract_v1_1.yaml"


def problems_in_one_skill(n: int) -> list[CalibratedProblem]:
    """n distinct-p_correct problems in one skill, p descending by construction."""
    return [
        CalibratedProblem(
            external_problem_key=f"p-{index:02d}",
            source_skill_code="6.NS.A.1",
            p_correct=0.99 - index * 0.01,
        )
        for index in range(n)
    ]


class TertileBoundaryTests(unittest.TestCase):
    def test_boundaries_use_floor_n3_and_floor_2n3(self) -> None:
        for n in (3, 9, 10, 11, 12, 13, 30):
            b1, b2 = tertile_boundaries(n)
            self.assertEqual(b1, n // 3)
            self.assertEqual(b2, (2 * n) // 3)
        self.assertEqual(TERTILE_BOUNDARY_RULE, {"b1": "floor(n / 3)", "b2": "floor(2 * n / 3)"})

    def test_n9_is_three_three_three(self) -> None:
        assigned = assign_within_skill_tiers(problems_in_one_skill(9))
        self.assertEqual(
            tier_counts_by_tier(assigned),
            {"proxy_easy": 3, "proxy_moderate": 3, "proxy_hard": 3},
        )

    def test_n10_is_three_three_four(self) -> None:
        assigned = assign_within_skill_tiers(problems_in_one_skill(10))
        self.assertEqual(
            tier_counts_by_tier(assigned),
            {"proxy_easy": 3, "proxy_moderate": 3, "proxy_hard": 4},
        )

    def test_n11_is_three_four_four(self) -> None:
        assigned = assign_within_skill_tiers(problems_in_one_skill(11))
        self.assertEqual(
            tier_counts_by_tier(assigned),
            {"proxy_easy": 3, "proxy_moderate": 4, "proxy_hard": 4},
        )

    def test_n12_is_four_four_four(self) -> None:
        assigned = assign_within_skill_tiers(problems_in_one_skill(12))
        self.assertEqual(
            tier_counts_by_tier(assigned),
            {"proxy_easy": 4, "proxy_moderate": 4, "proxy_hard": 4},
        )

    def test_rank_partition_matches_v1_1_examples(self) -> None:
        examples = {
            9: (3, 3, 3),
            10: (3, 3, 4),
            11: (3, 4, 4),
            12: (4, 4, 4),
        }
        for n, expected in examples.items():
            assigned = assign_within_skill_tiers(problems_in_one_skill(n))
            counts = tier_counts_by_tier(assigned)
            self.assertEqual(
                (counts["proxy_easy"], counts["proxy_moderate"], counts["proxy_hard"]),
                expected,
                f"n={n}",
            )


class DeterministicTierTests(unittest.TestCase):
    def test_sorting_is_p_correct_descending_then_key_ascending(self) -> None:
        problems = [
            CalibratedProblem("p-b", "skill-x", 0.50),
            CalibratedProblem("p-a", "skill-x", 0.90),
            CalibratedProblem("p-c", "skill-x", 0.10),
            CalibratedProblem("p-e", "skill-x", 0.40),
            CalibratedProblem("p-d", "skill-x", 0.30),
            CalibratedProblem("p-f", "skill-x", 0.20),
            CalibratedProblem("p-i", "skill-x", 0.05),
            CalibratedProblem("p-h", "skill-x", 0.07),
            CalibratedProblem("p-g", "skill-x", 0.08),
        ]
        assigned = assign_within_skill_tiers(problems)
        # Sorted by p_correct descending: p-a (0.90), p-b (0.50), p-e (0.40),
        # p-d (0.30), p-f (0.20), p-c (0.10), p-g (0.08), p-h (0.07), p-i (0.05).
        # n=9 -> easy ranks 1..3, moderate 4..6, hard 7..9.
        self.assertEqual(assigned["p-a"], "proxy_easy")
        self.assertEqual(assigned["p-b"], "proxy_easy")
        self.assertEqual(assigned["p-e"], "proxy_easy")
        self.assertEqual(assigned["p-d"], "proxy_moderate")
        self.assertEqual(assigned["p-c"], "proxy_moderate")
        self.assertEqual(assigned["p-i"], "proxy_hard")

    def test_tied_p_correct_is_deterministic_by_key_ascending(self) -> None:
        tied = [
            CalibratedProblem("p-2", "skill-t", 0.50),
            CalibratedProblem("p-1", "skill-t", 0.50),
            CalibratedProblem("p-3", "skill-t", 0.50),
            CalibratedProblem("p-5", "skill-t", 0.50),
            CalibratedProblem("p-4", "skill-t", 0.50),
            CalibratedProblem("p-6", "skill-t", 0.50),
            CalibratedProblem("p-8", "skill-t", 0.50),
            CalibratedProblem("p-7", "skill-t", 0.50),
            CalibratedProblem("p-9", "skill-t", 0.50),
        ]
        first = assign_within_skill_tiers(tied)
        second = assign_within_skill_tiers(tied)
        self.assertEqual(first, second)
        self.assertEqual(first["p-1"], "proxy_easy")
        self.assertEqual(first["p-2"], "proxy_easy")
        self.assertEqual(first["p-3"], "proxy_easy")
        self.assertEqual(first["p-9"], "proxy_hard")

    def test_different_skills_are_partitioned_independently(self) -> None:
        skill_a = problems_in_one_skill(10)
        skill_b = [
            CalibratedProblem(f"q-{index:02d}", "6.EE.B.7", 0.99 - index * 0.01)
            for index in range(12)
        ]
        only_a = assign_within_skill_tiers(skill_a)
        both = assign_within_skill_tiers(skill_a + skill_b)
        self.assertEqual({key: both[key] for key in only_a}, only_a)
        b_counts = tier_counts_by_tier({key: tier for key, tier in both.items() if key.startswith("q-")})
        self.assertEqual(
            (b_counts["proxy_easy"], b_counts["proxy_moderate"], b_counts["proxy_hard"]),
            (4, 4, 4),
        )

    def test_no_global_ranking_occurs(self) -> None:
        low_skill = [
            CalibratedProblem("l-1", "skill-low", 0.30),
            CalibratedProblem("l-2", "skill-low", 0.25),
            CalibratedProblem("l-3", "skill-low", 0.20),
            CalibratedProblem("l-4", "skill-low", 0.15),
            CalibratedProblem("l-5", "skill-low", 0.10),
            CalibratedProblem("l-6", "skill-low", 0.08),
            CalibratedProblem("l-7", "skill-low", 0.06),
            CalibratedProblem("l-8", "skill-low", 0.04),
            CalibratedProblem("l-9", "skill-low", 0.02),
        ]
        high_skill = [
            CalibratedProblem("h-1", "skill-high", 0.95),
            CalibratedProblem("h-2", "skill-high", 0.94),
            CalibratedProblem("h-3", "skill-high", 0.93),
            CalibratedProblem("h-4", "skill-high", 0.92),
            CalibratedProblem("h-5", "skill-high", 0.91),
            CalibratedProblem("h-6", "skill-high", 0.90),
            CalibratedProblem("h-7", "skill-high", 0.89),
            CalibratedProblem("h-8", "skill-high", 0.88),
            CalibratedProblem("h-9", "skill-high", 0.87),
        ]
        assigned = assign_within_skill_tiers(low_skill + high_skill)
        # A globally ranked scheme would put h-1..h-3 in proxy_easy and would
        # push low-skill problems into proxy_hard. Within-skill ranking gives
        # each skill its own easy/moderate/hard split.
        self.assertEqual(assigned["l-1"], "proxy_easy")
        self.assertEqual(assigned["l-5"], "proxy_moderate")
        self.assertEqual(assigned["l-9"], "proxy_hard")
        self.assertEqual(assigned["h-1"], "proxy_easy")

    def test_same_input_produces_identical_tiers_and_hash(self) -> None:
        problems = problems_in_one_skill(11)
        first = assign_within_skill_tiers(problems)
        second = assign_within_skill_tiers(problems)

        def canonical_hash(mapping: dict[str, str]) -> str:
            payload = json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode("utf-8")
            return hashlib.sha256(payload).hexdigest()

        self.assertEqual(first, second)
        self.assertEqual(canonical_hash(first), canonical_hash(second))

    def test_skill_below_three_calibrated_problems_gets_no_tiers(self) -> None:
        assigned = assign_within_skill_tiers(
            [
                CalibratedProblem("p1", "skill-tiny", 0.9),
                CalibratedProblem("p2", "skill-tiny", 0.5),
            ]
        )
        self.assertEqual(assigned, {})
        result = evaluate_skill_catalog(
            "skill-tiny",
            {"proxy_easy": 0, "proxy_moderate": 0, "proxy_hard": 0},
        )
        self.assertEqual(result.skill_proxy_status, "insufficient_skill_catalog")


class ContractAmendmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.v1 = load_external_adaptive_contract(V1_PATH)
        self.v1_1 = load_external_adaptive_contract(
            V1_1_PATH, version=EXTERNAL_ADAPTIVE_CONTRACT_V1_1_VERSION
        )

    def test_v1_predecessor_is_preserved(self) -> None:
        self.assertEqual(self.v1.contract_version, EXTERNAL_ADAPTIVE_CONTRACT_VERSION)
        self.assertEqual(
            self.v1_1.predecessor_contract_version,
            self.v1.contract_version,
        )
        self.assertEqual(
            self.v1_1.predecessor_contract_sha256,
            self.v1.contract_sha256,
        )

    def test_amendment_reason_and_scope_are_frozen(self) -> None:
        self.assertEqual(
            self.v1_1.amendment_reason,
            "deterministic_discrete_tertile_boundary_clarification",
        )
        loaded = yaml.safe_load(V1_1_PATH.read_text(encoding="utf-8"))
        amendment = loaded["amendment"]
        self.assertEqual(amendment["scope"], "within_skill_tertile_boundaries_only")
        self.assertTrue(amendment["fixesUnderspecifiedImplementationDetail"])
        self.assertFalse(amendment["motivatedByPolicyPerformance"])
        self.assertFalse(amendment["policyResultsExistedBeforeAmendment"])
        self.assertTrue(amendment["v1Preserved"])

    def test_every_non_boundary_v1_rule_is_unchanged(self) -> None:
        pairs = [
            ("provenance", self.v1.provenance, self.v1_1.provenance),
            ("dataset_release_id", self.v1.dataset_release_id, self.v1_1.dataset_release_id),
            ("evidence_mode", self.v1.evidence_mode, self.v1_1.evidence_mode),
            ("calibration_window", self.v1.calibration_window, self.v1_1.calibration_window),
            ("evaluation_window", self.v1.evaluation_window, self.v1_1.evaluation_window),
            (
                "minimum_calibration_learners",
                self.v1.minimum_calibration_learners,
                self.v1_1.minimum_calibration_learners,
            ),
            (
                "proxy_difficulty_values",
                self.v1.proxy_difficulty_values,
                self.v1_1.proxy_difficulty_values,
            ),
            (
                "skill_catalog_minimum_calibrated_problems",
                self.v1.skill_catalog_minimum_calibrated_problems,
                self.v1_1.skill_catalog_minimum_calibrated_problems,
            ),
            (
                "skill_catalog_minimum_per_tier",
                self.v1.skill_catalog_minimum_per_tier,
                self.v1_1.skill_catalog_minimum_per_tier,
            ),
            (
                "attempt_purity_threshold",
                self.v1.attempt_purity_threshold,
                self.v1_1.attempt_purity_threshold,
            ),
            ("replay_mode", self.v1.replay_mode, self.v1_1.replay_mode),
            (
                "reversal_history_source",
                self.v1.reversal_history_source,
                self.v1_1.reversal_history_source,
            ),
            (
                "allowed_claim_levels",
                self.v1.allowed_claim_levels,
                self.v1_1.allowed_claim_levels,
            ),
            (
                "forbidden_claim_levels",
                self.v1.forbidden_claim_levels,
                self.v1_1.forbidden_claim_levels,
            ),
            (
                "production_promotion_allowed",
                self.v1.production_promotion_allowed,
                self.v1_1.production_promotion_allowed,
            ),
            (
                "contains_raw_identifiers",
                self.v1.contains_raw_identifiers,
                self.v1_1.contains_raw_identifiers,
            ),
            (
                "adaptive_policy_sha256",
                self.v1.adaptive_policy_sha256,
                self.v1_1.adaptive_policy_sha256,
            ),
            (
                "policy_evaluation_sha256",
                self.v1.policy_evaluation_sha256,
                self.v1_1.policy_evaluation_sha256,
            ),
            ("bkt_version", self.v1.bkt_version, self.v1_1.bkt_version),
        ]
        for label, v1_value, v1_1_value in pairs:
            self.assertEqual(v1_value, v1_1_value, label)

    def test_v1_contract_still_loads_unchanged(self) -> None:
        self.assertEqual(self.v1.contract_version, EXTERNAL_ADAPTIVE_CONTRACT_VERSION)
        self.assertIsNone(self.v1.predecessor_contract_version)
        self.assertIsNone(self.v1.amendment_reason)

    def test_tampered_boundary_rule_is_rejected(self) -> None:
        original = yaml.safe_load(V1_1_PATH.read_text(encoding="utf-8"))
        variants = []
        changed_b1 = deepcopy(original)
        changed_b1["proxyDifficulty"]["withinSkillTiering"]["tertileBoundaryRule"]["b1"] = "ceil(n / 3)"
        variants.append(changed_b1)
        changed_example = deepcopy(original)
        changed_example["proxyDifficulty"]["withinSkillTiering"]["tertileBoundaryRule"]["examples"][
            "n10"
        ] = {"proxy_easy": 4, "proxy_moderate": 3, "proxy_hard": 3}
        variants.append(changed_example)
        changed_predecessor = deepcopy(original)
        changed_predecessor["predecessorContractSha256"] = "not-a-hash"
        variants.append(changed_predecessor)
        result_driven = deepcopy(original)
        result_driven["amendment"]["motivatedByPolicyPerformance"] = True
        variants.append(result_driven)
        with tempfile.TemporaryDirectory() as directory:
            for index, variant in enumerate(variants):
                path = Path(directory) / f"invalid-{index}.yaml"
                path.write_text(yaml.safe_dump(variant, sort_keys=False), encoding="utf-8")
                with self.subTest(index=index), self.assertRaises(ExternalContractError):
                    load_external_adaptive_contract(
                        path, version=EXTERNAL_ADAPTIVE_CONTRACT_V1_1_VERSION
                    )


class NoPolicyBoundaryTests(unittest.TestCase):
    def test_amendment_path_never_invokes_policy_selectors(self) -> None:
        for filename in (
            "assistments_adaptive_contract_v1_1.yaml",
            "external_policy_contract.py",
            "proxy_tiers.py",
            "run_difficulty_calibration.py",
        ):
            source = (ADAPTIVE_DIR / filename).read_text(encoding="utf-8")
            for forbidden in (
                "select_policy_decision",
                "PolicyArm",
                "DecisionDirection",
                "false_promotion",
            ):
                self.assertNotIn(forbidden, source, f"{filename} must not reference {forbidden}")

    def test_native_aqc_contracts_still_validate(self) -> None:
        from logic_oasis_ai.adaptive_policy import load_adaptive_policy_config
        from logic_oasis_ai.policy_evaluation import load_policy_evaluation_manifest

        configs = AI_PIPELINE / "configs"
        adaptive = load_adaptive_policy_config(configs / "adaptive_policy_v1.yaml")
        manifest = load_policy_evaluation_manifest(
            configs / "policy_evaluation_v1.yaml", adaptive_policy=adaptive
        )
        self.assertEqual(manifest.manifest_version, "policy-evaluation-v1")


if __name__ == "__main__":
    unittest.main()
