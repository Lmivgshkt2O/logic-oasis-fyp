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
from training.export_real_attempts import export_anonymized_attempts


NOW = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)


def firestore_attempts():
    return [{
        "id": "attempt-1", "attemptId": "attempt-1", "sessionId": "session-1", "studentId": "student-1",
        "totalQuestions": 2, "correctCount": 1, "score": 50, "responseIds": ["response-1", "response-2"],
        "finalizationStatus": "finalized", "validationStatus": "finalized", "dataSource": "runtime_callable",
        "finalizedAt": NOW, "topicId": "topic-1", "subtopicId": "subtopic-1", "bankId": "bank-1",
        "difficultyLevel": "Easy", "contentVersion": "v1",
    }]


def firestore_responses():
    return [
        {
            "id": "response-1", "responseId": "response-1", "sessionId": "session-1", "attemptId": "attempt-1",
            "studentId": "student-1", "questionId": "question-1", "skillId": "skill-1", "sequenceIndex": 0,
            "serverIsCorrect": True, "validationStatus": "validated", "createdAt": NOW,
            "responseTimeMs": 1000, "hintCount": 0,
        },
        {
            "id": "response-2", "responseId": "response-2", "sessionId": "session-1", "attemptId": "attempt-1",
            "studentId": "student-1", "questionId": "question-2", "skillId": "skill-1", "sequenceIndex": 1,
            "serverIsCorrect": False, "validationStatus": "validated", "createdAt": NOW,
            "responseTimeMs": 3000, "hintCount": 2,
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
            else:
                row[key] = str(value)
        rows.append(row)
    return rows


class SourceParityTests(unittest.TestCase):
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
            files = export_anonymized_attempts(
                dataset, temporary_directory, dataset_version="2026-07-16-r1", anonymization_salt="test-salt"
            )
            with files["attempts"].open(encoding="utf-8") as attempts_file:
                exported_attempts = list(csv.DictReader(attempts_file))
            manifest = json.loads(files["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(exported_attempts[0]["provenance"], "real")
            self.assertNotIn("student-1", files["attempts"].read_text(encoding="utf-8"))
            self.assertFalse(manifest["containsRawStudentIds"])
            reloaded = load_csv_files(files["attempts"], files["responses"], provenance="real")
            self.assertEqual(build_attempt_features(dataset, anonymization_salt="test-salt"), build_attempt_features(reloaded, anonymization_salt="test-salt"))

    def test_candidate_cannot_become_active_until_explicitly_promoted(self):
        registry = ModelRegistry()
        candidate = ModelArtifact(
            artifact_id="xgb-2026-07-16", model_type="xgboost", model_version="v1",
            feature_schema_version="quiz-attempt-features-v1", training_dataset_version="2026-07-16-r1",
            artifact_sha256="abc123",
        )
        registry.register_candidate(candidate)
        with self.assertRaisesRegex(ValueError, "no promoted runtime model"):
            registry.active_runtime_model()
        promoted = registry.promote(candidate.artifact_id, promoted_at=NOW)
        self.assertEqual(registry.active_runtime_model(), promoted)


if __name__ == "__main__":
    unittest.main()
