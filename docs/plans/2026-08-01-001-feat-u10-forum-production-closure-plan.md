---
title: U10 Q&A Forum FYP1 Controlled-Demonstration Closure - Plan
type: feat
date: 2026-08-01
deepened: 2026-08-01
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-plan-bootstrap
execution: code
---

# U10 Q&A Forum FYP1 Controlled-Demonstration Closure - Plan

## Goal Capsule

- **Objective:** Finish the remaining U10 Q&A Forum and automatic Naive Bayes work in dependency order using a developer-approved controlled-demonstration corpus, without rebuilding the committed or currently implemented baseline.
- **Authority:** This plan follows the confirmed FYP1 controlled-demonstration decision and four-tab navigation first, the controlled-demonstration XGBoost companion pattern second, current repository evidence third, and the canonical FYP1 plus CRISP-DM documents within the claim-boundary reconciliations recorded here.
- **Evidence boundary:** FYP1 proves reproducible scenario-fit, artifact integrity, automatic prototype integration, privacy, and reliability. It does not establish predictive accuracy, generalisability, educational effectiveness, or performance for real primary-school learners.
- **Execution profile:** Work through U1-U6 sequentially. Run focused checks that protect the next unit, then perform the complete regression, rehearsal, evidence, and documentation closure in U6.
- **Stop conditions:** Do not stage `.worktrees/`; do not promote the emulator fixture or deterministic baseline; do not copy real learner text or protected answer keys into the controlled corpus; do not use untouched test evidence to tune any model, policy, rubric, catalogue, or scenario; do not activate an artifact when its evidence structure, non-degeneracy gates, evidence mode, hashes, dependencies, schema, or runtime identity are incompatible.
- **Tail owner:** U6 owns FYP1 prototype verification, documentation reconciliation, limitations, safe deactivation evidence, and the final controlled-demonstration-only claim boundary. U10-R is deferred and is not part of FYP1 completion.

---

## Product Contract

### Summary

Close U10 for FYP1 by moving the existing forum into a primary tab between Forge and Settings, proving authenticated collaboration and privacy behavior, hardening retried jobs and Mutual Aid counters, selecting and freezing a Naive Bayes pipeline through scenario-family-isolated training/validation evidence, evaluating it once on untouched grouped test evidence when the catalogue supports that split, activating a non-degenerate Naive Bayes bundle only in controlled-demo mode, and finishing with one complete prototype verification and evidence pass.

### Problem Frame

Commit `b0ffaa5` established the forum, its advisory Naive Bayes pipeline, student-only Firestore surface, backend callables and triggers, safe parent projection, and initial tests. The current working tree adds an emulator path, a small synthetic fixture, artifact-integrity checks, counter repair, and evidence, but it is not yet stabilized and the forum is still a Home quick action.

FYP1 has no approved real-learner forum dataset. Requiring real-data release governance, learner-author grouping, production learner-text validation, or a `real_evaluated` artifact would make U10 impossible to close within the prototype evidence available. The correct boundary is a genuine automatic classifier trained and evaluated on a separate deterministic controlled-demonstration corpus, with claims limited to scenario-fit and prototype integration readiness.

Evaluation correctness remains mandatory. Related fictional scenarios stay group-isolated across training, validation, and test; selection and preprocessing use no untouched test text; canonical metrics and artifacts are reproducible and hash-bound; activation fails closed on insufficient, degenerate, or incompatible evidence; and the future real-data path replaces rather than relabels the controlled release.

### Existing Completion Baseline

| Baseline | Existing artifacts | Planning treatment |
|---|---|---|
| Committed forum feature | `lib/features/collaboration/qa_forum/`, forum models/repository/status service, `firestore.rules`, `functions/main.py`, `functions/forum_runtime.py`, initial Flutter/Python tests, and `tools/deploy_forum_runtime_iam.py` | Preserve and extend only where a remaining requirement exposes a gap. |
| Current emulator integration | `firebase.json`, `android/app/src/debug/AndroidManifest.xml`, `lib/main.dart`, `lib/shared/services/firebase_emulator_config.dart`, and `tools/run_forum_emulator_flow.js` | Review and stabilize in U1; do not recreate. |
| Current emulator fixture and integrity work | `ai_pipeline/logic_oasis_ai/forum_ai/dataset.py`, `ai_pipeline/training/train_forum_classifier.py`, `ai_pipeline/logic_oasis_ai/forum_ai/data/emulator_reviewed_examples.jsonl`, `functions/forum_model.joblib`, and `functions/forum_model_manifest.json` | Keep explicitly `synthetic_test` and emulator/test-only. It proves parsers, rejection, triggers, and smoke mechanics but never becomes the controlled evaluation corpus. |
| Current emulator evidence | `docs/evidence/u10-forum-emulator-validation.md` | Retain its mechanics-only claim boundary; U6 adds controlled-demonstration closure evidence. |
| Controlled-demo precedent | `ai_pipeline/controlled_demo/`, `ai_pipeline/training/publish_controlled_demo_bundle.py`, and `docs/evidence/2026-07-24-controlled-demo-xgboost-release.md` | Reuse evidence-mode, immutable release, one-active-record, and replacement-route patterns without mixing forum Naive Bayes with quiz XGBoost. |

### Actors

- A1. An authenticated student reads forum content, asks questions, submits reasoning-based answers, marks another learner's answer helpful, accepts one eligible answer to their own question, reports or blocks content, and sees qualitative advisory feedback.
- A2. An active linked parent never reads forum text or peer identity and may read only their child's count-only participation summary.
- A3. A developer curates and approves fictional forum scenarios, freezes the rubric and catalogue, runs grouped evaluation, and records a bounded controlled-demonstration release rationale.
- A4. An operator activates only a manifest-compatible controlled-demonstration artifact, records the exact runtime environment, and inspects privacy-safe logs. When cloud deployment is used, the operator also verifies activation under the dedicated forum runtime identity and least-privilege IAM.
- A5. A future authorized reviewer or data steward governs a later approved real or approved-external release under U10-R; that role is not required for FYP1 closure.

### Requirements

#### Navigation and forum experience

- R1. The primary tab order is Home, Forge, Q&A Forum, Settings, with Q&A Forum immediately left of Settings.
- R2. Home no longer embeds or pushes a duplicate Q&A Forum action, and saved navigation state migrates without turning a previously saved Settings index into Forum.
- R3. The student forum supports question discovery/filtering, question and reasoning-based answer submission, safe author edits with revision-bound reclassification, helpful marking, one accepted answer per question, reporting, blocking, and clear loading, empty, in-flight, denied, success, and recoverable failure states.

#### Authorization and privacy

- R4. Forum content and actions require an authenticated student; unauthenticated users, parents, foreign authors, and self-actions receive stable callable or Rules denials.
- R5. An active linked parent reads only their child's count-only participation summary; forum text, peer identity, reports, blocks, marks, participation events, AI jobs, and AI runs remain inaccessible.
- R6. Helpful and acceptance actions are idempotent, reject missing or ineligible targets, and update their deterministic source record and derived counter exactly once.

#### Trigger and counter reliability

- R7. Forum create/update triggers tolerate duplicate and out-of-order delivery through deterministic event identity, answer-content versioning, atomic claims, and idempotent finalization; stale feedback never overwrites a newer edit.
- R8. AI jobs distinguish retryable from terminal failures, expose bounded attempt and lease metadata, reclaim stale processing safely, and never remain stuck indefinitely.
- R9. Question, answer, accepted-answer, and helpful counters preserve the originating event timestamp, remain repairable after partial failure, and never regress a current Malaysia-week projection because an older event arrives late.
- R10. A verified classifier is cached once per warm Functions instance only after artifact and manifest validation; model calls occur outside Firestore transaction callbacks.

#### Controlled-demonstration evidence and activation

