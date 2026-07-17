"""Versioned, YAML-governed next-bank selection from trusted BKT evidence.

The policy is deliberately separate from model inference.  A promoted model
may contribute ``support_risk``; it never chooses a bank directly.  Runtime
callers must load a validated immutable policy file.  The small Python default
below exists solely for deterministic test fixtures and is not a runtime
fallback when the configuration is missing or invalid.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping

import yaml


ADAPTIVE_POLICY_VERSION = "adaptive-policy-v1"


class PolicyConfigurationError(ValueError):
    """Raised when a runtime policy cannot be safely loaded."""


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
    """Fixture-only defaults.  Production uses :class:`AdaptivePolicyConfig`."""

    move_up_mastery: float = 0.72
    move_down_mastery: float = 0.45
    low_support_risk: float = 0.35
    high_support_risk: float = 0.65
    minimum_evidence_for_move_up: int = 2
    minimum_evidence_for_hard: int = 6


DEFAULT_POLICY_THRESHOLDS = PolicyThresholds()


@dataclass(frozen=True)
class AdaptivePolicyConfig:
    """The complete immutable policy needed by a runtime assignment decision."""

    policy_version: str
    thresholds: PolicyThresholds
    cold_start_difficulty: Difficulty
    one_level_movement: bool
    prevent_immediate_reversal: bool
    prefer_unseen_banks: bool
    reason_texts: Mapping[str, str]
    source_path: str
    source_sha256: str

    def reason_text(self, code: str) -> str:
        try:
            return self.reason_texts[code]
        except KeyError as error:
            raise PolicyConfigurationError(
                f"policy {self.policy_version} has no reason text for {code}"
            ) from error


def load_adaptive_policy_config(path: str | Path) -> AdaptivePolicyConfig:
    """Load and validate the only production source of policy thresholds.

    Any failure raises ``PolicyConfigurationError``.  In particular, callers
    must not replace a missing or malformed file with Python defaults.
    """
    source = Path(path)
    try:
        raw_bytes = source.read_bytes()
        data = yaml.safe_load(raw_bytes)
    except (OSError, yaml.YAMLError) as error:
        raise PolicyConfigurationError(
            f"adaptive policy configuration is unavailable: {source}"
        ) from error
    if not isinstance(data, dict):
        raise PolicyConfigurationError("adaptive policy configuration must be a mapping")

    policy_version = _required_string(data, "policyVersion")
    thresholds_data = _required_mapping(data, "thresholds")
    mastery = _required_mapping(thresholds_data, "mastery")
    support_risk = _required_mapping(thresholds_data, "supportRisk")
    minimum_evidence = _required_mapping(data, "minimumEvidence")
    guardrails = _required_mapping(data, "guardrails")
    bank_selection = _required_mapping(data, "bankSelection")
    cold_start = _required_mapping(data, "coldStart")
    reason_texts = _required_mapping(data, "reasonTexts")

    thresholds = PolicyThresholds(
        move_up_mastery=_required_probability(mastery, "moveUpAtLeast"),
        move_down_mastery=_required_probability(mastery, "moveDownAtMost"),
        low_support_risk=_required_probability(support_risk, "moveUpAtMost"),
        high_support_risk=_required_probability(support_risk, "moveDownAtLeast"),
        minimum_evidence_for_move_up=_required_positive_int(minimum_evidence, "moveUp"),
        minimum_evidence_for_hard=_required_positive_int(minimum_evidence, "hard"),
    )
    if thresholds.move_down_mastery >= thresholds.move_up_mastery:
        raise PolicyConfigurationError("move-down mastery must be below move-up mastery")
    if thresholds.low_support_risk >= thresholds.high_support_risk:
        raise PolicyConfigurationError("move-up risk must be below move-down risk")
    if thresholds.minimum_evidence_for_hard < thresholds.minimum_evidence_for_move_up:
        raise PolicyConfigurationError("Hard evidence cannot be below move-up evidence")

    one_level_movement = _required_bool(guardrails, "oneLevelMovement")
    if not one_level_movement:
        raise PolicyConfigurationError("the FYP1 policy must enforce one-level movement")
    normalized_reason_texts = {
        code: _required_string(reason_texts, code)
        for code in _REQUIRED_REASON_CODES
    }
    return AdaptivePolicyConfig(
        policy_version=policy_version,
        thresholds=thresholds,
        cold_start_difficulty=_parse_difficulty(_required_string(cold_start, "difficulty")),
        one_level_movement=one_level_movement,
        prevent_immediate_reversal=_required_bool(guardrails, "preventImmediateReversal"),
        prefer_unseen_banks=_required_bool(bank_selection, "preferUnseenBanks"),
        reason_texts=MappingProxyType(normalized_reason_texts),
        source_path=str(source),
        source_sha256=sha256(raw_bytes).hexdigest(),
    )


@dataclass(frozen=True)
class EligibleBank:
    bank_id: str
    difficulty: Difficulty
    exposure_count: int = 0
    is_active: bool = True

    def __post_init__(self) -> None:
        if not self.bank_id:
            raise ValueError("bank_id is required")
        if self.exposure_count < 0:
            raise ValueError("exposure_count cannot be negative")


@dataclass(frozen=True)
class AssignmentContext:
    student_id: str
    subtopic_id: str
    current_difficulty: Difficulty | None
    mastery_probability: float | None
    evidence_count: int
    support_risk: float | None = None
    last_transition: str | None = None

    def __post_init__(self) -> None:
        if not self.student_id or not self.subtopic_id:
            raise ValueError("student_id and subtopic_id are required")
        if self.evidence_count < 0:
            raise ValueError("evidence_count cannot be negative")
        for name, value in (
            ("mastery_probability", self.mastery_probability),
            ("support_risk", self.support_risk),
        ):
            if value is not None and (not isinstance(value, (float, int)) or isinstance(value, bool) or not 0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be between zero and one")


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
    outcome_status: str

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
            "status": self.outcome_status,
        }


def deterministic_assignment_id(source_attempt_id: str) -> str:
    """Return the stable U8 persistence key for an attempt's next assignment."""
    if not source_attempt_id:
        raise ValueError("source_attempt_id is required")
    return f"adaptive-assignment-{source_attempt_id}"


