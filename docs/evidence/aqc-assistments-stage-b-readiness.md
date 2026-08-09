# AQC-E4 ASSISTments Stage-B Readiness Audit

Date: 2026-08-09
Stage: **AQC-E4 (readiness / sufficiency / coverage audit)**
Contract: `assistments-adaptive-contract-v1.2` (unchanged)
Decision: **READY_FOR_EXTERNAL_POLICY_REPLAY**

## 1. E1-E3 verification status

All sixteen frozen-lineage checks passed before any readiness analysis:
v1.2 contract hash, v1.1/v1 predecessor history, E2 catalog and manifest
hashes, E3 attempts CSV and manifest hashes, `external_real` provenance,
`containsRawIdentifiers: false`, `productionPromotionAllowed: false`, exact
Grade 6 cohort, 35 fully eligible exact skills, 2/3 purity contract, `bkt-v1`,
one-step non-propagating replay, zero policy output in E1-E3, and the affected
E1/E2/E3/U7 contract tests green.

## 2. Contract v1.2/hash

`assistments-adaptive-contract-v1.2`,
`d82b50432157f9321808dfced5ad7cb55960ce2dbc3501987ab17a23de725955`
(predecessors v1.1 `e54085dd…` and v1 `46997eaf…` preserved).

## 3. E2 catalog hash

`fe4cb2585bae9a8f15ee2802c23dea8270252384ab7e9c5a410d1ff934bd58e9` (frozen;
the only tier source; E4 never recalibrates or re-tiers).

## 4. E3 attempts hash

`b065d1d3cc70fc9086f92f24f998aed62a0d597ac74c1d2b9f385a1c4cd3b6a6` (frozen E3
output, re-verified; E3 manifest `f5a966e9…` binds it).

## 5. Files added

- `ai_pipeline/external_data/assistments/adaptive/readiness_audit.py`
- `ai_pipeline/external_data/assistments/adaptive/run_readiness_audit.py`
- `ai_pipeline/tests/test_assistments_stage_b_readiness.py`
- `docs/evidence/aqc-assistments-stage-b-readiness.md`
- Protected `processed/aqc/e4/e4_readiness_manifest.json` (outside Git).

## 6. Source / provenance / cohort

ASSISTments EDM Cup 2023, release `assistments-edm-cup-2023-release-v1`,
provenance `external_real`, primary cohort exact Grade 6 Mathematics
(`Grade 6 Accelerated` separate), evaluation window
`2022-01-01T00:00:00Z .. 2023-12-31T23:59:59Z`, calibration/evaluation learner
overlap zero.

## 7-11. Current-state intersection funnel

| Step | Attempts | Unique learners |
|---|---:|---:|
| A. All reconstructed attempts | 15,048 | 1,130 |
| B. In the 35 full eligible skills | 12,123 | 1,032 |
| C. Score-valid in eligible skills | 12,123 | 1,032 |
| D. BKT-valid in eligible skills | 12,123 | 1,032 |
| E. Current-proxy-tier-valid in eligible skills | 2,090 | 494 |
| F. Fully shared policy-ready states | **2,090** | **494** |

**G. Unique skills contributing F: 17.** **H.** The intersection was computed
explicitly (2,187 tier-valid attempts overall minus 97 outside the eligible
skills = 2,090 shared states).

## 12-14. Policy-ready tier distribution

| Tier | Attempts | Unique learners | Unique skills |
|---|---:|---:|---:|
| proxy_easy | 898 | 400 | 9 |
| proxy_moderate | 547 | 285 | 7 |
| proxy_hard | 645 | 350 | 8 |

All three tiers are represented by multiple independent learners and multiple
skills; no rebalancing or sampling was applied.

## 15. Adjacent-tier availability

**2,090 / 2,090 states** have full analytical adjacent-tier availability
(every shared state's exact skill is one of the 35 full 3-tier gate-passing
skills); missing: 0; unavailable-tier reasons: none. No catalog/E3
disagreement (any would have been a fail-closed data-integrity blocker).

## 16-18. Structural movement opportunity counts

- States with an UP target tier: **1,445** (898 easy + 547 moderate).
- States with a DOWN target tier: **1,192** (547 moderate + 645 hard).
- HOLD structurally possible: **2,090**.
- Upper boundary (hard): **645**; lower boundary (easy): **898**.

These are data-structure counts only; no policy direction was computed.

## 19. BKT readiness

**2,090 / 2,090** shared states are BKT-valid (494 learners). Evidence bands:
1-4 x509, 5-9 x655, 10-19 x541, 20+ x385; evidence median 10 (Q1 6, Q3 19,
max 107); mastery distribution reported in the manifest. Structural evidence
guards (frozen `bkt-v1` thresholds, not decisions): move-up guard satisfiable
(evidence >= 2) for **2,090** states; hard-tier guard satisfiable (evidence >=
6) for **1,470** states.

## 20-21. Reversal-history readiness

Previous observed tier available: **412** states; no previous tier
(cold history): **1,678** (not an exclusion). Observed history: same-as-
previous 180, one-level change 145, non-adjacent observed history 87,
unresolved/invalid 0.

## 22. freshProblemFraction availability

