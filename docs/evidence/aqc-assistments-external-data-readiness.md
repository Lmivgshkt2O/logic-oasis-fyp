# AQC-E1 ASSISTments External-Data Readiness and Contract Freeze

Date: 2026-08-08
Stage: **AQC-E1 (contract / governance / schema freeze only)**
Contract: `assistments-adaptive-contract-v1`
Config: `ai_pipeline/external_data/assistments/adaptive/assistments_adaptive_contract_v1.yaml`
Status: **FROZEN; E2 NOT EXECUTED**

## 1. Dataset selected

- Dataset: **ASSISTments EDM Cup 2023** (Kaggle competition release).
- Release ID: `assistments-edm-cup-2023-release-v1`.
- Usage terms: ASSISTments Data Terms of Use, effective 2020-10-30
  (non-commercial academic/research use, citation required, no
  de-anonymization, no redistribution).
- Verified raw source hashes (J0, 2026-08-07): `action_logs.csv`
  `DB6B0CD4875488D0847D9D9BA2896552F4AD1015F3E2388995222DD4A178443D`;
  `assignment_details.csv`
  `D02D8B62DE088C896FCEB901BC986C25FA07F5D9AEEC0364BF9D351208BEC70E`;
  `problem_details.csv`
  `4F45DAF2E010771C6B5E523DD4D583F3AC451F6CE8F2F35270FCB86B875CEE4E`;
  `sequence_details.csv`
  `A1FA10E6DEBD4FD30C4B04E1554E18F2C426A981BCB10BED0B41DD083CCDB541`.
- Verified normalized release (J1): `external_action_rows_v1.csv` SHA-256
  `20d9514cabb4b23de0b2a0a4afdc36661ba30d5936aeb1a7950682d6af1ea378`.
- Raw files and learner-level derived files remain **outside Git** in the
  protected external-data directory.
- Provenance: `external_real`; the ASSISTments source is **never** represented
  as native Logic Oasis runtime data.

## 2. Source fit

The source fit is the **external proxy-difficulty pathway**: real external
learner data, externally reconstructed learner-skill histories, analytically
calibrated proxy difficulty, and non-causal descriptive Stage-B replay.

The ASSISTments release contains **no native Logic Oasis difficulty or bank
metadata**. No `finalizationStatus`, `validationStatus`,
`dataSource=runtime_callable`, native `sourceAttemptSequence`, Logic Oasis
`bankId`, `questionBanks.version`/`isActive`, `contentVersionId`, native
adaptive-assignment ID, or native historical policy version may be fabricated
for these rows. Policy/evaluation versions exist only as analysis metadata in
the frozen evaluation manifest, never as ASSISTments source metadata.

Evidence mode: `external_real_proxy_difficulty`, distinct from
`native_runtime`, `pipeline_demo_only`, `controlled_demo`, and future
Stage-C/live-pilot evidence.

## 3. Cohort and attempt unit

- Primary cohort: **exact Grade 6 Mathematics** (`sourceGrade == "6"` AND
  `sourceSubject == "Mathematics"`). `Grade 6 Accelerated` stays separate and
  is never merged into the primary cohort; secondary grades never silently
  replace Grade 6.
- Prediction/reconstruction unit (reuses the approved U7-v2 semantic unit):
  **one externalStudentKey + one completed externalAssignmentKey + one exact
  non-null sourceSkillCode**. Skills are never mixed inside one reconstructed
  external adaptive attempt.

## 4. Time separation (frozen)

| Purpose | Window |
|---|---|
| Difficulty calibration | `2019-02-25T00:00:00Z` through `2021-12-31T23:59:59Z` |
| External policy evaluation | `2022-01-01T00:00:00Z` through `2023-12-31T23:59:59Z` |

The windows do not overlap, and the contract explicitly guarantees that **no
2022-2023 policy-evaluation correctness outcome may be used to determine the
frozen problem-difficulty mapping**. Calibration is preferred on pre-2022
learners disjoint from the 2022-2023 evaluation cohort; if that is not
feasible, the E2 gate must stop and record a versioned amendment before any
P1/P2/P3a results are produced.

## 5. Proxy methodology (frozen, not executed)

- Problem-level smoothing rule:
  `p_correct = (correct_responses + 1) / (total_graded_responses + 2)`;
  `difficulty_score = 1 - p_correct`.
- Minimum independent calibration learners per problem: **20**
  (below this: `calibrationStatus = insufficient_problem_evidence`,
  `proxyDifficulty = null`).
