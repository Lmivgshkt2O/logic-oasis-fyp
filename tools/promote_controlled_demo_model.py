"""Privileged, immutable promotion for one controlled-demo model registry record."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any, Mapping

from firebase_admin import firestore

AI_ROOT = Path(__file__).resolve().parents[1] / "ai_pipeline"
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from logic_oasis_ai.model_registry import (
    CONTROLLED_DEMO_APPROVAL_SCOPE,
    CONTROLLED_DEMO_DEPLOYMENT_SCOPE,
    CONTROLLED_DEMO_EVIDENCE_LEVEL,
    CONTROLLED_DEMO_PROVENANCE,
    CONTROLLED_DEMO_RATIONALE_MARKER,
    SHA256_PATTERN,
    controlled_demo_object_paths,
)


CONTROLLED_VALUES = MappingProxyType({
    "modelType": "xgboost",
    "featureSchemaVersion": "quiz-attempt-features-v2",
    "predictionTarget": "next_attempt_support_needed",
    "labelVersion": "next-attempt-support-needed-v1",
    "masteryCriterion": 0.60,
    "evaluationStatus": "evaluated",
    "promotionGateStatus": "passed",
    "lifecycleStatus": "promoted",
    "trainingDataProvenance": CONTROLLED_DEMO_PROVENANCE,
    "evidenceLevel": CONTROLLED_DEMO_EVIDENCE_LEVEL,
    "approvalScope": CONTROLLED_DEMO_APPROVAL_SCOPE,
    "deploymentScope": CONTROLLED_DEMO_DEPLOYMENT_SCOPE,
    "trainingDatasetVersion": "controlled-demo-dataset-v1",
    "isActive": True,
})
REQUIRED_TEXT_FIELDS = frozenset({
    "artifactId", "modelVersion", "artifactPath", "artifactManifestPath",
    "trainingDatasetVersion", "approvalId", "approvedBy", "approvalRationale",
})
HASH_FIELDS = frozenset({
    "artifactSha256", "artifactManifestSha256", "featureSchemaSha256",
    "packageSha256", "weakTopicRankingPolicySha256", "adaptivePolicySha256",
    "trainingDatasetSha256", "evaluationReportSha256", "scenarioCatalogueSha256",
    "controlledDemoConfigSha256",
})
def validate_controlled_demo_registry_document(document: Mapping[str, object]) -> None:
    if any(document.get(field) != value for field, value in CONTROLLED_VALUES.items()):
        raise ValueError("registry document does not match the controlled-demo activation scope")
    if any(not isinstance(document.get(field), str) or not str(document[field]).strip() for field in REQUIRED_TEXT_FIELDS):
        raise ValueError("controlled-demo registry metadata is incomplete")
    if any(
        not isinstance(document.get(field), str) or not SHA256_PATTERN.fullmatch(document[field])
        for field in HASH_FIELDS
    ):
        raise ValueError("controlled-demo registry hash bindings must be lowercase SHA-256 values")
    if CONTROLLED_DEMO_RATIONALE_MARKER not in document["approvalRationale"].lower():
        raise ValueError("approval rationale must state that the model is not real-world validated")
    version = str(document["modelVersion"])
    artifact_path = str(document["artifactPath"])
    manifest_path = str(document["artifactManifestPath"])
    bucket = artifact_path.removeprefix("gs://").partition("/")[0]
    try:
        expected_artifact, expected_manifest = controlled_demo_object_paths(f"gs://{bucket}", version)
    except ValueError as error:
        raise ValueError("controlled-demo artifact paths and immutable ID are invalid") from error
    if (artifact_path, manifest_path, document["artifactId"]) != (
        expected_artifact, expected_manifest, f"xgboost-{version}"
    ):
        raise ValueError("controlled-demo artifact paths and immutable ID are invalid")
    for field in ("approvedAt", "promotedAt"):
        timestamp = document.get(field)
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
            raise ValueError(f"{field} must be a timezone-aware timestamp")


def promote_controlled_demo_model(
    database: Any,
    registry_document: Mapping[str, object],
    *,
    now: datetime | None = None,
) -> Mapping[str, object]:
    """Create one immutable record and switch active state in one transaction."""
    document = dict(registry_document)
    timestamp = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("promotion timestamp must include a timezone")
    document["promotedAt"] = timestamp
    validate_controlled_demo_registry_document(document)
    if document["approvedAt"] > timestamp:
        raise ValueError("approval timestamp cannot be later than promotion")
    collection = database.collection("modelRegistry")
    artifact_ref = collection.document(str(document["artifactId"]))

    @firestore.transactional
    def promote(transaction: Any) -> Mapping[str, object]:
        active = list(collection.where("isActive", "==", True).limit(2).get(transaction=transaction))
        existing = artifact_ref.get(transaction=transaction)
        if len(active) > 1:
            raise ValueError("model registry contains multiple active records")
        if existing.exists:
            raise ValueError("artifact ID is immutable and already registered")
        if active:
            transaction.update(active[0].reference, {"isActive": False})
        transaction.create(artifact_ref, document)
        return dict(document)

    return promote(database.transaction())
