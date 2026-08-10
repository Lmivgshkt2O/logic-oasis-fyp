# U7 ASSISTments External-Real Data Readiness (J3)

Date: 2026-08-08
Contract: `assistments-j2-attempt-label-contract-v1`
Source: ASSISTments EDM Cup 2023, window 2022-01-01 .. 2023-12-31, provenance `external_real`

## Result

**INSUFFICIENT_FOR_MODEL_COMPARISON.** Neither the primary Grade 6 cohort nor
the predeclared Grades 4-6 Mathematics fallback produces any labelled
current -> next rows under the frozen J2 rules, so no model comparison,
pipeline/demo, or held-out claim can be made from this dataset as configured.

## Primary Grade 6 cohort (frozen result, recorded separately)

- Source assignments considered: 30,199
- Completed assignments: 24,630
- Outcome-valid attempts: 13,520
- Feature-valid attempts: 13,296
- Candidate current -> next pairs: 419
- Censored: no next attempt 12,877; identical-problem-set repeat 338;
  next not outcome-valid 81
- Labelled pairs: 0 (target true 0, target false 0)

The Grade 6 result is a data-structure insufficiency, not a pipeline failure,
and is never replaced or hidden by the fallback.

## Predeclared Grades 4-6 fallback

Fallback scope: exact `sourceGrade in {"4", "5", "6"}` and
`sourceSubject == "Mathematics"`, pooled only to enlarge the eligible cohort.
Compatibility, attempt, correctness, timing, censoring, and label semantics
are unchanged (same learner + same sequence; immediate next only;
`masteryCriterion = 0.60`). The fallback was frozen before J2 outcome
inspection and is not post-result dataset shopping. Grade is audit/filter
metadata only and is never a base feature. No KSSR equivalence is claimed.
Grades 7-8 were not used.

### Fallback counts

| Measure | Count |
|---|---:|
| Cohort-eligible assignments started | 59,985 |
| Cohort-eligible completed | 46,853 |
| Outcome-valid attempts | 25,106 |
| Feature-valid attempts | 24,790 (grade 4: 5,336; grade 5: 3,672; grade 6: 13,296) |
| Feature-valid learners | 3,019 |
| Candidate current -> next pairs | 700 |
| Censored: no next attempt | 24,090 |
| Censored: identical-problem-set repeat | 560 |
| Censored: next not outcome-valid | 140 |
| Censored: chronology ambiguous | 0 |
| Labelled pairs | **0** |

### Feature audit (model-ready rows)

No model-ready rows exist, so the feature audit is empty. The frozen contract
requires `correct_rate` finite in [0, 1] and `mean_response_time_ms` finite,
positive, and <= 1,800,000; the builder rejects any row that violates this
rather than retuning the 30-minute rule.

### BKT readiness

Sequence-level lineage remains available: 63,846 learner-skill-sequence
groups with graded responses carrying skill metadata, deterministic ordering
available. Because labelled rows are zero, BKT cannot attach to the base U7
dataset; a later ablation would still be evaluated only as a separately named
ablation if the dataset gate is ever reopened under an approved methodology
amendment.

## Gates

| Gate | Status |
|---|---|
| A. Pipeline/demo (>= 1 labelled row) | Not passed (0 rows) |
| B. Preliminary comparison | Not passed |
| C. Held-out comparison | Not passed |
| D. Cautious advantage | Deferred (J4/J6 only) |

## Decision

**NOT READY FOR J4.** Blocker: zero valid labelled current -> next rows in both
the primary Grade 6 cohort and the predeclared Grades 4-6 Mathematics fallback
under the frozen J2 contract. Reaching a comparison would require a separately
justified, versioned methodology amendment (e.g., to the immediate-next or
identical-problem-set rules) approved before any model-result inspection; no
such change was made in J3.

