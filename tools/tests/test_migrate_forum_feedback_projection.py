from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import firebase_admin
from firebase_admin import firestore


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "functions"))

from migrate_forum_feedback_projection import (  # noqa: E402
    apply_redactions,
    main,
    redaction_plan,
)


class _Snapshot:
    def __init__(self, data, identifier):
        self.id = identifier
        self.exists = data is not None
        self._data = data

    def to_dict(self):
        return dict(self._data or {})


class _DocumentReference:
    def __init__(self, database, collection, identifier):
        self.database = database
        self.collection = collection
        self.id = identifier

    def get(self):
        return _Snapshot(
            self.database.rows.get((self.collection, self.id)), self.id,
        )

    def update(self, values):
        row = self.database.rows[(self.collection, self.id)]
        for key, value in values.items():
            if value is firestore.DELETE_FIELD:
                row.pop(key, None)
            else:
                row[key] = value


class _Collection:
    def __init__(self, database, name):
        self.database = database
        self.name = name

    def document(self, identifier):
        return _DocumentReference(self.database, self.name, identifier)

    def stream(self):
        return iter([
            _Snapshot(data, identifier)
            for (collection, identifier), data in self.database.rows.items()
            if collection == self.name
        ])

    def limit(self, count):
        return self


class _Database:
    def __init__(self, rows):
        self.rows = rows

    def collection(self, name):
        return _Collection(self, name)


def _rows():
    return {
        ("forumAnswers", "legacy_a1"): {
            "questionId": "q1", "authorId": "student-a", "text": "Legacy answer.",
            "aiFeedback": {
                "state": "completed", "label": "clear", "revision": 1,
                "message": "Thanks for explaining your method.",
                "probability": 0.9, "modelVersion": "forum-explanation-nb-v1",
                "calibrationState": "not_calibrated",
                "logicalInferenceId": "legacy-run", "updatedAt": "stamp",
            },
        },
        ("forumAnswers", "clean_a2"): {
            "questionId": "q1", "authorId": "student-b", "text": "Clean answer.",
        },
        ("forumAnswers", "private_only_a3"): {
            "questionId": "q1", "authorId": "student-c", "text": "Private only.",
            "aiFeedback": {
                "message": "Author-only guidance.", "probability": 0.8,
            },
        },
    }


class ForumFeedbackMigrationTests(unittest.TestCase):
    def test_dry_run_reports_counts_without_writing(self):
        rows = _rows()
        database = _Database(rows)
        before = {key: dict(value) for key, value in rows.items()}

        plan = redaction_plan(database)

        self.assertEqual(3, plan["scanned"])
        self.assertEqual(2, plan["with_embedded_feedback"])
        self.assertEqual(2, plan["needs_redaction"])
        self.assertEqual(rows, before)
        fields = {frozenset(fields) for _, fields in plan["affected"]}
        self.assertIn(
            frozenset({
                "message", "probability", "modelVersion", "calibrationState",
                "logicalInferenceId", "updatedAt",
            }),
            fields,
        )
        self.assertNotIn("text", {field for _, fields in plan["affected"] for field in fields})

    def test_apply_redacts_disallowed_fields_and_is_idempotent(self):
        rows = _rows()
        database = _Database(rows)
        plan = redaction_plan(database)

        changed = apply_redactions(database, plan["affected"])

        self.assertEqual(2, changed)
        self.assertEqual(
            {"state": "completed", "label": "clear", "revision": 1},
            rows[("forumAnswers", "legacy_a1")]["aiFeedback"],
        )
        self.assertNotIn("aiFeedback", rows[("forumAnswers", "private_only_a3")])
        self.assertEqual(0, redaction_plan(database)["needs_redaction"])
        self.assertEqual(0, apply_redactions(database, redaction_plan(database)["affected"]))

    def test_main_dry_run_prints_counts_without_answer_content(self):
        rows = _rows()
        database = _Database(rows)
        output = StringIO()
        with patch.dict(
            "os.environ", {"FIRESTORE_EMULATOR_HOST": "127.0.0.1:8080"},
        ), patch("firebase_admin.initialize_app") as initialize, patch(
            "firebase_admin.firestore.client", return_value=database,
        ) as client, redirect_stdout(output):
            main(["--emulator", "--project", "logic-oasis-fyp"])

        rendered = output.getvalue()
        self.assertIn("mode=dry-run", rendered)
        self.assertIn("needs_redaction=2", rendered)
        self.assertIn("no writes performed", rendered)
        for secret in ("Thanks for explaining your method.", "Legacy answer.", "0.9"):
            self.assertNotIn(secret, rendered)
        initialize.assert_called_once_with(options={"projectId": "logic-oasis-fyp"})
        self.assertTrue(client.called)

    def test_main_emulator_mode_requires_the_local_host(self):
        with patch.dict(
            "os.environ", {"FIRESTORE_EMULATOR_HOST": "remote.example:8080"},
        ):
            with self.assertRaises(SystemExit):
                main(["--emulator"])


if __name__ == "__main__":
    unittest.main()
