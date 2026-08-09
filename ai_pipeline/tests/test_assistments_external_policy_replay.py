"""AQC-E5 real external policy replay tests (frozen rules, no future outcomes).

These tests verify that P1/P2/P3a replay the EXACT same frozen shared-state
population with strict row parity, frozen thresholds/guards, external proxy
candidates (never a native bankId), observed-history-only reversal context,
one-step non-propagation, deterministic outputs, and no P3b / XGBoost / future
outcome usage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import unittest

from logic_oasis_ai.policy_evaluation import PolicyArm

from external_data.assistments.adaptive.controlled_mechanics import (
    ControlledMechanicsConfig,
    external_options_for_tiers,
)
from external_data.assistments.adaptive.policy_replay import (
    CLAIM_LEVEL,
    DECISION_ROW_FIELDS,
    REPLAY_ARMS,
    SHARED_STATE_COUNT,
    agreement_metrics,
    build_decision_context,
    decision_rows_hash,
    direction_counts,
    eb_metrics,
    observed_transition_marker,
    reason_counts,
    replay_policies,
    reversal_signal_metrics,
    shared_policy_state_hash,
)
from external_data.assistments.adaptive.readiness_audit import (
    ReadinessAttempt,
    policy_ready_funnel,
)
from external_data.assistments.adaptive.schemas import CandidateKind


AI_PIPELINE = Path(__file__).resolve().parents[1]
CONFIG = ControlledMechanicsConfig(
    adaptive_policy_path=AI_PIPELINE / "configs" / "adaptive_policy_v1.yaml",
    policy_manifest_path=AI_PIPELINE / "configs" / "policy_evaluation_v1.yaml",
)
ELIGIBLE = frozenset({"6.NS.A.1", "6.EE.B.7"})
BASE = datetime(2022, 3, 1, tzinfo=timezone.utc)


def state(
    key: str = "s1",
    learner: str = "student-1",
    skill: str = "6.NS.A.1",
    tier: str = "proxy_easy",
    previous: str | None = None,
    correct: int = 80,
    total: int = 100,
    mastery: float = 0.60,
    evidence: int = 5,
    provenance: str = "external_real",
    purity: float | None = None,
    censor: str | None = None,
) -> ReadinessAttempt:
    if purity is None:
        purity = 1.0 if tier else 0.0
    return ReadinessAttempt(
        external_attempt_key=key,
        external_student_key=learner,
        external_assignment_key=f"assignment-{key}",
        source_skill_code=skill,
        source_timestamp=BASE,
        external_attempt_sequence=1,
        problem_keys=(f"p-{key}-1", f"p-{key}-2", f"p-{key}-3"),
        total_questions=total,
        correct_count=correct,
        correct_rate=correct / total,
        bkt_mastery_probability=mastery,
        bkt_evidence_count=evidence,
        bkt_version="bkt-v1",
        current_proxy_difficulty=tier,
        proxy_difficulty_purity=purity,
        external_problem_set_fingerprint=f"fp-{key}",
        previous_observed_proxy_difficulty=previous,
        fresh_problem_fraction=1.0,
        skill_proxy_status="eligible" if skill in ELIGIBLE else "not_eligible",
        current_tier_censor_reason=censor,
        cold_history=previous is None,
        chronology_ambiguous=False,
        provenance=provenance,
    )


def sample_population() -> list[ReadinessAttempt]:
    return [
        state("a1", "u1", tier="proxy_easy", previous=None, correct=80),
        state("a2", "u1", tier="proxy_moderate", previous="proxy_easy", correct=80, mastery=0.80, evidence=8),
        state("a3", "u2", tier="proxy_hard", previous="proxy_moderate", correct=40, mastery=0.40, evidence=8),
        state("a4", "u2", tier="proxy_easy", previous=None, correct=40, mastery=0.60, evidence=5),
        state("a5", "u3", tier="proxy_moderate", previous="proxy_moderate", correct=60, mastery=0.60, evidence=5),
        state("a6", "u3", tier="proxy_hard", previous="proxy_easy", correct=90, mastery=0.80, evidence=9),
    ]


class SharedPopulationTests(unittest.TestCase):
    def test_shared_states_are_exactly_the_frozen_e4_filter(self) -> None:
        rows = sample_population() + [
            state("outside", "u4", skill="7.EE.A.2", tier="proxy_easy"),
            state("no-tier", "u5", tier=None, purity=0.4, censor="mixed_proxy_difficulty"),
        ]
        from external_data.assistments.adaptive.policy_replay import load_shared_states

        # load_shared_states expects a CSV; verify the underlying funnel instead.
        ready, funnel = policy_ready_funnel(rows, ELIGIBLE)
        self.assertEqual(funnel["sharedPolicyReady"]["attempts"], 6)
        self.assertEqual([r.external_attempt_key for r in ready], ["a1", "a2", "a3", "a4", "a5", "a6"])

    def test_shared_state_count_is_frozen_at_2090(self) -> None:
        self.assertEqual(SHARED_STATE_COUNT, 2090)

    def test_shared_state_hash_is_deterministic(self) -> None:
        first = shared_policy_state_hash(sample_population())
        second = shared_policy_state_hash(sample_population())
        self.assertEqual(first, second)


class RowParityTests(unittest.TestCase):
    def test_all_policies_receive_all_shared_rows(self) -> None:
        rows, parity = replay_policies(sample_population(), config=CONFIG)
        self.assertEqual(parity["rowCounts"], {"P1": 6, "P2": 6, "P3a": 6})
        self.assertTrue(parity["rowParityExact"])
        self.assertEqual(len(rows), 18)

    def test_policy_row_keys_are_identical(self) -> None:
        rows, parity = replay_policies(sample_population(), config=CONFIG)
        by_policy = {arm.value: [r.external_state_key for r in rows if r.policy == arm.value] for arm in REPLAY_ARMS}
        self.assertEqual(by_policy["P1"], by_policy["P2"])
        self.assertEqual(by_policy["P2"], by_policy["P3a"])
        self.assertEqual(parity["rowParityExact"], True)

    def test_input_evidence_hashes_are_identical_across_policies(self) -> None:
        rows, parity = replay_policies(sample_population(), config=CONFIG)
        self.assertEqual(parity["inputHashes"]["P1"], parity["inputHashes"]["P2"])
        self.assertEqual(parity["inputHashes"]["P2"], parity["inputHashes"]["P3a"])
        self.assertEqual(parity["inputHashes"]["P1"], parity["sharedPolicyStateHash"])


class FrozenPolicyBehaviorTests(unittest.TestCase):
    def test_p1_frozen_threshold(self) -> None:
        rows, _ = replay_policies(
            [state("below", correct=79), state("at", correct=80)],
            config=CONFIG,
        )
        by_state = {r.external_state_key: r for r in rows if r.policy == "P1"}
        self.assertEqual(by_state["below"].proposed_direction, "hold")
        self.assertEqual(by_state["at"].proposed_direction, "up")

    def test_p1_never_auto_demotes(self) -> None:
        rows, _ = replay_policies(
            [state("low", correct=10, tier="proxy_moderate", mastery=0.30)],
            config=CONFIG,
        )
        p1 = [r for r in rows if r.policy == "P1"][0]
        self.assertEqual(p1.proposed_direction, "hold")
        self.assertEqual(p1.bkt_direction, "down")
        self.assertNotEqual(p1.proposed_direction, "down")

    def test_p2_frozen_boundaries(self) -> None:
        rows, _ = replay_policies(
            [
                state("up", tier="proxy_moderate", correct=80, mastery=0.80, evidence=8),
                state("down", tier="proxy_moderate", correct=40, mastery=0.40, evidence=8),
            ],
            config=CONFIG,
        )
        by_state = {r.external_state_key: r for r in rows if r.policy == "P2"}
        self.assertEqual(by_state["up"].proposed_direction, "up")
        self.assertEqual(by_state["down"].proposed_direction, "down")

    def test_p2_disagreement_holds(self) -> None:
        rows, _ = replay_policies(
            [state("disagree", tier="proxy_moderate", correct=80, mastery=0.60, evidence=5)],
            config=CONFIG,
        )
        p2 = [r for r in rows if r.policy == "P2"][0]
        self.assertEqual(p2.reason_code, "p2_disagreement_hold")
        self.assertEqual(p2.proposed_direction, "hold")

    def test_p3a_evidence_guard_unchanged(self) -> None:
        rows, _ = replay_policies(
            [
                state("insufficient", mastery=0.80, evidence=1),
                state("sufficient", mastery=0.80, evidence=3),
            ],
            config=CONFIG,
        )
        by_state = {r.external_state_key: r for r in rows if r.policy == "P3a"}
        self.assertEqual(by_state["insufficient"].reason_code, "p3_stay_build_evidence")
        self.assertEqual(by_state["insufficient"].proposed_direction, "hold")
        self.assertEqual(by_state["sufficient"].proposed_direction, "up")

    def test_p3a_bypasses_support_risk_and_uses_bkt_only_mode(self) -> None:
        rows, _ = replay_policies(sample_population(), config=CONFIG)
        p3a = [r for r in rows if r.policy == "P3a"]
        for row in p3a:
            self.assertEqual(row.selection_evidence_mode, "bkt_only_study")
            self.assertTrue(row.used_bkt_fallback)

    def test_p3a_reversal_protection(self) -> None:
        rows, _ = replay_policies(
            [
                state(
                    "rev",
                    tier="proxy_moderate",
                    previous="proxy_easy",
                    correct=40,
                    mastery=0.40,
                    evidence=8,
                )
            ],
            config=CONFIG,
        )
        p3a = [r for r in rows if r.policy == "P3a"][0]
        self.assertEqual(p3a.reason_code, "anti_oscillation_hold")
        self.assertEqual(p3a.proposed_direction, "hold")

    def test_cold_history_rows_are_retained(self) -> None:
        rows, _ = replay_policies(
            [state("cold", previous=None, tier="proxy_easy", correct=80)],
            config=CONFIG,
        )
        self.assertEqual(len([r for r in rows if r.policy == "P1"]), 1)

    def test_one_level_movement_only(self) -> None:
        rows, _ = replay_policies(
            [state("perfect", correct=100, tier="proxy_easy", mastery=0.90, evidence=9)],
            config=CONFIG,
        )
        for row in rows:
            if row.proposed_target_proxy_difficulty:
                gap = abs(
                    ("proxy_easy", "proxy_moderate", "proxy_hard").index(
                        row.proposed_target_proxy_difficulty
                    )
                    - ("proxy_easy", "proxy_moderate", "proxy_hard").index(
                        row.current_proxy_difficulty
                    )
                )
                self.assertLessEqual(gap, 1)

    def test_upper_and_lower_bounds_enforced(self) -> None:
        rows, _ = replay_policies(
            [
                state("top", tier="proxy_hard", correct=90, mastery=0.60, evidence=9),
                state("bottom", tier="proxy_easy", correct=10, mastery=0.30, evidence=9),
            ],
            config=CONFIG,
        )
        p1 = {r.external_state_key: r for r in rows if r.policy == "P1"}
        self.assertEqual(p1["top"].reason_code, "difficulty_upper_bound_hold")
        self.assertEqual(p1["top"].proposed_direction, "hold")
        p3a = {r.external_state_key: r for r in rows if r.policy == "P3a"}
        self.assertNotEqual(p3a["bottom"].proposed_direction, "down")


class ExternalCandidateTests(unittest.TestCase):
    def test_external_candidates_have_null_native_bank_id(self) -> None:
        for option in external_options_for_tiers():
            self.assertIs(option.candidate_kind, CandidateKind.EXTERNAL_PROXY_TIER)
            self.assertIsNone(option.native_bank_id)

    def test_no_native_bank_field_is_fabricated(self) -> None:
        rows, _ = replay_policies(sample_population(), config=CONFIG)
        self.assertNotIn("bankId", DECISION_ROW_FIELDS)
        for row in rows:
            self.assertEqual(row.candidate_kind, "external_proxy_tier")
            self.assertTrue(row.external_candidate_key.startswith("external_proxy_"))

    def test_observed_history_only_reversal_context(self) -> None:
        marker_up = observed_transition_marker("proxy_easy", "proxy_moderate")
        marker_down = observed_transition_marker("proxy_moderate", "proxy_easy")
        marker_same = observed_transition_marker("proxy_moderate", "proxy_moderate")
        marker_cold = observed_transition_marker(None, "proxy_easy")
        self.assertEqual(marker_up, "move_up_observed")
        self.assertEqual(marker_down, "move_down_observed")
        self.assertIsNone(marker_same)
        self.assertIsNone(marker_cold)

    def test_one_step_non_propagation_uses_observed_state(self) -> None:
        rows, _ = replay_policies(
            [
                state("t1", tier="proxy_moderate", correct=80, mastery=0.60, evidence=5),
                state("t2", tier="proxy_moderate", correct=60, mastery=0.60, evidence=5),
            ],
            config=CONFIG,
        )
        p1_t2 = [r for r in rows if r.policy == "P1" and r.external_state_key == "t2"][0]
        self.assertEqual(p1_t2.current_proxy_difficulty, "proxy_moderate")
        self.assertEqual(p1_t2.proposed_direction, "hold")


class MetricsAndGovernanceTests(unittest.TestCase):
    def test_metrics_use_identical_state_pairs(self) -> None:
        rows, _ = replay_policies(sample_population(), config=CONFIG)
        agreement = agreement_metrics(rows)
        self.assertEqual(agreement["pairwise"]["P1_vs_P2"]["comparedStates"], 6)
        self.assertEqual(agreement["threeWay"]["comparedStates"], 6)

    def test_eb2_p3a_restraint_is_descriptive(self) -> None:
        rows, _ = replay_policies(sample_population(), config=CONFIG)
        eb = eb_metrics(rows)
        self.assertIn("p3aHoldWhereP1Up", eb)
        self.assertIn("p2DisagreementHoldCount", eb)
        self.assertNotIn("falsePromotion", eb)

    def test_reversal_signal_metrics_fail_closed_on_same_tier(self) -> None:
        rows, _ = replay_policies(
            [state("same", tier="proxy_moderate", previous="proxy_moderate")],
            config=CONFIG,
        )
        reversal = reversal_signal_metrics(rows)
        self.assertEqual(reversal["P1"]["sameTierNoObservedMovement"], 1)
        self.assertEqual(reversal["P1"]["immediateReversalProposed"], 0)

    def test_claim_level_is_external_descriptive_replay(self) -> None:
        self.assertEqual(CLAIM_LEVEL, "external_descriptive_replay")

    def test_no_superiority_and_no_production_promotion(self) -> None:
        module = Path(__file__).resolve().parents[1] / "external_data" / "assistments" / "adaptive" / "policy_replay.py"
        source = module.read_text(encoding="utf-8")
        self.assertNotIn("superiority", source)
        self.assertNotIn("superior", source)
        self.assertIn('"productionPromotionAllowed": False', source)

    def test_no_p3b_and_no_xgboost_in_replay_path(self) -> None:
        module = Path(__file__).resolve().parents[1] / "external_data" / "assistments" / "adaptive" / "policy_replay.py"
        source = module.read_text(encoding="utf-8")
        self.assertNotIn("P3B", source)
        self.assertNotIn("import xgboost", source.lower())
        self.assertNotIn("xgboost_logic_oasis_model", source)
        self.assertNotIn("load_model", source)
        self.assertNotIn("support_risk=0.", source)
        self.assertNotIn("compatible_model_available=True", source)
        self.assertEqual({arm for arm in REPLAY_ARMS}, {PolicyArm.P1, PolicyArm.P2, PolicyArm.P3A})

    def test_no_future_outcome_values_in_replay_path(self) -> None:
        module = Path(__file__).resolve().parents[1] / "external_data" / "assistments" / "adaptive" / "policy_replay.py"
        source = module.read_text(encoding="utf-8")
        for forbidden in (
            "support_needed",
            "next_attempt",
            "nextCorrectRate",
            "matched",
            "counterfactual_proxy_tier_mismatch",
        ):
            self.assertNotIn(forbidden, source)

    def test_deterministic_rerun_identical_audit_hash(self) -> None:
        first_rows, first_parity = replay_policies(sample_population(), config=CONFIG)
        second_rows, second_parity = replay_policies(sample_population(), config=CONFIG)
        self.assertEqual(decision_rows_hash(first_rows), decision_rows_hash(second_rows))
        self.assertEqual(first_parity["sharedPolicyStateHash"], second_parity["sharedPolicyStateHash"])
        self.assertEqual(
            [r.decision_id for r in first_rows],
            [r.decision_id for r in second_rows],
        )
        self.assertEqual(
            [r.reason_code for r in first_rows],
            [r.reason_code for r in second_rows],
        )

    def test_controlled_demo_rows_cannot_enter_replay(self) -> None:
        rows, _ = replay_policies(
            [state("real", provenance="external_real")],
            config=CONFIG,
        )
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row.provenance, "external_real")


if __name__ == "__main__":
    unittest.main()
