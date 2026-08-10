"""Aggregate descriptive Stage-B metrics with student-clustered intervals."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import isfinite
from random import Random
from typing import Iterable, Mapping

from .outcomes import CENSORED, OBSERVED, DecisionOutcome, OutcomeResult
from .replay import ReplayDecision, ReplayResult


class MetricsError(ValueError):
    """Raised when metrics cannot be computed safely."""


@dataclass(frozen=True)
class ArmMetrics:
    arm: str
    policy_version: str
    claim_label: str
    decision_count: int
    assignable_count: int
    coverage_rate: float
    promotion_count: int
    promotion_rate: float
    promotion_rate_ci: tuple[float, float]
    demotion_count: int
    demotion_rate: float
    hold_count: int
    hold_rate: float
    observed_outcome_count: int
    observed_support_needed_count: int
    observed_support_needed_rate: float
    observed_support_needed_rate_ci: tuple[float, float]
    false_promotion_count: int
    false_promotion_burden: float
    false_promotion_burden_ci: tuple[float, float]
    conditional_promoted_false_promotion_rate: float
    descriptive_false_demotion_or_unnecessary_hold_count: int
    descriptive_false_demotion_or_unnecessary_hold_rate: float
    same_bank_observed_count: int
    cross_bank_observed_count: int
    censored_by_reason: tuple[tuple[str, int], ...]

    def to_document(self) -> dict[str, object]:
        return {
            "arm": self.arm,
            "policyVersion": self.policy_version,
            "claimLabel": self.claim_label,
            "decisionCount": self.decision_count,
            "assignableCount": self.assignable_count,
            "coverageRate": self.coverage_rate,
            "promotionCount": self.promotion_count,
            "promotionRate": self.promotion_rate,
            "promotionRateCi": list(self.promotion_rate_ci),
            "demotionCount": self.demotion_count,
            "demotionRate": self.demotion_rate,
            "holdCount": self.hold_count,
            "holdRate": self.hold_rate,
            "observedOutcomeCount": self.observed_outcome_count,
            "observedSupportNeededCount": self.observed_support_needed_count,
            "observedSupportNeededRate": self.observed_support_needed_rate,
            "observedSupportNeededRateCi": list(self.observed_support_needed_rate_ci),
            "falsePromotionCount": self.false_promotion_count,
            "falsePromotionBurden": self.false_promotion_burden,
            "falsePromotionBurdenCi": list(self.false_promotion_burden_ci),
            "conditionalPromotedFalsePromotionRate": (
                self.conditional_promoted_false_promotion_rate
            ),
            "descriptiveFalseDemotionOrUnnecessaryHoldCount": (
                self.descriptive_false_demotion_or_unnecessary_hold_count
            ),
            "descriptiveFalseDemotionOrUnnecessaryHoldRate": (
                self.descriptive_false_demotion_or_unnecessary_hold_rate
            ),
            "sameBankObservedCount": self.same_bank_observed_count,
            "crossBankObservedCount": self.cross_bank_observed_count,
            "censoredByReason": dict(self.censored_by_reason),
        }


@dataclass(frozen=True)
class PolicyComparisonMetrics:
    arms: tuple[ArmMetrics, ...]
    agreement: tuple[tuple[str, str, float, int], ...]
    censoring_summary: tuple[tuple[str, int], ...]
    decision_count: int
    student_count: int
    claim_label: str

    def to_document(self) -> dict[str, object]:
        return {
            "arms": [arm.to_document() for arm in self.arms],
            "agreement": [
                {"armA": a, "armB": b, "agreementRate": rate, "comparedDecisions": count}
                for a, b, rate, count in self.agreement
            ],
            "censoringSummary": dict(self.censoring_summary),
            "decisionCount": self.decision_count,
            "studentCount": self.student_count,
            "claimLabel": self.claim_label,
        }


def compute_metrics(
    replay_result: ReplayResult,
    outcome_result: OutcomeResult,
    *,
    random_seed: int,
    claim_label: str,
    bootstrap_iterations: int = 2000,
) -> PolicyComparisonMetrics:
    """Compute deterministic descriptive metrics for every compared arm."""
    if bootstrap_iterations < 100:
        raise MetricsError("bootstrap iterations must be at least 100")
    by_arm: dict[str, list[ReplayDecision]] = {}
    for decision in replay_result.decisions:
        by_arm.setdefault(decision.arm.value, []).append(decision)
    outcomes_by_arm: dict[str, list[DecisionOutcome]] = {}
    for outcome in outcome_result.outcomes:
        outcomes_by_arm.setdefault(outcome.arm.value, []).append(outcome)

    arms: list[ArmMetrics] = []
    for arm in sorted(by_arm):
        decisions = tuple(by_arm[arm])
        outcomes = tuple(outcomes_by_arm.get(arm, ()))
        arms.append(
            _arm_metrics(
                arm,
                decisions,
                outcomes,
                random_seed=random_seed,
                claim_label=claim_label,
                bootstrap_iterations=bootstrap_iterations,
            )
        )
    if not arms:
        raise MetricsError("no policy decisions were replayed")
    agreement = _agreement_matrix(replay_result.decisions, by_arm)
    censoring = Counter(
        row.reason
        for row in outcome_result.censoring_audit
    )
    students = {decision.student_key for decision in replay_result.decisions}
    return PolicyComparisonMetrics(
        arms=tuple(arms),
        agreement=agreement,
        censoring_summary=tuple(sorted(censoring.items())),
        decision_count=len(replay_result.decisions),
        student_count=len(students),
        claim_label=claim_label,
    )


def _arm_metrics(
    arm: str,
    decisions: tuple[ReplayDecision, ...],
    outcomes: tuple[DecisionOutcome, ...],
    *,
    random_seed: int,
    claim_label: str,
    bootstrap_iterations: int,
) -> ArmMetrics:
    if not decisions:
        raise MetricsError(f"arm {arm} has no decisions")
    assignable = tuple(decision for decision in decisions if decision.is_assignable)
    promotion = tuple(decision for decision in assignable if _is_promotion(decision))
    demotion = tuple(decision for decision in assignable if _is_demotion(decision))
    hold = tuple(decision for decision in assignable if _is_hold(decision))
    observed = tuple(outcome for outcome in outcomes if outcome.outcome_status == OBSERVED)
    support_needed = tuple(outcome for outcome in observed if outcome.support_needed)
    false_promotion = tuple(
        outcome for outcome in observed if _is_promotion_outcome(outcome) and outcome.support_needed
    )
    promoted_with_outcome = tuple(
        outcome for outcome in observed if _is_promotion_outcome(outcome)
    )
    descriptive_false_hold_or_demotion = tuple(
        outcome
        for outcome in observed
        if not outcome.support_needed and outcome.direction.value in {"hold", "down"}
    )
    same_bank = tuple(outcome for outcome in observed if outcome.stratum == "same_bank")
    cross_bank = tuple(outcome for outcome in observed if outcome.stratum == "cross_bank")
    censored_counts = Counter(
        outcome.censored_reason for outcome in outcomes if outcome.outcome_status == CENSORED
    )

    promotion_bootstrap = _bootstrap(
        observed,
        key=lambda outcome: _is_promotion_outcome(outcome),
        random_seed=random_seed,
        iterations=bootstrap_iterations,
    )
    support_bootstrap = _bootstrap(
        observed,
        key=lambda outcome: bool(outcome.support_needed),
        random_seed=random_seed,
        iterations=bootstrap_iterations,
    )
    false_promotion_bootstrap = _bootstrap(
        observed,
        key=lambda outcome: _is_promotion_outcome(outcome) and bool(outcome.support_needed),
        random_seed=random_seed + 1,
        iterations=bootstrap_iterations,
    )

    return ArmMetrics(
        arm=arm,
        policy_version=decisions[0].policy_version,
        claim_label=claim_label,
        decision_count=len(decisions),
        assignable_count=len(assignable),
        coverage_rate=_rate(len(assignable), len(decisions)),
        promotion_count=len(promotion),
        promotion_rate=_rate(len(promotion), len(assignable)),
        promotion_rate_ci=promotion_bootstrap,
        demotion_count=len(demotion),
        demotion_rate=_rate(len(demotion), len(assignable)),
        hold_count=len(hold),
        hold_rate=_rate(len(hold), len(assignable)),
        observed_outcome_count=len(observed),
        observed_support_needed_count=len(support_needed),
        observed_support_needed_rate=_rate(len(support_needed), len(observed)),
        observed_support_needed_rate_ci=support_bootstrap,
        false_promotion_count=len(false_promotion),
        false_promotion_burden=_rate(len(false_promotion), len(observed)),
        false_promotion_burden_ci=false_promotion_bootstrap,
        conditional_promoted_false_promotion_rate=_rate(
            len(false_promotion), len(promoted_with_outcome)
        ),
        descriptive_false_demotion_or_unnecessary_hold_count=len(
            descriptive_false_hold_or_demotion
        ),
        descriptive_false_demotion_or_unnecessary_hold_rate=_rate(
            len(descriptive_false_hold_or_demotion), len(observed)
        ),
        same_bank_observed_count=len(same_bank),
        cross_bank_observed_count=len(cross_bank),
        censored_by_reason=tuple(sorted(censored_counts.items())),
    )


def _bootstrap(
    rows: tuple[DecisionOutcome, ...],
    *,
    key,
    random_seed: int,
    iterations: int,
) -> tuple[float, float]:
    if not rows:
        return (0.0, 0.0)
    groups: dict[str, list[DecisionOutcome]] = {}
    for row in rows:
        groups.setdefault(row.student_key, []).append(row)
    student_keys = sorted(groups)
    if len(student_keys) < 2:
        observed = _rate(sum(int(key(row)) for row in rows), len(rows))
        return (observed, observed)
    rng = Random(random_seed)
    estimates: list[float] = []
    for _ in range(iterations):
        sample_total = 0
        sample_hits = 0
        for _ in range(len(student_keys)):
            student = rng.choice(student_keys)
            for row in groups[student]:
                sample_total += 1
                sample_hits += int(key(row))
        estimates.append(_rate(sample_hits, sample_total))
    estimates.sort()
    lower_index = max(0, int(round(0.025 * len(estimates))) - 1)
    upper_index = min(len(estimates) - 1, int(round(0.975 * len(estimates))) - 1)
    return (estimates[lower_index], estimates[upper_index])


def _agreement_matrix(
    decisions: tuple[ReplayDecision, ...],
    by_arm: Mapping[str, list[ReplayDecision]],
) -> tuple[tuple[str, str, float, int], ...]:
    arms = sorted(by_arm)
    by_attempt: dict[str, dict[str, ReplayDecision]] = {}
    for decision in decisions:
        by_attempt.setdefault(decision.source_attempt_id, {})[decision.arm.value] = decision
    result: list[tuple[str, str, float, int]] = []
    for index, arm_a in enumerate(arms):
        for arm_b in arms[index + 1 :]:
            compared = 0
            agreed = 0
            for decisions_by_arm in by_attempt.values():
                left = decisions_by_arm.get(arm_a)
                right = decisions_by_arm.get(arm_b)
                if left is None or right is None:
                    continue
                compared += 1
                if (
                    left.direction == right.direction
                    and left.selected_difficulty == right.selected_difficulty
                ):
                    agreed += 1
            result.append(
                (arm_a, arm_b, _rate(agreed, compared), compared)
            )
    return tuple(result)


def _is_promotion(decision: ReplayDecision) -> bool:
    return decision.direction.value == "up"


def _is_demotion(decision: ReplayDecision) -> bool:
    return decision.direction.value == "down"


def _is_hold(decision: ReplayDecision) -> bool:
    return decision.direction.value == "hold"


def _is_promotion_outcome(outcome: DecisionOutcome) -> bool:
    return outcome.direction.value == "up"


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    value = numerator / denominator
    if not isfinite(value) or not 0.0 <= value <= 1.0:
        raise MetricsError("computed rate is outside [0, 1]")
    return round(value, 8)