def select_next_bank(
    context: AssignmentContext,
    banks: Iterable[EligibleBank],
    *,
    policy: AdaptivePolicyConfig,
) -> AdaptiveAssignmentDecision:
    """Apply a loaded immutable policy to trusted BKT/model evidence.

    The required keyword-only policy prevents a runtime caller from silently
    returning to hardcoded thresholds.  ``select_next_bank_fixture`` is the
    only supported default-threshold helper for fixtures.
    """
    active_banks = tuple(bank for bank in banks if bank.is_active)
    if not active_banks:
        return _unavailable(context, policy)

    if context.current_difficulty is None or context.mastery_probability is None:
        return _choose(
            context,
            active_banks,
            policy.cold_start_difficulty,
            policy=policy,
            reason_code="cold_start_easy",
            used_bkt_fallback=True,
        )

    target, reason_code = _target_difficulty(context, policy.thresholds)
    if policy.prevent_immediate_reversal and _is_immediate_reversal(
        target, context.current_difficulty, context.last_transition
    ):
        target = context.current_difficulty
        reason_code = "anti_oscillation_stay"

    if target is Difficulty.HARD and context.evidence_count < policy.thresholds.minimum_evidence_for_hard:
        target = context.current_difficulty
        reason_code = "hard_requires_more_evidence"

    return _choose(
        context,
        active_banks,
        target,
        policy=policy,
        reason_code=reason_code,
        used_bkt_fallback=context.support_risk is None,
    )


def select_next_bank_fixture(
    context: AssignmentContext,
    banks: Iterable[EligibleBank],
    *,
    thresholds: PolicyThresholds = DEFAULT_POLICY_THRESHOLDS,
    policy_version: str = ADAPTIVE_POLICY_VERSION,
) -> AdaptiveAssignmentDecision:
    """Fixture-only adapter retained for isolated Python mechanics tests."""
    return select_next_bank(
        context,
        banks,
        policy=AdaptivePolicyConfig(
            policy_version=policy_version,
            thresholds=thresholds,
            cold_start_difficulty=Difficulty.EASY,
            one_level_movement=True,
            prevent_immediate_reversal=True,
            prefer_unseen_banks=True,
            reason_texts=MappingProxyType(_FIXTURE_REASON_TEXTS),
            source_path="fixture-only",
            source_sha256="fixture-only",
        ),
    )


def _target_difficulty(
    context: AssignmentContext,
    thresholds: PolicyThresholds,
) -> tuple[Difficulty, str]:
    current = context.current_difficulty
    mastery = context.mastery_probability
    assert current is not None and mastery is not None
    risk = context.support_risk

    if mastery <= thresholds.move_down_mastery or (
        risk is not None and risk >= thresholds.high_support_risk
    ):
        target = current.move(-1)
        return (target, "stay_easy_support" if target is current else "move_down_support")

    if (
        mastery >= thresholds.move_up_mastery
        and context.evidence_count >= thresholds.minimum_evidence_for_move_up
        and (risk is None or risk <= thresholds.low_support_risk)
    ):
        target = current.move(1)
        if target is current:
            return current, "stay_hard_mastery"
        return target, "move_up_bkt_fallback" if risk is None else "move_up_mastery"

    return (
        current,
        "stay_build_evidence"
        if context.evidence_count < thresholds.minimum_evidence_for_move_up
        else "stay_target_zone",
    )


