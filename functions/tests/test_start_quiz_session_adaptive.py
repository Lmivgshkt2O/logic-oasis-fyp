from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch
import unittest

FUNCTIONS_ROOT = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_ROOT) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_ROOT))

from functions import main


TOPIC_ID = "whole_numbers_y4"
SUBTOPIC_ID = "read_write_numbers"
STUDENT_ID = "student-1"
YEAR_LEVEL = 4


class Snapshot:
    def __init__(self, document_id: str, data: dict | None) -> None:
        self.id = document_id
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data or {})


class Document:
    def __init__(self, collection: "Collection", document_id: str) -> None:
        self._parent = collection
        self.id = document_id

    def get(self, transaction=None):
        return Snapshot(self.id, self._parent.documents.get(self.id))

    def collection(self, name: str):
        document = self._parent.documents.setdefault(self.id, {})
        return Collection(name, document.setdefault(name, {}))

    def create(self, data):
        if self.id in self._parent.documents:
            raise AssertionError(f"duplicate create: {self._parent.name}/{self.id}")
        self._parent.documents[self.id] = dict(data)


class Transaction:
    def get(self, reference: Document):
        return reference.get()

    def create(self, reference: Document, data: dict):
        reference.create(data)

    def set(self, reference: Document, data: dict):
        reference._parent.documents[reference.id] = dict(data)


class Query:
    def __init__(self, collection: "Collection", conditions: list[tuple[str, object]] | None = None) -> None:
        self.collection = collection
        self.conditions = conditions or []

    def where(self, field: str, _operator: str, value: object):
        return Query(self.collection, [*self.conditions, (field, value)])

    def limit(self, _value: int):
        return self

    def stream(self):
        return [
            Snapshot(document_id, data)
            for document_id, data in self.collection.documents.items()
            if all(data.get(field) == expected for field, expected in self.conditions)
        ]


class Collection:
    def __init__(self, name: str, documents: dict[str, dict]) -> None:
        self.name = name
        self.documents = documents

    def document(self, document_id: str):
        return Document(self, document_id)

    def where(self, field: str, operator: str, value: object):
        return Query(self, [(field, value)])


class Database:
    def __init__(self, collections: dict[str, dict[str, dict]]) -> None:
        self.collections = collections

    def collection(self, name: str):
        return Collection(name, self.collections.setdefault(name, {}))

    def get_all(self, references):
        return [reference.get() for reference in references]

    def transaction(self):
        return Transaction()


def bank(bank_id: str, difficulty: str) -> dict:
    question_ids = [f"{bank_id}_q{index}" for index in range(8)]
    return {
        "bankId": bank_id,
        "topicId": TOPIC_ID,
        "subtopicId": SUBTOPIC_ID,
        "skillId": "y4_whole_numbers_read_write",
        "yearLevel": YEAR_LEVEL,
        "difficultyLevel": difficulty,
        "questionIds": question_ids,
        "version": "2026.07.15",
        "isActive": True,
    }


def questions_for(bank_data: dict) -> dict[str, dict]:
    return {
        question_id: {
            "questionId": question_id,
            "bankId": bank_data["bankId"],
            "topicId": TOPIC_ID,
            "subtopicId": SUBTOPIC_ID,
            "skillId": "y4_whole_numbers_read_write",
            "yearLevel": YEAR_LEVEL,
            "difficultyLevel": bank_data["difficultyLevel"],
            "contentVersion": bank_data["version"],
            "isActive": True,
            "order": index,
            "questionText": f"Question {index}",
            "options": ["a", "b", "c", "d"],
            "optionsBm": ["a", "b", "c", "d"],
        }
        for index, question_id in enumerate(bank_data["questionIds"])
    }


def answer_keys_for(bank_data: dict) -> dict[str, dict]:
    return {
        question_id: {
            "questionId": question_id,
            "answerIndex": 0,
            "contentVersion": bank_data["version"],
            "isActive": True,
            "explanation": "Server-validated explanation.",
            "explanationBm": "Penerangan pelayan yang disahkan.",
        }
        for question_id in bank_data["questionIds"]
    }


class AdaptiveQuizStartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.easy = bank("easy-bank", "Easy")
        self.moderate = bank("moderate-bank", "Moderate")
        self.hard = bank("hard-bank", "Hard")
        self.database = Database({
            "questionBanks": {
                self.easy["bankId"]: self.easy,
                self.moderate["bankId"]: self.moderate,
                self.hard["bankId"]: self.hard,
            },
            "questions": {
                **questions_for(self.easy),
                **questions_for(self.moderate),
                **questions_for(self.hard),
            },
            "questionAnswerKeys": {
                **answer_keys_for(self.easy),
                **answer_keys_for(self.moderate),
                **answer_keys_for(self.hard),
            },
            "quizAttempts": {
                "attempt-1": {
                    "attemptId": "attempt-1",
                    "studentId": STUDENT_ID,
                    "topicId": TOPIC_ID,
                    "subtopicId": SUBTOPIC_ID,
                    "yearLevel": YEAR_LEVEL,
                    "sourceAttemptSequence": 1,
                    "validationStatus": "finalized",
                    "finalizationStatus": "finalized",
                    "dataSource": "runtime_callable",
                },
            },
            "subtopicMastery": {
                f"{STUDENT_ID}_y{YEAR_LEVEL}_{TOPIC_ID}_{SUBTOPIC_ID}": {
                    "studentId": STUDENT_ID,
                    "yearLevel": YEAR_LEVEL,
                    "topicId": TOPIC_ID,
                    "subtopicId": SUBTOPIC_ID,
                    "lastSourceAttemptId": "attempt-1",
                    "sourceAttemptSequence": 1,
                },
            },
            "studentSubtopicSequenceStates": {},
            "adaptiveAssignments": {
                f"{STUDENT_ID}_{SUBTOPIC_ID}": {
                    "studentId": STUDENT_ID,
                    "subtopicId": SUBTOPIC_ID,
                    "bankId": self.moderate["bankId"],
                    "difficultyLevel": "Moderate",
                    "policyVersion": "adaptive-policy-v1",
                    "status": "assigned",
                    "sourceAttemptId": "attempt-1",
                    "sourceAttemptSequence": 1,
                    "dataSource": "runtime_callable",
                },
            },
        })

    def _start(self) -> dict:
        with patch.object(main, "firestore_db", return_value=self.database), patch.object(
            main.firestore, "transactional", side_effect=lambda callback: callback
        ):
            return main.start_quiz_session({
                "topicId": TOPIC_ID,
                "subtopicId": SUBTOPIC_ID,
                "yearLevel": YEAR_LEVEL,
                # A client-supplied bank must never override the server assignment.
                "bankId": self.easy["bankId"],
            }, STUDENT_ID)

    def test_uses_only_a_compatible_runtime_assignment_and_rotates_question_forms(self) -> None:
        first = self._start()
        self.database.collections["quizAttempts"]["attempt-2"] = {
            **self.database.collections["quizAttempts"]["attempt-1"],
            "attemptId": "attempt-2",
            "sourceAttemptSequence": 2,
        }
        self.database.collections["subtopicMastery"][
            f"{STUDENT_ID}_y{YEAR_LEVEL}_{TOPIC_ID}_{SUBTOPIC_ID}"
        ].update({"lastSourceAttemptId": "attempt-2", "sourceAttemptSequence": 2})
        self.database.collections["adaptiveAssignments"][f"{STUDENT_ID}_{SUBTOPIC_ID}"].update({
            "sourceAttemptId": "attempt-2",
            "sourceAttemptSequence": 2,
        })
        persisted_first = next(iter(self.database.collections["quizSessions"].values()))
        self.assertEqual("attempt-1", persisted_first["assignedFromAttemptId"])
        self.assertEqual(1, persisted_first["assignedFromAttemptSequence"])
        persisted_first["status"] = "finalized"
        second = self._start()

        self.assertEqual("moderate-bank", first["bankId"])
        self.assertEqual("Moderate", first["difficultyLevel"])
        self.assertEqual(f"{STUDENT_ID}_{SUBTOPIC_ID}", first["assignmentId"])
        self.assertEqual("runtime_adaptive", first["assignmentSource"])
        self.assertNotEqual(first["questionIds"], second["questionIds"])
        self.assertEqual(
            set(self.moderate["questionIds"]),
            set(first["questionIds"]) | set(second["questionIds"]),
        )

    def test_untrusted_or_incompatible_assignment_safely_falls_back_to_easy(self) -> None:
        self.database.collections["adaptiveAssignments"][f"{STUDENT_ID}_{SUBTOPIC_ID}"]["dataSource"] = "seed_demo"

        session = self._start()

        self.assertEqual("easy-bank", session["bankId"])
        self.assertEqual("Easy", session["difficultyLevel"])
        self.assertEqual("cold_start_easy", session["assignmentId"])
        self.assertEqual("cold_start_easy", session["assignmentSource"])

    def test_mismatched_assignment_source_attempt_safely_falls_back_to_easy(self) -> None:
        self.database.collections["quizAttempts"]["attempt-1"]["attemptId"] = "different-attempt"

        session = self._start()

        self.assertEqual("easy-bank", session["bankId"])
        self.assertEqual("cold_start_easy", session["assignmentSource"])

    def test_compatible_hard_assignment_selects_the_hard_bank(self) -> None:
        self.database.collections["adaptiveAssignments"][f"{STUDENT_ID}_{SUBTOPIC_ID}"].update({
            "bankId": "hard-bank",
            "difficultyLevel": "Hard",
        })

        session = self._start()

        self.assertEqual("hard-bank", session["bankId"])
        self.assertEqual("Hard", session["difficultyLevel"])

    def test_inactive_assignment_bank_safely_falls_back_to_easy(self) -> None:
        self.database.collections["questionBanks"]["moderate-bank"]["isActive"] = False

        session = self._start()

        self.assertEqual("easy-bank", session["bankId"])
        self.assertEqual("cold_start_easy", session["assignmentSource"])

    def test_missing_assignment_answer_key_safely_falls_back_to_easy(self) -> None:
        self.database.collections["questionAnswerKeys"].pop("moderate-bank_q0")

        session = self._start()

        self.assertEqual("easy-bank", session["bankId"])
        self.assertEqual("cold_start_easy", session["assignmentSource"])

    def test_oversized_assignment_bank_safely_falls_back_to_easy(self) -> None:
        oversized = bank("moderate-bank", "Moderate")
        oversized["questionIds"] = [f"moderate-bank_q{index}" for index in range(11)]
        self.database.collections["questionBanks"]["moderate-bank"] = oversized
        self.database.collections["questions"].update(questions_for(oversized))

        session = self._start()

        self.assertEqual("easy-bank", session["bankId"])
        self.assertEqual("cold_start_easy", session["assignmentSource"])

    def test_invalid_first_easy_candidate_does_not_block_another_complete_easy_bank(self) -> None:
        self.database.collections["questionBanks"] = {
            "a-broken-easy": {
                **bank("a-broken-easy", "Easy"),
                "questionIds": ["missing-question"] * 5,
            },
            **self.database.collections["questionBanks"],
        }

        self.database.collections["adaptiveAssignments"].clear()
        session = self._start()

        self.assertEqual("easy-bank", session["bankId"])

    def test_fallback_uses_next_server_sequence_for_a_new_form(self) -> None:
        self.database.collections["adaptiveAssignments"].clear()
        self.database.collections["studentSubtopicSequenceStates"] = {
            STUDENT_ID: {"subtopics": {SUBTOPIC_ID: {"lastAllocatedSequence": 1}}},
        }

        session = self._start()

        self.assertEqual("easy-bank", session["bankId"])
        self.assertEqual(self.easy["questionIds"][5:], session["questionIds"][:3])

    def test_legacy_minimal_start_payload_remains_supported(self) -> None:
        with patch.object(main, "firestore_db", return_value=self.database), patch.object(
            main.firestore, "transactional", side_effect=lambda callback: callback
        ):
            session = main.start_quiz_session({
                "topicId": TOPIC_ID,
                "subtopicId": SUBTOPIC_ID,
                "yearLevel": YEAR_LEVEL,
            }, STUDENT_ID)

        self.assertEqual("moderate-bank", session["bankId"])
        self.assertIn("questions", session)

    def test_retry_reuses_the_one_active_session_and_form(self) -> None:
        first = self._start()
        second = self._start()

        self.assertEqual(first["sessionId"], second["sessionId"])
        self.assertEqual(first["questionIds"], second["questionIds"])
        self.assertEqual(1, len(self.database.collections["quizSessions"]))


if __name__ == "__main__":
    unittest.main()
