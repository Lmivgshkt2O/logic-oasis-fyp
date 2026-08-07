# U7 ASSISTments EDM Cup 2023 source validation (J0)

Date: 2026-08-07
Plan: `docs/plans/2026-08-07-001-feat-u7-assistments-edm-cup-2023-external-real-data-evaluation-plan.md`
Scope: **J0 only**. No dataset transformation, label generation, model
training, BKT replay, SHAP generation, or model promotion was performed.
Decision: **GO FOR BASE U7**

## 1. Physical source files detected

Protected raw root used for this run:

```text
C:\Users\zyonn\Documents\FYP\logic_oasis_private_data\assitments_edm_cup_2023\raw
```

Deviation note: the request named
`logic-oasis-private-data\assistments_edm_cup_2023 \raw`; the physically
existing protected directory is `logic_oasis_private_data\assitments_edm_cup_2023\raw`
(underscores, and the dataset folder carries the Kaggle-release spelling
`assitments`). The resolved path above is the one that was inspected.

| File | Size (bytes) | SHA-256 | Source role | Required for base U7 | Excluded from base features |
|---|---|---|---|---|---|
| action_logs.csv | 1,438,057,277 | `DB6B0CD4875488D0847D9D9BA2896552F4AD1015F3E2388995222DD4A178443D` | Learner interaction chronology and graded responses | Yes | No |
| assignment_details.csv | 966,175,816 | `D02D8B62DE088C896FCEB901BC986C25FA07F5D9AEEC0364BF9D351208BEC70E` | Assignment instance, learner, sequence, chronology | Yes | No |
| problem_details.csv | 61,843,139 | `4F45DAF2E010771C6B5E523DD4D583F3AC451F6CE8F2F35270FCB86B875CEE4E` | Problem identity and Mathematics skill metadata | Yes | No |
| sequence_details.csv | 3,996,722 | `A1FA10E6DEBD4FD30C4B04E1554E18F2C426A981BCB10BED0B41DD083CCDB541` | Sequence/unit and curriculum/grade hierarchy | Yes | No |
| assignment_relationships.csv | 14,942,545 | `155ADB0382B194A4F6DDDCB613CEB782805ABA35DCC16B13E2717549D00015AD` | Unit-test to in-unit assignment relationship | No | Yes |
| sequence_relationships.csv | 279,575 | `BEEB428DFAFBC7C31E0485F28AEAC5653F868D67A9B5FE26E7720FC29898CC2B` | Unit-test to in-unit sequence relationship | No | Yes |

No base-U7-required source file is missing. Hashes were computed with SHA-256
over the physical files on 2026-08-07; the machine-readable scan summary was
written to the protected `j0/scan-summary.json` (outside Git).

### Files expected by the Kaggle release but absent locally

`training_unit_test_scores.csv`, `evaluation_unit_test_scores.csv`,
`hint_details.csv`, and `explanation_details.csv` are **not physically
present** in the downloaded release. They are recorded in the schema mapping as
excluded source tables and are not required for base U7; their absence does not
block J0.

## 2. Physical -> semantic field mapping

Detected columns (no guesses; frozen in
`ai_pipeline/external_data/assistments/assistments_schema_mapping_v1.yaml`):

| Semantic concept | Physical table | Physical field(s) |
|---|---|---|
| Learner identifier | assignment_details.csv | `student_id` |
| Assignment instance (learner-specific in-unit assignment) | assignment_details.csv | `assignment_log_id` |
| Problem identifier | action_logs.csv / problem_details.csv | `problem_id` |
| Sequence/unit identifier | assignment_details.csv / sequence_details.csv | `sequence_id` |
| Event/action type | action_logs.csv | `action` |
| Event timestamp | action_logs.csv | `timestamp` (epoch seconds, UTC, ms precision) |
| Grade | sequence_details.csv | `sequence_folder_path_level_2` (exact `Grade N`) |
| Subject / Mathematics | problem_details.csv | `problem_skill_code` (CCSS-aligned; dataset is Mathematics by design) |
| Curriculum/unit/topic context | sequence_details.csv | `sequence_folder_path_level_1..5`, `sequence_name` |
| Assignment chronology | assignment_details.csv | `assignment_start_time` (plus release/due/end) |
| Problem/skill relationship | problem_details.csv | `problem_id`, `problem_skill_code`, `problem_skill_description`, `problem_type` |
| Sequence/problem relationship | sequence_details.csv | `sequence_problem_ids` (bare-token list literal) |
| Assignment/sequence relationship | assignment_details.csv | `assignment_log_id`, `sequence_id` |

