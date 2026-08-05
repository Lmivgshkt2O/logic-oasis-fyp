# U7 Model Comparison

No final model-performance result is recorded yet. The current project needs a
consented, pseudonymized real-attempt dataset with both target classes across
multiple students before it can make a preliminary comparison claim.

When the U7 evaluator is run, it records the frozen
`next_attempt_support_needed` label version, `masteryCriterion`, student-grouped
split (seed `20260716`), `quiz-attempt-features-v2` base features
(`correct_rate`, `mean_response_time_ms`), metrics, data-sufficiency level,
telemetry-readiness status, limitations, and pair-audit counts (same-bank,
cross-bank, and immediate-repeat rate). It compares Decision Tree, XGBoost,
and MLP on identical labelled rows; the optional typed BKT-evidence ablation is
named separately. FYP1 MLP early stopping is disabled.

The legacy `Weak`/`Moderate`/`Strong` `.pkl` artifact is excluded from the
active registry and this report.

No synthetic or seed data can support a comparison, superiority, calibration,
or promotion claim.

## Policy-comparison boundary

Bank-selection policy comparison (P1 score threshold, P2 BKT-plus-score
agreement, P3 guarded BKT) is a separate evidence slice. It is produced by the
offline replay pipeline and follows the template in
`ai_pipeline/reports/policy_comparison_template.md`. This report remains a U7
model comparison only (Decision Tree, XGBoost, MLP) and never claims that one
bank-selection policy is better than another.
