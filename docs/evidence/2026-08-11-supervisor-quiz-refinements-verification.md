---
artifact_contract: supervisor-quiz-refinements-verification/v1
title: Supervisor Quiz Learning Loop Refinements - Verification Evidence
type: evidence
date: 2026-08-12
status: automated_gates_passed_manual_review_pending
plan: docs/plans/2026-08-11-001-feat-supervisor-quiz-learning-loop-refinements-plan.md
---

# Supervisor Quiz Learning Loop Refinements - Verification Evidence

This document records the evidence for the seven supervisor refinements
(U15-U19, with U20 documentation/seed closure). It distinguishes **automated
evidence** (contract, unit, widget, parity, and emulator gates that pass on
this branch) from **manual child-language/content review** (human sign-off
still required before any external demonstration).

## Seven-Item Traceability Table

| # | Supervisor item | Shipped behavior | Automated contract test | Evidence |
|---|---|---|---|
| 1 | Child-friendly wrong-answer help | Wrong selections return the selected option's authored bilingual hint, optional different-number example, and review focus; no answer reveal; correct answers keep positive confirmation. | `firebase_seed/tests/question_bank_pedagogy.test.js` (feedback completeness, no-answer-reveal, live-value reuse); `functions/tests/test_quiz_session.py` (two wrong options -> two hints, payload bound); `test/quiz_feedback_guidance_test.dart` (hint/example/focus UI). | `python -m pytest` quiz files; `flutter test` quiz suites; emulator `npm test` PASS. |
| 2 | Next attempt destination | Server writes `recommendedLearningAction` (`repeat_subtopic`/`advance`) with target IDs; ResultPage shows one server-backed CTA; repeat restarts the same subtopic, advance opens the next ordered item; fallback uses labelled correct rate. | `functions/tests/test_ai_runtime.py` (below/at threshold, evidence gate, fallback label); `test/quiz_result_navigation_test.dart` (repeat/advance/next-topic/Forge flows). | `python -m pytest functions/tests/test_ai_runtime.py`; `flutter test test/quiz_result_navigation_test.dart`. |
| 3 | Exact review information | Result lists each missed question by sequence/prompt with authored type and focus (EN + BM); perfect score shows success; no count-only summary. | `functions/tests/test_quiz_session.py` (review items in order, bilingual); `functions/tests/test_quiz_finalize_review.py` (Firestore-backed finalize); `test/quiz_review_list_test.dart` (cards, BM fields, perfect score). | `flutter test test/quiz_review_list_test.dart`; pytest quiz files. |
| 4 | Meaningful difficulty differences | Easy/Moderate/Hard banks carry reviewed cognitive-demand metadata validated against the labelled band; no difficulty label on subtopic cards or in quizzes. | `firebase_seed/tests/question_bank_pedagogy.test.js` (band matching, relabel rejection); `test/subtopic_mastery_display_test.dart` (no Easy/Moderate/Hard text); `test/quiz_review_list_test.dart` (difficulty only in result panel). | Seed pedagogy PASS; `flutter test` display/review suites. |
| 5 | Zero-percent unlocking | Any valid finalized attempt writes `attempted`/`accessUnlocked`; 0% unlocks the next subtopic while `completed` stays false and repeat is recommended. | `functions/tests/test_quiz_finalize_review.py` (0% soft unlock, completed preserved); `test/app_state_test.dart` (trusted completion unlocks without completing); `test/subtopic_mastery_display_test.dart` (0% unlocks next card, topic bar at 0). | pytest finalize suite; `flutter test test/app_state_test.dart`. |
| 6 | BKT progress and next level | Subtopic cards show the server BKT mastery percentage with `Still learning`/`Ready to move on`, honest pending/fallback wording; topic progress stays completed-subtopic coverage; next assigned difficulty appears only in the result next-practice panel. | `test/subtopic_mastery_display_test.dart` (43% without rate reuse, pending no percentage, fallback label, completion-based topic progress); `test/quiz_review_list_test.dart` (panel-only difficulty). | `flutter test test/subtopic_mastery_display_test.dart test/quiz_review_list_test.dart`. |
| 7 | Material-grounded questions | Every active question carries material ID, bilingual locator, content digest, author/reviewer state, type, and review focus; no generative content; unapproved changes block activation. | `firebase_seed/tests/question_bank_pedagogy.test.js` (provenance, digest-change blocking, reviewer state); `firebase_seed/tests/question_answer_keys_rules.test.js` (manifest server-only). | Seed pedagogy + emulator rules PASS; `node validate_question_banks.js` (70 approved entries). |

## Scenario Coverage (U15-U19)

