# AQC-E6 ASSISTments Matched Historical Outcomes (structural + gated)

Date: 2026-08-09
Stage: **AQC-E6 (matched historical outcome stage)**
Contract: `assistments-adaptive-contract-v1.2` (unchanged)
Status: **VERIFICATION + STRUCTURAL MATCHING COMPLETE; OUTCOME ANALYSIS GATED**
Decision: **NOT READY FOR E6 OUTCOME ANALYSIS - student-clustered descriptive
CI configuration not frozen** (equivalently: NOT_READY_FOR_AQC_E7 until the
narrow pre-outcome statistical-contract clarification is approved).

## 1. E1-E5 verification

All frozen-input checks passed before any outcome work: contract v1.2 hash
`d82b5043…`, v1/v1.1 predecessor history, E2 catalog hash `fe4cb258…`, E3
attempts hash `b065d1d3…`, E4 readiness manifest hash `bf8a0b20…`, E5 manifest
hash `209750da…`, E5 decision audit hashes (below), P1/P2/P3a row parity
(2,090 each), `external_real`, `containsRawIdentifiers: false`,
`productionPromotionAllowed: false`, `p3bExecuted: false`, and no E5 future
outcome usage.

## 2. Contract v1.2/hash

`assistments-adaptive-contract-v1.2`,
`d82b50432157f9321808dfced5ad7cb55960ce2dbc3501987ab17a23de725955`.

## 3. E5 decision audit / manifest hashes (hash-naming resolved)

- `decisionAuditHash` = `75d9b9bdece8f410b787d68d7f7e99c3fb8405785bf142380683d704ff2907ab`
  (canonical/semantic hash of the E5 decision-row documents).
- `decisionAuditFileSha256` = `067da4bc0dacf0510db52d5688bdecd5112a54ed19e1f2abf3dd485a0379b412`
  (physical SHA-256 of the protected decision-audit CSV bytes).
- E5 manifest hash = `209750da34bc7fed5660ea6aa1ae3b0bbdd7cb9c75292ffe46204a9e06316c77`.

These are **intentionally two distinct hashes** (semantic vs physical), both
explicitly named and mutually consistent (the E5 manifest binds the semantic
decisionAuditHash and the E5 reproducibility item reports the physical file
hash). No inconsistency exists; both are recorded with explicit names.

## 4. U7 outcome-contract version/hash

`PREDICTION_TARGET = next_attempt_support_needed`,
`PREDICTION_LABEL_VERSION = next-attempt-support-needed-v1`, mastery criterion
`0.60` (authoritative `logic_oasis_ai.prediction_contract`, consistent with the
U7 J2-v2 external contract and manifests). No repository authority conflicts
with the frozen U7 evidence.

## 5. Frozen outcome definition

`support_needed = next_attempt_support_needed == true` (next direct eligible
exact-skill episode `correct_rate < 0.60`); `later_success = NOT
support_needed`. The adaptive 0.80 promotion threshold is NOT the outcome
criterion (test-enforced).

## 6. Mastery criterion

`0.60` (frozen; unchanged).

## 7. Direct-next matching rule

For every E5 decision: load current state + proposed target tier -> identify
the direct next eligible historical episode (same externalStudentKey + same
exact sourceSkillCode, immediate chronological, no skipping) -> structural
censor checks -> compare ONLY the next observed proxy tier -> mismatch censors
`counterfactual_proxy_tier_mismatch` (outcome value never read) -> only an
exact tier match may attach the frozen outcome. HOLD target = current tier; UP
target = one adjacent higher; DOWN target = one adjacent lower; non-adjacent
observed transitions can never match the one-level envelope.

## 8. E4 future-structure reconciliation

The structural matching reconciles with E4: 183 valid tier-bearing direct-next
pairs, of which 165 are adjacent/HOLD structurally policy-matchable and 18 are
non-adjacent (censored for every policy as `non_adjacent_observed_transition`).
Policy-specific matched subsets are drawn only from the 165 structurally
matchable pairs; the same historical transition can match some policies and
censor others (expected; no equalization).

## 9-11. P1/P2/P3a matched/censored totals (structural; no outcome values)

