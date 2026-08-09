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
    MIN_INDEPENDENT_LEARNERS_FOR_CI,
    SPARSE_CI_FLAG,
    MatchedOutcomeError,
    OutcomeGateError,
    attach_outcomes,
    attach_matched_outcome,
    bkt_calibration,
    build_next_tier_lookup,
    classify_matched_row,
    matched_outcome_summary,
    policy_direction_outcome_summary,
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
            require_frozen_bootstrap_config(None)

    def test_frozen_config_is_returned_from_v13_contract(self) -> None:
        from external_data.assistments.adaptive.external_policy_contract import (
            EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION,
            load_external_adaptive_contract,
        )

        contract = load_external_adaptive_contract(
            AI_PIPELINE
            / "external_data"
            / "assistments"
            / "adaptive"
            / "assistments_adaptive_contract_v1_3.yaml",
            version=EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION,
        )
        config = require_frozen_bootstrap_config(contract)
        self.assertEqual(config.seed, 20260716)
        self.assertEqual(config.iterations, 2000)
        self.assertEqual(config.confidence_level, 0.95)
        self.assertEqual(config.version, "assistments-adaptive-contract-v1.3")

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
            contract_path_v1_3=adaptive / "assistments_adaptive_contract_v1_3.yaml",
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
        self.assertIn("contractHashV1_3", result)

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
                    contract_path_v1_3=adaptive / "assistments_adaptive_contract_v1_3.yaml",
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


