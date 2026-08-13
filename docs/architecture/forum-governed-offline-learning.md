# Forum Governed Offline Learning (U10-R) - Design and Governance

This document describes the governed future workflow for a
`real_evaluated` forum model. **No learner text is collected, exported,
labelled, retained, or retrained for FYP1**, and no online or automatic
learning exists. This page is a design contract for the deferred U10-R unit,
not an instruction to collect data today.

## Principles

- Helpful marks, question-owner Accepted, and reports are human social/moderation
  signals only. They are never ground-truth labels for model training or
  evaluation.
- The controlled `forum-controlled-demo-nb-v1-release-5` release is immutable;
  a real-data release replaces it through one explicit registry transaction and
  is never created by mutating or relabelling the controlled record.
- Probabilities are never presented as learner-calibrated confidence.

## Required governance steps (before any data work)

1. **Consent and purpose approval.** Obtain approved consent (or an approved
   external dataset with documented provenance) and a written purpose scope
   for offline learning; record the approval.
2. **De-identification.** Strip identifiers from raw text; pseudonymize
   authors with a stable, documented grouping method. Keep raw text outside
   version control and outside the deployed Functions bundle.
3. **Quarantine.** Hold data in an access-controlled, time-boxed quarantine
   until provenance and retention are approved.
4. **Human dual review.** Label under a frozen rubric with independent
   reviewers and record agreement/disagreement; never use model outputs or
   social signals as labels.
5. **Author-grouped splits.** Split by stable pseudonymized author groups into
   train, validation, and untouched test; keep duplicates and same-author
   responses together. Selection and preprocessing use training/validation
   only; the frozen pipeline runs the untouched test exactly once.
6. **Evaluation gates.** Report accuracy, macro F1, per-class metrics,
   confusion matrices, abstention/coverage, language slices, calibration, and
   generalisation evidence with the same zero-false-public-decision and
   support/coverage gates as the controlled release. Insufficient evidence
   publishes no candidate.
7. **Approval and immutable candidate.** Bind the approved dataset, split
   manifests, report, rubric, reviewers, dependencies, and code revision to a
   new immutable candidate; issue a separate `real_evaluated` declaration.
8. **Activation.** Deploy under a compatible `real_evaluated_only` runtime mode
   only after every gate passes; the runtime rejects controlled-only artifacts
   in that mode.
9. **Promotion.** Replace the controlled release through the one-active scoped
   registry transaction with explicit supersession; never mutate the
   controlled record.
10. **Retention and deletion.** Record the retention owner and deadline and
    prove deletion (or approved archival) at the deadline.
11. **Rollback.** Revoke the active real-data release to safe advisory
    fallback; restore only through a fresh immutable successor.
12. **Prohibitions.** No test-driven retuning, no automatic retraining, and no
    automatic promotion. Any change to the frozen rubric, catalogue, or
    pipeline invalidates the release and requires a new governed cycle.

## Claim boundaries

Until U10-R completes, all forum AI evidence remains
`controlled_demonstration_only` and `not_established_on_real_learners`. No
real-learner accuracy, generalisability, educational-effectiveness, or
superiority claim is made.
