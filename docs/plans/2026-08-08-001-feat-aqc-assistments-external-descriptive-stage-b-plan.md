# Adaptive Question Bank Comparison and Selection — ASSISTments External-Real Descriptive Stage-B Plan

**Created:** 2026-08-08  
**Status:** Implementation-ready companion amendment for the existing AQC-1 to AQC-7 work  
**Primary dataset:** ASSISTments EDM Cup 2023  
**Primary cohort:** Exact Grade 6 Mathematics  
**Primary evidence mode:** `external_real_proxy_difficulty`  
**Claim level:** Descriptive, non-causal Stage-B evidence only

---

## 1. Purpose

This companion plan adds a defensible external-real Stage-B pathway to the existing **Adaptive Question Bank Comparison and Selection** implementation without discarding the completed AQC-1 to AQC-7 work.

The existing policy definitions remain authoritative:

- **P1 — Traditional score threshold**
- **P2 — BKT plus score-disagreement hold**
- **P3a — BKT-only guarded Logic Oasis policy**
- **P3b — model-assisted guarded policy, separate and not part of the primary external comparison**

The external ASSISTments pathway does **not** claim that ASSISTments contains Logic Oasis question banks, Easy/Moderate/Hard labels, native `quizAttempts`, native `questionResponses`, or runtime study assignments. Those concepts must not be fabricated.

The external comparison therefore evaluates the **difficulty-selection logic** of P1/P2/P3a using a pre-calibrated, source-derived **proxy difficulty tier**, while keeping native Stage-C/live-pilot claims and infrastructure separate.

---

## 2. Relationship to the Existing AQC-1 to AQC-7 Work

### 2.1 Keep the completed work

Do **not** discard the existing `codex/feat-policy-evaluation-aqc` implementation.

The existing work remains useful in the following way:

| Unit | Existing value | External ASSISTments use |
|---|---|---|
| AQC-1 | Frozen policy manifest, typed P1/P2/P3a/P3b selectors, deterministic decision IDs, reason codes | **Reuse directly**, extend manifest with external evidence mode |
| AQC-2 | Offline chronological replay, outcome/censoring pipeline, grouped metrics, CLI runner | **Reuse as the core Stage-B engine**, extend with external adapter and proxy-tier context |
| AQC-3 | Reporting, calibration, safety, agreement, censoring, decision audit output | **Reuse**, but relabel inferential outputs as descriptive external evidence |
| AQC-4 | Study control, consent, enrollment, blocked randomization | **Keep but do not use** for external ASSISTments Stage B |
| AQC-5 | Live runtime integration and study sidecar | **Keep but do not use** for external ASSISTments Stage B |
| AQC-6 | Controlled live-study export and governance | **Keep for future/native study**, not required to import ASSISTments |
| AQC-7 | Deployment verification | **Keep for future/native study**, not required for external Stage B |

### 2.2 No second full policy-comparison pipeline

Do **not** create an entirely separate P1/P2/P3a comparison engine.

Instead:

```text
Existing AQC-2 replay/metrics/reporting core
                    |
          source-mode abstraction
          /                     \
native_runtime                assistments_external
quizAttempts/responses        external-real adapter
real bank/difficulty          calibrated proxy tier
          \                     /
             shared P1/P2/P3a
                    |
          descriptive Stage-B report
```

Only source normalization, proxy difficulty, source-aware censoring, and source-aware claim language are new.

### 2.3 Existing controlled demonstration remains valid

The current fixture/emulator/controlled-demo evidence remains a **mechanics-only artifact**.

It is useful for regression testing but must remain separate from the real external comparison:

```yaml
controlled_demo:
  purpose: mechanics_only
  performance_claim: forbidden

assistments_external:
  purpose: external_real_descriptive_stage_b
  performance_claim: dataset_bounded_descriptive_only
```

Do not merge synthetic/demo rows into ASSISTments counts, intervals, or outcomes.

---

## 3. Frozen Policy Definitions

The external branch must call the same authoritative policy code/configuration used by the existing AQC implementation.

