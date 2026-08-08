# AQC-E3 ASSISTments External Adaptive-Attempt Reconstruction

Date: 2026-08-08
Stage: **AQC-E3 (2022-2023 exact-skill adaptive-attempt reconstruction)**
Contract: `assistments-adaptive-contract-v1.1` (unchanged)
Status: **RECONSTRUCTION FEASIBLE; FINAL OUTPUT BLOCKED**
Decision: **NOT READY FOR AQC-E4** - see section 30 for the exact blocker.

## 1. E1/E2 verification

All twelve frozen-artifact checks passed before any reconstruction ran:

1. v1.1 contract hash `e54085ddfe1e00e1cd12d02639f02a70681c767a2ea51697548890e8211f63de`.
2. v1 predecessor hash preserved (`46997eaf92d6c9aba0dc7d8d196080bc03bd59093ef5b2f04a1fd6fc4e424170`).
3. E2 catalog hash `fe4cb2585bae9a8f15ee2802c23dea8270252384ab7e9c5a410d1ff934bd58e9`.
4. E2 manifest hash `18502d7354c30a24849e659d7b8d656587eb3b48cefd495315f90b66436f3d17`.
5. Provenance `external_real`.
6. Primary cohort exact Grade 6 Mathematics; `Grade 6 Accelerated` separate.
7. Calibration/evaluation windows disjoint and at the frozen bounds.
8. Evaluation learners excluded from calibration; final learner count = possible
   minus excluded (post-exclusion overlap zero).
9. Skill catalog gate 9 / 3+3+3 present in the frozen manifest.
10. Exactly **35** exact skills derived as full-policy eligible, matching the
    E2 manifest; eligible-skill-code hash `ecaf1370b17b19b42acd7f3e182270f9576c6c7764144d21fefd4aca0b956a25`.
11. No native bank/status fields in the manifest or the E3 attempt schema; the
    never-fabricate guards are present.
12. E1/E2/v1.1/U7 contract suites green (see section 28).

## 2. Contract v1.1 and catalog hashes

Contract `assistments-adaptive-contract-v1.1`
`e54085ddfe1e00e1cd12d02639f02a70681c767a2ea51697548890e8211f63de`;
frozen E2 catalog
`fe4cb2585bae9a8f15ee2802c23dea8270252384ab7e9c5a410d1ff934bd58e9`.

## 3. Grade 6 evaluation scope

Exact Grade 6 Mathematics only (`sequence_folder_path_level_2 == "Grade 6"` via
the U7-v2 `cohortEligible` flag). `Grade 6 Accelerated` and all other grades
stay separate; no Grades 4-6 pooling.

## 4. Source window

`2022-01-01T00:00:00Z .. 2023-12-31T23:59:59Z` (frozen evaluation window; the
U7-v2 episodes are restricted to this window and the E3 loader re-verifies the
boundary).

## 5. Exact-skill reconstruction unit

One `externalStudentKey` + one completed `externalAssignmentKey` + one exact
non-null `sourceSkillCode`, reusing the validated U7-v2 episode reconstruction
(completed assignment, exact cohort, >= 3 valid first-graded problems).
Skills never mix inside an attempt.

## 6. Full 35-skill eligibility rule

An attempt is full-policy eligible only when its exact skill passes the E2
catalog gate (>= 9 calibrated problems AND >= 3 proxy_easy / proxy_moderate /
proxy_hard). A problem having `proxyDifficulty != null` alone does NOT confer
eligibility. 35 exact skills are eligible; all other skills are retained only
in audit counts.

## 7-8. Total reconstructed attempts and unique learners

- Reconstructed outcome-valid Grade 6 exact-skill attempts: **15,048**.
- Unique learners: **1,130**.

## 9-10. Eligible-skill vs noneligible-skill attempts

- Attempts inside the 35 full-eligible skills: **12,123**.
- Attempts outside eligible skills: **2,925**.

## 11. Score-valid attempts

**15,048** (all outcome-valid episodes carry `correctRate =
correctFirstResponseCount / gradedProblemCount` from valid first-graded
responses; `open_response` is never graded).

## 12. BKT-valid attempts

**15,048 / 15,048** (diagnostic replay, independent of the purity blocker).
Frozen `bkt-v1` replay per (learner, exact skill) produced a valid mastery
state at every attempt boundary; 388,777 graded observations (identical to the
U7 J5 lineage count), zero missing states, zero cross-skill mixing, no future
response injection.

## 13. Proxy-tier-valid attempts

**BLOCKED.** `currentProxyDifficulty` cannot be finalized because the contract
does not define the purity denominator when an attempt mixes problems with and
without a frozen tier (see section 30).

## 14. Mixed-tier censor count/rate

**319** attempts (2.12% of 15,048) mix tiered and untiered problems, which is
exactly the coverage pattern that makes the purity-denominator rule live.

## 15. Insufficient calibration coverage count/rate

**5,512** attempts (36.6%) have **zero** problems with a frozen tier (no
dominant tier possible); a further 319 are partially covered. 9,217 attempts
(61.3%) are fully tiered. These are coverage diagnostics; the eligibility rule
was not changed.

## 16-18. proxy_easy / proxy_moderate / proxy_hard attempt counts

**BLOCKED** (depend on the purity rule).

## 19. Proxy purity distribution