| Unit | Scenario coverage | Gate |
|---|---|---|
| U15 | Approved set passes; missing feedback/reviewer/locator/BM parity fails; hint/example reveal fails; difficulty relabel fails; cross-bank duplication fails; content digest change blocks activation; clients cannot read drafts/manifest. | `firebase emulators:exec "npm test"` (pedagogy + rules); `node firebase_seed/validate_question_banks.js`. |
| U16 | Two wrong options -> different hints; correct response has no feedback; idempotent retry identical; completion returns only missed items in order with bilingual prompt/type/focus; payload inspection shows no answer data; malformed feedback fails closed. | `python -m pytest functions/tests/test_quiz_session.py functions/tests/test_attempt_validation.py functions/tests/test_quiz_trigger.py`; `flutter test test/quiz_session_service_test.dart`. |
| U17 | 0% writes attempted/access with provisional repeat; BKT below/above threshold with evidence gate; correct-rate fallback labelled and deterministic; older events cannot overwrite; rules allow owner reads only; reattempt cannot reset completion; pending analysis returns retryable error. | `python -m pytest functions/tests/test_quiz_trigger.py functions/tests/test_ai_runtime.py functions/tests/test_start_quiz_session_adaptive.py`; emulator rules test. |
| U18 | 0% unlocks without completing; 43% renders without rate reuse; pending renders no percentage; fallback labelled; topic progress = completed/total; no difficulty text; BM copy overflow-safe. | `flutter test test/app_state_test.dart test/learning_repository_test.dart test/subtopic_mastery_display_test.dart`. |
| U19 | Two-error review cards without count; EN/BM review fields; processing disables CTA but keeps Back to Forge; repeat/advance/next-topic/Forge navigation; panel-only difficulty; fallback labelled; perfect score success. | `flutter test test/quiz_feedback_guidance_test.dart test/quiz_result_navigation_test.dart test/ai_result_page_status_test.dart test/quiz_review_list_test.dart`. |

## Verification Gates (automated, all passing on branch `codex/integrate-forum-cloud-supervisor-plans`)

| Gate | Command | Result |
|---|---|---|
| Seed pedagogy + content approval | `firebase emulators:exec "npm test"` (firebase_seed) | PASS - 35 source-grounded questions, rules deny answer keys/manifest |
| Seed CLI | `node firebase_seed/validate_question_banks.js` | PASS - 70 approved entries across 2 Year 4 materials |
| Callable/runtime contracts | `python -m pytest functions/tests/test_quiz_session.py functions/tests/test_attempt_validation.py functions/tests/test_quiz_trigger.py` | 27 passed |
| BKT completion/next action | `python -m pytest functions/tests/test_ai_runtime.py functions/tests/test_start_quiz_session_adaptive.py functions/tests/test_quiz_finalize_review.py` | passed (incl. Firestore-backed finalize) |
| Full functions suite | `python -m pytest functions/tests --ignore=tests/test_policy_evaluation_study_flow.py` | 156 passed, 21 subtests (3 pre-existing forum revision-mismatch failures unrelated to quiz work) |
| AI pipeline suite | `python -m pytest ai_pipeline/tests` | 620 passed, 99 subtests |
| Bundle/source parity | `python tools/build_function_bundle.py`; `python -m pytest tools/tests/test_function_bundle_parity.py ai_pipeline/tests/test_source_parity.py` | regenerated; 5 + 11 passed |
| Flutter contracts | `flutter test` (full suite) | 117 passed |
| Static quality | `flutter analyze --no-pub` | No issues |
| Firestore rules (emulator) | `firebase emulators:exec --only firestore "node firebase_seed/tests/question_answer_keys_rules.test.js"` | PASS - owner-only mastery reads, answer-key/manifest denial |

## Manual Review Checklist (human sign-off required)

The following is **manual evidence**, not automated, and must be signed by the
content reviewer before any external demonstration:

- [ ] Sampled English and Bahasa Melayu hints use simple primary-school language.
- [ ] Sampled hints, examples, and review focuses match the supplied Year 4-6
      textbook material (locators in `contentSourceManifest`).
- [ ] No sampled hint or example reveals the correct live option.
- [ ] Question types and review focuses are meaning-equivalent in English and
      Bahasa Melayu.
- [ ] Difficulty classification (Easy/Moderate/Hard) matches the declared
      cognitive-demand metadata.

## Emulator Journey Observations

The automated emulator journey covers: seed validation (approved set accepted,
unreviewed content rejected), rules denial of answer keys and the content
manifest, owner-only mastery reads, and deterministic rules-test assertions.
The interactive full-loop journey (start -> submit -> finalize -> AI trigger ->
result navigation) is exercised by the widget/integration test suites with
in-memory fakes; a full Firebase-emulator interactive run with seeded content is
recommended before the supervisor demonstration and is tracked as manual
evidence above.

## Definition of Done Checklist

- [x] Each supervisor item maps to shipped behavior, an automated test, and a
      row in the traceability table above.
- [x] Wrong selections receive option-specific, simple, bilingual,
      source-approved help with no correct-answer leak.
- [x] Results identify every missed question with authored type and focus.
- [x] Easy/Moderate/Hard banks pass the cognitive-demand rubric; labels absent
      from subtopic cards and active quizzes.
- [x] A 0% trusted attempt unlocks the next subtopic without completion or
      topic-progress credit.
- [x] Subtopic cards show safe BKT mastery or an honest pending/fallback state.
- [x] The result CTA repeats/advances from the server recommendation and shows
      the next assigned difficulty only after the quiz.
- [x] Topic progress represents completed subtopics, not score or average BKT.
- [x] No active question lacks a source locator and review state; no generative
      content is introduced.
- [x] Firestore/callable boundaries hide answer keys, raw BKT/model data, and
      the content approval manifest.
- [x] Documentation reflects the new semantics (schema, CRISP-DM, feature
      explanation, seed README).
