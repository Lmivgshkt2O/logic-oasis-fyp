# AQC-E6 ASSISTments Matched Historical Outcomes (amended by v1.3)

Date: 2026-08-09
Stage: **AQC-E6 (matched historical outcome analysis, completed under
assistments-adaptive-contract-v1.3)**
Status: **OUTCOME ANALYSIS COMPLETE**
Decision: **READY_FOR_AQC_E7**

## 0. Amendment history (v1.2 result preserved)

The first E6 run verified all frozen inputs, computed policy-specific
structural matching and censoring, and correctly STOPPED before any aggregate
outcome rate because the student-clustered descriptive CI configuration was
not frozen. That structural result is preserved. The pre-outcome
statistical-contract clarification `assistments-adaptive-contract-v1.3`
(below) froze the bootstrap and calibration reporting, and E6 outcome analysis
was rerun to completion. No outcome value was read before the amendment.

## 1. v1.2 predecessor hash

`assistments-adaptive-contract-v1.2`,
`d82b50432157f9321808dfced5ad7cb55960ce2dbc3501987ab17a23de725955` (preserved,
with v1 `46997eafâ€¦` and v1.1 `e54085ddâ€¦` also preserved).

## 2. v1.3 hash

`assistments-adaptive-contract-v1.3`,
`99897b2ac9486b3f725f549e3547f5905b0ba19980b9981f8c7bdffaa9815b77`.

## 3. Amendment rationale

`external_stage_b_descriptive_cluster_bootstrap_and_calibration_reporting_freeze`.
The plan required student-clustered descriptive CIs and BKT calibration
reporting for E6, but the statistical/reporting parameters were not
numerically specified before E6. v1.3 freezes only those parameters; every
other frozen rule is unchanged.

## 4. No outcome values existed before the amendment

Confirmed: `outcomeValuesInspectedBeforeAmendment = false`,
`policyOutcomeRatesExistedBeforeAmendment = false`,
`motivatedByPolicyPerformance = false`. Only structural matched/censor counts
existed before the amendment.

## 5. Bootstrap unit

`externalStudentKey` (learner clusters; rows of one learner never split across
bootstrap units).

## 6. Resample count

**2000** bootstrap replicates.

## 7. Seed

**20260716** (frozen; identical for P1/P2/P3a; never retried).

## 8. CI level / method

**95%**, percentile interval, `learner_cluster_with_replacement` (sample the
same number of learner clusters with replacement; include all rows of each
sampled learner, duplicated when sampled multiple times; never resample
individual rows independently).

## 9. Sparse-CI threshold / rule

`minimumIndependentLearnersForCI = 10` (project-defined conservative
descriptive reporting guard, not a universal statistical theorem). <10
learners: raw numerator/denominator/rate + learner count reported, CI
suppressed as `sparse_independent_learner_evidence`; 0 learners: not
estimable; 1 learner: raw count/rate allowed, CI suppressed. Repeated rows from
one learner never count as independent clusters.

## 10. BKT calibration band source/version

Reused the authoritative AQC-3 reliability curve
(`evaluation/visualizations.py`, `aqc3-bkt-reliability-bands-v1`): bands
[0.0,0.2), [0.2,0.4), [0.4,0.6), [0.6,0.8), [0.8,1.0] with 1.0 in the highest
band; `minimumCalibrationObservations = 5`. Brier score declared;
calibration-error formula not previously declared (recorded as absent; Brier +
reliability table are sufficient).

## 11. Matching rules unchanged

Same learner + exact skill, immediate chronological next, no skipping, target
tier must equal next observed tier, mismatch/no-next/repeat/tier-missing/
non-adjacent censoring unchanged (verified identical to v1.2 by tests).

## 12-14. P1/P2/P3a matched outcomes

- P1: matched **41** (UP 10, HOLD 31, DOWN 0), 31 learners, 4 skills; censors:
  mismatch 124, no-next 1,026, repeat 92, next-tier-missing 789, non-adjacent
  18.
- P2: matched **52** (UP 2, HOLD 31, DOWN 19), 47 learners, 5 skills; censors:
  mismatch 113 (+ same structural censors).
- P3a: matched **45** (UP 5, HOLD 21, DOWN 19), 45 learners, 5 skills; censors:
  mismatch 120 (+ same structural censors).

## 15. Matched UP/HOLD/DOWN results

Matched HOLD: P1 31 (7 support / 24 success, 77.4% success, CI [0.091,0.393],
26 learners), P2 31 (same row set: 7/24, CI [0.091,0.393], 26 learners), P3a
21 (5/16, 76.2%, CI [0.048,0.429], 21 learners).

Matched DOWN: P1 0 (P1 never demotes); P2 19 (6/13, 68.4% success, CI
[0.105,0.526], 19 learners); P3a 19 (same row set: 6/13, CI [0.105,0.526]).

Matched UP: P1 10 (1 support / 9 success, 90.0% success, CI [0.0,0.3], 10
learners); P2 2 (0/2, 100% success, sparse CI suppressed, 2 learners); P3a 5
(2/3, 60.0% success, sparse CI suppressed, 5 learners).

## 16. EB4

