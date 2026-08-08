# AQC-E2 ASSISTments Proxy-Difficulty Calibration

Date: 2026-08-08
Stage: **AQC-E2 (problem-difficulty calibration from pre-evaluation data)**
Contract: `assistments-adaptive-contract-v1` (unchanged; frozen in AQC-E1)
Status: **CALIBRATION COMPUTED; TIER ASSIGNMENT BLOCKED**
Decision: **NOT READY FOR AQC-E3** - see section 26 for the exact blocker.

## 1. E1 verification

Verified before any raw data was touched (fail closed):

- Contract version: `assistments-adaptive-contract-v1`; contract SHA-256
  `46997eaf92d6c9aba0dc7d8d196080bc03bd59093ef5b2f04a1fd6fc4e424170`.
- Provenance: `external_real` (never `runtime_callable`).
- Calibration window `2019-02-25T00:00:00Z .. 2021-12-31T23:59:59Z` and
  evaluation window `2022-01-01T00:00:00Z .. 2023-12-31T23:59:59Z` are
  disjoint.
- Minimum independent calibration learners: 20.
- Within-skill proxy tiering: `exact_sourceSkillCode` only.
- Skill catalog gate: >= 9 calibrated problems AND >= 3 per proxy tier.
- Proxy values exactly `proxy_easy` / `proxy_moderate` / `proxy_hard`.
- No native Logic Oasis bank/status fields are allowed on external records.
- E1 contract and claim-boundary tests: **54/54 passed** before E2 ran.

E1 verification passed; calibration processing proceeded.

## 2. ASSISTments release/hash lineage

- Dataset: ASSISTments EDM Cup 2023 (Kaggle), release
  `assistments-edm-cup-2023-release-v1`.
- Verified raw source hashes (J0, 2026-08-07):
  `action_logs.csv`
  `DB6B0CD4875488D0847D9D9BA2896552F4AD1015F3E2388995222DD4A178443D`;
  `assignment_details.csv`
  `D02D8B62DE088C896FCEB901BC986C25FA07F5D9AEEC0364BF9D351208BEC70E`;
  `problem_details.csv`
  `4F45DAF2E010771C6B5E523DD4D583F3AC451F6CE8F2F35270FCB86B875CEE4E`;
  `sequence_details.csv`
  `A1FA10E6DEBD4FD30C4B04E1554E18F2C426A981BCB10BED0B41DD083CCDB541`.
- Usage terms: ASSISTments Data Terms of Use, effective 2020-10-30.
- Raw files and the learner-safe calibration catalog remain outside Git in the
  protected directory. The protected E2 outputs are
  `processed/aqc/e2/assistments_problem_difficulty_proxy_v1.csv` and
  `processed/aqc/e2/e2_calibration_manifest.json`.

## 3. Primary cohort (exact Grade 6 Mathematics)

Membership is exact `sequence_folder_path_level_2 == "Grade 6"`. `Grade 6
Accelerated` is a distinct token and never enters the primary cohort; no
Grades 4-6 pooling was used to increase catalog size.

## 4. Calibration window

`2019-02-25T00:00:00Z` through `2021-12-31T23:59:59Z`.

Both the assignment scope (Grade 6 assignment started inside the calibration
window) and every contributing action timestamp must fall inside this window.
No action/response from 2022-01-01 onward influences p_correct, learner count,
response count, difficulty_score, proxy tier, or catalog eligibility.

## 5. Evaluation window

`2022-01-01T00:00:00Z` through `2023-12-31T23:59:59Z` (frozen; not used for any
calibration evidence).

## 6. Evaluation-learner exclusion / disjointness

The pseudonymous learner set belonging to the frozen 2022-2023 exact Grade 6
evaluation cohort was identified from source metadata only (Grade 6 assignment
started inside the evaluation window), then excluded from calibration:

| Measure | Count |
|---|---:|
| Possible pre-2022 Grade 6 calibration learners | 85,675 |
| Excluded because they also appear in the evaluation cohort | 8,616 |
| Final independent calibration learner count | 77,059 |
| Calibration/evaluation learner overlap after exclusion | **0** |

