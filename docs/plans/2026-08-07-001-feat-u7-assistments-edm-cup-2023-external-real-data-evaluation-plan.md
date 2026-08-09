---
title: Logic Oasis U7 ASSISTments EDM Cup 2023 External Real-Data Evaluation Plan
type: feat
date: 2026-08-07
last_updated: 2026-08-07
status: implementation-ready
artifact_readiness: implementation-ready
approval_status: recorded-for-external-real-route
implementation_entrypoint: J0
execution_state: ready-to-start-j0-after-data-access
artifact_contract: ce-unified-plan/v1
execution: code
canonical_parent: 2026-07-05-001-feat-fyp1-prototype-development-plan(2)(1)(2).md
scope_owner: U7 Prediction Contract and Fair Model Comparison
external_dataset: ASSISTments EDM Cup 2023
external_dataset_window: 2022-01-01/2023-12-31
external_provenance: external_real
source_platform: ASSISTments
source_distribution: Kaggle EDM Cup 2023
source_usage_terms: ASSISTments Data Terms of Use effective 2020-10-30
supersedes_external_plan: 2026-08-07-001-feat-u7-junyi-external-real-data-evaluation-plan.md
---

# Logic Oasis U7 ASSISTments EDM Cup 2023 External Real-Data Evaluation Plan

## Goal Capsule

Close the current U7 evidence gap by using the **ASSISTments EDM Cup 2023** competition dataset as approved **external real-learner evidence** for the existing Logic Oasis U7 prediction contract.

The evaluation will use only eligible ASSISTments Mathematics learning interactions dated **2022-01-01 through 2023-12-31 inclusive**. It will compare **Decision Tree, XGBoost, and a small regularized MLP** using the exact same frozen Logic Oasis base feature schema:

```text
quiz-attempt-features-v2
  - correct_rate
  - mean_response_time_ms
```

and the existing future-facing target:

```text
next_attempt_support_needed
```

This plan is a **companion to the canonical FYP1 plan**, not a replacement. The canonical FYP1 plan remains authoritative for U7 model roles, feature schema, target definition, student-grouped splitting, leakage controls, metrics, BKT/SHAP responsibilities, evidence levels, and runtime-promotion boundaries.

The ASSISTments dataset is used only as **offline external-domain real-data evidence**. It must never be relabelled as Logic Oasis native `runtime_callable` evidence and it must not weaken the trusted U3/U6/U8 runtime contract.

The previous Junyi 2019-2024 external-data plan is superseded because the required learner-interaction table was not physically available in the attached Kaggle release. ASSISTments EDM Cup 2023 is selected because the required interaction log is physically listed on Kaggle and the dataset documentation supports timestamped Mathematics learner actions, correctness events, assignment/sequence structure, and curriculum metadata.

---

## 1. Final Dataset Selection Decision

### 1.1 Selection checklist

| Requirement | ASSISTments EDM Cup 2023 status | Decision |
|---|---|---|
| Real learner data | ✅ Confirmed | Real ASSISTments learner clickstream and assignment data. |
| Mathematics | ✅ Confirmed | EDM Cup task is based on Mathematics assignments in ASSISTments. |
| Physically accessible interaction log | ✅ Confirmed | Kaggle Data Explorer lists `action_logs.csv` (approximately 1.44 GB) together with nine supporting CSV files. |
| Correct/wrong response events | ✅ Confirmed | Published dataset documentation identifies correct/wrong response actions. |
| Timestamped interactions | ✅ Confirmed | Published documentation states action-log records include timestamps. |
| Natural learning structure | ✅ Confirmed | Assignment, sequence, problem, and relationship tables are provided. |
| Curriculum/grade metadata | ✅ Confirmed | Sequence metadata/folder paths describe curriculum/grade context. |
| Recent observations | ✅ Confirmed by selected project window | Only 2022-2023 source interactions are eligible for final FYP1 U7 evidence. |
| Non-commercial academic use terms | ✅ Confirmed | ASSISTments Data Terms of Use permit use subject to non-commercial, citation, privacy, public-outcome, and no-redistribution obligations. |
| No redistribution | ✅ Required | Raw or derived learner-level ASSISTments data must not be published or committed to Git. |
| De-anonymization prohibition | ✅ Required | No re-identification attempt is permitted. |
| Base U7 feature compatibility | ✅ Strong semantic fit | `correct_rate` can be reconstructed from graded response events; `mean_response_time_ms` can be derived only from defensible timestamped start→first-graded-response pairs and must pass J0. |
| Student-grouped evaluation | ✅ Supported | Stable learner identity exists in the competition data; exact physical field is frozen during J0. |
| Future-facing next-attempt target | ✅ Supported | Chronological in-unit assignment histories can be reconstructed; exact join/order keys are frozen during J0. |
| BKT chronology | ✅ Likely, separately gated | Action logs are timestamped; exact deterministic ordering and content/skill linkage must pass J0/J2 before BKT ablation. |
| Supervisor/institutional approval | ✅ External-real route recorded | Preserve the existing approval record. If the institutional record names Junyi specifically rather than the external-real route generally, update the record to ASSISTments before J4 final evidence execution. |
| Implementation readiness | ✅ Yes | J0 is the first executable unit after Kaggle access is accepted and the source files are available locally. |

### 1.2 Final go decision

**Implementation decision: GO.**

The selected U7 evidence path is:

```text
ASSISTments EDM Cup 2023
          ↓
STRICT source-time filter
2022-01-01 .. 2023-12-31 inclusive
          ↓
Mathematics + primary Grade 6 scope where sufficient
          ↓
assignment/problem/action reconstruction
          ↓
correct_rate + mean_response_time_ms
          ↓
next_attempt_support_needed
          ↓
Decision Tree | XGBoost | small MLP
          ↓
student-grouped external-real-data comparison
          ↓
SHAP + optional BKT ablation + limitations
```

---

## 2. Why ASSISTments Replaces Junyi

The Junyi 2019-2024 release advertised a large interaction table, but the actual Kaggle notebook input mounted only user and content metadata. Without physical access to the learner-interaction table, the frozen U7 features and future-facing target could not be constructed reproducibly.

ASSISTments EDM Cup 2023 avoids this blocker because Kaggle physically lists the interaction table and the related metadata files. The dataset was created specifically to model future Mathematics performance from earlier ASSISTments clickstream behavior.

### Replacement rationale

| Criterion | Junyi 2019-2024 mounted release | ASSISTments EDM Cup 2023 |
|---|---|---|
| Interaction table physically available | ❌ Not mounted | ✅ `action_logs.csv` listed |
| Correct/wrong learner actions | Not physically accessible | ✅ Documented |
| Timestamped actions | Not physically accessible | ✅ Documented |
| Assignment boundaries | Unresolved | ✅ Assignment tables provided |
| Problem metadata | Unresolved | ✅ `problem_details.csv` |
| Sequence/curriculum metadata | Partial | ✅ Sequence tables provided |
| U7 response-time reconstruction | Blocked | ✅ Semantically possible, J0 verifies exact pairing |
| Recent FYP1 subset | Possible | ✅ 2022-2023 |
| U7 implementation risk | High | Lower |

The frozen U7 contract is **not changed to fit the dataset**. The dataset is selected because it can support the existing contract.

---

## 3. Source Data Inventory

### 3.1 Physical Kaggle files

The Kaggle EDM Cup 2023 Data Explorer lists ten CSV files:

```text
action_logs.csv
assignment_details.csv
assignment_relationships.csv
evaluation_unit_test_scores.csv
explanation_details.csv
hint_details.csv
problem_details.csv
sequence_details.csv
sequence_relationships.csv
training_unit_test_scores.csv
```

`action_logs.csv` is the largest file (approximately 1.44 GB in the Kaggle Data Explorer screenshot) and is the critical interaction source for this plan.

### 3.2 Files expected to be required for base U7

J0 must inspect all source headers, but the expected minimum semantic sources are:

```text
action_logs.csv
  learner/action chronology and graded response behavior

assignment_details.csv
  assignment identity and assignment-level structure

sequence_details.csv
  sequence/curriculum/grade context

problem_details.csv
  problem identity and Mathematics skill/content metadata

assignment_relationships.csv and/or sequence_relationships.csv
  relationship keys where required to connect assignments, sequences, units, or content
```

### 3.3 Files not used as base U7 features

The following must **not** become base U7 features:

```text
training_unit_test_scores.csv
evaluation_unit_test_scores.csv
hint_details.csv
explanation_details.csv
```

Unit-test scores belong to the original EDM Cup prediction task and can create future/outcome leakage relative to the Logic Oasis U7 contract. They may be inspected only to understand source relationships or for non-feature audit, and must never enter `correct_rate`, `mean_response_time_ms`, or the base model vector.

Hint/explanation data is also excluded because FYP1 `quiz-attempt-features-v2` contains only the two frozen base features.

---

## 4. Access, Usage Terms, and Data-Security Contract

### 4.1 Access step before J0

Kaggle requires the user to **join the EDM Cup 2023 competition and accept the competition rules** before viewing/downloading the competition data.

This is an execution access step, not an unresolved dataset-selection question.

Before J0 starts:

- join the competition using the authorized Kaggle account;
- accept the competition rules displayed by Kaggle;
- download/access the required source CSV files;
- do not bypass access controls or obtain mirrored copies from unofficial sources.

### 4.2 ASSISTments Data Terms of Use

The project must comply with the ASSISTments Data Terms of Use, effective 2020-10-30. The frozen project rules are:

- cite ASSISTments and the specific dataset/DOI where available;
- no commercial use;
- make research outcomes available using free/open-access practices as required by the terms;
- do not attempt to de-anonymize ASSISTments users;
- do not redistribute ASSISTments data;
- code that processes/manipulates the data may be distributed;
- collaborators must independently obtain the data from the original source;
- if re-identification becomes possible, follow the provider's required notification/deletion/halt procedure.

### 4.3 Repository rule

```text
Public/private Git repository
  preprocessing/evaluation code                   ✅
  schema mapping                                  ✅
  tests                                           ✅
  aggregate metrics/plots                         ✅
  model-comparison report                         ✅
  raw ASSISTments CSVs                            ❌
  row-level normalized learner extracts           ❌
  persistent source learner identifiers           ❌
```

### 4.4 Local protected-data layout

Recommended Windows structure:

```text
C:\Users\<user>\Documents\
├── logic-oasis\
│   └── ... Git repository ...
│
└── logic-oasis-private-data\
    └── assistments_edm_cup_2023\
        ├── raw\
        │   ├── action_logs.csv
        │   ├── assignment_details.csv
        │   ├── assignment_relationships.csv
        │   ├── evaluation_unit_test_scores.csv
        │   ├── explanation_details.csv
        │   ├── hint_details.csv
        │   ├── problem_details.csv
        │   ├── sequence_details.csv
        │   ├── sequence_relationships.csv
        │   └── training_unit_test_scores.csv
        ├── j0\
        └── processed\
```

