from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "functions"))
sys.path.insert(0, str(ROOT / "functions/vendor"))

from forum_runtime import (
    ForumAiClaim,
    ForumAiBundle,
    ForumOutcome,
    FORUM_COMPOSITE_POLICY_VERSION,
    FORUM_CONTROLLED_CLAIM_LEVEL,
    FORUM_PUBLIC_STATE_MAY_BE_IRRELEVANT,
    ForumRuntimeError,
    ForumRuntimeGateway,
    FORUM_PUBLIC_STATE_VERIFIED,
    FORUM_PUBLIC_STATE_NONE,
    FORUM_REASONING_MODEL_VERSION,
    FORUM_RELEVANCE_MODEL_VERSION,
    RELEVANCE_NEGATIVE_THRESHOLD,
    RELEVANCE_POSITIVE_THRESHOLD,
    _answer_content_hash,
    _transaction_snapshot,
    feedback_for,
    load_forum_bundle,
    load_forum_classifier,
    malaysia_week_start,
)
from logic_oasis_ai.forum_ai.classifier import ForumPrediction, REVISION, SUFFICIENT, UNCERTAIN
from logic_oasis_ai.forum_ai.relevance import ForumRelevancePrediction


class _Snapshot:
    def __init__(self, data, identifier=None):
        self._data = data
        self.id = identifier
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data or {})


class _Reference:
    def __init__(self, database, collection, identifier):
        self.database = database
        self.collection = collection
        self.identifier = identifier
        self.id = identifier


class _Collection:
    def __init__(self, database, name):
        self.database = database
        self.name = name

    def document(self, identifier=None):
        if identifier is None:
            self.database._auto_ids[self.name] = (
                self.database._auto_ids.get(self.name, 0) + 1
            )
            identifier = f"auto_{self.database._auto_ids[self.name]}"
        return _Reference(self.database, self.name, identifier)

    def where(self, field, operator, value):
        return _Query(self.database, self.name, [(field, operator, value)])


class _Query:
    def __init__(self, database, collection, filters):
        self.database = database
        self.collection = collection
        self.filters = filters


class _Transaction:
    def __init__(self, database):
        self.database = database

    def get(self, reference):
        if isinstance(reference, _Query):
            return iter([
                _Snapshot(data, identifier)
                for (collection, identifier), data in self.database.rows.items()
                if collection == reference.collection and all(
                    data.get(field) == value
                    for field, operator, value in reference.filters
                    if operator == "=="
                )
            ])
        return _Snapshot(
            self.database.rows.get((reference.collection, reference.identifier)),
            reference.identifier,
        )

    def update(self, reference, values):
        self.database.rows[(reference.collection, reference.identifier)].update(values)

    def set(self, reference, values, **_kwargs):
        key = (reference.collection, reference.identifier)
        if _kwargs.get("merge"):
            self.database.rows.setdefault(key, {}).update(values)
        else:
            self.database.rows[key] = dict(values)

    def create(self, reference, values):
        key = (reference.collection, reference.identifier)
        if key in self.database.rows:
            raise RuntimeError("already exists")
        self.database.rows[key] = dict(values)

    def delete(self, reference):
        key = (reference.collection, reference.identifier)
        if key in self.database.rows:
            del self.database.rows[key]


class _Database:
    def __init__(self, rows):
        self.rows = rows
        self._auto_ids = {}

    def collection(self, name):
        return _Collection(self, name)

    def transaction(self):
        return _Transaction(self)


def _completed_outcome(logical_inference_id="run-id", revision=1):
    return ForumOutcome(
        public_state=FORUM_PUBLIC_STATE_NONE,
        private={
            "state": "completed", "label": "sufficient_reasoning",
            "revision": revision, "logicalInferenceId": logical_inference_id,
        },
        run_bindings={},
    )


def _linked_source(question_id="bank_q1", version="v1"):
    return {
        ("questions", question_id): {
            "questionId": question_id,
            "questionText": "Which numeral shows twenty thousand and four?",
            "questionTextBm": "Angka manakah menunjukkan dua puluh ribu empat?",
            "options": ["20 004", "24 000", "20 400", "20 040"],
            "optionsBm": ["20 004", "24 000", "20 400", "20 040"],
            "contentVersion": version,
            "isActive": True,
        },
        ("questionAnswerKeys", question_id): {
            "questionId": question_id,
            "contentVersion": version,
            "isActive": True,
            "answerIndex": 0,
        },
    }


