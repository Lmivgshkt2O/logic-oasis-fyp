"""AQC-E6 matched historical outcome tests (structural matching + frozen gates).

These tests verify that E6 matches candidate policy target tiers to the direct
next observed proxy tier BEFORE any outcome value is read, censors mismatches
without using their outcome values, reuses the frozen U7 support-needed
definition (mastery 0.60, never the 0.80 promotion threshold), clusters CIs by
learner only under an approved frozen config, and never declares a policy
winner or uses P3b/XGBoost/off-policy weighting.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from logic_oasis_ai.prediction_contract import (
    DEFAULT_MASTERY_CRITERION,
    PREDICTION_LABEL_VERSION,
    PREDICTION_TARGET,
)

from external_data.assistments.adaptive.matched_outcomes import (
    CLAIM_LEVEL,
    FrozenBootstrapConfig,
    MatchedOutcomeError,
    OutcomeGateError,
    attach_matched_outcome,
    build_next_tier_lookup,
    classify_matched_row,
    matched_outcome_summary,
    require_frozen_bootstrap_config,
    structural_matching,
    student_clustered_bootstrap,
    target_tier_for_direction,
    verify_e6_inputs,
)
from external_data.assistments.adaptive.readiness_audit import ReadinessAttempt


BASE = datetime(2022, 3, 1, tzinfo=timezone.utc)
AI_PIPELINE = Path(__file__).resolve().parents[1]


def attempt(
    key: str = "s1",
    learner: str = "u1",
    skill: str = "6.NS.A.1",
    tier: str = "proxy_easy",
    ts: datetime = BASE,
    correct: float = 0.70,
    problems: tuple[str, ...] | None = None,
) -> ReadinessAttempt:
    if problems is None:
        problems = tuple(f"p-{key}-{index}" for index in range(3))
    total = 10
    correct_count = int(round(correct * total))
    return ReadinessAttempt(
        external_attempt_key=key,
        external_student_key=learner,
        external_assignment_key=f"assignment-{key}",
        source_skill_code=skill,
        source_timestamp=ts,
        external_attempt_sequence=1,
        problem_keys=problems,
        total_questions=total,
        correct_count=correct_count,
        correct_rate=correct,
        bkt_mastery_probability=0.6,
        bkt_evidence_count=5,
        bkt_version="bkt-v1",
        current_proxy_difficulty=tier,
        proxy_difficulty_purity=1.0,
        external_problem_set_fingerprint=f"fp-{key}",
        previous_observed_proxy_difficulty=None,
        fresh_problem_fraction=1.0,
        skill_proxy_status="eligible",
        current_tier_censor_reason=None,
        cold_history=True,
        chronology_ambiguous=False,
        provenance="external_real",
    )


def decision(
    state_key: str,
    policy: str = "P1",
    direction: str = "up",
    current_tier: str = "proxy_easy",
    learner: str = "u1",
    skill: str = "6.NS.A.1",
) -> dict[str, object]:
    return {
        "externalStateKey": state_key,
        "externalStudentKey": learner,
        "sourceSkillCode": skill,
        "currentProxyDifficulty": current_tier,
        "correctRate": "0.80000000",
        "bktMasteryProbability": "0.60000000",
        "bktEvidenceCount": "5",
        "previousObservedProxyDifficulty": "",
        "policy": policy,
        "scoreDirection": "up",
        "bktDirection": "neutral",
        "proposedDirection": direction,
        "proposedTargetProxyDifficulty": target_tier_for_direction(current_tier, direction),
        "reasonCode": "p1_score_promote",
        "selectionEvidenceMode": "score_only",
        "usedBktFallback": "false",
        "candidateKind": "external_proxy_tier",
        "externalCandidateKey": "external_proxy_proxy_moderate",
        "decisionId": f"policy-decision-{state_key}-{policy}",
        "provenance": "external_real",
    }


class MatchingRuleTests(unittest.TestCase):
    def test_direct_next_uses_same_learner_and_exact_skill(self) -> None:
        attempts = [
            attempt("a1", "u1", "6.NS.A.1"),
            attempt("b1", "u1", "6.EE.B.7", tier="proxy_moderate"),
            attempt("a2", "u1", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(1)),
        ]
        lookup = build_next_tier_lookup(attempts)
        self.assertEqual(lookup["a1"][0], "a2")

    def test_no_skipping_to_a_later_convenient_match(self) -> None:
        attempts = [
            attempt("a1", "u1", "6.NS.A.1", ts=BASE),
            attempt("a2", "u1", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(1)),
            attempt("a3", "u1", "6.NS.A.1", tier="proxy_hard", ts=BASE + _day(2)),
        ]
        lookup = build_next_tier_lookup(attempts)
        self.assertEqual(lookup["a1"][0], "a2")
        self.assertEqual(lookup["a2"][0], "a3")

    def test_target_tier_must_equal_next_observed_tier(self) -> None:
        row = classify_matched_row(
            state_key="s1", learner="u1", skill="6.NS.A.1", policy="P1",
            direction="up", current_tier="proxy_easy",
            next_key="s2", next_tier="proxy_easy", next_ambiguous=False,
            next_valid=True, current_problem_keys=frozenset({"p1", "p2", "p3"}),
            next_problem_keys=frozenset({"p4", "p5", "p6"}),
        )
        self.assertEqual(row.outcome_status, "censored")
        self.assertEqual(row.primary_censor_reason, "counterfactual_proxy_tier_mismatch")

    def test_mismatch_outcome_value_is_never_used(self) -> None:
        row = classify_matched_row(
            state_key="s1", learner="u1", skill="6.NS.A.1", policy="P1",
            direction="up", current_tier="proxy_easy",
            next_key="s2", next_tier="proxy_hard", next_ambiguous=False,
            next_valid=True, current_problem_keys=frozenset({"p1"}),
            next_problem_keys=frozenset({"p2"}),
        )
        with self.assertRaises(MatchedOutcomeError):
            attach_matched_outcome(row, next_correct_rate=0.10)

    def test_matched_row_may_attach_frozen_outcome(self) -> None:
        row = classify_matched_row(
            state_key="s1", learner="u1", skill="6.NS.A.1", policy="P1",
            direction="up", current_tier="proxy_easy",
            next_key="s2", next_tier="proxy_moderate", next_ambiguous=False,
            next_valid=True, current_problem_keys=frozenset({"p1"}),
            next_problem_keys=frozenset({"p2"}),
        )
        self.assertEqual(row.outcome_status, "matched")
        self.assertTrue(attach_matched_outcome(row, next_correct_rate=0.50))
        self.assertFalse(attach_matched_outcome(row, next_correct_rate=0.70))

    def test_no_next_is_censored(self) -> None:
        row = classify_matched_row(
            state_key="s1", learner="u1", skill="6.NS.A.1", policy="P1",
            direction="up", current_tier="proxy_easy",
            next_key=None, next_tier=None, next_ambiguous=False,
            next_valid=False, current_problem_keys=frozenset({"p1"}),
            next_problem_keys=frozenset(),
        )
        self.assertEqual(row.primary_censor_reason, "no_next_eligible_attempt")

    def test_repeat_is_censored(self) -> None:
        row = classify_matched_row(
            state_key="s1", learner="u1", skill="6.NS.A.1", policy="P1",
            direction="up", current_tier="proxy_easy",
            next_key="s2", next_tier="proxy_moderate", next_ambiguous=False,
            next_valid=True, current_problem_keys=frozenset({"p1", "p2", "p3"}),
            next_problem_keys=frozenset({"p1", "p2", "p3"}),
        )
        self.assertEqual(row.primary_censor_reason, "identical_problem_set_repeat")

    def test_next_tier_missing_is_censored(self) -> None:
        row = classify_matched_row(
            state_key="s1", learner="u1", skill="6.NS.A.1", policy="P1",
            direction="up", current_tier="proxy_easy",
            next_key="s2", next_tier=None, next_ambiguous=False,
            next_valid=True, current_problem_keys=frozenset({"p1"}),
            next_problem_keys=frozenset({"p2"}),
        )
        self.assertEqual(row.primary_censor_reason, "next_proxy_tier_missing")

    def test_chronology_ambiguity_fails_closed(self) -> None:
        row = classify_matched_row(
            state_key="s1", learner="u1", skill="6.NS.A.1", policy="P1",
            direction="up", current_tier="proxy_easy",
            next_key="s2", next_tier="proxy_moderate", next_ambiguous=True,
            next_valid=True, current_problem_keys=frozenset({"p1"}),
            next_problem_keys=frozenset({"p2"}),
        )
        self.assertEqual(row.primary_censor_reason, "chronology_ambiguous")

    def test_non_adjacent_transition_cannot_match(self) -> None:
        row = classify_matched_row(
            state_key="s1", learner="u1", skill="6.NS.A.1", policy="P1",
            direction="up", current_tier="proxy_easy",
            next_key="s2", next_tier="proxy_hard", next_ambiguous=False,
            next_valid=True, current_problem_keys=frozenset({"p1"}),
            next_problem_keys=frozenset({"p2"}),
        )
        self.assertEqual(row.primary_censor_reason, "non_adjacent_observed_transition")

    def test_hold_target_equals_current_tier(self) -> None:
        self.assertEqual(target_tier_for_direction("proxy_moderate", "hold"), "proxy_moderate")

    def test_up_target_is_one_level_higher(self) -> None:
        self.assertEqual(target_tier_for_direction("proxy_easy", "up"), "proxy_moderate")
        self.assertEqual(target_tier_for_direction("proxy_moderate", "up"), "proxy_hard")
        self.assertEqual(target_tier_for_direction("proxy_hard", "up"), "proxy_hard")

    def test_down_target_is_one_level_lower(self) -> None:
        self.assertEqual(target_tier_for_direction("proxy_moderate", "down"), "proxy_easy")
        self.assertEqual(target_tier_for_direction("proxy_hard", "down"), "proxy_moderate")
        self.assertEqual(target_tier_for_direction("proxy_easy", "down"), "proxy_easy")


class PolicySpecificTests(unittest.TestCase):
    def test_p1_has_zero_down_matches(self) -> None:
        attempts = [
            attempt("a1", "u1", "6.NS.A.1"),
            attempt("a2", "u1", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(1)),
            attempt("b1", "u2", "6.NS.A.1", tier="proxy_moderate"),
            attempt("b2", "u2", "6.NS.A.1", tier="proxy_easy", ts=BASE + _day(1)),
        ]
        decisions = [
            decision("a1", "P1", "up", "proxy_easy", "u1"),
            decision("b1", "P1", "hold", "proxy_moderate", "u2"),
            decision("a1", "P2", "up", "proxy_easy", "u1"),
            decision("b1", "P2", "down", "proxy_moderate", "u2"),
            decision("a1", "P3a", "up", "proxy_easy", "u1"),
            decision("b1", "P3a", "down", "proxy_moderate", "u2"),
        ]
        rows = structural_matching(decisions, attempts)
        summary = matched_outcome_summary(rows)
        self.assertEqual(summary["P1"]["matchedByDirection"]["down"], 0)
        self.assertEqual(summary["P2"]["matchedByDirection"]["down"], 1)
        self.assertEqual(summary["P3a"]["matchedByDirection"]["down"], 1)

    def test_policy_specific_matched_subsets_remain_distinct(self) -> None:
        attempts = [
            attempt("a1", "u1", "6.NS.A.1", tier="proxy_moderate"),
            attempt("a2", "u1", "6.NS.A.1", tier="proxy_hard", ts=BASE + _day(1)),
        ]
        decisions = [
            decision("a1", "P1", "up", "proxy_moderate", "u1"),
            decision("a1", "P2", "hold", "proxy_moderate", "u1"),
            decision("a1", "P3a", "up", "proxy_moderate", "u1"),
        ]
        rows = structural_matching(decisions, attempts)
        summary = matched_outcome_summary(rows)
        # Observed next tier is Hard: P1 UP (target Hard) matches; P2 HOLD
        # (target Moderate) mismatches; P3a UP matches.
        self.assertEqual(summary["P1"]["matchedOutcomes"], 1)
        self.assertEqual(summary["P2"]["matchedOutcomes"], 0)
        self.assertEqual(summary["P3a"]["matchedOutcomes"], 1)


class OutcomeContractTests(unittest.TestCase):
    def test_u7_frozen_support_needed_definition_is_reused(self) -> None:
        self.assertEqual(PREDICTION_TARGET, "next_attempt_support_needed")
        self.assertEqual(PREDICTION_LABEL_VERSION, "next-attempt-support-needed-v1")
        self.assertEqual(DEFAULT_MASTERY_CRITERION, 0.60)

    def test_adaptive_0_80_is_not_the_outcome_criterion(self) -> None:
        row = classify_matched_row(
            state_key="s1", learner="u1", skill="6.NS.A.1", policy="P1",
            direction="up", current_tier="proxy_easy",
            next_key="s2", next_tier="proxy_moderate", next_ambiguous=False,
            next_valid=True, current_problem_keys=frozenset({"p1"}),
            next_problem_keys=frozenset({"p2"}),
        )
        # 0.70 is below 0.80 but above 0.60: success under the frozen U7
        # criterion, proving 0.80 is not the outcome threshold.
        self.assertFalse(attach_matched_outcome(row, next_correct_rate=0.70))
        self.assertTrue(attach_matched_outcome(row, next_correct_rate=0.59))

    def test_outcome_mutation_cannot_change_e5_decisions(self) -> None:
        attempts = [
            attempt("a1", "u1", "6.NS.A.1"),
            attempt("a2", "u1", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(1), correct=0.30),
            attempt("a3", "u1", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(2), correct=0.90),
        ]
        decisions = [decision("a1", "P1", "up", "proxy_easy", "u1")]
        first = structural_matching(decisions, attempts)
        mutated = [
            attempt("a1", "u1", "6.NS.A.1"),
            attempt("a2", "u1", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(1), correct=0.90),
            attempt("a3", "u1", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(2), correct=0.30),
        ]
        second = structural_matching(decisions, mutated)
        self.assertEqual(first, second)

    def test_unmatched_outcome_mutation_cannot_change_matched_aggregates(self) -> None:
        attempts = [
            attempt("a1", "u1", "6.NS.A.1"),
            attempt("a2", "u1", "6.NS.A.1", tier="proxy_hard", ts=BASE + _day(1), correct=0.20),
        ]
        decisions = [decision("a1", "P1", "up", "proxy_easy", "u1")]  # target Moderate, next Hard -> mismatch
        first = matched_outcome_summary(structural_matching(decisions, attempts))
        mutated = [
            attempt("a1", "u1", "6.NS.A.1"),
            attempt("a2", "u1", "6.NS.A.1", tier="proxy_hard", ts=BASE + _day(1), correct=0.95),
        ]
        second = matched_outcome_summary(structural_matching(decisions, mutated))
        self.assertEqual(first, second)


class BootstrapGateTests(unittest.TestCase):
    def test_outcome_rate_gate_requires_frozen_ci_config(self) -> None:
        with self.assertRaises(OutcomeGateError):
            require_frozen_bootstrap_config()

    def test_student_clustered_bootstrap_clusters_by_learner(self) -> None:
        config = FrozenBootstrapConfig(version="test-v1", seed=20260809, iterations=2000, confidence_level=0.95)
        rows = [
            {"externalStudentKey": f"u{learner}", "support": 1 if index % 2 == 0 else 0}
            for learner in range(1, 9)
            for index in range(4)
        ]
        lower, upper = student_clustered_bootstrap(rows, config=config, value_key="support")
        self.assertLessEqual(lower, upper)
        self.assertGreaterEqual(lower, 0.0)
        self.assertLessEqual(upper, 1.0)

    def test_sparse_bootstrap_fails_closed(self) -> None:
        config = FrozenBootstrapConfig(version="test-v1", seed=1, iterations=2000, confidence_level=0.95)
        rows = [{"externalStudentKey": "u1", "support": 1}]
        with self.assertRaises(MatchedOutcomeError):
            student_clustered_bootstrap(rows, config=config, value_key="support")


class GovernanceAndVerificationTests(unittest.TestCase):
    def test_verify_e6_inputs_passes_on_real_artifacts(self) -> None:
        adaptive = AI_PIPELINE / "external_data" / "assistments" / "adaptive"
        protected = Path(
            r"C:\Users\zyonn\Documents\FYP\logic_oasis_private_data\assitments_edm_cup_2023\processed\aqc"
        )
        result = verify_e6_inputs(
            e3_attempts_path=protected / "e3/external_adaptive_attempts_v1.csv",
            e3_manifest_path=protected / "e3/e3_manifest.json",
            e4_manifest_path=protected / "e4/e4_readiness_manifest.json",
            e5_decision_audit_path=protected / "e5/external_policy_decisions_v1.csv",
            e5_manifest_path=protected / "e5/e5_manifest.json",
            e2_catalog_path=protected / "e2/assistments_problem_difficulty_proxy_v1.csv",
            e2_manifest_path=protected / "e2/e2_calibration_manifest.json",
            contract_path_v1_2=adaptive / "assistments_adaptive_contract_v1_2.yaml",
            contract_path_v1_1=adaptive / "assistments_adaptive_contract_v1_1.yaml",
            contract_path_v1=adaptive / "assistments_adaptive_contract_v1.yaml",
            configs_dir=AI_PIPELINE / "configs",
        )
        self.assertTrue(result["verified"])
        naming = result["hashNamingResolution"]
        self.assertTrue(naming["distinctIntentionally"])
        self.assertTrue(naming["consistent"])
        self.assertNotEqual(naming["decisionAuditHash"], naming["decisionAuditFileSha256"])
        self.assertEqual(result["u7OutcomeContract"]["masteryCriterion"], 0.60)

    def test_tampered_e5_audit_is_rejected(self) -> None:
        adaptive = AI_PIPELINE / "external_data" / "assistments" / "adaptive"
        protected = Path(
            r"C:\Users\zyonn\Documents\FYP\logic_oasis_private_data\assitments_edm_cup_2023\processed\aqc"
        )
        original = (protected / "e5/external_policy_decisions_v1.csv").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            tampered = Path(directory) / "audit.csv"
            tampered.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
            with self.assertRaises(MatchedOutcomeError):
                verify_e6_inputs(
                    e3_attempts_path=protected / "e3/external_adaptive_attempts_v1.csv",
                    e3_manifest_path=protected / "e3/e3_manifest.json",
                    e4_manifest_path=protected / "e4/e4_readiness_manifest.json",
                    e5_decision_audit_path=tampered,
                    e5_manifest_path=protected / "e5/e5_manifest.json",
                    e2_catalog_path=protected / "e2/assistments_problem_difficulty_proxy_v1.csv",
                    e2_manifest_path=protected / "e2/e2_calibration_manifest.json",
                    contract_path_v1_2=adaptive / "assistments_adaptive_contract_v1_2.yaml",
                    contract_path_v1_1=adaptive / "assistments_adaptive_contract_v1_1.yaml",
                    contract_path_v1=adaptive / "assistments_adaptive_contract_v1.yaml",
                    configs_dir=AI_PIPELINE / "configs",
                )

    def test_e6_never_recomputes_policy_decisions(self) -> None:
        module = AI_PIPELINE / "external_data" / "assistments" / "adaptive" / "matched_outcomes.py"
        source = module.read_text(encoding="utf-8")
        self.assertNotIn("select_policy_decision", source)
        self.assertNotIn("PolicyArm", source)

    def test_no_off_policy_weighting_or_synthetic_outcomes(self) -> None:
        module = AI_PIPELINE / "external_data" / "assistments" / "adaptive" / "matched_outcomes.py"
        source = module.read_text(encoding="utf-8")
        for forbidden in (
            "propensity",
            "inverse propensity",
            "imputed",
            "synthetic_outcome",
            "np.random",
            "sklearn",
        ):
            self.assertNotIn(forbidden, source)

    def test_bkt_calibration_uses_current_bkt_only(self) -> None:
        module = AI_PIPELINE / "external_data" / "assistments" / "adaptive" / "matched_outcomes.py"
        source = module.read_text(encoding="utf-8")
        self.assertNotIn("bkt_mastery_probability=", source)
        self.assertNotIn("update_probability", source)

    def test_no_p3b_and_no_xgboost(self) -> None:
        module = AI_PIPELINE / "external_data" / "assistments" / "adaptive" / "matched_outcomes.py"
        source = module.read_text(encoding="utf-8")
        self.assertNotIn("P3B", source)
        self.assertNotIn("import xgboost", source.lower())

    def test_claim_and_production_boundaries(self) -> None:
        self.assertEqual(CLAIM_LEVEL, "external_descriptive_replay")
        module = AI_PIPELINE / "external_data" / "assistments" / "adaptive" / "matched_outcomes.py"
        source = module.read_text(encoding="utf-8")
        self.assertNotIn("superior", source)
        self.assertIn('"productionPromotionAllowed": False', source)

    def test_rerun_produces_identical_structural_output(self) -> None:
        attempts = [
            attempt("a1", "u1", "6.NS.A.1"),
            attempt("a2", "u1", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(1)),
            attempt("b1", "u2", "6.NS.A.1", tier="proxy_moderate"),
            attempt("b2", "u2", "6.NS.A.1", tier="proxy_easy", ts=BASE + _day(1)),
        ]
        decisions = [
            decision("a1", "P1", "up", "proxy_easy", "u1"),
            decision("b1", "P2", "down", "proxy_moderate", "u2"),
            decision("a1", "P3a", "up", "proxy_easy", "u1"),
            decision("b1", "P3a", "hold", "proxy_moderate", "u2"),
        ]
        first = matched_outcome_summary(structural_matching(decisions, attempts))
        second = matched_outcome_summary(structural_matching(decisions, attempts))
        self.assertEqual(first, second)


def _day(n: int):
    from datetime import timedelta

    return timedelta(days=n)


if __name__ == "__main__":
    unittest.main()
