# AQC-E3 ASSISTments External Adaptive-Attempt Reconstruction (amended by v1.2)

Date: 2026-08-09
Stage: **AQC-E3 (2022-2023 exact-skill adaptive-attempt reconstruction),
completed under assistments-adaptive-contract-v1.2**
Status: **RECONSTRUCTION COMPLETE**
Decision: **READY FOR AQC-E4**

## 0. Amendment history (v1.1 result preserved)

The first E3 run reconstructed 15,048 Grade 6 exact-skill episodes but
correctly stopped before finalizing attempt proxy difficulty because v1.1 did
not define the purity denominator when an attempt mixes tiered and untiered
problems (319 mixed-coverage attempts observed). That blocked result and its
diagnostic summary are preserved. The pre-policy clarification
`assistments-adaptive-contract-v1.2` (below) resolved the gap, and AQC-E3 was
rerun to completion. No policy result existed at any point.

## 1. v1.1 predecessor hash

`assistments-adaptive-contract-v1.1`, SHA-256
`e54085ddfe1e00e1cd12d02639f02a70681c767a2ea51697548890e8211f63de` (unchanged
and preserved, with v1 `46997eaf92d6c9aba0dc7d8d196080bc03bd59093ef5b2f04a1fd6fc4e424170`
also preserved).

## 2. v1.2 hash

`assistments-adaptive-contract-v1.2`, SHA-256
`d82b50432157f9321808dfced5ad7cb55960ce2dbc3501987ab17a23de725955`.

## 3. Amendment rationale

`attempt_proxy_difficulty_purity_denominator_clarification`. The denominator
uses all valid graded problems because the purpose of purity is to determine
whether the reconstructed attempt as a whole has sufficient evidence for one
proxy difficulty. Untiered problems provide no evidence for
Easy/Moderate/Hard and cannot increase the dominant-tier numerator, but they
remain part of the observed attempt and reduce confidence in assigning one
tier. Scope: `attempt_purity_denominator_only`.

## 4. No policy results existed before the amendment

Confirmed: P1 = 0, P2 = 0, P3a = 0, P3b = 0, policy agreement rows = 0,
matched policy outcomes = 0, policy winner claims = 0
(`motivatedByPolicyPerformance: false`, `policyResultsExistedBeforeAmendment:
false`).

## 5. Purity denominator rule (frozen by v1.2)

```text
valid_problem_count   = number of valid graded problem outcomes in the attempt
easy_count            = valid problems with proxyDifficulty = proxy_easy
moderate_count        = valid problems with proxyDifficulty = proxy_moderate
hard_count            = valid problems with proxyDifficulty = proxy_hard
dominant_tier_count   = max(easy_count, moderate_count, hard_count)
proxyDifficultyPurity = dominant_tier_count / valid_problem_count
```

Untiered problems remain in `valid_problem_count` but contribute to none of
the tier counts (never invented a tier, never dropped). Assignment: purity >=
2/3 with a unique dominant tier -> `currentProxyDifficulty` = dominant tier;
otherwise null (`mixed_proxy_difficulty`). Zero tiered problems -> purity 0,
no current tier. Dominant-tier ties -> no arbitrary selection, null.
Examples frozen: 4/4 -> Easy; 4/5 -> Easy; 4/7 -> null; 5/7 -> Easy; 1/7 ->
null; 0/3 -> null; equal counts -> null.

## 6-7. Total reconstructed attempts and unique learners

- Reconstructed outcome-valid Grade 6 exact-skill attempts: **15,048**.
- Unique learners: **1,130** (79 unique exact skills).

## 8-9. Eligible vs noneligible skill attempts

- Attempts inside the 35 full-gate eligible skills: **12,123**.
- Attempts outside eligible skills: **2,925** (audit-only).

## 10. Proxy-tier-valid attempts

**2,187** attempts (14.5%) receive a `currentProxyDifficulty`
(purity >= 2/3 with a unique dominant tier, within the 35 eligible skills or
not - tier validity is computed for all reconstructed attempts; full policy
eligibility additionally requires the gate-passing skill).

## 11-13. proxy_easy / proxy_moderate / proxy_hard attempts

| Tier | Attempts |
|---|---:|
| proxy_easy | 898 |
| proxy_moderate | 547 |
| proxy_hard | 742 |

## 14. Mixed/insufficient-tier attempts

**7,349** attempts (48.8%) have at least one tiered problem but purity < 2/3
(or a non-unique dominant tier) -> null with `mixed_proxy_difficulty`.

## 15. Zero-tier attempts

**5,512** attempts (36.6%) have zero problems with a frozen tier -> purity 0,
no current tier.

## 16. Purity distribution

Across all 15,048 attempts: min 0.0, Q1 0.0, median 0.4, Q3 0.5, max 1.0.

## 17. BKT evidence distribution

