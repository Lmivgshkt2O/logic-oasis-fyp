# U7 ASSISTments Architecture Evidence (J5, v2 Grade 6)

- Contract: `assistments-j2-attempt-label-contract-v2`; provenance: `external_real`
- J4 conclusion preserved: **MODEL COMPARISON COMPLETED; NO STABLE ADVANTAGE ESTABLISHED**

## XGBoost global SHAP summary (frozen two-feature model)

- Model/artifact version: `xgboost-risk-bundle-v1`; explained rows (training): 4376
- Base value: -1.433746
- Ranking by mean |SHAP|: correct_rate, mean_response_time_ms

| Feature | Mean |SHAP| | Mean SHAP | 5% | 50% | 95% |
| --- | ---: | ---: | ---: | ---: | ---: |
| correct_rate | 0.436486 | -0.079565 | -0.571822 | -0.14154 | 0.636351 |
| mean_response_time_ms | 0.206929 | -0.030804 | -0.867017 | 0.035439 | 0.269174 |

Interpretation boundary: SHAP describes how the frozen XGBoost model's two input features contributed to its predicted support-risk probabilities; it is not causal evidence.

## Safe local SHAP examples (predeclared low / median / high risk)

- Rule: **lowest_predicted_risk**; correct_rate=0.875; mean_response_time_ms=4723.875; predicted_probability=0.041516; base_value=-1.433746; SHAP={'correct_rate': -0.600652, 'mean_response_time_ms': -1.104866}
- Rule: **median_predicted_risk**; correct_rate=0.81818182; mean_response_time_ms=20102.45454545; predicted_probability=0.17878; base_value=-1.433746; SHAP={'correct_rate': 0.046445, 'mean_response_time_ms': -0.137332}
- Rule: **highest_predicted_risk**; correct_rate=0.2; mean_response_time_ms=544096.0; predicted_probability=0.627546; base_value=-1.433746; SHAP={'correct_rate': 1.313428, 'mean_response_time_ms': 0.642023}

The examples demonstrate model explanation only, not prediction accuracy or pedagogical causality.

## Operational evidence (same machine, same input contract, warm-up + 10 runs)

| Model | Serialized size (bytes) | Latency median (ms) | Latency mean (ms) | Invalid predictions |
| --- | ---: | ---: | ---: | ---: |
| decision_tree | 3604 | 0.773 | 0.95217 | 0 |
| xgboost | 56167 | 5.62105 | 5.46639 | 0 |
| mlp | 9116 | 1.2593 | 1.17037 | 0 |

## Model complexity

```json
{
  "decision_tree": {
    "configuredMaxDepth": 4,
    "realizedMaxDepth": 4,
    "nodeCount": 31,
    "leafCount": 16,
    "note": "Decision Tree interpretability does not automatically imply better predictive performance"
  },
  "xgboost": {
    "nEstimators": 40,
    "configuredMaxDepth": 3,
    "featureCount": 2
  },
  "mlp": {
    "hiddenLayerSizes": [
      8
    ],
    "nLayers": 3,
    "parameterCount": 33,
    "nIter": 20,
    "earlyStopping": false,
    "interpretabilityLimitation": "MLP has weaker native human interpretability than the Decision Tree and the SHAP-explained XGBoost architecture"
  }
}
```

## BKT v2 lineage gate

```json
{
  "passed": true,
  "modelVersion": "bkt-v1",
  "parameterSource": "frozen bkt-v1 DEFAULT_BKT_PARAMETERS",
  "parameters": {
    "priorKnowledge": 0.35,
    "learnRate": 0.18,
    "guessRate": 0.2,
    "slipRate": 0.1
  },
  "deterministicOrder": true,
  "nonNullSkill": true,
  "learnerSkillStateCount": 43260,
  "observationCount": 388777,
  "orderingRule": "(sourceTimestamp, externalAssignmentKey, externalProblemKey)",
  "crossSkillMixingPrevented": true,
  "futureInjectionPrevented": true
}
```

BKT ablation status: completed

- Eligible labelled rows: 4401; learners: 655
- Base/BKT row identity identical except BKT feature: True

### Grouped metric delta (BKT variant - base variant, training-only 5 folds)

| Algorithm | Metric | Delta |
| --- | --- | ---: |
| decision_tree | accuracy | 0.0 |
| decision_tree | precision | 0.0 |
| decision_tree | recall | 0.0 |
| decision_tree | f1 | 0.0 |
| decision_tree | roc_auc | 0.0 |
| decision_tree | pr_auc | 0.0 |
| decision_tree | log_loss | 0.0 |
| decision_tree | brier_score | 0.0 |
| xgboost | accuracy | 0.000211 |
| xgboost | precision | 0.114336 |
| xgboost | recall | -0.000766 |
| xgboost | f1 | -0.002051 |
| xgboost | roc_auc | 0.002639 |
| xgboost | pr_auc | 0.000853 |
| xgboost | log_loss | -0.000971 |
| xgboost | brier_score | -0.000221 |
| mlp | accuracy | 0.013368 |
| mlp | precision | -0.240681 |
| mlp | recall | -0.0531 |
| mlp | f1 | -0.089212 |
| mlp | roc_auc | 0.019023 |
| mlp | pr_auc | 0.041725 |
| mlp | log_loss | -0.013521 |
| mlp | brier_score | -0.006382 |

A single numeric difference is not declared an improvement without considering grouped variability.

## Limitations and governance

- External U.S.-curriculum ASSISTments evidence; **not direct Malaysian KSSR validation**.
- Held-out contains only 2 independent learners / 2 positives; supplemental only.
- All artifacts remain `evidence_only_external`; no registry promotion.

## J5 conclusion

- SHAP/operational evidence completed; BKT ablation completed (if gate passed) or documented unavailable.
- The frozen J4 conclusion is not rewritten.
