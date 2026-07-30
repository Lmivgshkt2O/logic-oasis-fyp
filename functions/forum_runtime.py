"""Server-owned U10 forum AI and count-only Mutual Aid runtime."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from firebase_admin import firestore
from logic_oasis_ai.forum_ai.classifier import (
    ForumTextClassifier, REVISION, SUFFICIENT, UNCERTAIN,
)

FORUM_RUNTIME_SERVICE_ACCOUNT = "logic-oasis-forum-runtime@logic-oasis-fyp.iam.gserviceaccount.com"
FORUM_MODEL_PATH = Path(__file__).resolve().parent / "forum_model.joblib"
KUALA_LUMPUR = ZoneInfo("Asia/Kuala_Lumpur")
COUNTER_FIELDS = ("questionsPostedCount", "answersSubmittedCount", "acceptedAnswersCount", "helpfulReceivedCount")


class ForumRuntimeError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _as_datetime(value: Any) -> datetime:
    if hasattr(value, "to_datetime"):
        value = value.to_datetime()
    if not isinstance(value, datetime):
        raise ForumRuntimeError("failed-precondition", "Forum event is missing its server timestamp.")
    return value if value.tzinfo else value.replace(tzinfo=KUALA_LUMPUR)


def malaysia_week_start(value: Any) -> datetime:
    local = _as_datetime(value).astimezone(KUALA_LUMPUR)
    monday = (local - timedelta(days=local.weekday())).date()
    return datetime(monday.year, monday.month, monday.day, tzinfo=KUALA_LUMPUR)


def feedback_for(label: str) -> str:
    if label == SUFFICIENT:
        return "Thanks for explaining your method. Your peer can now follow the reasoning."
    if label == REVISION:
        return "Please add the steps or mathematical reason behind your answer so a peer can learn from it."
    return "Your answer is saved. You can add a little more about how you reached it if you wish."


class ForumRuntimeGateway:
    """Firestore adapter; raw jobs/runs are never a client read surface."""
    def __init__(self, database: Any) -> None:
        self.database = database

    def _record_participation(self, *, event_id: str, student_id: str, field: str, occurred_at: Any) -> None:
        if field not in COUNTER_FIELDS:
            raise ValueError("invalid forum counter")
        event_ref = self.database.collection("forumParticipationEvents").document(event_id)
        summary_ref = self.database.collection("forumParticipationSummaries").document(student_id)
        week_start = malaysia_week_start(occurred_at)

        @firestore.transactional
        def record(transaction: Any) -> None:
            if transaction.get(event_ref).exists:
                return
            summary = transaction.get(summary_ref)
            current = summary.to_dict() if summary.exists else {}
            current_week = current.get("weekStart")
            if current_week is not None:
                try:
                    same_week = malaysia_week_start(current_week) == week_start
                except ForumRuntimeError:
                    same_week = False
            else:
                same_week = False
            counts = {name: int(current.get(name, 0)) if same_week else 0 for name in COUNTER_FIELDS}
            counts[field] += 1
            transaction.set(event_ref, {
                "eventId": event_id, "studentId": student_id, "counter": field,
                "occurredAt": occurred_at, "weekStart": week_start,
            })
            transaction.set(summary_ref, {
                "studentId": student_id, "weekStart": week_start, **counts,
                "lastParticipationAt": occurred_at, "updatedAt": firestore.SERVER_TIMESTAMP,
            })
        record(self.database.transaction())

    def record_question(self, question_id: str, data: Mapping[str, Any]) -> None:
        self._record_participation(event_id=f"question:{question_id}", student_id=_required(data, "authorId"), field="questionsPostedCount", occurred_at=data.get("createdAt"))

    def record_answer(self, answer_id: str, data: Mapping[str, Any]) -> None:
        self._record_participation(event_id=f"answer:{answer_id}", student_id=_required(data, "authorId"), field="answersSubmittedCount", occurred_at=data.get("createdAt"))

    def mark_helpful(self, *, answer_id: str, actor_id: str, now: datetime) -> dict[str, Any]:
        answer_ref = self.database.collection("forumAnswers").document(answer_id)
        mark_ref = self.database.collection("forumHelpfulMarks").document(f"{answer_id}_{actor_id}")
        @firestore.transactional
        def mark(transaction: Any) -> dict[str, Any]:
            answer = transaction.get(answer_ref)
            if not answer.exists:
                raise ForumRuntimeError("not-found", "Answer not found.")
            answer_data = answer.to_dict()
            author_id = _required(answer_data, "authorId")
            if author_id == actor_id:
                raise ForumRuntimeError("failed-precondition", "You cannot mark your own answer helpful.")
            if transaction.get(mark_ref).exists:
                return {"alreadyMarked": True}
            transaction.set(mark_ref, {"answerId": answer_id, "studentId": actor_id, "createdAt": now})
            return {"alreadyMarked": False, "answerAuthorId": author_id}
        result = mark(self.database.transaction())
        if not result["alreadyMarked"]:
            self._record_participation(event_id=f"helpful:{answer_id}:{actor_id}", student_id=result["answerAuthorId"], field="helpfulReceivedCount", occurred_at=now)
        return result

    def accept_answer(self, *, answer_id: str, actor_id: str, now: datetime) -> dict[str, Any]:
        answer_ref = self.database.collection("forumAnswers").document(answer_id)
        @firestore.transactional
        def accept(transaction: Any) -> dict[str, Any]:
            answer = transaction.get(answer_ref)
            if not answer.exists:
                raise ForumRuntimeError("not-found", "Answer not found.")
            data = answer.to_dict()
            question_id, author_id = _required(data, "questionId"), _required(data, "authorId")
            question_ref = self.database.collection("forumQuestions").document(question_id)
            question = transaction.get(question_ref)
            if not question.exists or _required(question.to_dict(), "authorId") != actor_id:
                raise ForumRuntimeError("permission-denied", "Only the question author may accept an answer.")
            if author_id == actor_id:
                raise ForumRuntimeError("failed-precondition", "You cannot accept your own answer.")
            if data.get("acceptedAt") is not None:
                return {"alreadyAccepted": True}
            transaction.update(answer_ref, {"acceptedAt": now, "acceptedBy": actor_id})
            return {"alreadyAccepted": False, "answerAuthorId": author_id}
        result = accept(self.database.transaction())
        if not result["alreadyAccepted"]:
            self._record_participation(event_id=f"accept:{answer_id}", student_id=result["answerAuthorId"], field="acceptedAnswersCount", occurred_at=now)
        return result

    def process_answer(self, answer_id: str, data: Mapping[str, Any], classifier: ForumTextClassifier | None) -> str:
        answer_ref = self.database.collection("forumAnswers").document(answer_id)
        job_ref = self.database.collection("forumAiJobs").document(answer_id)
        run_ref = self.database.collection("forumAiRuns").document(answer_id)
        existing = job_ref.get()
        if existing.exists and (existing.to_dict() or {}).get("state") in {"completed", "fallback", "failed"}:
            return str(existing.to_dict()["state"])
        # A retry may arrive after the immutable run committed but before the
        # job's terminal state did. Recover that deterministic result instead
        # of trying to create a second run.
        existing_run = run_ref.get()
        if existing_run.exists and isinstance((existing_run.to_dict() or {}).get("state"), str):
            state = existing_run.to_dict()["state"]
            job_ref.set({"answerId": answer_id, "state": state, "updatedAt": firestore.SERVER_TIMESTAMP}, merge=True)
            return state
        job_ref.set({"answerId": answer_id, "state": "processing", "updatedAt": firestore.SERVER_TIMESTAMP}, merge=True)
        try:
            if classifier is None:
                state, prediction = "fallback", None
            else:
                prediction = classifier.predict(_required(data, "text"))
                state = "completed"
            safe_feedback = feedback_for(prediction.label) if prediction else feedback_for(UNCERTAIN)
            answer_ref.set({"aiFeedback": {
                "state": state, "label": prediction.label if prediction else UNCERTAIN,
                "probability": prediction.probability if prediction else None,
                "modelVersion": prediction.model_version if prediction else None,
                "calibrationState": prediction.calibration_state if prediction else "unavailable",
                "message": safe_feedback, "updatedAt": firestore.SERVER_TIMESTAMP,
            }}, merge=True)
            run_ref.create({"answerId": answer_id, "state": state, "prediction": asdict(prediction) if prediction else None, "createdAt": firestore.SERVER_TIMESTAMP})
            job_ref.set({"answerId": answer_id, "state": state, "updatedAt": firestore.SERVER_TIMESTAMP}, merge=True)
            return state
        except Exception as error:
            job_ref.set({"answerId": answer_id, "state": "failed", "errorCode": type(error).__name__, "updatedAt": firestore.SERVER_TIMESTAMP}, merge=True)
            return "failed"


def load_forum_classifier(path: Path = FORUM_MODEL_PATH) -> ForumTextClassifier | None:
    try:
        return ForumTextClassifier.load(path) if path.is_file() else None
    except Exception:
        return None


def _required(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ForumRuntimeError("failed-precondition", f"Forum {key} is missing.")
    return value.strip()