**BLOCKED.** Reported instead (tier coverage per attempt, tiered/untiered):
`3/0` x2,374; `4/0` x1,767; `5/0` x1,435; `0/3` x1,646; `0/4` x919; `0/5`
x941; `6/0` x899; `7/0` x743; `0/6` x666; `8/0` x411; `10/0` x430; `9/0`
x313; `11/0` x211; `14/0` x159; `0/7` x532; `12/0` x112; `13/0` x113; `15/0`
x116; `0/8` x190; `5/2` x189; `0/12` x145; `0/9` x106; `0/11` x99; `23/0` x89;
`0/14` x100; `15/5` x31; `0/24` x32; `0/10` x63; `0/17` x57; `20/0` x24; `0/16`
x13; `2/7` x56; `25/0` x21; `1/6` x20; `3/9` x22; `1/17` x1 (plus the fully
covered and fully uncovered patterns listed above).

## 20. BKT evidence-count distribution

Across the 15,048 attempt states: min 3, median 10, max 107. Bands: 1-4 x2,518;
5-9 x4,633; 10-19 x4,288; 20+ x3,609; zero-evidence states: 0.

## 21-22. Previous observed proxy tier / cold-history attempts

**BLOCKED** (`previousObservedProxyDifficulty` depends on the finalized
`currentProxyDifficulty` of prior attempts, which is blocked by the purity
denominator gap). The reconstruction pipeline is implemented to derive it from
observed tier-bearing history only (never from prior P1/P2/P3a decisions).

## 23. freshProblemFraction descriptive distribution

min 0.0, Q1 1.0, median 1.0, Q3 1.0, max 1.0 (most attempts introduce only new
problems for the learner-skill; repeats exist). Computed strictly from prior
observed exposure for the same learner + exact skill; no bank equivalence
claimed.

## 24. Chronology ambiguity count

**0** (deterministic `externalAttemptSequence` per learner + skill by
`episodeStartedAt` then assignment key; unresolved ties would be flagged
`chronology_ambiguous` and fail closed - none occurred).

## 25. Deterministic output hash

No final learner-level E3 output was written (blocked). The protected
aggregate diagnostic summary SHA-256:
`487de1829c1cbe9e317ed81bbd228ed3a548486ecf6c171a09779396cdfd3859`.

## 26. Rerun reproducibility

The verification and diagnostic paths are deterministic (verified by tests);
the final attempts/manifest rerun reproducibility check will be executed after
the purity amendment, mirroring the E2 rerun protocol.

## 27. Governance / protected-output status

Diagnostic summary written to the protected `processed/aqc/e3/` directory
(outside Git); no learner-level rows, no raw identifiers, no local paths.
`containsRawIdentifiers: false`, `productionPromotionAllowed: false`,
provenance `external_real`. No native bank/status fields anywhere.

## 28. Tests

- New E3 suite `tests.test_assistments_adaptive_attempts`: **25/25 passed**
  (evaluation-window/cohort filters, exact-skill unit, 35-skill eligibility,
  frozen-catalog-only tiers, no re-tiering, BKT learner+skill chronology,
  future-injection prevention, chronological evidence counts, purity 2/3 and
  mixed cases, all-untiered and mixed-coverage handling, fingerprint
  determinism/no-bankId, past-exposure-only freshness, deterministic
  sequences, chronology-tie fail-closed, provenance, no policy selectors,
  rerun identity, raw-identifier/production guards).
- E1/v1.1/E2/proxy-tier/U7 contract suites: **179/179 passed**.
- Full ai_pipeline suite: 292 tests, 1 failure - the documented pre-existing
  `test_report_records_hashes_parameters_and_safe_claim_boundary`
  (line-ending-dependent report/config hash; reproduced identically on the
  clean predecessor AQC branch).

## 29. Limitations

1. **Purity denominator gap (blocker).** The frozen contract defines the
   dominant-tier fraction for fully tiered attempts (example 4/5) but does not
   state whether uncalibrated problems (frozen `proxyDifficulty = null`)
   belong in the purity denominator when an attempt mixes tiered and untiered
   problems. 319 attempts (2.12%) hit this pattern; the rule must be frozen
   before any final attempt output.
2. BKT replay is diagnostic only (no attempt file was written).
3. 5,512 attempts (36.6%) have no frozen tier at all; they can never be
   tier-valid regardless of the denominator rule.
4. Attempt eligibility is limited to the 35 gate-passing skills; 2,925
   attempts fall outside and enter audit counts only.
5. Fresh-problem exposure is a descriptive substitute; exact fresh-bank
   equivalence is unavailable by contract.
6. No policy comparison or matched-outcome layer exists yet (by design).

## 30. Readiness decision and exact blocker

**NOT READY FOR AQC-E4.**

**Blocker:** `assistments-adaptive-contract-v1.1` does not define whether
uncalibrated problems (frozen `proxyDifficulty = null`) belong in the attempt
purity denominator when an attempt mixes tiered and untiered problems.

**Recommended next step (separately versioned, pre-policy amendment):** freeze
one deterministic rule in a versioned amendment (e.g.
`assistments-adaptive-contract-v1.2`), for example:

```text
purity denominator = number of valid problems in the attempt WITH a frozen
proxy tier (uncalibrated problems are excluded from both the numerator and the
denominator); an attempt with zero tiered problems has no dominant tier.
```

After the amendment is approved, re-run AQC-E3 (the reconstruction pipeline,
BKT replay, and tests are implemented and verified), finalize
`currentProxyDifficulty`/`previousObservedProxyDifficulty`, write the protected
attempts CSV + manifest, and proceed to E4.

## No-policy confirmation

P1 decisions = **0**; P2 decisions = **0**; P3a decisions = **0**; P3b
decisions = **0**; policy agreement rows = **0**; matched policy outcomes =
**0**; policy winner claims = **0**. No policy selector is imported or called
in the E3 path (enforced by tests). AQC-E4 was **not** executed.