`evaluationLearnersExcludedFromCalibration: true`. No policy outcome was
inspected to construct this exclusion. The frozen disjointness rule was not
weakened.

## 7. Graded-response rule

Only approved graded events contribute: `correct_response` -> 1 and
`wrong_response` -> 0 (first valid graded response per problem instance, per
the verified U7 semantics). `open_response`, hints, explanations, answers, and
all other actions never determine correctness. Per (learner, problem), only the
chronologically first graded outcome contributes; repeated encounters do not
inflate learner or response counts.

## 8. sourceSkillCode eligibility

A problem enters calibration only with an exact non-null `sourceSkillCode`.
Problems without a skill code are excluded and counted (never assigned or
inferred a skill). Different skills are never pooled.

## 9. Minimum learner threshold

20 independent calibration learners per problem (unique learners, not rows).
Problems below the threshold:

```text
calibrationStatus = insufficient_problem_evidence
proxyDifficulty = null
```

The threshold was not lowered after inspecting coverage.

## 10. Smoothing equation

```text
p_correct = (correct_responses + 1) / (total_graded_responses + 2)
difficulty_score = 1 - p_correct
```

## 11-13. Problem counts

| Count | Value |
|---|---:|
| Total observed problems (graded calibration evidence) | 1,749 |
| Exact-skill eligible problems | 1,731 |
| Calibrated problems (>= 20 independent learners) | 1,051 |
| Insufficient-evidence problems (< 20 learners) | 680 |

## 14-16. Skill counts

| Count | Value |
|---|---:|
| Exact skills observed | 90 |
| Skills with at least one calibrated problem | 62 |
| Skills passing the full 9 / 3+3+3 catalog gate | **not computed** (blocked) |

Diagnostic (not a gate result): 35 of the 62 skills have >= 9 calibrated
problems, covering 941 of the 1,051 calibrated problems (89.5%).

## 17-19. Proxy tier counts

```text
proxy_easy     not computed (blocked)
proxy_moderate not computed (blocked)
proxy_hard     not computed (blocked)
```

Real-data tier assignment was deliberately NOT executed. See section 26.

## 20. Calibration learners per problem (distribution)

Across all 1,731 eligible problems: min 1, Q1 7, median 138, Q3 235, max 621.

## 21. p_correct / difficulty_score (distribution)

All eligible problems: p_correct median 0.700 (Q1 0.576, Q3 0.812, min 0.100,
max 0.997); difficulty_score median 0.300.

Calibrated problems only (n = 1,051): p_correct median 0.730 (Q1 0.609,
Q3 0.830, min 0.159, max 0.997).

## 22. Excluded null-skill problems

18 distinct problems with graded calibration evidence had no exact
`sourceSkillCode` and were excluded from proxy difficulty calibration (1,087
action rows; counted, never assigned a skill).

## 23. Deterministic hash / reproducibility record

- Protected catalog SHA-256:
  `c504741612430a4e86bc6c7b477943b24163859acd3f8e87ea14024af931e4a2`
  (`assistments_problem_difficulty_proxy_v1.csv`, 1,731 rows).
- E2 manifest SHA-256:
  `d240e6b63da23b89db81c4d924aef91be984e5b7ca08f124065b631b3053a641`.
- Rerun check: the calibration was executed twice; catalog bytes and manifest
  bytes were identical on both runs (catalog and manifest hashes reproduced).
  The manifest contains no timestamps or local paths.

## 24. Remaining limitations

1. **Tertile boundary rule gap (blocker).** `assistments-adaptive-contract-v1`
   freezes ordering (p_correct descending, then externalProblemKey ascending)
   and the three-tertile semantics, but does not completely define how tertile
   boundaries are formed when a skill's calibrated problem count is not
   divisible by three. Per the frozen E2 governance rule, real-data tier
   assignment and the catalog gate were therefore NOT executed. See section 26.