All 15,048 attempts have a valid `bkt-v1` state (388,777 graded observations,
identical to the U7 J5 lineage). Evidence count: min 3, Q1 6, median 10, Q3
19, max 107; bands 1-4 x2,518; 5-9 x4,633; 10-19 x4,288; 20+ x3,609;
zero-evidence 0.

## 18. previousObservedProxyDifficulty coverage

**1,501 attempts** (10.0%) have a direct previous chronologically valid
tier-bearing attempt for the same learner + exact skill (observed history
only; never from prior policy decisions).

## 19. Cold-history count

**13,547 attempts** (90.0%) have no prior tier-bearing attempt
(`previousObservedProxyDifficulty = null`, cold-history context).

## 20. freshProblemFraction distribution

min 0.0, Q1 1.0, median 1.0, Q3 1.0, max 1.0 (past-exposure-only per learner +
exact skill; no bank equivalence claimed).

## 21. Chronology ambiguity

**0** (deterministic `externalAttemptSequence` per learner + skill; unresolved
ties fail closed with `chronology_ambiguous` - none occurred).

## 22. Final E3 output hash

Protected attempts CSV SHA-256:
`b065d1d3cc70fc9086f92f24f998aed62a0d597ac74c1d2b9f385a1c4cd3b6a6`
(`external_adaptive_attempts_v1.csv`, 15,048 rows). E3 manifest SHA-256:
`f5a966e98329c0936c12bce8728cf1601a57e8a649befd95c612b5cec468c2f1`.

## 23. Rerun reproducibility

**REPRODUCIBLE.** AQC-E3 was executed twice under v1.2; attempts CSV and
manifest bytes/hashes were identical on both runs. The manifest contains no
timestamps or local paths.

## 24. Protected-output status

Attempts CSV + manifest written to the protected `processed/aqc/e3/` directory
(outside Git); no raw identifiers, no local paths;
`containsRawIdentifiers: false`, `productionPromotionAllowed: false`,
provenance `external_real`; no native bank/status fields; the earlier blocked
diagnostic summary remains preserved in the same protected directory.

## 25. Tests/results

- New v1.2 suite `tests.test_assistments_adaptive_contract_v1_2`: **9/9
  passed** (version/hash/predecessor binding, amendment reason/scope,
  frozen purity formula/untiered flags/tie rule/examples, v1+v1.1 history
  preservation, unchanged non-purity rules, tamper rejection, no policy
  selectors, native AQC still validates).
- Updated E3 suite `tests.test_assistments_adaptive_attempts`: **32/32
  passed** (all 30 required behaviors, including the seven v1.2 purity
  examples, untiered-in-denominator, tie fail-closed, previous-tier/cold
  history, censor reasons).
- E1/v1.1/E2/U7 suites: **154/154 passed** (combined targeted run).
- Full ai_pipeline suite: 333 tests, 1 failure - the documented pre-existing
  `test_report_records_hashes_parameters_and_safe_claim_boundary`
  (line-ending-dependent report/config hash; reproduced identically on the
  clean predecessor AQC branch).

## 26. New regressions

**None.**

## 27-29. No policy outputs

P1 = **0**; P2 = **0**; P3a = **0**; P3b = **0**; policy agreement rows =
**0**; matched policy outcomes = **0**; policy winner claims = **0**. No policy
selector is imported or called in the E3/v1.2 path (test-enforced).

## 30. E4 NOT executed

Confirmed. No attempt purity of evaluation policy states, no P1/P2/P3a, no
matched outcomes, no policy comparison, and AQC-E4 was not started.

## Background (frozen context, unchanged)

- E1/E2 verification passed before reconstruction (v1.2 contract, v1.1/v1
  predecessors, E2 catalog `fe4cb2585bae9a8f15ee2802c23dea8270252384ab7e9c5a410d1ff934bd58e9`,
  E2 manifest `18502d7354c30a24849e659d7b8d656587eb3b48cefd495315f90b66436f3d17`,
  provenance, exact Grade 6 cohort, windows, learner disjointness, catalog
  gate, 35 eligible skills, no native fields).
- Attempt unit: one externalStudentKey + one completed externalAssignmentKey +
  one exact non-null sourceSkillCode; skills never mix; U7-v2 first-graded
  correctness; `open_response` never graded; BKT frozen `bkt-v1` per
  learner+skill, no future injection.
- 5,512 attempts (36.6%) have no frozen tier at all and can never be
  tier-valid; 7,349 more are below the 2/3 purity threshold; 2,187 are
  tier-valid. E4 remains the full Stage-B data-sufficiency gate and may still
  fail on policy-comparison/matched-outcome sufficiency.

## Final decision

**READY FOR AQC-E4** - the 2022-2023 Grade 6 histories reconstruct into
policy-ready states (15,048 attempts, 1,130 learners, valid score/BKT/tier
fields, deterministic chronology, reproducible protected output) under the
frozen v1.2 rules, and no contract/data-integrity gate failed.
