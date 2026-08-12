"""Server-authoritative quiz-session domain logic.

The callable handlers use this module for the rules that must be identical in
production and in focused tests: a student can submit each expected question
once, responses are ordered, and only a complete session can create an
attempt.  Correct-answer keys never leave this module's server boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re
from typing import Any
from uuid import uuid4


class QuizSessionError(ValueError):
    """A safe, caller-facing quiz session error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class QuizSessionPolicy:
    question_count: int = 5
    expiry_minutes: int = 30


MAX_RESPONSE_TIME_MS = 900_000
CLIENT_REPORTED_UNVERIFIED = "client_reported_unverified"
HINT_TELEMETRY_NOT_SUPPORTED = "not_supported"
POSITIVE_CONFIRMATION = "Correct. Your answer was securely checked."
POSITIVE_CONFIRMATION_BM = "Betul. Jawapan anda telah disemak dengan selamat."


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def response_document_id(session_id: str, sequence_index: int) -> str:
    """Stable response ID: retries always address the same sealed response."""
    return sha256(f"{session_id}:{sequence_index}".encode()).hexdigest()[:32]


def client_question(question: dict[str, Any]) -> dict[str, Any]:
    """Return only prompt fields; never copy answer keys into a response."""
    allowed = (
        "questionId",
        "bankId",
        "topicId",
        "subtopicId",
        "skillId",
        "yearLevel",
        "difficultyLevel",
        "estimatedDifficulty",
        "contentVersion",
        "language",
        "createdAt",
        "questionText",
        "questionTextBm",
        "options",
        "optionsBm",
        "sourceReference",
        "order",
        "bloomLevel",
    )
    return {key: question[key] for key in allowed if key in question}


