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
        self.registry: dict | None = None

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
        return self.registry

    def record_retry(self, attempt, code):
        self.jobs[attempt["attemptId"]].update({"retryState": "retry_pending", "errorCode": code})

    def finalize(self, attempt, *, state, code, raw_run, snapshots, assignment, mastery):
        job = self.jobs[attempt["attemptId"]]
        if job["status"] in ai_runtime.TERMINAL_STATES:
            return job["status"]
        job.update({"status": state, "errorCode": code})
        status = {"analysisState": state, "displayCode": f"analysis_{state}"}
        if raw_run.get("modelEvidenceState") == "controlled_demonstration":
            status["modelEvidenceState"] = "controlled_demonstration"
        self.statuses[attempt["attemptId"]] = status
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
        self.bundle = RuntimeBundle.from_runtime_root(
            ROOT / "ai_pipeline",
            evidence_mode="real_evaluated_only",
            model_bucket="logic-oasis-models",
        )

    def controlled_registry(self) -> dict[str, object]:
        return {
            "isActive": True, "lifecycleStatus": "promoted", "modelType": "xgboost",
            "evaluationStatus": "evaluated", "promotionGateStatus": "passed",
            "releaseId": "CDM-2026-001", "releasedBy": "zyonn", "releasedAt": NOW,
            "promotedAt": NOW,
            "releaseRationale": "Developer-released FYP1 controlled demonstration; not real-world validated.",
            "evaluationReportSha256": "1" * 64, "artifactManifestSha256": "2" * 64,
            "artifactPath": "gs://logic-oasis-models/controlled-demo/controlled-demo-xgboost-v1/model.ubj",
            "artifactManifestPath": "gs://logic-oasis-models/controlled-demo/controlled-demo-xgboost-v1/manifest.json",
            "artifactSha256": "3" * 64, "modelVersion": "controlled-demo-xgboost-v1",
            "featureSchemaVersion": "quiz-attempt-features-v2",
            "featureSchemaSha256": self.bundle.feature_schema_sha256,
            "packageSha256": self.bundle.package_sha256,
            "weakTopicRankingPolicySha256": self.bundle.ranking_policy_sha256,
            "adaptivePolicySha256": self.bundle.adaptive_policy_sha256,
            "predictionTarget": "next_attempt_support_needed",
            "labelVersion": "next-attempt-support-needed-v1",
            "trainingDataProvenance": "expert_authored_controlled_demo",
            "evidenceLevel": "controlled_demonstration",
            "releaseScope": "fyp1_controlled_demo",
            "deploymentScope": "controlled_demo",
            "trainingDatasetVersion": "controlled-demo-dataset-v1",
            "trainingDatasetSha256": "6" * 64,
            "scenarioCatalogueSha256": "4" * 64,
            "controlledDemoConfigSha256": "5" * 64,
        }

    @staticmethod
    def controlled_manifest(registry: dict[str, object]) -> bytes:
        document = {
            "bundleSchemaVersion": "controlled-demo-xgboost-bundle-v1",
            "modelType": "xgboost",
            "modelVersion": registry["modelVersion"],
            "artifactFile": "model.ubj",
            "artifactSha256": registry["artifactSha256"],
            "targetName": registry["predictionTarget"],
            "labelVersion": registry["labelVersion"],
            "featureSchemaVersion": registry["featureSchemaVersion"],
            "featureNames": ["correct_rate", "mean_response_time_ms"],
            "trainingDatasetVersion": registry["trainingDatasetVersion"],
            "trainingDatasetSha256": registry["trainingDatasetSha256"],
            "trainingDataProvenance": registry["trainingDataProvenance"],
            "scenarioCatalogueSha256": registry["scenarioCatalogueSha256"],
            "featureSchemaSha256": registry["featureSchemaSha256"],
            "controlledDemoConfigSha256": registry["controlledDemoConfigSha256"],
            "evaluationReportSha256": registry["evaluationReportSha256"],
            "evaluationStatus": registry["evaluationStatus"],
            "evidenceLevel": registry["evidenceLevel"],
            "claimLevel": "controlled_demonstration_only",
            "deploymentScope": registry["deploymentScope"],
            "packageSha256": registry["packageSha256"],
            "weakTopicRankingPolicySha256": registry["weakTopicRankingPolicySha256"],
            "adaptivePolicySha256": registry["adaptivePolicySha256"],
            "predictionTarget": registry["predictionTarget"],
        }
        return json.dumps(document, sort_keys=True).encode()

    def test_valid_missing_registry_writes_one_fallback_and_safe_status(self) -> None:
        self.assertEqual("fallback", process_finalized_attempt("attempt-1", gateway=self.gateway, bundle=self.bundle))
        self.assertEqual("fallback", self.gateway.statuses["attempt-1"]["analysisState"])
        self.assertEqual(1, len(self.gateway.finalized))
        self.assertNotIn("featureValues", self.gateway.statuses["attempt-1"])
        mastery = self.gateway.finalized[0]["mastery"]
        self.assertEqual(0.6, mastery["lastCorrectRate"])
        projected = ai_runtime._merged_subtopic_mastery(None, mastery)
        self.assertEqual(0.6, projected["bestCorrectRate"])
        self.assertTrue(projected["completed"])
        self.assertEqual("Moderate", projected["masteryLevel"])
        assignment = self.gateway.finalized[0]["assignment"]
        self.assertEqual("runtime_callable", assignment["dataSource"])
        self.assertEqual(1, assignment["sourceAttemptSequence"])
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

    def test_registry_requires_complete_release_metadata(self) -> None:
        registry = {"isActive": True, "lifecycleStatus": "promoted"}
        self.assertEqual("release_missing", ai_runtime._registry_mismatch(registry, self.bundle))

    def test_controlled_demo_registry_activates_only_in_controlled_demo_mode(self) -> None:
        registry = self.controlled_registry()
        controlled_bundle = RuntimeBundle.from_runtime_root(
            ROOT / "ai_pipeline",
            evidence_mode="controlled_demo",
            model_bucket="logic-oasis-models",
        )

        self.assertIsNone(ai_runtime._registry_mismatch(registry, controlled_bundle))
        self.assertEqual(
            "model_evidence_incompatible",
            ai_runtime._registry_mismatch(registry, self.bundle),
        )
        unknown_mode = RuntimeBundle.from_runtime_root(
            ROOT / "ai_pipeline", evidence_mode="unknown", model_bucket="logic-oasis-models"
        )
        self.assertEqual(
            "model_evidence_incompatible",
            ai_runtime._registry_mismatch(registry, unknown_mode),
        )

    def test_disabled_controlled_demo_falls_back_without_artifact_access(self) -> None:
        self.gateway.registry = self.controlled_registry()
        with patch.object(
            ai_runtime,
            "_released_artifact_path",
            side_effect=AssertionError("disabled controlled-demo must not access its artifact"),
        ):
            self.assertEqual(
                "fallback",
                process_finalized_attempt("attempt-1", gateway=self.gateway, bundle=self.bundle),
            )
        finalized = self.gateway.finalized[0]
        self.assertEqual("fallback", finalized["raw"]["status"])
        self.assertEqual("model_evidence_incompatible", finalized["raw"]["statusCode"])
        self.assertNotIn("modelEvidenceState", finalized["raw"])
        self.assertNotIn("modelEvidenceState", finalized["assignment"])
        self.assertNotIn("modelEvidenceState", self.gateway.statuses["attempt-1"])
        self.assertEqual("runtime_callable", finalized["assignment"]["dataSource"])

    def test_controlled_demo_registry_rejects_wrong_scope_hash_bucket_or_inactive_record(self) -> None:
        controlled_bundle = RuntimeBundle.from_runtime_root(
            ROOT / "ai_pipeline", evidence_mode="controlled_demo", model_bucket="logic-oasis-models"
        )
        cases = (
            ("releaseScope", "real_evaluated", "model_evidence_incompatible"),
            ("scenarioCatalogueSha256", "", "model_evidence_incompatible"),
            ("controlledDemoConfigSha256", "wrong", "model_evidence_incompatible"),
            ("trainingDatasetSha256", "wrong", "model_evidence_incompatible"),
            ("trainingDatasetVersion", "", "model_evidence_incompatible"),
            ("releaseRationale", "Developer-released for a demo.", "model_evidence_incompatible"),
            ("artifactPath", "gs://another-bucket/controlled-demo/controlled-demo-xgboost-v1/model.ubj", "artifact_unavailable"),
            ("packageSha256", "wrong", "bundle_mismatch"),
            ("featureSchemaSha256", "wrong", "bundle_mismatch"),
            ("adaptivePolicySha256", "wrong", "bundle_mismatch"),
            ("predictionTarget", "legacy_target", "model_target_incompatible"),
            ("isActive", False, "model_registry_inactive"),
        )
        for field, value, expected in cases:
            with self.subTest(field=field):
                registry = self.controlled_registry()
                registry[field] = value
                self.assertEqual(expected, ai_runtime._registry_mismatch(registry, controlled_bundle))

    def test_controlled_demo_registry_rejects_incomplete_training_bindings(self) -> None:
        controlled_bundle = RuntimeBundle.from_runtime_root(
            ROOT / "ai_pipeline", evidence_mode="controlled_demo", model_bucket="logic-oasis-models"
        )
        for field in ("trainingDatasetVersion", "trainingDatasetSha256"):
            with self.subTest(field=field):
                registry = self.controlled_registry()
                registry.pop(field)
                self.assertEqual(
                    "model_evidence_incompatible",
                    ai_runtime._registry_mismatch(registry, controlled_bundle),
                )

    def test_real_evaluated_registry_requires_the_configured_bucket(self) -> None:
        registry = self.controlled_registry()
        registry.update({
            "trainingDataProvenance": "approved_pseudonymized_real",
            "evidenceLevel": "real_evaluated",
            "releaseScope": "real_evaluated",
            "deploymentScope": "real_evaluated",
            "artifactPath": "gs://logic-oasis-models/approved/model.joblib",
        })
        self.assertIsNone(ai_runtime._registry_mismatch(registry, self.bundle))
        for model_bucket in ("", "another-model-bucket"):
            with self.subTest(model_bucket=model_bucket):
                bundle = RuntimeBundle.from_runtime_root(
                    ROOT / "ai_pipeline",
                    evidence_mode="real_evaluated_only",
                    model_bucket=model_bucket,
                )
                self.assertEqual("artifact_unavailable", ai_runtime._registry_mismatch(registry, bundle))

        legacy_registry = dict(registry)
        for field in ("trainingDataProvenance", "evidenceLevel", "releaseScope", "deploymentScope"):
            legacy_registry.pop(field)
        self.assertIsNone(ai_runtime._registry_mismatch(legacy_registry, self.bundle))

    def test_controlled_demo_downloads_explicit_sibling_manifest(self) -> None:
        from firebase_admin import storage

        controlled_bundle = RuntimeBundle.from_runtime_root(
            ROOT / "ai_pipeline", evidence_mode="controlled_demo", model_bucket="logic-oasis-models"
        )
        registry = self.controlled_registry()
        artifact = b"native-ubj-placeholder"
        registry["artifactSha256"] = sha256(artifact).hexdigest()
        manifest = self.controlled_manifest(registry)
        registry["artifactManifestSha256"] = sha256(manifest).hexdigest()
        objects = {
            "controlled-demo/controlled-demo-xgboost-v1/model.ubj": artifact,
            "controlled-demo/controlled-demo-xgboost-v1/manifest.json": manifest,
        }

        class Blob:
            def __init__(self, name):
                self.name = name

            def download_as_bytes(self):
                return objects[self.name]

        class Bucket:
            def blob(self, name):
                return Blob(name)

        with patch.object(storage, "bucket", return_value=Bucket()):
            with ai_runtime._released_artifact_path(controlled_bundle, registry) as model_path:
                self.assertEqual(model_path.read_bytes(), artifact)
                self.assertEqual(model_path.suffix, ".ubj")

    def test_controlled_demo_non_mapping_manifest_falls_back_as_runtime_failure(self) -> None:
        from firebase_admin import storage

        controlled_bundle = RuntimeBundle.from_runtime_root(
            ROOT / "ai_pipeline", evidence_mode="controlled_demo", model_bucket="logic-oasis-models"
        )
        registry = self.controlled_registry()
        artifact = b"native-ubj-placeholder"
        manifest = b"[]"
        registry["artifactSha256"] = sha256(artifact).hexdigest()
        registry["artifactManifestSha256"] = sha256(manifest).hexdigest()
        objects = {
            "controlled-demo/controlled-demo-xgboost-v1/model.ubj": artifact,
            "controlled-demo/controlled-demo-xgboost-v1/manifest.json": manifest,
        }

        class Blob:
            def __init__(self, name): self.name = name
            def download_as_bytes(self): return objects[self.name]

        class Bucket:
            def blob(self, name): return Blob(name)

        with patch.object(storage, "bucket", return_value=Bucket()), self.assertRaises(RuntimeFailure) as raised:
            with ai_runtime._released_artifact_path(controlled_bundle, registry):
                pass
        self.assertEqual("artifact_hash_mismatch", raised.exception.code)

    def test_cdm2_ubj_runs_native_prediction_shap_and_safe_lineage(self) -> None:
        from firebase_admin import storage
        from training.publish_controlled_demo_bundle import publish_controlled_demo_bundle
        from training.train_controlled_demo_xgboost import train_controlled_demo_xgboost

        controlled_bundle = RuntimeBundle.from_runtime_root(
            ROOT / "ai_pipeline", evidence_mode="controlled_demo", model_bucket="logic-oasis-models"
        )
        with TemporaryDirectory() as temporary:
            published = publish_controlled_demo_bundle(train_controlled_demo_xgboost(), temporary)
            artifact = published.artifact_path.read_bytes()
            registry = self.controlled_registry()
            registry.update({
                "artifactSha256": published.manifest["artifactSha256"],
                "artifactManifestSha256": published.manifest_sha256,
                "modelVersion": published.manifest["modelVersion"],
                "featureSchemaVersion": published.manifest["featureSchemaVersion"],
                "featureSchemaSha256": published.manifest["featureSchemaSha256"],
                "trainingDatasetVersion": published.manifest["trainingDatasetVersion"],
                "trainingDatasetSha256": published.manifest["trainingDatasetSha256"],
                "evaluationReportSha256": published.manifest["evaluationReportSha256"],
                "scenarioCatalogueSha256": published.manifest["scenarioCatalogueSha256"],
                "controlledDemoConfigSha256": published.manifest["controlledDemoConfigSha256"],
            })
            deployment_manifest = {
                **published.manifest,
                "packageSha256": registry["packageSha256"],
                "weakTopicRankingPolicySha256": registry["weakTopicRankingPolicySha256"],
                "adaptivePolicySha256": registry["adaptivePolicySha256"],
                "predictionTarget": registry["predictionTarget"],
            }
            manifest = (json.dumps(deployment_manifest, indent=2, sort_keys=True) + "\n").encode()
            registry["artifactManifestSha256"] = sha256(manifest).hexdigest()
            objects = {
                "controlled-demo/controlled-demo-xgboost-v1/model.ubj": artifact,
                "controlled-demo/controlled-demo-xgboost-v1/manifest.json": manifest,
            }

            class Blob:
                def __init__(self, name):
                    self.name = name

                def download_as_bytes(self):
                    return objects[self.name]

            class Bucket:
                def blob(self, name):
                    return Blob(name)

            self.gateway.registry = registry
            with patch.object(storage, "bucket", return_value=Bucket()):
                self.assertEqual(
                    "completed",
                    process_finalized_attempt("attempt-1", gateway=self.gateway, bundle=controlled_bundle),
                )
        finalized = self.gateway.finalized[0]
        self.assertEqual("completed", finalized["raw"]["status"])
        self.assertEqual("controlled_demonstration", finalized["raw"]["modelEvidenceState"])
        self.assertEqual("controlled_demonstration", finalized["assignment"]["modelEvidenceState"])
        self.assertEqual("controlled_demonstration", self.gateway.statuses["attempt-1"]["modelEvidenceState"])
        self.assertIn("shapValues", finalized["raw"])
        self.assertNotIn("shapValues", self.gateway.statuses["attempt-1"])
        self.assertNotIn("featureValues", self.gateway.statuses["attempt-1"])

    def test_invalid_controlled_ubj_falls_back_without_joblib_loading(self) -> None:
        from firebase_admin import storage

        controlled_bundle = RuntimeBundle.from_runtime_root(
            ROOT / "ai_pipeline", evidence_mode="controlled_demo", model_bucket="logic-oasis-models"
        )
        registry = self.controlled_registry()
        artifact = b"not-an-xgboost-ubj"
        registry["artifactSha256"] = sha256(artifact).hexdigest()
        manifest = self.controlled_manifest(registry)
        registry["artifactManifestSha256"] = sha256(manifest).hexdigest()
        objects = {
            "controlled-demo/controlled-demo-xgboost-v1/model.ubj": artifact,
            "controlled-demo/controlled-demo-xgboost-v1/manifest.json": manifest,
        }

        class Blob:
            def __init__(self, name):
                self.name = name

            def download_as_bytes(self):
                return objects[self.name]

        class Bucket:
            def blob(self, name):
                return Blob(name)

        with patch.object(storage, "bucket", return_value=Bucket()), patch(
            "joblib.load", side_effect=AssertionError("controlled UBJ must not use joblib")
        ):
            risk, run = ai_runtime._supervised_or_fallback(
                self.gateway.attempt_doc,
                ai_runtime.load_firestore_dataset(
                    *self.gateway.history(self.gateway.attempt_doc),
                    provenance="emulator_verified",
                    allow_emulator_records=True,
                ),
                registry,
                controlled_bundle,
            )
        self.assertIsNone(risk)
        self.assertEqual("fallback", run["status"])
        self.assertEqual("model_load_failed", run["statusCode"])

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
                "releaseId": "release-1", "releasedBy": "developer", "releasedAt": NOW, "releaseRationale": "accepted", "evaluationReportSha256": "report",
                "promotedAt": NOW,
                "artifactPath": "gs://logic-oasis-models/approved/model.joblib", "artifactSha256": artifact_sha, "modelVersion": "xgb-v1",
                "featureSchemaVersion": "quiz-attempt-features-v2", "featureSchemaSha256": self.bundle.feature_schema_sha256,
                "packageSha256": self.bundle.package_sha256, "weakTopicRankingPolicySha256": self.bundle.ranking_policy_sha256,
                "adaptivePolicySha256": self.bundle.adaptive_policy_sha256, "predictionTarget": "next_attempt_support_needed", "labelVersion": "next-attempt-support-needed-v1",
                "trainingDataProvenance": "approved_pseudonymized_real", "evidenceLevel": "real_evaluated",
                "releaseScope": "real_evaluated", "deploymentScope": "real_evaluated"}
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
            def __init__(self):
                self.wrote = False
                self.writes = 0
                self.documents = []

            def set(self, reference, document, **_kwargs):
                self.wrote = True
                self.writes += 1
                self.documents.append((reference, document))

        class Ref:
            def __init__(self, transaction, collection_id, document_id):
                self.transaction = transaction
                self.collection_id = collection_id
                self.document_id = document_id

            def get(self, transaction):
                if transaction.wrote:
                    raise AssertionError("Firestore read occurred after a transaction write")
                return Snapshot()

        class Collection:
            def __init__(self, transaction, collection_id):
                self.transaction = transaction
                self.collection_id = collection_id

            def document(self, document_id):
                return Ref(self.transaction, self.collection_id, document_id)

        class Database:
            def __init__(self):
                self.current_transaction = Transaction()

            def transaction(self):
                return self.current_transaction

            def collection(self, _collection_id):
                return Collection(self.current_transaction, _collection_id)

        database = Database()
        gateway = FirestoreRuntimeGateway(database)
        snapshot = {"studentId": "student-1", "subtopicId": "subtopic-1", "skillId": "skill-1"}
        assignment = {"studentId": "student-1", "subtopicId": "subtopic-1", "modelEvidenceState": "controlled_demonstration"}
        mastery = {"studentId": "student-1", "yearLevel": 4, "topicId": "topic-1", "subtopicId": "subtopic-1", "lastCorrectRate": 0.6}
        with patch("firebase_admin.firestore.transactional", lambda function: lambda transaction: function(transaction)):
            self.assertEqual("completed", gateway.finalize(trusted_attempt(), state="completed", code="model_completed",
                raw_run={"status": "completed", "modelEvidenceState": "controlled_demonstration",
                         "featureValues": {"correct_rate": 0.6}, "shapValues": {"correct_rate": -0.1}},
                snapshots=[snapshot], assignment=assignment, mastery=mastery))
        self.assertGreater(database.current_transaction.writes, 0)
        statuses = [
            document for _, document in database.current_transaction.documents
            if document.get("analysisState") == "completed"
        ]
        assignments = [
            document for reference, document in database.current_transaction.documents
            if reference.collection_id == "adaptiveAssignments"
        ]
        self.assertEqual("controlled_demonstration", assignments[0]["modelEvidenceState"])
        self.assertEqual(statuses[0]["modelEvidenceState"], "controlled_demonstration")
        self.assertNotIn("featureValues", statuses[0])
        self.assertNotIn("shapValues", statuses[0])

        database = Database()
        gateway = FirestoreRuntimeGateway(database)
        with patch("firebase_admin.firestore.transactional", lambda function: lambda transaction: function(transaction)):
            self.assertEqual("fallback", gateway.finalize(trusted_attempt(), state="fallback", code="model_load_failed",
                raw_run={"status": "fallback"}, snapshots=[snapshot],
                assignment={"studentId": "student-1", "subtopicId": "subtopic-1"}, mastery=mastery))
        assignments = [
            document for reference, document in database.current_transaction.documents
            if reference.collection_id == "adaptiveAssignments"
        ]
        from firebase_admin import firestore
        self.assertIs(assignments[0]["modelEvidenceState"], firestore.DELETE_FIELD)

    def test_firestore_gateway_derives_bank_exposure_from_trusted_student_history(self) -> None:
        class Snapshot:
            def __init__(self, document_id, data):
                self.id = document_id
                self._data = data
                self.exists = True

            def to_dict(self):
                return dict(self._data)

        class Query:
            def __init__(self, documents, conditions=()):
                self.documents = documents
                self.conditions = conditions

            def where(self, field, _operator, value):
                return Query(self.documents, (*self.conditions, (field, value)))

            def stream(self):
                return [
                    Snapshot(document_id, record)
                    for document_id, record in self.documents.items()
                    if all(record.get(field) == value for field, value in self.conditions)
                ]

        class Collection(Query):
            def __init__(self, documents):
                super().__init__(documents)

        class Database:
            def __init__(self, collections):
                self.collections = collections

            def collection(self, name):
                return Collection(self.collections[name])

        current = {**trusted_attempt(), "attemptId": "attempt-2", "bankId": "moderate-a", "sourceAttemptSequence": 2}
        earlier = {**trusted_attempt(), "attemptId": "attempt-1", "bankId": "moderate-a", "sourceAttemptSequence": 1}
        database = Database({
            "quizAttempts": {"attempt-1": earlier, "attempt-2": current},
            "questionBanks": {
                "moderate-a": {"bankId": "moderate-a", "topicId": "topic-1", "subtopicId": "subtopic-1", "yearLevel": 4},
                "moderate-b": {"bankId": "moderate-b", "topicId": "topic-1", "subtopicId": "subtopic-1", "yearLevel": 4},
            },
        })

        banks = FirestoreRuntimeGateway(database).banks(current)

        exposure = {bank["bankId"]: bank["exposureCount"] for bank in banks}
        self.assertEqual({"moderate-a": 2, "moderate-b": 0}, exposure)


if __name__ == "__main__":
    unittest.main()
