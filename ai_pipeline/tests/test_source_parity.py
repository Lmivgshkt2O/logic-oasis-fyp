import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from logic_oasis_ai.features import build_attempt_features
from logic_oasis_ai.model_registry import ModelArtifact, ModelRegistry
from logic_oasis_ai.sources.csv_source import load_csv_dataset, load_csv_files
from logic_oasis_ai.sources.firestore_source import load_firestore_dataset
from training.export_real_attempts import (
    PROTECTED_RELEASE_PREFIX,
    RealDataRelease,
    export_real_attempts,
)


NOW = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)


def firestore_attempts():
    return [{
        "id": "attempt-1", "attemptId": "attempt-1", "sessionId": "session-1", "studentId": "student-1",
        "totalQuestions": 2, "correctCount": 1, "score": 50, "responseIds": ["response-1", "response-2"],
        "finalizationStatus": "finalized", "validationStatus": "finalized", "dataSource": "runtime_callable",
        "sourceAttemptSequence": 1,
        "finalizedAt": NOW, "topicId": "topic-1", "subtopicId": "subtopic-1", "bankId": "bank-1",
        "difficultyLevel": "Easy", "contentVersion": "v1", "yearLevel": 4,
        "assignmentId": "cold_start_easy", "assignmentSource": "cold_start_easy",
        "adaptivePolicyVersion": "adaptive-policy-v1",
    }]


def firestore_responses():
    return [
        {
            "id": "response-1", "responseId": "response-1", "sessionId": "session-1", "attemptId": "attempt-1",
            "studentId": "student-1", "questionId": "question-1", "skillId": "skill-1", "sequenceIndex": 0,
            "serverIsCorrect": True, "validationStatus": "validated", "createdAt": NOW,
            "responseTimeMs": 1000, "responseTimeQuality": "client_reported_unverified",
            "hintCount": 0, "hintTelemetryStatus": "not_supported",
            "questionVersion": "v1", "contentVersion": "v1", "priorExposureCount": None,
        },
        {
            "id": "response-2", "responseId": "response-2", "sessionId": "session-1", "attemptId": "attempt-1",
            "studentId": "student-1", "questionId": "question-2", "skillId": "skill-1", "sequenceIndex": 1,
            "serverIsCorrect": False, "validationStatus": "validated", "createdAt": NOW,
            "responseTimeMs": 3000, "responseTimeQuality": "client_reported_unverified",
            "hintCount": 0, "hintTelemetryStatus": "not_supported",
            "questionVersion": "v1", "contentVersion": "v1", "priorExposureCount": None,
        },
    ]


def csv_rows(documents):
    rows = []
    for document in documents:
        row = {key: value for key, value in document.items() if key != "id"}
        for key, value in tuple(row.items()):
            if isinstance(value, datetime):
                row[key] = value.isoformat()
            elif isinstance(value, bool):
                row[key] = str(value).lower()
            elif isinstance(value, list):
                row[key] = "|".join(value)
            elif value is None:
                row[key] = ""
            else:
                row[key] = str(value)
        rows.append(row)
    return rows


