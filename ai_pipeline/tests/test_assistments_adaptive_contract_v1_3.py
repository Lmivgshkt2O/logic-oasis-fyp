"""AQC-E6A contract-v1.3 statistical reporting freeze tests.

v1.3 freezes ONLY the student-clustered bootstrap configuration, the sparse-CI
guard, and BKT calibration reporting needed for E6 outcome analysis.  These
tests prove the frozen statistical configuration, unchanged matching/censoring
rules, unchanged outcome contract, and the no-outcome-values-before-amendment
boundary.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

import yaml

from external_data.assistments.adaptive.external_policy_contract import (
    EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION,
    EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION,
    ExternalContractError,
    load_external_adaptive_contract,
)


AI_PIPELINE = Path(__file__).resolve().parents[1]
ADAPTIVE_DIR = AI_PIPELINE / "external_data" / "assistments" / "adaptive"
V1_2_PATH = ADAPTIVE_DIR / "assistments_adaptive_contract_v1_2.yaml"
V1_3_PATH = ADAPTIVE_DIR / "assistments_adaptive_contract_v1_3.yaml"


class ContractV1_3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v1_2 = load_external_adaptive_contract(
            V1_2_PATH, version=EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION
        )
        self.v1_3 = load_external_adaptive_contract(
            V1_3_PATH, version=EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION
        )
        self.bootstrap = self.v1_3.statistical_reporting["studentClusteredBootstrap"]

    def test_bootstrap_unit_is_external_student_key(self) -> None:
        self.assertEqual(self.bootstrap["bootstrapUnit"], "externalStudentKey")

    def test_2000_resamples_frozen(self) -> None:
        self.assertEqual(self.bootstrap["bootstrapResamples"], 2000)

    def test_seed_is_frozen(self) -> None:
        self.assertEqual(self.bootstrap["bootstrapSeed"], 20260716)

    def test_confidence_level_is_0_95(self) -> None:
        self.assertEqual(float(self.bootstrap["confidenceLevel"]), 0.95)

    def test_percentile_method_frozen(self) -> None:
        self.assertEqual(self.bootstrap["intervalMethod"], "percentile")

    def test_learners_sampled_with_replacement(self) -> None:
        self.assertEqual(
            self.bootstrap["resamplingMethod"],
            "learner_cluster_with_replacement",
        )

    def test_rows_of_sampled_learner_remain_together(self) -> None:
        self.assertTrue(self.bootstrap["neverSplitLearnerRowsAcrossBootstrapUnits"])

    def test_rows_never_independently_bootstrapped(self) -> None:
        self.assertTrue(self.bootstrap["neverResampleRowsIndependently"])

    def test_same_configuration_for_all_policies(self) -> None:
        self.assertTrue(self.bootstrap["sameConfigurationForAllPolicies"])

    def test_no_policy_difference_superiority_interval(self) -> None:
        self.assertTrue(self.bootstrap["noPolicyDifferenceSuperiorityInterval"])

    def test_sparse_ci_guard_is_frozen(self) -> None:
        guard = self.v1_3.statistical_reporting["ciSparsityGuard"]
        self.assertEqual(guard["minimumIndependentLearnersForCI"], 10)
        self.assertEqual(guard["sparseFlag"], "sparse_independent_learner_evidence")
        self.assertTrue(guard["projectDefinedConservativeDescriptiveGuard"])
        self.assertTrue(guard["notAUniversalStatisticalTheorem"])

    def test_bkt_calibration_bands_frozen_before_outcomes(self) -> None:
        calibration = self.v1_3.statistical_reporting["bktCalibration"]
        self.assertEqual(calibration["bandSource"], "aqc3_reliability_curve")
        self.assertEqual(
            calibration["bands"],
            [
                {"lower": 0.00, "upper": 0.20, "upperInclusive": False},
                {"lower": 0.20, "upper": 0.40, "upperInclusive": False},
                {"lower": 0.40, "upper": 0.60, "upperInclusive": False},
                {"lower": 0.60, "upper": 0.80, "upperInclusive": False},
                {"lower": 0.80, "upper": 1.00, "upperInclusive": True},
            ],
        )

    def test_one_point_zero_belongs_to_highest_band(self) -> None:
        calibration = self.v1_3.statistical_reporting["bktCalibration"]
        self.assertTrue(calibration["onePointZeroBelongsToHighestBand"])
        self.assertTrue(calibration["bands"][-1]["upperInclusive"])

    def test_mastery_criterion_remains_0_60(self) -> None:
        contract = self.v1_3.statistical_reporting["outcomeContractUnchanged"]
        self.assertEqual(contract["masteryCriterion"], 0.60)
        self.assertTrue(contract["adaptiveScoreThresholdNotOutcomeCriterion"])

    def test_v1_2_matching_and_censoring_rules_unchanged(self) -> None:
        self.assertEqual(
            self.v1_3.purity_denominator_rule,
            self.v1_2.purity_denominator_rule,
        )
        self.assertEqual(
            self.v1_3.tertile_boundary_rule,
            self.v1_2.tertile_boundary_rule,
        )
        self.assertEqual(self.v1_3.censor_reasons, self.v1_2.censor_reasons)

    def test_amendment_reason_and_no_outcome_values_before_amendment(self) -> None:
        self.assertEqual(
            self.v1_3.amendment_reason,
            "external_stage_b_descriptive_cluster_bootstrap_and_calibration_reporting_freeze",
        )
        loaded = yaml.safe_load(V1_3_PATH.read_text(encoding="utf-8"))
        amendment = loaded["amendment"]
        self.assertFalse(amendment["outcomeValuesInspectedBeforeAmendment"])
        self.assertFalse(amendment["policyOutcomeRatesExistedBeforeAmendment"])
        self.assertFalse(amendment["motivatedByPolicyPerformance"])
        self.assertTrue(amendment["v1_2Preserved"])

    def test_predecessor_binding_and_history(self) -> None:
        self.assertEqual(
            self.v1_3.predecessor_contract_sha256,
            self.v1_2.contract_sha256,
        )
        loaded = yaml.safe_load(V1_3_PATH.read_text(encoding="utf-8"))
        history = loaded["predecessorContracts"]["externalAdaptiveContracts"]
        self.assertEqual(history["v1_2"]["contractSha256"], self.v1_2.contract_sha256)

    def test_tampered_statistical_config_is_rejected(self) -> None:
        original = yaml.safe_load(V1_3_PATH.read_text(encoding="utf-8"))
        variants = []
        changed_seed = deepcopy(original)
        changed_seed["statisticalReporting"]["studentClusteredBootstrap"]["bootstrapSeed"] = 1
        variants.append(changed_seed)
        changed_ci = deepcopy(original)
        changed_ci["statisticalReporting"]["ciSparsityGuard"]["minimumIndependentLearnersForCI"] = 5
        variants.append(changed_ci)
        changed_band = deepcopy(original)
        changed_band["statisticalReporting"]["bktCalibration"]["bands"][-1]["upperInclusive"] = False
        variants.append(changed_band)
        outcome_seen = deepcopy(original)
        outcome_seen["amendment"]["outcomeValuesInspectedBeforeAmendment"] = True
        variants.append(outcome_seen)
        with tempfile.TemporaryDirectory() as directory:
            for index, variant in enumerate(variants):
                path = Path(directory) / f"invalid-{index}.yaml"
                path.write_text(yaml.safe_dump(variant, sort_keys=False), encoding="utf-8")
                with self.subTest(index=index), self.assertRaises(ExternalContractError):
                    load_external_adaptive_contract(
                        path, version=EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION
                    )


class NoPolicyBoundaryTests(unittest.TestCase):
    def test_amendment_path_never_invokes_policy_selectors(self) -> None:
        source = (ADAPTIVE_DIR / "external_policy_contract.py").read_text(encoding="utf-8")
        for forbidden in ("select_policy_decision", "PolicyArm", "DecisionDirection"):
            self.assertNotIn(forbidden, source)

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
