"""Produce governed, HMAC-pseudonymized U6 training releases.

The caller is responsible for obtaining the versioned Secret Manager value
under the data-export service account.  This module deliberately receives the
key in memory, never serializes it, and never records a local destination in a
release manifest.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import hmac
import json
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Iterable

from logic_oasis_ai.features import FEATURE_SCHEMA_VERSION
from logic_oasis_ai.sources.firestore_source import SourceDataset


EXPORT_SCHEMA_VERSION = "pseudonymized-attempt-export-v2"
PROTECTED_RELEASE_PREFIX = "gs://logic-oasis-fyp-protected-data/real-data-releases/"

ATTEMPT_FIELDS = (
    "attemptId", "sessionId", "studentKey", "totalQuestions", "correctCount", "score",
    "responseIds", "finalizationStatus", "validationStatus", "dataSource", "finalizedAt",
    "sourceAttemptSequence", "topicId", "subtopicId", "bankId", "difficultyLevel",
    "contentVersion", "yearLevel", "assignmentId", "assignmentSource",
    "adaptivePolicyVersion", "provenance",
)
RESPONSE_FIELDS = (
    "responseId", "sessionId", "attemptId", "studentKey", "questionId", "skillId",
    "sequenceIndex", "serverIsCorrect", "validationStatus", "createdAt", "responseTimeMs",
    "responseTimeQuality", "hintCount", "hintTelemetryStatus", "questionVersion",
    "contentVersion", "priorExposureCount", "provenance",
)


@dataclass(frozen=True)
class RealDataRelease:
    """The approval/custody record required before a final-data export."""

    release_id: str
    dataset_version: str
    consent_ethics_reference: str
    data_steward: str
    steward_approved_at: datetime
    collection_started_at: datetime
    collection_ended_at: datetime
    retention_review_at: datetime
    storage_path: str
    export_key_version: str

    def __post_init__(self) -> None:
        for field in (
            "release_id", "dataset_version", "consent_ethics_reference", "data_steward", "storage_path", "export_key_version"
        ):
            if not getattr(self, field):
                raise ValueError(f"{field} is required")
        expected_path = f"{PROTECTED_RELEASE_PREFIX}{self.release_id}/"
        if self.storage_path != expected_path:
            raise ValueError("release storage_path must be its protected versioned GCS release path")
        if not self.export_key_version.startswith("logic-oasis-export-pseudonymization-key-v"):
            raise ValueError("export_key_version must name the versioned HMAC Secret Manager secret")
        timestamps = (
            self.steward_approved_at,
            self.collection_started_at,
            self.collection_ended_at,
            self.retention_review_at,
        )
        if any(value.tzinfo is None for value in timestamps):
            raise ValueError("release timestamps must include a timezone")
        if self.collection_ended_at < self.collection_started_at:
            raise ValueError("collection end must not precede collection start")


def hmac_pseudonym(namespace: str, raw_identifier: str, key: bytes | str) -> str:
    """Return a stable release-series pseudonym without retaining its raw ID."""
    if not namespace or not raw_identifier:
        raise ValueError("namespace and raw_identifier are required")
    key_bytes = key.encode("utf-8") if isinstance(key, str) else key
    if not key_bytes:
        raise ValueError("a non-empty HMAC key is required")
    digest = hmac.new(key_bytes, f"{namespace}:{raw_identifier}".encode("utf-8"), sha256).hexdigest()
    return f"{namespace}_{digest}"


def export_real_attempts(
    dataset: SourceDataset,
    output_directory: str | Path,
    *,
    release: RealDataRelease,
    pseudonymization_key: bytes | str,
) -> dict[str, Path]:
    """Write approved, pseudonymized files and a safe, reproducible manifest.

    ``output_directory`` is a controlled execution destination (for example a
    Cloud Storage mount in deployment tests).  It intentionally never appears
    in ``manifest.json``; only ``release.storage_path`` is recorded.
    """
    if dataset.provenance != "real":
        raise ValueError("only approved real records may be exported for final evaluation")
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)

    attempt_keys = {
        attempt.attempt_id: hmac_pseudonym("attempt", attempt.attempt_id, pseudonymization_key)
        for attempt in dataset.attempts
    }
    session_keys = {
        attempt.session_id: hmac_pseudonym("session", attempt.session_id, pseudonymization_key)
        for attempt in dataset.attempts
    }
    response_keys = {
        response.response_id: hmac_pseudonym("response", response.response_id, pseudonymization_key)
        for responses in dataset.responses_by_attempt.values() for response in responses
    }
    staging = Path(mkdtemp(prefix=".release-staging-", dir=output))
    try:
        staged_attempts = staging / "attempts.csv"
        staged_responses = staging / "responses.csv"
        _write_csv(staged_attempts, ATTEMPT_FIELDS, _attempt_rows(dataset, attempt_keys, session_keys, response_keys, pseudonymization_key))
        _write_csv(staged_responses, RESPONSE_FIELDS, _response_rows(dataset, attempt_keys, session_keys, response_keys, pseudonymization_key))
        manifest = _manifest(release, dataset, staged_attempts, staged_responses)
        _assert_safe_manifest(manifest, pseudonymization_key)
        staged_manifest = staging / "manifest.json"
        staged_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        attempts_path = output / "attempts.csv"
        responses_path = output / "responses.csv"
        manifest_path = output / "manifest.json"
        staged_attempts.replace(attempts_path)
        staged_responses.replace(responses_path)
        staged_manifest.replace(manifest_path)
        return {"attempts": attempts_path, "responses": responses_path, "manifest": manifest_path}
    finally:
        rmtree(staging, ignore_errors=True)


def export_anonymized_attempts(*args, **kwargs):
    """Compatibility name; releases are pseudonymized, not anonymous."""
    return export_real_attempts(*args, **kwargs)


def _attempt_rows(dataset, attempt_keys, session_keys, response_keys, key) -> Iterable[dict[str, object]]:
    for attempt in dataset.attempts:
        context = dataset.attempt_context_by_id[attempt.attempt_id]
        yield {
            "attemptId": attempt_keys[attempt.attempt_id], "sessionId": session_keys[attempt.session_id],
            "studentKey": hmac_pseudonym("student", attempt.student_id, key),
            "totalQuestions": attempt.total_questions, "correctCount": attempt.correct_count, "score": attempt.score,
            "responseIds": "|".join(response_keys[value] for value in attempt.response_ids),
            "finalizationStatus": attempt.finalization_status, "validationStatus": attempt.validation_status,
            "dataSource": attempt.data_source, "finalizedAt": attempt.finalized_at.isoformat(),
            "sourceAttemptSequence": attempt.source_attempt_sequence,
            "topicId": context.topic_id, "subtopicId": context.subtopic_id, "bankId": context.bank_id,
            "difficultyLevel": context.difficulty_level, "contentVersion": context.content_version,
            "yearLevel": context.year_level, "assignmentId": context.assignment_id,
            "assignmentSource": context.assignment_source, "adaptivePolicyVersion": context.adaptive_policy_version,
            "provenance": dataset.provenance,
        }


def _response_rows(dataset, attempt_keys, session_keys, response_keys, key) -> Iterable[dict[str, object]]:
    for attempt in dataset.attempts:
        for response in dataset.responses_by_attempt[attempt.attempt_id]:
            metrics = dataset.response_metrics_by_id[response.response_id]
            yield {
                "responseId": response_keys[response.response_id], "sessionId": session_keys[response.session_id],
                "attemptId": attempt_keys[response.attempt_id], "studentKey": hmac_pseudonym("student", response.student_id, key),
                "questionId": response.question_id, "skillId": response.skill_id, "sequenceIndex": response.sequence_index,
                "serverIsCorrect": str(response.is_correct).lower(), "validationStatus": response.validation_status,
                "createdAt": response.created_at.isoformat(), "responseTimeMs": metrics.response_time_ms,
                "responseTimeQuality": metrics.response_time_quality, "hintCount": metrics.hint_count,
                "hintTelemetryStatus": metrics.hint_telemetry_status, "questionVersion": metrics.question_version,
                "contentVersion": metrics.content_version, "priorExposureCount": metrics.prior_exposure_count,
                "provenance": dataset.provenance,
            }


def _manifest(release: RealDataRelease, dataset: SourceDataset, attempts_path: Path, responses_path: Path) -> dict[str, object]:
    return {
        "releaseId": release.release_id,
        "datasetVersion": release.dataset_version,
        "exportSchemaVersion": EXPORT_SCHEMA_VERSION,
        "sourceSchemaVersion": dataset.schema_version,
        "featureSchemaVersion": FEATURE_SCHEMA_VERSION,
        "provenance": "real",
        "consentEthicsReference": release.consent_ethics_reference,
        "dataSteward": release.data_steward,
        "stewardApprovedAt": release.steward_approved_at.isoformat(),
        "collectionWindow": {"startedAt": release.collection_started_at.isoformat(), "endedAt": release.collection_ended_at.isoformat()},
        "storagePath": release.storage_path,
        "retentionReviewAt": release.retention_review_at.isoformat(),
        "exportKeyVersion": release.export_key_version,
        "attemptCount": len(dataset.attempts),
        "responseCount": sum(len(rows) for rows in dataset.responses_by_attempt.values()),
        "sourceAttemptOrdering": "(sourceAttemptSequence, sequenceIndex)",
        "pairAuditFields": ["bankId", "difficultyLevel", "contentVersion", "assignmentId", "assignmentSource", "adaptivePolicyVersion", "questionVersion", "priorExposureCount"],
        "fileSha256": {"attempts.csv": _file_sha256(attempts_path), "responses.csv": _file_sha256(responses_path)},
        "containsRawIdentifiers": False,
        "containsSecretMaterial": False,
    }


def _assert_safe_manifest(manifest: dict[str, object], key: bytes | str) -> None:
    serialized = json.dumps(manifest, sort_keys=True)
    key_text = key.decode("utf-8", errors="ignore") if isinstance(key, bytes) else key
    if key_text and key_text in serialized:
        raise ValueError("manifest must not contain HMAC key material")
    if "\\\\" in serialized or ":\\\\" in serialized:
        raise ValueError("manifest must not contain a local path")


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, fields: tuple[str, ...], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
