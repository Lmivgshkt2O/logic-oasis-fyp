"""Candidate/promotion lifecycle contract for model artifacts.

The registry is in-memory by design at U6.  It establishes the immutable
metadata and promotion gate that the U8 Firestore-backed runtime must honour.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Mapping


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
    lifecycle_status: str = CANDIDATE
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
        if self.lifecycle_status == PROMOTED and self.promoted_at is None:
            raise ValueError("promoted artifacts require promoted_at")
        if self.lifecycle_status == CANDIDATE and self.promoted_at is not None:
            raise ValueError("candidate artifacts cannot have promoted_at")

    def to_registry_document(self) -> dict[str, object]:
        return {
            "artifactId": self.artifact_id,
            "modelType": self.model_type,
            "modelVersion": self.model_version,
            "featureSchemaVersion": self.feature_schema_version,
            "trainingDatasetVersion": self.training_dataset_version,
            "artifactSha256": self.artifact_sha256,
            "lifecycleStatus": self.lifecycle_status,
            "promotedAt": self.promoted_at,
        }


class ModelRegistry:
    """Promote an explicit candidate; never train or activate implicitly."""

    def __init__(self) -> None:
        self._artifacts: dict[str, ModelArtifact] = {}
        self._active_artifact_id: str | None = None

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
