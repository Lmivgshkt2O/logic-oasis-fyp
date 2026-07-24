"""Runtime-safe native XGBoost prediction and Tree SHAP validation.

Imports of the optional numerical packages are deliberately deferred so the
Functions runtime can import the contract before it loads an approved model.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite
from typing import Any, Callable, Sequence


SHAP_RECONSTRUCTION_TOLERANCE = 1e-5


class NativeXGBoostContractError(ValueError):
    """A bounded failure code for native XGBoost/Tree SHAP validation."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class NativeXGBoostExplanation:
    support_risks: tuple[float, ...]
    shap_values: tuple[tuple[float, ...], ...]
    expected_values: tuple[float, ...]
    reconstructed_risks: tuple[float, ...]


def predict_and_explain_native_xgboost(
    model: Any,
    matrix: Any,
    *,
    feature_names: Sequence[str],
    explainer_factory: Callable[[Any], Any] | None = None,
    reconstruction_tolerance: float = SHAP_RECONSTRUCTION_TOLERANCE,
) -> NativeXGBoostExplanation:
    """Return positive-class probabilities plus matching finite Tree SHAP data.

    The caller owns artifact loading. This primitive validates the only values
    that cross the publisher/runtime boundary: positive-class probabilities,
    Tree SHAP feature values, expected values, and logistic reconstruction.
    """
    try:
        import numpy as np

        rows = np.asarray(matrix, dtype=float)
    except Exception as error:
        raise NativeXGBoostContractError("model_prediction_invalid") from error
    if rows.ndim != 2 or rows.shape[1] != len(feature_names) or rows.shape[0] == 0:
        raise NativeXGBoostContractError("model_prediction_invalid")
    try:
        classes = list(getattr(model, "classes_", ()))
        positive_index = classes.index(1)
    except ValueError as error:
        raise NativeXGBoostContractError("model_target_incompatible") from error
    try:
        probabilities = np.asarray(model.predict_proba(rows), dtype=float)
        support_risks = tuple(float(value) for value in probabilities[:, positive_index])
    except Exception as error:
        raise NativeXGBoostContractError("model_prediction_invalid") from error
    if any(not isfinite(value) or not 0.0 <= value <= 1.0 for value in support_risks):
        raise NativeXGBoostContractError("model_prediction_invalid")

    try:
        if explainer_factory is None:
            import shap

            explainer_factory = shap.TreeExplainer
        explained = explainer_factory(model)(rows)
        values = _normalise_shap_values(
            explained.values,
            row_count=rows.shape[0],
            feature_count=len(feature_names),
            positive_index=positive_index,
        )
        expected_values = _normalise_expected_values(
            explained.base_values,
            row_count=rows.shape[0],
            positive_index=positive_index,
        )
    except NativeXGBoostContractError:
        raise
    except Exception as error:
        raise NativeXGBoostContractError("shap_load_failed") from error

    reconstructed = tuple(_sigmoid(expected + sum(row)) for expected, row in zip(expected_values, values))
    if any(abs(actual - expected) > reconstruction_tolerance for actual, expected in zip(reconstructed, support_risks)):
        raise NativeXGBoostContractError("shap_reconstruction_mismatch")
    return NativeXGBoostExplanation(
        support_risks=support_risks,
        shap_values=values,
        expected_values=expected_values,
        reconstructed_risks=reconstructed,
    )


def _normalise_shap_values(
    raw_values: Any,
    *,
    row_count: int,
    feature_count: int,
    positive_index: int,
) -> tuple[tuple[float, ...], ...]:
    import numpy as np

    values = np.asarray(raw_values, dtype=float)
    if values.ndim == 3:
        if values.shape[:2] != (row_count, feature_count) or positive_index >= values.shape[2]:
            raise NativeXGBoostContractError("shap_output_invalid")
        values = values[:, :, positive_index]
    if values.ndim != 2 or values.shape != (row_count, feature_count):
        raise NativeXGBoostContractError("shap_output_invalid")
    normalised = tuple(tuple(float(value) for value in row) for row in values)
    if any(not isfinite(value) for row in normalised for value in row):
        raise NativeXGBoostContractError("shap_output_invalid")
    return normalised


def _normalise_expected_values(
    raw_values: Any,
    *,
    row_count: int,
    positive_index: int,
) -> tuple[float, ...]:
    import numpy as np

    values = np.asarray(raw_values, dtype=float)
    if values.ndim == 0 or values.size == 1:
        expected = (float(values.reshape(-1)[0]),) * row_count
    elif values.ndim == 1 and values.shape[0] == row_count:
        expected = tuple(float(value) for value in values)
    elif values.ndim == 1 and row_count == 1 and positive_index < values.shape[0]:
        expected = (float(values[positive_index]),)
    elif values.ndim == 2 and values.shape[0] == row_count and positive_index < values.shape[1]:
        expected = tuple(float(value) for value in values[:, positive_index])
    else:
        raise NativeXGBoostContractError("shap_output_invalid")
    if any(not isfinite(value) for value in expected):
        raise NativeXGBoostContractError("shap_output_invalid")
    return expected


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + exp(-value))
    exponent = exp(value)
    return exponent / (1.0 + exponent)
