from datetime import timedelta
import unittest

from ai_pipeline.logic_oasis_ai.schemas import (
    FinalizedQuizAttemptRecord,
    ValidatedResponseRecord,
)
from ai_pipeline.logic_oasis_ai.validators import validate_response_lineage
from functions.tests.test_quiz_session import NOW, service
from functions.quiz_session import QuizSessionError


class AttemptValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = service()
        self.session = self.service.start_session(
            student_id="student-a", topic_id="y4_whole_numbers",
            subtopic_id="read_write_numbers", year_level=4, now=NOW,
        )

    def _submit_all(self) -> None:
        for index, question_id in enumerate(self.session["questionIds"]):
            self.service.submit_response(
                student_id="student-a", session_id=self.session["sessionId"],
                question_id=question_id, selected_index=index % 4, sequence_index=index,
                response_time_ms=500, hint_count=0, idempotency_key=f"response-{index}", now=NOW,
            )

    def test_incomplete_session_cannot_finalize(self) -> None:
        with self.assertRaisesRegex(QuizSessionError, "Every question"):
            self.service.finalize_session(
                student_id="student-a", session_id=self.session["sessionId"], now=NOW,
            )

    def test_complete_session_finalizes_exactly_once_with_ordered_lineage(self) -> None:
        self._submit_all()
        first = self.service.finalize_session(
            student_id="student-a", session_id=self.session["sessionId"], now=NOW,
        )
        retry = self.service.finalize_session(
            student_id="student-a", session_id=self.session["sessionId"], now=NOW,
        )
        self.assertEqual(first, retry)
        self.assertEqual(1, len(self.service.attempts))
        attempt = next(iter(self.service.attempts.values()))
        self.assertEqual(5, len(attempt["responseIds"]))
        self.assertEqual(["q0", "q1", "q2", "q3", "q4"], self.session["questionIds"])
        self.assertNotIn("correctOptionIndex", attempt)
        self.assertNotIn("earnedCrystals", attempt)

        trusted_attempt = FinalizedQuizAttemptRecord.from_firestore(
            attempt["attemptId"], attempt,
        )
        trusted_responses = [
            ValidatedResponseRecord.from_firestore(response_id, response)
            for response_id, response in self.service.responses.items()
        ]
        validate_response_lineage(trusted_attempt, trusted_responses)

    def test_expired_complete_session_cannot_finalize(self) -> None:
        self._submit_all()
        with self.assertRaisesRegex(QuizSessionError, "session expired"):
            self.service.finalize_session(
                student_id="student-a",
                session_id=self.session["sessionId"],
                now=NOW + timedelta(minutes=31),
            )
        self.assertEqual("expired", self.service.sessions[self.session["sessionId"]]["status"])

    def test_foreign_student_cannot_finalize(self) -> None:
        self._submit_all()
        with self.assertRaisesRegex(QuizSessionError, "another student"):
            self.service.finalize_session(
                student_id="student-b", session_id=self.session["sessionId"], now=NOW,
            )


if __name__ == "__main__":
    unittest.main()
