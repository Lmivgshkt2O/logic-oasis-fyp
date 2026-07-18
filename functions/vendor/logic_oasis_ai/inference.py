"""Verified XGBoost inference helpers used by the U8 Functions runtime.

The runtime deliberately verifies the artifact bytes before importing joblib.
Loading a pickle/joblib artifact before its approved digest has been checked
would allow an altered object to execute in the server process.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Mapping, Sequence


class InferenceContractError(ValueError):
    """Raised when a promoted artifact cannot safely be used at runtime."""


@dataclass(frozen=True)
class InferenceResult:
    support_risk: float
    feature_values: Mapping[str, float]


def sha256_file(path: str | Path) -> str:
    source = Path(path)
    try:
        return sha256(source.read_bytes()).hexdigest()
    except OSError as error:
        raise InferenceContractError("artifact_unavailable") from error


def verify_artifact(path: str | Path, *, expected_sha256: str) -> Path:
    """Verify an approved digest before any deserialization is attempted."""
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise InferenceContractError("artifact_hash_invalid")
    source = Path(path)
    if sha256_file(source) != expected_sha256.lower():
        raise InferenceContractError("artifact_hash_mismatch")
    return source


def predict_support_risk(
    artifact_path: str | Path,
    *,
    expected_sha256: str,
    feature_names: Sequence[str],
    feature_values: Mapping[str, float],
) -> InferenceResult:
    """Load one verified promoted artifact and produce a bounded risk score."""
    source = verify_artifact(artifact_path, expected_sha256=expected_sha256)
    if tuple(feature_names) != ("correct_rate", "mean_response_time_ms"):
        raise InferenceContractError("feature_schema_incompatible")
    try:
        import joblib  # Imported only after the bytes passed verification.
        import numpy as np

        model = joblib.load(source)
        values = [float(feature_values[name]) for name in feature_names]
        probabilities = model.predict_proba(np.asarray([values]))
        classes = list(getattr(model, "classes_", ()))
        positive_index = classes.index(1) if 1 in classes else -1
        if positive_index < 0:
            raise InferenceContractError("model_target_incompatible")
        risk = float(probabilities[0][positive_index])
    except InferenceContractError:
        raise
    except Exception as error:  # Never leak model/library detail to clients.
        raise InferenceContractError("model_load_failed") from error
    if not 0.0 <= risk <= 1.0:
        raise InferenceContractError("model_prediction_invalid")
    return InferenceResult(
        support_risk=round(risk, 8),
        feature_values={name: float(feature_values[name]) for name in feature_names},
    )
