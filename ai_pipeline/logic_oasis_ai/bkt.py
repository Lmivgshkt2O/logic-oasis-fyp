"""Deterministic BKT mastery materialization from trusted U3-R evidence.

The BKT contract deliberately has no wall-clock ordering.  A U3-R finalized
attempt owns the monotonically increasing ``sourceAttemptSequence`` for its
student/subtopic, and each sealed response owns ``sequenceIndex`` within that
attempt.  Those two server-owned fields are the complete replay order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .schemas import FinalizedQuizAttemptRecord, ValidatedResponseRecord
from .validators import validate_bkt_attempt_lineage


BKT_MODEL_VERSION = "bkt-v1"


@dataclass(frozen=True)
class BktParameters:
    """Frozen bkt-v1 priors; live quiz completions never tune these values."""

    prior_knowledge: float = 0.35
    learn_rate: float = 0.18
    guess_rate: float = 0.20
    slip_rate: float = 0.10

    def __post_init__(self) -> None:
        for name, value in (
            ("prior_knowledge", self.prior_knowledge),
            ("learn_rate", self.learn_rate),
            ("guess_rate", self.guess_rate),
            ("slip_rate", self.slip_rate),
        ):
            if not 0.0 < value < 1.0:
                raise ValueError(f"{name} must be between zero and one")


DEFAULT_BKT_PARAMETERS = BktParameters()


@dataclass(frozen=True)
class BktAblationEvidence:
    """One-step-ahead BKT evidence for a single sealed response.

    ``next_response_probability`` is calculated *before* this response is
    observed.  ``p_known_after_attempt`` is calculated only after its answer
    is applied, so neither value can contain a later response.
    """

    student_id: str
    subtopic_id: str
    skill_id: str
    source_attempt_id: str
    source_response_id: str
    source_attempt_sequence: int
    sequence_index: int
    observation_count: int
    model_version: str
    p_known_before_response: float
    next_response_probability: float
    p_known_after_attempt: float


@dataclass(frozen=True)
class MasterySnapshot:
    """A reproducible, per-student/per-subtopic/per-skill BKT state."""

    student_id: str
    subtopic_id: str
    skill_id: str
    mastery_probability: float
    evidence_count: int
    model_version: str
    parameters: BktParameters
    source_attempt_ids: tuple[str, ...]
    source_response_ids: tuple[str, ...]
    source_attempt_sequence: int
    sequence_index: int
    p_known_after_attempt: float
    next_response_probability: float

    def to_firestore_document(self) -> dict[str, object]:
        """Return the server-owned shape a later U8 runtime may materialize."""
        return {
            "studentId": self.student_id,
            "subtopicId": self.subtopic_id,
            "skillId": self.skill_id,
            "pKnown": self.mastery_probability,
            "pLearn": self.parameters.learn_rate,
            "pGuess": self.parameters.guess_rate,
            "pSlip": self.parameters.slip_rate,
            "observationCount": self.evidence_count,
            # Response-level history remains in immutable quiz evidence. The
            # runtime snapshot stores only its bounded latest lineage marker.
            "sourceAttemptId": self.source_attempt_ids[-1],
            "sourceResponseId": self.source_response_ids[-1],
            "sourceAttemptSequence": self.source_attempt_sequence,
            "sequenceIndex": self.sequence_index,
            "pKnownAfterAttempt": self.p_known_after_attempt,
            "nextResponseProbability": self.next_response_probability,
            "modelVersion": self.model_version,
        }


@dataclass(frozen=True)
class BktMaterialization:
    """The complete result of one deterministic trusted-history replay."""

    snapshots: tuple[MasterySnapshot, ...]
    ablation_evidence: tuple[BktAblationEvidence, ...]


@dataclass(frozen=True)
class _ObservationEvent:
    attempt: FinalizedQuizAttemptRecord
    response: ValidatedResponseRecord

    @property
    def state_key(self) -> tuple[str, str, str]:
        return (
            self.attempt.student_id,
            self.attempt.subtopic_id,
            self.response.skill_id,
        )

    @property
    def ordering_key(self) -> tuple[int, int]:
        sequence = self.attempt.source_attempt_sequence
        if sequence is None:  # Defensive; validated before this property is used.
            raise ValueError("attempt is legacy_no_sequence and cannot be trusted final evidence")
        return (sequence, self.response.sequence_index)


def next_response_probability(
    mastery_probability: float,
    *,
    parameters: BktParameters = DEFAULT_BKT_PARAMETERS,
) -> float:
    """Return BKT's one-step-ahead predicted correctness probability."""
    _validate_probability(mastery_probability, "mastery_probability")
    return (
        mastery_probability * (1.0 - parameters.slip_rate)
        + (1.0 - mastery_probability) * parameters.guess_rate
    )