- R11a. FYP1 uses a versioned developer-approved controlled-demonstration corpus containing fictional text only, frozen rubric and catalogue provenance, scenario-family grouping, class balance, language labels, deterministic generation, immutable hashes, and no real learner identity, copied forum text, or protected answer keys.
- R11b. A future real-data release requires approved consented or approved-external provenance, de-identification review, rubric and reviewer-process versions, stable pseudonymized author groups, language, retention owner/date, class balance, and an immutable dataset hash; this is a U10-R replacement gate, not an FYP1 completion requirement.
- R12. FYP1 evaluation isolates scenario families across grouped training, validation or inner grouped cross-validation, and an untouched grouped test when catalogue size permits. Naive Bayes variant and configuration selection uses only training/validation evidence; the frozen pipeline is evaluated once on untouched test evidence, and cross-validation-only results are labelled preliminary rather than final-test performance. Reports include accuracy, macro F1 and per-class metrics, confusion matrix, abstention and publication/fallback coverage, latency, artifact size, dataset/group/class counts, split metadata, reproducibility bindings, non-degeneracy outcomes, and controlled-demonstration limitations. U10-R replaces scenario grouping with author-isolated real-data evaluation and stronger calibration/generalisation checks.
- R13. FYP1 controlled-demo release binds the authoritative catalogue, built dataset and split manifests, evaluation reports, rubric, preprocessing, vectorizer, selected Naive Bayes classifier, abstention policy, dependencies, code revision, artifact hashes, immutable release record, deployment scope, and intended advisory scope. Activation requires valid grouped evidence plus all non-degeneracy and integrity gates; any mismatch fails closed, the comparison baseline is never releasable, and `real_evaluated` replacement is reserved for U10-R.
- R14. All deployed forum endpoints use `logic-oasis-forum-runtime@logic-oasis-fyp.iam.gserviceaccount.com` with source/vendor parity and least-privilege IAM verified when cloud deployment is used. The approved Emulator path may satisfy FYP1 automatic-runtime evidence when cloud deployment is unavailable, provided the limitation is explicit.

#### Closure and claims

- R15. Architecture, implementation-status, evidence, and report documentation describe the four-tab navigation, actual Firestore schema, the `synthetic_test` versus `controlled_demonstration` versus `real_evaluated` evidence ladder, controlled-demo activation, runtime identity, metrics, limitations, and future replacement route.
- R16. Broad Flutter, Python, Rules Emulator, Auth/Functions/Firestore Emulator, release-contract, and student/parent manual verification runs after U1-U5 are complete, except for focused gates required by the next unit.
- R17. FYP1 closure records the controlled release, automatic answer-to-job-to-run-to-feedback path, safe logs, source/vendor parity, rollback or model deactivation, and exact environment. Cloud deployment may add identity evidence, but real-user traffic, a 24-hour production observation, real-data sign-off, and production accuracy claims are not unconditional FYP1 gates.

### Evidence Levels

| Evidence level | Permitted use | Prohibited claim |
|---|---|---|
| `synthetic_test` | Emulator integration, parser tests, artifact rejection, trigger mechanics, and smoke evidence | Evaluation quality, scenario-fit, or learner performance |
| `controlled_demonstration` | Developer-approved fictional corpus, reproducible scenario-fit evaluation, artifact integrity, and FYP1 prototype integration readiness | Real-student accuracy, generalisability, educational effectiveness, or production validation |
| `real_evaluated` | Future approved pseudonymized real or approved-external evidence under U10-R | Any claim beyond the separately reviewed dataset, population, and evaluation limits |

### Key Flows

- F1. A student selects the Q&A Forum tab, filters or opens a question, submits or edits reasoning, and receives an automatic `clear`, `needs_revision`, `uncertain`, or `fallback` result bound to the current answer revision.
- F2. Two authenticated students exercise helpful and acceptance actions; invalid identity, ownership, self-action, duplicate, missing-target, and competing-acceptance paths resolve without duplicate effects.
- F3. A duplicated or retried answer event claims one job, recovers an expired lease or immutable winning run, and repairs derived state without moving activity to another week.
- F4. A developer-approved, versioned fictional forum scenario catalogue is validated, deterministically built, and partitioned by scenario family. Training plus grouped validation or inner grouped cross-validation selects and freezes one Naive Bayes variant, preprocessing contract, vectorizer configuration, and abstention policy. When enough independent groups exist, the frozen pipeline is evaluated once on untouched grouped test evidence; otherwise the report labels valid grouped cross-validation as preliminary and never presents it as final-test performance. Canonical manifests, reports, and the eligible Naive Bayes candidate are produced without real learner forum text.
- F5. An operator verifies the immutable controlled-demonstration release record, grouped-evidence status, non-degeneracy gates, runtime bundle, dependencies, vectorizer, selected Naive Bayes classifier, abstention policy, deployment mode, and exact runtime environment. When cloud deployment is used, the operator also verifies the dedicated runtime identity and least-privilege IAM. A developer-authored demonstration answer submitted through the normal authenticated forum flow using a designated test student account then completes the automatic job, inference, immutable run, and safe feedback flow without exposing forum text in logs or entering the training/evaluation corpus.
- F6. Deferred U10-R replaces the controlled release with a separately governed `real_evaluated` artifact after approved real-data governance and author-isolated evaluation; it does not mutate or relabel the FYP1 release.

### Acceptance Examples

- AE1. Given the authenticated app shell, when the student taps Q&A Forum, then the forum opens as the third primary tab and Settings remains the fourth; Home contains no forum action.
- AE2. Given two students and one linked parent, when they read forum data, then students may read permitted posts, the parent may read only the linked child's count-only summary, and all raw or peer-bearing forum records are denied.
- AE3. Given one answer, when its author marks it helpful or a foreign student accepts it, then the callable rejects the action; when an eligible peer marks it twice, the mark and helpful counter exist once.
- AE4. Given two eligible answers to one question, when the question author attempts to accept both, then exactly one authoritative accepted answer remains and the accepted-answer counter increments once.
- AE5. Given duplicate delivery, a transient failure, or an expired processing lease, when the event retries, then one immutable run and one terminal job result remain and current-week counters do not duplicate or regress.
- AE6. Given a `synthetic_test` emulator fixture artifact, when runtime is outside emulator/test mode, then it is rejected and the answer remains safe.
- AE7. Given related scenarios crossing training, validation, or test partitions; too few independent groups for valid grouped validation; or either class missing from applicable held-out evidence, when evaluation runs, then it returns `controlled_catalogue_insufficient` and produces no activatable candidate.
- AE8. Given a valid controlled-demonstration artifact, when `FORUM_MODEL_EVIDENCE_MODE=controlled_demo`, then it may activate; under `real_evaluated_only`, it is rejected.
- AE9. Given an invalid catalogue, rubric, preprocessing, vectorizer, classifier, report, policy, dependency, or runtime-bundle binding, when activation is attempted, then it fails closed.
- AE10. Given a valid controlled release and a new developer-authored demonstration answer submitted through an authenticated test student account, when the automatic runtime executes, then the input traverses the normal answer/job/revision/inference/run/feedback path, is not added to training or evaluation evidence, produces one revision-bound qualitative result and immutable run, leaves no answer text in logs, and records `claimLevel: controlled_demonstration_only`.
- AE11. Given an answer edited while older inference is running, when both deliveries complete, then only feedback for the current revision is displayed and the earlier immutable run remains audit-only.
- AE12. Given a controlled-demonstration report, when presented, then it contains the limitation statement and makes no real-world accuracy, model-superiority, generalisability, or educational-effectiveness claim.
- AE13. Given grouped training, validation, and test partitions, when candidate selection runs, then model/vectorizer/preprocessing/feature/abstention decisions use no test rows and the frozen selected Naive Bayes pipeline is evaluated on the untouched test exactly once.
- AE14. Given too few groups for a separate untouched test but enough for valid grouped cross-validation, when evaluation runs, then the report labels results preliminary, states that no untouched final-test result exists, preserves grouping, and never manufactures rows; if valid grouped validation is also impossible, it returns `controlled_catalogue_insufficient` with no candidate.
- AE15. Given the deterministic baseline equals or outperforms both Naive Bayes variants, when the report is issued, then `baselineComparisonResult` states that no controlled-scenario advantage was demonstrated, the baseline remains non-promotable, and any activated non-degenerate Naive Bayes artifact carries no superiority claim.
- AE16. Given a candidate with one-class predictions, zero recall for either class on applicable final held-out evidence, empty vocabulary, all-abstain behavior, invalid confusion matrix, leakage, or invalid bindings, when activation is considered, then `controlledCandidateStatus: rejected` and `activationStatus: blocked` identify the failed gate.

### Success Criteria

