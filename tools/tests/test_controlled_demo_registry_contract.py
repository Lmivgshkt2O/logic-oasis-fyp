from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai_pipeline"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "functions"))

from deploy_controlled_demo_model import (
    SupervisorApproval,
    controlled_demo_object_paths,
    deploy_controlled_demo_model,
    validate_model_bucket,
)
import ai_runtime
from logic_oasis_ai.model_registry import ModelArtifact
from promote_controlled_demo_model import promote_controlled_demo_model
from training.publish_controlled_demo_bundle import publish_controlled_demo_bundle
from training.train_controlled_demo_xgboost import train_controlled_demo_xgboost


NOW = datetime(2026, 7, 24, tzinfo=timezone.utc)


def controlled_registry_document(artifact_id: str = "xgboost-controlled-demo-xgboost-v1") -> dict[str, object]:
    return {
        "artifactId": artifact_id,
        "modelType": "xgboost",
        "modelVersion": "controlled-demo-xgboost-v1",
        "artifactPath": "gs://logic-oasis-models/controlled-demo/controlled-demo-xgboost-v1/model.ubj",
        "artifactManifestPath": "gs://logic-oasis-models/controlled-demo/controlled-demo-xgboost-v1/manifest.json",
        "artifactSha256": "a" * 64,
        "artifactManifestSha256": "b" * 64,
        "featureSchemaVersion": "quiz-attempt-features-v2",
        "featureSchemaSha256": "c" * 64,
        "packageSha256": "d" * 64,
        "weakTopicRankingPolicySha256": "e" * 64,
        "adaptivePolicySha256": "f" * 64,
        "trainingDatasetVersion": "controlled-demo-dataset-v1",
        "trainingDatasetSha256": "1" * 64,
        "predictionTarget": "next_attempt_support_needed",
        "labelVersion": "next-attempt-support-needed-v1",
        "masteryCriterion": 0.60,
        "evaluationStatus": "evaluated",
        "evaluationReportSha256": "2" * 64,
        "promotionGateStatus": "passed",
        "lifecycleStatus": "promoted",
        "isActive": True,
        "approvalId": "approval-cdm-v1",
        "approvedBy": "supervisor@example.edu",
        "approvedAt": NOW,
        "approvalRationale": "Approved for FYP1 demonstration only; not real-world validated.",
        "trainingDataProvenance": "expert_authored_controlled_demo",
        "evidenceLevel": "controlled_demonstration",
        "approvalScope": "fyp1_controlled_demo",
        "deploymentScope": "controlled_demo",
        "scenarioCatalogueSha256": "3" * 64,
        "controlledDemoConfigSha256": "4" * 64,
        "promotedAt": NOW,
    }


class Snapshot:
    def __init__(self, reference, data):
        self.reference = reference
        self.id = reference.id
        self.exists = data is not None
        self._data = data

    def to_dict(self):
        return dict(self._data or {})


class DocumentReference:
    def __init__(self, collection, document_id):
        self.collection = collection
        self.id = document_id

    def get(self, transaction=None):
        return Snapshot(self, self.collection.documents.get(self.id))


class Query:
    def __init__(self, collection, field, value):
        self.collection = collection
        self.field = field
        self.value = value

    def get(self, transaction=None):
        return [
            Snapshot(DocumentReference(self.collection, document_id), document)
            for document_id, document in self.collection.documents.items()
            if document.get(self.field) == self.value
        ]

    def limit(self, count):
        if count != 2:
            raise AssertionError(count)
        return self


class Collection:
    def __init__(self, documents):
        self.documents = documents

    def document(self, document_id):
        return DocumentReference(self, document_id)

    def where(self, field, _operator, value):
        return Query(self, field, value)


class Transaction:
    def update(self, reference, values):
        reference.collection.documents[reference.id].update(values)

    def create(self, reference, values):
        if reference.id in reference.collection.documents:
            raise ValueError("document already exists")
        reference.collection.documents[reference.id] = dict(values)


class Database:
    def __init__(self, registry_documents=None):
        self.registry = dict(registry_documents or {})

    def collection(self, name):
        if name != "modelRegistry":
            raise AssertionError(name)
        return Collection(self.registry)

    def transaction(self):
        return Transaction()


class Blob:
    def __init__(self, objects, name, *, corrupt_download=False):
        self.objects = objects
        self.name = name
        self.corrupt_download = corrupt_download

    def upload_from_string(self, content, if_generation_match):
        if if_generation_match != 0 or self.name in self.objects:
            raise ValueError("object is not immutable")
        self.objects[self.name] = bytes(content)

    def download_as_bytes(self):
        content = self.objects[self.name]
        return content + b"corrupt" if self.corrupt_download else content


