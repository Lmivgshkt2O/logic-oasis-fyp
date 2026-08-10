# AQC-A ASSISTments Controlled Mechanics Regression

Date: 2026-08-09
Stage: **AQC-A (controlled mechanics regression)**
Contract: `assistments-adaptive-contract-v1.2` (unchanged)
Evidence mode: **pipeline_demo_only**
Decision: **READY_FOR_AQC_E5**

## 1. E4 readiness verification

The frozen E4 decision is `READY_FOR_EXTERNAL_POLICY_REPLAY` (policy replay
PASS, matched-outcome adequate): 2,090 shared policy-ready states / 494
learners / 17 exact skills / all three proxy tiers. AQC-A does not use any
real-data count to tune a rule; it verifies mechanics on controlled fixtures
only.

## 2. Contract v1.2/hash

`assistments-adaptive-contract-v1.2`,
`d82b50432157f9321808dfced5ad7cb55960ce2dbc3501987ab17a23de725955`
(predecessors v1.1 `e54085dd…`, v1 `46997eaf…` preserved).

## 3. Existing AQC policy bundle/hash

The fixtures run through the authoritative AQC-1 selectors
(`logic_oasis_ai.policy_evaluation.select_policy_decision`) with the frozen
`adaptive_policy_v1.yaml` (SHA-256
`1b53aef77a8027b4256f915663ee894225c17efe4f876bff2e23a38ed17eef16`) and
`policy_evaluation_v1.yaml` (SHA-256
`a12d251e5910a034c081950a8bede8dc7753329db0e9c540af108143e9a43a61`).

## 4. Fixture evidence mode

All fixture evidence is labelled **pipeline_demo_only**. The selectors'
decision audit claim labels come from the frozen AQC manifest (controlled
study arms); the AQC-A evidence mode is explicitly `pipeline_demo_only` and
never `external_descriptive_replay`, `external_real`, `superiority`,
`causal_effect`, `KSSR_validated`, or `production_validated`.

## 5. Fixture count

15 controlled scenarios (S1..S15), each run through the same
`EvaluationDifficultyOption -> selector` boundary E5 will use. No real
ASSISTments learner rows were read or used for policy outcomes.

## 6-9. P1 / P2 / P3a mechanics

- P1: score 0.79 -> HOLD (`p1_score_hold`); score 0.80 -> UP one tier
  (`p1_score_promote`); never auto-DOWN; at Hard with score >= 0.80 -> HOLD
  (`difficulty_upper_bound_hold`).
- P2: score UP + BKT UP -> UP (`p2_agreement_promote`); score DOWN + BKT DOWN
  -> DOWN (`p2_agreement_demote`); score UP/DOWN with BKT neutral or
  disagreeing -> HOLD (`p2_disagreement_hold`); 0.80/0.40 boundaries frozen.
- P3a: BKT-only (`bkt_only_study`, `usedBktFallback: true`); support-risk/
  XGBoost inference bypassed (P3a with support-risk evidence still returns the
  BKT-only decision); evidence guard (evidence 1 -> guarded HOLD
  `p3_stay_build_evidence`; evidence 3 -> permitted one-level UP
  `p3_move_up_bkt_fallback`); reversal protection (`anti_oscillation_hold`);
  cold history valid. P3b was not run.

## 10-14. Boundaries, unavailable tier, reversal, cold history, hard guard

- One-level movement enforced: P1 at Easy with a perfect score selects
  Moderate (never Hard); no two-level jump occurs in any fixture.
- Lower boundary: Easy cannot move below Easy; upper boundary: Hard cannot
  move above Hard (safe HOLD with `difficulty_upper_bound_hold`).
- Unavailable adjacent tier: with the Moderate external candidate marked
  unavailable, P1 UP at Easy -> HOLD (`no_eligible_bank`) at Easy; no fallback
  fabricates a native bank (selected identity remains `external:external_proxy_*`).
- Reversal guard: observed prior move-up + current DOWN request -> HOLD
  (`anti_oscillation_hold`), using observed-history context only (never a prior
  simulated policy decision).