## 3. Learner/assignment/problem/sequence join findings

- action_logs has 23,932,276 rows and 638,528 unique `assignment_log_id`
  values; **every** action-log assignment id resolves in assignment_details
  (0 orphans).
- assignment_details has 9,319,676 rows; `student_id`, `teacher_id`,
  `class_id`, `sequence_id`, and `assignment_log_id` are non-null on every row.
- Every action-bearing assignment log has exactly one `assignment_started`
  event.
- **Every** action-log assignment id appears as an
  `in_unit_assignment_log_id` in assignment_relationships (638,528 / 638,528)
  and none appear as unit-test assignment ids. The action logs therefore cover
  exactly the planned U7 prediction unit: in-unit assignments.
- All 130,308 problem ids referenced by sequence_details resolve in
  problem_details (0 unresolved).
- 8,774 distinct sequence ids used by assignments all resolve in
  sequence_details.
- `sequence_problem_ids` values are bare-token lists
  (`[AQ0ZKSP6D,2KTD380L98,...]`) and parse cleanly.

## 4. Actual action/event values (exact capitalization)

Observed `action_logs.action` values and counts:

| Action value | Count | Graded? | Used for base U7 |
|---|---|---|---|
| `problem_started` | 5,245,860 | No | Yes (start anchor, eligibility) |
| `problem_finished` | 5,140,911 | No | Audit only |
| `continue_selected` | 4,602,358 | No | No |
| `correct_response` | 3,587,501 | Yes (correct = 1) | Yes |
| `wrong_response` | 1,580,102 | Yes (correct = 0) | Yes |
| `open_response` | 1,541,432 | No (ungraded submission) | No |
| `assignment_started` | 638,528 | No | Assignment audit |
| `answer_requested` | 603,988 | No | No |
| `assignment_finished` | 531,285 | No | Assignment audit |
| `assignment_resumed` | 364,544 | No | Assignment audit |
| `hint_requested` | 73,343 | No | No |
| `explanation_requested` | 21,136 | No | No |
| `skill_related_video_requested` | 1,130 | No | No |
| `live_tutor_requested` | 158 | No | No |

`correct_response` and `wrong_response` are the only graded response actions.
`open_response` submissions never co-occur with graded responses for the same
problem key, so they are excluded from correctness rather than treated as
ungraded-correct. There are no other graded response action types.

## 5. Timestamp field and unit

- Field: `action_logs.timestamp` (and assignment time fields in
  assignment_details).
- Unit: **epoch seconds** (float) with millisecond precision, interpreted as
  UTC.
- Verified conversion: `1599150988.995` -> `2020-09-03T16:36:28.995Z`.
- action_logs bounds: `2019-02-25T19:20:57.474Z` .. `2023-01-24T17:38:32.573Z`.
- assignment_details `assignment_due_date` contains a rare outlier
  (`70464012120`, i.e. year 4202); it is a data-quality note, not a base
  feature.

## 6. Response-time derivation feasibility

Rule confirmed feasible: for each eligible problem,

```text
response_time_ms = (first graded response timestamp - problem_started timestamp) * 1000
```

Bounded feasibility sample (3,000 action-bearing assignments, 114,133 rows,
seed 20260807):

- 25,041 problems examined; **all** have a `problem_started` event.
- 17,074 (68.2%) have a later graded response; the remainder are
  open-response/ungraded or abandoned problems and are excluded from the
  correctness denominator and response-time means.
- **0** graded responses occur without a matching `problem_started`.
- **0** problems have multiple `problem_started` events within one assignment
  (problem instance identity is unambiguous).
- 4,115 problems (16.4%) have more than one graded response; the
  first-graded-response rule resolves these deterministically.
- Durations (n = 17,074): min 348 ms, max ~6.74e9 ms (~78 days), mean
  ~3.73e6 ms (~62 min). Negative durations: 0. Zero durations: 0. Extreme idle
  outliers exist and are reserved for the later frozen telemetry-quality rule;
  no proxy (assignment duration, time-on-platform, hint time, inter-event time)
  is used.
- Exact duplicate action rows: 0, so deterministic ordering by
  `(timestamp, file row ordinal)` is safe.

## 7. Correctness contract feasibility

The physical event structure supports the planned rule:

```text
problem_started -> first valid graded response (correct_response/wrong_response)
correct = 1 if correct_response, 0 if wrong_response
```