1. The forum is the confirmed primary tab and saved Settings navigation migrates safely.
2. Authenticated student collaboration and linked-parent count-only privacy boundaries pass.
3. Helpful, acceptance, reporting, blocking, counters, retries, leases, stale jobs, duplicate delivery, and answer-revision races pass.
4. The emulator fixture remains `synthetic_test` and test-only.
5. A separate developer-approved controlled-demonstration corpus is deterministic, versioned, schema-validated, canonically serialized, reproducible, and hash-bound to its authoritative catalogue.
6. Scenario-family-isolated training/validation selects and freezes one Naive Bayes pipeline without using untouched grouped test evidence; question-family checks prevent related-problem leakage.
7. When supported, the frozen pipeline is evaluated once on untouched grouped test data. Otherwise valid grouped cross-validation is labelled preliminary, and an insufficient catalogue produces no activatable candidate.
8. The report records `candidateSelectionDecision`, `selectedNaiveBayesVariant`, `baselineComparisonResult`, `controlledDemoActivationDecision`, required metrics, non-degeneracy outcomes, reproducibility bindings, and limitations. Macro F1 guides Naive Bayes selection but is not sufficient for activation.
9. A genuine non-degenerate Naive Bayes vectorizer-and-classifier bundle activates only in controlled-demo mode; the comparison baseline is never releasable and fallback remains a technical safety path.
10. A new developer-authored demonstration answer submitted through an authenticated test student account automatically reaches the job, inference, immutable run, and qualitative feedback path without becoming training/evaluation data.
11. Every missing or mismatched release binding and every failed non-degeneracy gate blocks activation safely.
12. Documentation distinguishes emulator mechanics, controlled-demonstration evaluation, runtime test-account demonstration, and future real-data evidence.
13. U10 FYP1 makes no claim of real-student accuracy, model superiority, educational effectiveness, generalisability, or production validation.

### Scope Boundaries

#### In scope

- Remaining forum UI, authenticated actions, privacy, reliability, controlled-demonstration evaluation, controlled-demo activation, documentation, and FYP1 evidence.
- Small schema changes for singular acceptance, deterministic actions, leases, counter repair, inference versioning, controlled release manifests, and runtime mode enforcement.
- A separate forum controlled-demonstration corpus that reuses the current forum artifact, job, manifest, registry, and runtime architecture.

#### Out of scope

- Rebuilding the committed forum page, models, repository, classifier, Rules surface, basic triggers, or synthetic emulator path.
- Team Challenge, Study Buddy, unrestricted messaging, parent forum access, correctness grading, punitive labels, autonomous moderation, or a human moderation platform.
- XGBoost, BKT, SHAP, MLP, transformers, large language models, or unrelated neural models in the forum classifier.
- Complex cryptographic signing, automated retraining/promotion, drift dashboards, large-scale monitoring, a second model registry, or multilingual research beyond controlled English, Bahasa Melayu, and bounded mixed-language scenarios.
- Treating fictional metrics, predicted probability, or a small language slice as learner-performance evidence or confidence.

#### Deferred to Follow-Up Work

- U10-R real-data governance, author-isolated evaluation, calibration/generalisation review, and `real_evaluated` replacement.
- Broader learner-benefit studies, production monitoring, advanced moderation, and larger bilingual model comparisons.
- Reconciliation of canonical FYP1 and CRISP-DM forum wording identified under Risks and Dependencies; those files remain unchanged by this plan-only task.

---

## Planning Contract

### Key Technical Decisions

- KTD1. **Adopt the existing baseline.** U1 stabilizes committed and current uncommitted U10 work; later units change it only where a traced requirement exposes a gap.
- KTD2. **Version the navigation index.** Use Home `0`, Forge `1`, Forum `2`, Settings `3` and remap legacy saved index `2` to Settings.
- KTD3. **Authorize at the server boundary.** Payload parsing, verified auth, student role, ownership, target existence, and domain errors share one stable callable boundary.
- KTD4. **Claim work before retry.** A transaction claims pending or expired work with event identity, lease expiry, attempt count, and newer fencing generation; model execution runs outside the transaction.
- KTD5. **Separate transient and permanent failures.** Only transient failures retry; invalid input, rejected artifacts, and exhausted attempts terminate safely.
- KTD6. **Repair from an immutable source ledger.** Helpful and acceptance actions own deterministic source records with original server timestamps; historical repair updates the originating week while the current projection advances monotonically.
- KTD7. **Keep three evidence levels separate.** `synthetic_test` proves mechanics, `controlled_demonstration` proves bounded scenario-fit and prototype integration, and `real_evaluated` is a future replacement. No release is promoted by relabelling another level.
- KTD8. **Freeze selection before final evaluation.** `evaluationGroupKey = scenarioFamilyId`, with `questionFamilyId` as additional leakage control. Select the Naive Bayes variant, preprocessing, vectorizer, n-grams, minimum document frequency, language normalization, and abstention policy only through grouped training plus validation or inner grouped cross-validation. Freeze those decisions before one evaluation on untouched grouped test evidence. If catalogue size supports only grouped cross-validation, report preliminary selection evidence with no final-test claim; fail closed when no valid grouped validation structure exists.
- KTD9. **Keep the baseline non-promotable.** Compare `MultinomialNB`, `ComplementNB`, and a deterministic rule or answer-only baseline under the same evidence and feature contract, but select only between the two Naive Bayes variants. The baseline supplies `baselineComparisonResult` and can never become a candidate or active release. Macro F1 is the default Naive Bayes selection metric, while activation additionally requires non-degeneracy and integrity gates.
- KTD10. **Preserve advisory semantics.** Predicted probability stays internal; FYP1 records `calibrationStatus: not_established_on_real_learners` and exposes only `clear`, `needs_revision`, `uncertain`, or `fallback`.
- KTD11. **Version inference by content and policy.** Logical runs bind answer ID/revision, text hash, vectorizer, classifier, and abstention policy; only the current compatible run may update feedback.
- KTD12. **Keep edit and acceptance concurrency server-owned.** Revision advancement, stale-feedback clearing, ownership, answer membership, non-self authorship, and competing acceptance are checked atomically.
- KTD13. **Activate by evidence mode and non-degeneracy.** `FORUM_MODEL_EVIDENCE_MODE=controlled_demo` accepts only a matching controlled Naive Bayes artifact whose grouped evidence, class coverage, predictions, recall, vocabulary, confusion matrix, abstention behavior, output contract, dependencies, and hashes pass. `real_evaluated_only` rejects it; fixtures and the deterministic baseline remain non-activatable.
- KTD14. **Use one immutable compatible active release.** Reuse the existing registry/manifest architecture and switch active records transactionally. Lifecycle is `candidate`, `evaluated`, `released`, `superseded`, or `revoked`; `isActive` is a separate Boolean. Only one compatible record may be `released` and active. Superseded/revoked records and their audit history remain immutable; U10-R creates a replacement record rather than mutating controlled evidence.
- KTD15. **End-load broad verification.** U1-U5 run focused gates; U6 performs documentation reconciliation and the complete automated/manual closure matrix.
- KTD16. **Hash canonical content, not execution context.** Deterministic ordering, canonical serialization, UTF-8, normalized line endings, stable numeric formatting, fixed seeds, and exact dependency versions govern reproducibility hashes. Volatile host/execution fields live in a separate execution record. When binary serialization differs across supported platforms, report semantic reproducibility, the exact artifact byte hash, and the runtime environment fingerprint instead of promising cross-environment byte equality.
- KTD17. **Keep generated rows derived.** `ai_pipeline/forum_controlled_demo/forum_scenario_catalog_v1.yaml` is authoritative. Generated rows are never hand-edited; this repository commits the fictional JSONL, dataset and split manifests, execution record, human/machine reports, and released artifact manifest because they contain no learner text and remain reproducible from the catalogue and builder.

### High-Level Technical Design

