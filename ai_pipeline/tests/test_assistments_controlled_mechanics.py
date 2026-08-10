"""AQC-A controlled mechanics regression tests (pipeline_demo_only fixtures).

These tests verify that the authoritative P1/P2/P3a selectors and the external
proxy-tier difficulty-candidate abstraction behave exactly as intended, using
only deterministic controlled fixtures.  No real ASSISTments data is read and
no policy rate or matched outcome is computed.
"""

from __future__ import annotations

from pathlib import Path
import unittest

from logic_oasis_ai.adaptive_policy import Difficulty, load_adaptive_policy_config
from logic_oasis_ai.policy_evaluation import (
    DecisionDirection,
    PolicyArm,
    PolicyDecisionContext,
    SelectionEvidenceMode,
    load_policy_evaluation_manifest,
    select_policy_decision,
)

from external_data.assistments.adaptive.controlled_mechanics import (
    FIXTURE_EVIDENCE_MODE,
    FORBIDDEN_FIXTURE_CLAIMS,
    ControlledMechanicsConfig,
    external_options_for_tiers,
    fixture_results_hash,
    native_options_for_tiers,
    run_all_fixtures,
    run_fixture,
    to_selector_banks,
)
from external_data.assistments.adaptive.schemas import (
    CandidateKind,
    ProxyDifficulty,
)


AI_PIPELINE = Path(__file__).resolve().parents[1]
CONFIG = ControlledMechanicsConfig(
    adaptive_policy_path=AI_PIPELINE / "configs" / "adaptive_policy_v1.yaml",
    policy_manifest_path=AI_PIPELINE / "configs" / "policy_evaluation_v1.yaml",
)


def context_for(**overrides) -> PolicyDecisionContext:
    from external_data.assistments.adaptive.controlled_mechanics import controlled_context

    values = {
        "current_tier": "proxy_easy",
        "correct": 80,
        "total": 100,
        "mastery": 0.60,
        "evidence": 3,
        "last_transition": None,
        "attempt_id": "fixture-attempt",
    }
    values.update(overrides)
    return controlled_context(**values)


class FixtureSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.results = {r.fixture_id: r for r in run_all_fixtures(config=CONFIG)}

    def test_p1_below_threshold_holds(self) -> None:
        self.assertEqual(self.results["S1"].direction, "hold")
        self.assertEqual(self.results["S1"].reason_code, "p1_score_hold")

    def test_p1_at_threshold_moves_up(self) -> None:
        self.assertEqual(self.results["S2"].direction, "up")
        self.assertEqual(self.results["S2"].reason_code, "p1_score_promote")
        self.assertEqual(self.results["S2"].selected_difficulty, "Moderate")

    def test_p1_never_auto_demotes(self) -> None:
        low = run_fixture(
            "P1-low",
            PolicyArm.P1,
            context_for(current_tier="proxy_moderate", correct=10, total=100, mastery=0.30, evidence=5),
            external_options_for_tiers(),
            config=CONFIG,
        )
        self.assertEqual(low.direction, "hold")
        self.assertNotEqual(low.direction, "down")

    def test_p1_up_at_upper_boundary_holds(self) -> None:
        self.assertEqual(self.results["S3"].direction, "hold")
        self.assertEqual(self.results["S3"].reason_code, "difficulty_upper_bound_hold")

    def test_p2_score_boundaries_are_frozen(self) -> None:
        self.assertEqual(self.results["S4"].direction, "up")  # score exactly 0.80
        self.assertEqual(self.results["S6"].direction, "down")  # score exactly 0.40

    def test_p2_agreement_permits_movement(self) -> None:
        self.assertEqual(self.results["S4"].reason_code, "p2_agreement_promote")
        self.assertEqual(self.results["S6"].reason_code, "p2_agreement_demote")

    def test_p2_disagreement_holds(self) -> None:
        self.assertEqual(self.results["S5"].reason_code, "p2_disagreement_hold")
        self.assertEqual(self.results["S5"].direction, "hold")
        self.assertEqual(self.results["S7"].reason_code, "p2_disagreement_hold")
        self.assertEqual(self.results["S7"].direction, "hold")

    def test_p3a_uses_bkt_evidence_and_guards(self) -> None:
        self.assertEqual(self.results["S8"].reason_code, "p3_stay_build_evidence")
        self.assertEqual(self.results["S8"].direction, "hold")
        self.assertEqual(self.results["S9"].reason_code, "p3_move_up_bkt_fallback")
        self.assertEqual(self.results["S9"].direction, "up")

    def test_p3a_reversal_protection(self) -> None:
        self.assertEqual(self.results["S10"].reason_code, "anti_oscillation_hold")
        self.assertEqual(self.results["S10"].direction, "hold")

    def test_cold_history_remains_valid(self) -> None:
        self.assertEqual(self.results["S11"].direction, "up")
        self.assertEqual(self.results["S11"].reason_code, "p1_score_promote")

    def test_unavailable_external_tier_holds(self) -> None:
        self.assertEqual(self.results["S12"].direction, "hold")
        self.assertEqual(self.results["S12"].reason_code, "no_eligible_bank")
        self.assertTrue(self.results["S12"].selected_identity.startswith("external:"))

    def test_one_level_movement_enforced(self) -> None:
        self.assertEqual(self.results["S13"].selected_difficulty, "Moderate")
        self.assertNotEqual(self.results["S13"].selected_difficulty, "Hard")