### P1 — Score threshold baseline

```text
correctCount / totalQuestions >= 0.80
    -> propose UP by one difficulty tier

otherwise
    -> HOLD

P1 never automatically demotes.
At the highest available tier, UP becomes HOLD.
```

### P2 — BKT + score-disagreement hold

Score direction:

```text
score >= 0.80 -> UP
score <= 0.40 -> DOWN
otherwise      -> NEUTRAL
```

BKT direction must come from the frozen `adaptive_policy_v1` configuration.

Delivery logic:

```text
BKT UP   + score UP   -> UP
BKT DOWN + score DOWN -> DOWN
all other combinations -> HOLD
```

All existing evidence limits, one-level movement, reversal protection, and hard-tier evidence guards remain frozen.

### P3a — BKT-only guarded policy

P3a must:

- forcibly bypass support-risk/XGBoost inference;
- use the frozen BKT state;
- use evidence count;
- preserve one-level movement;
- preserve reversal protection;
- preserve the hard-tier evidence requirement;
- preserve unavailable-tier safety;
- record `selectionEvidenceMode: bkt_only_study`;
- record `usedBktFallback: true`.

### Fresh-bank limitation

The production P3a policy includes fresh-bank selection, but ASSISTments does not expose native Logic Oasis bank IDs.

Therefore:

```yaml
freshBankRule:
  production_rule: preserved
  exact_external_observability: unavailable
  external_substitute: fresh_problem_exposure_audit_only
  included_in_full_policy_equivalence_claim: false
```

The external report may describe previously seen versus new problem IDs, but must not claim that full fresh-bank selection was reproduced.

---

## 4. Evidence and Claim Boundary

### 4.1 Allowed Stage-B conclusions

The external report may state:

- how often P1/P2/P3a propose UP/HOLD/DOWN;
- how often the policies agree/disagree;
- how often guardrails activate;
- descriptive challenge opportunity;
- proxy-tier availability/coverage;
- observed later support-needed rates only for proxy-tier-matched historical outcomes;
- BKT calibration against later eligible outcomes;
- censoring and data sufficiency.

### 4.2 Forbidden conclusions

The external report must not state:

- P3a caused better learning;
- P3a proved superior to P1/P2;
- ASSISTments validates Malaysian KSSR;
- proxy Easy/Moderate/Hard are native ASSISTments labels;
- the external replay reproduces exact Logic Oasis bank freshness;
- an external policy result authorizes production deployment.

### 4.3 Frozen external claim levels

Use source-aware claim levels:

```yaml
pipeline_demo_only:
  source: fixture_or_synthetic

external_descriptive_replay:
  source: external_real
  condition: sufficient proxy-tier and outcome coverage

external_descriptive_replay_limited:
  source: external_real
  condition: comparison runs but important coverage/matching gates are weak

external_replay_inconclusive:
  source: external_real
  condition: insufficient independent learners, tiers, or matched outcomes
```

No external ASSISTments run may automatically upgrade to a causal/superiority claim level.

---

## 5. Dataset and Provenance

### 5.1 Source

Dataset:

```text
ASSISTments EDM Cup 2023
```

Use the already verified physical release and hashes from the U7 ASSISTments evidence.

Keep:

```yaml
provenance: external_real
containsRawIdentifiers: false
productionPromotionAllowed: false
redistributionAllowed: false
```

Raw files and learner-level derived files remain outside Git.

### 5.2 Primary cohort

```text
Exact Grade 6 Mathematics
```

`Grade 6 Accelerated` remains separate.

Grades 4-6 may be generated only as a separately labelled secondary feasibility analysis after the Grade 6 result is fixed. They must not silently replace Grade 6 merely to obtain more rows.

---

## 6. Time Separation

The external adaptive study must separate **difficulty calibration** from **policy evaluation**.

### Calibration period

```text
2019-02-25 through 2021-12-31
```

Used only to estimate source-derived problem difficulty.

### Evaluation period

```text
2022-01-01 00:00:00 UTC
through
2023-12-31 23:59:59 UTC
```