~~~mermaid
flowchart TB
  Fixture[Synthetic emulator fixture] --> Mechanics[Parser trigger and smoke evidence]
  Catalogue[Developer-approved fictional scenario catalogue] --> Builder[Deterministic schema-validated builder]
  Builder --> Dataset[Hash-bound controlled dataset]
  Dataset --> Grouped[Scenario-family grouped evidence]
  Grouped --> Train[Grouped training evidence]
  Train --> Validate[Grouped validation or inner grouped CV]
  Validate --> Select[Select Naive Bayes variant and freeze pipeline]
  Select --> Test{Untouched grouped test available}
  Test -->|yes once| Final[Final untouched-test evaluation]
  Test -->|no| Preliminary[Preliminary grouped-CV evidence only]
  Final --> Gates[Non-degeneracy and integrity gates]
  Preliminary --> Gates
  Gates --> Report[Canonical controlled-demo report]
  Report --> Release[Immutable controlled-demonstration release]
  Release --> Runtime[Automatic forum runtime]
  Future[Approved pseudonymized real evidence] -. U10-R replacement .-> RealRelease[Separate real_evaluated release]
  RealRelease -. explicit registry switch .-> Runtime
~~~

~~~mermaid
flowchart TB
  Submit[Authenticated answer create or edit] --> Claim[Transactional job claim]
  Claim --> Validate[Evidence mode and manifest validation]
  Validate -->|compatible| Model[Verified vectorizer and Naive Bayes classifier]
  Validate -->|invalid| Fallback[Deterministic safe fallback]
  Model --> Finalize[Revision and lease fenced finalization]
  Fallback --> Finalize
  Finalize --> Run[Immutable AI run]
  Finalize --> Feedback[Qualitative current feedback]
~~~

~~~mermaid
stateDiagram-v2
  [*] --> queued
  queued --> processing: atomic claim
  processing --> completed: compatible revision-bound finalization
  processing --> retryable: transient failure
  retryable --> processing: retry or expired-lease reclaim
  processing --> failed: permanent failure or retry exhaustion
  completed --> completed: duplicate delivery
  failed --> failed: duplicate delivery
~~~

~~~mermaid
flowchart TB
  Mode{FORUM_MODEL_EVIDENCE_MODE}
  Mode -->|controlled_demo| Controlled{Controlled release bindings match}
  Mode -->|real_evaluated_only| Real{Real-evaluated release bindings match}
  Controlled -->|yes| Active[Load one active compatible model]
  Controlled -->|no| Safe[Safe deterministic fallback]
  Real -->|yes| Active
  Real -->|no| Safe
~~~

### Output Structure

~~~text
ai_pipeline/forum_controlled_demo/
  README.md
  forum_scenario_catalog_v1.yaml
  schema.py
  build_forum_dataset.py
  generated/
    forum_controlled_demo_v1.jsonl
    forum_controlled_demo_v1_manifest.json
    forum_controlled_demo_split_manifest.json
    forum_controlled_demo_execution_record.json
ai_pipeline/reports/
  forum_controlled_demo_report.md
  forum_controlled_demo_report.json
functions/
  forum_model_manifest.json
~~~

`ai_pipeline/forum_controlled_demo/forum_scenario_catalog_v1.yaml` is authoritative. Generated JSONL rows are committed because they contain only developer-authored fictional text, but they are derived output: changes are made only in the catalogue and rebuilt through the deterministic builder. The catalogue, schema, builder, generated JSONL, dataset manifest, split manifest, execution record, both evaluation reports, and released artifact manifest are committed and must reproduce their declared canonical content hashes. The emulator fixture stays in its existing separate location and is never copied here. `ai_pipeline/controlled_demo/` remains the separate quiz XGBoost surface.

### Execution Order

~~~mermaid
flowchart LR
  U1[U1 Stabilize baseline and tab] --> U2[U2 Authenticated collaboration]
  U2 --> U3[U3 Trigger and counter reliability]
  U3 --> U4[U4 Controlled dataset and evaluation]
  U4 --> U5[U5 Controlled release and activation]
  U5 --> U6[U6 FYP1 prototype closure]
  U6 -. future only .-> U10R[U10-R Real-evaluated replacement]
~~~

### Assumptions and Prerequisites

- No approved real-learner forum dataset is available, and FYP1 completion does not depend on obtaining one.
- The controlled corpus is developer-approved as a prototype demonstration asset and contains only fictional examples created for the declared rubric.
- U5 may use Firebase Emulator with the same packaged function entry point when cloud deployment is unavailable. Cloud deployment remains compatible and adds runtime identity evidence when authorized.
- The older canonical FYP1 plan remains authoritative for overall project scope, but its Home quick-action and real-forum-data evidence wording are superseded for U10 and require follow-up reconciliation.
- The user-supplied canonical path ending in `(2)(1)(1).md` is absent; the repository's `docs/plans/2026-07-05-001-feat-fyp1-prototype-development-plan(2)(1).md` is used because both companions identify it as canonical.

### System-Wide Impact

- **Flutter compatibility:** The tab migration preserves legacy Settings restoration; Home loses the duplicate forum route.
- **Authorization and privacy:** Forum reads remain student-only, mutations server-authorized, and linked-parent access count-only.
- **Firestore lifecycle:** Answer revisions, jobs, immutable runs, deterministic actions, historical aggregates, and the current participation projection retain U1-U3 contracts.
- **AI evidence lifecycle:** Fixture, controlled corpus, controlled evaluation, release, runtime bundle, and future real-data release have distinct provenance and acceptance rules.
- **Runtime operations:** Retries, fenced leases, warm cache, bounded logs, source/vendor parity, exact environment recording, and safe fallback remain part of the automatic path. Dedicated runtime identity and least-privilege IAM verification apply when cloud deployment is used.
- **Compatibility:** Existing fixture jobs/runs remain mechanics evidence. Controlled activation applies to new or edited answers and does not relabel historical fixture runs.
- **Documentation:** This plan records the authoritative U10 claim boundary; canonical FYP1 and CRISP-DM wording requires follow-up reconciliation.

---

## Implementation Units

### U1. Stabilize the Existing U10 Baseline and Add the Forum Tab

- **Goal:** Convert the dirty U10 working tree into a reviewed baseline and integrate Q&A Forum as the third primary tab without duplicating implemented work.
- **Requirements:** R1, R2, R16.
- **Dependencies:** None.
- **Files:** `lib/app/logic_oasis_shell.dart`, `lib/features/home/home_page.dart`, `lib/features/settings/settings_page.dart`, `lib/shared/state/app_state.dart`, `lib/l10n/app_en.arb`, `lib/l10n/app_ms.arb`, `lib/l10n/app_localizations.dart`, `lib/l10n/app_localizations_en.dart`, `lib/l10n/app_localizations_ms.dart`, `assets/icons/nav_forum.svg`, `test/logic_oasis_shell_test.dart`, `test/app_state_test.dart`, and current uncommitted U10 files in Existing Completion Baseline.
- **Approach:** Preserve valid emulator, fixture, and integrity work and exclude `.worktrees/`. Add `QaForumPage` between Forge and Settings, remove the Home push route, move Settings navigation to index `3`, raise bounds to `0..3`, and remap legacy saved index `2` to Settings. After focused checks, stage only reviewed U10 baseline/four-tab work and create the stabilization commit before U2.
- **Patterns to follow:** `lib/app/logic_oasis_shell.dart` ordering; `lib/shared/state/app_state.dart` persistence; `QaForumPage` injection; ARB localization.
- **Test scenarios:**
  1. Covers AE1. Shell order is Home, Forge, Q&A Forum, Settings and each item selects its page.
  2. Legacy saved index `2` restores Settings at `3`; new index `2` restores Forum.
  3. Invalid indexes clamp safely under the four-tab contract.
  4. Home Settings opens index `3` and Home has no forum button/import/pushed route.
  5. Forum loading, denied, app-bar, and action controls render inside the shell.
- **Verification:** Focused shell, AppState, and forum widget tests pass; `.worktrees/` is absent from staging and the clean baseline checkpoint exists.

### U2. Complete Authenticated Collaboration and Privacy Contracts

