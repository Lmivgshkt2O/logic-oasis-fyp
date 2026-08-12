from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from unittest.mock import patch
import unittest

FUNCTIONS_ROOT = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_ROOT) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_ROOT))

import main
from functions.quiz_session import response_document_id
from functions.tests.test_start_quiz_session_adaptive import (
    Database,
    STUDENT_ID,
    SUBTOPIC_ID,
    TOPIC_ID,
    YEAR_LEVEL,
)


NOW = datetime(2099, 1, 1, tzinfo=timezone.utc)
SESSION_ID = "session-review"
ATTEMPT_ID = "attempt-review"


def question(question_id: str, index: int) -> dict:
    return {
        "questionId": question_id,
        "bankId": "bank-review",
        "topicId": TOPIC_ID,
        "subtopicId": SUBTOPIC_ID,
        "skillId": "y4_whole_numbers_read_write",
        "yearLevel": YEAR_LEVEL,
        "difficultyLevel": "Easy",
        "contentVersion": "v1",
        "isActive": True,
        "order": index,
        "questionText": f"Prompt {index}",
        "questionTextBm": f"Soalan {index}",
        "questionType": f"Type {index}",
        "questionTypeBm": f"Jenis {index}",
        "options": ["a", "b", "c", "d"],
        "optionsBm": ["a", "b", "c", "d"],
    }


def answer_key(question_id: str) -> dict:
    return {
        "questionId": question_id,
        "answerIndex": 0,
        "contentVersion": "v1",
        "isActive": True,
        "feedbackByOption": {
            str(index): {
                "misconceptionCode": f"misconception_{index}",
                "hint": f"Hint for option {index}.",
                "hintBm": f"Petunjuk untuk pilihan {index}.",
                "reviewFocus": f"Focus on option {index}.",
                "reviewFocusBm": f"Fokus pada pilihan {index}.",
            }
            for index in (1, 2, 3)
        },
    }


def session_document(question_ids: list[str]) -> dict:
    return {
        "sessionId": SESSION_ID,
        "attemptId": ATTEMPT_ID,
        "studentId": STUDENT_ID,
        "bankId": "bank-review",
        "topicId": TOPIC_ID,
        "subtopicId": SUBTOPIC_ID,
        "yearLevel": YEAR_LEVEL,
        "difficultyLevel": "Easy",
        "contentVersion": "v1",
        "assignmentId": "cold_start_easy",
        "assignmentSource": "cold_start_easy",
        "adaptivePolicyVersion": "adaptive-policy-v1",
        "questionIds": question_ids,
        "expectedResponseCount": len(question_ids),
        "validatedResponseCount": len(question_ids),
        "status": "active",
        "startedAt": NOW,
        "expiresAt": NOW + timedelta(minutes=30),
    }


def response_document(question_id: str, index: int, is_correct: bool) -> dict:
    document = {
        "responseId": response_document_id(SESSION_ID, index),
        "sessionId": SESSION_ID,
        "attemptId": ATTEMPT_ID,
        "studentId": STUDENT_ID,
        "questionId": question_id,
        "skillId": "y4_whole_numbers_read_write",
        "bankId": "bank-review",
        "questionVersion": "v1",
        "contentVersion": "v1",
        "selectedIndex": index % 4,
        "serverIsCorrect": is_correct,
        "validationStatus": "validated",
        "responseTimeMs": 500,
        "responseTimeQuality": "client_reported_unverified",
        "hintCount": 0,
        "hintTelemetryStatus": "not_supported",
        "sequenceIndex": index,
        "idempotencyKey": f"response-{index}",
        "createdAt": NOW,
    }
    if not is_correct:
        document.update({
            "misconceptionCode": "misconception_test",
            "feedbackHint": f"Hint for option {index % 4}.",
            "feedbackHintBm": f"Petunjuk untuk pilihan {index % 4}.",
            "reviewFocus": f"Focus on option {index % 4}.",
            "reviewFocusBm": f"Fokus pada pilihan {index % 4}.",
        })
    return document


class QuizFinalizeReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        question_ids = [f"question-{index}" for index in range(5)]
        # Question 1 (index 1) and question 3 (index 3) are answered wrong;
        # the others are correct. ServerIsCorrect is fixed, not derived from
        # the answer key, so the sealed responses stay answer-free.
        response_data = {
            response_document_id(SESSION_ID, index): response_document(
                question_id, index, index not in (1, 3)
            )
            for index, question_id in enumerate(question_ids)
        }
        self.database = Database({
            "quizSessions": {SESSION_ID: session_document(question_ids)},
            "questions": {
                question_id: question(question_id, index)
                for index, question_id in enumerate(question_ids)
            },
            "questionAnswerKeys": {
                question_id: answer_key(question_id)
                for question_id in question_ids
            },
            "questionResponses": response_data,
            "studentSubtopicSequenceStates": {},
            "subtopicMastery": {},
        })

    def _finalize(self) -> dict:
        with patch.object(main, "firestore_db", return_value=self.database), patch.object(
            main.firestore, "transactional", side_effect=lambda callback: callback
        ):
            return main.finalize_quiz_session({"sessionId": SESSION_ID}, STUDENT_ID)

    def test_finalize_returns_only_missed_questions_in_order_with_review_metadata(self) -> None:
        completion = self._finalize()
        self.assertEqual(3, completion["correctCount"])
        self.assertEqual(2, len(completion["reviewItems"]))
        self.assertEqual(
            ["question-1", "question-3"],
            [item["questionId"] for item in completion["reviewItems"]],
        )
        self.assertEqual(
            [1, 3],
            [item["sequenceIndex"] for item in completion["reviewItems"]],
        )
        first = completion["reviewItems"][0]
        self.assertEqual("Prompt 1", first["questionText"])
        self.assertEqual("Soalan 1", first["questionTextBm"])
        self.assertEqual("Type 1", first["questionType"])
        self.assertEqual("Jenis 1", first["questionTypeBm"])
        self.assertEqual("Focus on option 1.", first["reviewFocus"])
        self.assertEqual("Fokus pada pilihan 1.", first["reviewFocusBm"])
        for item in completion["reviewItems"]:
            self.assertNotIn("options", item)
            self.assertNotIn("answerIndex", item)
            self.assertNotIn("feedbackHint", item)

    def test_duplicate_finalization_is_idempotent(self) -> None:
        first = self._finalize()
        second = self._finalize()
        self.assertEqual(first["reviewItems"], second["reviewItems"])
        self.assertEqual(first["attemptId"], second["attemptId"])

    def test_missing_review_focus_fails_closed(self) -> None:
        wrong_ref = self.database.collections["questionResponses"][
            response_document_id(SESSION_ID, 1)
        ]
        del wrong_ref["reviewFocus"]
        with self.assertRaisesRegex(Exception, "review focus"):
            self._finalize()


if __name__ == "__main__":
    unittest.main()