Used for the external policy replay.

No 2022-2023 correctness outcome may influence the frozen problem-difficulty mapping.

### Preferred calibration independence

Prefer estimating problem difficulty from pre-2022 learners who do not contribute to the 2022-2023 Grade 6 evaluation cohort.

If this causes unacceptable coverage, stop at the AQC-E2 gate and record a versioned amendment before running P1/P2/P3a results. Do not silently relax it after policy outputs are viewed.

---

## 7. External Source Contract

Do not force external rows into native runtime fields.

### 7.1 External problem calibration record

```yaml
ExternalProblemDifficultyV1:
  datasetReleaseId: string
  externalProblemKey: string
  sourceSkillCode: string
  calibrationStart: datetime
  calibrationEnd: datetime
  calibrationLearnerCount: integer
  calibrationResponseCount: integer
  correctResponseCount: integer
  smoothedCorrectProbability: float
  difficultyScore: float
  proxyDifficulty: proxy_easy | proxy_moderate | proxy_hard | null
  calibrationStatus: calibrated | insufficient_problem_evidence
  provenance: external_real
```

### 7.2 External adaptive attempt

```yaml
ExternalAdaptiveAttemptV1:
  datasetReleaseId: string
  externalAttemptKey: string
  externalStudentKey: string
  externalAssignmentKey: string
  sourceSkillCode: string
  sourceTimestamp: datetime
  externalAttemptSequence: integer

  problemKeys: list[string]
  totalQuestions: integer
  correctCount: integer
  correctRate: float

  bktMasteryProbability: float
  bktEvidenceCount: integer
  bktVersion: string

  currentProxyDifficulty: proxy_easy | proxy_moderate | proxy_hard | null
  proxyDifficultyPurity: float
  externalProblemSetFingerprint: string

  previousObservedProxyDifficulty: proxy_easy | proxy_moderate | proxy_hard | null
  freshProblemFraction: float | null

  provenance: external_real
```

### 7.3 Explicitly forbidden fabricated fields

Do not create fake values for:

```text
finalizationStatus
validationStatus
dataSource = runtime_callable
Logic Oasis bankId
Logic Oasis contentVersion
Logic Oasis policyVersion as source metadata
native sourceAttemptSequence
native adaptiveAssignment ID
native questionBank.isActive
```

Policy/evaluation versions may be added as **analysis metadata**, clearly separated from source metadata.

---

## 8. Problem Difficulty Calibration

### 8.1 Correctness source

Use only the already validated graded events:

```text
correct_response -> 1
wrong_response   -> 0
```

Follow the same first-graded-response semantics already established for the ASSISTments pathway.

### 8.2 Smoothed correctness estimate

For each Grade 6 problem with exact non-null `sourceSkillCode`:

```text
p_correct =
(correct_responses + 1)
/
(total_graded_responses + 2)

difficulty_score =
1 - p_correct
```

This smoothing rule is project-defined and must be frozen before policy results.

### 8.3 Minimum problem evidence

Initial frozen rule:

```text
minimum independent calibration learners per problem = 20
```

Problems below this threshold:

```text
calibrationStatus = insufficient_problem_evidence
proxyDifficulty = null
```

Do not lower the threshold after seeing Stage-B policy results.

### 8.4 Within-skill proxy tiers

Difficulty tiers are assigned separately within each exact `sourceSkillCode`.

For calibrated problems in one skill:

```text
highest p_correct third -> proxy_easy
middle p_correct third  -> proxy_moderate
lowest p_correct third  -> proxy_hard
```

Use deterministic rank/tie handling documented in the manifest.

Never call these native ASSISTments difficulty levels.

### 8.5 Skill catalog sufficiency

Initial frozen rule:

```text
>= 9 calibrated problems in the skill
AND
>= 3 proxy_easy problems
>= 3 proxy_moderate problems
>= 3 proxy_hard problems
```

Otherwise:

```text
skillProxyStatus = insufficient_skill_catalog
```

and exclude the skill from full proxy-tier policy replay.

