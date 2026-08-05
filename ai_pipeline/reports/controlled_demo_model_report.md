# Controlled-demonstration XGBoost mechanics report

- Claim level: `controlled_demonstration_only`
- Evaluation status: `evaluated`
- Dataset: `controlled-demo-dataset-v1` (`adb666f4a497044c6e908b1f57048da564b965fca8795234471ec13b8285b2c6`)
- Catalogue SHA-256: `5a19431be1188ddc8df32fbfa4c610c5b3d912811984c861d79029ec15606af0`
- Configuration SHA-256: `7e47adae0d00a84bd7cff39686029221255d9f096240c70263eacb03f3a1fdc7`
- Evaluation report SHA-256: `7c269eb0212b6a9196ee61de6f4a1169dbe4119aaef4250727959c2f8668c614`
- Model artifact SHA-256: `9a32079d95a37dc1d3eeecc52f5e7723e12ac1ee3dd8f6eb9dc609a3fa11f39a`
- Artifact manifest SHA-256: `470f7dca79f14035d910aae45958d6f21f85423b44d01c6bc5830ffbb914ed4e`
- Random seed: `20260716`
- Training groups: `challenge-transfer-v1, steady-recovery-v1, threshold-variation-v1`
- Held-out groups: `scaffolded-progress-v1`

## Mechanics comparison

All models used the same grouped rows and exactly `correct_rate` plus `mean_response_time_ms`.
These metrics describe fit to fictional developer-authored scenarios only; they are not real-world performance or superiority evidence.

| Model | Accuracy | F1 | ROC-AUC | PR-AUC | Log loss | Brier |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| decision_tree | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 |
| xgboost | 1.0 | 1.0 | 1.0 | 1.0 | 0.242898 | 0.055456 |
| mlp | 0.666667 | 0.0 | 0.0 | 0.333333 | 0.785715 | 0.290623 |

## Tree SHAP integrity

The same serialized XGBoost artifact reconstructed low-, medium-, and high-risk outputs within `1e-05`.
- `low`: risk `0.14796571`, reconstructed `0.1479657`, absolute error `1.42e-08`, features `correct_rate, mean_response_time_ms`.
- `medium`: risk `0.87733501`, reconstructed `0.87733496`, absolute error `5.02e-08`, features `correct_rate, mean_response_time_ms`.
- `high`: risk `0.8904053`, reconstructed `0.89040529`, absolute error `9.2e-09`, features `correct_rate, mean_response_time_ms`.

## Limitations

This is an implemented controlled demonstration based on fictional trajectories. It does not establish accuracy for real students, learning improvement, calibration, or superiority over Decision Tree or MLP baselines.