Among proxy-tier-matched observations, proposed-UP support-needed vs
later-success rates: P1 1/10 (10.0% support) vs 9/10 (90.0% success); P2 0/2
(0%) vs 2/2 (100%); P3a 2/5 (40.0%) vs 3/5 (60.0%). Descriptive only; matched
subsets are policy-specific, small, and observationally different; no policy
ranking is made.

## 17. Which CIs were computed

P1 matched-UP (10 learners), P1 matched-HOLD (26), P2 matched-HOLD (26), P2
matched-DOWN (19), P3a matched-HOLD (21), P3a matched-DOWN (19), and all
non-empty BKT reliability bands with >=10 learners. All used the frozen seed
20260716 / 2000 resamples / 95% percentile.

## 18. Which CIs were suppressed

P2 matched-UP (2 learners) and P3a matched-UP (5 learners) -> raw counts/rates
reported with `sparse_independent_learner_evidence`; P1 matched-DOWN and empty
BKT band [0.0,0.2) -> `not_estimable`. No row-level pseudo-independent CI was
invented.

## 19. BKT calibration result

Policy-independent population: **972 rows / 386 learners** (shared states with
a valid direct-next eligible outcome, no repeat/chronology ambiguity). Brier
score **0.13298**. Bands: [0.2,0.4) 60 rows/55 learners, mean mastery 0.260,
success 0.483, CI [0.356,0.607]; [0.4,0.6) 14/13, 0.473, 0.571, CI
[0.308,0.846]; [0.6,0.8) 54/50, 0.692, 0.593, CI [0.455,0.736]; [0.8,1.0] 844/
362, 0.985, 0.885, CI [0.862,0.906]; [0.0,0.2) empty. Calibration is
descriptive; no decision threshold was changed.

## 20. Censoring reconciliation

Per policy, matched + mismatch + no-next + repeat + next-tier-missing +
non-adjacent + invalid(0) + chronology(0) = 2,090 (e.g., P1 41+124+1,026+92+
789+18 = 2,090). Primary reasons are mutually exclusive; totals reconcile.

## 21. Outcome-leakage verification

Test-enforced: mutating a future outcome value cannot change any E5 decision
ID/direction/reason or earlier BKT state; mutating the outcome value of a
MISMATCHED row cannot change any matched aggregate (censored rows' values are
never read).

## 22. Deterministic output hashes

E6 manifest SHA-256 `b9a9d69c5a779cd043639b0616f22fede53dc77da6683befb44edfdb924f37ca`;
protected matched-outcomes CSV SHA-256
`a8e4c195d345e634d2e0eda1f64e034547f987f0a2df91b4b6324f9f346aa8ca`; semantic
matched-outcomes hash `263b5554e2bb49927a0d89e1fedbfecfad9a91299f7997544da0d0c976ebf995`.

## 23. Rerun reproducibility

**REPRODUCIBLE**: the amended E6 outcome analysis ran twice; matched rows,
outcome counts, rates, bootstrap intervals, BKT calibration aggregates,
manifest bytes, and the protected outcome artifact hash were identical on both
runs (no volatile timestamps/local paths in hashed content).

## 24. Tests/results

New v1.3 suite `tests.test_assistments_adaptive_contract_v1_3`: **20/20 passed**
(bootstrap unit/resamples/seed/CI/method, with-replacement clustering,
row-kept-together, same-config-for-all-policies, no superiority interval,
sparse guard, BKT bands frozen before outcomes, 1.0 in highest band, mastery
0.60, matching/censoring unchanged, no-outcome-values-before-amendment,
predecessor binding/history, tamper rejection, no policy selectors, native AQC
still validates). Updated E6 suite `tests.test_assistments_matched_outcomes`:
**36/36 passed** (structural + outcome analysis: <10 learners suppress CI,
>=10 permit CI, repeated rows from one learner don't inflate learner count,
Brier later_success=1 semantics, E6 manifest binds frozen E5 decision audit,
etc.). Full ai_pipeline suite: 470 tests, 1 failure - the documented
pre-existing `test_report_records_hashes_parameters_and_safe_claim_boundary`.

## 25. NEW regressions

**None.**

## 26. E7 NOT executed

Confirmed. No final external report (E7) was started; no policy was ranked and
no production behavior was changed.

## Interpretation

**Matched historical outcome analysis completed with limited proxy-tier
outcome coverage.** Among historically proxy-tier-matched observations,
observed support-needed rates after proposed UP were 10.0% (P1, n=10, CI
[0.0,0.3]), 0.0% (P2, n=2, CI suppressed) and 40.0% (P3a, n=5, CI suppressed).
Matched subsets are policy-specific, small, observationally different, and not
randomized; historical assignment was not generated by the candidate policies;
results are descriptive and non-causal; matched-UP coverage is a major
limitation. No superiority, causality, or false-promotion-prevention claim is
made, and the Stage-C confirmatory `falsePromotionBurden` is not computed.

## Final decision

**READY_FOR_AQC_E7** - E5 decisions remain frozen, candidate target matching is
correct with no skipping, unmatched rows are censored without outcome use,
only matched rows attach outcomes, the outcome definition is frozen (U7
`next_attempt_support_needed`, mastery 0.60), BKT calibration is valid and
bounded, censoring reconciles, outputs are reproducible, no regression exists,
and the claim remains descriptive/non-causal (`external_descriptive_replay`).
The final E7 report is the next stage and was not started.
