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
        self.assertEqual(1, attempt["sourceAttemptSequence"])
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

    def test_sequence_is_monotonic_per_student_subtopic_and_duplicate_finalization_preserves_it(self) -> None:
        self._submit_all()
        first = self.service.finalize_session(
            student_id="student-a", session_id=self.session["sessionId"], now=NOW,
        )
        self.assertEqual(first, self.service.finalize_session(
            student_id="student-a", session_id=self.session["sessionId"], now=NOW,
        ))

        next_session = self.service.start_session(
            student_id="student-a", topic_id="y4_whole_numbers",
            subtopic_id="read_write_numbers", year_level=4, now=NOW,
        )
        for index, question_id in enumerate(next_session["questionIds"]):
            self.service.submit_response(
                student_id="student-a", session_id=next_session["sessionId"], question_id=question_id,
                selected_index=index % 4, sequence_index=index, response_time_ms=500,
                hint_count=99, idempotency_key=f"next-{index}", now=NOW,
            )
        self.service.finalize_session(student_id="student-a", session_id=next_session["sessionId"], now=NOW)
        attempts = list(self.service.attempts.values())
        self.assertEqual([1, 2], [item["sourceAttemptSequence"] for item in attempts])

    def test_sequence_is_independent_for_a_different_subtopic(self) -> None:
        for index in range(5):
            original = dict(self.service._questions[f"q{index}"])
            original.update({
                "questionId": f"place_q{index}",
                "bankId": "bank_place_value_v1",
                "subtopicId": "place_value",
            })
            self.service._questions[original["questionId"]] = original
            self.service._answer_keys[original["questionId"]] = {
                "correctOptionIndex": index % 4,
                "explanation": "Server feedback",
                "explanationBm": "Maklum balas pelayan",
            }

        self._submit_all()
        self.service.finalize_session(
            student_id="student-a", session_id=self.session["sessionId"], now=NOW,
        )
        other = self.service.start_session(
            student_id="student-a", topic_id="y4_whole_numbers",
            subtopic_id="place_value", year_level=4, now=NOW,
        )
        for index, question_id in enumerate(other["questionIds"]):
            self.service.submit_response(
                student_id="student-a", session_id=other["sessionId"], question_id=question_id,
                selected_index=index % 4, sequence_index=index, response_time_ms=500,
                hint_count=0, idempotency_key=f"place-{index}", now=NOW,
            )
        self.service.finalize_session(student_id="student-a", session_id=other["sessionId"], now=NOW)
        attempts = list(self.service.attempts.values())
        self.assertEqual([1, 1], [item["sourceAttemptSequence"] for item in attempts])

    def test_response_telemetry_is_bounded_and_server_owned(self) -> None:
        with self.assertRaisesRegex(QuizSessionError, "responseTimeMs"):
            self.service.submit_response(
                student_id="student-a", session_id=self.session["sessionId"], question_id="q0",
                selected_index=0, sequence_index=0, response_time_ms=900_001,
                hint_count=0, idempotency_key="too-slow", now=NOW,
            )
        response = self.service.submit_response(
            student_id="student-a", session_id=self.session["sessionId"], question_id="q0",
            selected_index=0, sequence_index=0, response_time_ms=0,
            hint_count=999, idempotency_key="server-owned", now=NOW,
        )
        sealed = self.service.responses[response["responseId"]]
        self.assertEqual(0, sealed["hintCount"])
        self.assertEqual("client_reported_unverified", sealed["responseTimeQuality"])
        self.assertEqual("not_supported", sealed["hintTelemetryStatus"])

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
