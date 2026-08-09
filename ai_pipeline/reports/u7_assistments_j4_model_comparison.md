# U7 ASSISTments External-Real Model Comparison (J4, v2 Grade 6)

- Contract: `assistments-j2-attempt-label-contract-v2`
- Dataset version: `assistments-edm-cup-2023-release-v1`
- Provenance: `external_real`; artifact status: **evidence_only_external**
- Mastery criterion: `0.60`; split seed: `20260716`
- Feature columns: `correct_rate, mean_response_time_ms`

## Model configurations (frozen)

- **Decision Tree**: `max_depth=4, min_samples_leaf=2, class_weight=balanced, random_state=20260716`
- **XGBoost**: `n_estimators=40, max_depth=3, learning_rate=0.08, subsample=0.9, colsample_bytree=0.9, n_jobs=1, random_state=20260716 (existing XGBOOST_PARAMETERS)`
- **MLP**: `StandardScaler + MLP(hidden_layer_sizes=(8,), alpha=0.01, early_stopping=False, max_iter=500, tol=0.01, random_state=20260716)`

## Frozen split

- Training: 4376 rows / 653 learners (true 846, false 3530)
- Held-out: 25 rows / 2 learners (true 2, false 23)
- Row identity SHA-256 (all): `0474a94ec06bdb3e5fa930ec6030f48886d64b250e631a49ae2294b78bd91f61`
- Train identity SHA-256: `09eb1b25b308d5e046f0318ee4328089db71ca665b686bcb347a3a9e10621fd6`; held-out identity SHA-256: `7969c906bfe049a0693a1fb6d5b846b54a26c957f88ae1d92c5d2d0322b235f6`

## Baseline context

- Positive-class prevalence: 0.193
- Majority-class accuracy: 0.807

## Frozen held-out results (evaluated once)

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Log loss | Brier |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| decision_tree | 0.48 | 0.133333 | 1.0 | 0.235294 | 0.717391 | 0.166667 | 0.742983 | 0.269102 |
| xgboost | 0.92 | 0.0 | 0.0 | 0.0 | 0.847826 | 0.291667 | 0.324483 | 0.09203 |
| mlp | 0.92 | 0.0 | 0.0 | 0.0 | 0.717391 | 0.190909 | 0.346269 | 0.101372 |

Confusion matrices (held-out, rows=predicted, cols=true/false):
- **decision_tree**: [[10, 13], [0, 2]]
- **xgboost**: [[23, 0], [2, 0]]
- **mlp**: [[23, 0], [2, 0]]

## Training-only repeated student-grouped stability (5 folds, held-out learners excluded)

- Folds: 5; seed: 20260716
- Learners per validation fold: [131, 131, 131, 130, 130]

### decision_tree (mean +/- std across folds)

| Metric | Mean | Std | n |
| --- | ---: | ---: | ---: |
| accuracy | 0.610383 | 0.030424 | 5 |
| precision | 0.288288 | 0.012453 | 5 |
| recall | 0.691511 | 0.05579 | 5 |
| f1 | 0.406735 | 0.0213 | 5 |
| roc_auc | 0.67713 | 0.022492 | 5 |
| pr_auc | 0.320202 | 0.029536 | 5 |
| log_loss | 0.668475 | 0.063032 | 5 |
| brier_score | 0.223665 | 0.007347 | 5 |

### xgboost (mean +/- std across folds)

| Metric | Mean | Std | n |
| --- | ---: | ---: | ---: |
| accuracy | 0.804309 | 0.015754 | 5 |
| precision | 0.439394 | 0.087663 | 5 |
| recall | 0.029106 | 0.014988 | 5 |
| f1 | 0.053585 | 0.025521 | 5 |
| roc_auc | 0.686978 | 0.020631 | 5 |
| pr_auc | 0.346618 | 0.03128 | 5 |
| log_loss | 0.45724 | 0.026218 | 5 |
| brier_score | 0.145104 | 0.010185 | 5 |

### mlp (mean +/- std across folds)

| Metric | Mean | Std | n |
| --- | ---: | ---: | ---: |
| accuracy | 0.792485 | 0.016 | 5 |
| precision | 0.307348 | 0.037959 | 5 |
| recall | 0.054433 | 0.009088 | 5 |
| f1 | 0.091826 | 0.012747 | 5 |
| roc_auc | 0.663704 | 0.020691 | 5 |
| pr_auc | 0.295107 | 0.012635 | 5 |
| log_loss | 0.476289 | 0.027508 | 5 |
| brier_score | 0.153291 | 0.010666 | 5 |

## Training/preprocessing confirmation

- MLP `StandardScaler` is fit inside `train_mlp` on training learners only (pipeline fitted per fold and once on the frozen training partition); held-out data is never used for fitting.
- DT/XGBoost use only their existing declared preprocessing.
- Training time (seconds): {"decision_tree": 3.9305801999289542, "xgboost": 0.2324304000940174, "mlp": 0.47815590002574027}

## Limitations

- Held-out contains only **2 independent learners and 25 rows (2 positives)**; metrics are reported with this limitation and cannot alone support a cautious-superiority claim.
- Evidence is ASSISTments external U.S.-curriculum data; it is **not direct KSSR validation** and no generalization to Logic Oasis target users is claimed.
- Class imbalance (~19% positive) means accuracy near 81% equals the majority baseline; precision/recall/F1/PR-AUC and probability quality must be read alongside accuracy.

## Conclusion

- Level: **MODEL COMPARISON COMPLETED**
- Rationale: metrics exist but no stable advantage is established

No model artifact was promoted; all artifacts remain `evidence_only_external`.
