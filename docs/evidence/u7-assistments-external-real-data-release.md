# U7 ASSISTments External-Real-Data Release (Final)

Date: 2026-08-08
Status: **U7 EXTERNAL-REAL-DATA EVALUATION COMPLETE**
Evidence level: **HELD-OUT EXTERNAL-REAL-DATA COMPARISON** with explicit
small-held-out limitation
Model-superiority status: **NOT ESTABLISHED**
BKT-feature improvement: **NOT ESTABLISHED**
Production promotion: **NOT APPROVED**

## 1. Dataset record

- Dataset title: ASSISTments EDM Cup 2023 (competition dataset).
- Publisher/source: ASSISTments; distributed via the Kaggle EDM Cup 2023
  competition.
- Acquisition route: Kaggle competition access accepted; physical CSVs placed
  in the protected external-data directory (outside Git).
- Usage terms: ASSISTments Data Terms of Use, effective 2020-10-30 -
  non-commercial academic/research use, citation required, no
  de-anonymization, no redistribution. Raw and derived learner-level extracts
  are never committed to Git.

## 2. Source hashes and release lineage

- Raw source SHA-256 (J0 record): `action_logs.csv`
  `DB6B0CD4875488D0847D9D9BA2896552F4AD1015F3E2388995222DD4A178443D`;
  `assignment_details.csv`
  `D02D8B62DE088C896FCEB901BC986C25FA07F5D9AEEC0364BF9D351208BEC70E`;
  `problem_details.csv`
  `4F45DAF2E010771C6B5E523DD4D583F3AC451F6CE8F2F35270FCB86B875CEE4E`;
  `sequence_details.csv`
  `A1FA10E6DEBD4FD30C4B04E1554E18F2C426A981BCB10BED0B41DD083CCDB541`
  (full J0 inventory in `u7-assistments-source-validation.md`).
- J1 normalized action rows: `external_action_rows_v1.csv` SHA-256
  `20d9514cabb4b23de0b2a0a4afdc36661ba30d5936aeb1a7950682d6af1ea378`.
- J2-v2 contract: `assistments-j2-attempt-label-contract-v2`
  (predecessor `assistments-j2-attempt-label-contract-v1`); contract hashes in
  the protected `j2_v2_manifest.json`.

## 3. Eligibility and cohort

- Eligible observation window: **2022-01-01 through 2023-12-31** (2022-dominated;
  the release contains 790 action rows in January 2023).
- Primary cohort: **exact Grade 6 Mathematics** (`sourceGrade == "6"` and
  `sourceSubject == "Mathematics"`).
- Prediction unit: one learner-specific exact `sourceSkillCode` episode within
  one completed assignment.
- Grades 4-6 remains the declared secondary analysis and never replaces the
  Grade 6 primary result.

## 4. Frozen methodology

- Contract: `assistments-j2-attempt-label-contract-v2`; provenance
  `external_real`; source window 2022-01-01/2023-12-31.
- Mastery criterion: **0.60**; target `next_attempt_support_needed`.
- Base schema: `quiz-attempt-features-v2` with exactly `correct_rate` and
  `mean_response_time_ms`.
- Response-time rule: `0 < response_time_ms <= 1,800,000`; values above 30
  minutes were censored, not clipped; minimum 3 graded problems and 3 valid
  timing observations per episode; first-graded-response correctness;
  `open_response` excluded; identical-complete-problem-set censoring;
  immediate-next/no-skipping rule.
- Split seed: **20260716**; learner-grouped; no learner overlap.

## 5. Final Grade 6 model dataset

- Labelled rows: 4,401; unique learners: 655; true 848 (19.27%); false 3,553
  (80.73%).
- Training: 653 learners / 4,376 rows (846 true, 3,530 false).
- Held-out: 2 learners / 25 rows (2 true, 23 false); learner overlap 0.
- The held-out comparison gate technically passed under the predeclared
  contract, but the held-out result is **statistically fragile** (2 independent
  learners, 2 positive examples).

## 6. Fair model comparison (J4)

Frozen configurations: Decision Tree (`max_depth=4`, `min_samples_leaf=2`,
`class_weight=balanced`, `random_state=20260716`); XGBoost (`n_estimators=40`,
`max_depth=3`, `learning_rate=0.08`, `subsample=0.9`, `colsample_bytree=0.9`,
`n_jobs=1`, `random_state=20260716`); MLP (`StandardScaler`,
`hidden_layer_sizes=(8,)`, `alpha=0.01`, `max_iter=500`, `tol=0.01`,
`early_stopping=False`, `random_state=20260716`). All three used identical
rows, labels, features, learner groups, and metric definitions.

### Grouped stability (training-only, 5 folds)

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

XGBoost/MLP classified all held-out rows as negative at the frozen threshold;
the 0.92 accuracy reflects negative prevalence, not strong predictive success.
Baseline: positive prevalence ~0.193; majority-class accuracy ~0.807.

## 7. SHAP evidence (J5)

- Frozen artifact: `xgboost-risk-bundle-v1`; global mean |SHAP|:
  `correct_rate` ~0.4365, `mean_response_time_ms` ~0.2069.
- Safe low/median/high predicted-risk local examples preserved in
  `u7_assistments_j5_architecture_evidence.md`.
- SHAP is model-descriptive; it does not establish causality, XGBoost
  superiority, or KSSR validity.

## 8. BKT evidence (J5)

- v2 BKT lineage gate **passed**: 388,777 graded observations; 43,260
  learner-skill states; deterministic chronological ordering; exact skill
  isolation; no future-response injection.
