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
from parent_progress import (
    PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION,
    PARENT_PRACTICE_TIMEZONE,
    malaysia_week_start,
    malaysia_weekday_index,
)
from functions.quiz_session import response_document_id
from quiz_session import QuizSessionError
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
            "parentPracticeSummaries": {},
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

    def test_finalize_writes_the_current_week_practice_summary(self) -> None:
        before = datetime.now(timezone.utc)
        self._finalize()
        practice = self.database.collections["parentPracticeSummaries"][STUDENT_ID]
        expected_week = malaysia_week_start(before)
        expected_weekday = malaysia_weekday_index(before)

        self.assertEqual(PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION, practice["schemaVersion"])
        self.assertEqual(STUDENT_ID, practice["studentId"])
        self.assertEqual(PARENT_PRACTICE_TIMEZONE, practice["timezone"])
        self.assertEqual(expected_week, practice["weekStart"])
        daily = [0] * 7
        daily[expected_weekday] = 1
        self.assertEqual(daily, practice["dailyCompletionCounts"])
        self.assertEqual(1, practice["completedPracticeCount"])
        self.assertEqual(1, practice["activeDayCount"])
        self.assertNotIn("previousWeekCompletedPracticeCount", practice)
        self.assertIn("updatedAt", practice)

    def test_duplicate_finalization_does_not_increment_practice_twice(self) -> None:
        self._finalize()
        self._finalize()
        practice = self.database.collections["parentPracticeSummaries"][STUDENT_ID]
        self.assertEqual(1, practice["completedPracticeCount"])

    def test_finalize_rolls_the_weekly_summary_and_carries_the_prior_total(
        self,
    ) -> None:
        before = datetime.now(timezone.utc)
        previous_week = malaysia_week_start(before) - timedelta(days=7)
        self.database.collections["parentPracticeSummaries"][STUDENT_ID] = {
            "schemaVersion": PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION,
            "studentId": STUDENT_ID,
            "timezone": PARENT_PRACTICE_TIMEZONE,
            "weekStart": previous_week,
            "dailyCompletionCounts": [2, 0, 0, 0, 1, 0, 0],
            "completedPracticeCount": 3,
            "activeDayCount": 2,
        }

        self._finalize()

        practice = self.database.collections["parentPracticeSummaries"][STUDENT_ID]
        self.assertEqual(malaysia_week_start(before), practice["weekStart"])
        self.assertEqual(3, practice["previousWeekCompletedPracticeCount"])
        self.assertEqual(1, practice["completedPracticeCount"])

    def test_finalize_fails_closed_on_malformed_practice_summary(self) -> None:
        before = datetime.now(timezone.utc)
        self.database.collections["parentPracticeSummaries"][STUDENT_ID] = {
            "schemaVersion": PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION,
            "studentId": STUDENT_ID,
            "timezone": PARENT_PRACTICE_TIMEZONE,
            "weekStart": malaysia_week_start(before),
            "dailyCompletionCounts": [-1, 0, 0, 0, 0, 0, 0],
            "completedPracticeCount": -1,
            "activeDayCount": 1,
        }

        with self.assertRaisesRegex(QuizSessionError, "Practice summary"):
            self._finalize()

    def test_missing_review_focus_fails_closed(self) -> None:
        wrong_ref = self.database.collections["questionResponses"][
            response_document_id(SESSION_ID, 1)
        ]
        del wrong_ref["reviewFocus"]
        with self.assertRaisesRegex(Exception, "review focus"):
            self._finalize()

    def test_zero_percent_attempt_soft_unlocks_without_completing(self) -> None:
        for index in range(5):
            self._mark_wrong(index)
        completion = self._finalize()
        self.assertEqual(0, completion["correctCount"])
        mastery_id = f"{STUDENT_ID}_y{YEAR_LEVEL}_{TOPIC_ID}_{SUBTOPIC_ID}"
        mastery = self.database.collections["subtopicMastery"][mastery_id]
        self.assertTrue(mastery["attempted"])
        self.assertTrue(mastery["accessUnlocked"])
        self.assertFalse(mastery["completed"])
        self.assertEqual("repeat_subtopic", mastery["recommendedLearningAction"])
        self.assertEqual("provisional_pending_ai", mastery["recommendationBasis"])
        self.assertEqual(SUBTOPIC_ID, mastery["recommendationTargetSubtopicId"])
        self.assertEqual("New", mastery["masteryLevel"])
        self.assertEqual(0.0, mastery["bestCorrectRate"])

    def test_reattempting_a_completed_subtopic_preserves_completion(self) -> None:
        mastery_id = f"{STUDENT_ID}_y{YEAR_LEVEL}_{TOPIC_ID}_{SUBTOPIC_ID}"
        self.database.collections["subtopicMastery"][mastery_id] = {
            "studentId": STUDENT_ID,
            "yearLevel": YEAR_LEVEL,
            "topicId": TOPIC_ID,
            "subtopicId": SUBTOPIC_ID,
            "completed": True,
            "bestCorrectRate": 0.8,
        }
        for index in range(5):
            self._mark_wrong(index)
        self._finalize()
        mastery = self.database.collections["subtopicMastery"][mastery_id]
        self.assertTrue(mastery["completed"])
        self.assertTrue(mastery["accessUnlocked"])
        self.assertEqual(0.8, mastery["bestCorrectRate"])

    def _mark_wrong(self, index: int) -> None:
        wrong = self.database.collections["questionResponses"][
            response_document_id(SESSION_ID, index)
        ]
        wrong["serverIsCorrect"] = False
        wrong.setdefault("reviewFocus", f"Focus on option {index % 4}.")
        wrong.setdefault("reviewFocusBm", f"Fokus pada pilihan {index % 4}.")


if __name__ == "__main__":
    unittest.main()