2. Skill-code grade-prefix audit: 161 eligible problems (82 calibrated) sit in
   Grade 6 sequences but carry a non-grade-6 CCSS skill-code prefix (e.g.
   `3.G.A.1`, `4.NF.A.1`); 32 distinct such skills. These remain eligible under
   the frozen contract (sequence-level Grade 6 membership + exact non-null
   skill code) and are tiered within their exact skill code; the mismatch is
   recorded as audit metadata, not used to change eligibility.
3. 8,308 Grade 6 assignment rows with unparseable `assignment_start_time` were
   excluded (fail closed) from the assignment scan and counted.
4. 2 action rows from calibration-window assignments had timestamps after the
   calibration window end and were excluded.
5. Only 18 distinct null-skill problems were excluded; all other eligible
   problems carried exact skill codes.
6. The calibration is Grade 6-sequence-based; the evaluation cohort is defined
   by Grade 6 assignment start in the evaluation window (U7 convention).
7. Aggregate-only evidence: the protected catalog contains no learner rows, no
   raw identifiers, and no answer/question text.

## 25. Readiness decision

**NOT READY FOR AQC-E3.**

The calibration evidence itself is healthy (1,051 calibrated problems across
62 skills, 35 skills with >= 9 calibrated problems, zero calibration/evaluation
learner overlap, fully reproducible hashes), but the frozen contract does not
completely define the non-divisible tertile boundary rule, and the E2
governance rule forbids choosing a tertile implementation after seeing data.

## 26. Exact blocker and recommended amendment

**Blocker:** `assistments-adaptive-contract-v1` does not completely define how
within-skill tertile boundaries are formed when a skill's calibrated problem
count is not divisible by three ("stable rank boundaries" is a description,
not a complete algorithm).

**Recommended next step (separately versioned, pre-policy amendment):** freeze
one deterministic boundary rule in a versioned amendment (e.g.
`assistments-adaptive-contract-v1.1`), for example:

```text
sort by p_correct descending, then externalProblemKey ascending;
rank 1..n;
proxy_easy     = ranks 1..floor(n/3)
proxy_moderate = ranks floor(n/3)+1 .. floor(2n/3)
proxy_hard     = remaining ranks
```

After the amendment is approved, re-run AQC-E2 (the calibration pass is
already implemented, deterministic, and reproducible), assign tiers, apply the
9 / 3+3+3 catalog gate, and then proceed to E3.

## 27. Governance and no-policy confirmation

- `provenance: external_real`; `containsRawIdentifiers: false`;
  `productionPromotionAllowed: false`.
- No native Logic Oasis bank/status fields appear in the catalog or manifest.
- P1 decisions computed: **0**; P2 decisions computed: **0**; P3a decisions
  computed: **0**; matched outcomes: **0**; policy comparison reports: **0**.
- No policy selector is imported or called anywhere in the E2 path (enforced
  by tests).
- AQC-E3 was **not** executed. No 2022-2023 adaptive attempts were
  reconstructed and no `currentProxyDifficulty` was assigned to any evaluation
  attempt.

## 28. Tests executed

- New E2 suites: `tests.test_assistments_difficulty_calibration` (window
  isolation, cohort eligibility, graded semantics, unique-learner counting,
  20-learner boundary, smoothing, disjointness, determinism, provenance,
  no-native-fields, no-policy boundary) and
  `tests.test_assistments_proxy_tiers` (within-skill tiering, tie
  determinism, no cross-skill pooling, catalog gate 9/3+3+3): **33/33 passed**.
- E1 contract/claim-boundary suites: **54/54 passed**.
- Copied U7 ASSISTments contract/adapter suites: **48/48 passed**.
- Full ai_pipeline suite on the branch: 273 tests, 1 failure - the documented
  pre-existing `test_report_records_hashes_parameters_and_safe_claim_boundary`
  (line-ending-dependent report/config hash; reproduced identically on the
  clean predecessor AQC branch). No new regressions.