- Version/parameters: `bkt-v1`, prior/pKnown 0.35, pLearn 0.18, pGuess 0.20,
  pSlip 0.10 - reproducible defaults, not target-population calibrated mastery
  claims. BKT is not a fourth classifier.
- Ablation (same 4,401 rows / 655 learners): Decision Tree deltas all 0;
  XGBoost ROC-AUC +0.0026 / PR-AUC +0.0009 / log loss -0.0010 / Brier -0.0002;
  MLP ROC-AUC +0.019 / PR-AUC +0.042 / log loss -0.0135 / Brier -0.0064 but F1
  -0.089 / precision -0.241 / recall -0.053. **No stable improvement** under
  this external Grade 6 evaluation with the frozen bkt-v1 parameters.

## 9. Operational evidence (J5, same machine and input contract)

| Model | Serialized size | Latency median | Latency mean | Invalid predictions |
|---|---:|---:|---:|---:|
| Decision Tree | 3,604 B | 0.773 ms | 0.952 ms | 0 |
| XGBoost | 56,167 B | 5.621 ms | 5.466 ms | 0 |
| MLP | 9,116 B | 1.259 ms | 1.170 ms | 0 |

Complexity: DT realized depth 4 / 31 nodes / 16 leaves; XGBoost 40 trees, max
depth 3, 2 features; MLP one hidden layer of 8 units, 33 parameters, 20
epochs, early stopping disabled.

## 10. Methodology history preserved

- V1 (same learner + same sequence): Grade 6 = 0 labelled rows; Grades 4-6 = 0
  labelled rows, because sequences often represented multi-skill/fluency-round
  assignments with identical problem-set repeats. The v1 failure is not
  hidden.
- J3A: performed before any model training/performance inspection; Candidate A
  (exact non-null `sourceSkillCode`) identified as the closer source-native
  analogue of the canonical student-subtopic prediction unit.
- V2: approved, versioned methodology amendment (same learner + exact
  `sourceSkillCode`); v1 evidence preserved; the amendment was motivated by
  source semantics, not model results; no thresholds or features were changed
  to improve performance.

## 11. Final architecture rationale and promotion decision

- Decision Tree: strongest positive-class recall, easiest native
  interpretation, smallest model, lowest latency; weaker ranking/calibration
  evidence.
- XGBoost: strongest grouped ROC-AUC/PR-AUC and probability quality, supports
  SHAP; near-zero positive-class recall at the frozen threshold; largest and
  slowest of the three; no stable superiority.
- MLP: compact but less natively interpretable; no consistent advantage.
- BKT: remains the project's interpretable sequential mastery estimator; its
  mastery probability did not improve these classifiers stably here.
- SHAP: explanation mechanism for XGBoost risk predictions; not itself
  predictive-performance evidence.

**Production decision: DO NOT PROMOTE THE ASSISTMENTS-TRAINED ARTIFACT.** All
resulting classifiers remain `evidence_only_external`. Reasons: external
U.S.-curriculum evidence, not direct Malaysian KSSR Year 4-6 validation; tiny
frozen held-out learner count; no stable model superiority; poor frozen-
threshold positive recall for XGBoost/MLP; target-domain approval remains a
separate gate. The active model registry and runtime behaviour were not
modified.

## 12. Required limitations

1. External U.S.-curriculum source; not direct KSSR validation.
2. 2022-2023 window heavily dominated by 2022.
3. Only 2 independent learners in the final frozen held-out set.
4. Only 2 held-out support-needed examples.
5. Target imbalance (~19% positive).
6. `open_response` lacks correctness evidence.
7. The 30-minute telemetry censoring is a project-defined quality rule.
8. The v1 mapping failed and required the pre-model v2 skill-level amendment.
9. SHAP is descriptive, not causal.
10. bkt-v1 parameters are reproducible defaults, not calibrated KSSR mastery
    parameters.
11. The BKT feature produced no stable improvement.
12. External artifacts are not production approved.

## 13. Verification and tests

- All J0-J5 manifests, reports, and hashes were re-verified before this
  release (no conflicts).
- Consistency tests (`tests/test_assistments_u7_release_consistency.py`)
  verify report values against J3/J4/J5 manifests, contract v2, mastery 0.60,
  two-feature schema, `external_real` provenance, absence of raw identifiers
  and learner-level datasets in Git, unchanged J4/BKT conclusions, and no
  external artifact marked production-active.
- All affected U7/J0-J6 regression suites pass (see the run record).

## 14. Conclusion

U7 external-real-data evaluation is complete. Decision Tree, XGBoost, and MLP
were fairly compared using identical Grade 6 ASSISTments 2022-2023
learner-skill rows under the frozen Logic Oasis prediction contract. The
comparison produced valid dataset-bounded evidence but did not establish a
stable overall winner. XGBoost provided stronger probability-ranking/
calibration evidence and SHAP explainability, while Decision Tree provided
substantially stronger positive-class recall and lower operational complexity.
The named BKT-feature ablation did not show a stable improvement. Because the
data are external-domain and the frozen held-out set contains only two
learners, no evaluated external artifact is approved for Logic Oasis
production use.

## 15. Post-J6 boundary

Adaptive-question-bank P1/P2/P3a evaluation is **not** started automatically.
The next separate activity is to reuse the compatible external learner-skill
histories for the **Adaptive Question Bank Comparison and Selection Stage-B**
work, subject to its own mapping/evidence gate.