Raw data must remain outside the repository even if `.gitignore` exists.

---

## 5. Freshness Contract: 2022-01-01 to 2023-12-31 Only

Published analysis of the EDM Cup 2023 dataset reports data collected during academic years 2019-2023. The FYP1 evaluation will not use the complete historical range.

### 5.1 Hard inclusion rule

Eligible source actions must satisfy:

```text
2022-01-01 00:00:00 <= source timestamp <= 2023-12-31 23:59:59
```

No 2019, 2020, or 2021 action may enter the final U7 evidence dataset.

### 5.2 Fail-closed boundary tests

J0/J1 tests must prove:

```text
2021-12-31 23:59:59 -> excluded
2022-01-01 00:00:00 -> included
2023-12-31 23:59:59 -> included
2024-01-01 00:00:00 -> excluded
missing/unparseable timestamp -> excluded from chronological evidence
```

### 5.3 Final report wording

The final report must explicitly state:

> The source EDM Cup 2023 dataset contains earlier ASSISTments histories, but this FYP1 U7 analysis restricted eligible clickstream interactions to 2022-2023 to maintain the declared recent-data window.

---

## 6. Learner/Curriculum Scope

Logic Oasis targets Malaysian KSSR Year 4-6 students. ASSISTments is an external U.S.-curriculum platform, so direct curriculum equivalence must not be claimed.

### 6.1 Primary scope

Use **Grade 6 Mathematics** as the primary external cohort when J0/J3 confirm sufficient repeated learners, valid current→next pairs, and both target classes.

### 6.2 Predeclared fallback scope

If Grade 6 alone fails the data-sufficiency gates, the plan uses the
**predeclared secondary fallback: exact Grades 4, 5, and 6 Mathematics pooled**
(`sourceGrade in {"4", "5", "6"}` AND `sourceSubject == "Mathematics"`), as
already frozen in `assistments-j2-attempt-label-contract-v1` before any J2
outcome inspection. Pooling grades only enlarges the eligible cohort; the
current -> next semantics are unchanged (same learner + same sequence).

The fallback is:

- secondary external-domain evidence, clearly labelled as such;
- reported together with the separately reported Grade 6 insufficiency
  (the Grade 6 result is never silently replaced or hidden);
- built with grade as audit/filter metadata only; grade is **not** a base
  feature;
- subject to no KSSR equivalence claim;
- frozen before J2 outcome inspection, so it is a predeclared fallback, not
  post-result dataset shopping.

Grades 7-8 and other cohorts are not used during J3.

### 6.3 Content compatibility

J0/J2 must determine the narrowest defensible repeated content identity using available sequence/problem metadata such as:

- sequence/unit identity;
- topic/content hierarchy;
- Mathematics skill/CCSS code where physically available;
- assignment-to-sequence relationships.

Do not invent a KSSR mapping merely to increase sample size.

---

## 7. Non-Negotiable U7 Contracts Preserved

| Contract | Frozen FYP1 rule |
|---|---|
| Prediction target | `next_attempt_support_needed` |
| Prediction unit | One reconstructed learner-content in-unit assignment at time `t` |
| Observation boundary | Current assignment evidence only; no later assignment/test information |
| Default mastery criterion | `0.60` as current documented default; freeze before final held-out analysis |
| Base feature schema | `quiz-attempt-features-v2` |
| Base features | `correct_rate`, `mean_response_time_ms` only |
| Hint feature | Excluded |
| Models | Decision Tree, XGBoost, small regularized MLP |
| MLP | Fixed modest architecture; early stopping disabled |
| Split | Student-grouped; no learner appears in both train and held-out sets |
| BKT | Separate named ablation only |
| SHAP | XGBoost interpretability only |
| Missing next compatible assignment | Censored/unlabelled |
| Future leakage | Strictly forbidden |
| Model conclusion | Must follow measured results; XGBoost is not assumed to win |
| Runtime promotion | External evaluation does not automatically authorize production promotion |

---

## 8. External Claim Boundary

### Allowed claim

If the held-out gate passes:

> Decision Tree, XGBoost, and MLP were compared using the same frozen Logic Oasis U7 prediction contract on a recent subset of real ASSISTments Mathematics learner interactions, with identical base features, identical labelled rows, and student-grouped evaluation.

A model-specific conclusion must remain dataset bounded, for example:

> XGBoost achieved the strongest held-out predictive performance on the ASSISTments 2022-2023 external real-learner evaluation under the declared U7 contract.

### Not allowed

Do not claim that:

- ASSISTments students are Malaysian KSSR Year 4-6 users;
- ASSISTments metrics are direct Logic Oasis user metrics;
- the external evaluation proves learning improvement;
- U7 proves P3/P3a adaptive-policy superiority;
- an ASSISTments-trained model is automatically production-valid for Logic Oasis;
- competition unit-test scores were used as U7 base features;
- raw ASSISTments records are Logic Oasis U3 records;
- source rows have `runtime_callable`, `finalizationStatus`, `validationStatus`, or Logic Oasis `sourceAttemptSequence` semantics.

---

## 9. External Normalized Contract

Do not coerce source rows into native Logic Oasis trusted fields.

### 9.1 Normalized action row

```yaml
ExternalActionRow:
  datasetReleaseId: string
  externalStudentKey: string
  externalAssignmentKey: string
  externalSequenceKey: string|null
  externalProblemKey: string|null
  externalContentKey: string|null
  sourceTimestamp: datetime
  sourceActionType: string
  sourceGrade: string|null
  sourceSubject: string|null
  sourceSkillCode: string|null
  provenance: external_real
  sourceDataset: assistments_edm_cup_2023
  sourceWindow: "2022-01-01/2023-12-31"
```

