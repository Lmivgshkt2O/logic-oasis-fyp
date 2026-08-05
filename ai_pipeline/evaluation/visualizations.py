"""Figure-ready aggregate evidence for the Stage-B policy comparison.

AQC-3 produces deterministic, pseudonymized aggregates that a later plotting
step can render as the promotion-safety forest plot, safety-benefit quadrant,
next-level success/oscillation bars, BKT reliability curve, transition matrix,
decision audit table, fairness/censoring table, and limitations panel.  This
module never exposes raw identifiers, answer text, answer keys, SHAP arrays,
model artifact hashes, or internal error traces.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import re
from math import isfinite
from random import Random
from typing import Mapping

from logic_oasis_ai.adaptive_policy import Difficulty

from .manifest import EvaluationRunManifest
from .metrics import PolicyComparisonMetrics
from .outcomes import CENSORED, OBSERVED, DecisionOutcome, OutcomeResult
from .replay import ReplayDecision, ReplayResult


MIN_CALIBRATION_OBSERVATIONS = 5
PRIMARY_ARM = "P3a"
COMPARATOR_ARMS = ("P1", "P2")
CLAIM_LEVELS = ("pipeline_demo_only", "preliminary_comparison", "descriptive_replay_only")
DIFFICULTIES = ("Easy", "Moderate", "Hard")


class VisualizationError(ValueError):
    """Raised when evidence aggregates cannot be produced safely."""


@dataclass(frozen=True)
class ClaimLevel:
    label: str
    rationale: str


def derive_claim_level(
    run_manifest: EvaluationRunManifest,
    student_count: int,
) -> ClaimLevel:
    """Derive the evidence-package claim level and its rationale.

    Pipeline demonstrations always stay at ``pipeline_demo_only``.  Approved
    real descriptive replays with fewer than four independent students are
    downgraded to ``preliminary_comparison``; larger real replays may use
    ``descriptive_replay_only``.  A claim is never promoted to superiority.
    """
    if run_manifest.claim_label != "descriptive_replay_only":
        return ClaimLevel(
            "pipeline_demo_only",
            "records are not approved real runtime data or the run manifest "
            "declared a pipeline demonstration; results show mechanics only",
        )
    if student_count < 4:
        return ClaimLevel(
            "preliminary_comparison",
            "real descriptive replay with fewer than four independent students "
            "is preliminary and cannot support a stable comparison",
        )
    return ClaimLevel(
        "descriptive_replay_only",
        "approved real descriptive replay with at least four independent "
        "students; observational evidence that never claims one policy is "
        "better than another",
    )


def build_evidence_package(
    replay_result: ReplayResult,
    outcome_result: OutcomeResult,
    metrics: PolicyComparisonMetrics,
    run_manifest: EvaluationRunManifest,
    *,
    random_seed: int,
    bootstrap_iterations: int = 2000,
) -> dict[str, object]:
    """Build every figure-ready aggregate for the evidence package."""
    if bootstrap_iterations < 100:
        raise VisualizationError("bootstrap iterations must be at least 100")
    claim = derive_claim_level(run_manifest, metrics.student_count)
    decisions_by_arm = {
        arm: tuple(decision for decision in replay_result.decisions if decision.arm.value == arm)
        for arm in sorted({decision.arm.value for decision in replay_result.decisions})
    }
    outcomes_by_arm = {
        arm: tuple(outcome for outcome in outcome_result.outcomes if outcome.arm.value == arm)
        for arm in sorted({outcome.arm.value for outcome in outcome_result.outcomes})
    }

    forest = _forest_plot_data(
        outcomes_by_arm,
        random_seed=random_seed,
        bootstrap_iterations=bootstrap_iterations,
    )
    quadrant = [
        {
            "arm": arm,
            "falsePromotionBurden": _arm_metric(metrics, arm, "falsePromotionBurden"),
            "descriptiveFalseDemotionOrUnnecessaryHoldRate": _arm_metric(
                metrics, arm, "descriptiveFalseDemotionOrUnnecessaryHoldRate"
            ),
        }
        for arm in sorted(decisions_by_arm)
    ]
    success_oscillation = [
        {
            "arm": arm,
            "nextLevelSuccessCount": _next_level_success_count(outcomes_by_arm[arm]),
            "nextLevelSuccessRate": _next_level_success_rate(outcomes_by_arm[arm]),
            "oscillationCount": _oscillation_count(decisions_by_arm[arm]),
            "oscillationRate": _oscillation_rate(decisions_by_arm[arm]),
        }
        for arm in sorted(decisions_by_arm)
    ]
    reliability = _reliability_curve(replay_result, outcome_result)
    transitions = {
        arm: _transition_matrix(decisions_by_arm[arm])
        for arm in sorted(decisions_by_arm)
    }
    audit_rows = _decision_audit_rows(replay_result, outcome_result)
    fairness = _fairness_and_censoring(metrics, outcomes_by_arm)
    totals = _totals(replay_result, outcome_result, metrics)
    limitations = _limitations(run_manifest, claim)

    package = {
        "reportKind": "policy_comparison_evidence_v1",
        "claimLevel": claim.label,
        "claimRationale": claim.rationale,
        "manifestSha256": run_manifest.manifest_sha256(),
        "datasetSha256": run_manifest.dataset_sha256,
        "totals": totals,
        "forestPlot": forest,
        "safetyBenefitQuadrant": quadrant,
        "nextLevelSuccessAndOscillation": success_oscillation,
        "bktReliabilityCurve": reliability,
        "transitionMatrices": transitions,
        "decisionAuditTable": audit_rows,
        "fairnessAndCensoring": fairness,
        "limitations": limitations,
    }
    _assert_evidence_safety(package)
    return package


def _forest_plot_data(
    outcomes_by_arm: Mapping[str, tuple[DecisionOutcome, ...]],
    *,
    random_seed: int,
    bootstrap_iterations: int,
) -> list[dict[str, object]]:
    if PRIMARY_ARM not in outcomes_by_arm:
        return []
    result: list[dict[str, object]] = []
    for comparator in COMPARATOR_ARMS:
        if comparator not in outcomes_by_arm:
            continue
        primary = outcomes_by_arm[PRIMARY_ARM]
        other = outcomes_by_arm[comparator]
        primary_burden = _burden(primary)
        other_burden = _burden(other)
        primary_observed = tuple(
            outcome for outcome in primary if outcome.outcome_status == OBSERVED
        )
        difference, ci = _burden_difference_bootstrap(
            primary,
            other,
            random_seed=random_seed + (1 if comparator == "P2" else 0),
            iterations=bootstrap_iterations,
        )
        primary_delta_fd = _descriptive_fd_delta(primary, other)
        result.append(
            {
                "arm": PRIMARY_ARM,
                "comparator": comparator,
                "riskDifference": difference,
                "riskDifferenceCi": list(ci),
                "falsePromotionBurdenPrimary": primary_burden,
                "falsePromotionBurdenComparator": other_burden,
                "falseDemotionDelta": primary_delta_fd,
                "sampleDenominator": len(primary_observed),
            }
        )
    return result


def _burden(outcomes: tuple[DecisionOutcome, ...]) -> float:
    observed = tuple(outcome for outcome in outcomes if outcome.outcome_status == OBSERVED)
    false_promotions = sum(
        1
        for outcome in observed
        if outcome.direction.value == "up" and outcome.support_needed
    )
    return _rate(false_promotions, len(observed))


def _burden_difference_bootstrap(
    primary: tuple[DecisionOutcome, ...],
    comparator: tuple[DecisionOutcome, ...],
    *,
    random_seed: int,
    iterations: int,
) -> tuple[float, tuple[float, float]]:
    primary_by_student = _student_burden(primary)
    comparator_by_student = _student_burden(comparator)
    students = sorted(set(primary_by_student) | set(comparator_by_student))
    if len(students) < 2:
        observed_difference = _burden(primary) - _burden(comparator)
        return round(observed_difference, 8), (observed_difference, observed_difference)
    rng = Random(random_seed)
    differences: list[float] = []
    for _ in range(iterations):
        primary_fp = 0
        primary_observed = 0
        comparator_fp = 0
        comparator_observed = 0
        for _ in range(len(students)):
            student = rng.choice(students)
            for fp, observed in primary_by_student.get(student, ()):
                primary_fp += fp
                primary_observed += observed
            for fp, observed in comparator_by_student.get(student, ()):
                comparator_fp += fp
                comparator_observed += observed
        differences.append(
            _rate(primary_fp, primary_observed) - _rate(comparator_fp, comparator_observed)
        )
    differences.sort()
    lower = differences[max(0, int(round(0.025 * len(differences))) - 1)]
    upper = differences[min(len(differences) - 1, int(round(0.975 * len(differences))) - 1)]
    return round(_burden(primary) - _burden(comparator), 8), (round(lower, 8), round(upper, 8))


def _student_burden(
    outcomes: tuple[DecisionOutcome, ...],
) -> dict[str, tuple[tuple[int, int], ...]]:
    grouped: dict[str, list[DecisionOutcome]] = {}
    for outcome in outcomes:
        if outcome.outcome_status != OBSERVED:
            continue
        grouped.setdefault(outcome.student_key, []).append(outcome)
    return {
        student: (
            (
                sum(
                    1
                    for outcome in rows
                    if outcome.direction.value == "up" and outcome.support_needed
                ),
                len(rows),
            ),
        )
        for student, rows in sorted(grouped.items())
    }


def _descriptive_fd_delta(
    primary: tuple[DecisionOutcome, ...],
    comparator: tuple[DecisionOutcome, ...],
) -> float:
    return round(
        _descriptive_fd_rate(primary) - _descriptive_fd_rate(comparator),
        8,
    )


def _descriptive_fd_rate(outcomes: tuple[DecisionOutcome, ...]) -> float:
    observed = tuple(outcome for outcome in outcomes if outcome.outcome_status == OBSERVED)
    false_hold_or_demotion = sum(
        1
        for outcome in observed
        if not outcome.support_needed and outcome.direction.value in {"hold", "down"}
    )
    return _rate(false_hold_or_demotion, len(observed))


def _next_level_success_count(outcomes: tuple[DecisionOutcome, ...]) -> int:
    observed = tuple(outcome for outcome in outcomes if outcome.outcome_status == OBSERVED)
    return sum(1 for outcome in observed if not outcome.support_needed)


def _next_level_success_rate(outcomes: tuple[DecisionOutcome, ...]) -> float:
    observed = tuple(outcome for outcome in outcomes if outcome.outcome_status == OBSERVED)
    return _rate(_next_level_success_count(outcomes), len(observed))


def _oscillation_count(decisions: tuple[ReplayDecision, ...]) -> int:
    sequences: dict[tuple[str, str], list[ReplayDecision]] = defaultdict(list)
    for decision in decisions:
        sequences[(decision.student_key, decision.subtopic_id)].append(decision)
    count = 0
    for sequence in sequences.values():
        ordered = sorted(
            sequence,
            key=lambda item: (
                item.source_attempt_sequence,
                item.decision_id,
            ),
        )
        previous: str | None = None
        for decision in ordered:
            direction = decision.direction.value
            if direction == "hold":
                continue
            if previous is not None and previous != direction:
                count += 1
            previous = direction
    return count


def _oscillation_rate(decisions: tuple[ReplayDecision, ...]) -> float:
    sequences: dict[tuple[str, str], list[ReplayDecision]] = defaultdict(list)
    for decision in decisions:
        sequences[(decision.student_key, decision.subtopic_id)].append(decision)
    pairs = 0
    for sequence in sequences.values():
        ordered = sorted(
            sequence,
            key=lambda item: (
                item.source_attempt_sequence,
                item.decision_id,
            ),
        )
        pairs += max(0, len(ordered) - 1)
    return _rate(_oscillation_count(decisions), pairs)


def _reliability_curve(
    replay_result: ReplayResult,
    outcome_result: OutcomeResult,
) -> list[dict[str, object]]:
    mastery_by_decision = {
        decision.decision_id: decision.mastery_probability
        for decision in replay_result.decisions
        if decision.arm.value == PRIMARY_ARM
    }
    observed_by_decision = {
        outcome.decision_id: outcome
        for outcome in outcome_result.outcomes
        if outcome.arm.value == PRIMARY_ARM and outcome.outcome_status == OBSERVED
    }
    band_counts: dict[tuple[float, float], list[bool]] = defaultdict(list)
    for decision_id, mastery in mastery_by_decision.items():
        outcome = observed_by_decision.get(decision_id)
        if outcome is None:
            continue
        band = _mastery_band(mastery)
        band_counts[band].append(not outcome.support_needed)
    bands = (
        (0.0, 0.2),
        (0.2, 0.4),
        (0.4, 0.6),
        (0.6, 0.8),
        (0.8, 1.0),
    )
    rows: list[dict[str, object]] = []
    for lower, upper in bands:
        values = band_counts.get((lower, upper), [])
        count = len(values)
        success_rate = _rate(sum(1 for value in values if value), count)
        rows.append(
            {
                "lower": lower,
                "upper": upper,
                "predictedMasteryMid": round((lower + upper) / 2, 8),
                "observedSuccessRate": success_rate,
                "observationCount": count,
                "status": "reliable" if count >= MIN_CALIBRATION_OBSERVATIONS else "insufficient",
            }
        )
    return rows


def _mastery_band(value: float) -> tuple[float, float]:
    for lower, upper in ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)):
        if value < upper:
            return (lower, upper)
    return (0.8, 1.0)


def _transition_matrix(
    decisions: tuple[ReplayDecision, ...],
) -> dict[str, object]:
    matrix = {
        current: {target: 0 for target in DIFFICULTIES}
        for current in DIFFICULTIES
    }
    unassigned = 0
    for decision in decisions:
        if not decision.is_assignable:
            unassigned += 1
            continue
        current = decision.current_difficulty.value
        selected = decision.selected_difficulty.value
        matrix[current][selected] += 1
    return {
        "matrix": matrix,
        "unassignedCount": unassigned,
    }


def _decision_audit_rows(
    replay_result: ReplayResult,
    outcome_result: OutcomeResult,
) -> list[dict[str, object]]:
    outcome_by_decision = {
        outcome.decision_id: outcome for outcome in outcome_result.outcomes
    }
    rows: list[dict[str, object]] = []
    for decision in sorted(
        replay_result.decisions,
        key=lambda item: (
            item.student_key,
            item.subtopic_id,
            item.source_attempt_sequence,
            item.arm.value,
        ),
    ):
        outcome = outcome_by_decision.get(decision.decision_id)
        rows.append(
            {
                "decisionId": decision.decision_id,
                "studentKey": decision.student_key,
                "subtopicId": decision.subtopic_id,
                "arm": decision.arm.value,
                "policyVersion": decision.policy_version,
                "evidenceMode": decision.evidence_mode,
                "reasonCode": decision.reason_code,
                "direction": decision.direction.value,
                "selectedDifficulty": (
                    decision.selected_difficulty.value if decision.selected_difficulty else None
                ),
                "currentDifficulty": decision.current_difficulty.value,
                "usedBktFallback": decision.used_bkt_fallback,
                "outcomeStatus": outcome.outcome_status if outcome else None,
                "censoredReason": outcome.censored_reason if outcome else None,
                "supportNeeded": outcome.support_needed if outcome else None,
                "stratum": outcome.stratum if outcome else None,
            }
        )
    return rows


def _fairness_and_censoring(
    metrics: PolicyComparisonMetrics,
    outcomes_by_arm: Mapping[str, tuple[DecisionOutcome, ...]],
) -> dict[str, object]:
    by_arm: dict[str, dict[str, object]] = {}
    for arm in sorted(outcomes_by_arm):
        observed = tuple(
            outcome for outcome in outcomes_by_arm[arm] if outcome.outcome_status == OBSERVED
        )
        by_arm[arm] = {
            "observedCount": len(observed),
            "sameBankObservedCount": sum(1 for outcome in observed if outcome.stratum == "same_bank"),
            "crossBankObservedCount": sum(1 for outcome in observed if outcome.stratum == "cross_bank"),
            "censoredByReason": dict(
                Counter(
                    outcome.censored_reason
                    for outcome in outcomes_by_arm[arm]
                    if outcome.outcome_status == CENSORED
                )
            ),
        }
    return {
        "byArm": by_arm,
        "overallCensoringSummary": dict(metrics.censoring_summary),
    }


def _totals(
    replay_result: ReplayResult,
    outcome_result: OutcomeResult,
    metrics: PolicyComparisonMetrics,
) -> dict[str, int]:
    censored = sum(
        1 for outcome in outcome_result.outcomes if outcome.outcome_status == CENSORED
    )
    observed = sum(
        1 for outcome in outcome_result.outcomes if outcome.outcome_status == OBSERVED
    )
    if metrics.decision_count != len(replay_result.decisions):
        raise VisualizationError("decision totals do not reconcile with the replay")
    if censored + observed != len(outcome_result.outcomes):
        raise VisualizationError("outcome totals do not reconcile")
    return {
        "decisionCount": metrics.decision_count,
        "observedCount": observed,
        "censoredCount": censored,
    }


def _arm_metric(
    metrics: PolicyComparisonMetrics,
    arm: str,
    field: str,
) -> float:
    attribute = {
        "falsePromotionBurden": "false_promotion_burden",
        "descriptiveFalseDemotionOrUnnecessaryHoldRate": (
            "descriptive_false_demotion_or_unnecessary_hold_rate"
        ),
    }.get(field, field)
    for item in metrics.arms:
        if item.arm == arm:
            return float(getattr(item, attribute))
    raise VisualizationError(f"missing metrics for arm {arm}")


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    value = numerator / denominator
    if not isfinite(value) or not 0.0 <= value <= 1.0:
        raise VisualizationError("computed rate is outside [0, 1]")
    return round(value, 8)


def _limitations(
    run_manifest: EvaluationRunManifest,
    claim: ClaimLevel,
) -> list[str]:
    limitations = [
        "Offline observational replay; no causal learning-effect claim is made.",
        "Observed-assignment-matched outcomes exclude counterfactual difficulty mismatches.",
        "The false-demotion guard (deltaFD) is a Stage-C pre-registered gate, not a Stage-B finding.",
        "P3b (model-assisted) results are reported separately from P3a (BKT-only).",
        f"Claim level: {claim.label}. {claim.rationale}",
    ]
    if run_manifest.provenance != "real":
        limitations.append(
            "Records are not approved real runtime data; this is a pipeline demonstration only."
        )
    return limitations


def _assert_evidence_safety(package: Mapping[str, object]) -> None:
    import json

    serialized = json.dumps(package, sort_keys=True, ensure_ascii=True).lower()
    forbidden = (
        "studentid",
        "answertext",
        "answerkey",
        "shap",
        "artifactsha256",
        "@example",
        "traceback",
    )
    for token in forbidden:
        if token in serialized:
            raise VisualizationError(f"evidence package must not contain protected content: {token}")
    pseudonym_pattern = re.compile(r"^(student_[0-9a-f]{64}|[0-9a-f]{64})$")
    for row in package["decisionAuditTable"]:
        student_key = str(row["studentKey"])
        if not pseudonym_pattern.match(student_key):
            raise VisualizationError(
                "evidence packages require pseudonymized student keys only"
            )