Repeated responses (e.g. wrong, wrong, correct) are resolved by first graded
response; later corrections do not change the label. Graded responses without a
problem start and problems without a graded response are excluded, never
guessed. The final `correct_rate` dataset was **not** calculated in J0.

## 8. Grade 6 Mathematics filter

- Grade is represented by the exact `sequence_folder_path_level_2` token
  (`Grade 1` through `Grade 8`); `Grade 6 Accelerated` is a distinct token and
  is **not** merged into the primary Grade 6 cohort during J0.
- Corroboration: CCSS `problem_skill_code` values embed the grade
  (`6.RP.A.3b` -> grade 6).
- `sequence_folder_path_level_2 == "Grade 6"` identifies 792 sequences and
  9,460 referenced problems.
- In the 2022-2023 window (by `assignment_start_time`), Grade 6 accounts for
  267,720 assignment logs (21.7% of 1,232,758 in-window logs) across 23,961
  unique students; 30,199 of those assignment logs (1,483 students) also have
  action logs. Grade 6 is therefore present and non-trivial; the statistical
  sufficiency gate belongs to J3, not J0.

## 9. Strict 2022-2023 date-window verification

Full-scan year distribution of action_logs:

| Year | Rows |
|---|---:|
| 2019 | 101,907 |
| 2020 | 13,483,650 |
| 2021 | 7,526,341 |
| 2022 | 2,819,588 |
| 2023 | 790 |
| 2024+ | 0 |

- Rows inside `2022-01-01T00:00:00Z .. 2023-12-31T23:59:59Z`: **2,820,378**
  (in-window bounds `2022-01-01T20:33:31.542Z` .. `2023-01-24T17:38:32.573Z`).
- Rows before 2022: 21,111,898; rows after 2023: 0.
- The release contains almost no 2023 actions (790 rows in January 2023); the
  boundary tests below prove the filter logic itself, and the evidence window
  will therefore be dominated by 2022 rows.
- Automated boundary tests: 2021-12-31T23:59:59Z excluded, 2022-01-01T00:00:00Z
  included, 2023-12-31T23:59:59Z included, 2024-01-01T00:00:00Z excluded,
  missing/unparseable timestamps excluded (fail closed).

## 10. Assignment reconstruction feasibility

The source supports the planned attempt unit: one learner-specific in-unit
assignment instance, grouped by `assignment_log_id`, with `student_id`,
`sequence_id`, and `assignment_start_time` available on every assignment log.
Assignment chronology is unambiguous (`assignment_start_time` epoch seconds),
relationship to problems is available through sequence membership plus
problem-level action rows, and repeated assignment instances are naturally
separated by distinct `assignment_log_id` values. No final attempts were
constructed in J0.

## 11. Next-compatible-assignment feasibility

Yes, technically supported:

- Student chronology exists (`assignment_start_time` per assignment log).
- Compatible learning context is definable from the sequence hierarchy
  (`sequence_id` plus level_1..5 folder paths).
- Current -> next pairing is constructible by ordering a student's compatible
  in-unit assignments chronologically and comparing the next assignment's
  `correct_rate` against the frozen mastery criterion (default 0.60).
- Future leakage is preventable: features use current-assignment actions only,
  and the competition unit-test score tables (absent locally anyway) are
  excluded from base features and targets.

## 12. BKT ordering status

**AVAILABLE.** action_logs carries millisecond-precision epoch timestamps, has
zero exact duplicate rows, and provides per-problem graded response sequences
(e.g. wrong, wrong, correct). Deterministic ordering is `(timestamp, file row
ordinal)` within `(assignment_log_id, problem_id)`. Caveat: graded responses
exist only for auto-graded problems (~68% of problem starts); BKT remains a
separately gated ablation, not a fourth directly comparable classifier, and
does not block the base U7 comparison.

## 13. Data governance

- Source provenance is frozen as **external_real**.
- ASSISTments rows are never relabelled as `runtime_callable` or native Logic
  Oasis quiz attempts; no native fields (`finalizationStatus`,
  `validationStatus`, `sourceAttemptSequence`, `contentVersionId`, bank or
  policy metadata) are fabricated.
- Raw CSVs and learner-level extracts stay outside Git; the schema mapping,
  code, tests, and this evidence document are committed.
- ASSISTments Data Terms of Use (effective 2020-10-30) are recorded in the
  README: non-commercial academic/research use, citation of ASSISTments and the
  EDM Cup 2023 dataset, no de-anonymization attempts, no redistribution.

## 14. Files created

