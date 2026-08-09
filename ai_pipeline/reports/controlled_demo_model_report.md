# Controlled-demonstration XGBoost mechanics report

- Claim level: `controlled_demonstration_only`
- Evaluation status: `evaluated`
- Dataset: `controlled-demo-dataset-v1` (`c8e52cccbe839f508df55cb118a9620b72a207624c9acf4c0de27df5126e54c1`)
- Catalogue SHA-256: `2ef2a006e0fad0474204e94a7449b35d79618090b28de7086dec23976df7306f`
- Configuration SHA-256: `d18cc9017e121885741c7fbdbb4aff0ffb9310202e6f4d5dc82c27185032f668`
- Evaluation report SHA-256: `f58df991239701155aeabf6de75fb8ea209764bacdb353e6bfb3133656b2fdcf`
- Model artifact SHA-256: `04d4bb495e7e3d1cd713e611154d84153d22a6601e7b31890551e618d8d33731`
- Artifact manifest SHA-256: `494f0d67c6033a6d7933a369908900b0cc4d54ca414b8e8039008c8999421a39`
- Random seed: `20260716`
- Training groups: `challenge-transfer-v1, steady-recovery-v1, threshold-variation-v1`
- Held-out groups: `scaffolded-progress-v1`

## Mechanics comparison

All models used the same grouped rows and exactly `correct_rate` plus `mean_response_time_ms`.
These metrics describe fit to fictional developer-authored scenarios only; they are not real-world performance or superiority evidence.

| Model | Accuracy | F1 | ROC-AUC | PR-AUC | Log loss | Brier |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| decision_tree | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 |
| xgboost | 1.0 | 1.0 | 1.0 | 1.0 | 0.321737 | 0.094023 |
| mlp | 0.666667 | 0.0 | 0.0 | 0.333333 | 0.785715 | 0.290623 |

## Tree SHAP integrity

The same serialized XGBoost artifact reconstructed low-, medium-, and high-risk outputs within `1e-05`.
- `low`: risk `0.14865448`, reconstructed `0.14865453`, absolute error `5.12e-08`, features `correct_rate, mean_response_time_ms`.
- `medium`: risk `0.86070406`, reconstructed `0.86070405`, absolute error `1.02e-08`, features `correct_rate, mean_response_time_ms`.
- `high`: risk `0.89167809`, reconstructed `0.89167813`, absolute error `3.31e-08`, features `correct_rate, mean_response_time_ms`.

## Limitations

This is an implemented controlled demonstration based on fictional trajectories. It does not establish accuracy for real students, learning improvement, calibration, or superiority over Decision Tree or MLP baselines.