---

## 9. Evaluation Episode Reconstruction

Reuse the successful exact-skill U7-v2 semantic unit:

```text
one externalStudentKey
+ one completed externalAssignmentKey
+ one exact non-null sourceSkillCode
```

Never mix skills inside one adaptive attempt.

Preserve chronological ordering and no-future-leakage tests from U7.

### 9.1 Attempt correctness

Compute:

```text
correctRate = correctCount / totalQuestions
```

using valid graded outcomes only.

### 9.2 Attempt proxy difficulty

Each problem contributes its frozen calibrated proxy tier.

A reconstructed attempt receives one current tier only when:

```text
dominant proxy tier fraction >= 2/3
```

Example:

```text
easy, easy, easy, moderate, easy
-> purity = 4/5
-> proxy_easy
```

If:

```text
purity < 2/3
```

then:

```text
currentProxyDifficulty = null
censorReason = mixed_proxy_difficulty
```

The row may remain available for score/BKT descriptive auditing but not tier-dependent policy comparison.

### 9.3 Problem-set fingerprint

Create:

```text
externalProblemSetFingerprint =
SHA256(sourceSkillCode + sorted(valid_problem_keys))
```

Use it only for repeat/exposure audits.

It is not a `bankId`.

---

## 10. External Tier Availability

ASSISTments does not expose historical active-bank metadata.

For this external branch, define an analytical tier catalog:

```text
available proxy tier =
the exact source skill has a valid calibrated problem catalog
for that tier
```

Example:

```text
current = proxy_moderate
skill catalog has:
  proxy_easy     yes
  proxy_moderate yes
  proxy_hard     yes

DOWN/HOLD/UP are analytically available.
```

If the adjacent tier is not valid:

```text
proposed movement -> safe HOLD
reason -> external_proxy_tier_unavailable
```

Report this as **analytical proxy-tier availability**, not historical ASSISTments bank availability.

---

## 11. Replay Semantics

### 11.1 One-step, non-propagating replay

Use:

```yaml
replayMode: one_step_non_propagating
```

For each real historical state at time `t`:

1. reconstruct only evidence available at `t`;
2. compute P1 decision;
3. compute P2 decision;
4. compute P3a decision;
5. record the proposed direction/reason;
6. do not rewrite the learner's later history to follow that hypothetical policy.

The next historical decision point is reconstructed from the actual observed source history.

### 11.2 Reversal protection

For external replay:

```yaml
reversalHistorySource: observed_proxy_difficulty_history
```

Do not feed previous counterfactual P1/P2/P3a outputs recursively into later states.

### 11.3 Future isolation

A future response, future score, future proxy tier, or future outcome must never change:

- earlier BKT state;
- earlier score;
- earlier evidence count;
- earlier current proxy tier;
- earlier policy decision.

---

## 12. External Outcome Matching

A candidate policy's later historical outcome may be scored only when the proposed target tier matches the next observed eligible proxy tier.

Example:

```text
current observed tier = proxy_moderate
P3a proposes UP -> proxy_hard
next observed eligible attempt = proxy_hard
=> tier-matched outcome eligible
```

If:

```text
P3a proposes proxy_hard
next observed eligible attempt = proxy_moderate
```

then:

```text
censorReason = counterfactual_proxy_tier_mismatch
```

Additional required compatibility:

- same `externalStudentKey`;
- same exact `sourceSkillCode`;
- next chronological eligible episode;
- valid next correctness outcome;
- no chronology ambiguity;
- no identical complete problem-set repeat;
- all frozen U7-compatible leakage protections.

Missing next attempt is censored, never treated as success/failure.

---

## 13. Outcome Definitions for External Stage B

Use descriptive names that distinguish this analysis from the future randomized Stage C.

Primary external outputs:

```text
policy_up_rate
policy_hold_rate
policy_down_rate

p1_p2_agreement_rate
p1_p3a_agreement_rate
p2_p3a_agreement_rate
three_way_agreement_rate

guardrail_activation_rate
descriptive_challenge_opportunity

proxy_tier_matched_outcome_rate
observed_proxy_matched_support_after_up_rate
observed_proxy_matched_success_after_up_rate

matched_hold_support_rate
matched_down_support_rate

counterfactual_proxy_tier_mismatch_rate
no_next_censor_rate
repeat_censor_rate
mixed_proxy_difficulty_rate

bkt_calibration_by_band
```

Do not rename `observed_proxy_matched_support_after_up_rate` to the Stage-C confirmatory `falsePromotionBurden`.

### Oscillation

Only report:

```text
observed historical proxy-tier oscillation
```

and policy **proposed reversal signals**.

Do not claim long-term counterfactual P1/P2/P3a oscillation because replay is not recursive.

---

## 14. Descriptive Questions

Add these external Stage-B questions separately from the existing Stage-C hypotheses.

### EB1

How often do P1, P2, and P3a propose UP/HOLD/DOWN on identical observed learner-skill states?

### EB2

How often does P3a hold where P1 would promote?

### EB3

How often does P2 hold because BKT and score direction disagree?

### EB4

Among proxy-tier-matched historical observations, what proportion of proposed UP decisions are followed by `support_needed` versus later success?

### EB5

How well is frozen BKT mastery calibrated against later eligible exact-skill outcomes?

### EB6

How much of the external data is censored because proxy difficulty, adjacent tier availability, next history, or observed target-tier matching is unavailable?

The existing H1-H6 confirmatory/superiority language remains reserved for the future approved Stage-C live pilot.

---

## 15. Statistical Protocol

### 15.1 Student grouping

All rows from one external learner must remain together for any grouped resampling or split.

### 15.2 Confidence intervals

Use the existing student-clustered bootstrap implementation where applicable.

Report:

- estimate;
- 95% descriptive confidence interval;
- independent learner count;
- decision count;
- censoring denominator.

### 15.3 No superiority testing

For the external ASSISTments Stage B:

- no Holm superiority test;
- no causal effect estimate;
- no non-inferiority claim;
- no p-value-driven policy winner;
- no automatic claim-level upgrade to superiority.

Differences between policies are descriptive and dataset-bounded.

---

## 16. Reuse of Existing AQC Pipeline

### 16.1 `policy_evaluation.py`

Reuse the existing selector logic.

Add external evaluation context only if necessary; do not duplicate the policy rules.

If the current selector requires concrete `bankId` values, refactor the evaluation boundary so direction selection uses a generic tier candidate structure. Native runtime bank delivery remains unchanged.

Suggested abstraction:

```yaml
EvaluationDifficultyOption:
  difficulty: easy | moderate | hard
  candidateKind: native_bank | external_proxy_tier
  nativeBankId: string|null
  externalCandidateKey: string|null
  available: boolean
```

For ASSISTments:

```text
candidateKind = external_proxy_tier
nativeBankId = null
```

### 16.2 AQC-2 replay pipeline

Keep:

```text
ai_pipeline/evaluation/manifest.py
ai_pipeline/evaluation/replay.py
ai_pipeline/evaluation/outcomes.py
ai_pipeline/evaluation/metrics.py
ai_pipeline/evaluation/reporting.py
ai_pipeline/evaluation/run_policy_comparison.py
```

Extend rather than replace them.

### 16.3 Source mode

Add an explicit source mode:

```text
--source-mode native_runtime
--source-mode assistments_external
```

The existing `attempts.csv + responses.csv` native runtime contract remains unchanged.

The ASSISTments mode reads a protected external manifest and protected external derived data.

Do not make ASSISTments imitate the native CSV shape by fabricating statuses/banks.

### 16.4 Reporting

Reuse AQC-3 charts/tables where semantically valid.

For external mode:

- relabel safety forest plots as descriptive proxy-tier matched differences;
- suppress any superiority label;
- clearly show matched-outcome coverage;
- prominently show censoring;
- label fresh-bank evidence as unavailable/partial;
- label provenance `external_real`.

---

## 17. New/Modified Files

Suggested additions:

```text
ai_pipeline/external_data/assistments/adaptive/
  assistments_adaptive_contract_v1.yaml
  difficulty_calibration.py
  adaptive_attempts.py
  proxy_tiers.py
  external_policy_source.py

ai_pipeline/tests/
  test_assistments_adaptive_contract.py
  test_assistments_difficulty_calibration.py
  test_assistments_proxy_tiers.py
  test_assistments_external_policy_replay.py
  test_assistments_stage_b_claim_boundary.py
```

Suggested reports:

```text
docs/evidence/
  aqc-assistments-external-data-readiness.md
  aqc-assistments-proxy-difficulty-calibration.md

ai_pipeline/reports/
  adaptive_question_bank_assistments_stage_b.md
```

Protected learner-level outputs should stay outside Git, for example:

```text
<private_data>/assitments_edm_cup_2023/processed/aqc/
  e2/
  e3/
  e4/
  e5/
  e6/
```

---

## 18. Implementation Stages

# AQC-E1 — Freeze External Adaptive Contract

**Goal:** Add the ASSISTments-specific external Stage-B contract without running policy outcomes.

Freeze:

- dataset/release hashes;
- Grade 6 primary cohort;
- calibration/evaluation windows;
- exact-skill unit;
- proxy difficulty method;
- problem evidence threshold;
- skill catalog threshold;
- attempt purity threshold;
- BKT version;
- P1/P2/P3a versions;
- replay mode;
- censoring codes;
- claim level;
- no-production boundary.

**Gate:** Contract tests pass before E2.

**Do not run P1/P2/P3a results yet.**

---

# AQC-E2 — Calibrate Problem Difficulty from 2019-2021

**Goal:** Produce `assistments_problem_difficulty_proxy_v1`.

Steps:

1. Filter Grade 6 Mathematics.
2. Require exact non-null skill.
3. Use first graded response only.
4. Use calibration-period rows only.
5. Prefer learners disjoint from 2022-2023 evaluation learners.
6. Aggregate independent learner evidence per problem.
7. Apply smoothing.
8. Apply minimum 20-learner rule.
9. Assign within-skill tertile proxy tiers.
10. Apply skill-catalog sufficiency gate.
11. Freeze hashes and counts.

Report:

- problems observed;
- calibrated problems;
- insufficient problems;
- skills observed;
- eligible three-tier skills;
- per-tier problem counts;
- calibration learner counts;
- p(correct) distribution;
- overlap/disjointness status.

**Stop if the usable three-tier catalog is too sparse.**

Do not lower thresholds automatically.

---

# AQC-E3 — Build 2022-2023 External Adaptive Attempts

**Goal:** Reconstruct Grade 6 exact-skill attempts using the frozen U7-v2 semantic unit.

Attach:

- score;
- BKT mastery/evidence;
- calibrated problem tiers;
- current proxy difficulty;
- purity;
- problem-set fingerprint;
- observed previous proxy difficulty;
- fresh-problem audit.

No policy decisions yet.

Report:

- episodes;
- score-valid;
- BKT-valid;
- proxy-tier-valid;
- mixed-tier censors;
- tier distribution;
- learner distribution;
- per-skill coverage.

---

# AQC-E4 — Stage-B Readiness Gate

**Goal:** Decide whether enough real external evidence exists before running policy comparisons.

Required report:

- independent learners;
- eligible exact skills;
- calibrated problems;
- percentage of evaluation problems with a proxy tier;
- tier-valid attempts;
- Easy/Moderate/Hard counts;
- adjacent-tier availability;
- valid BKT states;
- current states capable of P1/P2/P3a comparison;
- valid next episodes;
- possible tier-matched observed outcomes;
- expected mismatch/censoring burden.

Decision:

```text
READY_FOR_EXTERNAL_POLICY_REPLAY
```

or:

```text
NOT_READY_FOR_EXTERNAL_POLICY_REPLAY
```

Do not inspect comparative policy performance before this gate is frozen.

---

# AQC-A — Controlled Mechanics Regression