- `ai_pipeline/external_data/assistments/README.md`
- `ai_pipeline/external_data/assistments/assistments_schema_mapping_v1.yaml`
- `ai_pipeline/external_data/assistments/assistments_contract.py`
- `ai_pipeline/external_data/assistments/inspect_assistments.py`
- `ai_pipeline/tests/test_assistments_schema_contract.py`
- `docs/evidence/u7-assistments-source-validation.md`

No existing runtime, feature, prediction-contract, or training files were
modified; no Flutter/Firebase behaviour changed.

## 15. Tests executed and results

`python -m unittest tests.test_assistments_schema_contract -v` from
`ai_pipeline`: **30/30 passed**, covering required schema concepts, physical ->
semantic mapping validation against detected headers, missing required field
rejection, date lower/upper boundaries, unparseable date rejection,
correctness-event recognition, response-time unit conversion, negative
response-time rejection, missing start/response pairing, the Grade 6 filter,
`external_real` provenance, and prevention of native provenance substitution.

## 16. Remaining limitations

- The downloaded release contains only 790 action rows in 2023 (all January),
  so the strict 2022-2023 evidence window is dominated by 2022 data. The
  report wording requirement from the plan ("restricted eligible clickstream
  interactions to 2022-2023") is preserved.
- Action logs cover 638,528 of 9,319,676 assignment logs; the remaining
  assignment logs have no captured actions and cannot contribute problem-level
  evidence.
- `open_response` problems (~32% of problem starts in the sample) have no
  logged correctness and are excluded from `correct_rate`; this is by design,
  not a silent substitution.
- Extreme response-time outliers (up to ~101 days) require the later frozen
  telemetry-quality capping rule; the J0 contract rejects negative durations
  and never substitutes proxy timings.
- `assignment_due_date` contains a rare out-of-range placeholder; it is not a
  base feature.
- Grade is derived from sequence folder metadata and corroborated by CCSS skill
  codes; `Grade 6 Accelerated` is tracked separately from the primary Grade 6
  cohort.

## 17. J0 decision

All twelve mandatory base-U7 GO conditions are defensibly resolved:

1. learner identity - `assignment_details.student_id`
2. assignment identity - `assignment_details.assignment_log_id`
3. problem identity - `problem_id` (action_logs/problem_details)
4. assignment/problem/content joins - fully resolved (0 orphans)
5. deterministic usable timestamps - epoch seconds UTC, ms precision
6. graded correctness outcome - `correct_response`/`wrong_response`
7. problem-start -> first-graded-response pairing - verified on sample
8. response-time conversion to milliseconds - verified; negative rejected
9. Grade 6 Mathematics filtering - `sequence_folder_path_level_2 == "Grade 6"`
10. assignment chronology - `assignment_start_time`
11. compatible current -> next assignment construction - feasible
12. strict 2022-01-01 through 2023-12-31 filtering - verified and tested

BKT ordering (condition 13) is **AVAILABLE** and does not gate the base result.

**Final J0 decision: GO FOR BASE U7**

J0 passed. J1 external adapter and normalized-history construction is ready to begin.

## 18. J1 addendum (adapter execution record, 2026-08-07)

J1 normalized **2,820,378** eligible 2022-2023 action rows (exactly the J0
in-window count) into `external_action_rows_v1.csv` plus `manifest.json` in
the protected processed directory.  Excluded: 21,111,898 rows outside the
window; 0 rows with unparseable timestamps.  Unique external keys: 5,940
students, 80,714 assignments, 27,577 problems.  Grade 6 accounts for 991,700
of the normalized rows (35.2%).

New finding recorded during J1: **819 action-log problem ids are absent from
`problem_details`** (342,998 rows overall; 12,283 in-window rows, including
84,728+30,933 graded responses across the full file).  The normalized contract
keeps `externalContentKey` and `sourceSkillCode` nullable, so the adapter
emits those rows with null content/skill metadata and counts them as
`rowsWithUnresolvedProblemMetadata` instead of fabricating or dropping them.
This does not change the J0 GO decision: problem identity remains stable and
correctness pairing in J2 uses the action-row keys directly.

All 2,820,378 normalized rows carry strictly conforming HMAC pseudonym keys
(`assistments_{namespace}_<64-hex>`), and the manifest records source hashes,
output hashes, counts, usage terms, and `containsRawIdentifiers: false`.
The pseudonym key lives only in the protected external-data root
(`pseudonym_key_v1.txt`) and never appears in the manifest or the repository.
