# AQC-E2 ASSISTments Proxy-Difficulty Calibration (amended by v1.1)

Date: 2026-08-08
Stage: **AQC-E2 (problem-difficulty calibration from pre-evaluation data),
completed under assistments-adaptive-contract-v1.1**
Status: **CALIBRATION + TIER CATALOG COMPLETE**
Decision: **READY FOR AQC-E3**

## 0. Amendment history (v1 result preserved)

The first E2 run used `assistments-adaptive-contract-v1` and correctly stopped
before real tier assignment because v1 did not completely define tertile
boundaries for non-divisible calibrated problem counts. That v1 result is
preserved (blocked status, catalog hash
`c504741612430a4e86bc6c7b477943b24163859acd3f8e87ea14024af931e4a2`) and is
superseded by the pre-policy amendment below. No policy result existed at any
point during this sequence.

## 1. v1 predecessor hash

`assistments-adaptive-contract-v1`, SHA-256
`46997eaf92d6c9aba0dc7d8d196080bc03bd59093ef5b2f04a1fd6fc4e424170` (unchanged
and preserved; the v1 file and its E1 tests remain intact).

## 2. v1.1 amendment hash

`assistments-adaptive-contract-v1.1`, SHA-256
`e54085ddfe1e00e1cd12d02639f02a70681c767a2ea51697548890e8211f63de`.

## 3. Amendment reason

`deterministic_discrete_tertile_boundary_clarification`. The amendment fixes an
underspecified implementation detail in v1 (rank boundaries when n is not
divisible by three). Scope is `within_skill_tertile_boundaries_only`.

## 4. No policy results existed before the amendment

Confirmed at amendment time: P1 decisions = 0, P2 decisions = 0, P3a decisions
= 0, matched outcomes = 0, policy comparison reports = 0. The amendment is a
pure methodology clarification, not a result-driven change
(`motivatedByPolicyPerformance: false`, `policyResultsExistedBeforeAmendment:
false`).

## 5. Deterministic tertile rule (frozen by v1.1)

Within each exact non-null `sourceSkillCode`, retain only adequately calibrated
problems (`calibrationLearnerCount >= 20`), sort by
`smoothedCorrectProbability` descending then `externalProblemKey` ascending,
and assign by 1-based rank with:

```text
n  = number of adequately calibrated problems
b1 = floor(n / 3)
b2 = floor(2 * n / 3)
ranks 1..b1            -> proxy_easy
ranks b1+1..b2         -> proxy_moderate
ranks b2+1..n          -> proxy_hard
```

Examples: n=9 -> 3/3/3; n=10 -> 3/3/4; n=11 -> 3/4/4; n=12 -> 4/4/4.
Forbidden implementations: pandas qcut, floating quantile interpolation,
empirical cut-point tuning, global cross-skill ranking, random tie breaking.

## 6-7. Calibrated problems and skills

- Total calibrated problems (>= 20 independent learners): **1,051**.
- Exact skills with calibrated problems: **62** (90 exact skills observed in
  total; 1,731 exact-skill eligible problems; 680 insufficient-evidence
  problems; 18 distinct null-skill problems excluded).

## 8. Skills passing the 9 / 3+3+3 catalog gate

**35** of 62 skills pass the full gate (`>= 9` calibrated problems and `>= 3`
proxy_easy / proxy_moderate / proxy_hard). 27 skills are
`insufficient_skill_catalog` (19 have >= 3 calibrated problems but fail the
gate; 8 have only 1-2 calibrated problems and therefore receive no tiers).

## 9-11. Proxy tier counts

| Tier | Problems |
|---|---:|
| proxy_easy | 329 |
| proxy_moderate | 350 |
| proxy_hard | 362 |

1,041 of 1,051 calibrated problems received a tier; 10 calibrated problems sit
in skills with fewer than 3 calibrated problems (no tier assignable, skill
insufficient).

## 12. Per-skill tier-count distribution

54 skills received tiers. Representative patterns (easy/moderate/hard per
skill): (38,38,38) x1, (24,25,25) x1, (18,18,19) x1, (14,14,15) x2,
(12,12,12) x2, (7,7,7) x3, (6,6,6) x3, (5,6,6) x4, (3,4,4) x4, (3,3,3) x2,
(2,3,3) x3, (2,2,3) x2, (1,2,2) x5, (1,1,2) x4, (1,1,1) x3, and other
larger-skill patterns. Top skills: `6.NS.A.1` 38/38/38 (114 problems),
`6.EE.B.7` 24/25/25 (74), `6.EE.A.2a` 18/18/19 (55), `6.RP.A.3a` 17/17/17
(51), `6.G.A.2` 14/14/15 (43).

