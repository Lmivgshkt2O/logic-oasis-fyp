"""Bounded SHAP explanation helpers for the audited U8 raw model run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .inference import InferenceContractError, verify_artifact


@dataclass(frozen=True)
class ShapExplanation:
    values: Mapping[str, float]
    expected_value: float | None


def explain_prediction(
    artifact_path: str,
    *,
    expected_sha256: str,
    feature_names: Sequence[str],
    feature_values: Mapping[str, float],
) -> ShapExplanation:
    """Return raw audit evidence only after the artifact integrity check."""
    source = verify_artifact(artifact_path, expected_sha256=expected_sha256)
    try:
        import joblib
        import numpy as np
        import shap

        model = joblib.load(source)
        row = np.asarray([[float(feature_values[name]) for name in feature_names]])
        explained = shap.TreeExplainer(model)(row)
        values = explained.values
        if getattr(values, "ndim", 0) == 3:
            values = values[0, :, -1]
        elif getattr(values, "ndim", 0) == 2:
            values = values[0]
        else:
            raise InferenceContractError("shap_output_invalid")
        base_values = explained.base_values
        expected = float(base_values.reshape(-1)[-1]) if hasattr(base_values, "reshape") else None
        return ShapExplanation(
            values={name: round(float(value), 8) for name, value in zip(feature_names, values)},
            expected_value=expected,
        )
    except InferenceContractError:
        raise
    except Exception as error:
        raise InferenceContractError("shap_load_failed") from error
