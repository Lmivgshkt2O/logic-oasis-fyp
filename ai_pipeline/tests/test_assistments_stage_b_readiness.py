"""AQC-E4 Stage-B readiness-audit tests (no protected data, no policy selectors).

These tests freeze the structural readiness rules: the shared policy-ready
funnel, per-tier counts, adjacent-tier availability, BKT/reversal/fresh
readiness, direct-next episode auditing, potential (structural) tier matches,
censoring, deterministic manifests, and the no-policy / outcome-value-blind
boundary of the E4 path.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from external_data.assistments.adaptive.readiness_audit import (
    ReadinessAttempt,
    ReadinessError,
    adjacent_tier_availability,
    boundary_opportunity_counts,
    build_e4_manifest,
    censoring_table,
    direct_next_audit,
    fresh_problem_summary,
    policy_ready_funnel,
    potential_tier_matches,
    reversal_history_summary,
    tier_stats,
)
from external_data.assistments.adaptive.run_readiness_audit import _decide


BASE = datetime(2022, 3, 1, tzinfo=timezone.utc)
ELIGIBLE_SKILLS = frozenset({"6.NS.A.1", "6.EE.B.7", "6.RP.A.3a"})


def attempt(
    key: str = "a1",
    learner: str = "student-1",
    skill: str = "6.NS.A.1",
    tier: str | None = "proxy_easy",
    previous_tier: str | None = None,
    ts: datetime = BASE,
    problems: tuple[str, ...] | None = None,
    correct: int = 2,
    total: int = 3,
    evidence: int = 6,
    mastery: float = 0.72,
    fresh: float | None = 1.0,
    cold: bool | None = None,
    censor: str | None = None,
    purity: float | None = None,
    ambiguous: bool = False,
) -> ReadinessAttempt:
    if cold is None:
        cold = previous_tier is None
    if purity is None:
        purity = 2 / 3 if tier else 0.0
    if problems is None:
        problems = tuple(f"p-{key}-{index}" for index in range(3))
    return ReadinessAttempt(
        external_attempt_key=key,
        external_student_key=learner,
        external_assignment_key=f"assignment-{key}",
        source_skill_code=skill,
        source_timestamp=ts,
        external_attempt_sequence=1,
        problem_keys=problems,
        total_questions=total,
        correct_count=correct,
        correct_rate=correct / total,
        bkt_mastery_probability=mastery,
        bkt_evidence_count=evidence,
        bkt_version="bkt-v1",
        current_proxy_difficulty=tier,
        proxy_difficulty_purity=purity,
        external_problem_set_fingerprint=f"fp-{key}",
        previous_observed_proxy_difficulty=previous_tier,
        fresh_problem_fraction=fresh,
        skill_proxy_status="eligible" if skill in ELIGIBLE_SKILLS else "not_eligible",
        current_tier_censor_reason=censor,
        cold_history=cold,
        chronology_ambiguous=ambiguous,
        provenance="external_real",
    )


def full_population() -> list[ReadinessAttempt]:
    rows = []
    for learner_index, learner in enumerate(("s1", "s2", "s3", "s4")):
        for skill in ("6.NS.A.1", "6.EE.B.7"):
            for tier_index, tier in enumerate(("proxy_easy", "proxy_moderate", "proxy_hard")):
                rows.append(
                    attempt(
                        key=f"a-{learner}-{skill}-{tier}",
                        learner=learner,
                        skill=skill,
                        tier=tier,
                        previous_tier=(
                            None
                            if tier_index == 0
                            else ("proxy_easy", "proxy_moderate")[tier_index - 1]
                        ),
                        ts=BASE + timedelta(days=tier_index),
                    )
                )
    return rows


class FunnelTests(unittest.TestCase):
    def test_only_full_eligible_skills_enter_shared_states(self) -> None:
        rows = [
            attempt(key="a1", skill="6.NS.A.1", tier="proxy_easy"),
            attempt(key="a2", skill="7.EE.A.2", tier="proxy_easy"),
        ]
        ready, funnel = policy_ready_funnel(rows, ELIGIBLE_SKILLS)
        self.assertEqual([a.external_attempt_key for a in ready], ["a1"])
        self.assertEqual(funnel["inEligibleSkills"]["attempts"], 1)

    def test_score_validity_is_required(self) -> None:
        bad = attempt(key="bad-score", correct=5, total=3)
        ready, _ = policy_ready_funnel([bad], ELIGIBLE_SKILLS)
        self.assertEqual(ready, [])

    def test_bkt_validity_is_required(self) -> None:
        bad = attempt(key="bad-bkt", evidence=0)
        ready, _ = policy_ready_funnel([bad], ELIGIBLE_SKILLS)
        self.assertEqual(ready, [])

    def test_current_proxy_difficulty_is_required(self) -> None:
        no_tier = attempt(key="no-tier", tier=None, purity=0.4, censor="mixed_proxy_difficulty")
        ready, funnel = policy_ready_funnel([no_tier], ELIGIBLE_SKILLS)
        self.assertEqual(ready, [])
        self.assertEqual(funnel["tierValidInEligible"]["attempts"], 0)

    def test_null_previous_tier_does_not_exclude_the_row(self) -> None:
        cold = attempt(key="cold", previous_tier=None, cold=True)
        ready, _ = policy_ready_funnel([cold], ELIGIBLE_SKILLS)
        self.assertEqual(len(ready), 1)
        self.assertTrue(ready[0].cold_history)

    def test_chronology_ambiguity_excludes_from_shared_states(self) -> None:
        ambiguous = attempt(key="amb", ambiguous=True)
        ready, _ = policy_ready_funnel([ambiguous], ELIGIBLE_SKILLS)
        self.assertEqual(ready, [])

    def test_funnel_reports_attempts_and_independent_learners(self) -> None:
        ready, funnel = policy_ready_funnel(full_population(), ELIGIBLE_SKILLS)
        self.assertEqual(funnel["sharedPolicyReady"]["attempts"], 24)
        self.assertEqual(funnel["sharedPolicyReady"]["learners"], 4)
        self.assertEqual(funnel["readyUniqueSkills"], 2)
        self.assertEqual(len(ready), 24)


class TierTests(unittest.TestCase):
    def test_all_three_tiers_are_counted_separately(self) -> None:
        stats = tier_stats(full_population())
        self.assertEqual(stats["proxy_easy"]["attempts"], 8)
        self.assertEqual(stats["proxy_moderate"]["attempts"], 8)
        self.assertEqual(stats["proxy_hard"]["attempts"], 8)
        self.assertEqual(stats["proxy_easy"]["learners"], 4)
        self.assertEqual(stats["proxy_easy"]["skills"], 2)

    def test_boundary_opportunity_counts_are_structural(self) -> None:
        counts = boundary_opportunity_counts(full_population())
        self.assertEqual(counts["statesAtLowerBoundary"], 8)
        self.assertEqual(counts["statesAtUpperBoundary"], 8)
        self.assertEqual(counts["statesWithUpTarget"], 16)
        self.assertEqual(counts["statesWithDownTarget"], 16)
        self.assertEqual(counts["statesWithHoldStructurallyPossible"], 24)

    def test_adjacent_tier_availability_is_full_for_eligible_skills(self) -> None:
        result = adjacent_tier_availability(full_population(), ELIGIBLE_SKILLS)
        self.assertEqual(result["fullAdjacentTierAvailabilityAttempts"], 24)
        self.assertEqual(result["missingAdjacentTierAttempts"], 0)

    def test_adjacent_tier_mismatch_fails_closed(self) -> None:
        rows = [attempt(key="x", skill="7.EE.A.2", tier="proxy_easy")]
        with self.assertRaises(ReadinessError):
            adjacent_tier_availability(rows, ELIGIBLE_SKILLS)


class ReversalAndFreshTests(unittest.TestCase):
    def test_reversal_history_uses_observed_tiers_only(self) -> None:
        rows = [
            attempt(key="cold", tier="proxy_easy", previous_tier=None),
            attempt(key="same", tier="proxy_moderate", previous_tier="proxy_moderate"),
            attempt(key="one", tier="proxy_hard", previous_tier="proxy_moderate"),
            attempt(key="non", tier="proxy_hard", previous_tier="proxy_easy"),
        ]
        summary = reversal_history_summary(rows)
        self.assertEqual(summary["noPreviousTier"], 1)
        self.assertEqual(summary["sameAsPrevious"], 1)
        self.assertEqual(summary["oneLevelChange"], 1)
        self.assertEqual(summary["nonAdjacentHistory"], 1)

    def test_fresh_problem_summary_reports_availability(self) -> None:
        rows = [
            attempt(key="f1", learner="learner-1", fresh=0.8),
            attempt(key="f2", learner="learner-2", fresh=None),
        ]
        summary = fresh_problem_summary(rows)
        self.assertEqual(summary["freshProblemFractionAvailable"], 1)
        self.assertEqual(summary["freshProblemFractionNull"], 1)
        self.assertEqual(summary["freshProblemLearnersRepresented"], 1)


class DirectNextTests(unittest.TestCase):
    def test_direct_next_uses_same_learner_and_exact_skill(self) -> None:
        rows = [
            attempt(key="a1", learner="s1", skill="6.NS.A.1", tier="proxy_easy"),
            attempt(key="b1", learner="s1", skill="6.EE.B.7", tier="proxy_moderate"),
            attempt(key="a2", learner="s1", skill="6.NS.A.1", tier="proxy_moderate", ts=BASE + timedelta(days=1)),
        ]
        pairs, counts = direct_next_audit(rows, rows)
        by_current = {pair["currentAttemptKey"]: pair for pair in pairs}
        self.assertEqual(by_current["a1"]["nextAttemptKey"], "a2")
        self.assertEqual(counts["valid"], 1)

    def test_direct_next_never_skips_intervening_episodes(self) -> None:
        rows = [
            attempt(key="a1", learner="s1", tier="proxy_easy", ts=BASE),
            attempt(key="a2", learner="s1", tier="proxy_moderate", ts=BASE + timedelta(days=1)),
            attempt(key="a3", learner="s1", tier="proxy_hard", ts=BASE + timedelta(days=2)),
        ]
        ready = [rows[0]]
        pairs, counts = direct_next_audit(ready, rows)
        self.assertEqual(pairs[0]["nextAttemptKey"], "a2")
        self.assertEqual(counts["valid"], 1)

    def test_no_next_is_censored(self) -> None:
        rows = [attempt(key="last", learner="s1", tier="proxy_easy")]
        _, counts = direct_next_audit(rows, rows)
        self.assertEqual(counts["none"], 1)

    def test_chronology_ambiguity_fails_closed(self) -> None:
        rows = [
            attempt(key="t1", learner="s1", tier="proxy_easy", ts=BASE),
            attempt(key="t2", learner="s1", tier="proxy_moderate", ts=BASE),
        ]
        _, counts = direct_next_audit(rows, rows)
        self.assertEqual(counts["chronologyAmbiguous"], 1)

    def test_identical_problem_set_repeat_is_separately_counted(self) -> None:
        rows = [
            attempt(key="r1", learner="s1", tier="proxy_easy", problems=("p1", "p2", "p3")),
            attempt(
                key="r2",
                learner="s1",
                tier="proxy_moderate",
                problems=("p1", "p2", "p3"),
                ts=BASE + timedelta(days=1),
            ),
        ]
        _, counts = direct_next_audit(rows, rows)
        self.assertEqual(counts["repeat"], 1)

    def test_next_missing_proxy_tier_is_separately_counted(self) -> None:
        rows = [
            attempt(key="n1", learner="s1", tier="proxy_easy"),
            attempt(
                key="n2",
                learner="s1",
                tier=None,
                purity=0.0,
                censor="mixed_proxy_difficulty",
                ts=BASE + timedelta(days=1),
            ),
        ]
        _, counts = direct_next_audit(rows, rows)
        self.assertEqual(counts["nextTierMissing"], 1)


class PotentialTierMatchTests(unittest.TestCase):
    def test_up_hold_down_matches_are_structural_only(self) -> None:
        rows = [
            attempt(key="e", learner="s1", tier="proxy_easy"),
            attempt(key="m1", learner="s1", tier="proxy_moderate", ts=BASE + timedelta(days=1)),
            attempt(key="m2", learner="s2", tier="proxy_moderate"),
            attempt(key="m2b", learner="s2", tier="proxy_moderate", ts=BASE + timedelta(days=1)),
            attempt(key="m3", learner="s3", tier="proxy_moderate"),
            attempt(key="e2", learner="s3", tier="proxy_easy", ts=BASE + timedelta(days=1)),
        ]
        pairs, counts = direct_next_audit(rows, rows)
        self.assertEqual(counts["valid"], 3)
        ready_by_key = {a.external_attempt_key: a for a in rows}
        matches = potential_tier_matches(pairs, ready_by_key)
        self.assertEqual(matches["potential_up_tier_match"]["pairs"], 1)
        self.assertEqual(matches["potential_hold_tier_match"]["pairs"], 1)
        self.assertEqual(matches["potential_down_tier_match"]["pairs"], 1)
        self.assertEqual(matches["potential_up_tier_match"]["learners"], 1)

    def test_non_adjacent_transition_is_not_a_policy_match(self) -> None:
        rows = [
            attempt(key="e", learner="s1", tier="proxy_easy"),
            attempt(key="h", learner="s1", tier="proxy_hard", ts=BASE + timedelta(days=1)),
        ]
        pairs, _ = direct_next_audit(rows, rows)
        ready_by_key = {a.external_attempt_key: a for a in rows}
        matches = potential_tier_matches(pairs, ready_by_key)
        self.assertEqual(matches["non_adjacent_observed_transition"]["pairs"], 1)
        self.assertEqual(matches["potential_up_tier_match"]["pairs"], 0)
        self.assertEqual(matches["potential_hold_tier_match"]["pairs"], 0)
        self.assertEqual(matches["potential_down_tier_match"]["pairs"], 0)


class CensoringTests(unittest.TestCase):
    def test_censoring_table_separates_categories(self) -> None:
        rows = [
            attempt(key="outside", skill="7.EE.A.2", tier="proxy_easy"),
            attempt(key="zero", skill="6.NS.A.1", tier=None, purity=0.0, censor="mixed_proxy_difficulty"),
            attempt(key="mixed", skill="6.NS.A.1", tier=None, purity=0.4, censor="mixed_proxy_difficulty"),
            attempt(key="ready1", skill="6.NS.A.1", tier="proxy_easy"),
        ]
        ready, _ = policy_ready_funnel(rows, ELIGIBLE_SKILLS)
        pairs, next_counts = direct_next_audit(ready, rows)
        table = censoring_table(rows, ready, ELIGIBLE_SKILLS, pairs)
        exclusive = table["mutuallyExclusiveStateCensors"]
        self.assertEqual(exclusive["outside_full_skill_catalog"]["attempts"], 1)
        self.assertEqual(exclusive["no_current_proxy_tier"]["attempts"], 2)
        self.assertEqual(exclusive["zero_tier_coverage"]["attempts"], 1)
        self.assertEqual(exclusive["mixed_proxy_difficulty"]["attempts"], 1)


class DecisionAndGovernanceTests(unittest.TestCase):
    def test_decision_uses_structure_not_outcome_values(self) -> None:
        rows = full_population()
        ready, funnel = policy_ready_funnel(rows, ELIGIBLE_SKILLS)
        tier_stats_ = tier_stats(ready)
        adjacent = adjacent_tier_availability(ready, ELIGIBLE_SKILLS)
        bkt = {
            "bktValidAttempts": len(ready),
            "bktValidLearners": 4,
        }
        pairs, next_counts = direct_next_audit(ready, rows)
        ready_by_key = {a.external_attempt_key: a for a in ready}
        matches = potential_tier_matches(pairs, ready_by_key)
        policy, matched, overall, components = _decide(
            funnel, tier_stats_, bkt, adjacent, next_counts, matches
        )
        self.assertEqual(policy, "PASS")
        self.assertIn(matched, ("adequate", "limited"))
        self.assertEqual(overall, "READY_FOR_EXTERNAL_POLICY_REPLAY")

    def test_decision_fails_closed_without_all_three_tiers(self) -> None:
        rows = [attempt(key="e1", learner="s1", tier="proxy_easy")]
        ready, funnel = policy_ready_funnel(rows, ELIGIBLE_SKILLS)
        tier_stats_ = tier_stats(ready)
        adjacent = adjacent_tier_availability(ready, ELIGIBLE_SKILLS)
        bkt = {"bktValidAttempts": len(ready)}
        pairs, next_counts = direct_next_audit(ready, rows)
        matches = potential_tier_matches(pairs, {a.external_attempt_key: a for a in ready})
        policy, matched, overall, _ = _decide(
            funnel, tier_stats_, bkt, adjacent, next_counts, matches
        )
        self.assertEqual(policy, "FAIL")
        self.assertEqual(overall, "NOT_READY_FOR_EXTERNAL_POLICY_REPLAY")

    def test_manifest_is_deterministic_and_governance_safe(self) -> None:
        verification = {
            "contractHashV1_2": "0" * 64,
            "predecessorContractHashV1_1": "1" * 64,
            "predecessorContractHashV1": "2" * 64,
            "e2CatalogHash": "3" * 64,
            "e3AttemptsHash": "4" * 64,
            "sourceReleaseHashes": {"action_logs.csv": "5" * 64},
        }
        first = build_e4_manifest(
            verification=verification,
            funnel={"sharedPolicyReady": {"attempts": 1, "learners": 1}, "readyUniqueSkills": 1},
            tier_stats_={"proxy_easy": {"attempts": 1}},
            adjacent={"fullAdjacentTierAvailabilityAttempts": 1},
            boundary={"statesWithUpTarget": 1},
            bkt={"bktValidAttempts": 1},
            reversal={"noPreviousTier": 1},
            fresh={"freshProblemFractionAvailable": 1},
            next_counts={"valid": 1},
            match_counts={"potential_up_tier_match": {"pairs": 1}},
            censoring={"mutuallyExclusiveStateCensors": {}},
            policy_replay_readiness="PASS",
            matched_outcome_readiness="limited",
            overall_decision="READY_FOR_EXTERNAL_POLICY_REPLAY",
            decision_components=["structural"],
        )
        second = build_e4_manifest(
            verification=verification,
            funnel={"sharedPolicyReady": {"attempts": 1, "learners": 1}, "readyUniqueSkills": 1},
            tier_stats_={"proxy_easy": {"attempts": 1}},
            adjacent={"fullAdjacentTierAvailabilityAttempts": 1},
            boundary={"statesWithUpTarget": 1},
            bkt={"bktValidAttempts": 1},
            reversal={"noPreviousTier": 1},
            fresh={"freshProblemFractionAvailable": 1},
            next_counts={"valid": 1},
            match_counts={"potential_up_tier_match": {"pairs": 1}},
            censoring={"mutuallyExclusiveStateCensors": {}},
            policy_replay_readiness="PASS",
            matched_outcome_readiness="limited",
            overall_decision="READY_FOR_EXTERNAL_POLICY_REPLAY",
            decision_components=["structural"],
        )
        self.assertEqual(first, second)
        self.assertNotIn("generatedAt", first)
        self.assertFalse(first["containsRawIdentifiers"])
        self.assertFalse(first["productionPromotionAllowed"])

    def test_e4_path_never_calls_policy_selectors_or_outcome_values(self) -> None:
        adaptive = Path(__file__).resolve().parents[1] / "external_data" / "assistments" / "adaptive"
        for filename in ("readiness_audit.py", "run_readiness_audit.py"):
            source = (adaptive / filename).read_text(encoding="utf-8")
            for forbidden in (
                "select_policy_decision",
                "PolicyArm",
                "DecisionDirection",
                "policy_evaluation",
                "false_promotion",
                "support_needed",
                "success_rate",
            ):
                self.assertNotIn(forbidden, source, f"{filename} must not reference {forbidden}")
        attempts_source = (adaptive / "readiness_audit.py").read_text(encoding="utf-8")
        self.assertNotIn("next_attempt_support_needed", attempts_source)

    def test_no_native_bank_fields_are_required_or_fabricated(self) -> None:
        fields = {name for name in ReadinessAttempt.__dataclass_fields__}
        for forbidden in ("bankId", "isActive", "finalizationStatus", "validationStatus"):
            self.assertNotIn(forbidden, fields)


if __name__ == "__main__":
    unittest.main()