### 9.2 Reconstructed U7 assignment-attempt row

```yaml
ExternalAttemptRow:
  datasetReleaseId: string
  externalAttemptId: string
  externalStudentKey: string
  externalAssignmentKey: string
  externalContentKey: string
  externalAttemptSequence: integer
  attemptStartedAt: datetime
  attemptEndedAt: datetime|null
  eligibleProblemCount: integer
  gradedProblemCount: integer
  correctFirstResponseCount: integer
  correct_rate: float
  mean_response_time_ms: float|null
  sourceGrade: string|null
  provenance: external_real
```

### 9.3 Forbidden fabricated fields

Never assign fake values to:

```text
finalizationStatus
validationStatus
dataSource = runtime_callable
Logic Oasis contentVersion
Logic Oasis policyVersion
Logic Oasis bankId
Logic Oasis sourceAttemptSequence
```

---

## 10. Frozen Attempt Reconstruction Strategy

### 10.1 Default prediction unit

The preferred external analogue of one Logic Oasis quiz attempt is one **in-unit assignment instance for one learner**.

Use the source's assignment identity rather than arbitrary fixed-size row grouping.

### 10.2 Correctness rule

For each eligible problem within an in-unit assignment, use the **first graded response**:

```text
first correct_response -> 1
first wrong_response   -> 0
```

Later correction attempts on the same problem do not retroactively change the first-response correctness label used for `correct_rate`.

Then:

```text
correct_rate
=
number of eligible problems whose first graded response is correct
/
number of eligible problems with a defensible first graded response
```

This rule must be implemented only if J0/J2 can reliably associate response events with the learner, assignment, and problem.

### 10.3 Response-time rule

For each eligible problem:

```text
problem_started at t_start
       ↓
first correct_response OR wrong_response at t_grade
       ↓
response_time_ms = (t_grade - t_start) converted to milliseconds
```

Then:

```text
mean_response_time_ms = mean(valid problem response_time_ms values)
```

### 10.4 Response-time exclusions

Exclude a problem response-time observation when:

- no defensible `problem_started` event exists;
- no subsequent graded response exists;
- the pairing crosses learner/assignment/problem identity;
- `t_grade < t_start`;
- timestamps are missing/unparseable;
- source ordering is ambiguous;
- duration fails the predeclared telemetry-quality rule frozen using training/development data only.

Never substitute assignment duration, hint time, or a different timing feature merely to make the contract fit.

### 10.5 Attempt minimum evidence

Do not require exactly five problems.

J2/J3 may freeze a minimum valid graded-problem count before held-out analysis if needed for stability. The threshold must be selected from source semantics/training-side quality evidence and recorded before final test inspection.

---

## 11. Target Construction

The frozen target remains:

```text
next_attempt_support_needed
```

For each current reconstructed assignment `t`:

1. identify the same external learner;
2. identify the approved compatible content/unit/skill context;
3. locate the first strictly later compatible in-unit assignment `t+1`;
4. calculate the next assignment's `correct_rate` using the same frozen reconstruction rule;
5. label the current assignment:
   - `true` if next `correct_rate < masteryCriterion`;
   - `false` if next `correct_rate >= masteryCriterion`;
6. if no compatible later assignment exists, censor the current assignment;
7. never use any `t+1` information as a feature for `t`.

### 11.1 Compatibility gate

A current→next pair must share a defensible stable context such as:

```text
same learner
+ Mathematics
+ compatible grade scope
+ same unit/sequence/content identity
```

If a narrower skill identity is available and sufficiently repeated, it may replace the broader unit/sequence identity, but the choice must be frozen in J2 before final held-out results.

### 11.2 Original EDM Cup labels are not the U7 target

`training_unit_test_scores.csv` and `evaluation_unit_test_scores.csv` belong to the original competition task. They do not replace `next_attempt_support_needed` in this FYP1 plan.

---

## 12. Feature Construction

### Base vector

Every Decision Tree, XGBoost, and MLP row must contain exactly:

```text
correct_rate
mean_response_time_ms
```

No ASSISTments-only field may be added to the base vector, including:

- grade;
- curriculum;
- unit-test score;
- problem text/embedding;
- hint count;
- explanation count;
- tutoring option;
- answer request count;
- school/class/teacher data;
- sequence ID;
- problem/skill ID.

These may be used only for filtering, grouping, audit, compatibility, or separate predeclared ablation where allowed by the canonical plan.

---

## 13. BKT Ablation Contract

BKT is not a fourth classifier in the fair comparison.

### Run BKT only if all gates pass

- response-level correctness order is deterministic;
- learner/content sequence linkage is stable;
- no ambiguous ordering remains after source tie handling;
- the BKT state at current attempt uses only responses available up to that current point.

If those gates pass, compare:

```text
base:
correct_rate + mean_response_time_ms

vs

ablation:
correct_rate + mean_response_time_ms + bkt_mastery_probability
```

If the gates fail, mark the external BKT ablation unavailable and preserve native Logic Oasis BKT evidence separately.

---

## 14. Filtering Order

Apply filters in this exact order:

```text
Kaggle EDM Cup 2023 raw files
    ↓
accepted access + source hashes recorded
    ↓
strict timestamp window: 2022-01-01 .. 2023-12-31
    ↓
valid source schema / joins
    ↓
Mathematics
    ↓
Grade 6 primary cohort where sufficient
    ↓
valid learner + assignment + problem linkage
    ↓
valid graded response events
    ↓
valid response-time start→first-grade pairs
    ↓
reconstructed in-unit assignments
    ↓
repeated compatible learner-content histories
    ↓
current→next labels
    ↓
both target classes across multiple independent learners
```

Never add synthetic or seed rows to force a gate to pass.

---

## 15. Data-Sufficiency Gates

| Gate | Minimum condition | Allowed conclusion |
|---|---|---|
| J0 source validation | Required tables/fields/joins/timestamps/response pairing are defensible | Source supports frozen U7 semantics |
| Pipeline/demo | At least one valid current→next path runs end-to-end | Adapter works; no performance claim |
| Preliminary comparison | Both target classes across multiple independent learners; grouped validation feasible | Preliminary external-real-data metrics |
| Held-out comparison | Independent student-grouped held-out set preserves both classes | Held-out external-real-data comparison |
| Cautious advantage | Repeated/grouped evidence shows stable practical advantage with uncertainty | Dataset-bounded advantage statement |
| Production promotion | Separate target-domain and supervisor approval | Only then consider runtime activation |

If Grade 6 fails the data-sufficiency gates, apply the predeclared Grades 4-6
Mathematics fallback (frozen in the J2 contract) and report both the Grade 6
insufficiency and the fallback evidence separately.

---

## 16. Student-Grouped Split and Leakage Controls

All records for one learner remain in one split.

```text
Student A -> train only
Student B -> train only
Student C -> held-out only
```

Preserve the canonical U7 split seed where applicable:

```text
20260716
```

### Leakage prohibitions

- no future assignment action may enter current features;
- no unit-test score may enter base features;
- no per-learner normalization may be fit using held-out future rows;
- preprocessing parameters are fit on training learners only;
- held-out test results are not used to choose response-time cleaning thresholds, content grouping, mastery criterion, model hyperparameters, or class weights.

---

## 17. Fair Model Comparison

Train and evaluate:

1. Decision Tree;
2. XGBoost;
3. small regularized MLP.

All three must use:

- the exact same labelled rows;
- the exact same two base features;
- the exact same student-group split;
- the exact same target version;
- training-only preprocessing;
- the same metric definitions.

MLP early stopping remains **disabled** for FYP1.

XGBoost is not presumed to win.

---

## 18. Required Metrics and Evidence

### Classification

- accuracy;
- precision;
- recall;
- F1;
- ROC-AUC;
- PR-AUC where appropriate;
- confusion matrix.

### Probability quality

- log loss;
- Brier score;
- calibration summary/curve when supported.

### Data/reproducibility audit

- source file names and hashes;
- acquisition date;
- Kaggle competition identifier;
- ASSISTments Data Terms of Use reference;
- 2022-2023 filter counts;
- learner count;
- Grade 6 count and fallback status;
- reconstructed assignment count;
- labelled/censored count;
- class balance;
- student-group split counts;
- response-time pairing coverage and quality;
- attempt-size distribution;
- content compatibility mapping version;
- BKT ordering availability.

### Operational

- inference latency;
- serialized model size;
- model complexity;
- invalid/failure prediction count.

### Interpretability

- Decision Tree structure/rule summary;
- XGBoost SHAP global summary;
- selected non-identifying local SHAP examples;
- MLP interpretability limitation.

---

## 19. Model Selection and Runtime-Promotion Boundary

U7 may identify the strongest **external-evaluation candidate** according to measured predictive quality, probability quality, interpretability, and operational trade-offs.

Default FYP1 decision:

```text
external ASSISTments evaluation result
        = U7 report evidence

external-trained artifact
        = candidate/evaluation artifact

active Logic Oasis production replacement
        = NO by default
```

A separate target-domain/supervisor decision is required before any external-trained model can become the active Logic Oasis runtime model.

---

## 20. Approval and Governance Record

The previously recorded supervisor/institutional approval for using an approved external real-learner dataset route remains the project governance basis for this plan.

Record conceptually:

```yaml
externalDatasetApproval:
  dataset: assistments_edm_cup_2023
  sourceKind: external_real
  selectedWindowStart: "2022-01-01"
  selectedWindowEnd: "2023-12-31"
  approvedFor: u7_offline_model_comparison
  approvalStatus: recorded_for_external_real_route
  approvalRecordedAt: "2026-08-07"
  usageTermsReviewed: true
  directTargetUserEvaluation: false
  productionPromotionAuthorized: false
```

If the actual approval record explicitly names **Junyi only**, update that record to name ASSISTments before J4 final model-evidence execution. This does not block J0 schema inspection, but final evidence must not be represented as institutionally approved under the wrong dataset name.

---

## 21. Implementation Units

### J0. Physical source-schema and U7-feasibility validation

**Goal:** Validate the actual Kaggle EDM Cup 2023 CSV headers, source relationships, timestamp semantics, graded-response semantics, and response-time derivation before any large-scale transformation.

**Estimate:** 0.5 day.

**Precondition:** User has joined the Kaggle competition, accepted its rules, and placed the required CSVs in the protected external-data directory.

**Planned files:**

- Create `ai_pipeline/external_data/assistments/README.md`.
- Create `ai_pipeline/external_data/assistments/inspect_assistments.py`.
- Create `ai_pipeline/external_data/assistments/assistments_schema_mapping_v1.yaml`.
- Create `ai_pipeline/tests/test_assistments_schema_contract.py`.
- Create `docs/evidence/u7-assistments-source-validation.md`.

**J0 must:**

