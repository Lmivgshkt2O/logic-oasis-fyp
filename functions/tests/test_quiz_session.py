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
        "questionType": f"Type {index}", "questionTypeBm": f"Jenis {index}",
    }


def feedback_for(correct_index: int) -> dict:
    """Authored bilingual feedback for every wrong option of a four-option item."""
    result = {}
    for index in range(4):
        if index == correct_index:
            continue
        result[str(index)] = {
            "misconceptionCode": f"misconception_{index}",
            "hint": f"Hint for option {index}.",
            "hintBm": f"Petunjuk untuk pilihan {index}.",
            "example": f"In 43 007, the 43 shows 43 thousands.",
            "exampleBm": f"Dalam 43 007, angka 43 menunjukkan 43 ribu.",
            "reviewFocus": f"Focus on option {index}.",
            "reviewFocusBm": f"Fokus pada pilihan {index}.",
        }
    return result


def service() -> InMemoryQuizSessionService:
    questions = [question(index) for index in range(6)]
    answer_keys = {
        item["questionId"]: {
            "correctOptionIndex": index % 4,
            "explanation": "Server feedback",
            "explanationBm": "Maklum balas pelayan",
            "feedbackByOption": feedback_for(index % 4),
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
        self.assertNotIn("feedbackByOption", self.session["questions"][0])

    def test_valid_response_is_stored_once_with_trusted_feedback(self) -> None:
        response = self.submit()
        self.assertTrue(response["serverIsCorrect"])
        self.assertEqual("validated", response["validationStatus"])
        self.assertEqual("Correct. Your answer was securely checked.", response["positiveConfirmation"])
        self.assertNotIn("feedbackHint", response)
        self.assertNotIn("reviewFocus", response)
        self.assertEqual(1, len(self.service.responses))

    def test_wrong_answer_returns_only_the_selected_options_authored_hint(self) -> None:
        response = self.submit(selected_index=1)
        self.assertFalse(response["serverIsCorrect"])
        self.assertEqual("Hint for option 1.", response["feedbackHint"])
        self.assertEqual("Petunjuk untuk pilihan 1.", response["feedbackHintBm"])
        self.assertEqual("In 43 007, the 43 shows 43 thousands.", response["feedbackExample"])
        self.assertEqual("Dalam 43 007, angka 43 menunjukkan 43 ribu.", response["feedbackExampleBm"])
        self.assertEqual("Focus on option 1.", response["reviewFocus"])
        self.assertEqual("Fokus pada pilihan 1.", response["reviewFocusBm"])
        self.assertNotIn("explanation", response)
        self.assertNotIn("positiveConfirmation", response)
        self.assertNotIn("misconceptionCode", response)

    def test_two_different_wrong_options_return_different_authored_hints(self) -> None:
        first = self.submit(selected_index=1)
        second_session = self.service.start_session(
            student_id="student-a", topic_id="y4_whole_numbers",
            subtopic_id="read_write_numbers", year_level=4, now=NOW,
        )
        second = self.service.submit_response(
            student_id="student-a", session_id=second_session["sessionId"],
            question_id="q0", selected_index=2, sequence_index=0,
            response_time_ms=500, hint_count=0, idempotency_key="second-option",
            now=NOW,
        )
        self.assertNotEqual(first["feedbackHint"], second["feedbackHint"])
        self.assertNotEqual(first["reviewFocus"], second["reviewFocus"])
        self.assertNotEqual(first["feedbackHintBm"], second["feedbackHintBm"])

    def test_invalid_or_answer_revealing_feedback_blocks_session_start(self) -> None:
        self.service._answer_keys["q0"]["feedbackByOption"] = {}
        with self.assertRaisesRegex(QuizSessionError, "quiz feedback is invalid"):
            self.service.start_session(
                student_id="student-b", topic_id="y4_whole_numbers",
                subtopic_id="read_write_numbers", year_level=4, now=NOW,
            )

        self.service._answer_keys["q0"]["feedbackByOption"] = feedback_for(1)
        self.service._answer_keys["q0"]["correctOptionIndex"] = 1
        self.service._answer_keys["q0"]["feedbackByOption"]["2"]["hint"] = "The answer is b."
        with self.assertRaisesRegex(QuizSessionError, "feedback reveals"):
            self.service.start_session(
                student_id="student-b", topic_id="y4_whole_numbers",
                subtopic_id="read_write_numbers", year_level=4, now=NOW,
            )

    def test_malformed_option_feedback_fails_closed_before_response_is_written(self) -> None:
        self.service._answer_keys["q0"]["feedbackByOption"]["1"]["reviewFocusBm"] = ""
        with self.assertRaisesRegex(QuizSessionError, "quiz feedback is invalid"):
            self.submit(selected_index=1)
        self.assertEqual(0, len(self.service.responses))

    def test_example_reusing_live_values_fails_closed(self) -> None:
        self.service._questions["q0"]["options"] = ["a", "b", "c", "20 004"]
        self.service._questions["q0"]["optionsBm"] = ["a", "b", "c", "20 004"]
        self.service._answer_keys["q0"]["feedbackByOption"]["1"]["example"] = (
            "Compare 20 004 with 21 004 to check the thousands group."
        )
        self.service._answer_keys["q0"]["feedbackByOption"]["1"]["exampleBm"] = (
            "Bandingkan 20 004 dengan 21 004 untuk menyemak kumpulan ribu."
        )
        with self.assertRaisesRegex(QuizSessionError, "reuses live question values"):
            self.submit(selected_index=1)
        self.assertEqual(0, len(self.service.responses))

    def test_rejects_out_of_range_answer_key(self) -> None:
        self.service._answer_keys["q0"]["correctOptionIndex"] = 4
        with self.assertRaisesRegex(QuizSessionError, "answer key is invalid"):
            self.submit()

    def test_same_idempotent_request_returns_the_sealed_response(self) -> None:
        first = self.submit(selected_index=1)
        retry = self.submit(selected_index=1)
        self.assertEqual(first, retry)
        self.assertEqual(1, len(self.service.responses))

    def test_second_response_for_a_sealed_question_is_rejected(self) -> None:
        self.submit()
        with self.assertRaisesRegex(QuizSessionError, "already sealed"):
            self.submit(selected_index=1, idempotency_key="different-request")

    def test_completion_returns_only_missed_questions_in_order_with_review_metadata(self) -> None:
        # q0 correct (index 0), q1 wrong, q2 wrong, q3 correct, q4 wrong.
        for index, question_id in enumerate(self.session["questionIds"]):
            selected_index = index % 4 if index in (0, 3) else (index + 1) % 4
            self.service.submit_response(
                student_id="student-a", session_id=self.session["sessionId"],
                question_id=question_id, selected_index=selected_index,
                sequence_index=index, response_time_ms=500, hint_count=0,
                idempotency_key=f"response-{index}", now=NOW,
            )
        completion = self.service.finalize_session(
            student_id="student-a", session_id=self.session["sessionId"], now=NOW,
        )
        self.assertEqual(2, completion["correctCount"])
        self.assertEqual(3, len(completion["reviewItems"]))
        missed = [
            self.session["questionIds"][index]
            for index in (1, 2, 4)
        ]
        self.assertEqual(
            missed,
            [item["questionId"] for item in completion["reviewItems"]],
        )
        self.assertEqual(
            [1, 2, 4],
            [item["sequenceIndex"] for item in completion["reviewItems"]],
        )
        for index, item in zip((1, 2, 4), completion["reviewItems"]):
            self.assertEqual(f"Question {index}", item["questionText"])
            self.assertEqual(f"Soalan {index}", item["questionTextBm"])
            self.assertEqual(f"Type {index}", item["questionType"])
            self.assertEqual(f"Jenis {index}", item["questionTypeBm"])
            self.assertEqual(
                f"Focus on option {(index + 1) % 4}.",
                item["reviewFocus"],
            )
            self.assertEqual(
                f"Fokus pada pilihan {(index + 1) % 4}.",
                item["reviewFocusBm"],
            )

    def test_perfect_score_returns_no_review_items(self) -> None:
        for index, question_id in enumerate(self.session["questionIds"]):
            correct_index = self.service._answer_keys[question_id]["correctOptionIndex"]
            self.service.submit_response(
                student_id="student-a", session_id=self.session["sessionId"],
                question_id=question_id, selected_index=correct_index,
                sequence_index=index, response_time_ms=500, hint_count=0,
                idempotency_key=f"perfect-{index}", now=NOW,
            )
        completion = self.service.finalize_session(
            student_id="student-a", session_id=self.session["sessionId"], now=NOW,
        )
        self.assertEqual(5, completion["correctCount"])
        self.assertEqual([], completion["reviewItems"])

    def test_payloads_never_expose_answer_data(self) -> None:
        client_payloads = []
        for index, question_id in enumerate(self.session["questionIds"]):
            client_payloads.append(self.service.submit_response(
                student_id="student-a", session_id=self.session["sessionId"],
                question_id=question_id, selected_index=1,
                sequence_index=index, response_time_ms=500, hint_count=0,
                idempotency_key=f"payload-{index}", now=NOW,
            ))
        completion = self.service.finalize_session(
            student_id="student-a", session_id=self.session["sessionId"], now=NOW,
        )
        serialized = repr([*client_payloads, completion])
        for forbidden in (
            "answerIndex", "correctOptionIndex", "explanation",
            "feedbackByOption", "sourceMaterialId", "contentSourceManifest",
            "misconceptionCode", "'options'",
        ):
            self.assertNotIn(forbidden, serialized)
        for item in completion["reviewItems"]:
            self.assertNotIn("options", item)
            self.assertNotIn("answerIndex", item)

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