def update_probability(
    mastery_probability: float,
    *,
    is_correct: bool,
    parameters: BktParameters = DEFAULT_BKT_PARAMETERS,
) -> float:
    """Apply one Bayesian observation followed by the fixed learning transition."""
    _validate_probability(mastery_probability, "mastery_probability")
    if not isinstance(is_correct, bool):
        raise ValueError("is_correct must be a boolean")
    if is_correct:
        numerator = mastery_probability * (1.0 - parameters.slip_rate)
        denominator = numerator + ((1.0 - mastery_probability) * parameters.guess_rate)
    else:
        numerator = mastery_probability * parameters.slip_rate
        denominator = numerator + ((1.0 - mastery_probability) * (1.0 - parameters.guess_rate))
    posterior = numerator / denominator
    return posterior + ((1.0 - posterior) * parameters.learn_rate)


def build_bkt_materialization(
    attempts: Iterable[FinalizedQuizAttemptRecord],
    responses_by_attempt: Mapping[str, Iterable[ValidatedResponseRecord]],
    *,
    parameters: BktParameters = DEFAULT_BKT_PARAMETERS,
    model_version: str = BKT_MODEL_VERSION,
) -> BktMaterialization:
    """Replay each independent state by ``(sourceAttemptSequence, sequenceIndex)``.

    Duplicate deliveries of an identical source attempt are collapsed.  A
    conflicting duplicate attempt ID or an ordering-tuple collision is refused
    rather than silently selecting a wall-clock or document-ID tie-breaker.
    """
    if not model_version:
        raise ValueError("model_version is required")
    unique_attempts = _unique_attempts(attempts)
    events = _validated_events(unique_attempts, responses_by_attempt)
    state: dict[tuple[str, str, str], float] = {}
    evidence_by_state: dict[tuple[str, str, str], list[BktAblationEvidence]] = {}

    for event in _ordered_events(events):
        key = event.state_key
        mastery_before = state.get(key, parameters.prior_knowledge)
        predicted_probability = next_response_probability(
            mastery_before,
            parameters=parameters,
        )
        mastery_after = update_probability(
            mastery_before,
            is_correct=event.response.is_correct,
            parameters=parameters,
        )
        state[key] = mastery_after
        attempt_sequence, response_index = event.ordering_key
        evidence_by_state.setdefault(key, []).append(
            BktAblationEvidence(
                student_id=event.attempt.student_id,
                subtopic_id=event.attempt.subtopic_id,
                skill_id=event.response.skill_id,
                source_attempt_id=event.attempt.attempt_id,
                source_response_id=event.response.response_id,
                source_attempt_sequence=attempt_sequence,
                sequence_index=response_index,
                observation_count=len(evidence_by_state[key]) + 1,
                model_version=model_version,
                p_known_before_response=round(mastery_before, 8),
                next_response_probability=round(predicted_probability, 8),
                p_known_after_attempt=round(mastery_after, 8),
            )
        )

    snapshots: list[MasterySnapshot] = []
    all_evidence: list[BktAblationEvidence] = []
    for key in sorted(evidence_by_state):
        rows = evidence_by_state[key]
        latest = rows[-1]
        snapshots.append(
            MasterySnapshot(
                student_id=latest.student_id,
                subtopic_id=latest.subtopic_id,
                skill_id=latest.skill_id,
                mastery_probability=latest.p_known_after_attempt,
                evidence_count=len(rows),
                model_version=model_version,
                parameters=parameters,
                source_attempt_ids=tuple(dict.fromkeys(row.source_attempt_id for row in rows)),
                source_response_ids=tuple(row.source_response_id for row in rows),
                source_attempt_sequence=latest.source_attempt_sequence,
                sequence_index=latest.sequence_index,
                p_known_after_attempt=latest.p_known_after_attempt,
                next_response_probability=latest.next_response_probability,
            )
        )
        all_evidence.extend(rows)
    return BktMaterialization(tuple(snapshots), tuple(all_evidence))