| Policy | Total | Matched | Tier mismatch | No next | Repeat | Next-tier missing | Non-adjacent | Invalid/chronology |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P1 | 2,090 | 41 | 124 | 1,026 | 92 | 789 | 18 | 0 |
| P2 | 2,090 | 52 | 113 | 1,026 | 92 | 789 | 18 | 0 |
| P3a | 2,090 | 45 | 120 | 1,026 | 92 | 789 | 18 | 0 |

All rows reconcile to 2,090 per policy (e.g., P1: 41+124+1,026+92+789+18 =
2,090). Matched learners/skills: P1 31 / 4; P2 47 / 5; P3a 45 / 5.

## 12-14. Matched UP/HOLD/DOWN structural counts

- P1: matched UP **10**, HOLD **31**, DOWN **0** (P1 never demotes).
- P2: matched UP **2**, HOLD **31**, DOWN **19**.
- P3a: matched UP **5**, HOLD **21**, DOWN **19**.

## 15. EB4 result by policy

**NOT COMPUTED** - EB4 requires support-needed/success outcome rates, which are
gated (see section 20). Structural matched-UP counts above are the denominators
that EB4 would use.

## 16-18. Matched-outcome coverage (structural)

- Matched outcome coverage (matched / 2,090): P1 **1.96%**, P2 **2.49%**, P3a
  **2.15%**.
- Matched-UP coverage (matched UP / policy UP decisions): P1 10/728, P2
  2/691, P3a 5/1,077.
- Matched-HOLD coverage: P1 31/1,362, P2 31/1,319, P3a 21/888; matched-DOWN:
  P1 0/0, P2 19/80, P3a 19/125.
- Independent learner/skill denominators: reported per policy above.

## 19. Policy-specific matched-subset composition

Structural composition (no outcome values): P1 41 matched (10 up / 31 hold / 0
down) across 31 learners and 4 skills; P2 52 (2 up / 31 hold / 19 down) across
47 learners and 5 skills; P3a 45 (5 up / 21 hold / 19 down) across 45 learners
and 5 skills. Matched subsets are policy-specific and observationally
different; no post-hoc balancing was applied.

## 20. Student-clustered descriptive CIs - BLOCKER

**No approved/frozen student-clustered bootstrap configuration exists for the
external Stage-B matched-outcome rates.** The existing AQC-2/AQC-3 bootstrap
(`evaluation/metrics.py`) is native/outcome-bound with a per-run seed and is
not frozen for the external path; no E1-E5 manifest or contract freezes a
seed/iterations/CI method for E6. Per the frozen E6 gate, E6 therefore STOPPED
before computing or viewing ANY aggregate outcome rate.

**Exact blocker: student-clustered descriptive CI configuration not frozen.**

Recommended next step: a narrow, separately reviewed pre-outcome
statistical-contract clarification (e.g., freeze `bootstrap_seed`,
`bootstrap_iterations = 2000`, `confidence_level = 0.95`, cluster key
`externalStudentKey`) before any outcome-rate computation. The E6 matching
code is implemented, verified, and outcome-value-free, so only the CI
configuration needs freezing before outcome analysis.

## 21. CI suppressions/instability

Not applicable yet (gated). Once a frozen config exists, sparse matched-UP
subsets (P1 10, P2 2, P3a 5 matched-UP pairs) will be reported with raw
counts/rates and CI marked unavailable/unstable where independent learners are
too few; no pseudo-independent row-level intervals will be invented.

## 22-23. BKT calibration

**NOT COMPUTED** - BKT calibration requires later-outcome values and shares the
same frozen statistical-contract gate. It remains a policy-independent E6
analysis to be run after the clarification; it will use current frozen BKT
mastery only (never feeding later outcomes back into earlier BKT states).

## 24. Complete censoring table

Primary mutually exclusive censors per policy (counts in section 9-11): no
`no_next_eligible_attempt` 1,026; `next_proxy_tier_missing` 789;
`identical_problem_set_repeat` 92; `non_adjacent_observed_transition` 18;
`counterfactual_proxy_tier_mismatch` 124/113/120 (P1/P2/P3a);
`invalid_next_outcome` 0; `chronology_ambiguous` 0. All rows have exactly one
primary reason; totals reconcile to 2,090 per policy. No native-bank censor
names.

