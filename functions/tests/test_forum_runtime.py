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

from forum_runtime import (
    ForumAiClaim,
    ForumRuntimeError,
    ForumRuntimeGateway,
    _transaction_snapshot,
    feedback_for,
    load_forum_classifier,
    malaysia_week_start,
)
from logic_oasis_ai.forum_ai.classifier import ForumPrediction, REVISION, SUFFICIENT, UNCERTAIN


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


class _Collection:
    def __init__(self, database, name):
        self.database = database
        self.name = name

    def document(self, identifier):
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


class _Database:
    def __init__(self, rows):
        self.rows = rows

    def collection(self, name):
        return _Collection(self, name)

    def transaction(self):
        return _Transaction(self)


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
        self.assertEqual("fallback", database.rows[("forumAnswers", "a1")]["aiFeedback"]["state"])
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
                stale, ForumPrediction(SUFFICIENT, 0.9, "model-v1"), now=now,
            )

        self.assertEqual("superseded", state)
        self.assertNotIn("aiFeedback", database.rows[("forumAnswers", "a1")])
        self.assertEqual("processing", database.rows[("forumAiJobs", "a1")]["state"])
        self.assertEqual("superseded", database.rows[("forumAiRuns", "old-run")]["state"])

    def test_reclaimed_same_identity_lease_lets_only_new_fencing_generation_win(self):
        now = datetime(2026, 8, 3, tzinfo=timezone.utc)
        text = "I regrouped and checked each place value."
        text_hash = sha256(text.encode("utf-8")).hexdigest()
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
                "superseded", gateway._finalize_answer(old_claim, prediction, now=now),
            )
            self.assertNotIn(("forumAiRuns", logical_id), database.rows)
            self.assertEqual(
                "completed", gateway._finalize_answer(winning_claim, prediction, now=now),
            )

        self.assertEqual("completed", database.rows[("forumAiRuns", logical_id)]["state"])
        self.assertEqual("completed", database.rows[("forumAnswers", "a1")]["aiFeedback"]["state"])

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
            new_feedback = dict(database.rows[("forumAnswers", "a1")]["aiFeedback"])
            self.assertEqual("superseded", gateway.process_answer(
                "a1", old, classifier, event_id="old", now=now + timedelta(seconds=1),
            ))

        self.assertEqual(new_job, database.rows[("forumAiJobs", "a1")])
        self.assertEqual(new_feedback, database.rows[("forumAnswers", "a1")]["aiFeedback"])

    def test_immutable_run_repairs_terminal_job_and_feedback_after_partial_failure(self):
        now = datetime(2026, 8, 3, tzinfo=timezone.utc)
        answer = {"authorId": "student-a", "revision": 1, "text": "My reasoning."}
        text_hash = sha256(answer["text"].encode("utf-8")).hexdigest()
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
        self.assertEqual("completed", database.rows[("forumAnswers", "a1")]["aiFeedback"]["state"])

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
        self.assertEqual("fallback", database.rows[("forumAnswers", "a1")]["aiFeedback"]["state"])

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
        self.assertEqual("fallback", database.rows[("forumAnswers", "a2")]["aiFeedback"]["state"])
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
            self.assertIsNotNone(load_forum_classifier(registry_documents=[release_manifest]))
        with self.assertLogs("forum_runtime", level="WARNING") as logs, patch.dict(
            os.environ,
            {**controlled, "FORUM_MODEL_EVIDENCE_MODE": "real_evaluated_only"},
            clear=False,
        ):
            self.assertIsNone(load_forum_classifier(registry_documents=[release_manifest]))
        rendered = " ".join(logs.output)
        self.assertIn("mode_or_registry_incompatible", rendered)
        self.assertNotIn("learner", rendered)

    def test_every_binding_is_validated_before_joblib_load(self):
        original = json.loads(
            (ROOT / "functions/forum_model_manifest.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "forum_model.joblib"
            shutil.copyfile(ROOT / "functions/forum_model.joblib", artifact)
            shutil.copyfile(ROOT / "functions/forum_runtime.py", root / "forum_runtime.py")
            shutil.copyfile(ROOT / "functions/main.py", root / "main.py")
            shutil.copytree(
                ROOT / "functions/vendor/logic_oasis_ai/forum_ai",
                root / "vendor/logic_oasis_ai/forum_ai",
            )
            shutil.copyfile(
                ROOT / "functions/vendor/bundle_manifest.json",
                root / "vendor/bundle_manifest.json",
            )
            manifest = root / "forum_model_manifest.json"
            manifest.write_text(json.dumps(original), encoding="utf-8")
            sentinel = type("Classifier", (), {"model_version": original["modelVersion"]})()
            with patch(
                "forum_runtime.ForumTextClassifier.load", return_value=sentinel,
            ) as valid_load:
                self.assertIs(
                    sentinel,
                    load_forum_classifier(
                        artifact,
                        manifest,
                        registry_documents=[original],
                        evidence_mode="controlled_demo",
                        code_revision=original["codeRevision"],
                    ),
                )
                valid_load.assert_called_once_with(artifact)
            for field in (
                "artifactSha256", "catalogueSha256", "datasetSha256",
                "evaluationReportSha256", "bundleManifestSha256", "codeRevision",
            ):
                with self.subTest(field=field):
                    broken = dict(original)
                    broken[field] = "0" * 64
                    manifest.write_text(json.dumps(broken), encoding="utf-8")
                    with patch.dict(os.environ, {
                        "FORUM_MODEL_EVIDENCE_MODE": "controlled_demo",
                        "FORUM_RUNTIME_CODE_REVISION": original["codeRevision"],
                    }, clear=False), patch(
                        "forum_runtime.ForumTextClassifier.load",
                    ) as unsafe_load:
                        self.assertIsNone(
                            load_forum_classifier(
                                artifact, manifest, registry_documents=[original],
                            )
                        )
                        unsafe_load.assert_not_called()
            manifest.write_text(json.dumps(original), encoding="utf-8")
            vendored_classifier = root / "vendor/logic_oasis_ai/forum_ai/classifier.py"
            vendored_classifier.write_bytes(vendored_classifier.read_bytes() + b"\n# tampered\n")
            with patch(
                "forum_runtime.ForumTextClassifier.load",
            ) as unsafe_load:
                self.assertIsNone(
                    load_forum_classifier(
                        artifact,
                        manifest,
                        registry_documents=[original],
                        evidence_mode="controlled_demo",
                        code_revision=original["codeRevision"],
                    )
                )
                unsafe_load.assert_not_called()

    def test_zero_or_multiple_active_compatible_releases_fail_closed(self):
        release = json.loads(
            (ROOT / "functions/forum_model_manifest.json").read_text(encoding="utf-8")
        )
        env = {
            "FORUM_MODEL_EVIDENCE_MODE": "controlled_demo",
            "FORUM_RUNTIME_CODE_REVISION": release["codeRevision"],
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertIsNone(load_forum_classifier(registry_documents=[]))
            self.assertIsNone(load_forum_classifier(registry_documents=[release, release]))

    def test_demo_student_answer_reaches_genuine_nb_once_without_corpus_or_text_log(self):
        release = json.loads(
            (ROOT / "functions/forum_model_manifest.json").read_text(encoding="utf-8")
        )
        with patch.dict(os.environ, {
            "FORUM_MODEL_EVIDENCE_MODE": "controlled_demo",
            "FORUM_RUNTIME_CODE_REVISION": release["codeRevision"],
        }, clear=False):
            classifier = load_forum_classifier(registry_documents=[release])
        self.assertIsNotNone(classifier)
        self.assertEqual("MultinomialNB", type(classifier.pipeline.named_steps["classifier"]).__name__)
        answer = {
            "authorId": "u10-demo-student", "questionId": "u10-demo-question",
            "revision": 1,
            "text": "I regrouped the tens first, subtracted each place, and checked by adding back.",
        }
        database = _Database({("forumAnswers", "u10-demo-answer"): dict(answer)})
        with patch("forum_runtime.firestore.transactional", lambda function: function):
            state = ForumRuntimeGateway(database).process_answer(
                "u10-demo-answer", answer, classifier,
                event_id="u10-demo-event", now=datetime(2026, 8, 9, tzinfo=timezone.utc),
            )
        self.assertEqual("completed", state)
        self.assertEqual(1, sum(key[0] == "forumAiJobs" for key in database.rows))
        self.assertEqual(1, sum(key[0] == "forumAiRuns" for key in database.rows))
        run = next(
            value for key, value in database.rows.items() if key[0] == "forumAiRuns"
        )
        self.assertEqual("controlled_demonstration_only", run["claimLevel"])
        self.assertEqual(release["artifactSha256"], run["artifactIdentity"])
        ai_records = {
            str(key): value for key, value in database.rows.items()
            if key[0] in {"forumAiJobs", "forumAiRuns"}
        }
        self.assertNotIn(answer["text"], json.dumps(ai_records, default=str))
        self.assertFalse(any("training" in key[0].casefold() or "dataset" in key[0].casefold() for key in database.rows))


if __name__ == "__main__":
    unittest.main()
