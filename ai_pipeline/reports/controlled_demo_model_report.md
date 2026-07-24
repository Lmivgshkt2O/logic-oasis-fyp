# Controlled-demonstration XGBoost mechanics report

- Claim level: `controlled_demonstration_only`
- Evaluation status: `evaluated`
- Dataset: `controlled-demo-dataset-v1` (`4f41f2cb3438ca4632235354980f51f8f36b88ede8846b89ac2d6714dbd02ec2`)
- Catalogue SHA-256: `0e984d84afd6ffcb8feef8340f73d6bcb74270bfe160bbdb27090627627237a8`
- Configuration SHA-256: `d18cc9017e121885741c7fbdbb4aff0ffb9310202e6f4d5dc82c27185032f668`
- Evaluation report SHA-256: `7c269eb0212b6a9196ee61de6f4a1169dbe4119aaef4250727959c2f8668c614`
- Model artifact SHA-256: `9a32079d95a37dc1d3eeecc52f5e7723e12ac1ee3dd8f6eb9dc609a3fa11f39a`
- Artifact manifest SHA-256: `c7f29d46afbfab7509550e8a301b56bc89a713fd3e4685519ede6e0ed4c1a98e`
- Random seed: `20260716`
- Training groups: `challenge-transfer-v1, steady-recovery-v1, threshold-variation-v1`
- Held-out groups: `scaffolded-progress-v1`

## Mechanics comparison

All models used the same grouped rows and exactly `correct_rate` plus `mean_response_time_ms`.
These metrics describe fit to fictional supervisor-reviewed scenarios only; they are not real-world performance or superiority evidence.

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
