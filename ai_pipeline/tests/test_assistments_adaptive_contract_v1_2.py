"""AQC-E3A contract-v1.2 tests (attempt purity denominator clarification).

v1.2 freezes ONLY the attempt proxy-difficulty purity denominator:
proxyDifficultyPurity = dominantTierCount / validProblemCount over ALL valid
graded problems, with untiered problems remaining in the denominator and
contributing to no tier numerator, and dominant-tier ties failing closed.
These tests prove the amendment, v1/v1.1 preservation, unchanged non-purity
rules, fail-closed tamper rejection, and the no-policy boundary.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

import yaml

from external_data.assistments.adaptive.external_policy_contract import (
    EXTERNAL_ADAPTIVE_CONTRACT_V1_1_VERSION,
    EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION,
    EXTERNAL_ADAPTIVE_CONTRACT_VERSION,
    ExternalContractError,
    load_external_adaptive_contract,
)


AI_PIPELINE = Path(__file__).resolve().parents[1]
ADAPTIVE_DIR = AI_PIPELINE / "external_data" / "assistments" / "adaptive"
V1_PATH = ADAPTIVE_DIR / "assistments_adaptive_contract_v1.yaml"
V1_1_PATH = ADAPTIVE_DIR / "assistments_adaptive_contract_v1_1.yaml"
V1_2_PATH = ADAPTIVE_DIR / "assistments_adaptive_contract_v1_2.yaml"


class ContractV1_2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v1 = load_external_adaptive_contract(V1_PATH)
        self.v1_1 = load_external_adaptive_contract(
            V1_1_PATH, version=EXTERNAL_ADAPTIVE_CONTRACT_V1_1_VERSION
        )
        self.v1_2 = load_external_adaptive_contract(
            V1_2_PATH, version=EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION
        )

    def test_version_hash_and_predecessor_binding(self) -> None:
        self.assertEqual(self.v1_2.contract_version, "assistments-adaptive-contract-v1.2")
        self.assertEqual(len(self.v1_2.contract_sha256), 64)
        self.assertEqual(
            self.v1_2.predecessor_contract_version,
            self.v1_1.contract_version,
        )
        self.assertEqual(
            self.v1_2.predecessor_contract_sha256,
            self.v1_1.contract_sha256,
        )

    def test_amendment_reason_scope_and_rationale(self) -> None:
        self.assertEqual(
            self.v1_2.amendment_reason,
            "attempt_proxy_difficulty_purity_denominator_clarification",
        )
        loaded = yaml.safe_load(V1_2_PATH.read_text(encoding="utf-8"))
        amendment = loaded["amendment"]
        self.assertEqual(amendment["scope"], "attempt_purity_denominator_only")
        self.assertTrue(amendment["fixesUnderspecifiedImplementationDetail"])
        self.assertFalse(amendment["motivatedByPolicyPerformance"])
        self.assertFalse(amendment["policyResultsExistedBeforeAmendment"])
        self.assertTrue(amendment["v1Preserved"])
        self.assertTrue(amendment["v1_1Preserved"])

    def test_purity_denominator_rule_is_frozen(self) -> None:
        rule = self.v1_2.purity_denominator_rule
        self.assertIsNotNone(rule)
        self.assertEqual(rule["proxyDifficultyPurity"], "dominantTierCount / validProblemCount")
        self.assertEqual(rule["dominantTierCount"], "max(easyCount, moderateCount, hardCount)")
        untiered = rule["untieredProblems"]
        self.assertTrue(untiered["remainInValidProblemCount"])
        self.assertTrue(untiered["contributeToNoTierCount"])
        self.assertTrue(untiered["neverInventedTier"])
        self.assertTrue(untiered["neverDroppedToIncreasePurity"])
        self.assertTrue(untiered["purityIsNeverDominantOverTieredOnlyCount"])
        ties = rule["dominantTierTies"]
        self.assertIn("no unique dominant tier", ties["rule"])
        self.assertEqual(ties["censorOrAuditReason"], "mixed_proxy_difficulty")

    def test_purity_examples_are_frozen(self) -> None:
        examples = self.v1_2.purity_denominator_rule["examples"]
        self.assertIn("4 Easy / 0 untiered -> purity 4/4 -> proxy_easy", examples.values())
        self.assertIn("4 Easy / 1 Moderate -> purity 4/5 -> proxy_easy", examples.values())
        self.assertIn(
            "4 Easy / 1 Moderate / 2 untiered -> purity 4/7 -> below 2/3 -> null",
            examples.values(),
        )
        self.assertIn("5 Easy / 2 untiered -> purity 5/7 -> proxy_easy", examples.values())
        self.assertIn("1 Easy / 6 untiered -> purity 1/7 -> null", examples.values())
        self.assertIn("0 tiered / 3 untiered -> purity 0/3 -> null", examples.values())
        self.assertIn(
            "equal dominant tier counts -> no arbitrary tier selection -> null",
            examples.values(),
        )

    def test_v1_and_v1_1_history_is_preserved(self) -> None:
        loaded = yaml.safe_load(V1_2_PATH.read_text(encoding="utf-8"))
        history = loaded["predecessorContracts"]["externalAdaptiveContracts"]
        self.assertEqual(
            history["v1"],
            {
                "contractVersion": self.v1.contract_version,
                "contractSha256": self.v1.contract_sha256,
            },
        )
        self.assertEqual(
            history["v1_1"],
            {
                "contractVersion": self.v1_1.contract_version,
                "contractSha256": self.v1_1.contract_sha256,
            },
        )

    def test_every_non_purity_v1_1_rule_is_unchanged(self) -> None:
        pairs = [
            ("provenance", self.v1_1.provenance, self.v1_2.provenance),
            ("calibration_window", self.v1_1.calibration_window, self.v1_2.calibration_window),
            ("evaluation_window", self.v1_1.evaluation_window, self.v1_2.evaluation_window),
            (
                "minimum_calibration_learners",
                self.v1_1.minimum_calibration_learners,
                self.v1_2.minimum_calibration_learners,
            ),
            (
                "tertile_boundary_rule",
                self.v1_1.tertile_boundary_rule,
                self.v1_2.tertile_boundary_rule,
            ),
            (
                "attempt_purity_threshold",
                self.v1_1.attempt_purity_threshold,
                self.v1_2.attempt_purity_threshold,
            ),
            (
                "skill_catalog_minimum_calibrated_problems",
                self.v1_1.skill_catalog_minimum_calibrated_problems,
                self.v1_2.skill_catalog_minimum_calibrated_problems,
            ),
            (
                "skill_catalog_minimum_per_tier",
                self.v1_1.skill_catalog_minimum_per_tier,
                self.v1_2.skill_catalog_minimum_per_tier,
            ),
            ("replay_mode", self.v1_1.replay_mode, self.v1_2.replay_mode),
            (
                "reversal_history_source",
                self.v1_1.reversal_history_source,
                self.v1_2.reversal_history_source,
            ),
            (
                "allowed_claim_levels",
                self.v1_1.allowed_claim_levels,
                self.v1_2.allowed_claim_levels,
            ),
            (
                "production_promotion_allowed",
                self.v1_1.production_promotion_allowed,
                self.v1_2.production_promotion_allowed,
            ),
            (
                "adaptive_policy_sha256",
                self.v1_1.adaptive_policy_sha256,
                self.v1_2.adaptive_policy_sha256,
            ),
            (
                "policy_evaluation_sha256",
                self.v1_1.policy_evaluation_sha256,
                self.v1_2.policy_evaluation_sha256,
            ),
            ("bkt_version", self.v1_1.bkt_version, self.v1_2.bkt_version),
        ]
        for label, before, after in pairs:
            self.assertEqual(before, after, label)

    def test_tampered_purity_rule_is_rejected(self) -> None:
        original = yaml.safe_load(V1_2_PATH.read_text(encoding="utf-8"))
        variants = []
        changed_formula = deepcopy(original)
        changed_formula["attemptTier"]["purityDenominatorRule"][
            "proxyDifficultyPurity"
        ] = "dominantTierCount / tieredProblemCount"
        variants.append(changed_formula)
        dropped_untiered = deepcopy(original)
        dropped_untiered["attemptTier"]["purityDenominatorRule"]["untieredProblems"][
            "remainInValidProblemCount"
        ] = False
        variants.append(dropped_untiered)
        arbitrary_tie = deepcopy(original)
        arbitrary_tie["attemptTier"]["purityDenominatorRule"]["dominantTierTies"][
            "rule"
        ] = "pick the first tier alphabetically"
        variants.append(arbitrary_tie)
        wrong_predecessor = deepcopy(original)
        wrong_predecessor["predecessorContractVersion"] = "assistments-adaptive-contract-v1"
        variants.append(wrong_predecessor)
        wrong_reason = deepcopy(original)
        wrong_reason["amendment"]["reason"] = "coverage_optimization"
        variants.append(wrong_reason)
        with tempfile.TemporaryDirectory() as directory:
            for index, variant in enumerate(variants):
                path = Path(directory) / f"invalid-{index}.yaml"
                path.write_text(yaml.safe_dump(variant, sort_keys=False), encoding="utf-8")
                with self.subTest(index=index), self.assertRaises(ExternalContractError):
                    load_external_adaptive_contract(
                        path, version=EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION
                    )


class NoPolicyBoundaryTests(unittest.TestCase):
    def test_amendment_path_never_invokes_policy_selectors(self) -> None:
        for filename in (
            "assistments_adaptive_contract_v1_2.yaml",
            "external_policy_contract.py",
            "adaptive_attempts.py",
            "run_adaptive_attempt_reconstruction.py",
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