class ExternalCandidateTests(unittest.TestCase):
    def test_external_candidate_requires_no_native_bank_id(self) -> None:
        for option in external_options_for_tiers():
            self.assertIs(option.candidate_kind, CandidateKind.EXTERNAL_PROXY_TIER)
            self.assertIsNone(option.native_bank_id)
            self.assertTrue(option.external_candidate_key.startswith("external_proxy_"))

    def test_external_candidate_never_fabricates_bank_id(self) -> None:
        results = run_all_fixtures(config=CONFIG)
        for result in results:
            self.assertTrue(result.selected_identity.startswith("external:"))
        banks = to_selector_banks(external_options_for_tiers())
        for bank in banks:
            self.assertTrue(bank.bank_id.startswith("external_proxy_"))

    def test_external_and_native_modes_share_policy_logic(self) -> None:
        external = {r.fixture_id: r for r in run_all_fixtures(config=CONFIG)}
        native_fixtures = [
            ("S1", PolicyArm.P1, context_for(current_tier="proxy_easy", correct=79, total=100)),
            ("S2", PolicyArm.P1, context_for(current_tier="proxy_easy", correct=80, total=100)),
            ("S4", PolicyArm.P2, context_for(current_tier="proxy_moderate", correct=80, total=100, mastery=0.80, evidence=8)),
            ("S6", PolicyArm.P2, context_for(current_tier="proxy_moderate", correct=40, total=100, mastery=0.40, evidence=5)),
            ("S9", PolicyArm.P3A, context_for(current_tier="proxy_easy", correct=80, total=100, mastery=0.80, evidence=3)),
        ]
        native_options = native_options_for_tiers()
        for fixture_id, arm, context in native_fixtures:
            native_result = run_fixture(fixture_id, arm, context, native_options, config=CONFIG)
            external_result = external[fixture_id]
            self.assertEqual(native_result.direction, external_result.direction)
            self.assertEqual(native_result.reason_code, external_result.reason_code)
            self.assertEqual(native_result.selected_difficulty, external_result.selected_difficulty)
            self.assertFalse(native_result.selected_identity.startswith("external:"))

    def test_p3a_bypasses_support_risk_inference(self) -> None:
        assisted = PolicyDecisionContext(
            source_attempt_id="fixture-assisted",
            student_id="fixture-student",
            subtopic_id="fixture-skill",
            current_difficulty=Difficulty.EASY,
            correct_count=80,
            total_questions=100,
            mastery_probability=0.80,
            evidence_count=3,
            support_risk=0.20,
            compatible_model_available=True,
            last_transition=None,
        )
        adaptive = load_adaptive_policy_config(CONFIG.adaptive_policy_path)
        manifest = load_policy_evaluation_manifest(
            CONFIG.policy_manifest_path,
            adaptive_policy=adaptive,
        )
        p3a = select_policy_decision(
            PolicyArm.P3A,
            assisted,
            to_selector_banks(external_options_for_tiers()),
            manifest=manifest,
            adaptive_policy=adaptive,
        )
        self.assertTrue(p3a.used_bkt_fallback)
        self.assertEqual(p3a.evidence_mode, SelectionEvidenceMode.BKT_ONLY_STUDY)
        self.assertEqual(p3a.reason_code, "p3_move_up_bkt_fallback")