class V1_3OutcomeAnalysisTests(unittest.TestCase):
    def test_frozen_config_values(self) -> None:
        self.assertEqual(MIN_INDEPENDENT_LEARNERS_FOR_CI, 10)
        self.assertEqual(SPARSE_CI_FLAG, "sparse_independent_learner_evidence")

    def test_less_than_10_learners_suppresses_ci(self) -> None:
        attempts = [
            attempt(f"a{u}0", f"u{u}", "6.NS.A.1", tier="proxy_easy", ts=BASE + _day(u * 2))
            for u in range(3)
        ] + [
            attempt(f"a{u}1", f"u{u}", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(u * 2 + 1))
            for u in range(3)
        ]
        decisions = [
            decision(f"a{u}0", "P1", "up", "proxy_easy", f"u{u}")
            for u in range(3)
        ]
        rows = structural_matching(decisions, attempts)
        results = attach_outcomes(rows, attempts)
        config = FrozenBootstrapConfig(
            version="assistments-adaptive-contract-v1.3",
            seed=20260716,
            iterations=2000,
            confidence_level=0.95,
        )
        summary = policy_direction_outcome_summary(results, config)
        up = summary["P1"]["up"]
        self.assertLess(up["independentLearners"], 10)
        self.assertIsNone(up["supportNeededCi"])
        self.assertIsNone(up["successCi"])
        self.assertEqual(up["ciStatus"], SPARSE_CI_FLAG)

    def test_10_or_more_learners_permits_ci(self) -> None:
        attempts = [
            attempt(f"a{i}0", f"u{i}", "6.NS.A.1", tier="proxy_easy", ts=BASE + _day(i * 2))
            for i in range(20)
        ] + [
            attempt(f"a{i}1", f"u{i}", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(i * 2 + 1))
            for i in range(20)
        ]
        decisions = [
            decision(f"a{i}0", "P1", "up", "proxy_easy", f"u{i}")
            for i in range(20)
        ]
        rows = structural_matching(decisions, attempts)
        results = attach_outcomes(rows, attempts)
        config = FrozenBootstrapConfig(
            version="assistments-adaptive-contract-v1.3",
            seed=20260716,
            iterations=2000,
            confidence_level=0.95,
        )
        summary = policy_direction_outcome_summary(results, config)
        up = summary["P1"]["up"]
        self.assertGreaterEqual(up["independentLearners"], 10)
        self.assertIsNotNone(up["supportNeededCi"])
        self.assertIsNotNone(up["successCi"])
        self.assertEqual(up["ciStatus"], "computed")

    def test_repeated_rows_from_one_learner_do_not_increase_learner_count(self) -> None:
        attempts = [
            attempt("a1", "u1", "6.NS.A.1", tier="proxy_easy"),
            attempt("a2", "u1", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(1)),
            attempt("a3", "u1", "6.NS.A.1", tier="proxy_easy", ts=BASE + _day(2)),
            attempt("a4", "u1", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(3)),
            attempt("a5", "u2", "6.NS.A.1", tier="proxy_easy", ts=BASE + _day(4)),
            attempt("a6", "u2", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(5)),
        ]
        decisions = [
            decision("a1", "P1", "up", "proxy_easy", "u1"),
            decision("a3", "P1", "up", "proxy_easy", "u1"),
            decision("a5", "P1", "up", "proxy_easy", "u2"),
        ]
        rows = structural_matching(decisions, attempts)
        results = attach_outcomes(rows, attempts)
        matched = [r for r in results if r.outcome_status == "matched"]
        self.assertEqual(len(matched), 3)
        learners = {r.external_student_key for r in matched}
        # u1 contributes two matched rows but counts as ONE independent learner.
        self.assertEqual(len(learners), 2)

    def test_brier_semantics_use_later_success_one(self) -> None:
        attempts = [
            attempt("a1", "u1", "6.NS.A.1", tier="proxy_easy", correct=0.50),
            attempt("a2", "u1", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(1), correct=0.90),
        ]
        # a1 mastery is 0.6 (from the attempt() helper); next success -> (0.6-1)^2.
        config = FrozenBootstrapConfig(
            version="v1.3", seed=20260716, iterations=2000, confidence_level=0.95
        )
        calibration = bkt_calibration(
            attempts,
            ["a1"],
            config,
        )
        self.assertIsNotNone(calibration["brierScore"])
        expected = (0.6 - 1.0) ** 2
        self.assertAlmostEqual(calibration["brierScore"], expected)

    def test_e6_manifest_binds_frozen_e5_decision_audit(self) -> None:
        from external_data.assistments.adaptive.matched_outcomes import (
            E5_DECISION_AUDIT_HASH,
            build_e6_manifest,
        )

        verification = {
            "contractHashV1_3": "0" * 64,
            "e2CatalogHash": "1" * 64,
            "e3AttemptsHash": "2" * 64,
            "e4ReadinessManifestHash": "3" * 64,
            "e5DecisionAuditHash": E5_DECISION_AUDIT_HASH,
            "e5ManifestHash": "4" * 64,
        }
        structural = {
            p: {
                "matchedOutcomes": 0,
                "matchedLearners": 0,
                "matchedSkills": 0,
                "matchedByDirection": {"up": 0, "hold": 0, "down": 0},
                "censorCounts": {},
                "matchedOutcomeCoverage": 0.0,
            }
            for p in ("P1", "P2", "P3a")
        }
        empty_summary = {
            p: {
                d: {
                    "matchedDecisions": 0,
                    "independentLearners": 0,
                    "skills": 0,
                    "supportNeededCount": 0,
                    "laterSuccessCount": 0,
                    "supportNeededRate": 0.0,
                    "successRate": 0.0,
                    "supportNeededCi": None,
                    "successCi": None,
                    "ciStatus": "not_estimable",
                }
                for d in ("up", "hold", "down")
            }
            for p in ("P1", "P2", "P3a")
        }
        config = FrozenBootstrapConfig(
            version="assistments-adaptive-contract-v1.3",
            seed=20260716,
            iterations=2000,
            confidence_level=0.95,
        )
        manifest = build_e6_manifest(
            verification=verification,
            structural_summary=structural,
            outcome_summary=empty_summary,
            eb4={p: {"matchedUpDecisions": 0} for p in ("P1", "P2", "P3a")},
            bkt_cal={"populationRowCount": 0, "populationLearnerCount": 0},
            coverage={p: {} for p in ("P1", "P2", "P3a")},
            bootstrap_config=config,
            matched_outcomes_hash="0" * 64,
        )
        self.assertEqual(manifest["e5DecisionAuditHash"], E5_DECISION_AUDIT_HASH)
        self.assertFalse(manifest["causalClaimAllowed"])
        self.assertFalse(manifest["productionPromotionAllowed"])


