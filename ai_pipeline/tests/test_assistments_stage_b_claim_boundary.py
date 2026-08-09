"""AQC-E1 Stage-B claim-boundary tests for the ASSISTments external pathway.

These tests freeze the descriptive, non-causal, non-production boundary of the
external ASSISTments evidence and the separation between evidence modes. They
never run calibration or policy comparison.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

import yaml

from external_data.assistments.adaptive.external_policy_contract import (
    ExternalContractError,
    load_external_adaptive_contract,
)
from external_data.assistments.adaptive.schemas import (
    ExternalEvidenceMode,
    ExternalClaimLevel,
    FORBIDDEN_EXTERNAL_CLAIM_LEVELS,
    REQUIRED_CENSOR_REASONS,
    CandidateKind,
    ProxyDifficulty,
    external_proxy_candidate,
    problem_set_fingerprint,
    validate_provenance_external_real,
)


AI_PIPELINE = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    AI_PIPELINE
    / "external_data"
    / "assistments"
    / "adaptive"
    / "assistments_adaptive_contract_v1.yaml"
)


class StageBClaimBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_external_adaptive_contract(CONTRACT_PATH)

    def test_external_evidence_cannot_receive_a_superiority_claim(self) -> None:
        allowed = {level.value for level in ExternalClaimLevel}
        self.assertTrue(FORBIDDEN_EXTERNAL_CLAIM_LEVELS <= self.contract.forbidden_claim_levels)
        self.assertTrue(allowed <= self.contract.allowed_claim_levels)
        self.assertEqual(allowed & self.contract.forbidden_claim_levels, set())

    def test_sample_size_never_upgrades_external_claim_level(self) -> None:
        loaded = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertTrue(loaded["claimLevels"]["sampleSizeNeverUpgradesToCausalOrSuperiority"])

    def test_external_artifacts_cannot_activate_runtime_production_policy(self) -> None:
        self.assertFalse(self.contract.production_promotion_allowed)
        loaded = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        governance = loaded["governance"]
        self.assertFalse(governance["productionPromotionAllowed"])
        self.assertNotIn("activation", governance)
        self.assertNotIn("promoteToProduction", governance)

    def test_controlled_demo_rows_cannot_enter_external_counts(self) -> None:
        loaded = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        distinct_from = loaded["evidenceMode"]["distinctFrom"]
        self.assertIn("controlled_demo", distinct_from)
        self.assertIn("pipeline_demo_only", distinct_from)
        self.assertIn("native_runtime", distinct_from)
        self.assertIn("stage_c_live_pilot", distinct_from)
        self.assertIs(
            ExternalEvidenceMode.CONTROLLED_DEMO,
            ExternalEvidenceMode("controlled_demo"),
        )
        self.assertIs(
            ExternalEvidenceMode.EXTERNAL_REAL_PROXY_DIFFICULTY,
            ExternalEvidenceMode("external_real_proxy_difficulty"),
        )

    def test_external_candidate_never_creates_a_fake_bank_id(self) -> None:
        for tier in ("proxy_easy", "proxy_moderate", "proxy_hard"):
            candidate = external_proxy_candidate(ProxyDifficulty(tier))
            self.assertIs(candidate.candidate_kind, CandidateKind.EXTERNAL_PROXY_TIER)
            self.assertIsNone(candidate.native_bank_id)
        fingerprint = problem_set_fingerprint("6.NS.A.1", ("p1", "p2"))
        self.assertNotIn("bankId", fingerprint)
        self.assertNotEqual(fingerprint, "bank")

    def test_stage_b_questions_are_separate_from_stage_c_hypotheses(self) -> None:
        loaded = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        questions = loaded["stageBQuestions"]
        for question_id in ("EB1", "EB2", "EB3", "EB4", "EB5", "EB6"):
            self.assertIn(question_id, questions)
        for reserved in ("H1", "H2", "H3", "H4", "H5", "H6"):
            self.assertNotIn(reserved, questions)
        self.assertIn("H1-H6", loaded["stageBQuestions"]["note"])

    def test_fresh_bank_equivalence_claim_is_excluded(self) -> None:
        limitation = self.contract.fresh_bank_limitation
        self.assertFalse(limitation["includedInFullPolicyEquivalenceClaim"])
        self.assertEqual(limitation["externalSubstitute"], "fresh_problem_exposure_audit_only")
        self.assertEqual(limitation["productionRule"], "preserved")

    def test_external_matched_support_metric_is_not_stage_c_confirmatory(self) -> None:
        loaded = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        metrics = loaded["externalMetrics"]
        self.assertIn(
            "observed_proxy_matched_support_after_up_rate",
            metrics["names"],
        )
        self.assertNotIn("falsePromotionBurden", metrics["names"])
        self.assertIn("falsePromotionBurden", metrics["reservedForStageCOnly"])

    def test_censors_are_never_translated_into_native_bank_errors(self) -> None:
        self.assertTrue(
            REQUIRED_CENSOR_REASONS <= self.contract.censor_reasons
        )
        loaded = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertTrue(loaded["censoringVocabulary"]["neverTranslateIntoNativeBankErrors"])
        for reason in REQUIRED_CENSOR_REASONS:
            self.assertNotIn("bank", reason)

    def test_external_provenance_cannot_be_native(self) -> None:
        self.assertEqual(self.contract.provenance, "external_real")
        with self.assertRaises(ExternalContractError):
            validate_provenance_external_real("runtime_callable")

    def test_claim_level_source_is_external_real(self) -> None:
        loaded = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(loaded["claimLevels"]["source"], "external_real")

    def test_tampered_superiority_claim_is_rejected(self) -> None:
        original = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        variant = deepcopy(original)
        variant["claimLevels"]["allowed"] = ["external_descriptive_replay", "superiority"]
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "variant.yaml"
            path.write_text(yaml.safe_dump(variant, sort_keys=False), encoding="utf-8")
            with self.assertRaises(ExternalContractError):
                load_external_adaptive_contract(path)

    def test_tampered_production_toggle_is_rejected(self) -> None:
        original = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        variant = deepcopy(original)
        variant["governance"]["productionPromotionAllowed"] = True
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "variant.yaml"
            path.write_text(yaml.safe_dump(variant, sort_keys=False), encoding="utf-8")
            with self.assertRaises(ExternalContractError):
                load_external_adaptive_contract(path)


if __name__ == "__main__":
    unittest.main()