- Within-skill proxy tiers, assigned only inside one exact `sourceSkillCode`:
  highest p(correct) third -> `proxy_easy`; middle -> `proxy_moderate`;
  lowest -> `proxy_hard`. Deterministic ordering/tie handling is frozen
  (descending p(correct), then ascending problem key; stable tertile rank
  boundaries), so identical inputs reproduce identical tier hashes.
- These are **analytical proxy tiers**, never labelled as native
  "ASSISTments Easy/Moderate/Hard".
- Skill-catalog gate: at least **9 calibrated problems** per exact skill and
  at least **3 proxy_easy / 3 proxy_moderate / 3 proxy_hard**; otherwise
  `skillProxyStatus = insufficient_skill_catalog`. No silent pooling of
  unrelated skills.
- Attempt-tier purity rule: dominant proxy-tier fraction >= **2/3**;
  otherwise `currentProxyDifficulty = null` with
  `censorReason = mixed_proxy_difficulty`.
- External tier availability is **proxy-tier catalog availability** (the exact
  skill has a valid frozen calibrated catalog for the adjacent tier), not
  historical ASSISTments bank availability. Missing adjacent tier -> safe
  HOLD with `external_proxy_tier_unavailable`.
- Problem-set fingerprint:
  `SHA256(sourceSkillCode + sorted(valid problem keys))`, used only for
  identical-repeat detection, exposure auditing, and same/different
  problem-set context. It is **never exposed as a native bankId**.
- E1 freezes this methodology **without executing it**. No calibration counts,
  tier catalogs, attempt reconstructions, or policy results exist yet.

## 6. Replay semantics (frozen)

- `replayMode = one_step_non_propagating`: for each real historical state at
  time t, ask P1, P2, and P3a what they would propose, record the proposals,
  and do not alter the learner's later observed history. The next decision
  state is always reconstructed from actual historical ASSISTments history.
- `reversalHistorySource = observed_proxy_difficulty_history`; previous
  simulated/counterfactual policy outputs are never fed recursively into later
  states.
- Outcome matching is frozen but not executed: a later observed outcome may be
  attached only when the candidate proposed target proxy tier equals the next
  observed eligible proxy tier; otherwise
  `censorReason = counterfactual_proxy_tier_mismatch`. Additional
  compatibility requires same learner, same exact skill, direct next eligible
  chronological episode, valid next correctness outcome, no chronology
  ambiguity, and no identical complete problem-set repeat. A missing next
  attempt is censored; success/failure is never assumed.

## 7. P1/P2/P3a unchanged

The external branch calls the same authoritative AQC policy
implementation/configuration. P1, P2, and P3a definitions are unchanged:

- P1: `correctCount / totalQuestions >= 0.80` -> UP one level; otherwise HOLD;
  never automatic DOWN; highest available difficulty -> HOLD.
- P2: score direction >= 0.80 UP, <= 0.40 DOWN, otherwise NEUTRAL; delivery
  is BKT UP + score UP -> UP, BKT DOWN + score DOWN -> DOWN, otherwise HOLD.
  Evidence limits, one-level movement, reversal protection, and the Hard-level
  evidence guard are preserved.
- P3a: BKT-only guarded policy that forcibly bypasses support-risk/XGBoost
  inference, preserves BKT mastery, evidence count, one-level movement,
  reversal protection, the Hard-level evidence rule, and unavailable-tier
  safety; records `selectionEvidenceMode: bkt_only_study` and
  `usedBktFallback: true`. P3b remains separate and is not part of the primary
  external comparison.
- Frozen configuration hashes (shared AQC-1..AQC-7 contract):
  adaptive policy `1b53aef77a8027b4256f915663ee894225c17efe4f876bff2e23a38ed17eef16`;
  policy evaluation `a12d251e5910a034c081950a8bede8dc7753329db0e9c540af108143e9a43a61`
  (recorded in the AQC release evidence). The E1 contract additionally freezes
  checkout-independent content hashes
  (`adaptivePolicyContentSha256`
  `1c782e3ca08fb021427af2a42eda1df4350d583b301f3ff79a7df529c6cf9d4b`,
  `policyEvaluationContentSha256`
  `effe57fb072cd3632ff227400db0ae6052749001ec9489a3abf5c6b555fa58e8`)
  computed over LF-normalized bytes, and the E1 contract tests verify the live
  config files against them.

## 8. Fresh-bank limitation (frozen)

Production P3a fresh-bank selection remains part of the native policy.
ASSISTments cannot reproduce exact historical bank freshness:

```yaml
freshBankRule:
  production_rule: preserved
  exact_external_observability: unavailable
  external_substitute: fresh_problem_exposure_audit_only
  included_in_full_policy_equivalence_claim: false
```

