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
    CONTROLLED_DEMO_RELEASE_SCOPE,
    CONTROLLED_DEMO_DEPLOYMENT_SCOPE,
    CONTROLLED_DEMO_EVIDENCE_LEVEL,
    CONTROLLED_DEMO_PROVENANCE,
    CONTROLLED_DEMO_RELEASE_RATIONALE_MARKER,
    SHA256_PATTERN,
    controlled_demo_object_paths,
)
from forum_function_inventory import (
    forum_inventory_digest,
    validate_forum_function_inventory,
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
    "releaseScope": CONTROLLED_DEMO_RELEASE_SCOPE,
    "deploymentScope": CONTROLLED_DEMO_DEPLOYMENT_SCOPE,
    "trainingDatasetVersion": "controlled-demo-dataset-v1",
    "isActive": True,
})
REQUIRED_TEXT_FIELDS = frozenset({
    "artifactId", "modelVersion", "artifactPath", "artifactManifestPath",
    "trainingDatasetVersion", "releaseId", "releasedBy", "releaseRationale",
})
HASH_FIELDS = frozenset({
    "artifactSha256", "artifactManifestSha256", "featureSchemaSha256",
    "packageSha256", "weakTopicRankingPolicySha256", "adaptivePolicySha256",
    "trainingDatasetSha256", "evaluationReportSha256", "scenarioCatalogueSha256",
    "controlledDemoConfigSha256",
})
FORUM_CONTROLLED_VALUES = MappingProxyType({
    "manifestSchemaVersion": "forum-model-release-manifest-v2",
    "lifecycleStatus": "released",
    "isActive": True,
    "trainingDataProvenance": "expert_authored_controlled_demo",
    "evidenceLevel": "controlled_demonstration",
    "releaseScope": "fyp1_forum_controlled_demo",
    "deploymentScope": "controlled_demo",
    "claimLevel": "controlled_demonstration_only",
    "candidateGateStatus": "passed",
    "failedGates": [],
})
FORUM_HASH_FIELDS = frozenset({
    "artifactSha256", "catalogueSha256", "datasetSha256",
    "datasetManifestSha256", "splitManifestSha256", "rubricSha256",
    "evaluationReportSha256", "candidateManifestSha256",
    "bundleManifestSha256", "codeRevision",
    "reasoningArtifactSha256", "relevanceArtifactSha256",
    "dependencyLockSha256",
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
    if CONTROLLED_DEMO_RELEASE_RATIONALE_MARKER not in document["releaseRationale"].lower():
        raise ValueError("release rationale must state that the model is not real-world validated")
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
    for field in ("releasedAt", "promotedAt"):
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
    if document["releasedAt"] > timestamp:
        raise ValueError("release timestamp cannot be later than promotion")
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


def validate_forum_controlled_demo_registry_document(
    document: Mapping[str, object],
) -> None:
    if any(document.get(field) != value for field, value in FORUM_CONTROLLED_VALUES.items()):
        raise ValueError("forum registry document does not match controlled-demo activation scope")
    if any(
        not isinstance(document.get(field), str) or not SHA256_PATTERN.fullmatch(document[field])
        for field in FORUM_HASH_FIELDS
    ):
        raise ValueError("forum registry hash bindings must be lowercase SHA-256 values")
    if any(
        not isinstance(document.get(field), str) or not str(document[field]).strip()
        for field in ("releaseId", "releasedBy", "releasedAt", "releaseRationale", "modelType", "modelVersion")
    ):
        raise ValueError("forum registry release metadata is incomplete")
    if not str(document["releasedAt"]).endswith("Z"):
        raise ValueError("forum release timestamp must be UTC")
    if "not evaluated on real learner forum responses" not in str(document["releaseRationale"]).casefold():
        raise ValueError("forum release rationale must state the learner-evidence limitation")
    for field in (
        "reasoningModelType", "relevanceModelType",
        "reasoningModelVersion", "relevanceModelVersion",
        "pythonVersion", "pythonImplementation",
        "dependencyLockFile",
    ):
        if not isinstance(document.get(field), str) or not str(document[field]).strip():
            raise ValueError(f"forum release v2 requires {field}")
    if not isinstance(document.get("compositePolicy"), Mapping) or not document["compositePolicy"]:
        raise ValueError("forum release v2 requires the frozen composite policy")
    if not str(document.get("pythonVersion", "")).startswith("3.11"):
        raise ValueError("forum release v2 must be built under Python 3.11")


def promote_forum_controlled_demo_model(
    database: Any,
    release_manifest: Mapping[str, object],
    *,
    now: datetime | None = None,
    deployment_attestation: Mapping[str, object] | None = None,
) -> Mapping[str, object]:
    """Create an immutable forum release and switch its scoped active pointer."""
    document = dict(release_manifest)
    timestamp = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("promotion timestamp must include a timezone")
    validate_forum_controlled_demo_registry_document(document)
    attestation_sha = _validate_deployment_attestation(
        deployment_attestation, document,
    )
    document["promotedAt"] = timestamp
    document["deploymentAttestationSha256"] = attestation_sha
    collection = database.collection("modelRegistry")
    release_ref = collection.document(str(document["releaseId"]))

    @firestore.transactional
    def promote(transaction: Any) -> Mapping[str, object]:
        scoped = list(
            collection.where("releaseScope", "==", "fyp1_forum_controlled_demo")
            .get(transaction=transaction)
        )
        active = [
            snapshot for snapshot in scoped
            if (snapshot.to_dict() or {}).get("isActive") is True
        ]
        existing = release_ref.get(transaction=transaction)
        if len(active) > 1:
            raise ValueError("forum registry contains multiple active records")
        if existing.exists:
            raise ValueError("forum release ID is immutable and already registered")
        if not scoped and document.get("supersedesReleaseId") is not None:
            raise ValueError("the first forum rollout cannot supersede an earlier release")
        if active:
            prior = dict(active[0].to_dict() or {})
            if document.get("supersedesReleaseId") != prior.get("releaseId"):
                raise ValueError("replacement must identify the active forum release")
            transaction.update(active[0].reference, {
                "isActive": False,
                "lifecycleStatus": "superseded",
            })
        elif document.get("supersedesReleaseId") is not None:
            prior_ref = collection.document(str(document["supersedesReleaseId"]))
            prior_snapshot = prior_ref.get(transaction=transaction)
            prior = dict(prior_snapshot.to_dict() or {})
            if (
                not prior_snapshot.exists
                or prior.get("releaseScope") != "fyp1_forum_controlled_demo"
                or prior.get("isActive") is True
                or prior.get("lifecycleStatus") not in {"revoked", "superseded"}
            ):
                raise ValueError("superseded forum release is not compatible history")
        transaction.create(release_ref, document)
        return dict(document)

    return promote(database.transaction())


def _validate_deployment_attestation(
    attestation: Mapping[str, object] | None,
    document: Mapping[str, object],
) -> str:
    if not isinstance(attestation, Mapping) or not attestation:
        raise ValueError("a live deployment attestation is required before promotion")
    if attestation.get("attestationKind") != "live_deployment_attestation_v1":
        raise ValueError("deployment attestation kind is not recognized")
    if attestation.get("deploymentState") != "deployed":
        raise ValueError("deployment attestation must prove a deployed state")
    if attestation.get("releaseId") != document.get("releaseId"):
        raise ValueError("deployment attestation release does not match the manifest")
    if attestation.get("codeRevision") != document.get("codeRevision"):
        raise ValueError("deployment attestation revision does not match the manifest")
    if attestation.get("functionInventorySha256") != forum_inventory_digest():
        raise ValueError("deployment attestation inventory does not match the authoritative inventory")
    if attestation.get("observedFunctionCount") != len(
        validate_forum_function_inventory()
    ):
        raise ValueError(
            "deployment attestation must cover the authoritative forum inventory"
        )
    attested_at = attestation.get("attestedAt")
    if not isinstance(attested_at, str) or not attested_at.endswith("Z"):
        raise ValueError("deployment attestation timestamp must be UTC")
    sha = attestation.get("attestationSha256")
    if not isinstance(sha, str) or not SHA256_PATTERN.fullmatch(sha):
        raise ValueError("deployment attestation hash is invalid")
    return sha


def revoke_forum_controlled_demo_model(
    database: Any, release_id: str,
) -> Mapping[str, object]:
    """Deactivate one active forum release without deleting its audit record."""
    if not release_id:
        raise ValueError("forum release ID is required")
    collection = database.collection("modelRegistry")
    release_ref = collection.document(release_id)

    @firestore.transactional
    def revoke(transaction: Any) -> Mapping[str, object]:
        scoped = list(
            collection.where("releaseScope", "==", "fyp1_forum_controlled_demo")
            .get(transaction=transaction)
        )
        active = [
            item for item in scoped
            if (item.to_dict() or {}).get("isActive") is True
        ]
        if len(active) != 1 or active[0].id != release_id:
            raise ValueError("forum registry must contain only the requested active release")
        snapshot = release_ref.get(transaction=transaction)
        document = dict(snapshot.to_dict() or {})
        if (
            not snapshot.exists
            or document.get("releaseScope") != "fyp1_forum_controlled_demo"
            or document.get("lifecycleStatus") != "released"
            or document.get("isActive") is not True
        ):
            raise ValueError("only the active released forum record may be revoked")
        transaction.update(release_ref, {
            "isActive": False,
            "lifecycleStatus": "revoked",
        })
        return {**document, "isActive": False, "lifecycleStatus": "revoked"}

    return revoke(database.transaction())