class SourceParityTests(unittest.TestCase):
    def release(self):
        return RealDataRelease(
            release_id="release-2026-07", dataset_version="real_attempts_v1_2026-07",
            consent_ethics_reference="ethics-2026-01", data_steward="supervisor@example.edu",
            steward_approved_at=NOW, collection_started_at=NOW, collection_ended_at=NOW,
            retention_review_at=datetime(2027, 7, 16, tzinfo=timezone.utc),
            storage_path=f"{PROTECTED_RELEASE_PREFIX}release-2026-07/",
            export_key_version="logic-oasis-export-pseudonymization-key-v1",
        )
    def test_firestore_and_csv_build_identical_features(self):
        firestore = load_firestore_dataset(firestore_attempts(), firestore_responses(), provenance="real")
        csv_dataset = load_csv_dataset(csv_rows(firestore_attempts()), csv_rows(firestore_responses()), provenance="real")

        self.assertEqual(
            build_attempt_features(firestore, anonymization_salt="test-salt"),
            build_attempt_features(csv_dataset, anonymization_salt="test-salt"),
        )

    def test_missing_or_invalid_fields_fail_validation(self):
        missing_metrics = firestore_responses()
        del missing_metrics[0]["responseTimeMs"]
        with self.assertRaisesRegex(ValueError, "responseTimeMs"):
            load_firestore_dataset(firestore_attempts(), missing_metrics, provenance="real")

        invalid_attempt = firestore_attempts()
        invalid_attempt[0]["dataSource"] = "legacy_client"
        with self.assertRaisesRegex(ValueError, "trusted finalized runtime"):
            load_firestore_dataset(invalid_attempt, firestore_responses(), provenance="real")

    def test_sequence_less_attempt_is_legacy_and_rejected_from_final_evidence(self):
        legacy = firestore_attempts()
        del legacy[0]["sourceAttemptSequence"]
        with self.assertRaisesRegex(ValueError, "legacy_no_sequence"):
            load_firestore_dataset(legacy, firestore_responses(), provenance="real")

    def test_u3r_telemetry_contract_rejects_invalid_values(self):
        excessive_time = firestore_responses()
        excessive_time[0]["responseTimeMs"] = 900_001
        with self.assertRaisesRegex(ValueError, "between 0 and 900000"):
            load_firestore_dataset(firestore_attempts(), excessive_time, provenance="real")

        client_defined_hint_state = firestore_responses()
        client_defined_hint_state[0]["hintTelemetryStatus"] = "available"
        with self.assertRaisesRegex(ValueError, "hintTelemetryStatus"):
            load_firestore_dataset(firestore_attempts(), client_defined_hint_state, provenance="real")

    def test_csv_preserves_u3r_sequence_and_server_owned_telemetry(self):
        dataset = load_csv_dataset(
            csv_rows(firestore_attempts()), csv_rows(firestore_responses()), provenance="real"
        )
        attempt = dataset.attempts[0]
        response = dataset.responses_by_attempt[attempt.attempt_id][0]
        metrics = dataset.response_metrics_by_id[response.response_id]
        self.assertEqual(1, attempt.source_attempt_sequence)
        self.assertEqual("client_reported_unverified", metrics.response_time_quality)
        self.assertEqual("not_supported", metrics.hint_telemetry_status)

    def test_synthetic_rows_are_rejected_from_final_evaluation(self):
        with self.assertRaisesRegex(ValueError, "only approved real records"):
            load_firestore_dataset(firestore_attempts(), firestore_responses(), provenance="synthetic_test")

        mismatch = csv_rows(firestore_attempts())
        mismatch[0]["provenance"] = "seed_demo"
        with self.assertRaisesRegex(ValueError, "provenance"):
            load_csv_dataset(mismatch, csv_rows(firestore_responses()), provenance="real")

    def test_csv_rejects_ambiguous_raw_and_anonymized_identity(self):
        attempts = csv_rows(firestore_attempts())
        attempts[0]["studentKey"] = "pseudonym"
        with self.assertRaisesRegex(ValueError, "exactly one"):
            load_csv_dataset(attempts, csv_rows(firestore_responses()), provenance="real")

    def test_duplicate_attempts_are_rejected(self):
        attempts = firestore_attempts()
        with self.assertRaisesRegex(ValueError, "duplicate attempt ID"):
            load_firestore_dataset(attempts + attempts, firestore_responses(), provenance="real")

    def test_export_preserves_provenance_and_removes_raw_student_id(self):
        dataset = load_firestore_dataset(firestore_attempts(), firestore_responses(), provenance="real")
        with TemporaryDirectory() as temporary_directory:
            files = export_real_attempts(
                dataset, temporary_directory, release=self.release(), pseudonymization_key="test-hmac-key"
            )
            with files["attempts"].open(encoding="utf-8") as attempts_file:
                exported_attempts = list(csv.DictReader(attempts_file))
            manifest = json.loads(files["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(exported_attempts[0]["provenance"], "real")
            self.assertNotIn("student-1", files["attempts"].read_text(encoding="utf-8"))
            self.assertFalse(manifest["containsRawIdentifiers"])
            self.assertEqual("logic-oasis-export-pseudonymization-key-v1", manifest["exportKeyVersion"])
            self.assertNotIn(str(temporary_directory), json.dumps(manifest))
            reloaded = load_csv_files(files["attempts"], files["responses"], provenance="real")
            original = build_attempt_features(dataset, anonymization_salt="test-salt")[0]
            reloaded_row = build_attempt_features(reloaded, anonymization_salt="test-salt")[0]
            self.assertEqual(original.to_model_features(), reloaded_row.to_model_features())

    def test_candidate_cannot_become_active_until_explicitly_promoted(self):
        registry = ModelRegistry()
        candidate = ModelArtifact(
            artifact_id="xgb-2026-07-16", model_type="xgboost", model_version="v1",
            feature_schema_version="quiz-attempt-features-v1", training_dataset_version="2026-07-16-r1",
            artifact_sha256="abc123", evaluation_status="evaluated", evaluation_report_sha256="report123",
            artifact_manifest_sha256="manifest123", promotion_gate_status="passed",
            approval_id="approval-1", approved_by="supervisor@example.edu", approved_at=NOW,
            approval_rationale="evaluation reviewed",
        )
        registry.register_candidate(candidate)
        with self.assertRaisesRegex(ValueError, "no promoted runtime model"):
            registry.active_runtime_model()
        promoted = registry.promote(candidate.artifact_id, promoted_at=NOW)
        self.assertEqual(registry.active_runtime_model(), promoted)


if __name__ == "__main__":
    unittest.main()