Available for **2,090 / 2,090** states (null: 0), 494 learners represented;
distribution min 0.0, median/Q1/Q3 1.0, max 1.0. Exposure-audit substitute
only; exact fresh-bank selection is not externally observable.

## 23-28. Direct next eligible episode audit

For the 2,090 shared policy-ready states (same learner + exact skill,
immediate chronological next, no skipping):

| Classification | Count |
|---|---:|
| Valid direct next | 183 |
| No next episode | 1,026 |
| Identical complete problem-set repeat | 92 |
| Next proxy tier missing | 789 |
| Invalid next outcome | 0 |
| Chronology ambiguous | 0 |
| Non-eligible next skill | 0 (fail-closed check passed) |

## 29-32. Potential (structural) tier-match opportunities

| Category | Pairs | Unique learners | Unique skills |
|---|---:|---:|---:|
| potential_up_tier_match | 20 | 18 | 3 |
| potential_hold_tier_match | 45 | 34 | 2 |
| potential_down_tier_match | 100 | 100 | 2 |
| non_adjacent_observed_transition | 18 | 18 | 2 |

Total structurally matchable direct-next pairs: **183**. These are structural
labels only; no policy was run and no outcome value was used.

## 33. Overall censoring burden

Mutually exclusive state censors (all reconstructed attempts denominator
unless noted): outside_full_skill_catalog 2,925 attempts / 705 learners;
no_current_proxy_tier (within eligible skills) 10,033 / 1,011, of which
mixed_proxy_difficulty 6,254 / 640 and zero_tier_coverage 3,779 / 467
(overlapping subsets). Next-episode censors (shared states denominator):
no_next 1,026; next_proxy_tier_missing 789; identical_problem_set_repeat 92;
invalid_next 0; chronology_ambiguous 0; non_adjacent_observed_transition 18
(overlap of valid pairs). No native-bank censor names.

## 34. policyReplayReadiness

**PASS** - 2,090 shared policy-ready states across 494 independent learners
and 17 exact eligible skills with all three proxy tiers, complete BKT and
adjacent-tier availability, and no contract/data-integrity failure.

## 35. matchedOutcomeReadiness

**ADEQUATE** - valid direct-next tier-bearing history exists (183 valid pairs)
with potential tier matches in all three directions (up 20, hold 45, down 100)
plus 18 non-adjacent observed transitions across 494 candidate learners.

## 36. Deterministic E4 manifest/report hash

Protected E4 readiness manifest SHA-256:
`bf8a0b20c94aea98e5b0d66df9ce0efcac1985f039f7b86e8218d3ed2a6c1b9c`.

## 37. Rerun reproducibility

**REPRODUCIBLE** - the E4 audit was executed twice on the identical frozen E3
inputs; the readiness manifest reproduced the identical hash/counts on both
runs (no timestamps or local paths in hashed content).

## 38. Protected-output / governance status

`e4_readiness_manifest.json` in protected `processed/aqc/e4/` (outside Git);
aggregate/hash/config evidence only; `containsRawIdentifiers: false`,
`productionPromotionAllowed: false`, `external_real`; no learner-level export
and no local protected paths.

## 39. Tests/results

New E4 suite `tests.test_assistments_stage_b_readiness`: **27/27 passed** (the
30 required behaviors: funnel/eligibility/score/BKT/tier requirements,
null-previous-tier non-exclusion, per-tier counts, frozen-catalog adjacent
availability, no native fields, same-learner+skill direct-next with no
skipping, no-next/repeat/tier-missing/chronology censors, structural
UP/HOLD/DOWN matches, non-adjacent not a policy match, outcome-value blindness,
no support/success rates, no P1/P2/P3a/P3b/agreement/performance artifacts,
descriptive claim boundary, production non-promotion, deterministic manifest,
and the no-policy source boundary). E1/E2/E3/U7 suites remain green; full
ai_pipeline suite: 360 tests, 1 failure - the documented pre-existing
`test_report_records_hashes_parameters_and_safe_claim_boundary`.

## 40. NEW regressions

**None.**

## 41-43. No policy outputs

P1 = **0**; P2 = **0**; P3a = **0**; P3b = **0**; policy agreement rows =
**0**; policy-specific matched outcomes = **0**; policy-specific performance
metrics = **0**; superiority claims = **0**. No policy selector is imported or
called anywhere in the E4 path (test-enforced), and no outcome VALUE was used
in the readiness decision.

## 44. AQC-A / E5 / E6 / E7 NOT executed

Confirmed. No controlled mechanics regression (AQC-A), no P1/P2/P3a replay
(E5), no matched-outcome analysis (E6), and no final report (E7) were started.

## 45. Final decision

**READY_FOR_EXTERNAL_POLICY_REPLAY**

Driven by: a viable shared policy-ready population (2,090 states / 494
learners / 17 skills / all three tiers), complete structural current inputs
(score, BKT, frozen-catalog proxy tier, adjacent-tier availability), adequate
matched-outcome feasibility (183 valid direct-next pairs with all three
potential match directions), and zero contract/data-integrity/leakage failures.

Per the plan, the next stage is **AQC-A** (controlled mechanics regression),
followed by a separately reviewed **AQC-E5** execution. Neither was started.
