"""Deterministic BKT mastery snapshots from trusted U3 response evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping

from .schemas import FinalizedQuizAttemptRecord, ValidatedResponseRecord
from .validators import validate_response_lineage


BKT_MODEL_VERSION = "bkt-v1"


@dataclass(frozen=True)
class BktParameters:
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
class MasterySnapshot:
    """A reproducible, per-student/per-skill BKT materialization candidate."""

    student_id: str
    skill_id: str
    mastery_probability: float
    evidence_count: int
    model_version: str
    parameters: BktParameters
    source_attempt_ids: tuple[str, ...]
    source_response_ids: tuple[str, ...]
    latest_response_at: datetime

    def to_firestore_document(self) -> dict[str, object]:
        """Return the server-owned shape to be written by the later U8 runtime."""
        return {
            "studentId": self.student_id,
            "skillId": self.skill_id,
            "pKnown": self.mastery_probability,
            "pLearn": self.parameters.learn_rate,
            "pGuess": self.parameters.guess_rate,
            "pSlip": self.parameters.slip_rate,
            "observationCount": self.evidence_count,
            "sourceAttemptIds": list(self.source_attempt_ids),
            "sourceResponseIds": list(self.source_response_ids),
            "lastObservedAt": self.latest_response_at,
            "modelVersion": self.model_version,
        }


@dataclass(frozen=True)
class _ObservationEvent:
    created_at: datetime
    finalized_at: datetime
    attempt_id: str
    sequence_index: int
    response: ValidatedResponseRecord

    def sort_key(self) -> tuple[datetime, datetime, str, int]:
        return (
            self.created_at,
            self.finalized_at,
            self.attempt_id,
            self.sequence_index,
        )


@dataclass(frozen=True)
class _EvidenceRow:
    attempt_id: str
    response_id: str
    created_at: datetime


def update_probability(
    mastery_probability: float,
    *,
    is_correct: bool,
    parameters: BktParameters = DEFAULT_BKT_PARAMETERS,
) -> float:
    """Apply one Bayesian observation then the fixed learning transition."""
    if is_correct:
        numerator = mastery_probability * (1.0 - parameters.slip_rate)
        denominator = numerator + (
            (1.0 - mastery_probability) * parameters.guess_rate
        )
    else:
        numerator = mastery_probability * parameters.slip_rate
        denominator = numerator + (
            (1.0 - mastery_probability) * (1.0 - parameters.guess_rate)
        )
    posterior = numerator / denominator
    return posterior + ((1.0 - posterior) * parameters.learn_rate)


def build_mastery_snapshots(
    attempts: Iterable[FinalizedQuizAttemptRecord],
    responses_by_attempt: Mapping[str, Iterable[ValidatedResponseRecord]],
    *,
    parameters: BktParameters = DEFAULT_BKT_PARAMETERS,
    model_version: str = BKT_MODEL_VERSION,
) -> tuple[MasterySnapshot, ...]:
    """Build deterministic snapshots from unique, trusted finalized attempts.

    Reprocessing the same attempt ID is intentionally a no-op. The caller can
    rebuild a snapshot from the complete trusted history without incrementing
    BKT state twice.
    """
    unique_attempts: dict[str, FinalizedQuizAttemptRecord] = {}
    for attempt in attempts:
        unique_attempts.setdefault(attempt.attempt_id, attempt)

    events: list[_ObservationEvent] = []
    for attempt in unique_attempts.values():
        responses = tuple(responses_by_attempt.get(attempt.attempt_id, ()))
        validate_response_lineage(attempt, responses)
        for response in responses:
            events.append(
                _ObservationEvent(
                    response.created_at,
                    attempt.finalized_at,
                    attempt.attempt_id,
                    response.sequence_index,
                    response,
                )
            )

    state: dict[tuple[str, str], float] = {}
    evidence: dict[tuple[str, str], list[_EvidenceRow]] = {}
    for event in sorted(events, key=_ObservationEvent.sort_key):
        response = event.response
        key = (response.student_id, response.skill_id)
        state[key] = update_probability(
            state.get(key, parameters.prior_knowledge),
            is_correct=response.is_correct,
            parameters=parameters,
        )
        evidence.setdefault(key, []).append(
            _EvidenceRow(
                attempt_id=event.attempt_id,
                response_id=response.response_id,
                created_at=response.created_at,
            ),
        )

    snapshots = []
    for (student_id, skill_id), mastery in sorted(state.items()):
        rows = evidence[(student_id, skill_id)]
        snapshots.append(
            MasterySnapshot(
                student_id=student_id,
                skill_id=skill_id,
                mastery_probability=round(mastery, 8),
                evidence_count=len(rows),
                model_version=model_version,
                parameters=parameters,
                source_attempt_ids=tuple(dict.fromkeys(row.attempt_id for row in rows)),
                source_response_ids=tuple(row.response_id for row in rows),
                latest_response_at=rows[-1].created_at,
            )
        )
    return tuple(snapshots)
