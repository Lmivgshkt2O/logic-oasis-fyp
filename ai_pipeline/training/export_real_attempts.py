"""Export anonymized trusted U3 evidence for reproducible offline evaluation."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from logic_oasis_ai.features import FEATURE_SCHEMA_VERSION, anonymized_key
from logic_oasis_ai.sources.firestore_source import SourceDataset


EXPORT_SCHEMA_VERSION = "anonymized-attempt-export-v1"

ATTEMPT_FIELDS = (
    "attemptId", "sessionId", "studentKey", "totalQuestions", "correctCount", "score",
    "responseIds", "finalizationStatus", "validationStatus", "dataSource", "finalizedAt",
    "topicId", "subtopicId", "bankId", "difficultyLevel", "contentVersion", "provenance",
)
RESPONSE_FIELDS = (
    "responseId", "sessionId", "attemptId", "studentKey", "questionId", "skillId",
    "sequenceIndex", "serverIsCorrect", "validationStatus", "createdAt", "responseTimeMs",
    "hintCount", "provenance",
)


def export_anonymized_attempts(
    dataset: SourceDataset,
    output_directory: str | Path,
    *,
    dataset_version: str,
    anonymization_salt: str,
) -> dict[str, Path]:
    """Write reproducible CSV evidence and a manifest without raw student IDs."""
    if dataset.provenance != "real":
        raise ValueError("only real approved records may be exported for final evaluation")
    if not dataset_version or not anonymization_salt:
        raise ValueError("dataset_version and anonymization_salt are required")
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)

    attempt_keys = {attempt.attempt_id: anonymized_key("attempt", attempt.attempt_id, anonymization_salt) for attempt in dataset.attempts}
    session_keys = {attempt.session_id: anonymized_key("session", attempt.session_id, anonymization_salt) for attempt in dataset.attempts}
    response_keys = {
        response.response_id: anonymized_key("response", response.response_id, anonymization_salt)
        for responses in dataset.responses_by_attempt.values() for response in responses
    }
    attempts_path = output / "attempts.csv"
    responses_path = output / "responses.csv"
    _write_csv(attempts_path, ATTEMPT_FIELDS, _attempt_rows(dataset, attempt_keys, session_keys, response_keys, anonymization_salt))
    _write_csv(responses_path, RESPONSE_FIELDS, _response_rows(dataset, attempt_keys, session_keys, response_keys, anonymization_salt))
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps({
        "datasetVersion": dataset_version,
        "exportSchemaVersion": EXPORT_SCHEMA_VERSION,
        "sourceSchemaVersion": dataset.schema_version,
        "featureSchemaVersion": FEATURE_SCHEMA_VERSION,
        "provenance": dataset.provenance,
        "attemptCount": len(dataset.attempts),
        "responseCount": len(response_keys),
        "containsRawStudentIds": False,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"attempts": attempts_path, "responses": responses_path, "manifest": manifest_path}


def _attempt_rows(dataset, attempt_keys, session_keys, response_keys, salt) -> Iterable[dict[str, object]]:
    for attempt in dataset.attempts:
        context = dataset.attempt_context_by_id[attempt.attempt_id]
        yield {
            "attemptId": attempt_keys[attempt.attempt_id], "sessionId": session_keys[attempt.session_id],
            "studentKey": anonymized_key("student", attempt.student_id, salt),
            "totalQuestions": attempt.total_questions, "correctCount": attempt.correct_count, "score": attempt.score,
            "responseIds": "|".join(response_keys[value] for value in attempt.response_ids),
            "finalizationStatus": attempt.finalization_status, "validationStatus": attempt.validation_status,
            "dataSource": attempt.data_source, "finalizedAt": attempt.finalized_at.isoformat(),
            "topicId": context.topic_id, "subtopicId": context.subtopic_id, "bankId": context.bank_id,
            "difficultyLevel": context.difficulty_level, "contentVersion": context.content_version,
            "provenance": dataset.provenance,
        }


def _response_rows(dataset, attempt_keys, session_keys, response_keys, salt) -> Iterable[dict[str, object]]:
    for attempt in dataset.attempts:
        for response in dataset.responses_by_attempt[attempt.attempt_id]:
            metrics = dataset.response_metrics_by_id[response.response_id]
            yield {
                "responseId": response_keys[response.response_id], "sessionId": session_keys[response.session_id],
                "attemptId": attempt_keys[response.attempt_id], "studentKey": anonymized_key("student", response.student_id, salt),
                "questionId": response.question_id, "skillId": response.skill_id, "sequenceIndex": response.sequence_index,
                "serverIsCorrect": str(response.is_correct).lower(), "validationStatus": response.validation_status,
                "createdAt": response.created_at.isoformat(), "responseTimeMs": metrics.response_time_ms,
                "hintCount": metrics.hint_count, "provenance": dataset.provenance,
            }


def _write_csv(path: Path, fields: tuple[str, ...], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
