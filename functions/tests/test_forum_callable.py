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


if __name__ == "__main__":
    unittest.main()
