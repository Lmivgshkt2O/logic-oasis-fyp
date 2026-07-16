# U7 Model Comparison

No final model-performance result is recorded yet. The current project needs a
consented, anonymized real-attempt dataset with both target classes across
multiple students before it can make a preliminary comparison claim.

When the U7 evaluator is run, it records the frozen
`next_attempt_support_needed` label version, `masteryCriterion`, grouped split,
feature set, metrics, data-sufficiency level, limitations, and reproducible
random seed. It compares Decision Tree, XGBoost, and MLP on identical labelled
rows; the optional BKT feature ablation is named separately.

The legacy `Weak`/`Moderate`/`Strong` `.pkl` artifact is excluded from the
active registry and this report.
