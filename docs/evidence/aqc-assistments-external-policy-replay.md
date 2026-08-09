# AQC-E5 ASSISTments External Policy Replay (P1/P2/P3a, one-step, descriptive)

Date: 2026-08-09
Stage: **AQC-E5 (first real external policy replay)**
Contract: `assistments-adaptive-contract-v1.2` (unchanged)
Claim level: **external_descriptive_replay**
Decision: **READY_FOR_AQC_E6**

## 1. E1-E4/AQC-A verification

All frozen lineage checks passed before replay: v1.2 contract hash, v1.1/v1
predecessors, E2 catalog and manifest hashes, E3 attempts and manifest hashes,
E4 readiness manifest hash (`bf8a0b20…`), 2,090-state shared population,
`external_real`, `containsRawIdentifiers: false`,
`productionPromotionAllowed: false`, and AQC-A controlled mechanics verified
(P1/P2/P3a thresholds/guards, external candidate, no-bankId, claim boundary).

## 2. Contract v1.2/hash

`assistments-adaptive-contract-v1.2`,
`d82b50432157f9321808dfced5ad7cb55960ce2dbc3501987ab17a23de725955`.

## 3. Policy bundle/config hashes

`adaptive_policy_v1.yaml` `1b53aef77a8027b4256f915663ee894225c17efe4f876bff2e23a38ed17eef16`;
`policy_evaluation_v1.yaml`
`a12d251e5910a034c081950a8bede8dc7753329db0e9c540af108143e9a43a61`; P1
`score-threshold-v1`, P2 `bkt-score-agreement-v1`, P3a `guarded-bkt-study-v1`.

## 4. Shared input state hash

`66bfb15f4d59de29eee07774fcf6e6e93ecf7b2230e261cc01da62eac35fda76` (identical
for P1, P2, and P3a; proven by row-parity proof).

## 5-8. Shared population and tier distribution

2,090 shared states / 494 independent learners / 17 exact eligible skills.
Current tiers: proxy_easy 898 (400 learners, 9 skills), proxy_moderate 547
(285, 7), proxy_hard 645 (350, 8). BKT-valid 2,090/2,090; adjacent-tier
availability 2,090/2,090; previous observed tier 412; cold history 1,678;
freshProblemFraction 2,090/2,090; chronology ambiguity 0.

## 9-11. Direction distributions (denominator 2,090)

| Policy | UP count/rate | HOLD count/rate | DOWN count/rate |
|---|---:|---:|---:|
| P1 | 728 / 34.83% | 1,362 / 65.17% | 0 / 0% |
| P2 | 691 / 33.06% | 1,319 / 63.11% | 80 / 3.83% |
| P3a | 1,077 / 51.53% | 888 / 42.49% | 125 / 5.98% |

Tier-specific: P1 easy 496 up / 402 hold, moderate 232 up / 315 hold, hard 645
hold; P2 easy 496 up / 402 hold, moderate 195 up / 55 down / 297 hold, hard 25
down / 620 hold; P3a easy 692 up / 206 hold, moderate 385 up / 58 down / 104
hold, hard 67 down / 578 hold.

## 12. Decision totals / parity

P1 = P2 = P3a = **2,090 decision rows** (6,270 total), identical state keys,
learners, skills, tiers, and input evidence (row parity exact; input hashes all
equal the shared state hash). No policy-specific subset was created.

## 13-15. Reason codes

- **P1**: `p1_score_promote` 728 (34.83%), `p1_score_hold` 1,006 (48.13%),
  `difficulty_upper_bound_hold` 305 (14.59%), `anti_oscillation_hold` 51
  (2.44%). No unexpected code; P1 never demotes.
- **P2**: `p2_agreement_promote` 691 (33.06%), `p2_agreement_demote` 80
  (3.83%), `p2_disagreement_hold` 713 (34.11%), `p2_neutral_hold` 37 (1.77%),
  `difficulty_upper_bound_hold` 285 (13.64%), `difficulty_lower_bound_hold` 54
  (2.58%), `hard_requires_more_evidence` 110 (5.26%), `anti_oscillation_hold`
  120 (5.74%).
- **P3a**: `p3_move_up_bkt_fallback` 1,077 (51.53%), `p3_stay_hard_mastery`
  559 (26.75%), `p3_stay_easy_support` 55 (2.63%), `p3_stay_target_zone` 81
  (3.88%), `p3_move_down_support` 83 (3.97%), `hard_requires_more_evidence`
  115 (5.50%), `anti_oscillation_hold` 120 (5.74%). All codes are in the frozen
  vocabulary; external candidates remained `external_proxy_*` with
  `nativeBankId = null` throughout (no native-bank-only reason fabricated).

## 16-19. Agreement

- P1 vs P2: **94.40%** (1,973 / 2,090).
- P1 vs P3a: **73.78%** (1,542 / 2,090).
- P2 vs P3a: **79.38%** (1,659 / 2,090).
- Three-way: all three same **73.78%** (1,542); at least one differs 548.

Descriptive only; no superiority test or winner claim.

## 20. P3a HOLD where P1 UP (EB2)

