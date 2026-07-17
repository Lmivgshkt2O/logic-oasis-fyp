"""Versioned feature construction from validated source datasets only."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

from .sources.firestore_source import SourceDataset


FEATURE_SCHEMA_VERSION = "quiz-attempt-features-v2"
BASE_FEATURE_NAMES = ("correct_rate", "mean_response_time_ms")


@dataclass(frozen=True)
class AttemptFeatureRow:
    """One leakage-safe feature row; future-attempt labels belong to U7."""

    attempt_id: str
    student_key: str
    topic_id: str
    subtopic_id: str
    bank_id: str
    difficulty_level: str
    content_version: str
    finalized_at: str
    total_questions: int
    correct_count: int
    correct_rate: float
    mean_response_time_ms: float
    mean_hint_count: float
    provenance: str
    feature_schema_version: str = FEATURE_SCHEMA_VERSION
    source_attempt_sequence: int | None = None
    year_level: int | None = None
    assignment_source: str = ""
    adaptive_policy_version: str = ""
    skill_ids: tuple[str, ...] = ()
    question_ids: tuple[str, ...] = ()
    response_ids: tuple[str, ...] = ()
    question_versions: tuple[str, ...] = ()
    response_time_quality: str = "client_reported_unverified"

    def to_model_features(self) -> dict[str, float]:
        """Return the numeric fields eligible for an eventual U7 comparison."""
        return {
            "correct_rate": self.correct_rate,
            "mean_response_time_ms": self.mean_response_time_ms,
        }


def build_attempt_features(
    dataset: SourceDataset,
    *,
    anonymization_salt: str,
) -> tuple[AttemptFeatureRow, ...]:
    """Build deterministic features from records already validated by an adapter."""
    if not anonymization_salt:
        raise ValueError("anonymization_salt is required")
    rows: list[AttemptFeatureRow] = []
    for attempt in dataset.attempts:
        responses = dataset.responses_by_attempt[attempt.attempt_id]
        metrics = [dataset.response_metrics_by_id[response.response_id] for response in responses]
        context = dataset.attempt_context_by_id[attempt.attempt_id]
        rows.append(
            AttemptFeatureRow(
                attempt_id=dataset.attempt_key_by_attempt_id.get(
                    attempt.attempt_id,
                    anonymized_key("attempt", attempt.attempt_id, anonymization_salt),
                ),
                student_key=dataset.student_key_by_student_id.get(
                    attempt.student_id,
                    anonymized_key("student", attempt.student_id, anonymization_salt),
                ),
                topic_id=context.topic_id,
                subtopic_id=context.subtopic_id,
                bank_id=context.bank_id,
                difficulty_level=context.difficulty_level,
                content_version=context.content_version,
                finalized_at=attempt.finalized_at.isoformat(),
                total_questions=attempt.total_questions,
                correct_count=attempt.correct_count,
                correct_rate=round(attempt.correct_count / attempt.total_questions, 8),
                mean_response_time_ms=round(_mean(metric.response_time_ms for metric in metrics), 8),
                mean_hint_count=round(_mean(metric.hint_count for metric in metrics), 8),
                provenance=dataset.provenance,
                source_attempt_sequence=attempt.source_attempt_sequence,
                year_level=context.year_level,
                assignment_source=context.assignment_source,
                adaptive_policy_version=context.adaptive_policy_version,
                skill_ids=tuple(sorted({response.skill_id for response in responses})),
                question_ids=tuple(sorted(response.question_id for response in responses)),
                response_ids=tuple(sorted(response.response_id for response in responses)),
                question_versions=tuple(sorted({metric.question_version for metric in metrics})),
                response_time_quality=_shared_response_time_quality(metrics),
            )
        )
    return tuple(rows)


def anonymized_key(namespace: str, raw_value: str, salt: str) -> str:
    """Produce a stable dataset-local pseudonym without retaining raw identity."""
    return sha256(f"{namespace}:{salt}:{raw_value}".encode("utf-8")).hexdigest()


def _mean(values: Iterable[int]) -> float:
    materialized = tuple(values)
    if not materialized:
        raise ValueError("validated attempt must contain responses")
    return sum(materialized) / len(materialized)


def _shared_response_time_quality(metrics: Iterable[object]) -> str:
    qualities = {getattr(metric, "response_time_quality") for metric in metrics}
    if len(qualities) != 1:
        raise ValueError("validated attempt response-time quality must be consistent")
    return qualities.pop()