class ForumRuntimeTests(unittest.TestCase):
    def test_delayed_counter_repairs_origin_week_without_regressing_current_projection(self):
        old = datetime(2026, 7, 27, tzinfo=timezone.utc)
        current = datetime(2026, 8, 3, tzinfo=timezone.utc)
        database = _Database({})
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            gateway._record_participation(
                event_id="answer:new", student_id="student-a",
                field="answersSubmittedCount", occurred_at=current,
            )
            gateway._record_participation(
                event_id="answer:old", student_id="student-a",
                field="answersSubmittedCount", occurred_at=old,
            )

        current_summary = database.rows[("forumParticipationSummaries", "student-a")]
        old_week = database.rows[(
            "forumParticipationWeeklySummaries", "student-a_2026-07-27",
        )]
        self.assertEqual(malaysia_week_start(current), current_summary["weekStart"])
        self.assertEqual(1, current_summary["answersSubmittedCount"])
        self.assertEqual(1, old_week["answersSubmittedCount"])

    def test_out_of_order_same_week_event_keeps_latest_participation_timestamp(self):
        later = datetime(2026, 8, 3, 10, tzinfo=timezone.utc)
        earlier = datetime(2026, 8, 3, 9, tzinfo=timezone.utc)
        database = _Database({})
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            gateway._record_participation(
                event_id="answer:later", student_id="student-a",
                field="answersSubmittedCount", occurred_at=later,
            )
            gateway._record_participation(
                event_id="question:earlier", student_id="student-a",
                field="questionsPostedCount", occurred_at=earlier,
            )

        weekly = database.rows[(
            "forumParticipationWeeklySummaries", "student-a_2026-08-03",
        )]
        current = database.rows[("forumParticipationSummaries", "student-a")]
        self.assertEqual(later, weekly["lastParticipationAt"])
        self.assertEqual(later, current["lastParticipationAt"])

    def test_duplicate_helpful_repairs_using_the_action_original_timestamp(self):
        original = datetime(2026, 7, 27, tzinfo=timezone.utc)
        retry = datetime(2026, 8, 3, tzinfo=timezone.utc)
        database = _Database({
            ("forumAnswers", "a1"): {"authorId": "student-a"},
            ("forumHelpfulMarks", "a1_student-b"): {
                "answerId": "a1", "studentId": "student-b", "createdAt": original,
            },
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            result = gateway.mark_helpful(
                answer_id="a1", actor_id="student-b", now=retry,
            )

        event = database.rows[("forumParticipationEvents", "helpful:a1:student-b")]
        self.assertTrue(result["alreadyMarked"])
        self.assertEqual(original, event["occurredAt"])

    def test_existing_ledger_event_backfills_weekly_aggregate_once(self):
        occurred_at = datetime(2026, 7, 27, tzinfo=timezone.utc)
        database = _Database({
            ("forumParticipationEvents", "answer:legacy"): {
                "eventId": "answer:legacy", "studentId": "student-a",
                "counter": "answersSubmittedCount", "occurredAt": occurred_at,
                "weekStart": malaysia_week_start(occurred_at),
            },
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            for _ in range(2):
                gateway._record_participation(
                    event_id="answer:legacy", student_id="student-a",
                    field="answersSubmittedCount", occurred_at=occurred_at,
                )

        weekly = database.rows[(
            "forumParticipationWeeklySummaries", "student-a_2026-07-27",
        )]
        self.assertEqual(1, weekly["answersSubmittedCount"])
        self.assertIn(
            ("forumParticipationAggregateClaims", "answer:legacy"), database.rows,
        )

    def test_concurrent_duplicate_claims_run_inference_once(self):
        now = datetime(2026, 8, 3, tzinfo=timezone.utc)
        answer = {
            "authorId": "student-a", "questionId": "q1", "revision": 1,
            "text": "I added the tens and then checked the ones.",
        }
        database = _Database({("forumAnswers", "a1"): dict(answer)})
        gateway = ForumRuntimeGateway(database)

        class ReentrantClassifier:
            model_version = "model-v1"
            calls = 0

            def predict(self, _text):
                self.calls += 1
                if self.calls == 1:
                    self.duplicate_state = gateway.process_answer(
                        "a1", answer, self, event_id="event-duplicate", now=now,
                    )
                return ForumPrediction(SUFFICIENT, 0.9, self.model_version)

        classifier = ReentrantClassifier()
        with patch("forum_runtime.firestore.transactional", lambda function: function):
            state = gateway.process_answer(
                "a1", answer, classifier, event_id="event-first", now=now,
            )

        self.assertEqual("completed", state)
        self.assertEqual("processing", classifier.duplicate_state)
        self.assertEqual(1, classifier.calls)
        self.assertEqual(1, len([
            key for key in database.rows if key[0] == "forumAiRuns"
        ]))

    def test_invalid_answer_is_terminalized_without_retrying_eventarc(self):
        now = datetime(2026, 8, 3, tzinfo=timezone.utc)
        database = _Database({
            ("forumAnswers", "a1"): {
                "authorId": "student-a", "revision": 0, "text": "",
            },
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            self.assertEqual(
                "failed",
                gateway.process_answer(
                    "a1", database.rows[("forumAnswers", "a1")], None,
                    event_id="invalid-event", now=now,
                ),
            )

        job = database.rows[("forumAiJobs", "a1")]
        self.assertEqual("failed", job["state"])
        self.assertEqual("permanent", job["failureType"])

    def test_artifact_hash_changes_logical_inference_identity(self):
        now = datetime(2026, 8, 3, tzinfo=timezone.utc)
        answer = {"authorId": "student-a", "revision": 1, "text": "My checked steps."}
        database = _Database({("forumAnswers", "a1"): dict(answer)})
        gateway = ForumRuntimeGateway(database)

        def classifier(artifact_hash):
            return type("Classifier", (), {
                "model_version": "model-v1",
                "artifact_sha256": artifact_hash,
                "predict": lambda self, _text: ForumPrediction(
                    SUFFICIENT, 0.9, self.model_version,
                ),
            })()

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            self.assertEqual("completed", gateway.process_answer(
                "a1", answer, classifier("artifact-a"), event_id="event-a", now=now,
            ))
            self.assertEqual("completed", gateway.process_answer(
                "a1", answer, classifier("artifact-b"), event_id="event-b", now=now,
            ))

        runs = [key for key in database.rows if key[0] == "forumAiRuns"]
        self.assertEqual(2, len(runs))

    def test_missing_classifier_finishes_with_safe_fallback_once(self):
        now = datetime(2026, 8, 3, tzinfo=timezone.utc)
        answer = {"authorId": "student-a", "revision": 1, "text": "My checked steps."}
        database = _Database({("forumAnswers", "a1"): dict(answer)})
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            self.assertEqual(
                "fallback",
                gateway.process_answer("a1", answer, None, event_id="event-a", now=now),
            )
            self.assertEqual(
                "fallback",
                gateway.process_answer("a1", answer, None, event_id="event-b", now=now),
            )

        self.assertEqual("fallback", database.rows[("forumAiJobs", "a1")]["state"])
        self.assertEqual("fallback", database.rows[("forumAiFeedback", "a1")]["state"])
        self.assertEqual("none", database.rows[("forumAnswers", "a1")]["aiPublicState"])
        self.assertNotIn("message", database.rows[("forumAnswers", "a1")])
        self.assertNotIn("probability", database.rows[("forumAnswers", "a1")])
        runs = [
            (key, value) for key, value in database.rows.items()
            if key[0] == "forumAiRuns"
        ]
        self.assertEqual(1, len(runs))
        run_key, run = runs[0]
        self.assertRegex(run_key[1], r"^[0-9a-f]{64}$")
        self.assertEqual("safe-fallback-v1", run["modelVersion"])
        self.assertEqual("safe-fallback-v1", run["artifactIdentity"])
        self.assertEqual("safe_fallback_only", run["claimLevel"])

    def test_legacy_terminal_job_is_not_reprocessed_after_identity_migration(self):
        now = datetime(2026, 8, 3, tzinfo=timezone.utc)
        answer = {
            "authorId": "student-a", "revision": 1, "text": "My checked steps.",
            "aiFeedback": {"state": "completed", "label": SUFFICIENT},
        }
        database = _Database({
            ("forumAnswers", "a1"): dict(answer),
            ("forumAiJobs", "a1"): {
                "answerId": "a1", "state": "completed", "modelVersion": "model-v1",
            },
        })
        gateway = ForumRuntimeGateway(database)

        class Classifier:
            model_version = "model-v1"
            calls = 0

            def predict(self, _text):
                self.calls += 1
                return ForumPrediction(SUFFICIENT, 0.9, self.model_version)

        classifier = Classifier()
        with patch("forum_runtime.firestore.transactional", lambda function: function):
            state = gateway.process_answer(
                "a1", answer, classifier, event_id="migration-retry", now=now,
            )

        self.assertEqual("completed", state)
        self.assertEqual(0, classifier.calls)
        self.assertFalse(any(key[0] == "forumAiRuns" for key in database.rows))

    def test_expired_lease_is_reclaimed_with_newer_fencing_generation(self):
        now = datetime(2026, 8, 3, tzinfo=timezone.utc)
        answer = {"authorId": "student-a", "revision": 1, "text": "My steps."}
        database = _Database({
            ("forumAnswers", "a1"): dict(answer),
            ("forumAiJobs", "a1"): {
                "state": "processing", "fencingGeneration": 4, "attemptCount": 1,
                "leaseExpiresAt": now - timedelta(seconds=1),
            },
        })
        gateway = ForumRuntimeGateway(database)
        classifier = type("Classifier", (), {
            "model_version": "model-v1",
            "predict": lambda self, text: ForumPrediction(SUFFICIENT, 0.9, self.model_version),
        })()

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            self.assertEqual("completed", gateway.process_answer(
                "a1", answer, classifier, event_id="event-retry", now=now,
            ))

        job = database.rows[("forumAiJobs", "a1")]
        self.assertEqual(5, job["fencingGeneration"])
        self.assertEqual(2, job["attemptCount"])

    def test_old_fencing_generation_cannot_finalize_or_replace_new_revision(self):
        now = datetime(2026, 8, 3, tzinfo=timezone.utc)
        answer = {"authorId": "student-a", "revision": 2, "text": "New reasoning."}
        database = _Database({
            ("forumAnswers", "a1"): dict(answer),
            ("forumAiJobs", "a1"): {
                "state": "processing", "logicalInferenceId": "new-run",
                "fencingGeneration": 2, "revision": 2,
            },
        })
        gateway = ForumRuntimeGateway(database)
        stale = ForumAiClaim(
            answer_id="a1", logical_inference_id="old-run", revision=1,
            text_hash="old-hash", model_version="model-v1",
            artifact_identity="artifact-v1", policy_version="policy-v1",
            fencing_generation=1, attempt_count=1, event_id="old-event",
        )

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            state = gateway._finalize_answer(
                stale, _completed_outcome("old-run", 1), now=now,
            )

        self.assertEqual("superseded", state)
        self.assertNotIn("aiFeedback", database.rows[("forumAnswers", "a1")])
        self.assertEqual("processing", database.rows[("forumAiJobs", "a1")]["state"])
        self.assertEqual("superseded", database.rows[("forumAiRuns", "old-run")]["state"])

    def test_reclaimed_same_identity_lease_lets_only_new_fencing_generation_win(self):
        now = datetime(2026, 8, 3, tzinfo=timezone.utc)
        text = "I regrouped and checked each place value."
        text_hash = _answer_content_hash({"text": text})
        logical_id = "same-logical-run"
        database = _Database({
            ("forumAnswers", "a1"): {
                "authorId": "student-a", "revision": 1, "text": text,
            },
            ("forumAiJobs", "a1"): {
                "state": "processing", "logicalInferenceId": logical_id,
                "fencingGeneration": 2, "revision": 1, "textHash": text_hash,
                "artifactIdentity": "artifact-v1",
            },
        })
        gateway = ForumRuntimeGateway(database)
        old_claim = ForumAiClaim(
            answer_id="a1", logical_inference_id=logical_id, revision=1,
            text_hash=text_hash, model_version="model-v1",
            artifact_identity="artifact-v1", policy_version="policy-v1",
            fencing_generation=1, attempt_count=1, event_id="old-event",
        )
        winning_claim = ForumAiClaim(
            answer_id="a1", logical_inference_id=logical_id, revision=1,
            text_hash=text_hash, model_version="model-v1",
            artifact_identity="artifact-v1", policy_version="policy-v1",
            fencing_generation=2, attempt_count=2, event_id="retry-event",
        )
        prediction = ForumPrediction(SUFFICIENT, 0.9, "model-v1")

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            self.assertEqual(
                "superseded",
                gateway._finalize_answer(
                    old_claim, _completed_outcome(logical_id, 1), now=now,
                ),
            )
            self.assertNotIn(("forumAiRuns", logical_id), database.rows)
            self.assertEqual(
                "completed",
                gateway._finalize_answer(
                    winning_claim, _completed_outcome(logical_id, 1), now=now,
                ),
            )

        self.assertEqual("completed", database.rows[("forumAiRuns", logical_id)]["state"])
        self.assertEqual("completed", database.rows[("forumAiFeedback", "a1")]["state"])

    def test_out_of_order_old_revision_does_not_replace_new_terminal_job_or_feedback(self):
        now = datetime(2026, 8, 3, tzinfo=timezone.utc)
        old = {"authorId": "student-a", "revision": 1, "text": "Old reasoning."}
        current = {"authorId": "student-a", "revision": 2, "text": "New reasoning."}
        database = _Database({("forumAnswers", "a1"): dict(current)})
        gateway = ForumRuntimeGateway(database)
        classifier = type("Classifier", (), {
            "model_version": "model-v1",
            "predict": lambda self, text: ForumPrediction(SUFFICIENT, 0.9, self.model_version),
        })()

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            self.assertEqual("completed", gateway.process_answer(
                "a1", current, classifier, event_id="new", now=now,
            ))
            new_job = dict(database.rows[("forumAiJobs", "a1")])
            new_public = dict(database.rows[("forumAnswers", "a1")])
            new_feedback = dict(database.rows[("forumAiFeedback", "a1")])
            self.assertEqual("superseded", gateway.process_answer(
                "a1", old, classifier, event_id="old", now=now + timedelta(seconds=1),
            ))

        self.assertEqual(new_job, database.rows[("forumAiJobs", "a1")])
        self.assertEqual(new_public, database.rows[("forumAnswers", "a1")])
        self.assertEqual(new_feedback, database.rows[("forumAiFeedback", "a1")])

    def test_immutable_run_repairs_terminal_job_and_feedback_after_partial_failure(self):
        now = datetime(2026, 8, 3, tzinfo=timezone.utc)
        answer = {"authorId": "student-a", "revision": 1, "text": "My reasoning."}
        text_hash = _answer_content_hash(answer)
        logical_id = "winning-run"
        prediction = ForumPrediction(SUFFICIENT, 0.9, "model-v1")
        database = _Database({
            ("forumAnswers", "a1"): dict(answer),
            ("forumAiRuns", logical_id): {
                "answerId": "a1", "logicalInferenceId": logical_id,
                "revision": 1, "textHash": text_hash,
                "state": "completed", "resultState": "completed",
                "prediction": {
                    "label": prediction.label, "probability": prediction.probability,
                    "model_version": prediction.model_version,
                    "calibration_state": prediction.calibration_state,
                },
            },
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            state = gateway._claim_answer(
                answer_id="a1", logical_inference_id=logical_id, revision=1,
                text_hash=text_hash, model_version="model-v1",
                artifact_identity="artifact-v1", event_id="retry", now=now,
            )

        self.assertEqual("completed", state)
        self.assertEqual("completed", database.rows[("forumAiJobs", "a1")]["state"])
        self.assertEqual("completed", database.rows[("forumAiFeedback", "a1")]["state"])

    def test_transient_failure_is_bounded_and_permanent_failure_terminates(self):
        now = datetime(2026, 8, 3, tzinfo=timezone.utc)
        answer = {"authorId": "student-a", "revision": 1, "text": "My steps."}

        class TransientClassifier:
            model_version = "model-v1"
            def predict(self, _text):
                raise ConnectionError("temporary")

        database = _Database({("forumAnswers", "a1"): dict(answer)})
        gateway = ForumRuntimeGateway(database)
        with patch("forum_runtime.firestore.transactional", lambda function: function):
            for attempt in range(2):
                with self.assertRaises(ConnectionError):
                    gateway.process_answer(
                        "a1", answer, TransientClassifier(),
                        event_id=f"event-{attempt}", now=now + timedelta(minutes=attempt * 6),
                    )
            state = gateway.process_answer(
                "a1", answer, TransientClassifier(), event_id="event-3",
                now=now + timedelta(minutes=12),
            )
        self.assertEqual("failed", state)
        self.assertEqual("attempts_exhausted", database.rows[("forumAiJobs", "a1")]["failureType"])
        self.assertEqual("fallback", database.rows[("forumAiFeedback", "a1")]["state"])
        self.assertEqual("none", database.rows[("forumAnswers", "a1")]["aiPublicState"])

        database = _Database({("forumAnswers", "a2"): dict(answer)})
        gateway = ForumRuntimeGateway(database)
        permanent = type("Classifier", (), {
            "model_version": "model-v1",
            "predict": lambda self, _text: (_ for _ in ()).throw(
                ForumRuntimeError("failed-precondition", "invalid artifact")
            ),
        })()
        with patch("forum_runtime.firestore.transactional", lambda function: function):
            self.assertEqual("failed", gateway.process_answer(
                "a2", answer, permanent, event_id="event-p", now=now,
            ))
        self.assertEqual("permanent", database.rows[("forumAiJobs", "a2")]["failureType"])
        self.assertEqual("fallback", database.rows[("forumAiFeedback", "a2")]["state"])
        self.assertEqual("none", database.rows[("forumAnswers", "a2")]["aiPublicState"])
    def test_reports_are_server_owned_deterministic_and_preserve_review_fields(self):
        now = datetime(2026, 8, 1, tzinfo=timezone.utc)
        later = datetime(2026, 8, 1, 1, tzinfo=timezone.utc)
        database = _Database({
            ("forumAnswers", "a1"): {
                "questionId": "q1", "authorId": "student-a",
            },
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            first = gateway.report_content(
                target_type="answer",
                target_id="a1",
                reason="This needs a review.",
                actor_id="student-b",
                now=now,
            )
            database.rows[("forumReports", "student-b_answer_a1")]["reviewState"] = "pending"
            duplicate = gateway.report_content(
                target_type="answer",
                target_id="a1",
                reason="Adding clearer context.",
                actor_id="student-b",
                now=later,
            )

        report = database.rows[("forumReports", "student-b_answer_a1")]
        self.assertFalse(first["alreadyReported"])
        self.assertTrue(duplicate["alreadyReported"])
        self.assertEqual(report["createdAt"], now)
        self.assertEqual(report["updatedAt"], later)
        self.assertEqual(report["reviewState"], "pending")

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            with self.assertRaisesRegex(ForumRuntimeError, "own content"):
                gateway.report_content(
                    target_type="answer", target_id="a1", reason="Invalid self report",
                    actor_id="student-a", now=now,
                )
            with self.assertRaisesRegex(ForumRuntimeError, "not found"):
                gateway.report_content(
                    target_type="question", target_id="missing", reason="Missing target",
                    actor_id="student-b", now=now,
                )
            with self.assertRaisesRegex(ForumRuntimeError, "document ID"):
                gateway.report_content(
                    target_type="answer", target_id="nested/a1", reason="Invalid target",
                    actor_id="student-b", now=now,
                )

    def test_only_one_answer_can_be_accepted_for_a_question(self):
        now = datetime(2026, 8, 1, tzinfo=timezone.utc)
        database = _Database({
            ("forumQuestions", "q1"): {"authorId": "question-author"},
            ("forumAnswers", "a1"): {
                "questionId": "q1", "authorId": "student-a",
            },
            ("forumAnswers", "a2"): {
                "questionId": "q1", "authorId": "student-b",
            },
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function), patch.object(
            gateway, "_record_participation"
        ):
            first = gateway.accept_answer(
                answer_id="a1", actor_id="question-author", now=now,
            )
            duplicate = gateway.accept_answer(
                answer_id="a1", actor_id="question-author", now=now,
            )
            with self.assertRaisesRegex(ForumRuntimeError, "already has an accepted answer"):
                gateway.accept_answer(
                    answer_id="a2", actor_id="question-author", now=now,
                )

        self.assertFalse(first["alreadyAccepted"])
        self.assertTrue(duplicate["alreadyAccepted"])
        self.assertEqual(
            database.rows[("forumQuestions", "q1")]["acceptedAnswerId"], "a1",
        )

    def test_duplicate_acceptance_repairs_the_original_week_only(self):
        original = datetime(2026, 7, 27, tzinfo=timezone.utc)
        retry = datetime(2026, 8, 3, tzinfo=timezone.utc)
        database = _Database({
            ("forumQuestions", "q1"): {
                "authorId": "question-author", "acceptedAnswerId": "a1",
                "acceptedAt": original,
            },
            ("forumAnswers", "a1"): {
                "questionId": "q1", "authorId": "student-a",
                "acceptedAt": original, "acceptedBy": "question-author",
            },
            ("forumParticipationSummaries", "student-a"): {
                "studentId": "student-a", "weekStart": malaysia_week_start(retry),
                "questionsPostedCount": 0, "answersSubmittedCount": 1,
                "helpfulReceivedCount": 0, "acceptedAnswersCount": 0,
                "lastParticipationAt": retry,
            },
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            result = gateway.accept_answer(
                answer_id="a1", actor_id="question-author", now=retry,
            )

        event = database.rows[("forumParticipationEvents", "accept:a1")]
        historical = database.rows[(
            "forumParticipationWeeklySummaries", "student-a_2026-07-27",
        )]
        current = database.rows[("forumParticipationSummaries", "student-a")]
        self.assertTrue(result["alreadyAccepted"])
        self.assertEqual(original, event["occurredAt"])
        self.assertEqual(1, historical["acceptedAnswersCount"])
        self.assertEqual(0, current["acceptedAnswersCount"])

    def test_legacy_answer_acceptance_blocks_a_second_answer(self):
        now = datetime(2026, 8, 1, tzinfo=timezone.utc)
        database = _Database({
            ("forumQuestions", "q1"): {"authorId": "question-author"},
            ("forumAnswers", "a1"): {
                "questionId": "q1", "authorId": "student-a", "acceptedAt": now,
            },
            ("forumAnswers", "a2"): {
                "questionId": "q1", "authorId": "student-b",
            },
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function), patch.object(
            gateway, "_record_participation"
        ):
            with self.assertRaisesRegex(ForumRuntimeError, "already has an accepted answer"):
                gateway.accept_answer(
                    answer_id="a2", actor_id="question-author", now=now,
                )
            duplicate = gateway.accept_answer(
                answer_id="a1", actor_id="question-author", now=now,
            )

        self.assertTrue(duplicate["alreadyAccepted"])
        self.assertEqual(
            database.rows[("forumQuestions", "q1")]["acceptedAnswerId"], "a1",
        )

    def test_supportive_feedback_is_advisory_and_has_an_uncertain_path(self):
        self.assertIn("method", feedback_for(SUFFICIENT))
        self.assertIn("steps", feedback_for(REVISION))
        self.assertIn("saved", feedback_for(UNCERTAIN))

    def test_event_week_is_stable_when_processing_happens_later(self):
        event_time = datetime(2026, 7, 26, 17, tzinfo=timezone.utc)
        self.assertEqual("2026-07-27", malaysia_week_start(event_time).date().isoformat())

    def test_transaction_read_accepts_the_current_sdk_iterator_shape(self):
        snapshot = type("Snapshot", (), {"exists": True})()
        transaction = type("Transaction", (), {"get": lambda self, _: iter([snapshot])})()
        self.assertIs(snapshot, _transaction_snapshot(transaction, object()))

    def test_transaction_query_read_accepts_iterator_and_snapshot_shapes(self):
        from forum_runtime import _transaction_snapshots

        first = type("Snapshot", (), {"exists": True})()
        second = type("Snapshot", (), {"exists": True})()
        iterator_transaction = type(
            "Transaction", (), {"get": lambda self, _: iter([first, second])}
        )()
        snapshot_transaction = type(
            "Transaction", (), {"get": lambda self, _: first}
        )()

        self.assertEqual([first, second], _transaction_snapshots(iterator_transaction, object()))
        self.assertEqual([first], _transaction_snapshots(snapshot_transaction, object()))

    def test_model_loader_rejects_an_artifact_that_does_not_match_its_manifest(self):
        from logic_oasis_ai.forum_ai.classifier import REVISION, SUFFICIENT, train_classifier
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "model.joblib"
            manifest = Path(directory) / "manifest.json"
            train_classifier([
                ("I used a number line to check.", SUFFICIENT),
                ("I added groups and checked.", SUFFICIENT),
                ("The answer is twelve.", REVISION),
                ("It is twelve.", REVISION),
            ]).save(artifact)
            manifest.write_text(json.dumps({"artifactSha256": "wrong", "modelVersion": "forum-explanation-nb-v1"}))
            self.assertIsNone(load_forum_classifier(artifact, manifest))

    def test_fixture_artifact_is_emulator_only(self):
        from logic_oasis_ai.forum_ai.classifier import REVISION, SUFFICIENT, train_classifier
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "model.joblib"
            manifest = Path(directory) / "manifest.json"
            classifier = train_classifier([
                ("I used a number line to check.", SUFFICIENT),
                ("I added groups and checked.", SUFFICIENT),
                ("The answer is twelve.", REVISION),
                ("It is twelve.", REVISION),
            ])
            classifier.save(artifact)
            manifest.write_text(json.dumps({"artifactSha256": sha256(artifact.read_bytes()).hexdigest(), "modelVersion": classifier.model_version, "evidenceState": "emulator_fixture_only"}))
            previous = os.environ.pop("FUNCTIONS_EMULATOR", None)
            try:
                self.assertIsNone(load_forum_classifier(artifact, manifest))
                os.environ["FUNCTIONS_EMULATOR"] = "true"
                self.assertIsNotNone(load_forum_classifier(artifact, manifest))
            finally:
                if previous is not None:
                    os.environ["FUNCTIONS_EMULATOR"] = previous
                else:
                    os.environ.pop("FUNCTIONS_EMULATOR", None)

    def test_controlled_release_loads_only_in_controlled_mode(self):
        release_manifest = json.loads(
            (ROOT / "functions/forum_model_manifest.json").read_text(encoding="utf-8")
        )
        revision = release_manifest["codeRevision"]
        controlled = {
            "FORUM_MODEL_EVIDENCE_MODE": "controlled_demo",
            "FORUM_RUNTIME_CODE_REVISION": revision,
        }
        with patch.dict(os.environ, controlled, clear=False):
            self.assertIsNotNone(
                load_forum_bundle(registry_documents=[release_manifest])
            )
        with self.assertLogs("forum_runtime", level="WARNING") as logs, patch.dict(
            os.environ,
            {**controlled, "FORUM_MODEL_EVIDENCE_MODE": "real_evaluated_only"},
            clear=False,
        ):
            self.assertIsNone(
                load_forum_bundle(registry_documents=[release_manifest])
            )
        rendered = " ".join(logs.output)
        self.assertIn("mode_or_registry_incompatible", rendered)
        self.assertNotIn("learner", rendered)

    def test_committed_v2_bundle_loads_and_legacy_v1_loader_is_superseded(self):
        release = json.loads(
            (ROOT / "functions/forum_model_manifest.json").read_text(encoding="utf-8")
        )
        with patch.dict(os.environ, {
            "FORUM_MODEL_EVIDENCE_MODE": "controlled_demo",
            "FORUM_RUNTIME_CODE_REVISION": release["codeRevision"],
        }, clear=False):
            bundle = load_forum_bundle(registry_documents=[release])
        self.assertIsNotNone(bundle)
        self.assertEqual(
            FORUM_RELEVANCE_MODEL_VERSION, bundle.relevance.model_version,
        )
        self.assertEqual(release["claimLevel"], bundle.claim_level)
        # The legacy single-component loader is superseded by the v2 bundle.
        self.assertIsNone(load_forum_classifier(registry_documents=[release]))

    def test_zero_or_multiple_active_compatible_releases_fail_closed(self):
        release = json.loads(
            (ROOT / "functions/forum_model_manifest.json").read_text(encoding="utf-8")
        )
        env = {
            "FORUM_MODEL_EVIDENCE_MODE": "controlled_demo",
            "FORUM_RUNTIME_CODE_REVISION": release["codeRevision"],
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertIsNone(load_forum_bundle(registry_documents=[]))
            self.assertIsNone(
                load_forum_bundle(registry_documents=[release, release])
            )

    def test_demo_student_answer_reaches_genuine_nb_once_without_corpus_or_text_log(self):
        release = json.loads(
            (ROOT / "functions/forum_model_manifest.json").read_text(encoding="utf-8")
        )
        with patch.dict(os.environ, {
            "FORUM_MODEL_EVIDENCE_MODE": "controlled_demo",
            "FORUM_RUNTIME_CODE_REVISION": release["codeRevision"],
        }, clear=False):
            bundle = load_forum_bundle(registry_documents=[release])
        self.assertIsNotNone(bundle)
        self.assertEqual(
            "MultinomialNB",
            type(bundle.reasoning.pipeline.named_steps["classifier"]).__name__,
        )
        answer = {
            "authorId": "u10-demo-student", "questionId": "u10-demo-question",
            "revision": 1,
            "text": "I regrouped the tens first, subtracted each place, and checked by adding back.",
        }
        database = _Database({("forumAnswers", "u10-demo-answer"): dict(answer)})
        with patch("forum_runtime.firestore.transactional", lambda function: function):
            state = ForumRuntimeGateway(database).process_answer(
                "u10-demo-answer", answer, bundle,
                event_id="u10-demo-event", now=datetime(2026, 8, 9, tzinfo=timezone.utc),
            )
        self.assertEqual("completed", state)
        self.assertEqual(1, sum(key[0] == "forumAiJobs" for key in database.rows))
        self.assertEqual(1, sum(key[0] == "forumAiRuns" for key in database.rows))
        run = next(
            value for key, value in database.rows.items() if key[0] == "forumAiRuns"
        )
        self.assertEqual("controlled_demonstration_only", run["claimLevel"])
        self.assertEqual(release["reasoningArtifactSha256"], run["artifactIdentity"])
        self.assertEqual(
            release["relevanceArtifactSha256"], run["relevanceArtifactIdentity"],
        )
        self.assertEqual("not_applicable", run["composite"]["correctness"])
        ai_records = {
            str(key): value for key, value in database.rows.items()
            if key[0] in {"forumAiJobs", "forumAiRuns"}
        }
        self.assertNotIn(answer["text"], json.dumps(ai_records, default=str))
        self.assertFalse(any("training" in key[0].casefold() or "dataset" in key[0].casefold() for key in database.rows))

    def test_committed_v2_bundle_verifies_a_correct_linked_answer(self):
        release = json.loads(
            (ROOT / "functions/forum_model_manifest.json").read_text(encoding="utf-8")
        )
        with patch.dict(os.environ, {
            "FORUM_MODEL_EVIDENCE_MODE": "controlled_demo",
            "FORUM_RUNTIME_CODE_REVISION": release["codeRevision"],
        }, clear=False):
            bundle = load_forum_bundle(registry_documents=[release])
        self.assertIsNotNone(bundle)
        database = _Database({
            ("forumQuestions", "linked_bank_q1_v1"): {
                "mode": "linked", "sourceQuestionId": "bank_q1",
                "sourceContentVersion": "v1",
                "promptSnapshot": {
                    "questionText": "What is 46 + 27? Show your working.",
                },
            },
            ("questionAnswerKeys", "bank_q1"): {
                "questionId": "bank_q1", "contentVersion": "v1",
                "isActive": True, "answerIndex": 2,
            },
            ("forumAnswers", "linked-a1"): {
                "questionId": "linked_bank_q1_v1", "authorId": "student-a",
                "mode": "linked", "selectedOption": 2, "revision": 1,
                "explanation": (
                    "I regrouped the ones into one ten and added the tens, "
                    "then checked by subtraction."
                ),
            },
        })
        with patch("forum_runtime.firestore.transactional", lambda function: function):
            state = ForumRuntimeGateway(database).process_answer(
                "linked-a1", database.rows[("forumAnswers", "linked-a1")],
                bundle, event_id="linked-event",
                now=datetime(2026, 8, 13, 9, 0, tzinfo=timezone.utc),
            )
        self.assertEqual("completed", state)
        self.assertEqual(
            FORUM_PUBLIC_STATE_VERIFIED,
            database.rows[("forumAnswers", "linked-a1")]["aiPublicState"],
        )
        self.assertEqual(
            "correct",
            database.rows[("forumAiFeedback", "linked-a1")]["correctness"],
        )
        run = next(
            value for key, value in database.rows.items() if key[0] == "forumAiRuns"
        )
        self.assertEqual("verified", run["composite"]["publicState"])
        self.assertEqual("bank_q1", run["sourceQuestionId"])


class ForumLinkedDiscussionTests(unittest.TestCase):
    NOW = datetime(2026, 8, 11, 9, 0, tzinfo=timezone.utc)

    def _gateway(self, rows):
        return ForumRuntimeGateway(_Database(rows))

    def test_open_or_create_linked_discussion_creates_one_canonical_thread(self):
        now = self.NOW
        database = _Database(_linked_source())
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            first = gateway.open_or_create_linked_discussion(
                question_id="bank_q1", actor_id="student-a", now=now,
            )
            second = gateway.open_or_create_linked_discussion(
                question_id="bank_q1", actor_id="student-b", now=now,
            )

        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["discussionId"], second["discussionId"])
        self.assertEqual("linked_bank_q1_v1", first["discussionId"])
        document = database.rows[("forumQuestions", "linked_bank_q1_v1")]
        self.assertEqual("linked", document["mode"])
        self.assertEqual("bank_q1", document["sourceQuestionId"])
        self.assertEqual("v1", document["sourceContentVersion"])
        self.assertEqual(4, len(document["promptSnapshot"]["options"]))
        self.assertEqual(4, len(document["promptSnapshot"]["optionsBm"]))
        self.assertNotIn("answerIndex", json.dumps(document, default=str))
        self.assertNotIn("answerIndex", document["promptSnapshot"])
        self.assertEqual("absent", document.get("authorId", "absent"))
        self.assertEqual(1, sum(
            key[0] == "forumQuestions" for key in database.rows
        ))

    def test_open_or_create_rejects_inactive_or_mismatched_sources(self):
        now = self.NOW
        mutations = (
            (("questions", "bank_q1"), {"isActive": False}, "not active"),
            (("questionAnswerKeys", "bank_q1"), {"isActive": False}, "incompatible"),
            (("questionAnswerKeys", "bank_q1"), {"contentVersion": "v2"}, "incompatible"),
            (("questionAnswerKeys", "bank_q1"), {"answerIndex": 4}, "invalid options"),
            (("questionAnswerKeys", "bank_q1"), {"answerIndex": True}, "invalid options"),
            (("questions", "bank_q1"), {"options": ["A", "B", "C"]}, "invalid options"),
            (("questions", "bank_q1"), {"optionsBm": ["A", "B", "C", "D", "E"]}, "invalid options"),
            (("questions", "bank_q1"), {"questionTextBm": ""}, "Bahasa Melayu"),
        )
        for key, mutation, expected in mutations:
            with self.subTest(key=key, mutation=mutation):
                source = _linked_source()
                source[key].update(mutation)
                gateway = self._gateway(source)
                with patch("forum_runtime.firestore.transactional", lambda function: function):
                    with self.assertRaisesRegex(ForumRuntimeError, expected):
                        gateway.open_or_create_linked_discussion(
                            question_id="bank_q1", actor_id="student-a", now=now,
                        )
                self.assertNotIn(("forumQuestions", "linked_bank_q1_v1"), gateway.database.rows)

    def test_open_or_create_fails_closed_on_deterministic_id_collision(self):
        now = self.NOW
        rows = _linked_source()
        rows[("forumQuestions", "linked_bank_q1_v1")] = {
            "authorId": "student-x", "title": "A free-form question",
            "text": "This doc already occupies the canonical linked ID.",
        }
        gateway = self._gateway(rows)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            with self.assertRaisesRegex(ForumRuntimeError, "collides"):
                gateway.open_or_create_linked_discussion(
                    question_id="bank_q1", actor_id="student-a", now=now,
                )

    def test_missing_question_or_key_fails_closed(self):
        now = self.NOW
        for rows in ({}, {("questions", "bank_q1"): _linked_source()["questions", "bank_q1"]}):
            gateway = self._gateway(rows)
            with patch("forum_runtime.firestore.transactional", lambda function: function):
                with self.assertRaises(ForumRuntimeError):
                    gateway.open_or_create_linked_discussion(
                        question_id="bank_q1", actor_id="student-a", now=now,
                    )

    def test_submit_linked_answer_stores_only_server_owned_structured_fields(self):
        now = self.NOW
        database = _Database({
            ("forumQuestions", "linked_bank_q1_v1"): {
                "mode": "linked", "sourceQuestionId": "bank_q1",
                "sourceContentVersion": "v1",
            },
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            result = gateway.submit_linked_answer(
                discussion_id="linked_bank_q1_v1", selected_option=2,
                explanation="I added the thousands and compared the digits.",
                actor_id="student-a", now=now,
            )

        self.assertEqual("linked_bank_q1_v1", result["questionId"])
        self.assertEqual(1, result["revision"])
        answer = next(value for key, value in database.rows.items() if key[0] == "forumAnswers")
        self.assertEqual("linked", answer["mode"])
        self.assertEqual(2, answer["selectedOption"])
        self.assertEqual("student-a", answer["authorId"])
        self.assertEqual("none", answer["aiPublicState"])
        self.assertEqual(1, answer["revision"])
        self.assertNotIn("text", answer)
        self.assertNotIn("sourceQuestionId", answer)

    def test_submit_linked_answer_validates_option_explanation_and_membership(self):
        now = self.NOW
        database = _Database({
            ("forumQuestions", "linked_bank_q1_v1"): {"mode": "linked"},
            ("forumQuestions", "free_q1"): {"mode": "free_form", "authorId": "student-a"},
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            for option in (-1, 4, True, "2", None):
                with self.subTest(option=option):
                    with self.assertRaisesRegex(ForumRuntimeError, "option"):
                        gateway.submit_linked_answer(
                            discussion_id="linked_bank_q1_v1", selected_option=option,
                            explanation="I compared the digits carefully.", actor_id="student-a",
                            now=now,
                        )
            for explanation in ("", "Short", "x" * 4001):
                with self.subTest(explanation=explanation):
                    with self.assertRaisesRegex(ForumRuntimeError, "explanation"):
                        gateway.submit_linked_answer(
                            discussion_id="linked_bank_q1_v1", selected_option=1,
                            explanation=explanation, actor_id="student-a", now=now,
                        )
            with self.assertRaisesRegex(ForumRuntimeError, "not found"):
                gateway.submit_linked_answer(
                    discussion_id="missing", selected_option=1,
                    explanation="I compared the digits carefully.", actor_id="student-a",
                    now=now,
                )
            with self.assertRaisesRegex(ForumRuntimeError, "structured"):
                gateway.submit_linked_answer(
                    discussion_id="free_q1", selected_option=1,
                    explanation="I compared the digits carefully.", actor_id="student-a",
                    now=now,
                )

    def test_edit_linked_answer_increments_revision_and_clears_derived_state(self):
        now = self.NOW
        database = _Database({
            ("forumQuestions", "linked_bank_q1_v1"): {"mode": "linked"},
            ("forumAnswers", "a1"): {
                "questionId": "linked_bank_q1_v1", "authorId": "student-a",
                "mode": "linked", "selectedOption": 0, "explanation": "Old explanation.",
                "revision": 2, "aiPublicState": "verified", "aiRunId": "run-1",
                "aiRevision": 2,
            },
            ("forumAiFeedback", "a1"): {
                "state": "completed", "label": "sufficient", "revision": 2,
            },
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            result = gateway.edit_linked_answer(
                answer_id="a1", selected_option=1,
                explanation="I checked by adding back the group.", actor_id="student-a",
                now=now,
            )

        self.assertEqual(3, result["revision"])
        answer = database.rows[("forumAnswers", "a1")]
        self.assertEqual(3, answer["revision"])
        self.assertEqual(1, answer["selectedOption"])
        self.assertEqual("none", answer["aiPublicState"])
        self.assertIsNone(answer["aiRunId"])
        self.assertIsNone(answer["aiRevision"])
        feedback = database.rows[("forumAiFeedback", "a1")]
        self.assertEqual("pending", feedback["state"])
        self.assertEqual(3, feedback["revision"])

    def test_edit_linked_answer_denies_foreign_accepted_missing_and_free_form(self):
        now = self.NOW
        base_answer = {
            "questionId": "linked_bank_q1_v1", "authorId": "student-a",
            "mode": "linked", "selectedOption": 0, "explanation": "I checked by adding back.",
            "revision": 1,
        }
        database = _Database({
            ("forumQuestions", "linked_bank_q1_v1"): {"mode": "linked"},
            ("forumAnswers", "a1"): dict(base_answer),
            ("forumAnswers", "accepted"): {**base_answer, "acceptedAt": now},
            ("forumAnswers", "free"): {
                "questionId": "free_q1", "authorId": "student-a", "text": "A free-form answer.",
                "revision": 1,
            },
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            with self.assertRaisesRegex(ForumRuntimeError, "author"):
                gateway.edit_linked_answer(
                    answer_id="a1", selected_option=1,
                    explanation="A different explanation for the peer.", actor_id="student-b",
                    now=now,
                )
            with self.assertRaisesRegex(ForumRuntimeError, "accepted answer"):
                gateway.edit_linked_answer(
                    answer_id="accepted", selected_option=1,
                    explanation="A different explanation for the peer.", actor_id="student-a",
                    now=now,
                )
            with self.assertRaisesRegex(ForumRuntimeError, "not found"):
                gateway.edit_linked_answer(
                    answer_id="missing", selected_option=1,
                    explanation="A different explanation for the peer.", actor_id="student-a",
                    now=now,
                )
            with self.assertRaisesRegex(ForumRuntimeError, "structured"):
                gateway.edit_linked_answer(
                    answer_id="free", selected_option=1,
                    explanation="A different explanation for the peer.", actor_id="student-a",
                    now=now,
                )

    def test_linked_question_creation_does_not_record_student_participation(self):
        now = self.NOW
        database = _Database({})
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            gateway.record_question("linked_bank_q1_v1", {"mode": "linked", "createdAt": now})

        self.assertEqual({}, database.rows)

    def test_open_or_create_linked_discussion_records_questions_posted_once_per_student(self):
        now = self.NOW
        database = _Database(_linked_source())
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            gateway.open_or_create_linked_discussion(
                question_id="bank_q1", actor_id="student-a", now=now,
            )
            gateway.open_or_create_linked_discussion(
                question_id="bank_q1", actor_id="student-a", now=now,
            )
            gateway.open_or_create_linked_discussion(
                question_id="bank_q1", actor_id="student-b", now=now,
            )

        self.assertEqual(
            1,
            database.rows[("forumParticipationSummaries", "student-a")][
                "questionsPostedCount"
            ],
        )
        self.assertEqual(
            1,
            database.rows[("forumParticipationSummaries", "student-b")][
                "questionsPostedCount"
            ],
        )

    def test_linked_discussions_have_no_accept_owner_and_cannot_be_reported(self):
        now = self.NOW
        database = _Database({
            ("forumQuestions", "linked_bank_q1_v1"): {"mode": "linked"},
            ("forumAnswers", "a1"): {
                "questionId": "linked_bank_q1_v1", "authorId": "student-a", "mode": "linked",
            },
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function), patch.object(
            gateway, "_record_participation"
        ):
            with self.assertRaisesRegex(ForumRuntimeError, "no question owner"):
                gateway.accept_answer(
                    answer_id="a1", actor_id="student-a", now=now,
                )
            with self.assertRaisesRegex(ForumRuntimeError, "cannot be reported"):
                gateway.report_content(
                    target_type="question", target_id="linked_bank_q1_v1",
                    reason="This canonical thread is incorrect", actor_id="student-b",
                    now=now,
                )

    def test_linked_answer_processing_uses_explanation_and_keeps_public_doc_clean(self):
        now = self.NOW
        answer = {
            "authorId": "student-a", "questionId": "linked_bank_q1_v1",
            "mode": "linked", "selectedOption": 0, "revision": 1,
            "explanation": "I compared the digits from left to right.",
        }
        database = _Database({("forumAnswers", "a1"): dict(answer)})
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            state = gateway.process_answer(
                "a1", answer, None, event_id="event-a", now=now,
            )

        self.assertEqual("fallback", state)
        public_answer = database.rows[("forumAnswers", "a1")]
        self.assertEqual("none", public_answer["aiPublicState"])
        self.assertNotIn("message", public_answer)
        self.assertNotIn("probability", public_answer)
        self.assertNotIn("modelVersion", public_answer)
        feedback = database.rows[("forumAiFeedback", "a1")]
        self.assertEqual("fallback", feedback["state"])
        self.assertIn("message", feedback)

    def test_completed_processing_writes_private_feedback_and_public_projection(self):
        now = self.NOW
        answer = {"authorId": "student-a", "revision": 1, "text": "My checked steps."}
        database = _Database({("forumAnswers", "a1"): dict(answer)})
        gateway = ForumRuntimeGateway(database)
        classifier = type("Classifier", (), {
            "model_version": "model-v1",
            "predict": lambda self, _text: ForumPrediction(SUFFICIENT, 0.9, "model-v1"),
        })()

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            self.assertEqual("completed", gateway.process_answer(
                "a1", answer, classifier, event_id="event-a", now=now,
            ))

        public_answer = database.rows[("forumAnswers", "a1")]
        self.assertEqual("none", public_answer["aiPublicState"])
        self.assertEqual(1, public_answer["aiRevision"])
        self.assertRegex(public_answer["aiRunId"], r"^[0-9a-f]{64}$")
        for field in ("message", "probability", "modelVersion", "logicalInferenceId", "label"):
            self.assertNotIn(field, public_answer)
        feedback = database.rows[("forumAiFeedback", "a1")]
        self.assertEqual("completed", feedback["state"])
        self.assertEqual(SUFFICIENT, feedback["label"])
        self.assertEqual(0.9, feedback["probability"])
        self.assertEqual(public_answer["aiRunId"], feedback["logicalInferenceId"])


class ForumDeletionTests(unittest.TestCase):
    NOW = datetime(2026, 8, 13, 9, 0, tzinfo=timezone.utc)

    def test_delete_answer_removes_own_answer_and_ai_projections_but_preserves_run(self):
        now = self.NOW
        database = _Database({
            ("forumAnswers", "a1"): {
                "questionId": "q1", "authorId": "student-a", "mode": "free_form",
                "text": "I regrouped the tens and ones.", "revision": 1,
            },
            ("forumQuestions", "q1"): {
                "authorId": "student-b",
                "title": "How do you add 46 and 27?",
                "text": "What is 46 + 27? Show your working.",
            },
            ("forumAiJobs", "a1"): {
                "state": "completed", "modelVersion": "forum-controlled-demo-nb-v1",
            },
            ("forumAiFeedback", "a1"): {"state": "completed", "label": "verified"},
            ("forumAiRuns", "run1"): {"state": "completed", "answerId": "a1"},
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            result = gateway.delete_answer(answer_id="a1", actor_id="student-a")

        self.assertTrue(result["deleted"])
        self.assertNotIn(("forumAnswers", "a1"), database.rows)
        self.assertNotIn(("forumAiJobs", "a1"), database.rows)
        self.assertNotIn(("forumAiFeedback", "a1"), database.rows)
        self.assertIn(("forumAiRuns", "run1"), database.rows)

    def test_delete_answer_denies_foreign_authors_and_missing_answers(self):
        now = self.NOW
        database = _Database({
            ("forumAnswers", "a1"): {"questionId": "q1", "authorId": "student-a"},
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            with self.assertRaisesRegex(ForumRuntimeError, "answer author"):
                gateway.delete_answer(answer_id="a1", actor_id="student-b")
            with self.assertRaisesRegex(ForumRuntimeError, "not found"):
                gateway.delete_answer(answer_id="missing", actor_id="student-a")

        self.assertIn(("forumAnswers", "a1"), database.rows)

    def test_delete_answer_rejects_accepted_answers_and_allows_linked_answers(self):
        now = self.NOW
        database = _Database({
            ("forumAnswers", "accepted"): {
                "questionId": "q1", "authorId": "student-a", "acceptedAt": now,
            },
            ("forumQuestions", "q1"): {
                "authorId": "student-b", "acceptedAnswerId": "accepted",
            },
            ("forumAnswers", "linked-a1"): {
                "questionId": "linked_bank_q1_v1", "authorId": "student-a",
                "mode": "linked", "selectedOption": 2,
                "explanation": "I regrouped the ones and tens.",
            },
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            with self.assertRaisesRegex(ForumRuntimeError, "accepted answer"):
                gateway.delete_answer(answer_id="accepted", actor_id="student-a")
            result = gateway.delete_answer(
                answer_id="linked-a1", actor_id="student-a",
            )

        self.assertTrue(result["deleted"])
        self.assertNotIn(("forumAnswers", "linked-a1"), database.rows)

    def test_delete_question_cascades_answers_and_ai_projections_but_preserves_runs(self):
        now = self.NOW
        database = _Database({
            ("forumQuestions", "q1"): {
                "authorId": "student-a",
                "title": "How do you add 46 and 27?",
                "text": "What is 46 + 27? Show your working.",
            },
            ("forumAnswers", "a1"): {
                "questionId": "q1", "authorId": "student-b", "text": "I regrouped the ones.",
            },
            ("forumAnswers", "a2"): {
                "questionId": "q1", "authorId": "student-c", "text": "I added the tens first.",
            },
            ("forumAiJobs", "a1"): {"state": "completed"},
            ("forumAiJobs", "a2"): {"state": "completed"},
            ("forumAiFeedback", "a1"): {"state": "completed"},
            ("forumAiFeedback", "a2"): {"state": "completed"},
            ("forumAiRuns", "run1"): {"state": "completed", "answerId": "a1"},
            ("forumAiRuns", "run2"): {"state": "completed", "answerId": "a2"},
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            result = gateway.delete_question(question_id="q1", actor_id="student-a")

        self.assertEqual(2, result["deletedAnswerCount"])
        for key in (
            ("forumQuestions", "q1"),
            ("forumAnswers", "a1"),
            ("forumAnswers", "a2"),
            ("forumAiJobs", "a1"),
            ("forumAiJobs", "a2"),
            ("forumAiFeedback", "a1"),
            ("forumAiFeedback", "a2"),
        ):
            self.assertNotIn(key, database.rows)
        self.assertIn(("forumAiRuns", "run1"), database.rows)
        self.assertIn(("forumAiRuns", "run2"), database.rows)

    def test_delete_question_denies_foreign_authors_linked_threads_and_missing(self):
        now = self.NOW
        database = _Database({
            ("forumQuestions", "q1"): {
                "authorId": "student-a",
                "title": "How do you add 46 and 27?",
                "text": "What is 46 + 27?",
            },
            ("forumQuestions", "linked_bank_q1_v1"): {
                "mode": "linked", "sourceQuestionId": "bank_q1",
            },
        })
        gateway = ForumRuntimeGateway(database)

        with patch("forum_runtime.firestore.transactional", lambda function: function):
            with self.assertRaisesRegex(ForumRuntimeError, "question author"):
                gateway.delete_question(question_id="q1", actor_id="student-b")
            with self.assertRaisesRegex(ForumRuntimeError, "linked discussions"):
                gateway.delete_question(
                    question_id="linked_bank_q1_v1", actor_id="student-a",
                )
            with self.assertRaisesRegex(ForumRuntimeError, "not found"):
                gateway.delete_question(question_id="missing", actor_id="student-a")

        self.assertIn(("forumQuestions", "q1"), database.rows)


class ForumCompositeRuntimeTests(unittest.TestCase):
    NOW = datetime(2026, 8, 13, 9, 0, tzinfo=timezone.utc)

    def _bundle(self, reasoning_label=SUFFICIENT, relevance_label="relevant"):
        reasoning = type("Reasoning", (), {
            "model_version": FORUM_REASONING_MODEL_VERSION,
            "artifact_sha256": "a" * 64,
            "predict": lambda self, text: ForumPrediction(
                reasoning_label, 0.9, self.model_version,
            ),
        })()
        relevance = type("Relevance", (), {
            "model_version": FORUM_RELEVANCE_MODEL_VERSION,
            "artifact_sha256": "b" * 64,
            "predict": lambda self, prompt, text: ForumRelevancePrediction(
                relevance_label, 0.9, self.model_version,
            ),
        })()
        return ForumAiBundle(
            reasoning=reasoning,
            relevance=relevance,
            policy={"policyVersion": FORUM_COMPOSITE_POLICY_VERSION},
            release_id="v2-test",
            reasoning_artifact_identity="a" * 64,
            relevance_artifact_identity="b" * 64,
            claim_level=FORUM_CONTROLLED_CLAIM_LEVEL,
        )

    def _linked_database(
        self, *, answer_index=2, selected_option=2, key_active=True,
        key_version="v1", explanation=None,
    ):
        rows = {
            ("forumQuestions", "linked_q1_v1"): {
                "mode": "linked", "sourceQuestionId": "bank_q1",
                "sourceContentVersion": "v1",
                "promptSnapshot": {"questionText": "What is 46 + 27?"},
            },
            ("questionAnswerKeys", "bank_q1"): {
                "questionId": "bank_q1", "contentVersion": key_version,
                "isActive": key_active, "answerIndex": answer_index,
            },
            ("forumAnswers", "a1"): {
                "questionId": "linked_q1_v1", "authorId": "student-a",
                "mode": "linked", "selectedOption": selected_option,
                "explanation": explanation or (
                    "I regrouped the ones and added the tens, then checked "
                    "by subtraction."
                ),
                "revision": 1,
            },
        }
        return _Database(rows)

    def _process(self, database, bundle, *, mode="linked"):
        gateway = ForumRuntimeGateway(database)
        data = database.rows[("forumAnswers", "a1")]
        with patch("forum_runtime.firestore.transactional", lambda function: function):
            return gateway.process_answer(
                "a1", data, bundle, event_id="composite-event", now=self.NOW,
            )

    def test_composite_verified_path_binds_public_state_and_private_guidance(self):
        database = self._linked_database(answer_index=2, selected_option=2)
        state = self._process(database, self._bundle())
        self.assertEqual("completed", state)
        answer = database.rows[("forumAnswers", "a1")]
        self.assertEqual(FORUM_PUBLIC_STATE_VERIFIED, answer["aiPublicState"])
        private = database.rows[("forumAiFeedback", "a1")]
        self.assertEqual("verified", private["label"])
        self.assertEqual("correct", private["correctness"])
        self.assertEqual("relevant", private["relevance"])
        self.assertEqual("sufficient_reasoning", private["reasoning"])
        run = next(value for key, value in database.rows.items() if key[0] == "forumAiRuns")
        self.assertEqual("verified", run["composite"]["publicState"])
        self.assertEqual("v2-test", run["releaseId"])
        self.assertEqual("bank_q1", run["sourceQuestionId"])
        self.assertEqual("v1", run["sourceContentVersion"])
        self.assertEqual(2, run["selectedOption"])
        self.assertEqual(FORUM_COMPOSITE_POLICY_VERSION, run["policyVersion"])

    def test_composite_incorrect_option_has_no_public_negative(self):
        database = self._linked_database(answer_index=2, selected_option=1)
        self._process(database, self._bundle())
        answer = database.rows[("forumAnswers", "a1")]
        self.assertEqual(FORUM_PUBLIC_STATE_NONE, answer["aiPublicState"])
        private = database.rows[("forumAiFeedback", "a1")]
        self.assertEqual("correction_needed", private["label"])
        self.assertEqual("incorrect", private["correctness"])
        self.assertIn("does not match", private["correctnessGuidance"])

    def test_composite_may_be_irrelevant_is_public_with_private_guidance(self):
        database = self._linked_database(answer_index=2, selected_option=2)
        self._process(
            database, self._bundle(reasoning_label=SUFFICIENT, relevance_label="irrelevant"),
        )
        answer = database.rows[("forumAnswers", "a1")]
        self.assertEqual(FORUM_PUBLIC_STATE_MAY_BE_IRRELEVANT, answer["aiPublicState"])
        private = database.rows[("forumAiFeedback", "a1")]
        self.assertEqual("may_be_irrelevant", private["label"])
        self.assertIn("may not address", private["message"])
        self.assertIn("may be irrelevant", private["relevanceGuidance"])

    def test_composite_needs_reasoning_withholds_badge(self):
        database = self._linked_database(answer_index=2, selected_option=2)
        self._process(database, self._bundle(reasoning_label=REVISION))
        answer = database.rows[("forumAnswers", "a1")]
        self.assertEqual(FORUM_PUBLIC_STATE_NONE, answer["aiPublicState"])
        private = database.rows[("forumAiFeedback", "a1")]
        self.assertEqual("needs_reasoning", private["label"])

    def test_missing_or_stale_key_never_verifies(self):
        for kwargs in (
            {"key_active": False},
            {"key_version": "v2"},
            {"answer_index": 9},
        ):
            with self.subTest(kwargs=kwargs):
                database = self._linked_database(**kwargs)
                self._process(database, self._bundle())
                answer = database.rows[("forumAnswers", "a1")]
                self.assertEqual(FORUM_PUBLIC_STATE_NONE, answer["aiPublicState"])
                private = database.rows[("forumAiFeedback", "a1")]
                self.assertEqual("unavailable", private["correctness"])

    def test_free_form_never_verified_but_may_show_irrelevance(self):
        for relevance_label, expected in (
            ("relevant", FORUM_PUBLIC_STATE_NONE),
            ("irrelevant", FORUM_PUBLIC_STATE_MAY_BE_IRRELEVANT),
        ):
            with self.subTest(relevance=relevance_label):
                database = _Database({
                    ("forumAnswers", "a1"): {
                        "questionId": "free_q1", "authorId": "student-a",
                        "text": "I regrouped the ones and checked with subtraction.",
                        "revision": 1,
                    },
                })
                self._process(
                    database, self._bundle(
                        reasoning_label=SUFFICIENT, relevance_label=relevance_label,
                    ),
                    mode="free_form",
                )
                answer = database.rows[("forumAnswers", "a1")]
                self.assertEqual(expected, answer["aiPublicState"])
                private = database.rows[("forumAiFeedback", "a1")]
                self.assertEqual("not_applicable", private["correctness"])

    def test_component_abstention_withholds_public_decisions(self):
        for reasoning_label, relevance_label in (
            (UNCERTAIN, "relevant"),
            (SUFFICIENT, "uncertain"),
            (UNCERTAIN, "uncertain"),
        ):
            with self.subTest(reasoning=reasoning_label, relevance=relevance_label):
                database = self._linked_database(answer_index=2, selected_option=2)
                self._process(
                    database,
                    self._bundle(
                        reasoning_label=reasoning_label,
                        relevance_label=relevance_label,
                    ),
                )
                answer = database.rows[("forumAnswers", "a1")]
                self.assertEqual(FORUM_PUBLIC_STATE_NONE, answer["aiPublicState"])

    def test_public_payload_contains_only_allowlisted_fields(self):
        database = self._linked_database(answer_index=2, selected_option=2)
        self._process(database, self._bundle())
        answer = database.rows[("forumAnswers", "a1")]
        for forbidden in (
            "message", "probability", "correctness", "relevance",
            "reasoning", "answerIndex", "guidance", "policyVersion",
        ):
            self.assertNotIn(forbidden, answer)

    def test_canary_answer_key_is_absent_from_all_written_records(self):
        database = self._linked_database(
            answer_index=2, selected_option=3,
        )
        self._process(database, self._bundle())
        written = {
            str(key): value for key, value in database.rows.items()
            if key[0] in {
                "forumAnswers", "forumAiJobs", "forumAiRuns",
                "forumAiFeedback",
            }
        }
        rendered = json.dumps(written, default=str)
        self.assertNotIn("answerIndex", rendered)

    def test_swapped_option_fences_the_stale_run(self):
        original = self._linked_database(answer_index=2, selected_option=2)
        self._process(original, self._bundle())
        original_run = next(
            key for key in original.rows if key[0] == "forumAiRuns"
        )
        swapped = self._linked_database(answer_index=2, selected_option=1)
        self._process(swapped, self._bundle())
        self.assertNotIn(original_run, swapped.rows)

    def test_v2_bundle_loader_requires_every_binding(self):
        from importlib import metadata

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reasoning_source = ROOT / (
                "ai_pipeline/forum_controlled_demo/generated/"
                "forum_controlled_demo_candidate.joblib"
            )
            relevance_source = ROOT / (
                "ai_pipeline/forum_controlled_demo/generated/"
                "forum_controlled_demo_relevance_candidate.joblib"
            )
            reasoning_path = root / "forum_model.joblib"
            relevance_path = root / "forum_relevance_model.joblib"
            shutil.copyfile(reasoning_source, reasoning_path)
            shutil.copyfile(relevance_source, relevance_path)
            shutil.copyfile(
                ROOT / "functions/forum_runtime.py", root / "forum_runtime.py",
            )
            shutil.copyfile(
                ROOT / "functions/main.py", root / "main.py",
            )
            vendor_root = root / "vendor/logic_oasis_ai/forum_ai"
            vendor_root.mkdir(parents=True)
            vendor_hashes = {}
            for name in ("__init__.py", "classifier.py", "relevance.py"):
                source = ROOT / "functions/vendor/logic_oasis_ai/forum_ai" / name
                shutil.copyfile(source, vendor_root / name)
                vendor_hashes[name] = sha256(source.read_bytes()).hexdigest()
            bundle_manifest = root / "vendor/bundle_manifest.json"
            bundle_manifest.write_text(json.dumps({
                "bundleVersion": "u8-ai-runtime-v1",
                "forumRuntimeBundle": {
                    "bundleSchemaVersion": "forum-runtime-bundle-v1",
                    "files": vendor_hashes,
                },
            }), encoding="utf-8")
            manifest_path = root / "forum_model_manifest.json"
            revision = "0" * 64
            manifest = {
                "manifestSchemaVersion": "forum-model-release-manifest-v2",
                "releaseId": "forum-controlled-demo-nb-v1-release-5",
                "releasedBy": "developer",
                "releasedAt": "2026-08-13T00:00:00Z",
                "lifecycleStatus": "released", "isActive": True,
                "releaseRationale": (
                    "Developer-released FYP1 controlled-demonstration model. "
                    "Not evaluated on real learner forum responses."
                ),
                "supersedesReleaseId": None,
                "trainingDataProvenance": "expert_authored_controlled_demo",
                "evidenceLevel": "controlled_demonstration",
                "releaseScope": "fyp1_forum_controlled_demo",
                "deploymentScope": "controlled_demo",
                "claimLevel": FORUM_CONTROLLED_CLAIM_LEVEL,
                "candidateGateStatus": "passed", "failedGates": [],
                "reasoningModelType": "MultinomialNB",
                "relevanceModelType": "MultinomialNB",
                "reasoningModelVersion": FORUM_REASONING_MODEL_VERSION,
                "relevanceModelVersion": FORUM_RELEVANCE_MODEL_VERSION,
                "reasoningArtifactSha256": sha256(
                    reasoning_path.read_bytes()
                ).hexdigest(),
                "relevanceArtifactSha256": sha256(
                    relevance_path.read_bytes()
                ).hexdigest(),
                "reasoningArtifactSizeBytes": reasoning_path.stat().st_size,
                "relevanceArtifactSizeBytes": relevance_path.stat().st_size,
                "catalogueSha256": "1" * 64,
                "datasetSha256": "2" * 64,
                "datasetManifestSha256": "3" * 64,
                "splitManifestSha256": "4" * 64,
                "rubricSha256": "5" * 64,
                "evaluationReportSha256": "6" * 64,
                "candidateManifestSha256": "7" * 64,
                "bundleManifestSha256": sha256(
                    bundle_manifest.read_bytes()
                ).hexdigest(),
                "dependencyLockSha256": "8" * 64,
                "codeRevision": revision,
                "codeRevisionKind": "sha256_bounded_release_sources_v1",
                "dependencies": {
                    name: metadata.version(name)
                    for name in ("joblib", "numpy", "scikit-learn")
                },
                "semanticReproducibilityStatus": "verified_same_runtime_contract",
                "baselineComparisonResult": "naive_bayes_advantage_demonstrated",
                "compositePolicy": {
                    "policyVersion": FORUM_COMPOSITE_POLICY_VERSION,
                    "correctness": "deterministic_protected_answer_key_v1",
                    "relevancePositiveThreshold": RELEVANCE_POSITIVE_THRESHOLD,
                    "relevanceNegativeThreshold": RELEVANCE_NEGATIVE_THRESHOLD,
                    "reasoningAbstentionThreshold": 0.60,
                    "freeFormNeverVerified": True,
                    "withholdOnAnyAbstention": True,
                    "noPublicNegativeCorrectnessLabel": True,
                },
                "vectorizerContract": {
                    "family": "TfidfVectorizer",
                    "abstentionPolicyVersion": "forum-advisory-policy-v1",
                },
                "relevanceVectorizerContract": {
                    "family": "TfidfVectorizer",
                    "positiveThreshold": RELEVANCE_POSITIVE_THRESHOLD,
                    "negativeThreshold": RELEVANCE_NEGATIVE_THRESHOLD,
                },
                "sourceRuntimeHashes": vendor_hashes,
                "vendorRuntimeHashes": vendor_hashes,
                "deploymentRuntimeHashes": {
                    "forum_runtime.py": sha256(
                        (root / "forum_runtime.py").read_bytes()
                    ).hexdigest(),
                    "main.py": sha256(
                        (root / "main.py").read_bytes()
                    ).hexdigest(),
                },
            }
            manifest_path.write_text(
                json.dumps(manifest), encoding="utf-8",
            )

            env = {
                "FORUM_MODEL_EVIDENCE_MODE": "controlled_demo",
                "FORUM_RUNTIME_CODE_REVISION": revision,
            }
            with patch.dict(os.environ, env, clear=False):
                loaded = load_forum_bundle(
                    reasoning_path, relevance_path, manifest_path,
                    registry_documents=[manifest],
                )
            self.assertIsNotNone(loaded)
            self.assertEqual(
                FORUM_REASONING_MODEL_VERSION, loaded.reasoning.model_version,
            )
            self.assertEqual(
                FORUM_RELEVANCE_MODEL_VERSION, loaded.relevance.model_version,
            )

            for field in (
                "reasoningArtifactSha256", "relevanceArtifactSha256",
                "catalogueSha256", "bundleManifestSha256", "codeRevision",
                "compositePolicy",
            ):
                with self.subTest(field=field):
                    broken = dict(manifest)
                    broken[field] = (
                        "x" if field == "compositePolicy" else "f" * 64
                    )
                    manifest_path.write_text(
                        json.dumps(broken), encoding="utf-8",
                    )
                    with patch.dict(os.environ, env, clear=False):
                        self.assertIsNone(
                            load_forum_bundle(
                                reasoning_path, relevance_path, manifest_path,
                                registry_documents=[manifest],
                            )
                        )


if __name__ == "__main__":
    unittest.main()