- **Goal:** Prove student, parent, ownership, reporting, blocking, helpful, and singular-acceptance behavior through unit, Rules, widget, and authenticated emulator coverage.
- **Requirements:** R3-R6.
- **Dependencies:** U1.
- **Files:** `lib/features/collaboration/qa_forum/qa_forum_page.dart`, `lib/shared/models/forum_question.dart`, `lib/shared/models/forum_answer.dart`, `lib/shared/repositories/collaboration_repository.dart`, `firestore.rules`, `functions/main.py`, `functions/forum_runtime.py`, `functions/tests/test_forum_callable.py`, `functions/tests/test_forum_runtime.py`, `firebase_seed/tests/question_answer_keys_rules.test.js`, `tools/run_forum_emulator_flow.js`, and `test/qa_forum_flow_test.dart`.
- **Approach:** Extend existing UI/repository. Add filter, edit, report, and student-local block interactions; preserve drafts and prevent duplicate in-flight submission. Use deterministic active reports with trusted review fields, make acceptance singular, derive actors server-side, and map auth/payload/domain failures consistently. Use Auth Emulator tokens for distinct students and a parent.
- **Execution note:** Start with failing authority and singular-acceptance scenarios.
- **Patterns to follow:** Parent-link callable tests; Firestore fakes and transactions in `functions/tests/`; existing Rules boundaries.
- **Test scenarios:**
  1. Covers AE2. Students read permitted forum content; unauthenticated users/parents cannot; linked parent reads only count summary.
  2. Covers AE3. Eligible helpful succeeds; self/missing targets fail; duplicate is idempotent.
  3. Covers AE4. Only question author accepts another learner's answer and a competing acceptance fails.
  4. Invalid auth, parent role, missing/wrong payload, and domain errors map to stable callable errors.
  5. Creation enforces owner/length; report/block writes are student-scoped and private.
  6. Eligible unaccepted answer edits enter pending reclassification; foreign/accepted edits fail.
  7. Duplicate reports converge; only trusted operator path changes review fields.
  8. Filter, empty, loading, in-flight, denied, success, retryable error, report, block, helpful, accepted, `clear`, `needs_revision`, `uncertain`, and `fallback` states work.
  9. Authenticated emulator flow creates one question, answer, helpful mark, and acceptance and observes all four counters once.
- **Verification:** Focused callable/runtime, Flutter, Rules, and Auth/Functions/Firestore collaboration checks pass and freeze mutation/acceptance semantics.

### U3. Harden Trigger, Job, and Counter Reliability

- **Goal:** Make duplicate, out-of-order, concurrent, partially failed, and retried deliveries converge on one safe result and repairable weekly counters.
- **Requirements:** R7-R10.
- **Dependencies:** U2.
- **Files:** `functions/main.py`, `functions/forum_runtime.py`, `functions/tests/test_forum_trigger.py`, `functions/tests/test_forum_runtime.py`, `tools/run_forum_emulator_flow.js`, and `docs/evidence/u10-forum-emulator-validation.md`.
- **Approach:** Use transactional claims with bounded attempts, CloudEvent audit identity, logical inference identity, lease expiry, and monotonically newer fencing generation. Reclassify edits, clear stale feedback, retain immutable runs, and finalize only for matching lease/revision/text/model/policy. Keep job lifecycle separate from feedback outcome. Run models outside transactions, recover winning runs, reclaim expired work, and stop permanent/exhausted retries. Repair counters from original timestamps and immutable source actions; update historical week aggregates without regressing the current projection. Cache only a verified classifier.
- **Execution note:** Use failure-injection and concurrency tests before relying on retries.
- **Patterns to follow:** Deterministic documents in `functions/forum_runtime.py`; warm cache in `functions/main.py`; side-effect-free transaction callbacks.
- **Test scenarios:**
  1. Covers AE5. Concurrent claims converge on one lease, run, and terminal job.
  2. Duplicate/out-of-order delivery does not repeat inference, feedback, or counters.
  3. Expired lease is reclaimed and old fencing generation cannot finalize.
  4. Transient failure retries with bounded metadata; permanent/exhausted failure terminates.
  5. Run-before-job partial failure recovers without a duplicate run.
  6. Helpful/accept repair preserves original timestamp across Malaysia-week boundaries.
  7. Delayed old events cannot replace newer current-week projection.
  8. Warm-instance verification caches once; fixture/missing/mismatched artifact fails closed.
  9. Covers AE11. Edited answer gets a new inference identity and old result remains audit-only.
  10. Reacquired lease receives a newer fencing generation.
- **Verification:** Focused concurrency/failure tests and one emulator reliability smoke pass, freezing job/run/feedback and manifest-consumer contracts before U4.

### U4. Controlled-Demonstration Forum Dataset and Evaluation

