from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from firebase_functions import https_fn
import main


class _Snapshot:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return self._data


class _Document:
    def __init__(self, data):
        self._data = data

    def get(self):
        return _Snapshot(self._data)


class _Users:
    def __init__(self, profiles):
        self._profiles = profiles

    def document(self, identifier):
        return _Document(self._profiles.get(identifier))


class _Database:
    def __init__(self, profiles):
        self._profiles = profiles

    def collection(self, name):
        assert name == "users"
        return _Users(self._profiles)


class ForumCallableTests(unittest.TestCase):
    def test_forum_call_maps_anonymous_and_parent_authority_to_https_errors(self):
        database = _Database({"parent-1": {"role": "parent"}})
        anonymous = SimpleNamespace(auth=None)
        parent = SimpleNamespace(auth=SimpleNamespace(uid="parent-1"))

        with patch.object(main, "firestore_db", return_value=database):
            for request, expected in (
                (anonymous, https_fn.FunctionsErrorCode.UNAUTHENTICATED),
                (parent, https_fn.FunctionsErrorCode.PERMISSION_DENIED),
            ):
                with self.subTest(expected=expected):
                    with self.assertRaises(https_fn.HttpsError) as raised:
                        main._forum_call(lambda _student_id: {}, request)
                    self.assertEqual(raised.exception.code, expected)

    def test_forum_call_derives_the_student_actor_from_authenticated_profile(self):
        database = _Database({"student-1": {"role": "student"}})
        request = SimpleNamespace(auth=SimpleNamespace(uid="student-1"))

        with patch.object(main, "firestore_db", return_value=database):
            result = main._forum_call(lambda student_id: {"actorId": student_id}, request)

        self.assertEqual(result, {"actorId": "student-1"})

    def test_forum_call_maps_missing_and_wrong_payloads_to_invalid_argument(self):
        database = _Database({"student-1": {"role": "student"}})

        with patch.object(main, "firestore_db", return_value=database):
            for payload in (None, {}, {"answerId": 42}):
                request = SimpleNamespace(
                    auth=SimpleNamespace(uid="student-1"), data=payload,
                )
                with self.subTest(payload=payload):
                    with self.assertRaises(https_fn.HttpsError) as raised:
                        main._forum_call(
                            lambda _student_id: {
                                "answerId": main._string(main._data(request), "answerId")
                            },
                            request,
                        )
                    self.assertEqual(
                        raised.exception.code,
                        https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
                    )


class _RowsSnapshot:
    def __init__(self, data, identifier=None):
        self._data = data
        self.id = identifier
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data or {})


class _RowsReference:
    def __init__(self, database, collection, identifier):
        self.database = database
        self.collection = collection
        self.id = identifier

    def get(self):
        return _RowsSnapshot(
            self.database.rows.get((self.collection, self.id)), self.id,
        )


class _RowsCollection:
    def __init__(self, database, name):
        self.database = database
        self.name = name

    def document(self, identifier=None):
        if identifier is None:
            self.database._auto_ids[self.name] = (
                self.database._auto_ids.get(self.name, 0) + 1
            )
            identifier = f"auto_{self.database._auto_ids[self.name]}"
        return _RowsReference(self.database, self.name, identifier)

    def where(self, field, operator, value):
        return _RowsQuery(self.database, self.name, [(field, operator, value)])


class _RowsQuery:
    def __init__(self, database, collection, filters):
        self.database = database
        self.collection = collection
        self.filters = filters


class _RowsTransaction:
    def __init__(self, database):
        self.database = database

    def get(self, reference):
        if isinstance(reference, _RowsQuery):
            return iter([
                _RowsSnapshot(data, identifier)
                for (collection, identifier), data in self.database.rows.items()
                if collection == reference.collection and all(
                    data.get(field) == value
                    for field, operator, value in reference.filters
                    if operator == "=="
                )
            ])
        return _RowsSnapshot(
            self.database.rows.get((reference.collection, reference.id)),
            reference.id,
        )

    def set(self, reference, values, **_kwargs):
        key = (reference.collection, reference.id)
        if _kwargs.get("merge"):
            self.database.rows.setdefault(key, {}).update(values)
        else:
            self.database.rows[key] = dict(values)

    def update(self, reference, values):
        self.database.rows[(reference.collection, reference.id)].update(values)

    def create(self, reference, values):
        key = (reference.collection, reference.id)
        if key in self.database.rows:
            raise RuntimeError("already exists")
        self.database.rows[key] = dict(values)

    def delete(self, reference):
        key = (reference.collection, reference.id)
        if key in self.database.rows:
            del self.database.rows[key]