## 13. Deterministic catalog hash

Protected catalog SHA-256:
`fe4cb2585bae9a8f15ee2802c23dea8270252384ab7e9c5a410d1ff934bd58e9`
(`assistments_problem_difficulty_proxy_v1.csv`, 1,731 rows).

## 14. Rerun reproducibility

**REPRODUCIBLE.** The amended E2 was executed twice; catalog bytes/hash and
manifest bytes/hash were identical on both runs. Manifest SHA-256:
`18502d7354c30a24849e659d7b8d656587eb3b48cefd495315f90b66436f3d17`. The
manifest contains no timestamps or local paths.

## 15. Calibration/evaluation learner overlap

**0.** Possible pre-2022 Grade 6 learners 85,675; excluded evaluation-cohort
learners 8,616; final calibration learners 77,059;
`evaluationLearnersExcludedFromCalibration: true`.

## 16. Tests/results

- New v1.1 suite `tests.test_assistments_adaptive_contract_v1_1`: **18/18
  passed** (n=9/10/11/12 boundaries, floor rule, sorting, ties, per-skill
  independence, no global ranking, deterministic hash, v1 preservation,
  unchanged non-boundary rules, tamper rejection, no policy selectors, native
  AQC still validates).
- E1, E2, proxy-tier, v1.1, and U7 contract/adapter suites: **154/154 passed**.
- Full ai_pipeline suite: 292 tests, 1 failure - the documented pre-existing
  `test_report_records_hashes_parameters_and_safe_claim_boundary`
  (line-ending-dependent report/config hash; reproduced identically on the
  clean predecessor AQC branch).

## 17. New regressions

**None.**

## 18-21. No policy outputs

P1 decisions = **0**; P2 decisions = **0**; P3a decisions = **0**; matched
outcomes = **0**; policy comparison reports = **0**. No policy selector is
imported or called in the E2/amendment path (enforced by tests).

## 22. AQC-E3 NOT executed

Confirmed. No 2022-2023 adaptive attempts were reconstructed, no attempt
purity was computed, no `currentProxyDifficulty` was assigned to any
evaluation attempt, and AQC-E3 was not started.

## Background (frozen context, unchanged)

- E1 verification passed before any raw data was touched (contract v1.1 now
  also verifies the v1 predecessor binding and the amendment fields).
- ASSISTments EDM Cup 2023 release `assistments-edm-cup-2023-release-v1`; raw
  hashes per J0; provenance `external_real`; raw files and learner-safe
  outputs outside Git; `containsRawIdentifiers: false`;
  `productionPromotionAllowed: false`.
- Cohort: exact Grade 6 Mathematics (`sequence_folder_path_level_2 == "Grade
  6"`); `Grade 6 Accelerated` separate; no Grades 4-6 pooling.
- Calibration window `2019-02-25T00:00:00Z .. 2021-12-31T23:59:59Z`;
  evaluation window `2022-01-01T00:00:00Z .. 2023-12-31T23:59:59Z`; disjoint.
- Graded-response rule: `correct_response` = 1, `wrong_response` = 0, first
  graded response per (learner, problem); `open_response` and all other
  actions never graded; repeated encounters never inflate learner/response
  counts.
- Smoothing: `p_correct = (correct + 1) / (total + 2)`,
  `difficulty_score = 1 - p_correct`; minimum 20 independent learners.
- p_correct distribution (all eligible): median 0.700 (Q1 0.576, Q3 0.812);
  calibrated only: median 0.730. Learners/problem: median 138, max 621.
- Audit: 161 eligible problems (82 calibrated) in Grade 6 sequences carry a
  non-grade-6 CCSS skill-code prefix (32 distinct skills); retained per the
  frozen contract and tiered within their exact skill code.

## Final decision

**READY FOR AQC-E3** - a non-trivial exact Grade 6 three-tier catalog exists
under the frozen (v1.1-amended) rules: 35 skills pass the 9 / 3+3+3 gate with
1,041 tiered calibrated problems, calibration/evaluation leakage is zero, and
reruns reproduce the same catalog and manifest hashes. AQC-E4 remains the
full Stage-B data-sufficiency gate.