1. inspect headers and bounded samples first;
2. compute source file hashes/metadata;
3. resolve exact physical fields for learner, assignment, problem, sequence/unit/content, timestamp, and action type;
4. verify relationship-table joins needed for learner-content chronology;
5. verify correct/wrong action values;
6. verify `problem_started` or equivalent start event exists;
7. prove a defensible start→first-graded-response pairing can be constructed;
8. verify Mathematics/grade metadata and Grade 6 representation;
9. verify strict 2022-2023 date filtering on actual timestamp values;
10. check timestamp tie behavior and deterministic response ordering for optional BKT;
11. explicitly verify that unit-test score tables are not required as base features;
12. write the physical→semantic mapping without guessing field names.

**Base-U7 J0 GO conditions:**

- stable learner identity resolved;
- in-unit assignment identity resolved;
- problem identity/linkage resolved;
- content/unit/sequence compatibility identity resolved;
- source timestamp resolved;
- correct/wrong graded-response semantics resolved;
- start→first-graded-response timing can be reconstructed defensibly;
- strict 2022-2023 filter verified;
- Mathematics scope resolved.

**Separate BKT condition:** deterministic fine-grained response order/content sequence exists.

**J0 NO-GO conditions:**

- response events cannot be linked to the correct learner/assignment/problem;
- no defensible start→first-graded-response timing can be derived;
- timestamps do not support chronological current→next assignment ordering;
- Grade/curriculum/content relationships cannot support defensible compatible histories;
- the physically downloaded files differ materially from the documented EDM Cup source.

If J0 is GO, stop and report that J1 is ready. Do not automatically continue to J1 in the same execution unless explicitly instructed.

---

### J1. Versioned external-real-data adapter and manifest

**Goal:** Normalize only eligible 2022-2023 ASSISTments source rows into an auditable external contract.

**Estimate:** 0.5-1 day.

**Planned files:**

- Create `ai_pipeline/external_data/assistments/schemas.py`.
- Create `ai_pipeline/external_data/assistments/adapter.py`.
- Create `ai_pipeline/external_data/assistments/manifest.py`.
- Create `ai_pipeline/tests/test_assistments_adapter.py`.
- Update `.gitignore` for protected working-data patterns if required.

**Approach:**

- `provenance: external_real` only;
- strict 2022-2023 filter;
- project-local stable learner keys for processing;
- no publication of source learner identifiers;
- retain only required audit/grouping fields;
- preserve source terms/acquisition/hash metadata;
- fail closed on unresolved required fields;
- never generate fake U3 statuses.

---

### J2. Reconstruct in-unit assignment attempts and freeze labels

**Goal:** Build leakage-safe current attempts and chronological next-attempt labels.

**Estimate:** 0.5-1 day.

**Planned files:**

- Create `ai_pipeline/external_data/assistments/reconstruct_attempts.py`.
- Create `ai_pipeline/external_data/assistments/build_labels.py`.
- Create `ai_pipeline/tests/test_assistments_attempt_reconstruction.py`.
- Create `ai_pipeline/tests/test_assistments_next_attempt_labels.py`.

**Approach:**

- one learner-specific in-unit assignment instance = one external attempt;
- first graded response per problem determines correctness;
- response time = problem start→first graded response;
- freeze validity/censoring rules before held-out analysis;
- freeze compatible content identity;
- freeze mastery criterion;
- label current attempt only from next strictly later compatible attempt.

**Required tests:**

- later correction does not alter first-response correctness;
- response-time pairing never crosses problem/assignment/learner identity;
- future rows cannot change current features;
- missing next attempt remains censored;
- incompatible transitions are censored;
- same input produces identical IDs/order/labels;
- out-of-window actions cannot enter attempts.

---

### J3. Build frozen two-feature U7 table and readiness report

**Goal:** Produce the exact rows used by all three models and determine the permitted claim level before model interpretation.

**Estimate:** 0.5 day.

**Planned files:**

- Create `ai_pipeline/external_data/assistments/build_u7_dataset.py`.
- Create `ai_pipeline/reports/u7_assistments_data_readiness.md`.
- Create `ai_pipeline/tests/test_assistments_u7_feature_contract.py`.

**Approach:**

- emit only `correct_rate`, `mean_response_time_ms`;
- primary Grade 6 cohort first;
- apply the predeclared exact Grades 4-6 Mathematics fallback only if Grade 6 fails the data-sufficiency gates;
- student-grouped split using seed `20260716`;
- verify both target classes in train and held-out groups;
- record censoring, response-time coverage, class balance, learner counts, attempt counts, and content coverage;
- record BKT availability separately.

---

### J4. Fair Decision Tree vs XGBoost vs MLP evaluation

**Goal:** Close the missing U7 real-data model-performance result.

**Estimate:** 0.5-1 day.

**Planned work:**

- reuse `ai_pipeline/training/train_decision_tree.py`;
- reuse `ai_pipeline/training/train_xgboost.py`;
- reuse `ai_pipeline/training/train_mlp.py`;
- modify `ai_pipeline/training/evaluate_models.py` only as needed to accept the external manifest without weakening native source validation;
- update notebook evidence only if required;
- add regression tests proving identical rows/features/split.

**Approach:**

- training-only preprocessing;
- identical features/labels/rows;
- MLP early stopping disabled;
- held-out students untouched by tuning;
- report uncertainty and data-sufficiency level.

---

### J5. SHAP, operational evidence, and conditional BKT ablation

**Goal:** Complete interpretability and architecture evidence beyond headline scores.