The existing controlled-demo implementation is retained.

Run only a small regression fixture suite proving:

- P1 threshold boundary;
- P2 disagreement hold;
- P3a BKT-only mode;
- one-level movement;
- highest-tier hold;
- unavailable adjacent tier hold;
- reversal protection;
- future leakage rejection;
- external candidate does not create a fake bank ID;
- external claim level cannot become superiority.

This stage produces no real-data performance evidence.

---

# AQC-E5 — Run P1/P2/P3a One-Step Replay

**Goal:** Run all three policies on identical eligible external states.

For every decision record:

```text
externalStudentKey
sourceSkillCode
current proxy tier
correct rate
BKT mastery
BKT evidence count
previous observed tier

P1 proposed direction + reason
P2 proposed direction + reason
P3a proposed direction + reason
```

Report:

- UP/HOLD/DOWN rates;
- pairwise agreement;
- three-way agreement;
- P1 promotion opportunities;
- P2 disagreement holds;
- P3a guardrail holds;
- proposed reversal signals;
- source/tier coverage.

No future outcome is used in decision construction.

---

# AQC-E6 — Matched Historical Outcome Analysis

**Goal:** Add later real outcomes only where historical delivery matches the candidate proxy tier.

For each policy:

1. determine the proposed target proxy tier;
2. find the direct next eligible exact-skill historical episode;
3. verify the next observed proxy tier;
4. if target != observed tier, censor as `counterfactual_proxy_tier_mismatch`;
5. if equal, attach the frozen later support-needed/success outcome;
6. preserve repeat/no-next/invalid-next censors.

Report:

- candidate decisions;
- matched outcomes;
- tier mismatches;
- no-next censors;
- repeated-set censors;
- support-needed after matched UP;
- success after matched UP;
- matched HOLD outcomes;
- matched DOWN outcomes;
- student-clustered descriptive CIs;
- BKT calibration.

No causal interpretation.

---

# AQC-E7 — Final External Adaptive Report

Create:

```text
ai_pipeline/reports/adaptive_question_bank_assistments_stage_b.md
```

Include:

1. source/release/provenance;
2. ethics/terms boundary;
3. calibration and evaluation windows;
4. Grade 6 scope;
5. external contract/version;
6. proxy difficulty method and limitations;
7. tier catalog coverage;
8. attempt reconstruction;
9. BKT version and chronology;
10. P1/P2/P3a versions;
11. replay mode;
12. policy direction distributions;
13. policy agreement/disagreement;
14. guardrail activation;
15. matched-outcome coverage;
16. descriptive later-outcome rates;
17. BKT calibration;
18. censoring;
19. fresh-bank limitation;
20. external-domain/KSSR limitation;
21. tests;
22. final claim level;
23. production non-promotion statement.

Valid final statuses:

```text
EXTERNAL POLICY REPLAY COMPLETED
```

```text
EXTERNAL POLICY REPLAY COMPLETED WITH LIMITED PROXY-TIER OUTCOME COVERAGE
```

or:

```text
EXTERNAL POLICY REPLAY INCONCLUSIVE
```

Never:

```text
P3a PROVED SUPERIOR
```

---

## 19. Acceptance Gates

### Contract gate

- external provenance cannot become native runtime provenance;
- no fake bank/status fields;
- all thresholds/versions frozen before results.

### Calibration gate

- calibration uses pre-evaluation rows only;
- no 2022-2023 outcome influences difficulty;
- minimum calibration evidence enforced;
- tier mapping deterministic and hashed.

### Reconstruction gate

- exact skills never mix;
- BKT state is past/current only;
- current tier uses frozen problem calibration only;
- mixed-tier attempts are censored by the frozen purity rule.

### Fair replay gate

- P1/P2/P3a receive the same eligible rows/state;
- no future row changes an earlier decision;
- one-step replay does not propagate counterfactual states.

### Outcome gate

- later outcome attached only after candidate target tier equals next observed proxy tier;
- unmatched decisions are censored;
- missing next outcome is never converted to success/failure.

