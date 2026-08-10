# Adaptive Question Bank Comparison and Selection - ASSISTments External-Real Descriptive Stage B (Final)

Date: 2026-08-09
Final status: **AQC ASSISTMENTS EXTERNAL-REAL DESCRIPTIVE STAGE-B COMPLETE**
Evidence level: **EXTERNAL_DESCRIPTIVE_REPLAY_WITH_LIMITED_MATCHED_OUTCOME_COVERAGE**
Policy superiority: **NOT_ESTABLISHED**
Causal policy benefit: **NOT_ESTABLISHED**
P3a external Stage-B: **BEHAVIORALLY_DIFFERENT_BUT_NOT_PROVEN_SUPERIOR**
Production promotion: **NOT_APPROVED**

## 1. Dataset and provenance

- Dataset: **ASSISTments EDM Cup 2023** (Kaggle release
  `assistments-edm-cup-2023-release-v1`).
- Evidence mode: `external_real_proxy_difficulty`; claim level
  `external_descriptive_replay`.
- Primary cohort: **exact Grade 6 Mathematics** (`Grade 6 Accelerated`
  separate; no Grades 4-6 pooling).
- Provenance: `external_real`; `containsRawIdentifiers: false`;
  `productionPromotionAllowed: false`; raw and learner-level files outside Git.
- Source hashes (J0-verified): action_logs `DB6B0CD4…`, assignment_details
  `D02D8B62…`, problem_details `4F45DAF2…`, sequence_details `A1FA10E6…`;
  J1 normalized rows `20d9514c…`.

## 2. Contract history (pre-result clarifications, not performance tuning)

| Version | Clarification | Reason | Made before |
|---|---|---|---|
| v1 | Initial external adaptive contract | - | - |
| v1.1 | Discrete within-skill tertile boundaries (`floor(n/3)`, `floor(2n/3)`) | v1 did not define n % 3 partition behavior | any proxy-policy result |
| v1.2 | Attempt-purity denominator (all valid graded problems) | v1 did not define treatment of untiered problems in purity | any real P1/P2/P3a result |
| v1.3 | Student-clustered bootstrap + BKT calibration reporting freeze | plan required learner-clustered CIs but did not freeze seed/resamples/sparsity | any matched-outcome value/rate |

All amendments were made before the relevant results existed and are
documented as methodology clarifications, never policy-performance tuning.
Contract hashes: v1 `46997eaf…`, v1.1 `e54085dd…`, v1.2 `d82b5043…`, v1.3
`99897b2a…`.

## 3. E2 - pre-evaluation proxy difficulty calibration

- Calibration window 2019-02-25..2021-12-31; evaluation window
  2022-01-01..2023-12-31; calibration/evaluation learner overlap **0**.
- Independent calibration learners: **77,059** (85,675 possible; 8,616
  evaluation-cohort learners excluded).
- Calibrated problems: **1,051** (1,731 exact-skill eligible; 680
  insufficient-evidence; 18 null-skill excluded); tiered problems **1,041**.
- Skills with calibrated problems: **62**; full 9 / 3+3+3 gate-passing skills:
  **35**.
- Problem tiers (ANALYTICAL PROXY, not native ASSISTments labels):
  proxy_easy **329**, proxy_moderate **350**, proxy_hard **362**.
- Smoothing `p_correct=(correct+1)/(total+2)`; `difficulty_score=1-p_correct`;
  minimum 20 independent learners; within-skill tertiles; catalog gate 9 /
  3+3+3. Catalog hash `fe4cb258…`.

## 4. E3 - 2022-2023 exact-skill reconstruction

- Reconstructed Grade 6 exact-skill attempts: **15,048** (unique learners
  **1,130**; unique skills 79).
- Attempts inside the 35 eligible skills: **12,123**; outside: 2,925.
- Score-valid **15,048 / 15,048**; BKT-valid **15,048 / 15,048**.
- Proxy-tier-valid attempts: **2,187** (proxy_easy 898, proxy_moderate 547,
  proxy_hard 742); mixed/insufficient-tier 7,349; zero-tier 5,512.
- Chronology ambiguity **0**. Attempt hash `b065d1d3…`.

Substantial proxy-coverage limitation: only 2,187 of 15,048 reconstructed
attempts (14.5%) are proxy-tier-valid, and only 2,090 (13.9%) fall inside the
35 eligible skills with a valid tier.

## 5. E4 - Stage-B readiness

- Shared policy-ready states: **2,090**; independent learners **494**; exact
  skills **17**.
- Tiers: proxy_easy 898 (400 learners, 9 skills), proxy_moderate 547 (285, 7),
  proxy_hard 645 (350, 8).