- **Goal:** Build a separate fictional forum corpus, select and freeze a Naive Bayes pipeline without test leakage, and produce reproducible grouped evidence plus an eligible controlled-demonstration candidate without real learner text.
- **Requirements:** R11a, R12.
- **Dependencies:** U3.
- **Files:** `ai_pipeline/forum_controlled_demo/README.md`, `ai_pipeline/forum_controlled_demo/forum_scenario_catalog_v1.yaml`, `ai_pipeline/forum_controlled_demo/schema.py`, `ai_pipeline/forum_controlled_demo/build_forum_dataset.py`, `ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_v1.jsonl`, `ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_v1_manifest.json`, `ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_split_manifest.json`, `ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_execution_record.json`, `ai_pipeline/logic_oasis_ai/forum_ai/classifier.py`, `ai_pipeline/training/train_forum_classifier.py`, `ai_pipeline/training/evaluate_forum_classifier.py`, `ai_pipeline/reports/forum_controlled_demo_report.md`, `ai_pipeline/reports/forum_controlled_demo_report.json`, `ai_pipeline/tests/test_naive_bayes.py`, `ai_pipeline/tests/test_forum_controlled_demo_dataset.py`, and `ai_pipeline/tests/test_forum_evaluation.py`.
- **Source and repository policy:** `forum_scenario_catalog_v1.yaml` is authoritative. Catalogue fictional answer/reasoning text labelled `explanation_sufficient` or `answer_only_or_insufficient` with English, Bahasa Melayu, or controlled mixed language; mathematics scenario family; `scenarioFamilyId`; optional `questionFamilyId`; rubric/catalogue versions; and `expert_authored_controlled_demo` provenance. Reject identifiers, copied learner text, answer keys, unsupported fields, and learner-distribution claims. Generated rows are never edited manually. Commit the catalogue, schema, builder, fictional JSONL, dataset manifest, grouped split manifest, execution record, human/machine reports, and released artifact manifest; every generated item must rebuild from the catalogue. Keep the emulator fixture in its existing separate location.
- **Selection and final-test lifecycle:** Set `evaluationGroupKey = scenarioFamilyId` and keep related `questionFamilyId` examples together. Partition scenario families into grouped training, grouped validation, and untouched grouped test when independent-group and class support permit. Use training plus validation or inner `StratifiedGroupKFold` to choose only between `MultinomialNB` and `ComplementNB` and to freeze vectorizer family, tokenization, n-grams, minimum document frequency, language normalization, preprocessing, and abstention policy. After freezing, evaluate the selected pipeline once on untouched grouped test evidence. Test rows or results may not choose, revise, or expand the model, vectorizer, preprocessing, threshold, rubric, catalogue, scenario examples, or selection metric.
- **Dataset-size fallback:** When three-way grouped separation is invalid but enough independent groups and class support exist for grouped cross-validation, use grouped CV for preliminary controlled-demonstration selection evidence, record that no untouched final-test result exists, and apply non-degeneracy gates across applicable held-out folds. Do not describe CV metrics as final-test performance. When neither valid grouped validation/CV nor valid grouped test evidence can be supported, return `controlled_catalogue_insufficient` and produce no activatable candidate. Never weaken grouping, manufacture examples inside the evaluator, or use row-level random splitting.
- **Comparator contract:** Evaluate `MultinomialNB`, `ComplementNB`, and the deterministic rule/answer-only baseline using identical source rows, grouped evidence, labels, train-only fitted preprocessing, feature/vectorizer/tokenization/n-gram/minimum-document-frequency/language contracts, abstention evaluation, and report structure. The baseline is comparison-only and never eligible for candidate selection, release, or activation. Selection occurs only between the two Naive Bayes variants.
- **Baseline outcome:** If neither Naive Bayes variant outperforms the baseline, set `baselineComparisonResult` to state that no controlled-scenario advantage was demonstrated. A non-degenerate selected Naive Bayes artifact may still proceed for the required automatic FYP1 architecture after every evidence, integrity, abstention, revision, runtime, and release gate passes, but no accuracy, superiority, or effectiveness claim is permitted.
- **Non-degeneracy candidate gates:** Both labels exist in training and in validation when used; both exist in untouched grouped test evidence when a final test exists; the classifier predicts both classes at least once on applicable held-out evidence; neither class has zero recall on the applicable final held-out evaluation; the labelled confusion matrix is valid; vectorizer vocabulary is non-empty; preprocessing and group-leakage checks pass; no test row is fitted; abstention does not convert every held-out example to `uncertain`; publication/fallback coverage is reported; the artifact loads and reproduces its declared output contract; and all hashes/dependencies bind. Failure records `controlledCandidateStatus: rejected`, `activationStatus: blocked`, and the exact failed gate. Do not invent an accuracy or F1 threshold.
- **Report contract:** Record accuracy, macro F1, per-class precision/recall/F1/support, balanced accuracy when needed, labelled confusion matrix, abstention and publication/fallback coverage, latency, serialized size, dataset/group/class counts, split/seed, preprocessing/rubric/catalogue versions/hashes, limitations, `candidateSelectionDecision`, `selectedNaiveBayesVariant`, `baselineComparisonResult`, `controlledDemoActivationDecision`, candidate/activation status, and claim level. Macro F1 is the primary Naive Bayes selection metric unless a reason is documented; it is not an activation threshold. Record `calibrationStatus: not_established_on_real_learners`.
- **Canonical reproducibility:** Use deterministic ordering, canonical serialization, UTF-8, normalized line endings, stable numeric formatting, fixed seeds where applicable, and exact dependency versions for dataset, manifest, split, report, vectorizer, and classifier reproducibility. Exclude timestamps, absolute/user-profile paths, host/machine names, temporary paths, process IDs, platform cache paths, non-deterministic archive metadata, and environment-specific diagnostics from canonical hashes. Put execution timestamp, OS, Python version, command, repository-relative logical working path, environment mode, and a non-secret opaque operator identifier or role in `forum_controlled_demo_execution_record.json`; this record does not alter canonical hashes. Reject credentials, environment-variable values, user-profile names, hostnames, and absolute paths from committed execution metadata. If model serialization cannot be byte-identical across supported platforms, report `semanticReproducibilityStatus`, the exact `artifactByteHash`, and `runtimeEnvironmentFingerprint` rather than claiming incompatible environments produce identical binaries.
- **Claim metadata:** Report/candidate include `claimLevel: controlled_demonstration_only`, `trainingDataProvenance: expert_authored_controlled_demo`, `evidenceLevel: controlled_demonstration`, `releaseScope: fyp1_forum_controlled_demo`, and `deploymentScope: controlled_demo`.
- **Limitation statement:** “The metrics demonstrate reproducible classifier behaviour, scenario-fit, artifact integrity, and prototype integration readiness. They do not establish predictive accuracy, generalisability, educational effectiveness, or performance for real primary-school learners.”
- **Execution note:** Build schema, canonical determinism, split isolation, selection freeze, leakage, and insufficiency tests before accepting controlled provenance.
- **Patterns to follow:** `ai_pipeline/controlled_demo/`; `ai_pipeline/training/publish_controlled_demo_bundle.py`; existing forum vectorizer/classifier pipeline.
- **Test scenarios:**
  1. Emulator fixture stays parser/emulator-only and cannot enter controlled evaluation.
  2. Fictional multilingual rows validate only with declared labels, family, rubric/catalogue, and provenance.
  3. Learner identity, copied forum provenance, answer keys, unsupported fields, or real-data claims fail.
  4. Same catalogue reproduces canonical ordering/hashes/counts across normalized line endings; catalogue edit changes the manifest hash and manual generated-row edits fail verification.
  5. Covers AE7. Class/group/leakage/preprocessing failure returns `controlled_catalogue_insufficient` with no candidate.
  6. Covers AE13. Training/validation selects and freezes the Naive Bayes pipeline; a sentinel test proves untouched test rows and results cannot influence selection or configuration.
  7. Covers AE14. Three-way grouped evidence yields one final test; valid grouped-CV fallback reports no final test; invalid grouped validation/CV produces no candidate.
  8. Comparators use identical evidence contracts, but only `MultinomialNB` or `ComplementNB` can populate `selectedNaiveBayesVariant`.
  9. Covers AE15. A baseline win is reported without activating the baseline or claiming Naive Bayes superiority.
  10. Covers AE16. Every non-degeneracy failure rejects the candidate and names its failed gate.
  11. Report contains all metrics, selection/activation fields, bindings, applicable final-test status, and no confidence wording.
  12. Canonical content reproduces independently of volatile execution fields; execution-record changes do not alter canonical hashes.
  13. Same compatible environment reproduces semantic outputs and declared byte hashes; incompatible serialization environments are distinguished through the runtime fingerprint.
  14. Future real-data evaluator rejects controlled provenance.
- **Verification:** Dataset/schema, repository policy, canonical determinism, grouped split isolation, selection freeze, comparator parity, baseline non-promotion, non-degeneracy, metrics, abstention, latency, size, claim metadata, and reproducibility tests pass. One immutable report and eligible Naive Bayes candidate exist, or the report records `controlled_catalogue_insufficient`/rejection without claiming activation readiness.

### U5. Controlled-Demo Release and Runtime Activation

- **Goal:** Release and activate a genuine Naive Bayes vectorizer/classifier as the normal successful FYP1 forum AI path, only under controlled-demo mode.
- **Requirements:** R13, R14, R17.
- **Dependencies:** U4.
- **Files:** `ai_pipeline/training/publish_forum_controlled_demo.py`, `ai_pipeline/logic_oasis_ai/model_registry.py`, `functions/forum_model.joblib`, `functions/forum_model_manifest.json`, `functions/forum_runtime.py`, `functions/main.py`, `functions/vendor/logic_oasis_ai/forum_ai/`, `functions/vendor/bundle_manifest.json`, `tools/deploy_forum_runtime_iam.py`, `tools/tests/test_deploy_forum_runtime_iam.py`, `functions/tests/test_forum_runtime.py`, `ai_pipeline/tests/test_forum_model_promotion.py`, and `docs/evidence/u10-forum-controlled-demo-release.md`.
- **Approach:** Publish one immutable release using the existing forum manifest/registry architecture; do not create a second registry. Bind catalogue, generated dataset, dataset/split manifests, rubric, preprocessing, vectorizer, selected Naive Bayes classifier, evaluation reports, abstention policy, dependencies, code revision, artifact byte hash, semantic reproducibility status, runtime environment fingerprint, release record, advisory scope, runtime bundle, and deployment scope. The baseline has no publish path.
- **Release metadata:** Record `releaseId`, `releasedBy`, trusted/server-controlled `releasedAt`, `releaseRationale`, nullable `supersedesReleaseId`, `trainingDataProvenance`, `evidenceLevel`, `releaseScope`, `deploymentScope`, and `claimLevel`. Use `lifecycleStatus` (`candidate`, `evaluated`, `released`, `superseded`, or `revoked`) separately from Boolean `isActive`; do not use an overlapping `releaseStatus`. Only one compatible record may have `lifecycleStatus: released` and `isActive: true`.

~~~yaml
releaseId: immutable release identifier
releasedBy: developer or operator identifier
releasedAt: server-controlled or trusted release timestamp
lifecycleStatus: released
isActive: true
releaseRationale: >
  Developer-released FYP1 controlled-demonstration model.
  Not evaluated on real learner forum responses.
supersedesReleaseId: null
trainingDataProvenance: expert_authored_controlled_demo
evidenceLevel: controlled_demonstration
releaseScope: fyp1_forum_controlled_demo
deploymentScope: controlled_demo
claimLevel: controlled_demonstration_only
~~~