- Cold history (`previousObservedProxyDifficulty = null`) remains fully valid:
  the state is not excluded and the policy decides from current evidence.
- Hard-tier evidence guard: movement toward Hard with insufficient evidence is
  guarded per the frozen rule (P2/P3a hard guard verified in E1/E2 suites and
  fixture S4 uses sufficient evidence to permit the move).

## 15. Fresh-bank limitation handling

AQC-A does not claim exact ASSISTments fresh-bank equivalence. External states
carry `freshProblemFraction` (an exposure-audit substitute); no fake bank
history is created, and the frozen limitation remains
`exact_external_observability: unavailable`,
`included_in_full_policy_equivalence_claim: false`. The production selector's
native fresh-bank behavior is not fabricated for the external path.

## 16-17. Future leakage and one-step non-propagation

- Future leakage: an earlier decision recomputed from an unchanged earlier
  context is identical (direction, reason, decision ID) even after a future
  state with more evidence/exposure is constructed. Future correctness, BKT
  evidence, proxy tier, outcome, and exposure never leak backward.
- One-step non-propagation: a historical Moderate state where P1 would propose
  Hard is followed by a later OBSERVED Moderate state; the later state is
  reconstructed from the observed Moderate history (not the counterfactual
  Hard) and yields the correct HOLD decision.

## 18. External candidate / no-bankId

External candidates use `candidateKind = external_proxy_tier`,
`nativeBankId = null`, and a namespaced `externalCandidateKey`
(`external_proxy_*`). The selector bridge uses that namespaced key as the
identity slot; no native bankId is fabricated, and movement across
Easy/Moderate/Hard is fully expressible.

## 19. Native runtime parity/regression status

The same fixture contexts run with native `native_bank` candidates produce
identical directions, reason codes, and selected difficulties as the external
path (parity proven by tests). The native runtime policy files and selectors
are unchanged.

## 20. Claim-boundary test

Controlled fixtures cannot produce `external_descriptive_replay`,
`superiority`, `causal_effect`, `KSSR_validated`, or `production_validated`;
the AQC-A evidence mode is `pipeline_demo_only`, and `productionPromotionAllowed`
remains false.

## 21. Determinism / rerun result

All fixtures run twice with identical decision IDs, directions, reason codes,
audit metadata, and claim metadata. Deterministic fixture-output hash:
`c68d60d890a0199b5d42911230bfe8a488b3150670d23ebce2006df24bd425d6`.

## 22. Tests executed/results

New AQC-A suite `tests.test_assistments_controlled_mechanics`: **24/24 passed**
(all 27 required behaviors: P1 0.79/0.80/upper-boundary/no-auto-DOWN, P2
0.80/0.40 boundaries and agreement/disagreement, P3a BKT-only/evidence
guard/reversal/cold history, one-level and non-adjacent movement, unavailable
external tier, no-native-bankId, no fabrication, freshProblemFraction naming,
future leakage, one-step non-propagation, pipeline_demo_only claim, forbidden
claim rejection, production non-promotion, native parity, deterministic
rerun). E1-E4/U7 suites remain green; full ai_pipeline suite: 384 tests, 1
failure - the documented pre-existing
`test_report_records_hashes_parameters_and_safe_claim_boundary`.

## 23. New regressions

**None.**

## 24. No real ASSISTments policy replay

Confirmed. No real P1/P2/P3a/P3b decision was computed on real ASSISTments
rows; real policy agreement rows = 0; real matched policy outcomes = 0.
Fixture decisions exist only in `pipeline_demo_only` controlled evidence.

## 25. E5/E6/E7 NOT executed

Confirmed. No real policy replay (E5), no matched-outcome analysis (E6), and
no final external report (E7) were started.

## 26. Final decision

**READY_FOR_AQC_E5** - policy mechanics verified on controlled fixtures with
no contract change and no regression. Real P1/P2/P3a replay (E5) is the next
stage and requires separate review before execution.