class CiLabelConsistencyTests(unittest.TestCase):
    """E6 reporting-consistency: support/success rates and CI complements."""

    def _summary(self, matched: list[tuple[str, str, str, bool]]) -> dict[str, object]:
        config = FrozenBootstrapConfig(
            version="assistments-adaptive-contract-v1.3",
            seed=20260716,
            iterations=2000,
            confidence_level=0.95,
        )
        # matched rows: (state_key, learner, policy, support_needed)
        attempts = []
        for index, (state_key, learner, _policy, _support) in enumerate(matched):
            attempts.append(
                attempt(
                    state_key,
                    learner,
                    "6.NS.A.1",
                    tier="proxy_easy",
                    ts=BASE + _day(index * 2),
                )
            )
            attempts.append(
                attempt(
                    f"{state_key}-n",
                    learner,
                    "6.NS.A.1",
                    tier="proxy_moderate",
                    ts=BASE + _day(index * 2 + 1),
                    correct=0.50 if _support else 0.80,
                )
            )
        decisions = [
            decision(state_key, policy, "up", "proxy_easy", learner)
            for state_key, learner, policy, _support in matched
        ]
        rows = structural_matching(decisions, attempts)
        results = attach_outcomes(rows, attempts)
        summary = policy_direction_outcome_summary(results, config)
        return summary

    def test_support_and_success_rates_use_their_counts_over_denominator(self) -> None:
        matched = [
            ("s1", "u1", "P1", True),
            ("s2", "u2", "P1", False),
            ("s3", "u3", "P1", False),
            ("s4", "u4", "P1", False),
            ("s5", "u5", "P1", False),
            ("s6", "u6", "P1", False),
            ("s7", "u7", "P1", False),
            ("s8", "u8", "P1", False),
            ("s9", "u9", "P1", False),
            ("s10", "u10", "P1", False),
        ]
        summary = self._summary(matched)
        up = summary["P1"]["up"]
        self.assertEqual(up["supportNeededCount"], 1)
        self.assertEqual(up["laterSuccessCount"], 9)
        self.assertEqual(up["matchedDecisions"], 10)
        self.assertAlmostEqual(up["supportNeededRate"], 0.1)
        self.assertAlmostEqual(up["successRate"], 0.9)

    def test_support_plus_success_equals_denominator(self) -> None:
        matched = [("s1", "u1", "P1", True), ("s2", "u2", "P1", False)]
        summary = self._summary(matched)
        up = summary["P1"]["up"]
        self.assertEqual(
            up["supportNeededCount"] + up["laterSuccessCount"],
            up["matchedDecisions"],
        )

    def test_success_rate_is_one_minus_support_rate(self) -> None:
        matched = [("s1", "u1", "P1", True), ("s2", "u2", "P1", False)]
        summary = self._summary(matched)
        up = summary["P1"]["up"]
        self.assertAlmostEqual(up["successRate"], 1.0 - up["supportNeededRate"])

    def test_displayed_support_ci_belongs_to_support_rate(self) -> None:
        matched = [
            ("s1", "u1", "P1", True),
            ("s2", "u2", "P1", False),
            ("s3", "u3", "P1", False),
            ("s4", "u4", "P1", False),
            ("s5", "u5", "P1", False),
            ("s6", "u6", "P1", False),
            ("s7", "u7", "P1", False),
            ("s8", "u8", "P1", False),
            ("s9", "u9", "P1", False),
            ("s10", "u10", "P1", False),
        ]
        summary = self._summary(matched)
        up = summary["P1"]["up"]
        support_ci = up["supportNeededCi"]
        self.assertIsNotNone(support_ci)
        # The bootstrapped support CI must straddle the support rate (0.1).
        self.assertLessEqual(support_ci[0], 0.1)
        self.assertGreaterEqual(support_ci[1], 0.1)

    def test_displayed_success_ci_belongs_to_success_rate(self) -> None:
        matched = [
            ("s1", "u1", "P1", True),
            ("s2", "u2", "P1", False),
            ("s3", "u3", "P1", False),
            ("s4", "u4", "P1", False),
            ("s5", "u5", "P1", False),
            ("s6", "u6", "P1", False),
            ("s7", "u7", "P1", False),
            ("s8", "u8", "P1", False),
            ("s9", "u9", "P1", False),
            ("s10", "u10", "P1", False),
        ]
        summary = self._summary(matched)
        up = summary["P1"]["up"]
        success_ci = up["successCi"]
        self.assertIsNotNone(success_ci)
        self.assertLessEqual(success_ci[0], 0.9)
        self.assertGreaterEqual(success_ci[1], 0.9)

    def test_success_ci_is_exact_complement_of_support_ci(self) -> None:
        matched = [
            ("s1", "u1", "P1", True),
            ("s2", "u2", "P1", False),
            ("s3", "u3", "P1", False),
            ("s4", "u4", "P1", False),
            ("s5", "u5", "P1", False),
            ("s6", "u6", "P1", False),
            ("s7", "u7", "P1", False),
            ("s8", "u8", "P1", False),
            ("s9", "u9", "P1", False),
            ("s10", "u10", "P1", False),
        ]
        summary = self._summary(matched)
        up = summary["P1"]["up"]
        support_ci = up["supportNeededCi"]
        success_ci = up["successCi"]
        self.assertIsNotNone(support_ci)
        self.assertIsNotNone(success_ci)
        self.assertAlmostEqual(success_ci[0], 1.0 - support_ci[1])
        self.assertAlmostEqual(success_ci[1], 1.0 - support_ci[0])

    def test_sparse_subsets_remain_suppressed_for_both_representations(self) -> None:
        matched = [("s1", "u1", "P3a", True), ("s2", "u2", "P3a", False)]
        summary = self._summary(matched)
        up = summary["P3a"]["up"]
        self.assertLess(up["independentLearners"], 10)
        self.assertIsNone(up["supportNeededCi"])
        self.assertIsNone(up["successCi"])
        self.assertEqual(up["ciStatus"], SPARSE_CI_FLAG)

    def test_no_outcome_counts_change_with_labeling(self) -> None:
        matched = [("s1", "u1", "P1", True), ("s2", "u2", "P1", False)]
        first = self._summary(matched)
        second = self._summary(matched)
        self.assertEqual(
            first["P1"]["up"]["supportNeededCount"],
            second["P1"]["up"]["supportNeededCount"],
        )
        self.assertEqual(
            first["P1"]["up"]["laterSuccessCount"],
            second["P1"]["up"]["laterSuccessCount"],
        )

    def test_bootstrap_settings_are_frozen(self) -> None:
        config = FrozenBootstrapConfig(
            version="assistments-adaptive-contract-v1.3",
            seed=20260716,
            iterations=2000,
            confidence_level=0.95,
        )
        self.assertEqual(config.seed, 20260716)
        self.assertEqual(config.iterations, 2000)
        self.assertEqual(config.confidence_level, 0.95)

    def test_matched_row_hash_is_unchanged_by_labeling(self) -> None:
        from external_data.assistments.adaptive.matched_outcomes import (
            matched_outcome_results_hash,
        )

        matched = [("s1", "u1", "P1", True), ("s2", "u2", "P1", False)]
        summary = self._summary(matched)
        self.assertIn("P1", summary)
        # The labeling correction never changes the underlying row documents.
        config = FrozenBootstrapConfig(
            version="assistments-adaptive-contract-v1.3",
            seed=20260716,
            iterations=2000,
            confidence_level=0.95,
        )
        attempts = [
            attempt("s10", "u1", "6.NS.A.1", tier="proxy_easy"),
            attempt("s11", "u1", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(1)),
            attempt("s20", "u2", "6.NS.A.1", tier="proxy_easy"),
            attempt("s21", "u2", "6.NS.A.1", tier="proxy_moderate", ts=BASE + _day(1)),
        ]
        decisions = [
            decision("s10", "P1", "up", "proxy_easy", "u1"),
            decision("s20", "P1", "up", "proxy_easy", "u2"),
        ]
        rows = structural_matching(decisions, attempts)
        results = attach_outcomes(rows, attempts)
        first_hash = matched_outcome_results_hash(results)
        second_hash = matched_outcome_results_hash(results)
        self.assertEqual(first_hash, second_hash)

    def test_e5_decision_hash_is_unchanged(self) -> None:
        from external_data.assistments.adaptive.matched_outcomes import (
            E5_DECISION_AUDIT_HASH,
        )

        self.assertEqual(
            E5_DECISION_AUDIT_HASH,
            "75d9b9bdece8f410b787d68d7f7e99c3fb8405785bf142380683d704ff2907ab",
        )


def _day(n: int):
    from datetime import timedelta

    return timedelta(days=n)


if __name__ == "__main__":
    unittest.main()
