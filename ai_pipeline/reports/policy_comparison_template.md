# Logic Oasis Policy Comparison - Stage B Evidence Package

**Claim level:** `{{claimLevel}}`. {{claimRationale}}

This evidence package is **observational and descriptive**. It does not claim
that any bank-selection policy is better than another and it does not claim
that offline replay proves a learning effect.

## Frozen run manifest

Records the dataset version and SHA-256, provenance, HMAC namespace, source /
feature / BKT / adaptive-policy / policy-evaluation versions, frozen prediction
target and label version, outcome window, censoring rules, random seed, and
manifest SHA-256. Every figure below traces to this manifest.

## Decision and censoring totals

Total reconstructed decisions, observed assignment-matched outcomes, and
censored outcomes. Figure data and tabular metrics must reconcile to these
totals.

## Promotion-safety forest plot data

P3a minus each comparator (P1, P2) on descriptive false-promotion burden over
observed assignment-matched outcomes, with student-clustered bootstrap 95%
intervals, both arms' burdens, the descriptive false-demotion delta, and the
sample denominator. This is the primary evidence chart.

## Safety-benefit quadrant data

False-promotion burden on one axis and descriptive false demotion / unnecessary
hold rate on the other. A policy is preferable only in the lower-left /
safety-acceptable region; Stage B reports this descriptively.

## Next-level success and oscillation

Next-level success is the complement of the frozen
`next_attempt_support_needed` label for observed assignment-matched outcomes.
Oscillation is a move up followed by a move down, or the reverse, within a
learner/subtopic decision sequence.

## BKT reliability curve

Predicted BKT mastery bands against observed next-level success. Bands with
fewer than five observations are labelled `insufficient` and must not be
plotted as reliable.

## Transition matrices

Per-arm Easy/Moderate/Hard movement counts with unassigned decisions reported
separately.

## Decision audit table

Pseudonymized decision rows with reason codes, selected and delivered
difficulty, and later outcome status. Counterfactual mismatches are censored,
never scored. No raw student ID, answer text, answer key, SHAP array, artifact
hash, email, or internal error trace appears here.

## Fairness and censoring

Observed, same-bank, cross-bank, and censored-by-reason counts per arm, plus the
overall censoring summary.

## Limitations

Offline observational replay only; no causal learning-effect claim. The
false-demotion guard (`deltaFD`) is a Stage-C pre-registered gate, not a
Stage-B finding. P3b (model-assisted) results are reported separately from P3a
(BKT-only). Records that are not approved real runtime data are a pipeline
demonstration only.

## Reproducibility

Every plotted aggregate traces to the frozen manifest and dataset hashes. The
report SHA-256 is deterministic for identical inputs.

