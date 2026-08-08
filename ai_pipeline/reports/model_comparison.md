# U7 Model Comparison

## Status

**MODEL COMPARISON COMPLETED. NO STABLE OVERALL MODEL ADVANTAGE ESTABLISHED.**

The final U7 model-comparison evidence is a **held-out external-real-data
comparison** on ASSISTments EDM Cup 2023 (Grade 6 Mathematics, 2022-2023,
provenance `external_real`, contract
`assistments-j2-attempt-label-contract-v2`) with an explicit small-held-out
limitation (2 independent learners, 2 positive examples). The full evidence
record is in
`docs/evidence/u7-assistments-external-real-data-release.md`.

## Final comparison summary (ASSISTments external-real-data evidence)

Prediction target: `next_attempt_support_needed`; mastery criterion `0.60`;
base schema `quiz-attempt-features-v2` (`correct_rate`,
`mean_response_time_ms`); split seed `20260716`; training 653 learners / 4,376
rows (846 true, 3,530 false); held-out 2 learners / 25 rows (2 true, 23
false); zero learner overlap.

### Training-only repeated student-grouped stability (5 folds)

| Model | ROC-AUC | PR-AUC | Recall | F1 | Log loss | Brier |
|---|---:|---:|---:|---:|---:|---:|
| Decision Tree | 0.677 +/- 0.022 | 0.320 +/- 0.030 | 0.692 | 0.407 | 0.668 | 0.224 |
| XGBoost | 0.687 +/- 0.021 | 0.347 +/- 0.031 | 0.029 | 0.054 | 0.457 | 0.145 |
| MLP | 0.664 +/- 0.021 | 0.295 +/- 0.013 | 0.054 | 0.092 | 0.476 | 0.153 |

### Frozen held-out (evaluated once)

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Log loss | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Decision Tree | 0.48 | 0.133 | 1.000 | 0.235 | 0.717 | 0.167 | 0.743 | 0.269 |
| XGBoost | 0.92 | 0.000 | 0.000 | 0.000 | 0.848 | 0.292 | 0.324 | 0.092 |
| MLP | 0.92 | 0.000 | 0.000 | 0.000 | 0.717 | 0.191 | 0.346 | 0.101 |

XGBoost and MLP classified all 25 held-out rows as negative at the frozen
threshold; the 0.92 accuracy mostly reflects the 23/25 negative prevalence
(majority-class accuracy 0.807) and must not be described as strong predictive
success.

### Final interpretation

Decision Tree offered the strongest positive-class recall and the simplest
operational/interpretability profile, while XGBoost showed somewhat stronger
ranking and probability-quality metrics and supported SHAP-based explanations.
However, XGBoost's positive-class recall at the frozen classification
threshold was near zero, and its small ROC-AUC advantage over the Decision Tree
was inside grouped variability. The MLP did not demonstrate a clear advantage.
The evaluation does not support a claim that any one classifier is superior.

## SHAP and BKT (ASSISTments external-real-data evidence)

- XGBoost global SHAP (frozen artifact `xgboost-risk-bundle-v1`): mean |SHAP|
  `correct_rate` ~0.4365 > `mean_response_time_ms` ~0.2069. SHAP is
  model-descriptive, not causal, and does not establish superiority or KSSR
  validity.
- Named BKT ablation (base vs `bkt_mastery_probability`, frozen `bkt-v1`
  parameters, same 4,401 rows / 655 learners): all changes were within grouped
  variability or involved trade-offs. **BKT feature showed no stable
  improvement** under this external Grade 6 evaluation.

## Evidence-level separation

- **Demonstration evidence** (controlled-demo / synthetic fixtures): exercises
  pipeline mechanics only; never supports a real-data claim. See
  `reports/controlled_demo_model_report.md` and the forum emulator evidence.
- **ASSISTments external-real-data evidence (this report)**: valid
  dataset-bounded comparison with explicit small-held-out limitation; no
  production promotion.
- **Native Logic Oasis runtime/target-domain evidence**: not yet available;
  remains a separate gate and is not claimed by this external comparison.

No external-trained artifact is approved for production. All evaluated
classifiers remain `evidence_only_external`.