External Stage B may audit previously seen problem IDs, newly seen problem
IDs, and `freshProblemFraction`, but may not claim exact fresh-bank selection
was reproduced or that historical Logic Oasis bank exposure was reconstructed.

## 9. Claim level (frozen)

Allowed external claim levels:

```text
pipeline_demo_only
external_descriptive_replay
external_descriptive_replay_limited
external_replay_inconclusive
```

Forbidden for ASSISTments Stage B: `superiority`, `causal_effect`,
`KSSR_validated`, `production_validated`. Sample size alone must never upgrade
the external claim to causal/superiority. The Stage-B questions EB1-EB6 are
frozen separately; the existing H1-H6 confirmatory hypotheses remain reserved
for future Stage C and were not deleted.

External descriptive metric names are frozen (e.g. `policy_up_rate`,
`policy_hold_rate`, `policy_down_rate`, `p1_p2_agreement_rate`,
`three_way_agreement_rate`, `guardrail_activation_rate`,
`proxy_tier_matched_outcome_rate`,
`observed_proxy_matched_support_after_up_rate`,
`counterfactual_proxy_tier_mismatch_rate`, `bkt_calibration_by_band`).
`observed_proxy_matched_support_after_up_rate` is **not** renamed to the
Stage-C confirmatory `falsePromotionBurden`.

## 10. Governance boundary (frozen)

```yaml
productionPromotionAllowed: false
containsRawIdentifiers: false
redistributionAllowed: false
learnerLevelOutputsProtectedOutsideGit: true
```

The censoring vocabulary is frozen (at least
`insufficient_problem_evidence`, `insufficient_skill_catalog`,
`mixed_proxy_difficulty`, `external_proxy_tier_unavailable`,
`counterfactual_proxy_tier_mismatch`, `no_next_eligible_attempt`,
`identical_problem_set_repeat`, `chronology_ambiguous`,
`invalid_next_outcome`), and external censors are never translated into
native-bank errors.

## 11. Source abstraction (frozen schema; engine wiring deferred)

The existing AQC-2 replay engine is reused; no second full comparison pipeline
is created. The frozen source-mode vocabulary supports `native_runtime` and
`assistments_external`, and the `EvaluationDifficultyOption` schema
(`difficulty`, `candidateKind`, `nativeBankId`, `externalCandidateKey`,
`available`) is frozen:

- native: `candidateKind = native_bank`, `nativeBankId` required,
  `externalCandidateKey = null`;
- ASSISTments: `candidateKind = external_proxy_tier`, `nativeBankId = null`,
  namespaced `externalCandidateKey` (prefix `external_proxy_`), `available`
  meaning proxy-tier catalog availability.

E1 freezes this boundary in schema/contract form only. Wiring the option into
the AQC-2 selector boundary and building the external adapter belong to the
E2-E5 stages; the native runtime delivery path is not modified.

## 12. What E1 has NOT done

- No problem-difficulty calibration was run.
- No proxy Easy/Moderate/Hard tiers were calculated from real data.
- The 2022-2023 adaptive evaluation dataset was not reconstructed.
- P1/P2/P3a were not run on ASSISTments.
- No comparative policy results were inspected or produced.
- No matched-outcome results were produced.
- AQC-E2 (and every later stage) was **not** executed.
- No U7 model was retrained; no XGBoost support-risk inference was used.
- No production/runtime adaptive behaviour was modified.

## 13. Tests executed

- `tests.test_assistments_adaptive_contract` (E1 contract freeze): contract
  loads, provenance cannot become runtime_callable, native statuses/bankId not
  fabricated, proxy-tier vocabulary, window separation, frozen thresholds
  (20 / 9 / 3 / 2/3), replay and reversal semantics, fresh-bank limitation,
  claim levels, production non-promotion, P3a BKT-only, unchanged P1/P2/P3a
  hashes, native AQC source mode still validates, and fail-closed tamper
  rejection.
- `tests.test_assistments_stage_b_claim_boundary` (claim boundary):
  superiority/causal claims forbidden, sample size never upgrades claims, no
  runtime production activation, controlled-demo separation, no fake bank IDs,
  EB1-EB6 separate from H1-H6, fresh-bank equivalence excluded, external
  metric naming boundary, censor vocabulary not translated to native-bank
  errors.
- Existing AQC-1..AQC-7 policy evaluation suites remain green, and the
  relevant U7 ASSISTments adapter/contract suites were re-run (see the branch
  verification record in the E1 end report).

## 14. E1 decision

**FROZEN. READY FOR AQC-E2** (difficulty calibration from the 2019-2021
window), subject to the E2 gate rules. No E2 work was started.
