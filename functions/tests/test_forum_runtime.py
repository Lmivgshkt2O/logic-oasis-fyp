from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "functions"))

from forum_runtime import (
    ForumRuntimeError,
    ForumRuntimeGateway,
    _transaction_snapshot,
    feedback_for,
    load_forum_classifier,
    malaysia_week_start,
)
from logic_oasis_ai.forum_ai.classifier import REVISION, SUFFICIENT, UNCERTAIN


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
        self.database.rows[(reference.collection, reference.identifier)] = dict(values)


class _Database:
    def __init__(self, rows):
        self.rows = rows

    def collection(self, name):
        return _Collection(self, name)

    def transaction(self):
        return _Transaction(self)


class ForumRuntimeTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