## 25-29. Censoring burden

Counterfactual mismatch burden: P1 124 (5.93%), P2 113 (5.41%), P3a 120
(5.74%). No-next burden: 1,026 (49.09%) per policy. Repeat burden: 92 (4.40%).
Next-tier-missing burden: 789 (37.75%). Non-adjacent burden: 18 (0.86%). These
dominate the censoring table and are structural, not outcome-based.

## 30. Outcome leakage verification

Test-enforced: E6 never recomputes policy decisions; mutating a future outcome
value cannot change any E5 decision ID/direction/reason or earlier BKT state;
mutating the outcome value of a MISMATCHED row cannot change any matched
aggregate (the row remains censored and its value is never read).

## 31. Deterministic output hash

Protected E6 structural diagnostic SHA-256:
`85852f742167f385135ad26f07e4546be5af0257746e84fcdbb8447c5b0e52d9`.

## 32. Rerun reproducibility

The verification and structural-matching paths are deterministic (test-
enforced); the E6 structural diagnostic is reproducible. The final E6
outcome/CI reproducibility check will be executed after the statistical-
contract clarification, mirroring E2/E3/E4/E5 rerun protocols.

## 33. Fresh-bank limitation

Unchanged: `freshProblemFraction` exposure audit only; exact fresh-bank
observability unavailable; full-policy-equivalence claim false.

## 34. External-domain / no-KSSR limitation

ASSISTments is an external U.S.-curriculum source; no KSSR validation claim.

## 35. Observational / non-causal limitation

E6 is observational one-step replay. No causal effect, no treatment effect, no
off-policy weighting, no propensity adjustment, no synthetic outcomes, and no
counterfactual outcome for mismatched tiers (mismatch is censored).

## 36. Matched-UP sparsity limitation

Structural matched-UP counts are small (P1 10, P2 2, P3a 5 pairs across 18
structural potential-UP pairs from E4). Even after the clarification, matched-UP
outcome rates will be severely limited; this is reported, not "fixed" by
broadening the cohort, weakening matching, skipping attempts, pooling grades,
or relaxing purity.

## 37. Production non-promotion

`productionPromotionAllowed: false`; no policy selection or production change.

## 38. Tests/results

New E6 suite `tests.test_assistments_matched_outcomes`: **30/30 passed** (all
34 required behaviors: E5 audit immutability, no recomputation, direct-next
same learner+skill, no skipping, target==next-tier requirement, mismatch censor
without outcome use, matched attachment, no-next/repeat/tier-missing/
chronology/non-adjacent censors, HOLD/UP/DOWN target semantics, P1 zero DOWN,
frozen U7 definition (0.60, not 0.80), future-outcome mutation cannot change
E5 decisions, unmatched-outcome mutation cannot change matched aggregates,
policy-specific subset distinctness, no off-policy weighting/synthetic
outcomes, BKT current-only, learner-clustered CI with frozen config,
sparse-CI fail-closed, no P3b/XGBoost, claim/production boundaries, rerun
identity). E1-E5/AQC-A/U7/native suites remain green; full ai_pipeline suite:
443 tests, 1 failure - the documented pre-existing
`test_report_records_hashes_parameters_and_safe_claim_boundary`.

## 39. NEW regressions

**None.**

## 40. E7 NOT executed

Confirmed. No final external report (E7) was started, and no outcome-rate or
policy-ranking work was performed.

## 41. Final readiness decision

**NOT READY FOR E6 OUTCOME ANALYSIS - student-clustered descriptive CI
configuration not frozen** (equivalently NOT_READY_FOR_AQC_E7 until the narrow
pre-outcome statistical-contract clarification is approved and E6 outcome
analysis reruns).

All lineage, hashing, U7 outcome-contract, matching, and censoring gates
passed; the ONLY blocker is the unfrozen student-clustered CI configuration,
and no outcome value was read or aggregated. No policy was ranked and no
production change was made.