def _is_immediate_reversal(
    target: Difficulty,
    current: Difficulty,
    last_transition: str | None,
) -> bool:
    if last_transition is None or target is current:
        return False
    lowered = last_transition.lower()
    return (target.value != current.value) and (
        (target is current.move(1) and lowered.startswith("move_down"))
        or (target is current.move(-1) and lowered.startswith("move_up"))
    )


def _choose(
    context: AssignmentContext,
    banks: tuple[EligibleBank, ...],
    difficulty: Difficulty,
    *,
    policy: AdaptivePolicyConfig,
    reason_code: str,
    used_bkt_fallback: bool,
) -> AdaptiveAssignmentDecision:
    candidates = [bank for bank in banks if bank.difficulty is difficulty]
    if not candidates:
        return _unavailable(context, policy)
    if policy.prefer_unseen_banks:
        candidates.sort(key=lambda bank: (bank.exposure_count != 0, bank.exposure_count, bank.bank_id))
    else:
        candidates.sort(key=lambda bank: (bank.exposure_count, bank.bank_id))
    return AdaptiveAssignmentDecision(
        bank_id=candidates[0].bank_id,
        difficulty=difficulty,
        policy_version=policy.policy_version,
        reason_code=reason_code,
        child_friendly_explanation=policy.reason_text(reason_code),
        evidence_count=context.evidence_count,
        mastery_probability=context.mastery_probability,
        support_risk=context.support_risk,
        used_bkt_fallback=used_bkt_fallback,
        outcome_status="assigned",
    )


def _unavailable(
    context: AssignmentContext,
    policy: AdaptivePolicyConfig,
) -> AdaptiveAssignmentDecision:
    return AdaptiveAssignmentDecision(
        bank_id=None,
        difficulty=None,
        policy_version=policy.policy_version,
        reason_code="no_eligible_bank",
        child_friendly_explanation=policy.reason_text("no_eligible_bank"),
        evidence_count=context.evidence_count,
        mastery_probability=context.mastery_probability,
        support_risk=context.support_risk,
        used_bkt_fallback=context.support_risk is None,
        outcome_status="fallback",
    )


_REQUIRED_REASON_CODES = (
    "cold_start_easy",
    "move_up_mastery",
    "move_up_bkt_fallback",
    "move_down_support",
    "stay_easy_support",
    "stay_hard_mastery",
    "stay_build_evidence",
    "stay_target_zone",
    "anti_oscillation_stay",
    "hard_requires_more_evidence",
    "no_eligible_bank",
)

_FIXTURE_REASON_TEXTS = {
    "cold_start_easy": "Let us begin with a friendly practice set.",
    "move_up_mastery": "You are ready for a gentle new challenge.",
    "move_up_bkt_fallback": "You are ready for a gentle new challenge.",
    "move_down_support": "Let us practise a friendlier level while building confidence.",
    "stay_easy_support": "Let us keep building confidence with a fresh practice set.",
    "stay_hard_mastery": "You are doing well at this challenge level. Let us try fresh questions.",
    "stay_build_evidence": "Let us keep practising this level with a fresh question set.",
    "stay_target_zone": "Let us keep practising this level with a fresh question set.",
    "anti_oscillation_stay": "Let us build confidence at this level before the next change.",
    "hard_requires_more_evidence": "You are progressing well. Let us practise a little more before a bigger challenge.",
    "no_eligible_bank": "This practice set is being prepared. Please try again soon.",
}


def _required_mapping(data: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise PolicyConfigurationError(f"adaptive policy requires mapping: {key}")
    return value


def _required_string(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise PolicyConfigurationError(f"adaptive policy requires string: {key}")
    return value


def _required_bool(data: Mapping[str, object], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise PolicyConfigurationError(f"adaptive policy requires boolean: {key}")
    return value


def _required_probability(data: Mapping[str, object], key: str) -> float:
    value = data.get(key)
    if not isinstance(value, (float, int)) or isinstance(value, bool) or not 0.0 <= value <= 1.0:
        raise PolicyConfigurationError(f"adaptive policy requires probability: {key}")
    return float(value)


def _required_positive_int(data: Mapping[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise PolicyConfigurationError(f"adaptive policy requires positive integer: {key}")
    return value


def _parse_difficulty(value: str) -> Difficulty:
    try:
        return Difficulty(value)
    except ValueError as error:
        raise PolicyConfigurationError(f"adaptive policy has unknown difficulty: {value}") from error