- BKT ready **2,090 / 2,090**; adjacent-tier availability **2,090 / 2,090**;
  previous observed tier 412; cold history 1,678; freshProblemFraction
  2,090/2,090.
- Direct-next audit: **183** valid tier-bearing direct-next pairs, of which
  **165** are structurally one-step policy-matchable (potential UP 20, HOLD
  45, DOWN 100) and **18** are non-adjacent (cannot match the one-level
  envelope). The 183 figure is NOT "183 policy-matchable pairs".
- Decision: READY_FOR_EXTERNAL_POLICY_REPLAY. Readiness manifest hash
  `bf8a0b20…`.

## 6. AQC-A - controlled mechanics regression (pipeline_demo_only)

Verified on deterministic controlled fixtures: P1 threshold (0.79 HOLD / 0.80
UP / no auto-DOWN / upper-bound HOLD), P2 score/BKT agreement and
disagreement holds, P3a BKT-only behavior (support-risk bypassed), one-level
movement, Easy/Hard boundaries, unavailable-tier safety, reversal protection,
cold history, hard-tier evidence guard, future-leakage prevention, one-step
non-propagation, external candidate without native bankId, and claim boundary.
These are mechanics-only (`pipeline_demo_only`) and are never mixed with real
Stage-B performance evidence.

## 7. E5 - real P1/P2/P3a replay (2,090 identical states / 494 learners / 17 skills)

| Policy | UP count/rate | HOLD count/rate | DOWN count/rate |
|---|---:|---:|---:|
| P1 | 728 / 34.83% | 1,362 / 65.17% | 0 / 0% |
| P2 | 691 / 33.06% | 1,319 / 63.11% | 80 / 3.83% |
| P3a | 1,077 / 51.53% | 888 / 42.49% | 125 / 5.98% |

- Agreement: P1-P2 94.40%; P1-P3a 73.78%; P2-P3a 79.38%; three-way 73.78%.
- EB2: P3a HOLD where P1 UP = **37 states / 36 learners / 4 skills** (5.08% of
  P1-UP); P2 HOLD where P1 UP = 37 (5.08%).
- P2 disagreement HOLD = **713 (34.11%)**; P3a guardrail HOLD = **807
  (38.61%)**.
- Shared state hash `66bfb15f…`; decision audit hash `75d9b9bd…`; E5 manifest
  `209750da…`.

Important final interpretation: P3a did NOT simply behave as a more
conservative version of P1. P3a proposed UP on 51.53% of states versus P1's
34.83%. P3a showed a distinct BKT/evidence-guarded decision pattern, including
both additional promotion decisions and guarded holds/demotions depending on
learner state.

## 8. E6 - matched historical outcomes (v1.3)

Structural matching (no outcome values used for decisions):

| Policy | Matched | UP / HOLD / DOWN | Mismatch |
|---|---:|---:|---:|
| P1 | 41 | 10 / 31 / 0 | 124 |
| P2 | 52 | 2 / 31 / 19 | 113 |
| P3a | 45 | 5 / 21 / 19 | 120 |

All policies: no-next 1,026; repeat 92; next-tier-missing 789; non-adjacent
18; invalid 0; chronology ambiguous 0 (totals reconcile to 2,090 per policy).

Matched outcomes (frozen U7 `next_attempt_support_needed`, mastery 0.60):

- **UP**: P1 1 support / 9 success (n=10 learners; support rate 10%,
  supportNeededCi [0.0, 0.3]; success rate 90%, successCi [0.7, 1.0]); P2 0/2
  (n=2; 0% / 100%; CIs suppressed, sparse); P3a 2/3 (n=5; 40% / 60%; CIs
  suppressed, sparse).
- **HOLD**: P1/P2 7 support / 24 success (31 matched rows; 77.4% success,
  supportNeededCi [0.091, 0.393], successCi [0.607, 0.909]); P3a 5/16 (21 rows;
  76.2% success, successCi [0.571, 0.952]).
- **DOWN**: P1 not applicable; P2/P3a 6 support / 13 success (19 rows; 68.4%
  success, successCi [0.474, 0.895]).

CI labeling is corrected: the bootstrapped CI is the SUPPORT-NEEDED CI and the
success CI is its exact complement (`successCi = 1 - supportNeededCi` reversed);
sparse subsets (P2/P3a matched-UP) suppress both representations.

Matched-outcome coverage: P1 41/2,090 = 1.96%; P2 52/2,090 = 2.49%; P3a
45/2,090 = 2.15%. Matched-UP coverage: P1 10/728, P2 2/691, P3a 5/1,077.
This is a MAJOR limitation.