def client_session(
    session: dict[str, Any], questions: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return the session payload without trusted server-only fields."""
    return {
        key: session[key]
        for key in (
            "sessionId", "attemptId", "assignmentId", "assignmentSource", "bankId",
            "topicId", "subtopicId", "yearLevel", "difficultyLevel", "contentVersion",
            "questionIds", "status",
        )
    } | {"questions": [client_question(question) for question in questions]}


def client_response(response: dict[str, Any]) -> dict[str, Any]:
    """Return trusted feedback only after the server validates a response."""
    return {
        key: response[key]
        for key in (
            "responseId", "sessionId", "attemptId", "questionId", "selectedIndex",
            "serverIsCorrect", "positiveConfirmation", "positiveConfirmationBm",
            "feedbackHint", "feedbackHintBm", "feedbackExample",
            "feedbackExampleBm", "reviewFocus", "reviewFocusBm",
            "validationStatus",
            "sequenceIndex",
        )
        if key in response
    }


def client_completion(attempt: dict[str, Any]) -> dict[str, Any]:
    """Return the finalized attempt summary that the client may display."""
    return {
        key: attempt[key]
        for key in (
            "attemptId", "sessionId", "correctCount", "totalQuestions", "score",
            "finalizationStatus", "reviewItems",
        )
        if key in attempt
    }


class InMemoryQuizSessionService:
    """Deterministic store used by focused tests and emulator-independent QA."""

    def __init__(
        self,
        questions: list[dict[str, Any]],
        answer_keys: dict[str, dict[str, Any]],
        policy: QuizSessionPolicy = QuizSessionPolicy(),
    ) -> None:
        self._questions = {question["questionId"]: question for question in questions}
        self._answer_keys = answer_keys
        self._policy = policy
        self.sessions: dict[str, dict[str, Any]] = {}
        self.responses: dict[str, dict[str, Any]] = {}
        self.attempts: dict[str, dict[str, Any]] = {}
        self.sequence_states: dict[tuple[str, str], int] = {}

    def start_session(
        self,
        *,
        student_id: str,
        topic_id: str,
        subtopic_id: str,
        year_level: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or utc_now()
        candidates = [
            question
            for question in self._questions.values()
            if question.get("topicId") == topic_id
            and question.get("subtopicId") == subtopic_id
            and question.get("yearLevel") == year_level
            and question.get("difficultyLevel") == "Easy"
        ]
        candidates.sort(key=lambda item: (item.get("order", 0), item["questionId"]))
        if len(candidates) < self._policy.question_count:
            raise QuizSessionError("failed-precondition", "No complete active question bank is available.")

        selected = candidates[: self._policy.question_count]
        for question in selected:
            answer_key = self._answer_keys.get(question["questionId"])
            if answer_key is None:
                raise QuizSessionError("failed-precondition", "The answer key is unavailable.")
            validate_answer_key_feedback(
                answer_key, question.get("options"), question.get("optionsBm")
            )
        skill_ids = {question.get("skillId") for question in selected}
        if None in skill_ids or len(skill_ids) != 1:
            raise QuizSessionError(
                "failed-precondition", "A quiz session must contain one skill.")
        session_id = f"session_{uuid4().hex}"
        attempt_id = f"attempt_{uuid4().hex}"
        session = {
            "sessionId": session_id,
            "attemptId": attempt_id,
            "studentId": student_id,
            "assignmentId": "cold_start_easy",
            "assignmentSource": "cold_start_easy",
            "adaptivePolicyVersion": "adaptive-policy-v1",
            "bankId": selected[0]["bankId"],
            "topicId": topic_id,
            "subtopicId": subtopic_id,
            "yearLevel": year_level,
            "difficultyLevel": "Easy",
            "contentVersion": selected[0]["contentVersion"],
            "questionIds": [question["questionId"] for question in selected],
            "expectedResponseCount": len(selected),
            "status": "active",
            "validatedResponseCount": 0,
            "startedAt": now,
            "expiresAt": now + timedelta(minutes=self._policy.expiry_minutes),
            "finalizedAt": None,
        }
        self.sessions[session_id] = session
        return self._client_session(session, selected)

    def submit_response(
        self,
        *,
        student_id: str,
        session_id: str,
        question_id: str,
        selected_index: int,
        sequence_index: int,
        response_time_ms: int,
        hint_count: int,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or utc_now()
        session = self._owned_active_session(student_id, session_id, now)
        self._validate_expected_question(session, question_id, sequence_index)
        if not isinstance(selected_index, int) or selected_index < 0:
            raise QuizSessionError("invalid-argument", "The selected option is invalid.")
        if (
            isinstance(response_time_ms, bool)
            or not isinstance(response_time_ms, int)
            or response_time_ms < 0
            or response_time_ms > MAX_RESPONSE_TIME_MS
        ):
            raise QuizSessionError(
                "invalid-argument",
                f"responseTimeMs must be between 0 and {MAX_RESPONSE_TIME_MS}.",
            )
        if not idempotency_key:
            raise QuizSessionError("invalid-argument", "A response idempotency key is required.")

        response_id = response_document_id(session_id, sequence_index)
        existing = self.responses.get(response_id)
        if existing is not None:
            same_request = (
                existing["idempotencyKey"] == idempotency_key
                and existing["selectedIndex"] == selected_index
                and existing["questionId"] == question_id
            )
            if same_request:
                return self._client_response(existing)
            raise QuizSessionError("already-exists", "This question response is already sealed.")

        if sequence_index > 0:
            previous_response_id = response_document_id(session_id, sequence_index - 1)
            if previous_response_id not in self.responses:
                raise QuizSessionError(
                    "failed-precondition", "Submit quiz responses in sequence."
                )

        question = self._questions[question_id]
        if question.get("contentVersion") != session["contentVersion"]:
            raise QuizSessionError("failed-precondition", "The quiz content changed. Start a new quiz.")
        options = question.get("options", [])
        if selected_index >= len(options):
            raise QuizSessionError("invalid-argument", "The selected option is invalid.")
        answer_key = self._answer_keys.get(question_id)
        if answer_key is None:
            raise QuizSessionError("failed-precondition", "The answer key is unavailable.")
        answer_index = _answer_index(answer_key)
        if answer_index < 0 or answer_index >= len(options):
            raise QuizSessionError("failed-precondition", "The quiz answer key is invalid.")

        is_correct = selected_index == answer_index
        response = {
            "responseId": response_id,
            "sessionId": session_id,
            "attemptId": session["attemptId"],
            "studentId": student_id,
            "questionId": question_id,
            "skillId": question["skillId"],
            "bankId": session["bankId"],
            "questionVersion": question["contentVersion"],
            "contentVersion": session["contentVersion"],
            "priorExposureCount": question.get("priorExposureCount"),
            "selectedIndex": selected_index,
            "serverIsCorrect": is_correct,
            "validationStatus": "validated",
            "responseTimeMs": response_time_ms,
            "responseTimeQuality": CLIENT_REPORTED_UNVERIFIED,
            # Keep the parameter only for older test/client call sites. It is
            # deliberately ignored because FYP1 does not collect hints.
            "hintCount": 0,
            "hintTelemetryStatus": HINT_TELEMETRY_NOT_SUPPORTED,
            "sequenceIndex": sequence_index,
            "idempotencyKey": idempotency_key,
            "createdAt": now,
        }
        if is_correct:
            response.update({
                "positiveConfirmation": POSITIVE_CONFIRMATION,
                "positiveConfirmationBm": POSITIVE_CONFIRMATION_BM,
            })
        else:
            feedback = validated_option_feedback(
                answer_key, selected_index, options, question.get("optionsBm")
            )
            response.update({
                "misconceptionCode": feedback["misconceptionCode"],
                "feedbackHint": feedback["hint"],
                "feedbackHintBm": feedback["hintBm"],
                "feedbackExample": feedback["example"],
                "feedbackExampleBm": feedback["exampleBm"],
                "reviewFocus": feedback["reviewFocus"],
                "reviewFocusBm": feedback["reviewFocusBm"],
            })
        self.responses[response_id] = response
        session["validatedResponseCount"] += 1
        return self._client_response(response)

    def finalize_session(
        self, *, student_id: str, session_id: str, now: datetime | None = None
    ) -> dict[str, Any]:
        now = now or utc_now()
        session = self.sessions.get(session_id)
        if session is None:
            raise QuizSessionError("not-found", "Quiz session not found.")
        if session["studentId"] != student_id:
            raise QuizSessionError("permission-denied", "This quiz session belongs to another student.")
        if session["status"] == "finalized":
            return self._client_completion(self.attempts[session["attemptId"]])
        self._owned_active_session(student_id, session_id, now)
        expected = len(session["questionIds"])
        if (
            session.get("expectedResponseCount") != expected
            or session["validatedResponseCount"] != expected
        ):
            raise QuizSessionError("failed-precondition", "Every question must be securely checked first.")
        ordered = [
            self.responses[response_document_id(session_id, index)]
            for index in range(expected)
        ]
        if any(item["validationStatus"] != "validated" for item in ordered):
            raise QuizSessionError("failed-precondition", "Every response must be validated.")
        correct_count = sum(1 for item in ordered if item["serverIsCorrect"])
        total = len(ordered)
        review_items: list[dict[str, Any]] = []
        for item in ordered:
            if item["serverIsCorrect"]:
                continue
            question = self._questions[item["questionId"]]
            review_focus = item.get("reviewFocus")
            review_focus_bm = item.get("reviewFocusBm")
            if (
                not isinstance(review_focus, str)
                or not review_focus.strip()
                or not isinstance(review_focus_bm, str)
                or not review_focus_bm.strip()
            ):
                raise QuizSessionError(
                    "failed-precondition",
                    "A missed question is missing its review focus.",
                )
            review_items.append({
                "questionId": item["questionId"],
                "sequenceIndex": item["sequenceIndex"],
                "questionText": question.get("questionText", ""),
                "questionTextBm": question.get("questionTextBm", ""),
                "questionType": question.get("questionType", ""),
                "questionTypeBm": question.get("questionTypeBm", ""),
                "reviewFocus": review_focus,
                "reviewFocusBm": review_focus_bm,
            })
        sequence_key = (student_id, session["subtopicId"])
        source_attempt_sequence = self.sequence_states.get(sequence_key, 0) + 1
        attempt = {
            "attemptId": session["attemptId"],
            "sessionId": session_id,
            "studentId": student_id,
            "topicId": session["topicId"],
            "subtopicId": session["subtopicId"],
            "yearLevel": session["yearLevel"],
            "bankId": session["bankId"],
            "difficultyLevel": session["difficultyLevel"],
            "contentVersion": session["contentVersion"],
            "assignmentId": session["assignmentId"],
            "assignmentSource": session["assignmentSource"],
            "adaptivePolicyVersion": session["adaptivePolicyVersion"],
            "correctCount": correct_count,
            "totalQuestions": total,
            "score": round((correct_count / total) * 100),
            "trustedCorrectCount": correct_count,
            "trustedScore": round((correct_count / total) * 100),
            "responseCount": total,
            "responseIds": [item["responseId"] for item in ordered],
            "reviewItems": review_items,
            "validationStatus": "finalized",
            "finalizationStatus": "finalized",
            "processingStatus": "pending",
            "dataSource": "runtime_callable",
            "sourceAttemptSequence": source_attempt_sequence,
            "startedAt": session["startedAt"],
            "deviceSessionId": "not_recorded",
            "finalizedAt": now,
        }
        self.attempts[attempt["attemptId"]] = attempt
        self.sequence_states[sequence_key] = source_attempt_sequence
        session["status"] = "finalized"
        session["finalizedAt"] = now
        return self._client_completion(attempt)

    def _owned_active_session(
        self, student_id: str, session_id: str, now: datetime
    ) -> dict[str, Any]:
        session = self.sessions.get(session_id)
        if session is None:
            raise QuizSessionError("not-found", "Quiz session not found.")
        if session["studentId"] != student_id:
            raise QuizSessionError("permission-denied", "This quiz session belongs to another student.")
        if session["status"] != "active":
            raise QuizSessionError("failed-precondition", "Quiz session is not active.")
        if now >= session["expiresAt"]:
            session["status"] = "expired"
            raise QuizSessionError("deadline-exceeded", "Quiz session expired. Start a new quiz.")
        return session

    @staticmethod
    def _validate_expected_question(
        session: dict[str, Any], question_id: str, sequence_index: int
    ) -> None:
        question_ids = session["questionIds"]
        if sequence_index < 0 or sequence_index >= len(question_ids):
            raise QuizSessionError("invalid-argument", "The response sequence is invalid.")
        if question_ids[sequence_index] != question_id:
            raise QuizSessionError("failed-precondition", "Submit quiz responses in the assigned order.")

    def _client_session(
        self, session: dict[str, Any], questions: list[dict[str, Any]]) -> dict[str, Any]:
        return client_session(session, questions)

    @staticmethod
    def _client_response(response: dict[str, Any]) -> dict[str, Any]:
        return client_response(response)

    @staticmethod
    def _client_completion(attempt: dict[str, Any]) -> dict[str, Any]:
        return client_completion(attempt)


def _answer_index(answer_key: dict[str, Any]) -> int:
    """Accept the deployed U2 key name while keeping test fixtures explicit."""
    value = answer_key.get("correctOptionIndex", answer_key.get("answerIndex"))
    if isinstance(value, bool) or not isinstance(value, int):
        raise QuizSessionError("failed-precondition", "The answer key is invalid.")
    return value


def validate_answer_key_feedback(
    answer_key: dict[str, Any],
    options: Any,
    options_bm: Any,
) -> None:
    """Validate every wrong option has complete, safe authored feedback."""
    if not isinstance(options, list) or not isinstance(options_bm, list):
        raise QuizSessionError("failed-precondition", "The quiz feedback is invalid.")
    if len(options) != len(options_bm):
        raise QuizSessionError("failed-precondition", "The quiz feedback is invalid.")
    correct_index = _answer_index(answer_key)
    if correct_index < 0 or correct_index >= len(options):
        raise QuizSessionError("failed-precondition", "The quiz answer key is invalid.")
    feedback = answer_key.get("feedbackByOption")
    if not isinstance(feedback, dict):
        raise QuizSessionError("failed-precondition", "The quiz feedback is invalid.")
    for index in range(len(options)):
        if index == correct_index:
            continue
        validated_option_feedback(answer_key, index, options, options_bm)


def validated_option_feedback(
    answer_key: dict[str, Any],
    selected_index: int,
    options: Any,
    options_bm: Any,
) -> dict[str, Any]:
    """Return the authored, sealed feedback for one wrong option.

    The entry is held beside the server-only answer key and is projected only
    after an incorrect answer has been securely validated. Malformed or
    incomplete entries fail closed before any response is written.
    """
    feedback = answer_key.get("feedbackByOption")
    if not isinstance(feedback, dict):
        raise QuizSessionError("failed-precondition", "The quiz feedback is invalid.")
    entry = feedback.get(str(selected_index))
    if not isinstance(entry, dict):
        raise QuizSessionError("failed-precondition", "The quiz feedback is invalid.")
    hint = entry.get("hint")
    hint_bm = entry.get("hintBm")
    example = entry.get("example")
    example_bm = entry.get("exampleBm")
    review_focus = entry.get("reviewFocus")
    review_focus_bm = entry.get("reviewFocusBm")
    misconception_code = entry.get("misconceptionCode")
    if (
        not isinstance(hint, str)
        or not hint.strip()
        or not isinstance(hint_bm, str)
        or not hint_bm.strip()
        or not isinstance(review_focus, str)
        or not review_focus.strip()
        or not isinstance(review_focus_bm, str)
        or not review_focus_bm.strip()
        or not isinstance(misconception_code, str)
        or not misconception_code.strip()
        or (example is None) != (example_bm is None)
        or (
            example is not None
            and (
                not isinstance(example, str)
                or not example.strip()
                or not isinstance(example_bm, str)
                or not example_bm.strip()
            )
        )
    ):
        raise QuizSessionError("failed-precondition", "The quiz feedback is invalid.")

    _validate_feedback_safety(
        hint, hint_bm, example, example_bm, answer_key, options, options_bm
    )
    return {
        "misconceptionCode": misconception_code,
        "hint": hint,
        "hintBm": hint_bm,
        "example": example,
        "exampleBm": example_bm,
        "reviewFocus": review_focus,
        "reviewFocusBm": review_focus_bm,
    }


def _validate_feedback_safety(
    hint: str,
    hint_bm: str,
    example: str | None,
    example_bm: str | None,
    answer_key: dict[str, Any],
    options: Any,
    options_bm: Any,
) -> None:
    """Fail closed when feedback names the live answer or reuses live values."""
    if not isinstance(options, list) or not isinstance(options_bm, list):
        raise QuizSessionError("failed-precondition", "The quiz feedback is invalid.")
    correct_index = _answer_index(answer_key)
    if correct_index < 0 or correct_index >= len(options):
        raise QuizSessionError("failed-precondition", "The quiz answer key is invalid.")
    correct_options = tuple(
        option.strip().casefold()
        for option in (options[correct_index], options_bm[correct_index])
        if isinstance(option, str) and len(option.strip()) >= 2
    )
    revealing_phrases = (
        "the answer is", "correct answer", "answer:", "choose option",
        "jawapan ialah", "jawapan yang betul", "jawapan:", "pilih pilihan",
    )

    def check(text: str) -> None:
        normalized = re.sub(r"[^\w]+", " ", text.casefold()).strip()
        if any(phrase in normalized for phrase in revealing_phrases):
            raise QuizSessionError("failed-precondition", "The quiz feedback reveals an answer.")
        if any(
            normalized.strip() == option
            or f"{option} is correct" in normalized
            or f"{option} ialah jawapan" in normalized
            or f"{option} adalah jawapan" in normalized
            or (
                option in normalized
                and any(directive in normalized for directive in ("choose", "select", "pick", "pilih"))
            )
            for option in correct_options
        ):
            raise QuizSessionError("failed-precondition", "The quiz feedback reveals an answer.")

    for text in (hint, hint_bm):
        check(text)

    live_values = {
        token
        for value in [*options, *options_bm]
        if isinstance(value, str)
        for token in _numeric_tokens(value)
    }
    for example_text in (example, example_bm):
        if example_text is None:
            continue
        check(example_text)
        reused = [token for token in _numeric_tokens(example_text) if token in live_values]
        if reused:
            raise QuizSessionError(
                "failed-precondition",
                "The quiz example reuses live question values.",
            )


def _numeric_tokens(value: str) -> list[str]:
    """Return distinctive five-digit (or larger) values inside a string."""
    return [
        token.replace(" ", "")
        for token in re.findall(r"\d[\d\s,]*\d|\d", value)
        if len(token.replace(" ", "")) >= 5
    ]


