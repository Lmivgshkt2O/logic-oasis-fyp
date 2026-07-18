from datetime import datetime, timedelta, timezone
import unittest

from functions.quiz_session import InMemoryQuizSessionService, QuizSessionError


NOW = datetime(2026, 7, 15, tzinfo=timezone.utc)


def question(index: int) -> dict:
    return {
        "questionId": f"q{index}", "bankId": "bank_read_write_v1",
        "topicId": "y4_whole_numbers", "subtopicId": "read_write_numbers",
        "skillId": "read_write", "yearLevel": 4, "difficultyLevel": "Easy",
        "estimatedDifficulty": 0.2, "contentVersion": "v1", "language": "en",
        "createdAt": "2026-07-01T00:00:00Z", "questionText": f"Question {index}",
        "questionTextBm": f"Soalan {index}", "options": ["a", "b", "c", "d"],
        "optionsBm": ["a", "b", "c", "d"], "sourceReference": "KSSR", "order": index,
    }


def service() -> InMemoryQuizSessionService:
    questions = [question(index) for index in range(6)]
    answer_keys = {
        item["questionId"]: {
            "correctOptionIndex": index % 4,
            "explanation": "Server feedback",
            "explanationBm": "Maklum balas pelayan",
        }
        for index, item in enumerate(questions)
    }
    return InMemoryQuizSessionService(questions, answer_keys)


class QuizSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = service()
        self.session = self.service.start_session(
            student_id="student-a", topic_id="y4_whole_numbers",
            subtopic_id="read_write_numbers", year_level=4, now=NOW,
        )

    def submit(self, **overrides: object) -> dict:
        request = {
            "student_id": "student-a", "session_id": self.session["sessionId"],
            "question_id": "q0", "selected_index": 0, "sequence_index": 0,
            "response_time_ms": 1000, "hint_count": 0, "idempotency_key": "first-response",
            "now": NOW,
        }
        request.update(overrides)
        return self.service.submit_response(**request)

    def test_start_returns_prompts_without_answer_keys(self) -> None:
        self.assertEqual(5, len(self.session["questions"]))
        self.assertNotIn("correctOptionIndex", self.session["questions"][0])
        self.assertNotIn("explanation", self.session["questions"][0])

    def test_valid_response_is_stored_once_with_trusted_feedback(self) -> None:
        response = self.submit()
        self.assertTrue(response["serverIsCorrect"])
        self.assertEqual("validated", response["validationStatus"])
        self.assertEqual(1, len(self.service.responses))

    def test_rejects_out_of_range_answer_key(self) -> None:
        self.service._answer_keys["q0"]["correctOptionIndex"] = 4
        with self.assertRaisesRegex(QuizSessionError, "answer key is invalid"):
            self.submit()

    def test_same_idempotent_request_returns_the_sealed_response(self) -> None:
        first = self.submit()
        retry = self.submit()
        self.assertEqual(first, retry)
        self.assertEqual(1, len(self.service.responses))

    def test_second_response_for_a_sealed_question_is_rejected(self) -> None:
        self.submit()
        with self.assertRaisesRegex(QuizSessionError, "already sealed"):
            self.submit(selected_index=1, idempotency_key="different-request")

    def test_foreign_student_out_of_order_and_expired_sessions_fail(self) -> None:
        with self.assertRaisesRegex(QuizSessionError, "another student"):
            self.submit(student_id="student-b")
        with self.assertRaisesRegex(QuizSessionError, "assigned order"):
            self.submit(question_id="q1", sequence_index=0)
        with self.assertRaisesRegex(QuizSessionError, "in sequence"):
            self.submit(question_id="q1", sequence_index=1)
        with self.assertRaisesRegex(QuizSessionError, "expired"):
            self.submit(now=NOW + timedelta(minutes=31))


if __name__ == "__main__":
    unittest.main()
