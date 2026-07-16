"""Versioned, explainable next-bank selection from trusted BKT evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


ADAPTIVE_POLICY_VERSION = "adaptive-policy-v1"


class Difficulty(str, Enum):
    EASY = "Easy"
    MODERATE = "Moderate"
    HARD = "Hard"

    def move(self, direction: int) -> "Difficulty":
        levels = tuple(Difficulty)
        index = levels.index(self)
        return levels[max(0, min(index + direction, len(levels) - 1))]


@dataclass(frozen=True)
class PolicyThresholds:
    move_up_mastery: float = 0.72
    move_down_mastery: float = 0.45
    low_support_risk: float = 0.35
    high_support_risk: float = 0.65
    minimum_evidence_for_move_up: int = 2
    minimum_evidence_for_hard: int = 6


DEFAULT_POLICY_THRESHOLDS = PolicyThresholds()


@dataclass(frozen=True)
class EligibleBank:
    bank_id: str
    difficulty: Difficulty
    exposure_count: int = 0
    is_active: bool = True


@dataclass(frozen=True)
class AssignmentContext:
    student_id: str
    subtopic_id: str
    current_difficulty: Difficulty | None
    mastery_probability: float | None
    evidence_count: int
    support_risk: float | None = None
    last_transition: str | None = None


@dataclass(frozen=True)
class AdaptiveAssignmentDecision:
    bank_id: str | None
    difficulty: Difficulty | None
    policy_version: str
    reason_code: str
    child_friendly_explanation: str
    evidence_count: int
    mastery_probability: float | None
    support_risk: float | None
    used_bkt_fallback: bool

    @property
    def is_assignable(self) -> bool:
        return self.bank_id is not None and self.difficulty is not None

    def to_firestore_document(self) -> dict[str, object]:
        if not self.is_assignable:
            raise ValueError("an unavailable assignment cannot be persisted")
        return {
            "bankId": self.bank_id,
            "difficultyLevel": self.difficulty.value,
            "policyVersion": self.policy_version,
            "reasonCode": self.reason_code,
            "reasonText": self.child_friendly_explanation,
            "evidenceCount": self.evidence_count,
            "masteryProbability": self.mastery_probability,
            "supportRisk": self.support_risk,
            "usedBktFallback": self.used_bkt_fallback,
        }


def select_next_bank(
    context: AssignmentContext,
    banks: Iterable[EligibleBank],
    *,
    thresholds: PolicyThresholds = DEFAULT_POLICY_THRESHOLDS,
    policy_version: str = ADAPTIVE_POLICY_VERSION,
) -> AdaptiveAssignmentDecision:
    """Select one active bank without allowing score-only jumps or oscillation."""
    active_banks = tuple(bank for bank in banks if bank.is_active)
    if not active_banks:
        return _unavailable(context, policy_version)

    if context.current_difficulty is None or context.mastery_probability is None:
        return _choose(
            context,
            active_banks,
            Difficulty.EASY,
            policy_version=policy_version,
            reason_code="cold_start_easy",
            explanation="Let us begin with a friendly practice set.",
            used_bkt_fallback=True,
        )

    target, reason_code, explanation = _target_difficulty(context, thresholds)
    if target != context.current_difficulty and context.last_transition == "move_down":
        target = context.current_difficulty
        reason_code = "anti_oscillation_stay"
        explanation = "Let us build confidence at this level before the next change."

    if target is Difficulty.HARD and context.evidence_count < thresholds.minimum_evidence_for_hard:
        target = Difficulty.MODERATE
        reason_code = "hard_requires_more_evidence"
        explanation = "You are progressing well. Let us practise a little more before a bigger challenge."

    return _choose(
        context,
        active_banks,
        target,
        policy_version=policy_version,
        reason_code=reason_code,
        explanation=explanation,
        used_bkt_fallback=context.support_risk is None,
    )


def _target_difficulty(
    context: AssignmentContext,
    thresholds: PolicyThresholds,
) -> tuple[Difficulty, str, str]:
    current = context.current_difficulty
    assert current is not None
    mastery = context.mastery_probability
    assert mastery is not None
    risk = context.support_risk

    if mastery <= thresholds.move_down_mastery or (
        risk is not None and risk >= thresholds.high_support_risk
    ):
        target = current.move(-1)
        if target is current:
            return (
                current,
                "stay_easy_support",
                "Let us keep building confidence with a fresh practice set.",
            )
        return (
            target,
            "move_down_support",
            "Let us practise a friendlier level while building confidence.",
        )

    can_move_up = (
        mastery >= thresholds.move_up_mastery
        and context.evidence_count >= thresholds.minimum_evidence_for_move_up
        and (risk is None or risk <= thresholds.low_support_risk)
    )
    if can_move_up:
        target = current.move(1)
        if target is current:
            return (
                current,
                "stay_hard_mastery",
                "You are doing well at this challenge level. Let us try fresh questions.",
            )
        return (
            target,
            "move_up_mastery" if risk is not None else "move_up_bkt_fallback",
            "You are ready for a gentle new challenge.",
        )

    return (
        current,
        "stay_build_evidence" if context.evidence_count < thresholds.minimum_evidence_for_move_up else "stay_target_zone",
        "Let us keep practising this level with a fresh question set.",
    )


def _choose(
    context: AssignmentContext,
    banks: tuple[EligibleBank, ...],
    difficulty: Difficulty,
    *,
    policy_version: str,
    reason_code: str,
    explanation: str,
    used_bkt_fallback: bool,
) -> AdaptiveAssignmentDecision:
    candidates = sorted(
        (bank for bank in banks if bank.difficulty is difficulty),
        key=lambda bank: (bank.exposure_count, bank.bank_id),
    )
    if not candidates:
        return _unavailable(context, policy_version)
    return AdaptiveAssignmentDecision(
        bank_id=candidates[0].bank_id,
        difficulty=difficulty,
        policy_version=policy_version,
        reason_code=reason_code,
        child_friendly_explanation=explanation,
        evidence_count=context.evidence_count,
        mastery_probability=context.mastery_probability,
        support_risk=context.support_risk,
        used_bkt_fallback=used_bkt_fallback,
    )


def _unavailable(
    context: AssignmentContext,
    policy_version: str,
) -> AdaptiveAssignmentDecision:
    return AdaptiveAssignmentDecision(
        bank_id=None,
        difficulty=None,
        policy_version=policy_version,
        reason_code="no_eligible_bank",
        child_friendly_explanation="This practice set is being prepared. Please try again soon.",
        evidence_count=context.evidence_count,
        mastery_probability=context.mastery_probability,
        support_risk=context.support_risk,
        used_bkt_fallback=context.support_risk is None,
    )