**37 states** (36 learners, 4 skills); 1.77% of all states and 5.08% of the 728
P1-UP states. Wording: "P3a restrained a P1 promotion proposal on 37 states."
Not called prevented false promotions (no future outcome evaluated).

## 21. P2 HOLD where P1 UP

**37 states** (1.77% of all states; 5.08% of P1-UP states).

## 22. P2 disagreement HOLD count

**713 states (34.11%)** with `p2_disagreement_hold` (score and BKT directions
disagree); EB3 measurable. Not interpreted as better/worse.

## 23. P3a guardrail HOLD count

**807 states (38.61%)** with guard/boundary/evidence hold reasons (definition:
P3a HOLD with reason in {p3_stay_build_evidence, anti_oscillation_hold,
hard_requires_more_evidence, p3_stay_easy_support, p3_stay_hard_mastery,
difficulty_upper/lower_bound_hold, no_eligible_bank}). Full reason distribution
is reported above.

## 24. Proposed reversal-signal summary

Among the 412 states with observed previous-tier context: same-tier no observed
movement 180; directional history 232. P1: same-direction-as-observed 1,
reversal converted to HOLD 51, no movement 180, immediate unguarded reversal 0;
P2: 1 / 120 / 111 / 0; P3a: 7 / 120 / 105 / 0. Observed history only; no
recursive simulated oscillation.

## 25. Challenge opportunity

`descriptive_challenge_opportunity` is **not exactly observable**: the frozen
AQC manifest names the metric but no operational formula is implemented for the
external decision replay, so none was invented after seeing decisions.

## 26. Learner/skill/tier coverage

Every policy covered 494 learners, 17 exact skills, and all three current
tiers; no state was dropped for any single policy.

## 27. Descriptive confidence intervals

Raw descriptive rates with independent-learner counts are reported above
(e.g., P1 UP 728/2,090 states across 327 learners). No approved
student-clustered CI configuration exists for E5 decision-direction rates (the
frozen AQC-2 bootstrap is outcome-bound for E6), so no new statistical
methodology was invented.

## 28. Protected decision-audit hash

`75d9b9bdece8f410b787d68d7f7e99c3fb8405785bf142380683d704ff2907ab`
(`external_policy_decisions_v1.csv`, 6,270 rows, outside Git).

## 29. Rerun reproducibility

**REPRODUCIBLE**: E5 ran twice; decision audit CSV hash
`067da4bc0dacf0510db52d5688bdecd5112a54ed19e1f2abf3dd485a0379b412` and E5
manifest hash `209750da34bc7fed5660ea6aa1ae3b0bbdd7cb9c75292ffe46204a9e06316c77`
were identical on both runs (no timestamps/local paths in hashed content).

## 30. Claim level

`external_descriptive_replay` (real external learner states, E4 passed, all E5
integrity gates passed). Never `superiority` / `causal_effect` /
`KSSR_validated` / `production_validated`.

## 31. Fresh-bank limitation

`freshProblemFraction` exposure audit only; `exact_external_observability:
unavailable`; `included_in_full_policy_equivalence_claim: false`; no fake bank
history.

## 32. External-domain / KSSR boundary

ASSISTments is a U.S.-curriculum external source; this replay is not direct
Malaysian KSSR validation and makes no such claim.

## 33. Production non-promotion

`productionPromotionAllowed: false`; no production policy selection or change
was made. P1/P2/P3a behavior differences are reported descriptively only.

## 34. Tests/results

New E5 suite `tests.test_assistments_external_policy_replay`: **29/29 passed**
(all 33 required behaviors: frozen shared-state set, P1/P2/P3a receive all
rows, identical row keys/input hashes, frozen 0.80/0.40 boundaries, P2
disagreement hold, P3a BKT-only/evidence-guard/reversal/cold history, one-level
movement, bounds, external candidates null-bankId, no bankId fabrication,
observed-history-only reversal, one-step non-propagation, no future outcome
usage, no P3b/XGBoost loading, deterministic IDs/reason codes/audit hash,
agreement on identical pairs, no controlled-demo leakage, claim level,
no-superiority, production non-promotion). E1-E4/AQC-A/U7/native suites remain
green; full ai_pipeline suite: 413 tests, 1 failure - the documented
pre-existing `test_report_records_hashes_parameters_and_safe_claim_boundary`.

## 35. NEW regressions

**None.**

## 36-38. No future outcomes / no P3b / no XGBoost

Future support-needed labels used = **0**; future success/failure values used =
**0**; policy-specific matched outcomes = **0**; counterfactual tier matching
for outcomes = **0** (E6 territory). P3b decisions = **0**; XGBoost
support-risk calls = **0**; no U7 artifact loaded into P3a.

## 39. E6/E7 NOT executed

Confirmed. No matched-outcome layer (E6) and no final external report (E7)
were started.

## 40. Final decision

**READY_FOR_AQC_E6** - all three policies ran on identical 2,090 frozen states
with exact row parity, frozen configurations, no future outcome leakage, no
P3b/XGBoost, reproducible outputs, claim level `external_descriptive_replay`,
and no new regression. The E6 matched-outcome layer is the next stage and was
not started; no policy was selected.