class _RowsDatabase:
    def __init__(self, rows):
        self.rows = rows
        self._auto_ids = {}

    def collection(self, name):
        return _RowsCollection(self, name)

    def transaction(self):
        return _RowsTransaction(self)


def _linked_rows():
    return {
        ("users", "student-1"): {"role": "student"},
        ("users", "student-2"): {"role": "student"},
        ("questions", "bank_q1"): {
            "questionId": "bank_q1",
            "questionText": "Which numeral shows twenty thousand and four?",
            "questionTextBm": "Angka manakah menunjukkan dua puluh ribu empat?",
            "options": ["20 004", "24 000", "20 400", "20 040"],
            "optionsBm": ["20 004", "24 000", "20 400", "20 040"],
            "contentVersion": "v1",
            "isActive": True,
        },
        ("questionAnswerKeys", "bank_q1"): {
            "questionId": "bank_q1", "contentVersion": "v1",
            "isActive": True, "answerIndex": 0,
        },
    }


def _student_request(data):
    return SimpleNamespace(
        auth=SimpleNamespace(uid="student-1"), data=data,
    )


class LinkedForumCallableTests(unittest.TestCase):
    def _call(self, handler_name, rows, payload, uid="student-1"):
        database = _RowsDatabase(rows)
        handler = getattr(main, handler_name)
        request = _student_request(payload)
        with patch.object(
            main, "firestore_db", return_value=database,
        ), patch("forum_runtime.firestore.transactional", lambda function: function):
            return main._forum_call(
                lambda student_id: handler(main._data(request), student_id), request,
            )

    def test_open_or_create_forum_discussion_accepts_only_the_public_question_id(self):
        rows = _linked_rows()
        first = self._call(
            "_open_or_create_linked_discussion",
            rows,
            {"questionId": "bank_q1"},
        )
        second = self._call(
            "_open_or_create_linked_discussion",
            rows,
            {"questionId": "bank_q1"},
        )
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual("linked_bank_q1_v1", first["discussionId"])
        self.assertEqual(first["discussionId"], second["discussionId"])
        self.assertEqual("bank_q1", first["sourceQuestionId"])
        self.assertEqual("v1", first["sourceContentVersion"])
        self.assertNotIn("answerIndex", first)

    def test_open_or_create_forum_discussion_rejects_wrong_payloads(self):
        rows = _linked_rows()
        for payload in (None, {}, {"questionId": 42}, {"questionId": ""}):
            with self.subTest(payload=payload):
                with self.assertRaises(https_fn.HttpsError) as raised:
                    self._call("_open_or_create_linked_discussion", rows, payload)
                self.assertEqual(
                    raised.exception.code,
                    https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
                )

    def test_open_or_create_forum_discussion_maps_incompatible_source_errors(self):
        rows = _linked_rows()
        rows[("questionAnswerKeys", "bank_q1")]["isActive"] = False
        with self.assertRaises(https_fn.HttpsError) as raised:
            self._call(
                "_open_or_create_linked_discussion",
                rows,
                {"questionId": "bank_q1"},
            )
        self.assertEqual(
            raised.exception.code,
            https_fn.FunctionsErrorCode.FAILED_PRECONDITION,
        )

    def test_submit_linked_forum_answer_creates_structured_answer(self):
        rows = _linked_rows()
        rows[("forumQuestions", "linked_bank_q1_v1")] = {
            "mode": "linked", "sourceQuestionId": "bank_q1",
            "sourceContentVersion": "v1",
        }
        result = self._call(
            "_submit_linked_forum_answer",
            rows,
            {
                "discussionId": "linked_bank_q1_v1",
                "selectedOption": 2,
                "explanation": "I added the thousands and compared the digits.",
            },
        )
        self.assertEqual("linked_bank_q1_v1", result["questionId"])
        self.assertEqual(1, result["revision"])

    def test_submit_linked_forum_answer_maps_validation_errors(self):
        rows = _linked_rows()
        rows[("forumQuestions", "linked_bank_q1_v1")] = {"mode": "linked"}
        cases = (
            ({"discussionId": "linked_bank_q1_v1", "selectedOption": 4,
              "explanation": "I compared the digits carefully."},
             https_fn.FunctionsErrorCode.INVALID_ARGUMENT),
            ({"discussionId": "missing", "selectedOption": 1,
              "explanation": "I compared the digits carefully."},
             https_fn.FunctionsErrorCode.NOT_FOUND),
        )
        for payload, expected in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(https_fn.HttpsError) as raised:
                    self._call(
                        "_submit_linked_forum_answer", rows, payload,
                    )
                self.assertEqual(raised.exception.code, expected)

    def test_edit_linked_forum_answer_maps_ownership_and_validation_errors(self):
        rows = _linked_rows()
        rows[("forumQuestions", "linked_bank_q1_v1")] = {"mode": "linked"}
        rows[("forumAnswers", "a1")] = {
            "questionId": "linked_bank_q1_v1", "authorId": "student-2",
            "mode": "linked", "selectedOption": 0, "explanation": "Original explanation.",
            "revision": 1,
        }
        with self.assertRaises(https_fn.HttpsError) as raised:
            self._call(
                "_edit_linked_forum_answer",
                rows,
                {
                    "answerId": "a1", "selectedOption": 1,
                    "explanation": "A revised explanation for the peer.",
                },
            )
        self.assertEqual(
            raised.exception.code, https_fn.FunctionsErrorCode.PERMISSION_DENIED,
        )

    def test_delete_forum_answer_removes_own_answer_and_maps_validation_errors(self):
        rows = _linked_rows()
        rows[("forumQuestions", "linked_bank_q1_v1")] = {
            "mode": "linked", "sourceQuestionId": "bank_q1",
        }
        rows[("forumAnswers", "a1")] = {
            "questionId": "linked_bank_q1_v1", "authorId": "student-1",
            "mode": "linked", "selectedOption": 0,
            "explanation": "I compared the digits carefully.", "revision": 1,
        }
        result = self._call("_delete_forum_answer", rows, {"answerId": "a1"})
        self.assertTrue(result["deleted"])
        self.assertNotIn(("forumAnswers", "a1"), rows)

        for payload in (None, {}, {"answerId": 42}):
            with self.subTest(payload=payload):
                with self.assertRaises(https_fn.HttpsError) as raised:
                    self._call("_delete_forum_answer", rows, payload)
                self.assertEqual(
                    raised.exception.code,
                    https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
                )

    def test_delete_forum_question_removes_own_thread_and_denies_foreign_author(self):
        rows = _linked_rows()
        rows[("forumQuestions", "q1")] = {
            "authorId": "student-1",
            "title": "How do you add 46 and 27?",
            "text": "What is 46 + 27? Show your working.",
        }
        rows[("forumAnswers", "a1")] = {
            "questionId": "q1", "authorId": "student-2", "text": "I regrouped the ones.",
        }
        result = self._call("_delete_forum_question", rows, {"questionId": "q1"})
        self.assertTrue(result["deleted"])
        self.assertEqual(1, result["deletedAnswerCount"])
        self.assertNotIn(("forumQuestions", "q1"), rows)
        self.assertNotIn(("forumAnswers", "a1"), rows)

        rows[("forumQuestions", "q2")] = {
            "authorId": "student-2",
            "title": "How do you subtract 46 from 100?",
            "text": "What is 100 minus 46? Show your working.",
        }
        with self.assertRaises(https_fn.HttpsError) as raised:
            self._call("_delete_forum_question", rows, {"questionId": "q2"})
        self.assertEqual(
            raised.exception.code, https_fn.FunctionsErrorCode.PERMISSION_DENIED,
        )

    def test_delete_forum_question_hides_linked_thread_from_the_viewer(self):
        rows = _linked_rows()
        rows[("forumQuestions", "linked_bank_q1_v1")] = {
            "mode": "linked", "sourceQuestionId": "bank_q1",
        }
        result = self._call(
            "_delete_forum_question",
            rows,
            {"questionId": "linked_bank_q1_v1"},
        )
        self.assertTrue(result["deleted"])
        self.assertEqual("viewer", result["scope"])
        # The canonical shared thread remains; only the viewer marker is added.
        self.assertIn(("forumQuestions", "linked_bank_q1_v1"), rows)
        marker = rows[("forumQuestionDeletions", "student-1_linked_bank_q1_v1")]
        self.assertEqual("student-1", marker["studentId"])
        self.assertEqual("linked_bank_q1_v1", marker["questionId"])


if __name__ == "__main__":
    unittest.main()