### Claim gate

- external Stage B remains descriptive;
- no superiority/causal label;
- no KSSR validation claim;
- no production policy/model promotion.

---

## 20. Required Tests

Add tests proving at least:

1. calibration excludes evaluation-period rows;
2. evaluation learners do not enter preferred disjoint difficulty calibration;
3. insufficient problem evidence produces no tier;
4. tier assignment is within exact skill only;
5. deterministic ties reproduce identical tier hashes;
6. skills below catalog requirements fail closed;
7. skills never mix in one attempt;
8. attempt purity below 2/3 is censored;
9. external fingerprint is not exposed as `bankId`;
10. P1 0.80 boundary is unchanged;
11. P2 score boundaries 0.80/0.40 are unchanged;
12. P3a bypasses support risk;
13. future injection cannot change an earlier decision;
14. one-step replay does not use prior counterfactual outputs as observed history;
15. target proxy tier mismatch is censored;
16. same target tier may attach later outcome only after all compatibility checks;
17. controlled-demo rows cannot enter external counts;
18. external evidence cannot receive a superiority claim level;
19. external artifacts cannot activate runtime production policy/model state;
20. native AQC-1 to AQC-7 tests remain green.

---

## 21. Definition of Done

The ASSISTments external Stage-B branch is complete when:

- AQC-E1 through AQC-E7 are implemented;
- all existing AQC tests still pass;
- all new external tests pass;
- the calibration manifest is frozen before policy comparison;
- the external policy report contains only aggregate/non-identifying evidence;
- P1/P2/P3a were replayed on identical current-state rows;
- matched outcomes use only observed proxy-tier-compatible later history;
- censoring is fully reported;
- the fresh-bank limitation is explicit;
- no native source field was fabricated;
- no causal/superiority claim is made;
- no production activation occurs.

---

## 22. Recommended Git/Branch Strategy

Because AQC-1 to AQC-7 are already committed, do not delete or reset that work merely because real data was not yet supplied.

Recommended practical path:

```text
codex/feat-policy-evaluation-aqc
        |
        | existing AQC-1 to AQC-7
        |
        +--> create new continuation branch
             codex/feat-aqc-assistments-stage-b
                    |
                    +-- AQC-E1
                    +-- AQC-E2
                    +-- AQC-E3
                    +-- AQC-E4
                    +-- AQC-E5
                    +-- AQC-E6
                    +-- AQC-E7
```

This avoids rewriting the already-tested policy engine and keeps the external-data amendment auditable.

If the final FYP1 merge should remain minimal, AQC-4 to AQC-7 may remain documented/deferred native-live infrastructure rather than being exercised as part of the external evidence run. Do not remove them simply to make the external comparison work.

---

## 23. Execution Order

Run each stage separately:

```text
E1 contract
   ↓
E2 calibration
   ↓
E3 reconstruction
   ↓
E4 readiness gate
   ↓
A mechanics regression
   ↓
E5 policy replay
   ↓
E6 matched outcomes
   ↓
E7 final report
```

Do not execute all stages in one uncontrolled command.

Especially:

- stop after E2 if calibration coverage is inadequate;
- stop after E4 if the external Stage-B gate fails;
- do not loosen thresholds merely to make E4 pass;
- do not rewrite the proxy-tier contract after E5/E6 results are visible.

---

## 24. Final Intended FYP1 Position

The final external evidence should support wording such as:

> The Logic Oasis adaptive policies were replayed on real, de-identified Grade 6 mathematics learner histories from ASSISTments EDM Cup 2023. Because ASSISTments does not provide native Logic Oasis question-bank difficulty labels, ordered analytical proxy tiers were calibrated independently from pre-evaluation historical learner performance and frozen before the 2022-2023 policy replay. P1, P2, and P3a were then compared descriptively on identical chronological learner-skill states, with later outcomes evaluated only where the proposed proxy tier matched the tier historically observed next. The analysis is external-domain and non-causal and does not establish policy superiority or direct KSSR validation.

This is the maximum intended claim for this branch.
