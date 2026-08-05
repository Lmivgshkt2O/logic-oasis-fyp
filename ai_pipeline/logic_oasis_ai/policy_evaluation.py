"""Immutable AQC-1 policy-comparison contract and pure selectors.

This module compares assignment decisions; it does not evaluate educational
outcomes.  Runtime callers must load the complete YAML manifest and the
hash-bound adaptive policy.  Missing or altered configuration fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from typing import Iterable, Mapping

import yaml

from .adaptive_policy import (
    AdaptivePolicyConfig,
    AssignmentContext,
    Difficulty,
    EligibleBank,
    select_next_bank,
)
from .prediction_contract import PREDICTION_TARGET


POLICY_EVALUATION_MANIFEST_VERSION = "policy-evaluation-v1"
POLICY_EVALUATION_STUDY_VERSION = "policy-evaluation-study-v1"
POLICY_OUTCOME_PROTOCOL_VERSION = "policy-outcomes-v1"
P1_PROMOTION_THRESHOLD = 0.80
P2_DEMOTION_THRESHOLD = 0.40


class PolicyEvaluationConfigurationError(ValueError):
    """Raised when the evaluation contract is incomplete or incompatible."""


class PolicyArm(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3A = "P3a"
    P3B = "P3b"


class StudyStatus(str, Enum):
    DRAFT = "draft"
    ENROLLING = "enrolling"
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class SelectionEvidenceMode(str, Enum):
    SCORE_ONLY = "score_only"
    BKT_SCORE_AGREEMENT = "bkt_score_agreement"
    BKT_ONLY_STUDY = "bkt_only_study"
    MODEL_ASSISTED = "model_assisted"


class DecisionDirection(str, Enum):
    DOWN = "down"
    HOLD = "hold"
    UP = "up"


@dataclass(frozen=True)
class PolicyArmConfig:
    arm: PolicyArm
    policy_version: str
    evidence_mode: SelectionEvidenceMode
    claim_label: str


@dataclass(frozen=True)
class StudyConfiguration:
    study_version: str
    status: StudyStatus
    allowed_statuses: tuple[StudyStatus, ...]
    live_approval_required: bool
    default_claim_label: str

    @property
    def may_enrol(self) -> bool:
        return self.status in {StudyStatus.ENROLLING, StudyStatus.ACTIVE}


@dataclass(frozen=True)
class CommonSafetyEnvelope:
    difficulty_order: tuple[Difficulty, ...]
    active_compatible_banks_only: bool
    maximum_movement_levels: int
    prevent_immediate_reversal: bool
    prefer_unseen_banks: bool
    unavailable_bank_behavior: str


@dataclass(frozen=True)
class PolicyEvaluationManifest:
    manifest_version: str
    study: StudyConfiguration
    policy_arms: tuple[PolicyArmConfig, ...]
    promotion_threshold: float
    demotion_threshold: float
    adaptive_policy_version: str
    adaptive_policy_sha256: str
    safety: CommonSafetyEnvelope
    outcome_protocol_version: str
    frozen_prediction_target: str
    primary_metric: str
    safety_metric: str
    challenge_opportunity_metric: str
    reason_codes: frozenset[str]
    source_path: str
    source_sha256: str

    def arm(self, arm: PolicyArm) -> PolicyArmConfig:
        for item in self.policy_arms:
            if item.arm is arm:
                return item
        raise PolicyEvaluationConfigurationError(f"manifest has no policy arm {arm.value}")


@dataclass(frozen=True)
class EvaluationEligibility:
    eligible: bool
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if self.eligible == (self.reason_code is not None):
            raise ValueError("eligible rows have no reason; ineligible rows require one")


@dataclass(frozen=True)
class PolicyDecisionContext:
    source_attempt_id: str
    student_id: str
    subtopic_id: str
    current_difficulty: Difficulty
    correct_count: int
    total_questions: int
    mastery_probability: float
    evidence_count: int
    support_risk: float | None = None
    compatible_model_available: bool = False
    last_transition: str | None = None

    def __post_init__(self) -> None:
        if not self.source_attempt_id or not self.student_id or not self.subtopic_id:
            raise ValueError("source attempt, student, and subtopic are required")
        if self.total_questions < 1 or not 0 <= self.correct_count <= self.total_questions:
            raise ValueError("score counts are invalid")
        if self.evidence_count < 0:
            raise ValueError("evidence_count cannot be negative")
        _validate_probability(self.mastery_probability, "mastery_probability")
        if self.support_risk is not None:
            _validate_probability(self.support_risk, "support_risk")
        if self.compatible_model_available != (self.support_risk is not None):
            raise ValueError("compatible model availability must match support-risk evidence")

    @property
    def score_rate(self) -> float:
        return self.correct_count / self.total_questions


@dataclass(frozen=True)
class CandidatePolicyDecision:
    decision_id: str
    source_attempt_id: str
    arm: PolicyArm
    policy_version: str
    claim_label: str
    evidence_mode: SelectionEvidenceMode
    direction: DecisionDirection
    selected_bank_id: str | None
    selected_difficulty: Difficulty | None
    reason_code: str
    used_bkt_fallback: bool
    outcome_status: str

    @property
    def is_assignable(self) -> bool:
        return self.selected_bank_id is not None and self.selected_difficulty is not None


@dataclass(frozen=True)
class DecisionAuditPayload:
    decision_id: str
    source_attempt_id: str
    arm: PolicyArm
    policy_version: str
    manifest_version: str
    manifest_sha256: str
    adaptive_policy_version: str
    adaptive_policy_sha256: str
    evidence_mode: SelectionEvidenceMode
    reason_code: str
    selected_bank_id: str | None
    selected_difficulty: Difficulty | None
    used_bkt_fallback: bool

    @classmethod
    def from_decision(
        cls, decision: CandidatePolicyDecision, manifest: PolicyEvaluationManifest
    ) -> "DecisionAuditPayload":
        return cls(
            decision_id=decision.decision_id,
            source_attempt_id=decision.source_attempt_id,
            arm=decision.arm,
            policy_version=decision.policy_version,
            manifest_version=manifest.manifest_version,
            manifest_sha256=manifest.source_sha256,
            adaptive_policy_version=manifest.adaptive_policy_version,
            adaptive_policy_sha256=manifest.adaptive_policy_sha256,
            evidence_mode=decision.evidence_mode,
            reason_code=decision.reason_code,
            selected_bank_id=decision.selected_bank_id,
            selected_difficulty=decision.selected_difficulty,
            used_bkt_fallback=decision.used_bkt_fallback,
        )

    def to_document(self) -> dict[str, object]:
        return {
            "decisionId": self.decision_id,
            "sourceAttemptId": self.source_attempt_id,
            "assignedArm": self.arm.value,
            "policyVersion": self.policy_version,
            "manifestVersion": self.manifest_version,
            "manifestSha256": self.manifest_sha256,
            "adaptivePolicyVersion": self.adaptive_policy_version,
            "adaptivePolicySha256": self.adaptive_policy_sha256,
            "selectionEvidenceMode": self.evidence_mode.value,
            "reasonCode": self.reason_code,
            "selectedBankId": self.selected_bank_id,
            "selectedDifficulty": (
                self.selected_difficulty.value if self.selected_difficulty else None
            ),
            "usedBktFallback": self.used_bkt_fallback,
        }


def load_policy_evaluation_manifest(
    path: str | Path,
    *,
    adaptive_policy: AdaptivePolicyConfig,
) -> PolicyEvaluationManifest:
    """Load the complete manifest and bind it to the authoritative P3 policy."""
    source = Path(path)
    try:
        raw_bytes = source.read_bytes()
        data = yaml.safe_load(raw_bytes)
    except (OSError, yaml.YAMLError) as error:
        raise PolicyEvaluationConfigurationError(
            f"policy evaluation manifest is unavailable: {source}"
        ) from error
    if not isinstance(data, dict):
        raise PolicyEvaluationConfigurationError("policy evaluation manifest must be a mapping")

    _require_exact_keys(
        data,
        {
            "manifestVersion", "study", "claimLabels", "policyArms", "scoreRules",
            "adaptivePolicy", "commonSafetyEnvelope", "outcomes", "reasonCodes",
        },
        "manifest",
    )
    if _string(data, "manifestVersion") != POLICY_EVALUATION_MANIFEST_VERSION:
        raise PolicyEvaluationConfigurationError("unsupported policy evaluation manifest version")

    study_data = _mapping(data, "study")
    _require_exact_keys(
        study_data,
        {"studyVersion", "status", "allowedStatuses", "liveApprovalRequired", "defaultClaimLabel"},
        "study",
    )
    allowed_statuses = tuple(
        _enum(StudyStatus, value, "study status")
        for value in _string_list(study_data, "allowedStatuses")
    )
    if allowed_statuses != tuple(StudyStatus):
        raise PolicyEvaluationConfigurationError("study lifecycle statuses are incomplete or reordered")
    study = StudyConfiguration(
        study_version=_string(study_data, "studyVersion"),
        status=_enum(StudyStatus, _string(study_data, "status"), "study status"),
        allowed_statuses=allowed_statuses,
        live_approval_required=_bool(study_data, "liveApprovalRequired"),
        default_claim_label=_string(study_data, "defaultClaimLabel"),
    )
    if study.study_version != POLICY_EVALUATION_STUDY_VERSION:
        raise PolicyEvaluationConfigurationError("unsupported study contract version")
    if study.status is not StudyStatus.DRAFT:
        raise PolicyEvaluationConfigurationError("the repository manifest cannot silently start a study")
    if not study.live_approval_required:
        raise PolicyEvaluationConfigurationError("live study approval cannot be disabled")

    claims = _mapping(data, "claimLabels")
    _require_exact_keys(claims, {"mechanics", "offlineReplay", "controlledPilot", "modelAssisted"}, "claimLabels")
    expected_claims = {
        "mechanics": "pipeline_demo_only",
        "offlineReplay": "descriptive_replay_only",
        "controlledPilot": "controlled_pilot",
        "modelAssisted": "model_assisted_separate",
    }
    if {key: _string(claims, key) for key in expected_claims} != expected_claims:
        raise PolicyEvaluationConfigurationError("claim labels do not preserve the evidence boundary")
    if study.default_claim_label != expected_claims["mechanics"]:
        raise PolicyEvaluationConfigurationError("a draft manifest must default to pipeline_demo_only")

    arms_data = _mapping(data, "policyArms")
    _require_exact_keys(arms_data, {arm.value for arm in PolicyArm}, "policyArms")
    expected_modes = {
        PolicyArm.P1: SelectionEvidenceMode.SCORE_ONLY,
        PolicyArm.P2: SelectionEvidenceMode.BKT_SCORE_AGREEMENT,
        PolicyArm.P3A: SelectionEvidenceMode.BKT_ONLY_STUDY,
        PolicyArm.P3B: SelectionEvidenceMode.MODEL_ASSISTED,
    }
    expected_policy_versions = {
        PolicyArm.P1: "score-threshold-v1",
        PolicyArm.P2: "bkt-score-agreement-v1",
        PolicyArm.P3A: "guarded-bkt-study-v1",
        PolicyArm.P3B: "guarded-bkt-model-assisted-v1",
    }
    policy_arms = []
    for arm in PolicyArm:
        arm_data = _mapping(arms_data, arm.value)
        _require_exact_keys(arm_data, {"policyVersion", "evidenceMode", "claimLabel"}, arm.value)
        mode = _enum(SelectionEvidenceMode, _string(arm_data, "evidenceMode"), f"{arm.value} evidence mode")
        if mode is not expected_modes[arm]:
            raise PolicyEvaluationConfigurationError(f"{arm.value} has the wrong evidence mode")
        claim_label = _string(arm_data, "claimLabel")
        expected_claim = expected_claims["modelAssisted" if arm is PolicyArm.P3B else "controlledPilot"]
        if claim_label != expected_claim:
            raise PolicyEvaluationConfigurationError(f"{arm.value} has the wrong claim label")
        policy_version = _string(arm_data, "policyVersion")
        if policy_version != expected_policy_versions[arm]:
            raise PolicyEvaluationConfigurationError(f"{arm.value} has the wrong policy version")
        policy_arms.append(PolicyArmConfig(arm, policy_version, mode, claim_label))

    score = _mapping(data, "scoreRules")
    _require_exact_keys(
        score,
        {"denominator", "promotionAtLeast", "demotionAtMost", "promotionInclusive", "demotionInclusive", "p1BelowPromotion", "p1AutomaticDemotion", "p2Disagreement", "p2Neutral"},
        "scoreRules",
    )
    if (
        _string(score, "denominator") != "totalQuestions"
        or not _bool(score, "promotionInclusive")
        or not _bool(score, "demotionInclusive")
        or _string(score, "p1BelowPromotion") != "hold"
        or _bool(score, "p1AutomaticDemotion")
        or _string(score, "p2Disagreement") != "hold"
        or _string(score, "p2Neutral") != "hold"
    ):
        raise PolicyEvaluationConfigurationError("score policy branches do not match the frozen protocol")
    promotion_threshold = _probability(score, "promotionAtLeast")
    demotion_threshold = _probability(score, "demotionAtMost")
    if (
        promotion_threshold != P1_PROMOTION_THRESHOLD
        or demotion_threshold != P2_DEMOTION_THRESHOLD
    ):
        raise PolicyEvaluationConfigurationError("score thresholds do not match the frozen protocol")

    adaptive = _mapping(data, "adaptivePolicy")
    _require_exact_keys(adaptive, {"policyVersion", "sourceSha256"}, "adaptivePolicy")
    adaptive_version = _string(adaptive, "policyVersion")
    adaptive_sha = _sha256(adaptive, "sourceSha256")
    if adaptive_version != adaptive_policy.policy_version or adaptive_sha != adaptive_policy.source_sha256:
        raise PolicyEvaluationConfigurationError("evaluation manifest does not match the adaptive policy")

    safety_data = _mapping(data, "commonSafetyEnvelope")
    _require_exact_keys(
        safety_data,
        {"difficultyOrder", "activeCompatibleBanksOnly", "maximumMovementLevels", "preventImmediateReversal", "preferUnseenBanks", "unavailableBankBehavior"},
        "commonSafetyEnvelope",
    )
    difficulty_order = tuple(_enum(Difficulty, value, "difficulty order") for value in _string_list(safety_data, "difficultyOrder"))
    safety = CommonSafetyEnvelope(
        difficulty_order=difficulty_order,
        active_compatible_banks_only=_bool(safety_data, "activeCompatibleBanksOnly"),
        maximum_movement_levels=_positive_int(safety_data, "maximumMovementLevels"),
        prevent_immediate_reversal=_bool(safety_data, "preventImmediateReversal"),
        prefer_unseen_banks=_bool(safety_data, "preferUnseenBanks"),
        unavailable_bank_behavior=_string(safety_data, "unavailableBankBehavior"),
    )
    if (
        safety.difficulty_order != tuple(Difficulty)
        or not safety.active_compatible_banks_only
        or safety.maximum_movement_levels != 1
        or not safety.prevent_immediate_reversal
        or not safety.prefer_unseen_banks
        or safety.unavailable_bank_behavior != "hold"
        or safety.prevent_immediate_reversal != adaptive_policy.prevent_immediate_reversal
        or safety.prefer_unseen_banks != adaptive_policy.prefer_unseen_banks
    ):
        raise PolicyEvaluationConfigurationError("common safety envelope is incomplete or incompatible")

    outcomes = _mapping(data, "outcomes")
    _require_exact_keys(
        outcomes,
        {"outcomeProtocolVersion", "frozenPredictionTarget", "primaryMetric", "safetyMetric", "challengeOpportunityMetric", "noLaterOutcome", "counterfactualDifficultyMismatch"},
        "outcomes",
    )
    if (
        _string(outcomes, "outcomeProtocolVersion") != POLICY_OUTCOME_PROTOCOL_VERSION
        or _string(outcomes, "frozenPredictionTarget") != PREDICTION_TARGET
        or _string(outcomes, "primaryMetric") != "false_promotion_burden"
        or _string(outcomes, "safetyMetric") != "false_demotion_or_unnecessary_hold_rate"
        or _string(outcomes, "challengeOpportunityMetric") != "challenge_opportunity"
        or _string(outcomes, "noLaterOutcome") != "censored"
        or _string(outcomes, "counterfactualDifficultyMismatch") != "censored"
    ):
        raise PolicyEvaluationConfigurationError("outcome definitions do not match the frozen protocol")

    reason_codes = frozenset(_string_list(data, "reasonCodes"))
    if reason_codes != _REQUIRED_REASON_CODES:
        raise PolicyEvaluationConfigurationError("canonical reason-code table is incomplete or altered")

    return PolicyEvaluationManifest(
        manifest_version=POLICY_EVALUATION_MANIFEST_VERSION,
        study=study,
        policy_arms=tuple(policy_arms),
        promotion_threshold=promotion_threshold,
        demotion_threshold=demotion_threshold,
        adaptive_policy_version=adaptive_version,
        adaptive_policy_sha256=adaptive_sha,
        safety=safety,
        outcome_protocol_version=POLICY_OUTCOME_PROTOCOL_VERSION,
        frozen_prediction_target=PREDICTION_TARGET,
        primary_metric="false_promotion_burden",
        safety_metric="false_demotion_or_unnecessary_hold_rate",
        challenge_opportunity_metric="challenge_opportunity",
        reason_codes=reason_codes,
        source_path=str(source),
        source_sha256=sha256(raw_bytes).hexdigest(),
    )


def select_policy_decision(
    arm: PolicyArm,
    context: PolicyDecisionContext,
    banks: Iterable[EligibleBank],
    *,
    manifest: PolicyEvaluationManifest,
    adaptive_policy: AdaptivePolicyConfig,
) -> CandidatePolicyDecision:
    """Select one bank using a declared arm and the shared safety envelope."""
    if (
        adaptive_policy.policy_version != manifest.adaptive_policy_version
        or adaptive_policy.source_sha256 != manifest.adaptive_policy_sha256
    ):
        raise PolicyEvaluationConfigurationError("selector inputs do not match the frozen manifest")
    active_banks = tuple(bank for bank in banks if bank.is_active)
    if not active_banks:
        return _decision(context, manifest, arm, DecisionDirection.HOLD, None, "no_eligible_bank")
    if arm is PolicyArm.P1:
        direction = DecisionDirection.UP if context.score_rate >= manifest.promotion_threshold else DecisionDirection.HOLD
        reason = "p1_score_promote" if direction is DecisionDirection.UP else "p1_score_hold"
        return _select_direction(context, active_banks, manifest, arm, direction, reason)
    if arm is PolicyArm.P2:
        bkt_direction, bkt_reason = _bkt_direction(context, adaptive_policy)
        score_direction = (
            DecisionDirection.UP
            if context.score_rate >= manifest.promotion_threshold
            else DecisionDirection.DOWN
            if context.score_rate <= manifest.demotion_threshold
            else DecisionDirection.HOLD
        )
        if bkt_direction is score_direction and bkt_direction is not DecisionDirection.HOLD:
            reason = "p2_agreement_promote" if bkt_direction is DecisionDirection.UP else "p2_agreement_demote"
            return _select_direction(context, active_banks, manifest, arm, bkt_direction, reason)
        reason = "p2_neutral_hold" if bkt_direction is score_direction else "p2_disagreement_hold"
        if bkt_reason in {"hard_requires_more_evidence", "anti_oscillation_hold"}:
            reason = bkt_reason
        return _select_direction(context, active_banks, manifest, arm, DecisionDirection.HOLD, reason)
    if arm is PolicyArm.P3B and not context.compatible_model_available:
        raise ValueError("P3b requires compatible model-assisted support-risk evidence")
    return _select_p3(arm, context, active_banks, manifest, adaptive_policy)


def deterministic_policy_decision_id(
    source_attempt_id: str,
    arm: PolicyArm,
    policy_version: str,
    manifest_sha256: str,
) -> str:
    if not source_attempt_id or not policy_version or len(manifest_sha256) != 64:
        raise ValueError("complete decision identity inputs are required")
    payload = json.dumps(
        [source_attempt_id, arm.value, policy_version, manifest_sha256],
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"policy-decision-{sha256(payload).hexdigest()}"


def _select_p3(
    arm: PolicyArm,
    context: PolicyDecisionContext,
    banks: tuple[EligibleBank, ...],
    manifest: PolicyEvaluationManifest,
    adaptive_policy: AdaptivePolicyConfig,
) -> CandidatePolicyDecision:
    support_risk = None if arm is PolicyArm.P3A else context.support_risk
    result = select_next_bank(
        AssignmentContext(
            student_id=context.student_id,
            subtopic_id=context.subtopic_id,
            current_difficulty=context.current_difficulty,
            mastery_probability=context.mastery_probability,
            evidence_count=context.evidence_count,
            support_risk=support_risk,
            last_transition=context.last_transition,
        ),
        banks,
        policy=adaptive_policy,
    )
    if not result.is_assignable:
        hold_candidates = [
            bank for bank in banks if bank.difficulty is context.current_difficulty
        ]
        if hold_candidates:
            hold_candidates.sort(
                key=lambda bank: (
                    bank.exposure_count != 0,
                    bank.exposure_count,
                    bank.bank_id,
                )
            )
            return _decision(
                context,
                manifest,
                arm,
                DecisionDirection.HOLD,
                hold_candidates[0].bank_id,
                "no_eligible_bank",
                selected_difficulty=context.current_difficulty,
                used_bkt_fallback=(arm is PolicyArm.P3A),
            )
    direction = _direction(context.current_difficulty, result.difficulty)
    reason = {
        "cold_start_easy": "p3_cold_start_easy",
        "move_up_mastery": "p3_move_up_mastery",
        "move_up_bkt_fallback": "p3_move_up_bkt_fallback",
        "move_down_support": "p3_move_down_support",
        "stay_easy_support": "p3_stay_easy_support",
        "stay_hard_mastery": "p3_stay_hard_mastery",
        "stay_build_evidence": "p3_stay_build_evidence",
        "stay_target_zone": "p3_stay_target_zone",
        "anti_oscillation_stay": "anti_oscillation_hold",
        "hard_requires_more_evidence": "hard_requires_more_evidence",
        "no_eligible_bank": "no_eligible_bank",
    }[result.reason_code]
    return _decision(
        context,
        manifest,
        arm,
        direction,
        result.bank_id,
        reason,
        selected_difficulty=result.difficulty,
        used_bkt_fallback=(arm is PolicyArm.P3A),
        outcome_status=result.outcome_status,
    )


def _bkt_direction(
    context: PolicyDecisionContext,
    adaptive_policy: AdaptivePolicyConfig,
) -> tuple[DecisionDirection, str | None]:
    thresholds = adaptive_policy.thresholds
    if context.mastery_probability <= thresholds.move_down_mastery:
        direction = DecisionDirection.DOWN
    elif (
        context.mastery_probability >= thresholds.move_up_mastery
        and context.evidence_count >= thresholds.minimum_evidence_for_move_up
    ):
        direction = DecisionDirection.UP
    else:
        return DecisionDirection.HOLD, None
    target = context.current_difficulty.move(1 if direction is DecisionDirection.UP else -1)
    if adaptive_policy.prevent_immediate_reversal and _is_reversal(context, direction):
        return DecisionDirection.HOLD, "anti_oscillation_hold"
    if target is Difficulty.HARD and context.evidence_count < thresholds.minimum_evidence_for_hard:
        return DecisionDirection.HOLD, "hard_requires_more_evidence"
    return direction, None


def _select_direction(
    context: PolicyDecisionContext,
    banks: tuple[EligibleBank, ...],
    manifest: PolicyEvaluationManifest,
    arm: PolicyArm,
    direction: DecisionDirection,
    reason: str,
) -> CandidatePolicyDecision:
    if _is_reversal(context, direction):
        direction, reason = DecisionDirection.HOLD, "anti_oscillation_hold"
    movement = 1 if direction is DecisionDirection.UP else -1 if direction is DecisionDirection.DOWN else 0
    target = context.current_difficulty.move(movement)
    if movement and target is context.current_difficulty:
        reason = "difficulty_upper_bound_hold" if movement > 0 else "difficulty_lower_bound_hold"
        direction = DecisionDirection.HOLD
    candidates = [bank for bank in banks if bank.difficulty is target]
    if not candidates:
        hold_candidates = [
            bank for bank in banks if bank.difficulty is context.current_difficulty
        ]
        if not hold_candidates:
            return _decision(
                context, manifest, arm, DecisionDirection.HOLD, None, "no_eligible_bank"
            )
        hold_candidates.sort(
            key=lambda bank: (
                bank.exposure_count != 0,
                bank.exposure_count,
                bank.bank_id,
            )
        )
        return _decision(
            context,
            manifest,
            arm,
            DecisionDirection.HOLD,
            hold_candidates[0].bank_id,
            "no_eligible_bank",
            selected_difficulty=context.current_difficulty,
        )
    candidates.sort(key=lambda bank: (bank.exposure_count != 0, bank.exposure_count, bank.bank_id))
    return _decision(context, manifest, arm, direction, candidates[0].bank_id, reason, selected_difficulty=target)


def _decision(
    context: PolicyDecisionContext,
    manifest: PolicyEvaluationManifest,
    arm: PolicyArm,
    direction: DecisionDirection,
    selected_bank_id: str | None,
    reason_code: str,
    *,
    selected_difficulty: Difficulty | None = None,
    used_bkt_fallback: bool = False,
    outcome_status: str | None = None,
) -> CandidatePolicyDecision:
    if reason_code not in manifest.reason_codes:
        raise PolicyEvaluationConfigurationError(f"undeclared reason code: {reason_code}")
    arm_config = manifest.arm(arm)
    return CandidatePolicyDecision(
        decision_id=deterministic_policy_decision_id(
            context.source_attempt_id, arm, arm_config.policy_version, manifest.source_sha256
        ),
        source_attempt_id=context.source_attempt_id,
        arm=arm,
        policy_version=arm_config.policy_version,
        claim_label=arm_config.claim_label,
        evidence_mode=arm_config.evidence_mode,
        direction=direction,
        selected_bank_id=selected_bank_id,
        selected_difficulty=selected_difficulty,
        reason_code=reason_code,
        used_bkt_fallback=used_bkt_fallback,
        outcome_status=outcome_status or ("assigned" if selected_bank_id else "fallback"),
    )


def _direction(current: Difficulty, selected: Difficulty | None) -> DecisionDirection:
    if selected is None or selected is current:
        return DecisionDirection.HOLD
    return DecisionDirection.UP if tuple(Difficulty).index(selected) > tuple(Difficulty).index(current) else DecisionDirection.DOWN


def _is_reversal(context: PolicyDecisionContext, direction: DecisionDirection) -> bool:
    if direction is DecisionDirection.HOLD or not context.last_transition:
        return False
    previous = context.last_transition.lower()
    return (direction is DecisionDirection.UP and previous.startswith("move_down")) or (
        direction is DecisionDirection.DOWN and previous.startswith("move_up")
    )


_REQUIRED_REASON_CODES = frozenset(
    {
        "p1_score_promote", "p1_score_hold", "p2_agreement_promote",
        "p2_agreement_demote", "p2_disagreement_hold", "p2_neutral_hold",
        "p3_cold_start_easy", "p3_move_up_mastery", "p3_move_up_bkt_fallback",
        "p3_move_down_support", "p3_stay_easy_support", "p3_stay_hard_mastery",
        "p3_stay_build_evidence", "p3_stay_target_zone", "anti_oscillation_hold",
        "hard_requires_more_evidence", "difficulty_upper_bound_hold",
        "difficulty_lower_bound_hold", "no_eligible_bank",
    }
)


def _require_exact_keys(data: Mapping[str, object], expected: set[str], section: str) -> None:
    if set(data) != expected:
        missing = sorted(expected - set(data))
        extra = sorted(set(data) - expected)
        raise PolicyEvaluationConfigurationError(
            f"{section} keys are invalid; missing={missing}, extra={extra}"
        )


def _mapping(data: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise PolicyEvaluationConfigurationError(f"policy evaluation requires mapping: {key}")
    return value


def _string(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise PolicyEvaluationConfigurationError(f"policy evaluation requires string: {key}")
    return value


def _string_list(data: Mapping[str, object], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
        raise PolicyEvaluationConfigurationError(f"policy evaluation requires string list: {key}")
    if len(set(value)) != len(value):
        raise PolicyEvaluationConfigurationError(f"policy evaluation list contains duplicates: {key}")
    return value


def _bool(data: Mapping[str, object], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise PolicyEvaluationConfigurationError(f"policy evaluation requires boolean: {key}")
    return value


def _probability(data: Mapping[str, object], key: str) -> float:
    value = data.get(key)
    if not isinstance(value, (float, int)) or isinstance(value, bool):
        raise PolicyEvaluationConfigurationError(f"policy evaluation requires probability: {key}")
    value = float(value)
    _validate_probability(value, key)
    return value


def _positive_int(data: Mapping[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise PolicyEvaluationConfigurationError(f"policy evaluation requires positive integer: {key}")
    return value


def _sha256(data: Mapping[str, object], key: str) -> str:
    value = _string(data, key)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise PolicyEvaluationConfigurationError(f"policy evaluation requires lowercase SHA-256: {key}")
    return value


def _enum(enum_type: type[Enum], value: str, label: str):
    try:
        return enum_type(value)
    except ValueError as error:
        raise PolicyEvaluationConfigurationError(f"unknown {label}: {value}") from error


def _validate_probability(value: float, label: str) -> None:
    if not isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{label} must be between zero and one")