**Estimate:** 0.5 day.

**Approach:**

- XGBoost SHAP global summary;
- selected non-identifying local examples;
- model size and latency;
- Decision Tree complexity summary;
- MLP interpretability limitation;
- BKT ablation only if J0/J2 ordering gates pass.

---

### J6. Final U7 external-real-data report

**Goal:** Replace the current placeholder/no-final-result state with the strongest valid external-real-data evidence achieved.

**Estimate:** 0.5 day.

**Planned files:**

- Modify `ai_pipeline/reports/model_comparison.md`.
- Create `docs/evidence/u7-assistments-external-real-data-release.md`.
- Update `ai_pipeline/models/README.md` with candidate/evidence status.

**Minimum report contents:**

1. ASSISTments EDM Cup 2023 source and acquisition route;
2. ASSISTments Data Terms of Use and no-redistribution boundary;
3. strict 2022-2023 window;
4. Grade 6 primary scope and fallback status;
5. external-domain/KSSR limitation;
6. schema/reconstruction/label versions;
7. mastery criterion;
8. exact two-feature schema;
9. learner-group split and class balance;
10. DT/XGBoost/MLP metrics;
11. confusion matrices;
12. probability/calibration metrics;
13. SHAP evidence;
14. BKT result or explicit unavailability;
15. latency/model size;
16. response-time quality/coverage;
17. censoring and data-sufficiency level;
18. model-selection rationale;
19. explicit non-promotion decision unless separately approved.

---

## 22. Proposed Repository Layout

```text
ai_pipeline/
  external_data/
    assistments/
      README.md
      assistments_schema_mapping_v1.yaml
      schemas.py
      inspect_assistments.py
      adapter.py
      manifest.py
      reconstruct_attempts.py
      build_labels.py
      build_u7_dataset.py
  reports/
    model_comparison.md
    u7_assistments_data_readiness.md
  tests/
    test_assistments_schema_contract.py
    test_assistments_adapter.py
    test_assistments_attempt_reconstruction.py
    test_assistments_next_attempt_labels.py
    test_assistments_u7_feature_contract.py

docs/
  evidence/
    u7-assistments-source-validation.md
    u7-assistments-external-real-data-release.md
```

Raw competition data and normalized learner-level extracts remain outside the repository.

---

## 23. Acceptance Gates

### A. Source/access/terms gate

- [x] ASSISTments EDM Cup 2023 selected.
- [x] Real Mathematics learner clickstream source confirmed.
- [x] `action_logs.csv` physically listed in Kaggle Data Explorer.
- [x] Nine supporting source CSVs physically listed.
- [x] ASSISTments Data Terms of Use identified.
- [x] Non-commercial requirement recorded.
- [x] Citation requirement recorded.
- [x] No-de-anonymization requirement recorded.
- [x] No-redistribution requirement recorded.
- [x] Strict 2022-2023 analysis window frozen.
- [x] External-real approval route recorded.
- [ ] Kaggle competition joined and rules accepted on the executing account.
- [ ] Required CSV files downloaded/accessed in protected local path.

The final two items are execution preconditions, not remaining dataset-selection research.

### B. J0 physical-schema gate

- [ ] Exact physical headers recorded.
- [ ] Learner key resolved.
- [ ] Assignment key resolved.
- [ ] Problem key resolved.
- [ ] Sequence/unit/content relationship resolved.
- [ ] Timestamp field/unit/timezone semantics resolved.
- [ ] Correct/wrong action values resolved.
- [ ] Problem-start event resolved.
- [ ] Start→first-graded-response timing verified.
- [ ] Mathematics and Grade 6 filters resolved.
- [ ] 2022-2023 boundary tests pass.
- [ ] BKT ordering availability recorded.

### C. Reconstruction gate

- [ ] First-response correctness implemented.
- [ ] Response-time pairing deterministic.
- [ ] No cross-problem/assignment/learner pairing.
- [ ] Compatible content identity frozen.
- [ ] Chronology deterministic.
- [ ] Missing next attempt censored.
- [ ] No future leakage.

### D. Feature gate

- [ ] Exact base feature names are `correct_rate`, `mean_response_time_ms`.
- [ ] No source-only field added to base vector.
- [ ] Response-time quality rule frozen before held-out analysis.
- [ ] BKT feature only appears in named ablation if approved by ordering gate.

### E. Fair-comparison gate

- [ ] DT/XGBoost/MLP use identical rows.
- [ ] Same student-group split.
- [ ] No learner overlap across train/held-out.
- [ ] MLP early stopping disabled.
- [ ] Held-out set not used for tuning.

### F. Evidence gate

- [ ] Both target classes exist across multiple learners.
- [ ] Grade 6 sufficiency status recorded.
- [ ] Broader middle-school fallback, if used, is separately labelled.
- [ ] Achieved evidence level named.
- [ ] Metrics/limitations recorded.
- [ ] SHAP recorded.
- [ ] BKT ablation recorded or explicitly unavailable.
- [ ] Final conclusion follows measured results.

### G. Claim/promotion gate

- [ ] Report says external real-learner evidence, not direct KSSR validation.
- [ ] No learning-effect/policy-superiority claim made from U7.
- [ ] External-trained artifact remains non-production unless separately approved.

---

## 24. Risks and Mitigations

