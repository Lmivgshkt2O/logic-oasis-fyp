"""AQC-E1 frozen external adaptive schema records (contract representation only).

This module freezes the external data-record shapes and the generic difficulty
candidate boundary agreed for the ASSISTments Stage-B pathway. It contains no
calibration engine and no policy replay: it exists so the E1 contract is
machine-checkable and so later E2/E3 stages build on typed, validated records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from fractions import Fraction
from hashlib import sha256
from math import isfinite

from logic_oasis_ai.adaptive_policy import Difficulty


# Frozen E1 constants (mirrored by assistments_adaptive_contract_v1.yaml).
CALIBRATION_WINDOW_START = datetime(2019, 2, 25, 0, 0, 0, tzinfo=timezone.utc)
CALIBRATION_WINDOW_END = datetime(2021, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
EVALUATION_WINDOW_START = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
EVALUATION_WINDOW_END = datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

MINIMUM_CALIBRATION_LEARNERS = 20
SKILL_CATALOG_MINIMUM_CALIBRATED_PROBLEMS = 9
SKILL_CATALOG_MINIMUM_PER_TIER = 3
ATTEMPT_PURITY_THRESHOLD = Fraction(2, 3)

EXTERNAL_PROVENANCE = "external_real"
BKT_VERSION = "bkt-v1"
REPLAY_MODE = "one_step_non_propagating"
REVERSAL_HISTORY_SOURCE = "observed_proxy_difficulty_history"
PRODUCTION_PROMOTION_ALLOWED = False
CONTAINS_RAW_IDENTIFIERS = False
EXTERNAL_CANDIDATE_KEY_NAMESPACE = "external_proxy_"

PROXY_DIFFICULTY_VALUES = ("proxy_easy", "proxy_moderate", "proxy_hard")
CALIBRATION_STATUS_VALUES = ("calibrated", "insufficient_problem_evidence")
SKILL_PROXY_STATUS_VALUES = ("sufficient_skill_catalog", "insufficient_skill_catalog")


class ExternalContractError(ValueError):
    """Raised when an external contract record is missing, altered, or invalid."""


class ProxyDifficulty(str, Enum):
    EASY = "proxy_easy"
    MODERATE = "proxy_moderate"
    HARD = "proxy_hard"


class CandidateKind(str, Enum):
    NATIVE_BANK = "native_bank"
    EXTERNAL_PROXY_TIER = "external_proxy_tier"


class SourceMode(str, Enum):
    NATIVE_RUNTIME = "native_runtime"
    ASSISTMENTS_EXTERNAL = "assistments_external"


class ExternalEvidenceMode(str, Enum):
    EXTERNAL_REAL_PROXY_DIFFICULTY = "external_real_proxy_difficulty"
    NATIVE_RUNTIME = "native_runtime"
    PIPELINE_DEMO_ONLY = "pipeline_demo_only"
    CONTROLLED_DEMO = "controlled_demo"


class ExternalClaimLevel(str, Enum):
    PIPELINE_DEMO_ONLY = "pipeline_demo_only"
    EXTERNAL_DESCRIPTIVE_REPLAY = "external_descriptive_replay"
    EXTERNAL_DESCRIPTIVE_REPLAY_LIMITED = "external_descriptive_replay_limited"
    EXTERNAL_REPLAY_INCONCLUSIVE = "external_replay_inconclusive"


FORBIDDEN_EXTERNAL_CLAIM_LEVELS = frozenset(
    {"superiority", "causal_effect", "KSSR_validated", "production_validated"}
)

REQUIRED_CENSOR_REASONS = frozenset(
    {
        "insufficient_problem_evidence",
        "insufficient_skill_catalog",
        "mixed_proxy_difficulty",
        "external_proxy_tier_unavailable",
        "counterfactual_proxy_tier_mismatch",
        "no_next_eligible_attempt",
        "identical_problem_set_repeat",
        "chronology_ambiguous",
        "invalid_next_outcome",
    }
)

FORBIDDEN_NATIVE_FIELDS = frozenset(
    {
        "finalizationStatus",
        "validationStatus",
        "dataSource: runtime_callable",
        "native sourceAttemptSequence",
        "Logic Oasis bankId",
        "questionBanks.version",
        "questionBanks.isActive",
        "Logic Oasis contentVersionId",
        "native adaptiveAssignment ID",
        "native historical policyVersion as source metadata",
    }
)


def validate_provenance_external_real(provenance: str) -> str:
    """Fail-closed provenance boundary: external rows never become native."""
    if provenance != EXTERNAL_PROVENANCE:
        raise ExternalContractError(
            f"external ASSISTments provenance must be {EXTERNAL_PROVENANCE!r}, got {provenance!r}"
        )
    return provenance


def in_calibration_window(timestamp: datetime) -> bool:
    """True only inside the frozen 2019-02-25..2021-12-31 calibration window."""
    if timestamp.tzinfo is None:
        return False
    return CALIBRATION_WINDOW_START <= timestamp <= CALIBRATION_WINDOW_END


def in_evaluation_window(timestamp: datetime) -> bool:
    """True only inside the frozen 2022-01-01..2023-12-31 evaluation window."""
    if timestamp.tzinfo is None:
        return False
    return EVALUATION_WINDOW_START <= timestamp <= EVALUATION_WINDOW_END


def windows_do_not_overlap() -> bool:
    """Freeze: the calibration and evaluation windows are disjoint."""
    return CALIBRATION_WINDOW_END < EVALUATION_WINDOW_START


def smoothed_correct_probability(correct_responses: int, total_graded_responses: int) -> float:
    """Frozen smoothing rule: p_correct = (correct + 1) / (total + 2)."""
    if not isinstance(correct_responses, int) or isinstance(correct_responses, bool):
        raise ExternalContractError("correct_responses must be an integer")
    if not isinstance(total_graded_responses, int) or isinstance(total_graded_responses, bool):
        raise ExternalContractError("total_graded_responses must be an integer")
    if correct_responses < 0 or total_graded_responses < correct_responses:
        raise ExternalContractError("correct/total counts are invalid")
    return (correct_responses + 1) / (total_graded_responses + 2)


def difficulty_score(correct_responses: int, total_graded_responses: int) -> float:
    """Frozen difficulty rule: difficulty_score = 1 - p_correct."""
    probability = smoothed_correct_probability(correct_responses, total_graded_responses)
    return 1.0 - probability


def problem_set_fingerprint(source_skill_code: str, problem_keys: tuple[str, ...]) -> str:
    """Frozen external problem-set fingerprint (never a native bankId)."""
    if not source_skill_code:
        raise ExternalContractError("sourceSkillCode is required for a problem-set fingerprint")
    if not problem_keys or any(not key for key in problem_keys):
        raise ExternalContractError("valid problem keys are required for a problem-set fingerprint")
    payload = source_skill_code + "".join(sorted(set(problem_keys)))
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvaluationDifficultyOption:
    """Generic difficulty candidate accepted by the AQC-2 selector boundary.

    Native runtime delivery keeps ``candidateKind=native_bank`` and a concrete
    ``nativeBankId``. ASSISTments external candidates use
    ``candidateKind=external_proxy_tier`` with ``nativeBankId=None`` and a
    namespaced ``externalCandidateKey``, so no native bankId is fabricated.
    """

    difficulty: Difficulty
    candidate_kind: CandidateKind
    native_bank_id: str | None = None
    external_candidate_key: str | None = None
    available: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_kind, CandidateKind):
            raise ExternalContractError("candidateKind is not a frozen candidate kind")
        if self.candidate_kind is CandidateKind.NATIVE_BANK:
            if not self.native_bank_id or self.external_candidate_key is not None:
                raise ExternalContractError(
                    "native_bank candidates require nativeBankId and forbid externalCandidateKey"
                )
        else:
            if self.native_bank_id is not None:
                raise ExternalContractError(
                    "external_proxy_tier candidates must not carry a nativeBankId"
                )
            if not self.external_candidate_key or not self.external_candidate_key.startswith(
                EXTERNAL_CANDIDATE_KEY_NAMESPACE
            ):
                raise ExternalContractError(
                    "external_proxy_tier candidates require a namespaced externalCandidateKey"
                )

    def to_document(self) -> dict[str, object]:
        return {
            "difficulty": self.difficulty.value,
            "candidateKind": self.candidate_kind.value,
            "nativeBankId": self.native_bank_id,
            "externalCandidateKey": self.external_candidate_key,
            "available": self.available,
        }


def external_proxy_candidate(
    proxy_tier: ProxyDifficulty, *, available: bool = True
) -> EvaluationDifficultyOption:
    """Build the ASSISTments external candidate without any native bankId."""
    difficulty = {
        ProxyDifficulty.EASY: Difficulty.EASY,
        ProxyDifficulty.MODERATE: Difficulty.MODERATE,
        ProxyDifficulty.HARD: Difficulty.HARD,
    }[proxy_tier]
    return EvaluationDifficultyOption(
        difficulty=difficulty,
        candidate_kind=CandidateKind.EXTERNAL_PROXY_TIER,
        external_candidate_key=f"{EXTERNAL_CANDIDATE_KEY_NAMESPACE}{proxy_tier.value}",
        available=available,
    )


def native_bank_candidate(
    difficulty: Difficulty, bank_id: str, *, available: bool = True
) -> EvaluationDifficultyOption:
    """Build the unchanged native runtime candidate."""
    return EvaluationDifficultyOption(
        difficulty=difficulty,
        candidate_kind=CandidateKind.NATIVE_BANK,
        native_bank_id=bank_id,
        available=available,
    )


@dataclass(frozen=True)
class ExternalProblemDifficultyV1:
    """Frozen per-problem calibration record (schema only, no calibration run)."""

    dataset_release_id: str
    external_problem_key: str
    source_skill_code: str
    calibration_start: datetime
    calibration_end: datetime
    calibration_learner_count: int
    calibration_response_count: int
    correct_response_count: int
    smoothed_correct_probability: float
    difficulty_score: float
    proxy_difficulty: ProxyDifficulty | None
    calibration_status: str
    provenance: str

    def __post_init__(self) -> None:
        validate_provenance_external_real(self.provenance)
        if not self.dataset_release_id or not self.external_problem_key or not self.source_skill_code:
            raise ExternalContractError("release id, problem key, and skill code are required")
        if self.calibration_start.tzinfo is None or self.calibration_end.tzinfo is None:
            raise ExternalContractError("calibration timestamps must be timezone-aware UTC")
        if not (self.calibration_start <= self.calibration_end):
            raise ExternalContractError("calibration window is inverted")
        if self.calibration_learner_count < 1 or self.calibration_response_count < 1:
            raise ExternalContractError("calibration counts must be positive")
        if not 0 <= self.correct_response_count <= self.calibration_response_count:
            raise ExternalContractError("correct counts are invalid")
        expected_probability = smoothed_correct_probability(
            self.correct_response_count, self.calibration_response_count
        )
        if not _close(self.smoothed_correct_probability, expected_probability):
            raise ExternalContractError("smoothedCorrectProbability violates the frozen smoothing rule")
        if not _close(self.difficulty_score, 1.0 - expected_probability):
            raise ExternalContractError("difficultyScore violates the frozen difficulty rule")
        if self.calibration_status not in CALIBRATION_STATUS_VALUES:
            raise ExternalContractError("calibrationStatus is not in the frozen vocabulary")
        if self.calibration_status == "calibrated":
            if self.calibration_learner_count < MINIMUM_CALIBRATION_LEARNERS:
                raise ExternalContractError(
                    "calibrated problems require the frozen minimum independent calibration learners"
                )
            if not isinstance(self.proxy_difficulty, ProxyDifficulty):
                raise ExternalContractError("calibrated problems require a proxy tier")
        else:
            if self.proxy_difficulty is not None:
                raise ExternalContractError(
                    "insufficient_problem_evidence requires proxyDifficulty null"
                )


@dataclass(frozen=True)
class ExternalAdaptiveAttemptV1:
    """Frozen external adaptive attempt record (schema only, no reconstruction)."""

    dataset_release_id: str
    external_attempt_key: str
    external_student_key: str
    external_assignment_key: str
    source_skill_code: str
    source_timestamp: datetime
    external_attempt_sequence: int
    problem_keys: tuple[str, ...]
    total_questions: int
    correct_count: int
    correct_rate: float
    bkt_mastery_probability: float
    bkt_evidence_count: int
    bkt_version: str
    current_proxy_difficulty: ProxyDifficulty | None
    proxy_difficulty_purity: float | None
    external_problem_set_fingerprint: str
    previous_observed_proxy_difficulty: ProxyDifficulty | None
    fresh_problem_fraction: float | None
    provenance: str

    def __post_init__(self) -> None:
        validate_provenance_external_real(self.provenance)
        if not self.dataset_release_id or not self.external_attempt_key:
            raise ExternalContractError("release id and attempt key are required")
        if not self.external_student_key or not self.external_assignment_key:
            raise ExternalContractError("student and assignment keys are required")
        if not self.source_skill_code:
            raise ExternalContractError("sourceSkillCode is required and must never be mixed")
        if self.source_timestamp.tzinfo is None:
            raise ExternalContractError("source timestamp must be timezone-aware UTC")
        if self.external_attempt_sequence < 1:
            raise ExternalContractError("externalAttemptSequence must be positive")
        if not self.problem_keys or any(not key for key in self.problem_keys):
            raise ExternalContractError("problemKeys are required")
        if self.total_questions < 1 or not 0 <= self.correct_count <= self.total_questions:
            raise ExternalContractError("score counts are invalid")
        expected_rate = self.correct_count / self.total_questions
        if not _close(self.correct_rate, expected_rate):
            raise ExternalContractError("correctRate violates the score rule")
        if not isfinite(self.bkt_mastery_probability) or not 0.0 <= self.bkt_mastery_probability <= 1.0:
            raise ExternalContractError("bktMasteryProbability must be between zero and one")
        if self.bkt_evidence_count < 1:
            raise ExternalContractError("bktEvidenceCount must be positive")
        if self.bkt_version != BKT_VERSION:
            raise ExternalContractError("bktVersion does not match the frozen bkt-v1 contract")
        if self.current_proxy_difficulty is not None:
            if self.proxy_difficulty_purity is None or self.proxy_difficulty_purity < _fraction_float(
                ATTEMPT_PURITY_THRESHOLD
            ):
                raise ExternalContractError(
                    "a current proxy tier requires the frozen 2/3 dominance purity rule"
                )
        else:
            if (
                self.proxy_difficulty_purity is not None
                and self.proxy_difficulty_purity >= _fraction_float(ATTEMPT_PURITY_THRESHOLD)
            ):
                raise ExternalContractError(
                    "a null current tier cannot carry a dominant-tier purity value"
                )
        expected_fingerprint = problem_set_fingerprint(self.source_skill_code, self.problem_keys)
        if self.external_problem_set_fingerprint != expected_fingerprint:
            raise ExternalContractError(
                "externalProblemSetFingerprint violates the frozen fingerprint rule"
            )
        if self.fresh_problem_fraction is not None and not (
            0.0 <= self.fresh_problem_fraction <= 1.0
        ):
            raise ExternalContractError("freshProblemFraction must be between zero and one")


def _fraction_float(fraction: Fraction) -> float:
    return float(fraction.numerator) / float(fraction.denominator)


def _close(actual: float, expected: float, tolerance: float = 1e-9) -> bool:
    return isfinite(actual) and abs(actual - expected) <= tolerance
