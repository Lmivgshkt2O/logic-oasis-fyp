"""Trusted U3 attempt/response records accepted by downstream AI work."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ValidatedResponseRecord:
    response_id: str
    session_id: str
    attempt_id: str
    student_id: str
    question_id: str
    skill_id: str
    sequence_index: int
    is_correct: bool
    validation_status: str
    created_at: datetime

    @classmethod
    def from_firestore(cls, response_id: str, data: dict[str, Any]) -> "ValidatedResponseRecord":
        return cls(
            response_id=response_id,
            session_id=_required_string(data, "sessionId"),
            attempt_id=_required_string(data, "attemptId"),
            student_id=_required_string(data, "studentId"),
            question_id=_required_string(data, "questionId"),
            skill_id=_required_string(data, "skillId"),
            sequence_index=_required_int(data, "sequenceIndex"),
            is_correct=_required_bool(data, "serverIsCorrect"),
            validation_status=_required_string(data, "validationStatus"),
            created_at=_required_datetime(data, "createdAt"),
        )


@dataclass(frozen=True)
class FinalizedQuizAttemptRecord:
    attempt_id: str
    session_id: str
    student_id: str
    total_questions: int
    correct_count: int
    score: int
    response_ids: tuple[str, ...]
    finalization_status: str
    validation_status: str
    data_source: str
    finalized_at: datetime

    @classmethod
    def from_firestore(cls, attempt_id: str, data: dict[str, Any]) -> "FinalizedQuizAttemptRecord":
        response_ids = data.get("responseIds")
        if not isinstance(response_ids, list) or any(not isinstance(item, str) for item in response_ids):
            raise ValueError("attempt responseIds must be a string list")
        return cls(
            attempt_id=attempt_id,
            session_id=_required_string(data, "sessionId"),
            student_id=_required_string(data, "studentId"),
            total_questions=_required_int(data, "totalQuestions"),
            correct_count=_required_int(data, "correctCount"),
            score=_required_int(data, "score"),
            response_ids=tuple(response_ids),
            finalization_status=_required_string(data, "finalizationStatus"),
            validation_status=_required_string(data, "validationStatus"),
            data_source=_required_string(data, "dataSource"),
            finalized_at=_required_datetime(data, "finalizedAt"),
        )


def _required_string(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} is required")
    return value


def _required_int(data: dict[str, Any], field: str) -> int:
    value = data.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _required_bool(data: dict[str, Any], field: str) -> bool:
    value = data.get(field)
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value


def _required_datetime(data: dict[str, Any], field: str) -> datetime:
    value = data.get(field)
    if not isinstance(value, datetime):
        raise ValueError(f"{field} must be a Firestore timestamp")
    if value.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return value
