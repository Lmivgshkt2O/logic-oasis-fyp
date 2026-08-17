# U10 Forum AI Verification Release (v2) - Controlled Evidence

Release date: 2026-08-13
Release ID: `forum-controlled-demo-nb-v1-release-5`
Manifest: `functions/forum_model_manifest.json` (`forum-model-release-manifest-v2`)

## Runtime contract

- Project: `logic-oasis-fyp`; region `asia-southeast1`; Cloud Run functions
  (Gen 2) runtime `python311`.
- Interpreter: CPython `3.11.9`; the candidates and evaluation were rebuilt
  under Python 3.11 per the release contract (release 4 remains historical and
  was never relabelled or promoted).
- Dependency lock: `functions/forum-runtime-requirements.lock.txt` pins the
  direct and transitive Functions dependencies; its digest
  `0067273f13fc463f830c49f4f91169a2dbf71c36246c7d2db2cba3e9e15c7006` is bound
  in the release manifest (`dependencyLockSha256`).
- Components: reasoning `MultinomialNB` (`forum-controlled-demo-nb-v1`) and
  relevance `MultinomialNB` (`forum-relevance-nb-v1`), both vendored with the
  runtime and bound by the `forum-runtime-bundle-v1` bundle manifest.
- Composite policy: `forum-composite-policy-v1` (deterministic protected
  answer-key correctness; relevance positive 0.65 / negative 0.80; reasoning
  abstention 0.60; free-form never verified; withhold on any abstention; no
  public negative correctness label).

## Controlled evaluation

The authoritative fictional verification catalogue
(`ai_pipeline/forum_controlled_demo/forum_verification_catalog_v1.yaml`, 88
examples across 13 scenario families in English, Bahasa Melayu, and mixed
text) is rebuilt deterministically and split by scenario family into a 3-way
train/validation/test partition. Variants and thresholds were frozen on
train+validation; the untouched grouped test ran exactly once.

Test results (`ai_pipeline/reports/forum_controlled_demo_report.json`):

- Reasoning macro F1: 1.0; Relevance macro F1: 1.0 (test partition).
- Composite: 9 verified emitted (precision 1.0, coverage 1.0) and 9
  `May be irrelevant` emitted (precision 1.0, coverage 1.0); false
  `AI-verified` and false `May be irrelevant` both 0.
- Candidate status: `eligible`; failed gates: none.
- Claim level: `controlled_demonstration_only`; calibration status:
  `not_established_on_real_learners`; the report makes no real-learner,
  generalisability, effectiveness, or Naive-Bayes-superiority claim.

## Emulator rehearsal (2026-08-13)

The authenticated Auth/Firestore/Functions emulator rehearsal
(`tools/run_forum_emulator_flow.js`) completed successfully with two students
and one linked parent against the dual-component bundle:

- free-form answer: public state `none`, run `composite.correctness =
  not_applicable`;
- linked answer with correct option: public `verified`, private correctness
  `correct`;
- linked answer with wrong option: public `none`, private correction guidance;
- revision edit: feedback revision 2 with two immutable runs (revision 1 run
  preserved audit-only);
- Helpful, Accept, report, and block/unblock completed; parent was denied all
  10 raw reads (question, answer, AI job, AI run, AI feedback, linked
  discussion, linked answer, registry, report, block);
- revocation produced safe `fallback` while the prior run stayed `completed`;
- controlled corpus aggregate hash was unchanged before/after inference;
- captured emulator output contained no submitted fictional text.

## Claim boundary

This evidence supports reproducible scenario fit, artifact integrity,
prototype integration readiness, and controlled-demonstration mechanics only.
It does not establish predictive accuracy, generalisability, educational
effectiveness, or performance for real primary-school learners. A future
`real_evaluated` release requires the governed U10-R workflow.