def build_mastery_snapshots(
    attempts: Iterable[FinalizedQuizAttemptRecord],
    responses_by_attempt: Mapping[str, Iterable[ValidatedResponseRecord]],
    *,
    parameters: BktParameters = DEFAULT_BKT_PARAMETERS,
    model_version: str = BKT_MODEL_VERSION,
) -> tuple[MasterySnapshot, ...]:
    """Compatibility entry point returning only the materialized snapshots."""
    return build_bkt_materialization(
        attempts,
        responses_by_attempt,
        parameters=parameters,
        model_version=model_version,
    ).snapshots


def build_bkt_ablation_evidence(
    attempts: Iterable[FinalizedQuizAttemptRecord],
    responses_by_attempt: Mapping[str, Iterable[ValidatedResponseRecord]],
    *,
    parameters: BktParameters = DEFAULT_BKT_PARAMETERS,
    model_version: str = BKT_MODEL_VERSION,
) -> tuple[BktAblationEvidence, ...]:
    """Return typed one-step-ahead evidence without exposing future answers."""
    return build_bkt_materialization(
        attempts,
        responses_by_attempt,
        parameters=parameters,
        model_version=model_version,
    ).ablation_evidence


def _unique_attempts(
    attempts: Iterable[FinalizedQuizAttemptRecord],
) -> tuple[FinalizedQuizAttemptRecord, ...]:
    unique: dict[str, FinalizedQuizAttemptRecord] = {}
    for attempt in attempts:
        existing = unique.get(attempt.attempt_id)
        if existing is None:
            unique[attempt.attempt_id] = attempt
        elif existing != attempt:
            raise ValueError("duplicate attempt ID has conflicting lineage")
    return tuple(unique.values())


def _validated_events(
    attempts: Iterable[FinalizedQuizAttemptRecord],
    responses_by_attempt: Mapping[str, Iterable[ValidatedResponseRecord]],
) -> tuple[_ObservationEvent, ...]:
    events: list[_ObservationEvent] = []
    for attempt in attempts:
        responses = tuple(responses_by_attempt.get(attempt.attempt_id, ()))
        validate_bkt_attempt_lineage(attempt, responses)
        events.extend(_ObservationEvent(attempt, response) for response in responses)
    return tuple(events)


def _ordered_events(events: Iterable[_ObservationEvent]) -> tuple[_ObservationEvent, ...]:
    grouped: dict[tuple[str, str, str], list[_ObservationEvent]] = {}
    for event in events:
        grouped.setdefault(event.state_key, []).append(event)

    ordered: list[_ObservationEvent] = []
    for state_key in sorted(grouped):
        state_events = sorted(grouped[state_key], key=lambda item: item.ordering_key)
        seen_keys: set[tuple[int, int]] = set()
        for event in state_events:
            key = event.ordering_key
            if key in seen_keys:
                raise ValueError("duplicate BKT ordering tuple-key")
            seen_keys.add(key)
        ordered.extend(state_events)
    return tuple(ordered)


def _validate_probability(value: float, field: str) -> None:
    if not isinstance(value, (float, int)) or isinstance(value, bool) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{field} must be between zero and one")