| Risk | Consequence | Mitigation |
|---|---|---|
| Kaggle competition access not accepted | Files cannot be downloaded/read | Join competition and accept rules before J0 |
| Raw data redistributed accidentally | Violates ASSISTments terms | Keep outside Git; publish code/aggregate outcomes only |
| Exact physical column names differ from literature | Wrong joins/semantics | J0 header/sample inspection + versioned mapping |
| `problem_started` cannot be paired reliably to first graded response | `mean_response_time_ms` invalid | J0 NO-GO rather than silent feature substitution |
| Multiple attempts per problem | Inflated correctness if final outcome used | Freeze first graded response semantics |
| Unit-test scores leak future outcomes | Invalid comparison | Explicitly exclude competition score tables from base U7 features/target |
| Grade 6 too sparse | Weak target-age evidence | Predeclared exact Grades 4-6 Mathematics fallback with separate limitation |
| Curriculum mismatch | Metrics may not generalize to KSSR | External-domain wording; no fabricated KSSR mapping |
| Row-level learner leakage | Inflated metrics | Student-grouped split only |
| Future assignment leakage | Invalid target | Feature timestamp boundary + leakage tests |
| Timing outliers / idle time | Noisy response-time feature | Training-side quality audit and frozen censoring/capping rule |
| XGBoost assumed to win | Biased conclusion | Same rows/features/split; measured evidence controls selection |
| External artifact auto-promoted | Domain mismatch | Evidence-only candidate by default |
| Approval record names Junyi only | Governance mismatch | Update dataset name before J4 final evidence run |

---

## 25. Recommended Execution Order

```text
PRE-J0  Join Kaggle competition + accept rules + place source CSVs in protected path
   ↓
J0  Resolve physical schema, joins, timestamps, first-response and timing contract
   ↓
J1  Build external_real adapter + manifest
   ↓
J2  Reconstruct in-unit assignments + freeze next-attempt labels
   ↓
J3  Build exact two-feature dataset + data-sufficiency gate
   ↓
J4  Decision Tree vs XGBoost vs MLP
   ↓
J5  XGBoost SHAP + operational evidence + conditional BKT ablation
   ↓
J6  Update final model_comparison.md
   ↓
NEXT  Reuse compatible external histories for later P1/P2/P3a Stage-B work only after its own mapping gate
```

### Estimated focused implementation time

- Pre-J0 download/access: variable, mostly download time
- J0: 0.5 day
- J1: 0.5-1 day
- J2: 0.5-1 day
- J3: 0.5 day
- J4: 0.5-1 day
- J5: 0.5 day
- J6: 0.5 day

**Total implementation:** approximately **3.0-5.0 focused working days**, excluding download time and unexpected source-format issues.

---

## 26. Definition of Done

This companion plan is complete when:

1. Kaggle EDM Cup 2023 access is accepted through the authorized account;
2. ASSISTments source files are stored outside Git and source hashes are recorded;
3. only 2022-01-01 through 2023-12-31 source interactions enter final evidence;
4. Grade 6 is evaluated as the primary cohort where sufficient;
5. physical headers/joins/actions/timestamps are frozen in a schema mapping;
6. first graded response per problem defines correctness;
7. start→first-graded-response timing produces defensible `mean_response_time_ms`;
8. current→next compatible in-unit assignments construct `next_attempt_support_needed` without leakage;
9. base features are exactly `correct_rate` and `mean_response_time_ms`;
10. Decision Tree, XGBoost, and MLP use identical student-grouped rows and split;
11. the achieved evidence gate is reported honestly;
12. classification, calibration, SHAP, latency/model-size, timing-quality, and limitation evidence is recorded;
13. BKT is a separately gated ablation, not a fourth classifier;
14. final results are labelled external real-learner evidence, not KSSR target-user validation;
15. raw/normalized ASSISTments learner data is not redistributed;
16. no external-trained artifact is promoted to Logic Oasis production without separate approval;
17. `model_comparison.md` no longer states “no final model-performance result” when a valid preliminary/held-out gate has passed.

---

## 27. Source Alignment Notes

### Canonical Logic Oasis sources

This plan remains aligned with:

- `2026-07-05-001-feat-fyp1-prototype-development-plan(2)(1)(2).md` — canonical FYP1 authority;
- `ai_pipeline/reports/model_comparison.md` — current U7 evidence gap;
- the CRISP-DM/pipeline companion documents — native trust, leakage prevention, BKT/XGBoost/SHAP responsibilities, and evidence boundaries.

### External dataset references

**EDM Cup 2023 / ASSISTments**

- Kaggle competition data page: `https://www.kaggle.com/competitions/edm-cup-2023/data`
- Kaggle competition rules page: `https://www.kaggle.com/competitions/edm-cup-2023/rules`
- Educational Data Mining Society EDM Cup 2023 description: `https://educationaldatamining.org/edm2023/edm-cup-2023/`
- ASSISTments Data Terms of Use: effective 2020-10-30; retain the local terms record used for this project.

Published EDM/JEDM descriptions used for semantic planning establish that the dataset contains Mathematics clickstream actions, assignments, sequences, problems, timestamps, correct/wrong actions, and curriculum/grade context. J0 remains responsible for freezing the exact physical Kaggle column names and join semantics from the actual downloaded release.

---

## 28. Plan Status After Dataset Switch

```yaml
status: implementation-ready
selected_external_dataset: assistments_edm_cup_2023
superseded_dataset: junyi_user_demographics_2019_2024
implementation_entrypoint: J0
remaining_research_blocker: none
remaining_execution_preconditions:
  - accept_kaggle_competition_rules
  - download_or_mount_required_source_files
  - provide_external_data_root_to_codex
```

No further public dataset-selection research is required before J0. J0 is intentionally responsible for the remaining physical-column and source-semantic validation.
