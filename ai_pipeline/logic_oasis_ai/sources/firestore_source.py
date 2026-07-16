"""Convert Firestore documents into one validated, read-only source contract.

This module deliberately accepts already-fetched documents.  It does not hold
credentials, query Firestore, or write derived records; the later U8 runtime is
the only place that may orchestrate production reads and writes.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from ..schemas import FinalizedQuizAttemptRecord, ValidatedResponseRecord
from ..validators import validate_response_lineage


SOURCE_SCHEMA_VERSION = "attempt-evidence-v1"
APPROVED_PROVENANCE = frozenset({"real", "emulator_verified"})
KNOWN_PROVENANCE = APPROVED_PROVENANCE | frozenset({"seed_demo", "synthetic_test"})


@dataclass(frozen=True)
class AttemptContext:
    """Non-answer-key context attached to a finalized attempt."""

    topic_id: str
    subtopic_id: str
    bank_id: str
    difficulty_level: str
    content_version: str


@dataclass(frozen=True)
class ResponseMetrics:
    response_time_ms: int
    hint_count: int


@dataclass(frozen=True)
class SourceDataset:
    """Trusted, validated evidence ready for feature construction or export."""

    attempts: tuple[FinalizedQuizAttemptRecord, ...]
    responses_by_attempt: Mapping[str, tuple[ValidatedResponseRecord, ...]]
    attempt_context_by_id: Mapping[str, AttemptContext]
    response_metrics_by_id: Mapping[str, ResponseMetrics]
    provenance: str
    schema_version: str = SOURCE_SCHEMA_VERSION
    student_key_by_student_id: Mapping[str, str] = field(default_factory=dict)
    attempt_key_by_attempt_id: Mapping[str, str] = field(default_factory=dict)


def load_firestore_dataset(
    attempt_documents: Iterable[object],
    response_documents: Iterable[object],
    *,
    provenance: str,
    allow_emulator_records: bool = False,
) -> SourceDataset:
    """Validate Firestore-like snapshots against the U3 trusted record gate.

    Each item may be a ``(document_id, mapping)`` pair, a mapping containing
    ``id``/``documentId``, or a Firestore snapshot exposing ``id`` and
    ``to_dict``.  The supplied provenance is a deliberate dataset/export choice
    rather than a claim made by client-owned Firestore data.
    """
    _validate_provenance(provenance, allow_emulator_records=allow_emulator_records)
    attempts = _indexed_documents(attempt_documents, "attempt")
    responses = _indexed_documents(response_documents, "response")

    parsed_attempts: list[FinalizedQuizAttemptRecord] = []
    contexts: dict[str, AttemptContext] = {}
    for attempt_id, data in attempts.items():
        _assert_document_id(data, "attemptId", attempt_id)
        parsed_attempts.append(FinalizedQuizAttemptRecord.from_firestore(attempt_id, data))
        contexts[attempt_id] = AttemptContext(
            topic_id=_required_string(data, "topicId"),
            subtopic_id=_required_string(data, "subtopicId"),
            bank_id=_required_string(data, "bankId"),
            difficulty_level=_required_string(data, "difficultyLevel"),
            content_version=_required_string(data, "contentVersion"),
        )

    responses_by_attempt: dict[str, list[ValidatedResponseRecord]] = defaultdict(list)
    metrics: dict[str, ResponseMetrics] = {}
    for response_id, data in responses.items():
        _assert_document_id(data, "responseId", response_id)
        response = ValidatedResponseRecord.from_firestore(response_id, data)
        if response_id in metrics:
            raise ValueError(f"duplicate response ID: {response_id}")
        responses_by_attempt[response.attempt_id].append(response)
        metrics[response_id] = ResponseMetrics(
            response_time_ms=_required_non_negative_int(data, "responseTimeMs"),
            hint_count=_required_non_negative_int(data, "hintCount"),
        )

    _assert_no_orphan_responses(responses_by_attempt, attempts)
    ordered_attempts = tuple(sorted(parsed_attempts, key=lambda item: (item.finalized_at, item.attempt_id)))
    frozen_responses: dict[str, tuple[ValidatedResponseRecord, ...]] = {}
    for attempt in ordered_attempts:
        rows = tuple(sorted(responses_by_attempt[attempt.attempt_id], key=lambda row: row.sequence_index))
        validate_response_lineage(attempt, rows)
        frozen_responses[attempt.attempt_id] = rows

    return SourceDataset(
        attempts=ordered_attempts,
        responses_by_attempt=frozen_responses,
        attempt_context_by_id=contexts,
        response_metrics_by_id=metrics,
        provenance=provenance,
    )


def _validate_provenance(provenance: str, *, allow_emulator_records: bool) -> None:
    if provenance not in KNOWN_PROVENANCE:
        raise ValueError("provenance is not recognized")
    if provenance == "real":
        return
    if provenance == "emulator_verified" and allow_emulator_records:
        return
    raise ValueError("only approved real records may be used for final evaluation")


def _indexed_documents(documents: Iterable[object], kind: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in documents:
        document_id, data = _document_pair(item, kind)
        if document_id in indexed:
            raise ValueError(f"duplicate {kind} ID: {document_id}")
        indexed[document_id] = data
    return indexed


def _document_pair(item: object, kind: str) -> tuple[str, dict[str, Any]]:
    if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) and isinstance(item[1], Mapping):
        return item[0], dict(item[1])
    if isinstance(item, Mapping):
        data = dict(item)
        document_id = data.pop("documentId", data.pop("id", None))
        if not isinstance(document_id, str) or not document_id:
            raise ValueError(f"{kind} document ID is required")
        return document_id, data
    document_id = getattr(item, "id", None)
    to_dict = getattr(item, "to_dict", None)
    data = to_dict() if callable(to_dict) else None
    if not isinstance(document_id, str) or not document_id or not isinstance(data, Mapping):
        raise ValueError(f"{kind} document must expose an ID and mapping data")
    return document_id, dict(data)


def _assert_document_id(data: Mapping[str, Any], field: str, document_id: str) -> None:
    value = data.get(field)
    if value is not None and value != document_id:
        raise ValueError(f"{field} does not match its document ID")


def _assert_no_orphan_responses(
    responses_by_attempt: Mapping[str, list[ValidatedResponseRecord]],
    attempts: Mapping[str, Mapping[str, Any]],
) -> None:
    orphan_attempt_ids = sorted(set(responses_by_attempt) - set(attempts))
    if orphan_attempt_ids:
        raise ValueError(f"responses reference unknown attempt: {orphan_attempt_ids[0]}")


def _required_string(data: Mapping[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} is required")
    return value


def _required_non_negative_int(data: Mapping[str, Any], field: str) -> int:
    value = data.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value
