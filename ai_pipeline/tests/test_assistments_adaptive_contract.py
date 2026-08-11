"""AQC-E1 frozen external adaptive contract tests (ASSISTments Stage B).

These tests prove the contract freeze only: provenance, time separation,
thresholds, replay semantics, censoring vocabulary, claim levels, and the
unchanged shared P1/P2/P3a binding. No calibration and no policy replay are
performed anywhere in this module.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

import yaml

from logic_oasis_ai.adaptive_policy import Difficulty, load_adaptive_policy_config
from logic_oasis_ai.bkt import BKT_MODEL_VERSION
from logic_oasis_ai.policy_evaluation import (
    P1_PROMOTION_THRESHOLD,
    P2_DEMOTION_THRESHOLD,
    load_policy_evaluation_manifest,
)

from external_data.assistments.adaptive.external_policy_contract import (
    EXTERNAL_ADAPTIVE_CONTRACT_VERSION,
    ExternalContractError,
    load_external_adaptive_contract,
    verify_frozen_policy_hashes,
    verify_shared_aqc_constants,
)
from external_data.assistments.adaptive.schemas import (
    ATTEMPT_PURITY_THRESHOLD,
    CALIBRATION_WINDOW_END,
    CALIBRATION_WINDOW_START,
    EVALUATION_WINDOW_END,
    EVALUATION_WINDOW_START,
    EXTERNAL_CANDIDATE_KEY_NAMESPACE,
    EXTERNAL_PROVENANCE,
    MINIMUM_CALIBRATION_LEARNERS,
    PRODUCTION_PROMOTION_ALLOWED,
    PROXY_DIFFICULTY_VALUES,
    REPLAY_MODE,
    REQUIRED_CENSOR_REASONS,
    REVERSAL_HISTORY_SOURCE,
    SKILL_CATALOG_MINIMUM_CALIBRATED_PROBLEMS,
    SKILL_CATALOG_MINIMUM_PER_TIER,
    CONTAINS_RAW_IDENTIFIERS,
    CandidateKind,
    ExternalClaimLevel,
    EvaluationDifficultyOption,
    ExternalProblemDifficultyV1,
    ExternalAdaptiveAttemptV1,
    ProxyDifficulty,
    difficulty_score,
    external_proxy_candidate,
    in_calibration_window,
    in_evaluation_window,
    problem_set_fingerprint,
    smoothed_correct_probability,
    validate_provenance_external_real,
    windows_do_not_overlap,
)


AI_PIPELINE = Path(__file__).resolve().parents[1]
CONFIGS = AI_PIPELINE / "configs"
ADAPTIVE_POLICY_PATH = CONFIGS / "adaptive_policy_v1.yaml"
POLICY_EVALUATION_PATH = CONFIGS / "policy_evaluation_v1.yaml"
CONTRACT_PATH = (
    AI_PIPELINE
    / "external_data"
    / "assistments"
    / "adaptive"
    / "assistments_adaptive_contract_v1.yaml"
)


class ContractFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_external_adaptive_contract(CONTRACT_PATH)
        verify_frozen_policy_hashes(cls.contract, CONFIGS)
        verify_shared_aqc_constants(cls.contract)

    def test_contract_version_and_sha_are_frozen(self) -> None:
        self.assertEqual(
            self.contract.contract_version,
            EXTERNAL_ADAPTIVE_CONTRACT_VERSION,
        )
        self.assertEqual(len(self.contract.contract_sha256), 64)

    def test_external_provenance_cannot_become_runtime_callable(self) -> None:
        self.assertEqual(self.contract.provenance, EXTERNAL_PROVENANCE)
        for forbidden in (
            "runtime_callable",
            "real",
            "logic_oasis_runtime_real",
            "native_logic_oasis_quizAttempts",
        ):
            with self.assertRaises(ExternalContractError):
                validate_provenance_external_real(forbidden)

    def test_native_finalization_and_validation_statuses_are_not_fabricated(self) -> None:
        self.assertIn("finalizationStatus", self.contract.never_fabricate_native_fields)
        self.assertIn("validationStatus", self.contract.never_fabricate_native_fields)
        attempt_fields = {field.name for field in ExternalAdaptiveAttemptV1.__dataclass_fields__.values()}
        self.assertNotIn("finalizationStatus", attempt_fields)
        self.assertNotIn("validationStatus", attempt_fields)

    def test_native_bank_id_is_not_required_for_external_candidates(self) -> None:
        candidate = external_proxy_candidate(ProxyDifficulty.MODERATE)
        self.assertIs(candidate.candidate_kind, CandidateKind.EXTERNAL_PROXY_TIER)
        self.assertIsNone(candidate.native_bank_id)
        self.assertTrue(candidate.external_candidate_key.startswith(EXTERNAL_CANDIDATE_KEY_NAMESPACE))
        self.assertTrue(candidate.available)
        with self.assertRaises(ExternalContractError):
            EvaluationDifficultyOption(
                difficulty=Difficulty.EASY,
                candidate_kind=CandidateKind.EXTERNAL_PROXY_TIER,
                native_bank_id="bank-fake",
                external_candidate_key="external_proxy_proxy_easy",
            )

    def test_proxy_difficulty_values_are_only_the_three_proxy_tiers(self) -> None:
        self.assertEqual(self.contract.proxy_difficulty_values, PROXY_DIFFICULTY_VALUES)
        self.assertEqual(
            {tier.value for tier in ProxyDifficulty},
            {"proxy_easy", "proxy_moderate", "proxy_hard"},
        )
        with self.assertRaises(ValueError):
            ProxyDifficulty("easy")

    def test_calibration_and_evaluation_windows_do_not_overlap(self) -> None:
        self.assertTrue(self.contract.windows_are_disjoint)
        self.assertTrue(windows_do_not_overlap())
        self.assertLess(CALIBRATION_WINDOW_END, EVALUATION_WINDOW_START)

    def test_evaluation_period_outcomes_cannot_be_calibration_input(self) -> None:
        evaluation_start = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.assertFalse(in_calibration_window(evaluation_start))
        self.assertTrue(in_evaluation_window(evaluation_start))
        self.assertFalse(in_evaluation_window(CALIBRATION_WINDOW_END))
        self.assertFalse(in_calibration_window(EVALUATION_WINDOW_END))
        self.assertFalse(in_calibration_window(datetime(2022, 6, 1, tzinfo=timezone.utc)))

    def test_minimum_calibration_learners_is_frozen_at_20(self) -> None:
        self.assertEqual(self.contract.minimum_calibration_learners, 20)
        self.assertEqual(MINIMUM_CALIBRATION_LEARNERS, 20)

    def test_skill_catalog_requirement_is_frozen(self) -> None:
        self.assertEqual(self.contract.skill_catalog_minimum_calibrated_problems, 9)
        self.assertEqual(self.contract.skill_catalog_minimum_per_tier, 3)
        self.assertEqual(SKILL_CATALOG_MINIMUM_CALIBRATED_PROBLEMS, 9)
        self.assertEqual(SKILL_CATALOG_MINIMUM_PER_TIER, 3)

    def test_attempt_purity_threshold_is_frozen_at_two_thirds(self) -> None:
        self.assertEqual(self.contract.attempt_purity_threshold, Fraction(2, 3))
        self.assertEqual(ATTEMPT_PURITY_THRESHOLD, Fraction(2, 3))

    def test_one_step_non_propagating_replay_mode_is_frozen(self) -> None:
        self.assertEqual(self.contract.replay_mode, REPLAY_MODE)
        self.assertEqual(REPLAY_MODE, "one_step_non_propagating")

    def test_reversal_history_source_is_observed_history(self) -> None:
        self.assertEqual(
            self.contract.reversal_history_source,
            REVERSAL_HISTORY_SOURCE,
        )
        self.assertEqual(REVERSAL_HISTORY_SOURCE, "observed_proxy_difficulty_history")

    def test_fresh_bank_limitation_is_explicit(self) -> None:
        limitation = self.contract.fresh_bank_limitation
        self.assertEqual(limitation["productionRule"], "preserved")
        self.assertEqual(limitation["exactExternalObservability"], "unavailable")
        self.assertEqual(
            limitation["externalSubstitute"],
            "fresh_problem_exposure_audit_only",
        )
        self.assertFalse(limitation["includedInFullPolicyEquivalenceClaim"])

    def test_external_claim_level_cannot_become_superiority(self) -> None:
        allowed = {level.value for level in ExternalClaimLevel}
        self.assertEqual(self.contract.allowed_claim_levels, allowed)
        for forbidden in ("superiority", "causal_effect", "KSSR_validated", "production_validated"):
            self.assertIn(forbidden, self.contract.forbidden_claim_levels)
            self.assertNotIn(forbidden, self.contract.allowed_claim_levels)

    def test_production_promotion_is_forbidden(self) -> None:
        self.assertFalse(self.contract.production_promotion_allowed)
        self.assertFalse(PRODUCTION_PROMOTION_ALLOWED)
        self.assertFalse(self.contract.contains_raw_identifiers)
        self.assertFalse(CONTAINS_RAW_IDENTIFIERS)

    def test_p3a_remains_bkt_only_and_bypasses_model_risk_inference(self) -> None:
        loaded = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        p3a = loaded["policyBindings"]["P3a"]
        self.assertTrue(p3a["bktOnly"])
        self.assertTrue(p3a["bypassSupportRiskXgboostInference"])
        self.assertEqual(p3a["evidenceMode"], "bkt_only_study")
        self.assertEqual(p3a["selectionEvidenceMode"], "bkt_only_study")
        self.assertTrue(p3a["usedBktFallback"])
        self.assertEqual(p3a["policyVersion"], "guarded-bkt-study-v1")

    def test_existing_p1_p2_p3a_definitions_and_hashes_are_unchanged(self) -> None:
        adaptive = load_adaptive_policy_config(ADAPTIVE_POLICY_PATH)
        manifest = load_policy_evaluation_manifest(
            POLICY_EVALUATION_PATH, adaptive_policy=adaptive
        )
        self.assertEqual(
            manifest.adaptive_policy_sha256,
            self.contract.adaptive_policy_content_sha256,
        )
        self.assertEqual(P1_PROMOTION_THRESHOLD, 0.80)
        self.assertEqual(P2_DEMOTION_THRESHOLD, 0.40)
        self.assertEqual(
            manifest.policy_arms[0].policy_version,
            "score-threshold-v1",
        )
        versions = {arm.policy_version for arm in manifest.policy_arms}
        self.assertEqual(
            versions,
            {
                "score-threshold-v1",
                "bkt-score-agreement-v1",
                "guarded-bkt-study-v1",
                "guarded-bkt-model-assisted-v1",
            },
        )
        self.assertEqual(self.contract.bkt_version, BKT_MODEL_VERSION)

    def test_native_aqc_source_mode_still_validates(self) -> None:
        adaptive = load_adaptive_policy_config(ADAPTIVE_POLICY_PATH)
        manifest = load_policy_evaluation_manifest(
            POLICY_EVALUATION_PATH, adaptive_policy=adaptive
        )
        self.assertEqual(manifest.manifest_version, "policy-evaluation-v1")
        self.assertEqual(manifest.study.status.value, "draft")
        self.assertEqual(
            self.contract.policy_evaluation_sha256,
            "a12d251e5910a034c081950a8bede8dc7753329db0e9c540af108143e9a43a61",
        )

    def test_required_censoring_vocabulary_is_frozen(self) -> None:
        self.assertTrue(REQUIRED_CENSOR_REASONS <= self.contract.censor_reasons)
        self.assertEqual(len(REQUIRED_CENSOR_REASONS), 9)


class ContractTamperTests(unittest.TestCase):
    """Altering any frozen boundary must fail closed."""

    def setUp(self) -> None:
        self.original = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))

    def load_variant(self, variant: dict) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "variant.yaml"
            path.write_text(yaml.safe_dump(variant, sort_keys=False), encoding="utf-8")
            with self.assertRaises(ExternalContractError):
                load_external_adaptive_contract(path)

    def test_provenance_tamper_is_rejected(self) -> None:
        variant = deepcopy(self.original)
        variant["dataset"]["provenance"] = "runtime_callable"
        self.load_variant(variant)

    def test_predecessor_contract_swap_is_rejected(self) -> None:
        variant = deepcopy(self.original)
        variant["predecessorContracts"]["sharedAqcPolicyContract"][
            "policyEvaluationVersion"
        ] = "policy-evaluation-v2"
        self.load_variant(variant)

    def test_u7_contract_swap_is_rejected(self) -> None:
        variant = deepcopy(self.original)
        variant["predecessorContracts"]["u7ExternalRealData"][
            "attemptLabelContract"
        ] = "assistments-j2-attempt-label-contract-v1"
        self.load_variant(variant)

    def test_overlapping_windows_are_rejected(self) -> None:
        variant = deepcopy(self.original)
        variant["timeContract"]["calibrationWindow"]["end"] = "2022-06-01T00:00:00Z"
        self.load_variant(variant)

    def test_lowering_minimum_calibration_learners_is_rejected(self) -> None:
        variant = deepcopy(self.original)
        variant["proxyDifficulty"]["minimumIndependentCalibrationLearnersPerProblem"] = 19
        self.load_variant(variant)

    def test_lowering_skill_catalog_gate_is_rejected(self) -> None:
        variant = deepcopy(self.original)
        variant["proxyDifficulty"]["skillCatalogGate"]["minimumCalibratedProblemsPerSkill"] = 8
        self.load_variant(variant)

    def test_lowering_attempt_purity_is_rejected(self) -> None:
        variant = deepcopy(self.original)
        variant["attemptTier"]["purityThresholdNumerator"] = 1
        self.load_variant(variant)

    def test_switching_replay_mode_is_rejected(self) -> None:
        variant = deepcopy(self.original)
        variant["replayMode"]["mode"] = "propagating_counterfactual"
        self.load_variant(variant)

    def test_switching_reversal_history_source_is_rejected(self) -> None:
        variant = deepcopy(self.original)
        variant["replayMode"]["reversalHistorySource"] = "simulated_counterfactual_history"
        self.load_variant(variant)

    def test_claim_level_upgrade_is_rejected(self) -> None:
        variant = deepcopy(self.original)
        variant["claimLevels"]["allowed"].append("superiority")
        self.load_variant(variant)

    def test_production_promotion_toggle_is_rejected(self) -> None:
        variant = deepcopy(self.original)
        variant["governance"]["productionPromotionAllowed"] = True
        self.load_variant(variant)

    def test_p3a_model_assisted_toggle_is_rejected(self) -> None:
        variant = deepcopy(self.original)
        variant["policyBindings"]["P3a"]["bypassSupportRiskXgboostInference"] = False
        self.load_variant(variant)

    def test_fresh_bank_equivalence_claim_is_rejected(self) -> None:
        variant = deepcopy(self.original)
        variant["freshBankLimitation"]["includedInFullPolicyEquivalenceClaim"] = True
        self.load_variant(variant)

    def test_missing_censor_reason_is_rejected(self) -> None:
        variant = deepcopy(self.original)
        variant["censoringVocabulary"]["reasons"].remove("chronology_ambiguous")
        self.load_variant(variant)

    def test_native_bank_id_fabrication_guard_cannot_be_removed(self) -> None:
        variant = deepcopy(self.original)
        variant["governance"]["neverFabricateNativeFields"] = ["finalizationStatus"]
        self.load_variant(variant)


class FrozenHelperTests(unittest.TestCase):
    """Tiny pure helpers that freeze the E1 methodology for later E2+ stages."""

    def test_smoothing_rule_matches_frozen_formula(self) -> None:
        self.assertEqual(smoothed_correct_probability(7, 20), 8 / 22)
        self.assertEqual(smoothed_correct_probability(0, 0), 0.5)
        self.assertEqual(difficulty_score(7, 20), 1 - 8 / 22)
        with self.assertRaises(ExternalContractError):
            smoothed_correct_probability(21, 20)

    def test_problem_set_fingerprint_is_deterministic_and_never_a_bank_id(self) -> None:
        keys = ("p2", "p1", "p2")
        first = problem_set_fingerprint("6.NS.A.1", keys)
        second = problem_set_fingerprint("6.NS.A.1", ("p1", "p2"))
        different_skill = problem_set_fingerprint("6.NS.B.2", ("p1", "p2"))
        self.assertEqual(first, second)
        self.assertNotEqual(first, different_skill)
        self.assertEqual(len(first), 64)
        self.assertFalse(first.startswith("bank"))
        self.assertNotEqual(first, "bank_fake")

    def test_evaluation_difficulty_option_maps_external_tier_to_shared_difficulty(self) -> None:
        mapping = {
            ProxyDifficulty.EASY: Difficulty.EASY,
            ProxyDifficulty.MODERATE: Difficulty.MODERATE,
            ProxyDifficulty.HARD: Difficulty.HARD,
        }
        for proxy_tier, difficulty in mapping.items():
            option = external_proxy_candidate(proxy_tier)
            self.assertEqual(option.difficulty, difficulty)
            self.assertIsNone(option.native_bank_id)

    def test_external_problem_difficulty_record_enforces_threshold_and_tiers(self) -> None:
        record = ExternalProblemDifficultyV1(
            dataset_release_id="assistments-edm-cup-2023-release-v1",
            external_problem_key="problem-1",
            source_skill_code="6.NS.A.1",
            calibration_start=CALIBRATION_WINDOW_START,
            calibration_end=CALIBRATION_WINDOW_END,
            calibration_learner_count=25,
            calibration_response_count=60,
            correct_response_count=42,
            smoothed_correct_probability=smoothed_correct_probability(42, 60),
            difficulty_score=difficulty_score(42, 60),
            proxy_difficulty=ProxyDifficulty.EASY,
            calibration_status="calibrated",
            provenance=EXTERNAL_PROVENANCE,
        )
        self.assertEqual(record.proxy_difficulty, ProxyDifficulty.EASY)
        with self.assertRaises(ExternalContractError):
            ExternalProblemDifficultyV1(
                dataset_release_id="assistments-edm-cup-2023-release-v1",
                external_problem_key="problem-2",
                source_skill_code="6.NS.A.1",
                calibration_start=CALIBRATION_WINDOW_START,
                calibration_end=CALIBRATION_WINDOW_END,
                calibration_learner_count=10,
                calibration_response_count=30,
                correct_response_count=15,
                smoothed_correct_probability=smoothed_correct_probability(15, 30),
                difficulty_score=difficulty_score(15, 30),
                proxy_difficulty=ProxyDifficulty.EASY,
                calibration_status="calibrated",
                provenance=EXTERNAL_PROVENANCE,
            )

    def test_external_adaptive_attempt_record_requires_purity_and_fingerprint(self) -> None:
        keys = ("p1", "p2", "p3", "p4", "p5")
        attempt = ExternalAdaptiveAttemptV1(
            dataset_release_id="assistments-edm-cup-2023-release-v1",
            external_attempt_key="attempt-1",
            external_student_key="student-1",
            external_assignment_key="assignment-1",
            source_skill_code="6.NS.A.1",
            source_timestamp=EVALUATION_WINDOW_START,
            external_attempt_sequence=1,
            problem_keys=keys,
            total_questions=5,
            correct_count=4,
            correct_rate=0.8,
            bkt_mastery_probability=0.72,
            bkt_evidence_count=5,
            bkt_version=BKT_MODEL_VERSION,
            current_proxy_difficulty=ProxyDifficulty.EASY,
            proxy_difficulty_purity=4 / 5,
            external_problem_set_fingerprint=problem_set_fingerprint("6.NS.A.1", keys),
            previous_observed_proxy_difficulty=None,
            fresh_problem_fraction=0.6,
            provenance=EXTERNAL_PROVENANCE,
        )
        self.assertEqual(attempt.correct_rate, 0.8)
        with self.assertRaises(ExternalContractError):
            ExternalAdaptiveAttemptV1(
                dataset_release_id="assistments-edm-cup-2023-release-v1",
                external_attempt_key="attempt-2",
                external_student_key="student-1",
                external_assignment_key="assignment-2",
                source_skill_code="6.NS.A.1",
                source_timestamp=EVALUATION_WINDOW_START,
                external_attempt_sequence=2,
                problem_keys=keys,
                total_questions=5,
                correct_count=4,
                correct_rate=0.8,
                bkt_mastery_probability=0.72,
                bkt_evidence_count=5,
                bkt_version=BKT_MODEL_VERSION,
                current_proxy_difficulty=ProxyDifficulty.EASY,
                proxy_difficulty_purity=0.5,
                external_problem_set_fingerprint=problem_set_fingerprint("6.NS.A.1", keys),
                previous_observed_proxy_difficulty=None,
                fresh_problem_fraction=0.6,
                provenance=EXTERNAL_PROVENANCE,
            )

    def test_mixed_tier_audit_row_keeps_purity_with_null_current_tier(self) -> None:
        keys = ("p1", "p2", "p3", "p4", "p5")
        attempt = ExternalAdaptiveAttemptV1(
            dataset_release_id="assistments-edm-cup-2023-release-v1",
            external_attempt_key="attempt-mixed",
            external_student_key="student-1",
            external_assignment_key="assignment-3",
            source_skill_code="6.NS.A.1",
            source_timestamp=EVALUATION_WINDOW_START,
            external_attempt_sequence=3,
            problem_keys=keys,
            total_questions=5,
            correct_count=3,
            correct_rate=0.6,
            bkt_mastery_probability=0.60,
            bkt_evidence_count=4,
            bkt_version=BKT_MODEL_VERSION,
            current_proxy_difficulty=None,
            proxy_difficulty_purity=3 / 5,
            external_problem_set_fingerprint=problem_set_fingerprint("6.NS.A.1", keys),
            previous_observed_proxy_difficulty=None,
            fresh_problem_fraction=0.4,
            provenance=EXTERNAL_PROVENANCE,
        )
        self.assertIsNone(attempt.current_proxy_difficulty)
        self.assertLess(attempt.proxy_difficulty_purity, 2 / 3)

    def test_window_boundaries_are_utc_only(self) -> None:
        self.assertFalse(in_calibration_window(datetime(2021, 6, 1)))
        self.assertFalse(in_evaluation_window(datetime(2022, 6, 1)))
        self.assertTrue(
            in_calibration_window(
                datetime(2021, 6, 1, tzinfo=timezone.utc)
            )
        )
        self.assertTrue(
            in_evaluation_window(
                datetime(2022, 6, 1, tzinfo=timezone.utc)
            )
        )
        self.assertTrue(in_calibration_window(CALIBRATION_WINDOW_START))
        self.assertTrue(in_calibration_window(CALIBRATION_WINDOW_END))
        self.assertTrue(in_evaluation_window(EVALUATION_WINDOW_START))
        self.assertTrue(in_evaluation_window(EVALUATION_WINDOW_END))
        # Windows are adjacent: the last calibration second is 23:59:59 on
        # 2021-12-31 and the first evaluation second is 00:00:00 on 2022-01-01.
        self.assertTrue(
            in_calibration_window(EVALUATION_WINDOW_START - timedelta(seconds=1))
        )
        self.assertFalse(in_calibration_window(EVALUATION_WINDOW_START))
        self.assertFalse(in_evaluation_window(CALIBRATION_WINDOW_END))


if __name__ == "__main__":
    unittest.main()