- **Release lifecycle:** Creation fields and evidence bindings become immutable at release. Switching releases is one explicit registry transaction that activates the new compatible released record and marks the prior record inactive/superseded with `supersedesReleaseId` on the replacement. Deactivate or revoke records instead of deleting them; preserve superseded/revoked audit history. Never mutate a controlled release into `real_evaluated`.
- **Runtime mode:** `FORUM_MODEL_EVIDENCE_MODE=controlled_demo` accepts only matching controlled evidence and an eligible selected Naive Bayes artifact; `real_evaluated_only` rejects it. Fixtures and the deterministic baseline remain non-activatable. Missing/mismatched bindings, failed non-degeneracy gates, unsupported dependency/schema, zero or multiple compatible active releases, or load-before-validation fail closed. Validate before loading and cache only the verified vectorizer/classifier pair.
- **Automatic path:** Normal FYP1 uses a new developer-authored demonstration answer submitted through the normal authenticated forum flow with a designated test student account and reaches genuine Naive Bayes. The runtime input is not reused as hidden training data, silently added to the evaluation corpus, or described as real learner evidence. Fallback is reserved for faults, invalid registry evidence, incompatible revision, disabled mode, or unsupported input.
- **Release rationale:** State that this is a developer-released FYP1 controlled-demonstration model not evaluated on real learner forum responses; separately report when `baselineComparisonResult` shows no controlled-scenario Naive Bayes advantage.
- **Rollback:** Transactionally deactivate/revoke the current record and create a new immutable replacement release that references the last compatible controlled artifact and supersedes the current release. Leave earlier superseded/revoked records unchanged and preserve releases, jobs, runs, actions, and audit history. Never delete a record or relabel it `real_evaluated`.
- **Execution note:** Start with fail-closed promotion and mode tests; activate only after U4 hashes and source/vendor parity match.
- **Patterns to follow:** Controlled-demo one-active/evidence-mode pattern in `docs/plans/2026-07-24-001-feat-controlled-demonstration-xgboost-model-plan.md`; current forum manifests and service account.
- **Test scenarios:**
  1. Covers AE6. Fixture artifacts cannot publish/load outside emulator/test.
  2. Covers AE8. Complete controlled release activates only in `controlled_demo`.
  3. Covers AE9. Every missing/mismatched binding fails closed.
  4. Activation rejects zero or multiple compatible active released records and enforces the `lifecycleStatus`/`isActive` contract transactionally.
  5. Source/vendor match and unsupported dependencies/schema cannot load.
  6. Covers AE10. A developer-authored demonstration answer submitted through an authenticated test student account reaches genuine Naive Bayes qualitative feedback, one run, and one terminal job without text logs or corpus mutation.
  7. Covers AE11. Late inference cannot overwrite newer revision feedback.
  8. Failure/disabled mode yields deterministic fallback preserving answer/audit.
  9. If cloud is used, endpoints declare dedicated runtime identity and IAM rejects default/unintended broad identity.
  10. Candidate rejection records the exact non-degeneracy failure and blocks activation without inventing a metric threshold.
  11. Released creation/binding fields cannot mutate; replacement sets `supersedesReleaseId`, preserves audit history, and switches active releases in one transaction.
  12. Evidence has the limitation statement, explicit baseline result, and no production/learner-validity/superiority claim.
- **Verification:** Candidate eligibility, release metadata/lifecycle, evidence mode, one-active transaction, parity, fail-closed runtime, automatic inference, revision fencing, fallback, and safe-log tests pass. Emulator activation suffices for FYP1 when cloud access is unavailable; cloud identity evidence is added when used.

### U6. FYP1 Prototype Closure, Verification, and Evidence

- **Goal:** Reconcile documentation, run the complete automated/manual matrix, and record truthful controlled-demonstration-only U10 closure.
- **Requirements:** R15-R17.
- **Dependencies:** U1-U5.
- **Files:** `docs/architecture/logic-oasis-firestore-database-schema.md`, `docs/architecture/logic-oasis-ai-pipeline-crisp-dm.md`, `docs/logic_oasis_feature_implementation_explanation.md`, `docs/evidence/u10-forum-emulator-validation.md`, `docs/evidence/u10-forum-controlled-demo-release.md`, `docs/evidence/u10-forum-fyp1-final-closure.md`, `firestore.rules`, `firebase.json`, `test/`, `functions/tests/`, `ai_pipeline/tests/`, `tools/tests/`, and `firebase_seed/tests/question_answer_keys_rules.test.js`.
- **Approach:** Reconcile navigation, forum schema/states, evidence ladder, catalogue/evaluation, selection/final-test lifecycle, canonical hashes, release lifecycle, mode, identity, qualitative outcomes, limitations, and U10-R route. Run Flutter, Python, Rules, multi-emulator, release-contract, and manual student/linked-parent matrices. Capture a new developer-authored demonstration answer submitted through an authenticated test student account traversing answer-to-job-to-inference-to-run-to-feedback, plus safe logs, corpus non-mutation, parity, release bindings, and rollback/deactivation. Cloud is optional; Emulator using the same packaged entry point can satisfy FYP1 when disclosed.
- **Claim boundary:** Evidence states scenario-fit, artifact integrity, reproducible behavior, and prototype integration readiness only; it never says production-validated, real-world validated, learner-validated, generalisable, educationally effective, or more accurate for real learners.
- **Test scenarios:**
  1. Final docs agree on tab order, schema, job/counter semantics, provenance, mode, calibration, identity, and claims.
  2. Full Flutter analysis/tests pass.
  3. Full AI and Functions suites pass controlled dataset/evaluation, selection freeze, untouched-test isolation, non-degeneracy, release lifecycle, retry, counter, mode, rejection, and applicable IAM contracts.
  4. Rules and Auth/Functions/Firestore Emulator suites pass roles, actions, counters, and automatic feedback.
  5. Multi-student rehearsal covers tab, filter, ask, answer, revision feedback, helpful, accept, report, block, errors, and parent isolation.
  6. Duplicate events, stale leases, run recovery, stale revisions, counter repair, timestamps, and Malaysia-week projection remain proven.
  7. A valid controlled artifact automatically classifies a new demonstration answer from an authenticated test student account without adding it to the corpus; fixture/baseline/mode/hash/dependency/revision mismatches fail safely.
  8. Logs contain no forum text and parity plus exact environment are recorded.
  9. Rollback/mode disable restores safe fallback without deleting immutable records.
  10. Cloud unavailability, weak language slice, insufficient catalogue, or other limitation is recorded without making U10-R a blocker.
- **Verification:** Verification Contract and Definition of Done pass; abandoned U10-owned attempts are removed; `.worktrees/` is not staged; final evidence states controlled-demonstration closure or the exact engineering blocker.

---

## Deferred Future Upgrade

### U10-R. Real-Evaluated Forum Model Replacement

This future unit is not part of the FYP1 Definition of Done and does not block U1-U6.

1. Obtain an approved consented or approved-external forum dataset.
2. Keep raw text outside version control and the deployed Functions bundle.
3. De-identify free text and pseudonymize authors with a documented stable grouping method.
4. Label independently under the frozen rubric and record agreement/disagreement.
5. Use author-grouped train, validation, and untouched test separation; keep duplicates together.
6. Evaluate real-data performance, false rejection, adequately supported language slices, calibration, and generalisation without tuning on untouched test.
7. Issue a separate immutable `real_evaluated` declaration with consent/provenance, retention, report, artifact, dependency, and approval bindings.
8. Deploy only under compatible `real_evaluated_only` mode.
9. Replace through an explicit one-active registry transaction; never mutate/relabel controlled release.
10. Retain rollback, revocation, fallback, and evidence-aware projections.
11. Prohibit test-driven retuning, automatic retraining, and automatic promotion.
12. Reuse the forum UI, job, registry, revision, privacy, runtime identity, and fallback architecture.

---

## Verification Contract

| Gate | Applies after | Evidence of success |
|---|---|---|
| Focused shell/navigation | U1 | Four-tab order, Settings migration, removed Home route, and clean baseline checkpoint are proven. |
| Focused collaboration | U2 | Functions, Rules, widget, and authenticated emulator tests prove roles, denials, actions, singular acceptance, reporting/blocking, and four counters. |
| Focused reliability | U3 | Failure/concurrency tests plus emulator smoke prove duplicate convergence, fenced leases, retries, run recovery, counter repair, timestamps, and warm-cache validation. |
| Controlled dataset/evaluation | U4 | Authoritative-source/rebuild policy, canonical determinism, grouped train/validation/test isolation, selection freeze, CV-only labelling, comparator parity, baseline non-promotion, non-degeneracy, metrics, latency, size, insufficiency, claims, and reproducibility pass. |
| Controlled release | U5 | Only a completely bound, eligible selected Naive Bayes artifact activates in `controlled_demo`; baseline/fixture/real-only mode, invalid lifecycle state, failed candidate gate, and every binding mismatch reject safely. |
| Automatic forum AI | U5-U6 | A new developer-authored demonstration answer submitted through an authenticated test student account traverses normal submission, claim, genuine Naive Bayes, immutable run, and revision-bound feedback without fallback as normal path or corpus mutation. |
| Flutter full gate | U6 | `flutter analyze --no-pub` and `flutter test --no-pub` pass. |
| AI full gate | U6 | `py -3.11 -m unittest discover -s ai_pipeline/tests` passes classifier, corpus, evaluation, boundary, and promotion tests. |
| Functions full gate | U6 | `py -3.11 -m unittest discover -s functions/tests` passes callable, trigger, runtime, privacy, retry, lease, revision, and counters. |
| Rules gate | U6 | `firebase_seed/tests/question_answer_keys_rules.test.js` passes under Firestore Emulator. |
| Multi-emulator gate | U6 | Auth, Firestore, and Functions emulators complete collaboration and controlled-demo AI with all counters. |
| Manual student/parent | U6 | Multi-student and linked-parent journeys match Product Contract and count-only parent projection. |
| Release integrity/environment | U6 | Canonical hashes, semantic/byte/environment fields, immutable metadata, one-active transaction, parity, and exact Emulator/cloud environment are recorded and valid. |
| Safe deactivation/claims | U6 | Disable/rollback restores fallback, logs contain no text, and evidence stays controlled-only. |
| Optional cloud identity | U6 when cloud is used | Forum endpoints use dedicated runtime identity and IAM rejects default/unintended broad identities. |

