"""CSV adapter that reconstructs the same trusted source contract as Firestore."""

from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable, Mapping

from .firestore_source import SourceDataset, load_firestore_dataset
from ..time_utils import parse_timestamp


def load_csv_dataset(
    attempt_rows: Iterable[Mapping[str, str]],
    response_rows: Iterable[Mapping[str, str]],
    *,
    provenance: str,
    allow_emulator_records: bool = False,
) -> SourceDataset:
    """Parse exported CSV rows, then run the exact Firestore validation path."""
    attempt_rows = tuple(attempt_rows)
    response_rows = tuple(response_rows)
    _validate_row_provenance((*attempt_rows, *response_rows), provenance)
    dataset = load_firestore_dataset(
        (_parse_attempt_row(row) for row in attempt_rows),
        (_parse_response_row(row) for row in response_rows),
        provenance=provenance,
        allow_emulator_records=allow_emulator_records,
    )
    is_anonymized_export = any(row.get("studentKey") for row in attempt_rows)
    if not is_anonymized_export:
        return dataset
    pseudonyms = {
        _student_identity(row): _student_identity(row)
        for row in (*attempt_rows, *response_rows)
        if row.get("studentKey")
    }
    attempt_keys = {_string(row, "attemptId"): _string(row, "attemptId") for row in attempt_rows}
    return replace(
        dataset,
        student_key_by_student_id=pseudonyms,
        attempt_key_by_attempt_id=attempt_keys,
    )


def load_csv_files(
    attempts_path: str | Path,
    responses_path: str | Path,
    *,
    provenance: str,
    allow_emulator_records: bool = False,
) -> SourceDataset:
    with Path(attempts_path).open(newline="", encoding="utf-8") as attempts_file, Path(responses_path).open(
        newline="", encoding="utf-8"
    ) as responses_file:
        return load_csv_dataset(
            csv.DictReader(attempts_file),
            csv.DictReader(responses_file),
            provenance=provenance,
            allow_emulator_records=allow_emulator_records,
        )


def _parse_attempt_row(row: Mapping[str, str]) -> tuple[str, dict[str, Any]]:
    attempt_id = _string(row, "attemptId")
    response_ids = tuple(item for item in _string(row, "responseIds").split("|") if item)
    if not response_ids:
        raise ValueError("responseIds is required")
    attempt = {
        "attemptId": attempt_id,
        "sessionId": _string(row, "sessionId"),
        "studentId": _student_identity(row),
        "totalQuestions": _integer(row, "totalQuestions"),
        "correctCount": _integer(row, "correctCount"),
        "score": _integer(row, "score"),
        "responseIds": list(response_ids),
        "finalizationStatus": _string(row, "finalizationStatus"),
        "validationStatus": _string(row, "validationStatus"),
        "dataSource": _string(row, "dataSource"),
        "finalizedAt": _timestamp(row, "finalizedAt"),
        "topicId": _string(row, "topicId"),
        "subtopicId": _string(row, "subtopicId"),
        "bankId": _string(row, "bankId"),
        "difficultyLevel": _string(row, "difficultyLevel"),
        "contentVersion": _string(row, "contentVersion"),
        "yearLevel": _integer(row, "yearLevel"),
        "assignmentId": _string(row, "assignmentId"),
        "assignmentSource": _string(row, "assignmentSource"),
        "adaptivePolicyVersion": _string(row, "adaptivePolicyVersion"),
    }
    sequence = _optional_integer(row, "sourceAttemptSequence")
    if sequence is not None:
        attempt["sourceAttemptSequence"] = sequence
    return attempt_id, attempt


def _parse_response_row(row: Mapping[str, str]) -> tuple[str, dict[str, Any]]:
    response_id = _string(row, "responseId")
    response = {
        "responseId": response_id,
        "sessionId": _string(row, "sessionId"),
        "attemptId": _string(row, "attemptId"),
        "studentId": _student_identity(row),
        "questionId": _string(row, "questionId"),
        "skillId": _string(row, "skillId"),
        "sequenceIndex": _integer(row, "sequenceIndex"),
        "serverIsCorrect": _boolean(row, "serverIsCorrect"),
        "validationStatus": _string(row, "validationStatus"),
        "createdAt": _timestamp(row, "createdAt"),
        "responseTimeMs": _integer(row, "responseTimeMs"),
        "responseTimeQuality": _string(row, "responseTimeQuality"),
        "hintCount": _integer(row, "hintCount"),
        "hintTelemetryStatus": _string(row, "hintTelemetryStatus"),
        "questionVersion": _string(row, "questionVersion"),
        "contentVersion": _string(row, "contentVersion"),
    }
    prior_exposure = _optional_integer(row, "priorExposureCount")
    if prior_exposure is not None:
        response["priorExposureCount"] = prior_exposure
    return response_id, response


def _student_identity(row: Mapping[str, str]) -> str:
    has_student_id = bool(row.get("studentId"))
    has_student_key = bool(row.get("studentKey"))
    if has_student_id == has_student_key:
        raise ValueError("CSV row must contain exactly one of studentId or studentKey")
    return _string(row, "studentId") if has_student_id else _string(row, "studentKey")


def _validate_row_provenance(rows: Iterable[Mapping[str, str]], provenance: str) -> None:
    for row in rows:
        row_provenance = row.get("provenance")
        if row_provenance and row_provenance != provenance:
            raise ValueError("CSV row provenance does not match the requested dataset provenance")


def _string(row: Mapping[str, str], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} is required")
    return value


def _integer(row: Mapping[str, str], field: str) -> int:
    value = _string(row, field)
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{field} must be an integer") from error
    if parsed < 0:
        raise ValueError(f"{field} must be non-negative")
    return parsed


def _optional_integer(row: Mapping[str, str], field: str) -> int | None:
    value = row.get(field)
    if value in (None, ""):
        return None
    return _integer(row, field)


def _boolean(row: Mapping[str, str], field: str) -> bool:
    value = _string(row, field).lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"{field} must be true or false")


def _timestamp(row: Mapping[str, str], field: str):
    return parse_timestamp(_string(row, field), field)
