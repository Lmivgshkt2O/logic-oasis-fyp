# U7 ASSISTments J3A Compatibility Feasibility (diagnostic only)

Date: 2026-08-08
Contract (unchanged): `assistments-j2-attempt-label-contract-v1`
Source: ASSISTments EDM Cup 2023, window 2022-01-01 .. 2023-12-31, provenance `external_real`

## Purpose and scope

J3A is a source-mapping feasibility analysis only. It asks whether a narrower,
source-native skill identity maps the external source to the canonical U7
student-subtopic prediction unit better than the failed same-sequence mapping.

No model was trained, no model metrics were produced, no held-out split was
created, no J4-J6 work ran, and the frozen J2 contract was **not modified**.
The original J2/J3 zero-label result remains part of the audit history.

## Method

Candidate A reconstructs **skill-level episodes**: one episode per
`externalStudentKey + externalAssignmentKey + exact non-null sourceSkillCode`
(physical field `problem_skill_code`). An episode uses only responses belonging
to that skill within the current completed assignment; skills are never mixed.
All other frozen rules are applied unchanged, independently per episode:
first-graded-response correctness, 30-minute response-time admissibility,
>= 3 graded problems, >= 3 valid timing pairs, immediate later valid episode
for the same learner + skill, and exact-identical problem-set censoring.
`masteryCriterion` stays 0.60.

## Candidate A results

### Grade 6 (primary cohort, reported separately)

| Measure | Count |
|---|---:|
| Eligible problem responses | 265,102 |
| Skill/content groups | 277 |
| Unique learners | 2,344 |
| Reconstructed episodes | 62,601 |
| Outcome-valid episodes | 18,062 |
| Feature-valid episodes | 17,671 |
| Candidate immediate-next pairs | 13,083 |
| Identical-problem-set censors | 320 |
| Next-not-outcome-valid censors | 7,384 |
| No-next censors | 4,588 |
| Chronology ambiguities | 0 |
| **Labelled pairs** | **5,379** |
| Target true | 1,021 (19.0%) |
| Target false | 4,358 (81.0%) |
| Learners with labelled pairs | 815 |
| Learners contributing true class | 440 |
| Learners contributing false class | 763 |

### Grades 4-6 (predeclared fallback, reported separately)

| Measure | Count |
|---|---:|
| Eligible problem responses | 455,680 |
| Skill/content groups | 326 |
| Unique learners | 4,007 |
| Reconstructed episodes | 98,003 |
| Outcome-valid episodes | 27,586 |
| Feature-valid episodes | 27,104 |
| Candidate immediate-next pairs | 19,723 |
| Identical-problem-set censors | 487 |
| Next-not-outcome-valid censors | 11,159 |
| No-next censors | 7,381 |
| Chronology ambiguities | 0 |
| **Labelled pairs** | **8,077** |
| Target true | 1,600 (19.8%) |
| Target false | 6,477 (80.2%) |
| Learners with labelled pairs | 1,376 |
| Learners contributing true class | 718 |
| Learners contributing false class | 1,256 |

Problems without resolvable skill metadata (excluded from skill episodes):
3,483 problem instances; they never enter Candidate A evidence and are not
fabricated.

## Candidate B

**Not evaluated.** The selection rule allows Candidate B only when Candidate A
is structurally unusable. Candidate A produces 5,379 (Grade 6) and 8,077
(Grades 4-6) labelled pairs with both classes across many independent learners
and a feasible student-grouped held-out split, so Candidate A is structurally
viable and preferred. No broader family (cluster/domain) mapping was therefore
considered; no invented hierarchy was used.

## Candidate C (sensitivity only)

Same-sequence identical-problem-set pairs, descriptive only and **not approved
as a primary dataset**:

| Cohort | Identical-set pairs | Next rate < 0.60 | Next rate >= 0.60 |
|---|---:|---:|---:|
| Grade 6 | 338 | 39 | 299 |
| Grades 4-6 | 560 | 87 | 473 |

Limitation retained: same-question retest evidence does not demonstrate
generalization to a fresh compatible problem set.

## Sufficiency gates (probed, no split created)

| Candidate A cohort | Gate achieved |
|---|---|
| Grade 6 | Potential held-out comparison (student-grouped split feasible) |
| Grades 4-6 | Potential held-out comparison (student-grouped split feasible) |

Both target classes exist across multiple independent learners in both cohorts;
the final held-out split was **not** created (requires an approved amended
contract).

## Proposed methodology-amendment delta (NOT applied)

If a separately approved, versioned methodology amendment is authorized, the
proposed delta from `assistments-j2-attempt-label-contract-v1` is:

```text
compatibilityIdentity:
  old: same externalStudentKey AND same externalSequenceKey
  new: same externalStudentKey AND exact non-null sourceSkillCode
attemptUnit:
  new: one learner + exact-skill episode inside a completed in-unit assignment;
       an episode uses only responses belonging to that skill in the current
       assignment context; skills are never mixed within an episode
identicalQuestionRepeatRule: unchanged (exact identical valid problem-set
       repeat remains censored)
everything else: unchanged (window, provenance, correctness, 30-minute timing
       rule, minimum evidence counts, immediate-next rule, masteryCriterion
       0.60, features correct_rate + mean_response_time_ms, no leakage)
```

The delta is not applied in J3A.

## Why the amendment is semantically stronger

The failed sequence-level mapping treats an entire in-unit assignment as one
attempt even when it contains multiple skills, and pairs consecutive fluency
rounds that reuse identical problem sets (the dominant censor). Mapping to the
exact `sourceSkillCode` produces one student-skill episode per assignment:

- it matches the canonical one student-subtopic attempt unit;
- it is source-native and reproducible (the physical `problem_skill_code`
  field);
- chronology remains defensible (assignment start timestamps, immediate next
  episode, no skipping);
- non-identical problem evidence is preserved by the unchanged identical-set
  censor (identical-set censors drop from 338 to 320 at sequence vs skill
  level for Grade 6, while 5,379 pairs survive with fresh problem evidence);
- both target classes exist across 815 (Grade 6) / 1,376 (Grades 4-6)
  independent learners, reaching the potential held-out gate.

## Honest limitations

- The largest censor class remains next-not-outcome-valid (7,384 / 11,159):
  many immediate next skill episodes lack >= 3 graded problems of that skill.
- Target classes are imbalanced (~19-20% true) and will need uncertainty
  reporting if the amendment is later approved and evaluated.
- The 2022-2023 window remains 2022-dominated (790 rows in Jan 2023).
- Candidate A is a diagnostic proposal; it does not change the frozen contract
  and no claim is made about KSSR equivalence or model performance.

## Decision

**A. AMENDMENT CANDIDATE A RECOMMENDED** (subject to separate approval and a
versioned methodology amendment). Counts above demonstrate feasibility;
no contract change is applied by this diagnostic run.