---

## Risks and Dependencies

| Risk or dependency | Treatment |
|---|---|
| Catalogue too small or lacks classes across groups | Return `controlled_catalogue_insufficient`; expand only with developer-authored fictional scenarios, never weakened grouping or evaluator-manufactured rows. |
| Test evidence influences selection | Freeze the Naive Bayes variant, preprocessing, vectorizer, feature configuration, and abstention policy through grouped training/validation only; run untouched test once and prohibit test-driven corpus/rubric/configuration changes. |
| Catalogue supports grouped CV but not a final test | Label metrics preliminary, state that no untouched final-test result exists, and never present CV as final-test performance. Produce no candidate if valid grouped validation/CV is impossible. |
| Fixture mistaken for controlled corpus | Enforce separate provenance, directories, manifests, and evaluator rules. |
| Generated rows diverge from catalogue | Make the YAML catalogue authoritative, prohibit manual row edits, and verify committed generated JSONL/manifests/reports rebuild exactly. |
| Fictional scenarios encode assumptions | Document scenario assumptions and forbid learner-distribution/generalisation/effectiveness claims. |
| Related examples leak | Group by scenario family and check question-family leakage before fitting. |
| Accuracy or macro F1 hides degenerate behavior | Select the Naive Bayes variant by macro F1 but separately require both-class predictions, non-zero class recall on applicable final held-out evidence, valid confusion matrix/vocabulary, and non-collapsed abstention before activation. |
| Baseline outperforms Naive Bayes | Report that no controlled-scenario advantage was demonstrated; never release the baseline, and allow only a non-degenerate Naive Bayes architecture demonstration with no superiority claim. |
| Volatile metadata breaks reproducible hashes | Canonicalize deterministic content and keep timestamps, paths, hosts, process IDs, and environment diagnostics in the separate execution record. Distinguish semantic reproducibility, byte hash, and environment fingerprint when binary serialization differs. |
| Probability becomes confidence | Record `not_established_on_real_learners` and expose qualitative outcomes only. |
| Fallback becomes normal path | Require genuine Naive Bayes success in normal rehearsal; fallback is safety evidence only. |
| Controlled artifact enters real mode | Evidence-mode and release-scope checks reject before load. |
| Release records drift or two become active | Freeze creation/binding fields, preserve superseded/revoked audit records, and switch the single compatible active released record transactionally rather than deleting or mutating it. |
| Retry/edit corrupts state | Preserve U3 claims, fencing, identities, immutable runs, timestamps, and repair tests. |
| Emulator mistaken for IAM proof | State environment; require IAM evidence only when cloud is used and never call Emulator evidence production validation. |
| Canonical FYP1 plan requires consented forum data and Home quick action | Treat this U10 plan as superseding U10 evidence/navigation; reconcile canonical wording separately. |
| CRISP-DM 7.4/U10 requires pseudonymized real export and author-aware evaluation | Reconcile companion later to recognize evidence levels and move those controls to U10-R. |
| Named canonical `(2)(1)(1).md` is missing | Use existing `(2)(1).md` identified as canonical by both companions and record filename mismatch. |

---

## Definition of Done

- U1-U6 complete in dependency order and focused gates pass before dependent work.
- App has Home, Forge, Q&A Forum, Settings; legacy Settings migrates and Home has no duplicate forum.
- Authenticated tests prove collaboration, stable errors, singular acceptance, report/block, student-only content, parent count-only access, and raw-data denials.
- Duplicate/concurrent/stale/out-of-order/transient/permanent/partial deliveries converge on one compatible job/run/result and repair counters in the original Malaysia week.
- Emulator fixture remains `synthetic_test` and never becomes controlled evaluation evidence.
- Separate fictional controlled corpus is canonically reproducible/hash-bound from the authoritative catalogue and passes provenance, class, language, scenario-family, and question-family leakage controls; generated rows are never manually edited.
- `MultinomialNB`, `ComplementNB`, and the non-promotable baseline share the evidence contract. Only grouped training/validation selects and freezes a Naive Bayes pipeline; untouched grouped test evidence is used once when available, grouped-CV-only evidence is labelled preliminary, and invalid evidence returns `controlled_catalogue_insufficient` with no candidate.
- Report records required metrics/bindings/limitations, selection and baseline fields, applicable final-test status, every non-degeneracy gate, `calibrationStatus: not_established_on_real_learners`, and `claimLevel: controlled_demonstration_only`; macro F1 alone never authorizes activation.
- Active FYP1 artifact is a genuine non-degenerate vectorizer/Naive Bayes bundle bound to catalogue, generated dataset/split manifests, evaluation reports, rubric, preprocessing, policy, dependencies, code, immutable release, artifact, runtime bundle, and `controlled_demo` scope. The deterministic baseline has no release or activation path.
- Canonical content hashes exclude volatile execution metadata; the separate execution record carries timestamp/host/path context, and binary reproducibility claims distinguish semantic status, artifact byte hash, and runtime environment fingerprint.
- Release creation/binding fields are immutable; lifecycle state and `isActive` remain distinct; exactly one compatible released record is active; switching is transactional; superseded/revoked records remain auditable and undeleted.
- Controlled artifact loads only under `FORUM_MODEL_EVIDENCE_MODE=controlled_demo`; real-only mode, fixture provenance, unsupported versions, multiple active models, or missing bindings fail safely.
- One new developer-authored demonstration answer submitted through an authenticated test student account automatically reaches genuine Naive Bayes feedback, one immutable run, and terminal job through the packaged runtime without becoming training/evaluation evidence; fallback is not normal success.
- Logs contain no forum text, parity is proven, and exact Emulator/cloud environment is recorded.
- Safe deactivation/rollback preserves content, immutable jobs/runs/actions, and fallback.
- Documentation distinguishes `synthetic_test`, `controlled_demonstration`, and `real_evaluated` and identifies U10-R as future.
- Verification Contract passes, or evidence names the exact unmet engineering gate without claiming closure.
- U10-R data acquisition, steward approval, retention/deletion, author-grouped learner evaluation, `real_evaluated` activation, production learner-text smoke, 24-hour observation, and production sign-off are not FYP1 Definition of Done.
- Final wording makes no real-student accuracy, superiority, generalisability, educational-effectiveness, learner-validation, or production-validation claim.
- Abandoned U10-owned attempts are removed; generated artifacts are reproducible; unrelated `.worktrees/` is excluded.

---

## Sources and Research

- Current U10 baseline: `docs/plans/2026-08-01-001-feat-u10-forum-production-closure-plan.md`.
- Controlled-demo precedent: `docs/plans/2026-07-24-001-feat-controlled-demonstration-xgboost-model-plan.md`.
- AI methodology and outstanding forum mismatch: `docs/architecture/logic-oasis-ai-pipeline-crisp-dm.md`.
- Canonical scope and outstanding forum/navigation mismatch: `docs/plans/2026-07-05-001-feat-fyp1-prototype-development-plan(2)(1).md`.
- Mechanics-only emulator evidence: `docs/evidence/u10-forum-emulator-validation.md`.
- Controlled-demo release evidence pattern: `docs/evidence/2026-07-24-controlled-demo-xgboost-release.md`.