class LeakageAndPropagationTests(unittest.TestCase):
    def test_future_injection_cannot_change_earlier_decision(self) -> None:
        earlier_context = context_for(
            current_tier="proxy_easy",
            correct=80,
            total=100,
            mastery=0.60,
            evidence=3,
            attempt_id="earlier-attempt",
        )
        first = run_fixture("future-1", PolicyArm.P1, earlier_context, external_options_for_tiers(), config=CONFIG)
        # A future state with far more evidence/exposure must not alter the
        # earlier decision when the earlier context is recomputed unchanged.
        future_context = context_for(
            current_tier="proxy_hard",
            correct=100,
            total=100,
            mastery=0.95,
            evidence=30,
            attempt_id="future-attempt",
        )
        run_fixture("future-2", PolicyArm.P1, future_context, external_options_for_tiers(), config=CONFIG)
        recomputed = run_fixture("future-1", PolicyArm.P1, earlier_context, external_options_for_tiers(), config=CONFIG)
        self.assertEqual(first.direction, recomputed.direction)
        self.assertEqual(first.reason_code, recomputed.reason_code)
        self.assertEqual(first.decision_id, recomputed.decision_id)

    def test_one_step_replay_does_not_propagate_counterfactual_state(self) -> None:
        # Historical t1 at Moderate: P1 would propose Hard.
        t1 = run_fixture(
            "t1",
            PolicyArm.P1,
            context_for(current_tier="proxy_moderate", correct=80, total=100, mastery=0.60, evidence=5),
            external_options_for_tiers(),
            config=CONFIG,
        )
        self.assertEqual(t1.selected_difficulty, "Hard")
        # Historical t2 is OBSERVED at Moderate (not the counterfactual Hard).
        t2 = run_fixture(
            "t2",
            PolicyArm.P1,
            context_for(current_tier="proxy_moderate", correct=60, total=100, mastery=0.60, evidence=5),
            external_options_for_tiers(),
            config=CONFIG,
        )
        self.assertEqual(t2.selected_difficulty, "Moderate")
        self.assertEqual(t2.direction, "hold")
        self.assertEqual(t2.reason_code, "p1_score_hold")


class ClaimAndGovernanceTests(unittest.TestCase):
    def test_controlled_fixture_claim_remains_pipeline_demo_only(self) -> None:
        results = run_all_fixtures(config=CONFIG)
        for result in results:
            self.assertEqual(result.fixture_evidence_mode, FIXTURE_EVIDENCE_MODE)
            self.assertEqual(FIXTURE_EVIDENCE_MODE, "pipeline_demo_only")

    def test_controlled_fixture_cannot_create_forbidden_claims(self) -> None:
        results = run_all_fixtures(config=CONFIG)
        for result in results:
            self.assertNotIn(result.fixture_evidence_mode, FORBIDDEN_FIXTURE_CLAIMS)
            self.assertNotIn(result.decision_claim_label, FORBIDDEN_FIXTURE_CLAIMS)
        self.assertIn("superiority", FORBIDDEN_FIXTURE_CLAIMS)
        self.assertIn("external_descriptive_replay", FORBIDDEN_FIXTURE_CLAIMS)
        self.assertIn("production_validated", FORBIDDEN_FIXTURE_CLAIMS)

    def test_production_promotion_remains_false(self) -> None:
        from external_data.assistments.adaptive.external_policy_contract import (
            EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION,
            load_external_adaptive_contract,
        )

        contract = load_external_adaptive_contract(
            AI_PIPELINE / "external_data" / "assistments" / "adaptive" / "assistments_adaptive_contract_v1_2.yaml",
            version=EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION,
        )
        self.assertFalse(contract.production_promotion_allowed)
        adaptive = load_adaptive_policy_config(CONFIG.adaptive_policy_path)
        manifest = load_policy_evaluation_manifest(
            CONFIG.policy_manifest_path,
            adaptive_policy=adaptive,
        )
        self.assertEqual(manifest.study.status.value, "draft")
        self.assertFalse(manifest.study.may_enrol)

    def test_fresh_problem_fraction_is_not_called_fresh_bank(self) -> None:
        module = Path(__file__).resolve().parents[1] / "external_data" / "assistments" / "adaptive" / "controlled_mechanics.py"
        source = module.read_text(encoding="utf-8")
        self.assertNotIn("freshBank", source)
        self.assertNotIn("fresh_bank", source.lower().replace("fresh-bank", ""))
        schemas = (
            Path(__file__).resolve().parents[1]
            / "external_data"
            / "assistments"
            / "adaptive"
            / "schemas.py"
        ).read_text(encoding="utf-8")
        self.assertIn("fresh_problem_fraction", schemas)


class DeterminismTests(unittest.TestCase):
    def test_deterministic_rerun_produces_identical_outputs(self) -> None:
        first = run_all_fixtures(config=CONFIG)
        second = run_all_fixtures(config=CONFIG)
        self.assertEqual(first, second)
        self.assertEqual(fixture_results_hash(first), fixture_results_hash(second))
        for before, after in zip(first, second):
            self.assertEqual(before.decision_id, after.decision_id)
            self.assertEqual(before.direction, after.direction)
            self.assertEqual(before.reason_code, after.reason_code)

    def test_no_randomness_in_fixtures(self) -> None:
        results = run_all_fixtures(config=CONFIG)
        rerun = run_all_fixtures(config=CONFIG)
        for before, after in zip(results, rerun):
            self.assertTrue(before.decision_id.startswith("policy-decision-"))
            self.assertEqual(len(before.decision_id), len("policy-decision-") + 64)
            self.assertEqual(before.decision_id, after.decision_id)


if __name__ == "__main__":
    unittest.main()
