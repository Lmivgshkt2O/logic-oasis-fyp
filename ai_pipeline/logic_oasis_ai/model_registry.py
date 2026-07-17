"""Candidate/promotion lifecycle contract for model artifacts.

The registry is in-memory by design at U6.  It establishes the immutable
metadata and promotion gate that the U8 Firestore-backed runtime must honour.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Mapping

from .prediction_contract import (
    DEFAULT_MASTERY_CRITERION, PREDICTION_LABEL_VERSION, PREDICTION_TARGET,
    PredictionContract,
)


CANDIDATE = "candidate"
PROMOTED = "promoted"


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
    approval_id: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    approval_rationale: str | None = None
    promoted_at: datetime | None = None

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
        approval_values = (self.approval_id, self.approved_by, self.approved_at, self.approval_rationale)
        if any(value is not None for value in approval_values) and not all(value is not None for value in approval_values):
            raise ValueError("approval metadata must be complete when supplied")
        if self.approved_at is not None and self.approved_at.tzinfo is None:
            raise ValueError("approved_at must include a timezone")

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
            "approvalId": self.approval_id,
            "approvedBy": self.approved_by,
            "approvedAt": self.approved_at,
            "approvalRationale": self.approval_rationale,
            "promotedAt": self.promoted_at,
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
        if not all((artifact.approval_id, artifact.approved_by, artifact.approved_at, artifact.approval_rationale)):
            raise ValueError("supervisor approval metadata is required before activation")
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