EB4 (among historically proxy-tier-matched UP observations): P1 10% support /
90% success; P2 0% / 100%; P3a 40% / 60% - immediately qualified: P1 n=10, P2
n=2, P3a n=5; matched subsets differ by policy; observations were not
randomized to candidate policies; P2/P3a matched-UP CIs are suppressed; rates
cannot establish policy ranking. These are NOT false-promotion rates; no
policy is called safer or better.

## 9. BKT calibration (policy-independent, v1.3)

- Population: **972 rows / 386 learners**; Brier **0.13298**.
- Reliability bands: [0.2,0.4) 60 rows/55 learners, success 0.483; [0.4,0.6)
  14/13, success 0.571; [0.6,0.8) 54/50, success 0.593; [0.8,1.0] 844/362,
  success 0.885; [0.0,0.2) empty/not estimable.
- Observed later success increased monotonically across the non-empty BKT
  mastery bands: descriptive evidence that higher BKT mastery corresponded to
  higher later observed success in this external dataset. This does NOT show
  BKT caused success and is NOT proof P3a is superior.

## 10. Final primary conclusion

**EXTERNAL POLICY REPLAY COMPLETED WITH LIMITED PROXY-TIER OUTCOME COVERAGE.**

P1, P2, and P3a were successfully replayed on identical real external
learner-skill states and produced materially different difficulty-selection
behavior. P3a was not simply more conservative: it proposed UP more frequently
overall while also applying evidence and reversal guardrails in specific
states. Historical assignment-matched outcome coverage was sparse, especially
for UP decisions, and the matched subsets were policy-specific and
observational. Therefore the external Stage-B evidence does NOT establish that
P3a, P2, or P1 is superior. BKT showed useful monotonic descriptive
calibration against later observed success, but this does not establish policy
superiority.

## 11. Policy-selection status

- `policySuperiority`: **NOT_ESTABLISHED**.
- `causalPolicyBenefit`: **NOT_ESTABLISHED**.
- `P3aExternalStageB`: **BEHAVIORALLY_DIFFERENT_BUT_NOT_PROVEN_SUPERIOR**.
- `productionPromotion`: **NOT_APPROVED**.
- `P3b`: **NOT_EVALUATED** (never executed; XGBoost support-risk never used).
- If the existing native Logic Oasis architecture uses P3a as its declared
  candidate/default research policy, that architecture may remain unchanged,
  but this external analysis does NOT prove P3a should be selected for
  production.

## 12. Limitations

- Proxy difficulty is analytically derived, not native ASSISTments difficulty
  and not proven equivalent to Logic Oasis Easy/Moderate/Hard content.
- Only 35 calibrated eligible skills; 17 represented in the final replay.
- Only 2,090 policy-ready states from 15,048 reconstructed attempts; 12,861
  attempts have no current proxy tier; 90% cold-history at E3 (1,678/2,090)
  with limited previous-tier context.
- No native bank availability; no exact fresh-bank equivalence
  (`freshProblemFraction` is only an exposure audit; `included_in_full_policy_equivalence_claim:
  false`).
- Matched outcome coverage ~2% (41/52/45 of 2,090); matched-UP samples
  10/2/5.
- Observational one-step replay; no recursive counterfactual trajectory; no
  causal interpretation.
- External U.S.-curriculum evidence; NOT direct Malaysian KSSR validation; no
  KSSR equivalence claim.
- P3b not evaluated; no production promotion; policy configs/thresholds
  unchanged throughout.
- Documented pre-existing full-suite failure
  `test_report_records_hashes_parameters_and_safe_claim_boundary`
  (line-ending-dependent; reproduced identically on the clean predecessor AQC
  branch; not a Stage-B regression).

## 13. Evidence index

- E1 contract: `docs/evidence/aqc-assistments-external-data-readiness.md`
- E2 calibration: `docs/evidence/aqc-assistments-proxy-difficulty-calibration.md`
- E3 reconstruction: `docs/evidence/aqc-assistments-external-attempt-reconstruction.md`
- E4 readiness: `docs/evidence/aqc-assistments-stage-b-readiness.md`
- AQC-A mechanics: `docs/evidence/aqc-assistments-controlled-mechanics-regression.md`
- E5 replay: `docs/evidence/aqc-assistments-external-policy-replay.md`
- E6 outcomes: `docs/evidence/aqc-assistments-matched-historical-outcomes.md`
- Release record: `docs/evidence/aqc-assistments-stage-b-release-record.md`

The original Stage-C confirmatory hypotheses (H1-H6) remain reserved for the
future controlled live pilot and are unchanged.
