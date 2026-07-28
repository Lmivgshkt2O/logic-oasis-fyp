"""Candidate/promotion lifecycle contract for model artifacts.

The registry is in-memory by design at U6.  It establishes the immutable
metadata and promotion gate that the U8 Firestore-backed runtime must honour.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import re
from typing import Mapping

from .prediction_contract import (
    DEFAULT_MASTERY_CRITERION, PREDICTION_LABEL_VERSION, PREDICTION_TARGET,
    PredictionContract,
)


CANDIDATE = "candidate"
PROMOTED = "promoted"
CONTROLLED_DEMO_PROVENANCE = "expert_authored_controlled_demo"
CONTROLLED_DEMO_EVIDENCE_LEVEL = "controlled_demonstration"
CONTROLLED_DEMO_RELEASE_SCOPE = "fyp1_controlled_demo"
CONTROLLED_DEMO_DEPLOYMENT_SCOPE = "controlled_demo"
REAL_EVALUATED_DEPLOYMENT_SCOPE = "real_evaluated"
CONTROLLED_DEMO_RELEASE_RATIONALE_MARKER = "not real-world validated"
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
MODEL_VERSION_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?")
BUCKET_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{1,221}[a-z0-9]")


@dataclass(frozen=True)
class ModelArtifact:
    artifact_id: str
    model_type: str
    model_version: str
    feature_schema_version: str
    training_dataset_version: str
    artifact_sha256: str
    prediction_target: str = PREDICTION_TARGET
    label_version: str = PREDICTION_LABEL_VERSION
    mastery_criterion: float = DEFAULT_MASTERY_CRITERION
    evaluation_status: str = "not_evaluated"
    evaluation_report_sha256: str | None = None
    artifact_manifest_sha256: str | None = None
    promotion_gate_status: str = "not_passed"
    lifecycle_status: str = CANDIDATE
    release_id: str | None = None
    released_by: str | None = None
    released_at: datetime | None = None
    release_rationale: str | None = None
    promoted_at: datetime | None = None
    training_data_provenance: str | None = None
    evidence_level: str | None = None
    release_scope: str | None = None
    deployment_scope: str | None = None
    scenario_catalogue_sha256: str | None = None
    controlled_demo_config_sha256: str | None = None

    def __post_init__(self) -> None:
        for field in (
            "artifact_id", "model_type", "model_version", "feature_schema_version",
            "training_dataset_version", "artifact_sha256",
        ):
            if not getattr(self, field):
                raise ValueError(f"{field} is required")
        if self.lifecycle_status not in (CANDIDATE, PROMOTED):
            raise ValueError("lifecycle_status must be candidate or promoted")
        if not 0.0 < self.mastery_criterion < 1.0:
            raise ValueError("mastery_criterion must be between zero and one")
        if self.evaluation_status not in {"not_evaluated", "evaluated"}:
            raise ValueError("evaluation_status must be not_evaluated or evaluated")
        if self.evaluation_status == "evaluated" and not self.evaluation_report_sha256:
            raise ValueError("evaluated artifacts require evaluation_report_sha256")
        if self.promotion_gate_status not in {"not_passed", "passed"}:
            raise ValueError("promotion_gate_status must be not_passed or passed")
        if self.promotion_gate_status == "passed" and self.evaluation_status != "evaluated":
            raise ValueError("promotion requires an evaluated artifact")
        if self.lifecycle_status == PROMOTED and self.promoted_at is None:
            raise ValueError("promoted artifacts require promoted_at")
        if self.lifecycle_status == CANDIDATE and self.promoted_at is not None:
            raise ValueError("candidate artifacts cannot have promoted_at")
        release_values = (self.release_id, self.released_by, self.released_at, self.release_rationale)
        if any(value is not None for value in release_values) and not all(value is not None for value in release_values):
            raise ValueError("release metadata must be complete when supplied")
        if self.released_at is not None and self.released_at.tzinfo is None:
            raise ValueError("released_at must include a timezone")
        if self.deployment_scope == CONTROLLED_DEMO_DEPLOYMENT_SCOPE:
            validate_controlled_demo_artifact(self)

    def to_registry_document(self) -> dict[str, object]:
        return {
            "artifactId": self.artifact_id,
            "modelType": self.model_type,
            "modelVersion": self.model_version,
            "featureSchemaVersion": self.feature_schema_version,
            "trainingDatasetVersion": self.training_dataset_version,
            "artifactSha256": self.artifact_sha256,
            "predictionTarget": self.prediction_target,
            "labelVersion": self.label_version,
            "masteryCriterion": self.mastery_criterion,
            "evaluationStatus": self.evaluation_status,
            "evaluationReportSha256": self.evaluation_report_sha256,
            "artifactManifestSha256": self.artifact_manifest_sha256,
            "promotionGateStatus": self.promotion_gate_status,
            "lifecycleStatus": self.lifecycle_status,
            "releaseId": self.release_id,
            "releasedBy": self.released_by,
            "releasedAt": self.released_at,
            "releaseRationale": self.release_rationale,
            "promotedAt": self.promoted_at,
            "trainingDataProvenance": self.training_data_provenance,
            "evidenceLevel": self.evidence_level,
            "releaseScope": self.release_scope,
            "deploymentScope": self.deployment_scope,
            "scenarioCatalogueSha256": self.scenario_catalogue_sha256,
            "controlledDemoConfigSha256": self.controlled_demo_config_sha256,
        }


class ModelRegistry:
    """Promote an explicit candidate; never train or activate implicitly."""

    def __init__(self, *, prediction_contract: PredictionContract = PredictionContract()) -> None:
        self._artifacts: dict[str, ModelArtifact] = {}
        self._active_artifact_id: str | None = None
        self._prediction_contract = prediction_contract

    def register_candidate(self, artifact: ModelArtifact) -> ModelArtifact:
        if artifact.lifecycle_status != CANDIDATE:
            raise ValueError("only candidate artifacts may be registered")
        existing = self._artifacts.get(artifact.artifact_id)
        if existing is not None and existing != artifact:
            raise ValueError("artifact ID is immutable")
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def promote(self, artifact_id: str, *, promoted_at: datetime | None = None) -> ModelArtifact:
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            raise ValueError("candidate artifact is not registered")
        if artifact.lifecycle_status != CANDIDATE:
            raise ValueError("only candidate artifacts may be promoted")
        if artifact.model_type != "xgboost":
            raise ValueError("only evaluated XGBoost artifacts may become active runtime models")
        if artifact.evaluation_status != "evaluated":
            raise ValueError("an unevaluated artifact cannot become active")
        if artifact.promotion_gate_status != "passed":
            raise ValueError("an artifact whose promotion gates have not passed cannot become active")
        contract = self._prediction_contract
        if (
            artifact.prediction_target != contract.target_name
            or artifact.label_version != contract.label_version
            or artifact.mastery_criterion != contract.mastery_criterion
            or artifact.feature_schema_version != contract.feature_schema_version
        ):
            raise ValueError("artifact does not match the active prediction contract")
        if not artifact.artifact_manifest_sha256:
            raise ValueError("an artifact without a manifest cannot become active")
        if not all((artifact.release_id, artifact.released_by, artifact.released_at, artifact.release_rationale)):
            raise ValueError("developer release metadata is required before activation")
        timestamp = promoted_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise ValueError("promoted_at must include a timezone")
        promoted = replace(artifact, lifecycle_status=PROMOTED, promoted_at=timestamp)
        self._artifacts[artifact_id] = promoted
        self._active_artifact_id = artifact_id
        return promoted

    def active_runtime_model(self) -> ModelArtifact:
        if self._active_artifact_id is None:
            raise ValueError("no promoted runtime model is active")
        artifact = self._artifacts[self._active_artifact_id]
        if artifact.lifecycle_status != PROMOTED:
            raise ValueError("an unpromoted artifact cannot be active")
        return artifact

    def artifacts(self) -> Mapping[str, ModelArtifact]:
        return dict(self._artifacts)


def validate_controlled_demo_artifact(artifact: ModelArtifact) -> None:
    """Require the complete developer-release boundary for demo evidence."""
    expected = {
        "training_data_provenance": CONTROLLED_DEMO_PROVENANCE,
        "evidence_level": CONTROLLED_DEMO_EVIDENCE_LEVEL,
        "release_scope": CONTROLLED_DEMO_RELEASE_SCOPE,
        "deployment_scope": CONTROLLED_DEMO_DEPLOYMENT_SCOPE,
    }
    if any(getattr(artifact, field) != value for field, value in expected.items()):
        raise ValueError("controlled-demo artifact metadata does not match its release scope")
    if any(
        not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value)
        for value in (artifact.scenario_catalogue_sha256, artifact.controlled_demo_config_sha256)
    ):
        raise ValueError("controlled-demo catalogue and configuration hashes are required")
    if (
        not isinstance(artifact.release_rationale, str)
        or CONTROLLED_DEMO_RELEASE_RATIONALE_MARKER not in artifact.release_rationale.lower()
    ):
        raise ValueError("controlled-demo release must state that it is not real-world validated")


def validate_model_bucket_uri(value: str) -> str:
    if not isinstance(value, str) or not value.startswith("gs://"):
        raise ValueError("model bucket must be a gs:// bucket root")
    bucket_name = value[5:]
    if "/" in bucket_name or ".." in bucket_name or not BUCKET_PATTERN.fullmatch(bucket_name):
        raise ValueError("model bucket must not contain an object prefix or traversal")
    return bucket_name


def validate_model_version(value: object) -> str:
    if not isinstance(value, str) or not MODEL_VERSION_PATTERN.fullmatch(value) or ".." in value:
        raise ValueError("model version must be a safe lowercase token")
    return value


def controlled_demo_object_paths(model_bucket: str, model_version: object) -> tuple[str, str]:
    bucket_name = validate_model_bucket_uri(model_bucket)
    version = validate_model_version(model_version)
    prefix = f"gs://{bucket_name}/controlled-demo/{version}"
    return f"{prefix}/model.ubj", f"{prefix}/manifest.json"