class Bucket:
    name = "logic-oasis-models"

    def __init__(self, *, corrupt_download=False):
        self.objects = {}
        self.corrupt_download = corrupt_download

    def blob(self, name):
        return Blob(self.objects, name, corrupt_download=self.corrupt_download)


class ControlledDemoRegistryContractTests(unittest.TestCase):
    def test_model_artifact_serializes_complete_controlled_approval_metadata(self):
        artifact = ModelArtifact(
            artifact_id="xgboost-controlled-demo-v1", model_type="xgboost",
            model_version="controlled-demo-xgboost-v1",
            feature_schema_version="quiz-attempt-features-v2",
            training_dataset_version="controlled-demo-dataset-v1", artifact_sha256="a" * 64,
            evaluation_status="evaluated", evaluation_report_sha256="b" * 64,
            artifact_manifest_sha256="c" * 64, promotion_gate_status="passed",
            approval_id="approval-cdm-v1", approved_by="supervisor@example.edu", approved_at=NOW,
            approval_rationale="Approved only for demonstration; not real-world validated.",
            training_data_provenance="expert_authored_controlled_demo",
            evidence_level="controlled_demonstration", approval_scope="fyp1_controlled_demo",
            deployment_scope="controlled_demo", scenario_catalogue_sha256="d" * 64,
            controlled_demo_config_sha256="e" * 64,
        )

        document = artifact.to_registry_document()
        self.assertEqual(document["deploymentScope"], "controlled_demo")
        self.assertEqual(document["scenarioCatalogueSha256"], "d" * 64)

    def test_privileged_transaction_deactivates_previous_record_and_creates_one_active(self):
        database = Database({"previous": {"artifactId": "previous", "isActive": True}})
        document = controlled_registry_document()

        with patch("firebase_admin.firestore.transactional", lambda function: lambda transaction: function(transaction)):
            result = promote_controlled_demo_model(database, document, now=NOW)

        self.assertEqual(result["artifactId"], document["artifactId"])
        self.assertFalse(database.registry["previous"]["isActive"])
        active = [item for item in database.registry.values() if item.get("isActive") is True]
        self.assertEqual(active, [document])

    def test_transaction_rejects_corrupt_multiple_active_state_before_writing(self):
        database = Database({
            "one": {"artifactId": "one", "isActive": True},
            "two": {"artifactId": "two", "isActive": True},
        })

        with patch("firebase_admin.firestore.transactional", lambda function: lambda transaction: function(transaction)):
            with self.assertRaisesRegex(ValueError, "multiple active"):
                promote_controlled_demo_model(database, controlled_registry_document(), now=NOW)

        self.assertEqual(set(database.registry), {"one", "two"})
        self.assertTrue(all(item["isActive"] for item in database.registry.values()))

    def test_transaction_rejects_duplicate_immutable_artifact_id(self):
        document = controlled_registry_document()
        database = Database({str(document["artifactId"]): dict(document, isActive=False)})

        with patch("firebase_admin.firestore.transactional", lambda function: lambda transaction: function(transaction)):
            with self.assertRaisesRegex(ValueError, "immutable"):
                promote_controlled_demo_model(database, document, now=NOW)

    def test_incomplete_scope_hash_or_rationale_cannot_be_promoted(self):
        mutations = (
            ("approvalScope", "another_scope"),
            ("scenarioCatalogueSha256", ""),
            ("controlledDemoConfigSha256", "not-a-hash"),
            ("approvalRationale", "Approved for a demo."),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                document = controlled_registry_document()
                document[field] = value
                with self.assertRaises(ValueError):
                    promote_controlled_demo_model(Database(), document, now=NOW)

    def test_promotion_rejects_approval_later_than_the_trusted_promotion_time(self):
        document = controlled_registry_document()
        document["approvedAt"] = NOW + timedelta(seconds=1)

        with self.assertRaisesRegex(ValueError, "later than promotion"):
            promote_controlled_demo_model(Database(), document, now=NOW)

        document["approvedAt"] = NOW
        with patch("firebase_admin.firestore.transactional", lambda function: lambda transaction: function(transaction)):
            promoted = promote_controlled_demo_model(Database(), document, now=NOW)
        self.assertEqual(promoted["approvedAt"], promoted["promotedAt"])

    def test_bucket_and_controlled_demo_object_paths_are_exact(self):
        self.assertEqual(validate_model_bucket("gs://logic-oasis-models"), "logic-oasis-models")
        self.assertEqual(
            controlled_demo_object_paths("gs://logic-oasis-models", "controlled-demo-xgboost-v1"),
            (
                "gs://logic-oasis-models/controlled-demo/controlled-demo-xgboost-v1/model.ubj",
                "gs://logic-oasis-models/controlled-demo/controlled-demo-xgboost-v1/manifest.json",
            ),
        )
        for invalid in (
            "logic-oasis-models",
            "gs://logic-oasis-models/subdirectory",
            "gs://logic-oasis-models/../other",
            "https://storage.googleapis.com/logic-oasis-models",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_model_bucket(invalid)

    def test_deploy_verifies_both_uploaded_objects_before_registry_promotion(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as output:
            published = publish_controlled_demo_bundle(train_controlled_demo_xgboost(), output)
            database = Database()
            bucket = Bucket()
            approval = SupervisorApproval(
                "approval-cdm-v1", "supervisor@example.edu", NOW,
                "Approved for FYP1 demonstration only; not real-world validated.",
            )
            with patch("firebase_admin.firestore.transactional", lambda function: lambda transaction: function(transaction)):
                result = deploy_controlled_demo_model(
                    database=database, bucket=bucket, model_bucket="gs://logic-oasis-models",
                    artifact_path=published.artifact_path, manifest_path=published.manifest_path,
                    approval=approval, promoted_at=NOW,
                )

        self.assertEqual(result["deploymentScope"], "controlled_demo")
        self.assertEqual(set(bucket.objects), {
            "controlled-demo/controlled-demo-xgboost-v1/model.ubj",
            "controlled-demo/controlled-demo-xgboost-v1/manifest.json",
        })
        uploaded_manifest = json.loads(
            bucket.objects["controlled-demo/controlled-demo-xgboost-v1/manifest.json"]
        )
        for binding in (
            "packageSha256", "weakTopicRankingPolicySha256",
            "adaptivePolicySha256", "predictionTarget",
        ):
            self.assertEqual(uploaded_manifest[binding], result[binding])
        self.assertEqual(
            sha256(bucket.objects["controlled-demo/controlled-demo-xgboost-v1/manifest.json"]).hexdigest(),
            result["artifactManifestSha256"],
        )
        runtime_bundle = ai_runtime.RuntimeBundle.from_runtime_root(
            ROOT / "ai_pipeline", evidence_mode="controlled_demo", model_bucket="logic-oasis-models"
        )
        with patch("firebase_admin.storage.bucket", return_value=bucket):
            with ai_runtime._approved_artifact_path(runtime_bundle, result) as downloaded:
                self.assertEqual(sha256(downloaded.read_bytes()).hexdigest(), result["artifactSha256"])
        self.assertEqual([item for item in database.registry.values() if item["isActive"]], [result])

    def test_deploy_accepts_byte_identical_immutable_objects_on_retry(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as output:
            published = publish_controlled_demo_bundle(train_controlled_demo_xgboost(), output)
            bucket = Bucket()
            approval = SupervisorApproval(
                "approval-cdm-v1", "supervisor@example.edu", NOW,
                "Approved for FYP1 demonstration only; not real-world validated.",
            )
            with patch("firebase_admin.firestore.transactional", lambda function: lambda transaction: function(transaction)):
                first = deploy_controlled_demo_model(
                    database=Database(), bucket=bucket, model_bucket="gs://logic-oasis-models",
                    artifact_path=published.artifact_path, manifest_path=published.manifest_path,
                    approval=approval, promoted_at=NOW,
                )
                second = deploy_controlled_demo_model(
                    database=Database(), bucket=bucket, model_bucket="gs://logic-oasis-models",
                    artifact_path=published.artifact_path, manifest_path=published.manifest_path,
                    approval=approval, promoted_at=NOW,
                )

        self.assertEqual(first["artifactSha256"], second["artifactSha256"])
        self.assertEqual(len(bucket.objects), 2)

    def test_failed_upload_verification_never_creates_an_active_registry_record(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as output:
            published = publish_controlled_demo_bundle(train_controlled_demo_xgboost(), output)
            database = Database()
            approval = SupervisorApproval(
                "approval-cdm-v1", "supervisor@example.edu", NOW,
                "Approved for FYP1 demonstration only; not real-world validated.",
            )
            with self.assertRaisesRegex(ValueError, "byte verification"):
                deploy_controlled_demo_model(
                    database=database, bucket=Bucket(corrupt_download=True),
                    model_bucket="gs://logic-oasis-models", artifact_path=published.artifact_path,
                    manifest_path=published.manifest_path, approval=approval, promoted_at=NOW,
                )

        self.assertEqual(database.registry, {})

    def test_firestore_rules_deny_client_registry_reads_and_writes(self):
        rules = (ROOT / "firestore.rules").read_text(encoding="utf-8")
        registry_rule = rules.split("match /modelRegistry/{modelId}", 1)[1].split("}", 1)[0]
        self.assertIn("allow read, write: if false;", registry_rule)


if __name__ == "__main__":
    unittest.main()
