from __future__ import annotations

from math import log
from types import SimpleNamespace
import unittest

import numpy as np

from logic_oasis_ai.native_xgboost import (
    NativeXGBoostContractError,
    predict_and_explain_native_xgboost,
)


FEATURE_NAMES = ("correct_rate", "mean_response_time_ms")


class FakeModel:
    def __init__(self, probabilities, *, classes=(0, 1)) -> None:
        self.classes_ = list(classes)
        self._probabilities = probabilities

    def predict_proba(self, _matrix):
        return self._probabilities


class NativeXGBoostTests(unittest.TestCase):
    def test_normalises_positive_class_tree_shap_and_reconstructs_prediction(self) -> None:
        support_risk = 0.75
        expected_value = 0.2
        explanation = SimpleNamespace(
            values=np.asarray([[[0.1, 0.3], [0.2, log(support_risk / (1 - support_risk)) - expected_value - 0.3]]]),
            base_values=np.asarray([[0.0, expected_value]]),
        )

        result = predict_and_explain_native_xgboost(
            FakeModel([[0.25, support_risk]]), [[0.5, 400.0]], feature_names=FEATURE_NAMES,
            explainer_factory=lambda _model: lambda _matrix: explanation,
        )

        self.assertEqual((support_risk,), result.support_risks)
        self.assertEqual((expected_value,), result.expected_values)
        self.assertAlmostEqual(support_risk, result.reconstructed_risks[0])

    def test_rejects_contract_failure_branches(self) -> None:
        valid = SimpleNamespace(values=np.asarray([[0.3, log(3) - 0.5]]), base_values=np.asarray([0.5]))
        cases = (
            ("missing_positive_class", FakeModel([[1.0]], classes=(0,)), valid, "model_target_incompatible"),
            ("invalid_probability", FakeModel([[float("nan"), 1.2]]), valid, "model_prediction_invalid"),
            ("malformed_shap", FakeModel([[0.25, 0.75]]), SimpleNamespace(values=np.asarray([0.3, 0.4]), base_values=np.asarray([0.5])), "shap_output_invalid"),
            ("nonfinite_shap", FakeModel([[0.25, 0.75]]), SimpleNamespace(values=np.asarray([[float("inf"), 0.4]]), base_values=np.asarray([0.5])), "shap_output_invalid"),
            ("nonfinite_base", FakeModel([[0.25, 0.75]]), SimpleNamespace(values=np.asarray([[0.3, 0.4]]), base_values=np.asarray([float("nan")])), "shap_output_invalid"),
            ("reconstruction_mismatch", FakeModel([[0.25, 0.75]]), SimpleNamespace(values=np.asarray([[0.1, 0.1]]), base_values=np.asarray([0.1])), "shap_reconstruction_mismatch"),
        )
        for name, model, explanation, expected_code in cases:
            with self.subTest(name=name), self.assertRaises(NativeXGBoostContractError) as raised:
                predict_and_explain_native_xgboost(
                    model, [[0.5, 400.0]], feature_names=FEATURE_NAMES,
                    explainer_factory=lambda _model, result=explanation: lambda _matrix: result,
                )
            self.assertEqual(expected_code, raised.exception.code)

    def test_explainer_failure_is_bounded(self) -> None:
        def explode(_model):
            raise RuntimeError("TreeExplainer unavailable")

        with self.assertRaises(NativeXGBoostContractError) as raised:
            predict_and_explain_native_xgboost(
                FakeModel([[0.25, 0.75]]), [[0.5, 400.0]], feature_names=FEATURE_NAMES,
                explainer_factory=explode,
            )
        self.assertEqual("shap_load_failed", raised.exception.code)
