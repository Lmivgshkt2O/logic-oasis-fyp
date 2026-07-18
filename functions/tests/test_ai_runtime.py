from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai_pipeline"))
sys.path.insert(0, str(ROOT / "functions"))

import ai_runtime
from ai_runtime import FirestoreRuntimeGateway, RuntimeBundle, RuntimeClaim, RuntimeFailure, process_finalized_attempt


NOW = datetime(2026, 7, 17, tzinfo=timezone.utc)


class MemoryGateway:
    def __init__(self, attempt: dict, responses: list[dict]) -> None:
        self.attempt_doc = attempt
        self.responses = responses
        self.jobs: dict[str, dict] = {}
        self.statuses: dict[str, dict] = {}
        self.finalized: list[dict] = []

    def attempt(self, attempt_id):
        return self.attempt_doc if attempt_id == self.attempt_doc["attemptId"] else None

    def claim(self, attempt):
        job = self.jobs.setdefault(attempt["attemptId"], {"attemptCount": 0, "status": "queued"})
        if job["status"] in ai_runtime.TERMINAL_STATES:
            return RuntimeClaim(job["attemptCount"], job["status"])
        job["attemptCount"] += 1
        job["status"] = "processing"
        self.statuses.setdefault(attempt["attemptId"], {"analysisState": "processing", "displayCode": "analysis_in_progress"})
        return RuntimeClaim(job["attemptCount"])

    def history(self, attempt):
        return [dict(self.attempt_doc, documentId=self.attempt_doc["attemptId"])], [
            dict(response, documentId=response["responseId"]) for response in self.responses
        ]

    def banks(self, attempt):
        return [{"bankId": "bank_easy_2", "difficultyLevel": "Easy", "isActive": True}]

    def active_registry(self):
        return None

    def record_retry(self, attempt, code):
        self.jobs[attempt["attemptId"]].update({"retryState": "retry_pending", "errorCode": code})

    def finalize(self, attempt, *, state, code, raw_run, snapshots, assignment, mastery):
        job = self.jobs[attempt["attemptId"]]
        if job["status"] in ai_runtime.TERMINAL_STATES:
            return job["status"]
        job.update({"status": state, "errorCode": code})
        self.statuses[attempt["attemptId"]] = {"analysisState": state, "displayCode": f"analysis_{state}"}
        self.finalized.append({"state": state, "raw": raw_run, "snapshots": snapshots, "assignment": assignment, "mastery": mastery})
        return state


def trusted_attempt() -> dict:
    return {
        "attemptId": "attempt-1", "sessionId": "session-1", "studentId": "student-1",
        "topicId": "topic-1", "subtopicId": "subtopic-1", "yearLevel": 4,
        "bankId": "bank-easy", "difficultyLevel": "Easy", "contentVersion": "v1",
        "assignmentId": "cold_start_easy", "assignmentSource": "cold_start_easy",
        "adaptivePolicyVersion": "adaptive-policy-v1", "correctCount": 3, "totalQuestions": 5,
        "score": 60, "responseIds": [f"response-{index}" for index in range(5)],
        "validationStatus": "finalized", "finalizationStatus": "finalized",
        "dataSource": "runtime_callable", "sourceAttemptSequence": 1, "finalizedAt": NOW,
    }


def trusted_responses() -> list[dict]:
    rows = []
    for index in range(5):
        rows.append({
            "responseId": f"response-{index}", "sessionId": "session-1", "attemptId": "attempt-1",
            "studentId": "student-1", "questionId": f"question-{index}", "skillId": "skill-1",
            "sequenceIndex": index, "serverIsCorrect": index < 3, "validationStatus": "validated",
            "createdAt": NOW, "responseTimeMs": 500, "responseTimeQuality": "client_reported_unverified",
            "hintCount": 0, "hintTelemetryStatus": "not_supported", "questionVersion": "v1", "contentVersion": "v1",
        })
    return rows


class AiRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = MemoryGateway(trusted_attempt(), trusted_responses())
        self.bundle = RuntimeBundle.from_runtime_root(ROOT / "ai_pipeline")

    def test_valid_missing_registry_writes_one_fallback_and_safe_status(self) -> None:
        self.assertEqual("fallback", process_finalized_attempt("attempt-1", gateway=self.gateway, bundle=self.bundle))
        self.assertEqual("fallback", self.gateway.statuses["attempt-1"]["analysisState"])
        self.assertEqual(1, len(self.gateway.finalized))
        self.assertNotIn("featureValues", self.gateway.statuses["attempt-1"])
        self.assertEqual("fallback", process_finalized_attempt("attempt-1", gateway=self.gateway, bundle=self.bundle))
        self.assertEqual(1, len(self.gateway.finalized))

    def test_invalid_source_fails_without_inference(self) -> None:
        self.gateway.attempt_doc["dataSource"] = "seed_demo"
        self.assertEqual("failed", process_finalized_attempt("attempt-1", gateway=self.gateway, bundle=self.bundle))
        self.assertEqual("trusted_source_invalid", self.gateway.finalized[0]["raw"]["statusCode"])

    def test_compatible_supervised_result_completes_without_exposing_raw_fields_in_status(self) -> None:
        completed_run = {
            "status": "completed", "statusCode": "model_completed", "featureValues": {"correct_rate": 0.6},
            "shapValues": {"correct_rate": -0.1}, "supportRisk": 0.4,
        }
        with patch.object(ai_runtime, "_supervised_or_fallback", return_value=(0.4, completed_run)):
            self.assertEqual("completed", process_finalized_attempt("attempt-1", gateway=self.gateway, bundle=self.bundle))
        self.assertEqual("completed", self.gateway.statuses["attempt-1"]["analysisState"])
        self.assertNotIn("shapValues", self.gateway.statuses["attempt-1"])
        self.assertNotIn("featureValues", self.gateway.statuses["attempt-1"])

    def test_registry_requires_complete_approval_metadata(self) -> None:
        registry = {"isActive": True, "lifecycleStatus": "promoted"}
        self.assertEqual("approval_missing", ai_runtime._registry_mismatch(registry, self.bundle))

    def test_verified_gcs_artifact_runs_xgboost_and_shap(self) -> None:
        import joblib
        import numpy as np
        from xgboost import XGBClassifier
        from firebase_admin import storage

        with TemporaryDirectory() as temporary:
            model_path = Path(temporary) / "model.joblib"
            model = XGBClassifier(n_estimators=2, max_depth=1, learning_rate=0.5, n_jobs=1, random_state=7)
            model.fit(np.asarray([[0.1, 100.0], [0.9, 200.0], [0.2, 700.0], [0.8, 300.0]]), np.asarray([1, 0, 1, 0]))
            joblib.dump(model, model_path)
            artifact = model_path.read_bytes()
            artifact_sha = sha256(artifact).hexdigest()
            registry = {"isActive": True, "lifecycleStatus": "promoted", "modelType": "xgboost", "evaluationStatus": "evaluated", "promotionGateStatus": "passed",
                "approvalId": "approval-1", "approvedBy": "supervisor", "approvedAt": NOW, "approvalRationale": "accepted", "evaluationReportSha256": "report",
                "artifactPath": "gs://logic-oasis-models/approved/model.joblib", "artifactSha256": artifact_sha, "modelVersion": "xgb-v1",
                "featureSchemaVersion": "quiz-attempt-features-v2", "featureSchemaSha256": self.bundle.feature_schema_sha256,
                "packageSha256": self.bundle.package_sha256, "weakTopicRankingPolicySha256": self.bundle.ranking_policy_sha256,
                "adaptivePolicySha256": self.bundle.adaptive_policy_sha256, "predictionTarget": "next_attempt_support_needed", "labelVersion": "next-attempt-support-needed-v1"}
            manifest = {**{key: registry[key] for key in ("artifactSha256", "modelVersion", "featureSchemaVersion", "featureSchemaSha256", "packageSha256", "weakTopicRankingPolicySha256", "adaptivePolicySha256", "predictionTarget", "labelVersion")}}
            manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
            registry["artifactManifestSha256"] = sha256(manifest_bytes).hexdigest()
            objects = {"approved/model.joblib": artifact, "approved/model.joblib.manifest.json": manifest_bytes}
            class Blob:
                def __init__(self, name): self.name = name
                def download_as_bytes(self): return objects[self.name]
            class Bucket:
                def blob(self, name): return Blob(name)
            with patch.object(storage, "bucket", return_value=Bucket()):
                risk, run = ai_runtime._supervised_or_fallback(self.gateway.attempt_doc,
                    ai_runtime.load_firestore_dataset(*self.gateway.history(self.gateway.attempt_doc), provenance="emulator_verified", allow_emulator_records=True), registry, self.bundle)
        self.assertIsNotNone(risk)
        self.assertEqual("completed", run["status"])
        self.assertIn("shapValues", run)

    def test_transient_error_rethrows_twice_then_terminalizes(self) -> None:
        with patch.object(ai_runtime, "build_bkt_materialization", side_effect=RuntimeFailure("temporary", retryable=True)):
            with self.assertRaises(RuntimeFailure):
                process_finalized_attempt("attempt-1", gateway=self.gateway, bundle=self.bundle)
            self.assertEqual("retry_pending", self.gateway.jobs["attempt-1"]["retryState"])
            with self.assertRaises(RuntimeFailure):
                process_finalized_attempt("attempt-1", gateway=self.gateway, bundle=self.bundle)
            self.assertEqual("failed", process_finalized_attempt("attempt-1", gateway=self.gateway, bundle=self.bundle))
        self.assertEqual(3, self.gateway.jobs["attempt-1"]["attemptCount"])

    def test_firestore_finalization_reads_all_projections_before_its_first_write(self) -> None:
        class Snapshot:
            exists = False
            id = "unused"
            reference = ""

            def to_dict(self):
                return {}

        class Transaction:
            wrote = False
            writes = 0

            def set(self, *_args, **_kwargs):
                self.wrote = True
                self.writes += 1

        class Ref:
            def __init__(self, transaction):
                self.transaction = transaction

            def get(self, transaction):
                if transaction.wrote:
                    raise AssertionError("Firestore read occurred after a transaction write")
                return Snapshot()

        class Collection:
            def __init__(self, transaction):
                self.transaction = transaction

            def document(self, _document_id):
                return Ref(self.transaction)

        class Database:
            def __init__(self):
                self.current_transaction = Transaction()

            def transaction(self):
                return self.current_transaction

            def collection(self, _collection_id):
                return Collection(self.current_transaction)

        database = Database()
        gateway = FirestoreRuntimeGateway(database)
        snapshot = {"studentId": "student-1", "subtopicId": "subtopic-1", "skillId": "skill-1"}
        assignment = {"studentId": "student-1", "subtopicId": "subtopic-1"}
        mastery = {"studentId": "student-1", "yearLevel": 4, "topicId": "topic-1", "subtopicId": "subtopic-1"}
        with patch("firebase_admin.firestore.transactional", lambda function: lambda transaction: function(transaction)):
            self.assertEqual("fallback", gateway.finalize(trusted_attempt(), state="fallback", code="approval_missing",
                raw_run={"status": "fallback"}, snapshots=[snapshot], assignment=assignment, mastery=mastery))
        self.assertGreater(database.current_transaction.writes, 0)


if __name__ == "__main__":
    unittest.main()
