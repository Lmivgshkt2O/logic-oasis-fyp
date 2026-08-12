"""Server-owned U10 forum AI and count-only Mutual Aid runtime."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any, Mapping
from zoneinfo import ZoneInfo

from firebase_admin import firestore

if TYPE_CHECKING:
    from logic_oasis_ai.forum_ai.classifier import ForumTextClassifier
LOGGER = logging.getLogger(__name__)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")

FORUM_RUNTIME_SERVICE_ACCOUNT = "logic-oasis-forum-runtime@logic-oasis-fyp.iam.gserviceaccount.com"
FORUM_MODEL_PATH = Path(__file__).resolve().parent / "forum_model.joblib"
FORUM_MODEL_MANIFEST_PATH = Path(__file__).resolve().parent / "forum_model_manifest.json"
KUALA_LUMPUR = ZoneInfo("Asia/Kuala_Lumpur")
COUNTER_FIELDS = ("questionsPostedCount", "answersSubmittedCount", "acceptedAnswersCount", "helpfulReceivedCount")
FORUM_AI_POLICY_VERSION = "forum-advisory-policy-v1"
FORUM_AI_LEASE_DURATION = timedelta(minutes=5)
FORUM_AI_MAX_ATTEMPTS = 3
FORUM_RELEASE_MANIFEST_SCHEMA = "forum-model-release-manifest-v1"
FORUM_CONTROLLED_MODE = "controlled_demo"
FORUM_REAL_EVALUATED_MODE = "real_evaluated_only"
FORUM_CONTROLLED_CLAIM_LEVEL = "controlled_demonstration_only"
FORUM_UNVALIDATED_CLAIM_LEVEL = "unvalidated_model_output"
FORUM_FALLBACK_CLAIM_LEVEL = "safe_fallback_only"
_SHA256_FIELDS = (
    "artifactSha256", "catalogueSha256", "datasetSha256", "datasetManifestSha256",
    "splitManifestSha256", "rubricSha256", "evaluationReportSha256",
    "candidateManifestSha256", "bundleManifestSha256",
)
_CONTROLLED_RELEASE_VALUES = {
    "lifecycleStatus": "released", "isActive": True,
    "trainingDataProvenance": "expert_authored_controlled_demo",
    "evidenceLevel": "controlled_demonstration",
    "releaseScope": "fyp1_forum_controlled_demo",
    "deploymentScope": "controlled_demo",
    "claimLevel": FORUM_CONTROLLED_CLAIM_LEVEL,
}


@dataclass(frozen=True)
class ForumAiClaim:
    answer_id: str
    logical_inference_id: str
    revision: int
    text_hash: str
    model_version: str
    artifact_identity: str
    policy_version: str
    fencing_generation: int
    attempt_count: int
    event_id: str
    claim_level: str = FORUM_UNVALIDATED_CLAIM_LEVEL


class ForumRuntimeError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _document_id(value: str) -> str:
    if not value or "/" in value or len(value) > 1500:
        raise ForumRuntimeError("invalid-argument", "Forum document ID is invalid.")
    return value


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


def _latest_timestamp(existing: Any, candidate: Any) -> Any:
    if existing is None:
        return candidate
    try:
        return existing if _as_datetime(existing) >= _as_datetime(candidate) else candidate
    except ForumRuntimeError:
        return candidate


def feedback_for(label: str) -> str:
    from logic_oasis_ai.forum_ai.classifier import REVISION, SUFFICIENT

    if label == SUFFICIENT:
        return "Thanks for explaining your method. Your peer can now follow the reasoning."
    if label == REVISION:
        return "Please add the steps or mathematical reason behind your answer so a peer can learn from it."
    return "Your answer is saved. You can add a little more about how you reached it if you wish."


def _forum_text_hash(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return sha256(value.strip().encode("utf-8")).hexdigest()


def _feedback_payload(
    *, state: str, prediction: Any, revision: int, logical_inference_id: str,
) -> dict[str, Any]:
    from logic_oasis_ai.forum_ai.classifier import UNCERTAIN

    if isinstance(prediction, Mapping):
        label = prediction.get("label", UNCERTAIN)
        probability = prediction.get("probability")
        model_version = prediction.get("model_version")
        calibration_state = prediction.get("calibration_state", "unavailable")
    elif prediction is not None:
        label = prediction.label
        probability = prediction.probability
        model_version = prediction.model_version
        calibration_state = prediction.calibration_state
    else:
        label = UNCERTAIN
        probability = None
        model_version = None
        calibration_state = "unavailable"
    return {
        "state": state,
        "label": label,
        "probability": probability,
        "modelVersion": model_version,
        "calibrationState": calibration_state,
        "message": feedback_for(label),
        "revision": revision,
        "logicalInferenceId": logical_inference_id,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }


def _transaction_snapshot(transaction: Any, reference: Any) -> Any:
    """Normalise Admin SDK transaction reads across supported Python releases.

    Recent google-cloud-firestore versions return an iterator even for a single
    document reference; older versions and focused fakes return a snapshot.
    """
    value = transaction.get(reference)
    if hasattr(value, "exists"):
        return value
    return next(iter(value), None)


def _transaction_snapshots(transaction: Any, query: Any) -> list[Any]:
    value = transaction.get(query)
    if hasattr(value, "exists"):
        return [value]
    return list(value)


class ForumRuntimeGateway:
    """Firestore adapter; raw jobs/runs are never a client read surface."""
    def __init__(self, database: Any) -> None:
        self.database = database

    def _record_participation(self, *, event_id: str, student_id: str, field: str, occurred_at: Any) -> None:
        if field not in COUNTER_FIELDS:
            raise ValueError("invalid forum counter")
        event_ref = self.database.collection("forumParticipationEvents").document(event_id)
        aggregate_ref = self.database.collection(
            "forumParticipationAggregateClaims"
        ).document(event_id)

        @firestore.transactional
        def record(transaction: Any) -> None:
            event = _transaction_snapshot(transaction, event_ref) or _MissingSnapshot()
            aggregate = _transaction_snapshot(transaction, aggregate_ref) or _MissingSnapshot()
            if aggregate.exists:
                return
            source = event.to_dict() if event.exists else {
                "studentId": student_id, "counter": field, "occurredAt": occurred_at,
            }
            source_student_id = _required(source, "studentId")
            source_field = source.get("counter")
            if source_field not in COUNTER_FIELDS:
                raise ForumRuntimeError(
                    "failed-precondition", "Forum participation event counter is invalid.",
                )
            source_occurred_at = source.get("occurredAt")
            week_start = malaysia_week_start(source_occurred_at)
            summary_ref = self.database.collection(
                "forumParticipationSummaries"
            ).document(source_student_id)
            weekly_ref = self.database.collection(
                "forumParticipationWeeklySummaries"
            ).document(f"{source_student_id}_{week_start.date().isoformat()}")
            weekly = _transaction_snapshot(transaction, weekly_ref) or _MissingSnapshot()
            weekly_data = weekly.to_dict() if weekly.exists else {}
            weekly_counts = {
                name: int(weekly_data.get(name, 0)) for name in COUNTER_FIELDS
            }
            summary = _transaction_snapshot(transaction, summary_ref) or _MissingSnapshot()
            current = summary.to_dict() if summary.exists else {}
            current_week = current.get("weekStart")
            if current_week is not None:
                try:
                    current_week = malaysia_week_start(current_week)
                except ForumRuntimeError:
                    current_week = None
            # Bootstrap the historical aggregate from the pre-U3 current
            # projection so the first post-migration event cannot reset it.
            if not weekly.exists and current_week == week_start:
                weekly_counts = {
                    name: int(current.get(name, 0)) for name in COUNTER_FIELDS
                }
            bootstrapped_legacy_current_week = (
                event.exists and not weekly.exists and current_week == week_start
            )
            if not bootstrapped_legacy_current_week:
                weekly_counts[source_field] += 1
            weekly_last = _latest_timestamp(
                weekly_data.get("lastParticipationAt") or (
                    current.get("lastParticipationAt")
                    if bootstrapped_legacy_current_week else None
                ),
                source_occurred_at,
            )
            if not event.exists:
                transaction.set(event_ref, {
                    "eventId": event_id, "studentId": source_student_id,
                    "counter": source_field, "occurredAt": source_occurred_at,
                    "weekStart": week_start,
                })
            transaction.set(weekly_ref, {
                "studentId": source_student_id, "weekStart": week_start, **weekly_counts,
                "lastParticipationAt": weekly_last, "updatedAt": firestore.SERVER_TIMESTAMP,
            })
            # Historical repairs update their immutable week aggregate but may
            # never move the linked-parent current-week projection backwards.
            if current_week is None or week_start >= current_week:
                transaction.set(summary_ref, {
                    "studentId": source_student_id, "weekStart": week_start, **weekly_counts,
                    "lastParticipationAt": _latest_timestamp(
                        current.get("lastParticipationAt") if current_week == week_start else None,
                        weekly_last,
                    ),
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                })
            transaction.set(aggregate_ref, {
                "eventId": event_id,
                "studentId": source_student_id,
                "counter": source_field,
                "weekStart": week_start,
                "aggregatedAt": firestore.SERVER_TIMESTAMP,
            })
        record(self.database.transaction())

    def record_question(self, question_id: str, data: Mapping[str, Any]) -> None:
        self._record_participation(event_id=f"question:{question_id}", student_id=_required(data, "authorId"), field="questionsPostedCount", occurred_at=data.get("createdAt"))

    def record_answer(self, answer_id: str, data: Mapping[str, Any]) -> None:
        self._record_participation(event_id=f"answer:{answer_id}", student_id=_required(data, "authorId"), field="answersSubmittedCount", occurred_at=data.get("createdAt"))

    def mark_helpful(self, *, answer_id: str, actor_id: str, now: datetime) -> dict[str, Any]:
        answer_id = _document_id(answer_id)
        answer_ref = self.database.collection("forumAnswers").document(answer_id)
        mark_ref = self.database.collection("forumHelpfulMarks").document(f"{answer_id}_{actor_id}")
        @firestore.transactional
        def mark(transaction: Any) -> dict[str, Any]:
            answer = _transaction_snapshot(transaction, answer_ref) or _MissingSnapshot()
            if not answer.exists:
                raise ForumRuntimeError("not-found", "Answer not found.")
            answer_data = answer.to_dict()
            author_id = _required(answer_data, "authorId")
            if author_id == actor_id:
                raise ForumRuntimeError("failed-precondition", "You cannot mark your own answer helpful.")
            existing = _transaction_snapshot(transaction, mark_ref) or _MissingSnapshot()
            if existing.exists:
                action_time = existing.to_dict().get("createdAt") or now
                return {
                    "alreadyMarked": True, "answerAuthorId": author_id,
                    "actionOccurredAt": action_time,
                }
            transaction.set(mark_ref, {"answerId": answer_id, "studentId": actor_id, "createdAt": now})
            return {
                "alreadyMarked": False, "answerAuthorId": author_id,
                "actionOccurredAt": now,
            }
        result = mark(self.database.transaction())
        # The deterministic event is independently idempotent. Replaying it
        # repairs a counter if a prior callable died after writing the mark.
        self._record_participation(
            event_id=f"helpful:{answer_id}:{actor_id}",
            student_id=result["answerAuthorId"], field="helpfulReceivedCount",
            occurred_at=result["actionOccurredAt"],
        )
        return result

    def report_content(
        self,
        *,
        target_type: str,
        target_id: str,
        reason: str,
        actor_id: str,
        now: datetime,
    ) -> dict[str, Any]:
        target_id = _document_id(target_id)
        if target_type not in {"question", "answer"}:
            raise ForumRuntimeError("invalid-argument", "Report targetType must be question or answer.")
        clean_reason = reason.strip()
        if len(clean_reason) < 3 or len(clean_reason) > 500:
            raise ForumRuntimeError("invalid-argument", "Report reason must be between 3 and 500 characters.")

        target_collection = "forumQuestions" if target_type == "question" else "forumAnswers"
        target_ref = self.database.collection(target_collection).document(target_id)
        report_ref = self.database.collection("forumReports").document(
            f"{actor_id}_{target_type}_{target_id}"
        )

        @firestore.transactional
        def report(transaction: Any) -> dict[str, Any]:
            target = _transaction_snapshot(transaction, target_ref) or _MissingSnapshot()
            if not target.exists:
                raise ForumRuntimeError("not-found", "Report target not found.")
            if _required(target.to_dict(), "authorId") == actor_id:
                raise ForumRuntimeError("failed-precondition", "You cannot report your own content.")

            existing = _transaction_snapshot(transaction, report_ref) or _MissingSnapshot()
            if existing.exists:
                transaction.update(report_ref, {"reason": clean_reason, "updatedAt": now})
                return {"alreadyReported": True}

            transaction.set(report_ref, {
                "reporterId": actor_id,
                "targetType": target_type,
                "targetId": target_id,
                "reason": clean_reason,
                "status": "active",
                "createdAt": now,
                "updatedAt": now,
            })
            return {"alreadyReported": False}

        return report(self.database.transaction())

    def accept_answer(self, *, answer_id: str, actor_id: str, now: datetime) -> dict[str, Any]:
        answer_id = _document_id(answer_id)
        answer_ref = self.database.collection("forumAnswers").document(answer_id)
        @firestore.transactional
        def accept(transaction: Any) -> dict[str, Any]:
            answer = _transaction_snapshot(transaction, answer_ref) or _MissingSnapshot()
            if not answer.exists:
                raise ForumRuntimeError("not-found", "Answer not found.")
            data = answer.to_dict()
            question_id, author_id = _required(data, "questionId"), _required(data, "authorId")
            question_ref = self.database.collection("forumQuestions").document(question_id)
            question = _transaction_snapshot(transaction, question_ref) or _MissingSnapshot()
            question_data = question.to_dict() if question.exists else {}
            if not question.exists or _required(question_data, "authorId") != actor_id:
                raise ForumRuntimeError("permission-denied", "Only the question author may accept an answer.")
            if author_id == actor_id:
                raise ForumRuntimeError("failed-precondition", "You cannot accept your own answer.")
            accepted_answer_id = question_data.get("acceptedAnswerId")
            if not accepted_answer_id:
                answer_query = self.database.collection("forumAnswers").where(
                    "questionId", "==", question_id
                )
                legacy_accepted = next(
                    (
                        snapshot
                        for snapshot in _transaction_snapshots(transaction, answer_query)
                        if snapshot.to_dict().get("acceptedAt") is not None
                    ),
                    None,
                )
                if legacy_accepted is not None:
                    if legacy_accepted.id != answer_id:
                        raise ForumRuntimeError(
                            "already-exists", "This question already has an accepted answer."
                        )
                    transaction.update(question_ref, {
                        "acceptedAnswerId": answer_id,
                        "acceptedAt": data["acceptedAt"],
                        "updatedAt": now,
                    })
                    return {
                        "alreadyAccepted": True, "answerAuthorId": author_id,
                        "actionOccurredAt": data["acceptedAt"],
                    }
            if accepted_answer_id == answer_id and data.get("acceptedAt") is not None:
                return {
                    "alreadyAccepted": True, "answerAuthorId": author_id,
                    "actionOccurredAt": data["acceptedAt"],
                }
            if isinstance(accepted_answer_id, str) and accepted_answer_id:
                raise ForumRuntimeError(
                    "already-exists", "This question already has an accepted answer."
                )
            if data.get("acceptedAt") is not None:
                raise ForumRuntimeError(
                    "failed-precondition", "This answer is already accepted elsewhere."
                )
            transaction.update(question_ref, {
                "acceptedAnswerId": answer_id,
                "acceptedAt": now,
                "updatedAt": now,
            })
            transaction.update(answer_ref, {"acceptedAt": now, "acceptedBy": actor_id})
            return {
                "alreadyAccepted": False, "answerAuthorId": author_id,
                "actionOccurredAt": now,
            }
        result = accept(self.database.transaction())
        # As above, a retry after a partial failure restores the safe count
        # without ever creating a second acceptance event.
        self._record_participation(
            event_id=f"accept:{answer_id}",
            student_id=result["answerAuthorId"], field="acceptedAnswersCount",
            occurred_at=result["actionOccurredAt"],
        )
        return result

    def process_answer(
        self,
        answer_id: str,
        data: Mapping[str, Any],
        classifier: ForumTextClassifier | None,
        *,
        event_id: str | None = None,
        now: datetime | None = None,
    ) -> str:
        answer_id = _document_id(answer_id)
        now = now or datetime.now(timezone.utc)
        audit_event_id = event_id or f"answer:{answer_id}"
        try:
            text = _required(data, "text")
            revision = data.get("revision", 1)
            if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
                raise ForumRuntimeError(
                    "failed-precondition", "Forum answer revision is invalid.",
                )
        except ForumRuntimeError as error:
            return self._terminalize_invalid_answer(
                answer_id=answer_id,
                data=data,
                event_id=audit_event_id,
                error=error,
            )
        model_version = classifier.model_version if classifier is not None else "safe-fallback-v1"
        artifact_identity = (
            str(getattr(classifier, "artifact_sha256", model_version))
            if classifier is not None else model_version
        )
        claim_level = (
            str(getattr(classifier, "claim_level", FORUM_UNVALIDATED_CLAIM_LEVEL))
            if classifier is not None else FORUM_FALLBACK_CLAIM_LEVEL
        )
        text_hash = _forum_text_hash(text)
        if text_hash is None:
            raise ForumRuntimeError("failed-precondition", "Forum answer text is invalid.")
        logical_id = sha256(
            json.dumps({
                "answerId": answer_id,
                "revision": revision,
                "textHash": text_hash,
                "modelVersion": model_version,
                "artifactIdentity": artifact_identity,
                "claimLevel": claim_level,
                "policyVersion": FORUM_AI_POLICY_VERSION,
            }, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        claim_or_state = self._claim_answer(
            answer_id=answer_id,
            logical_inference_id=logical_id,
            revision=revision,
            text_hash=text_hash,
            model_version=model_version,
            artifact_identity=artifact_identity,
            claim_level=claim_level,
            event_id=audit_event_id,
            now=now,
        )
        if isinstance(claim_or_state, str):
            return claim_or_state
        claim = claim_or_state
        try:
            prediction = classifier.predict(text) if classifier is not None else None
            return self._finalize_answer(claim, prediction, now=now)
        except Exception as error:
            permanent = isinstance(error, (ForumRuntimeError, ValueError, TypeError))
            state = self._fail_answer(claim, error, permanent=permanent, now=now)
            if state == "retryable":
                raise
            return state

    def _terminalize_invalid_answer(
        self,
        *,
        answer_id: str,
        data: Mapping[str, Any],
        event_id: str,
        error: ForumRuntimeError,
    ) -> str:
        answer_ref = self.database.collection("forumAnswers").document(answer_id)
        job_ref = self.database.collection("forumAiJobs").document(answer_id)

        @firestore.transactional
        def terminalize(transaction: Any) -> str:
            answer_snapshot = _transaction_snapshot(transaction, answer_ref) or _MissingSnapshot()
            current = answer_snapshot.to_dict() if answer_snapshot.exists else {}
            if (
                current.get("revision", 1) != data.get("revision", 1)
                or current.get("text") != data.get("text")
            ):
                return "superseded"
            transaction.set(job_ref, {
                "answerId": answer_id,
                "state": "failed",
                "failureType": "permanent",
                "errorCode": error.code,
                "claimEventId": event_id,
                "attemptCount": 1,
                "leaseExpiresAt": None,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }, merge=True)
            return "failed"

        return terminalize(self.database.transaction())

    def _claim_answer(
        self,
        *,
        answer_id: str,
        logical_inference_id: str,
        revision: int,
        text_hash: str,
        model_version: str,
        artifact_identity: str,
        event_id: str,
        now: datetime,
        claim_level: str = FORUM_UNVALIDATED_CLAIM_LEVEL,
    ) -> ForumAiClaim | str:
        answer_ref = self.database.collection("forumAnswers").document(answer_id)
        job_ref = self.database.collection("forumAiJobs").document(answer_id)
        run_ref = self.database.collection("forumAiRuns").document(logical_inference_id)

        @firestore.transactional
        def claim(transaction: Any) -> ForumAiClaim | str:
            answer_snapshot = _transaction_snapshot(transaction, answer_ref) or _MissingSnapshot()
            answer = answer_snapshot.to_dict() if answer_snapshot.exists else {}
            current_text_hash = _forum_text_hash(answer.get("text"))
            if answer.get("revision", 1) != revision or current_text_hash != text_hash:
                return "superseded"
            job_snapshot = _transaction_snapshot(transaction, job_ref) or _MissingSnapshot()
            job = job_snapshot.to_dict() if job_snapshot.exists else {}
            state = job.get("state")
            feedback = answer.get("aiFeedback")
            feedback_state = feedback.get("state") if isinstance(feedback, Mapping) else None
            feedback_revision = feedback.get("revision") if isinstance(feedback, Mapping) else None
            legacy_terminal_feedback = (
                not job.get("logicalInferenceId")
                and state in {"completed", "fallback", "failed"}
                and feedback_state in {"completed", "fallback", "failed"}
                and (
                    feedback_revision == revision
                    or (feedback_revision is None and revision == 1)
                )
            )
            if legacy_terminal_feedback:
                return str(state)
            same_identity = (
                job.get("logicalInferenceId") == logical_inference_id
                or (
                    not job.get("logicalInferenceId")
                    and state in {"processing", "retryable"}
                )
            )
            # A completed duplicate is a read-only no-op. Run recovery below
            # is reserved for the partial-failure case where the terminal job
            # write did not commit.
            if same_identity and state in {"completed", "fallback", "failed"}:
                return str(state)
            run_snapshot = _transaction_snapshot(transaction, run_ref) or _MissingSnapshot()
            if run_snapshot.exists:
                run = run_snapshot.to_dict()
                state = str(run.get("resultState") or run.get("state") or "completed")
                prediction = run.get("prediction")
                if run.get("state") != "superseded":
                    transaction.set(answer_ref, {"aiFeedback": _feedback_payload(
                        state=state,
                        prediction=prediction,
                        revision=revision,
                        logical_inference_id=logical_inference_id,
                    )}, merge=True)
                transaction.set(job_ref, {
                    "answerId": answer_id, "state": state,
                    "logicalInferenceId": logical_inference_id,
                    "artifactIdentity": artifact_identity,
                    "recoveredFromRun": True, "updatedAt": firestore.SERVER_TIMESTAMP,
                }, merge=True)
                return state

            lease_expires_at = job.get("leaseExpiresAt")
            if (
                same_identity and state == "processing"
                and isinstance(lease_expires_at, datetime) and lease_expires_at > now
            ):
                return "processing"

            previous_generation = job.get("fencingGeneration", 0)
            if isinstance(previous_generation, bool) or not isinstance(previous_generation, int):
                previous_generation = 0
            previous_attempt = job.get("attemptCount", 0) if same_identity else 0
            if isinstance(previous_attempt, bool) or not isinstance(previous_attempt, int):
                previous_attempt = 0
            attempt_count = previous_attempt + 1
            fencing_generation = previous_generation + 1
            lease_expiry = now + FORUM_AI_LEASE_DURATION
            if attempt_count > FORUM_AI_MAX_ATTEMPTS:
                transaction.set(job_ref, {
                    "answerId": answer_id, "state": "failed",
                    "failureType": "attempts_exhausted",
                    "attemptCount": previous_attempt,
                    "logicalInferenceId": logical_inference_id,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                }, merge=True)
                return "failed"
            transaction.set(job_ref, {
                "answerId": answer_id,
                "state": "processing",
                "logicalInferenceId": logical_inference_id,
                "revision": revision,
                "textHash": text_hash,
                "modelVersion": model_version,
                "artifactIdentity": artifact_identity,
                "claimLevel": claim_level,
                "policyVersion": FORUM_AI_POLICY_VERSION,
                "claimEventId": event_id,
                "attemptCount": attempt_count,
                "fencingGeneration": fencing_generation,
                "leaseExpiresAt": lease_expiry,
                "completedAt": None,
                "failureType": None,
                "errorCode": None,
                "recoveredFromRun": False,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }, merge=True)
            transaction.set(answer_ref, {"aiFeedback": {
                "state": "pending", "revision": revision,
                "logicalInferenceId": logical_inference_id,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }}, merge=True)
            return ForumAiClaim(
                answer_id=answer_id,
                logical_inference_id=logical_inference_id,
                revision=revision,
                text_hash=text_hash,
                model_version=model_version,
                artifact_identity=artifact_identity,
                claim_level=claim_level,
                policy_version=FORUM_AI_POLICY_VERSION,
                fencing_generation=fencing_generation,
                attempt_count=attempt_count,
                event_id=event_id,
            )

        return claim(self.database.transaction())

    def _finalize_answer(self, claim: ForumAiClaim, prediction: Any, *, now: datetime) -> str:
        answer_ref = self.database.collection("forumAnswers").document(claim.answer_id)
        job_ref = self.database.collection("forumAiJobs").document(claim.answer_id)
        run_ref = self.database.collection("forumAiRuns").document(claim.logical_inference_id)

        @firestore.transactional
        def finalize(transaction: Any) -> str:
            existing_run = _transaction_snapshot(transaction, run_ref) or _MissingSnapshot()
            if existing_run.exists:
                run = existing_run.to_dict()
                return str(run.get("resultState") or run.get("state") or "completed")
            answer_snapshot = _transaction_snapshot(transaction, answer_ref) or _MissingSnapshot()
            job_snapshot = _transaction_snapshot(transaction, job_ref) or _MissingSnapshot()
            answer = answer_snapshot.to_dict() if answer_snapshot.exists else {}
            job = job_snapshot.to_dict() if job_snapshot.exists else {}
            current_text_hash = _forum_text_hash(answer.get("text"))
            compatible = (
                job.get("state") == "processing"
                and job.get("logicalInferenceId") == claim.logical_inference_id
                and job.get("fencingGeneration") == claim.fencing_generation
                and job.get("artifactIdentity") == claim.artifact_identity
                and answer.get("revision", 1) == claim.revision
                and current_text_hash == claim.text_hash
            )
            result_state = "completed" if prediction is not None else "fallback"
            run_state = result_state if compatible else "superseded"
            if (
                not compatible
                and job.get("logicalInferenceId") == claim.logical_inference_id
                and job.get("fencingGeneration") != claim.fencing_generation
            ):
                return "superseded"
            transaction.create(run_ref, {
                "answerId": claim.answer_id,
                "logicalInferenceId": claim.logical_inference_id,
                "revision": claim.revision,
                "textHash": claim.text_hash,
                "modelVersion": claim.model_version,
                "artifactIdentity": claim.artifact_identity,
                "claimLevel": claim.claim_level,
                "policyVersion": claim.policy_version,
                "fencingGeneration": claim.fencing_generation,
                "claimEventId": claim.event_id,
                "state": run_state,
                "resultState": result_state,
                "prediction": asdict(prediction) if prediction is not None else None,
                "createdAt": firestore.SERVER_TIMESTAMP,
            })
            if not compatible:
                return "superseded"
            transaction.set(answer_ref, {"aiFeedback": _feedback_payload(
                state=result_state,
                prediction=prediction,
                revision=claim.revision,
                logical_inference_id=claim.logical_inference_id,
            )}, merge=True)
            transaction.set(job_ref, {
                "state": result_state,
                "completedAt": firestore.SERVER_TIMESTAMP,
                "leaseExpiresAt": None,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }, merge=True)
            return result_state

        return finalize(self.database.transaction())

    def _fail_answer(
        self,
        claim: ForumAiClaim,
        error: Exception,
        *,
        permanent: bool,
        now: datetime,
    ) -> str:
        job_ref = self.database.collection("forumAiJobs").document(claim.answer_id)
        answer_ref = self.database.collection("forumAnswers").document(claim.answer_id)

        @firestore.transactional
        def fail(transaction: Any) -> str:
            job_snapshot = _transaction_snapshot(transaction, job_ref) or _MissingSnapshot()
            answer_snapshot = _transaction_snapshot(transaction, answer_ref) or _MissingSnapshot()
            job = job_snapshot.to_dict() if job_snapshot.exists else {}
            answer = answer_snapshot.to_dict() if answer_snapshot.exists else {}
            if (
                job.get("logicalInferenceId") != claim.logical_inference_id
                or job.get("fencingGeneration") != claim.fencing_generation
            ):
                return "superseded"
            exhausted = claim.attempt_count >= FORUM_AI_MAX_ATTEMPTS
            state = "failed" if permanent or exhausted else "retryable"
            transaction.set(job_ref, {
                "state": state,
                "failureType": (
                    "permanent" if permanent else
                    "attempts_exhausted" if exhausted else "transient"
                ),
                "errorCode": type(error).__name__,
                "leaseExpiresAt": None if state == "failed" else now,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }, merge=True)
            if (
                state == "failed"
                and answer.get("revision", 1) == claim.revision
                and _forum_text_hash(answer.get("text")) == claim.text_hash
            ):
                transaction.set(answer_ref, {"aiFeedback": _feedback_payload(
                    state="fallback",
                    prediction=None,
                    revision=claim.revision,
                    logical_inference_id=claim.logical_inference_id,
                )}, merge=True)
            return state

        return fail(self.database.transaction())


def load_forum_classifier(
    path: Path = FORUM_MODEL_PATH, manifest_path: Path = FORUM_MODEL_MANIFEST_PATH,
    *, registry_documents: list[Mapping[str, Any]] | None = None,
    evidence_mode: str | None = None, code_revision: str | None = None,
) -> ForumTextClassifier | None:
    from logic_oasis_ai.forum_ai.classifier import ForumTextClassifier

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            return None
        if manifest.get("evidenceState") == "emulator_fixture_only" and os.environ.get("FUNCTIONS_EMULATOR") != "true":
            return None
        if manifest.get("evidenceState") == "emulator_fixture_only":
            if manifest.get("artifactSha256") != sha256(path.read_bytes()).hexdigest():
                return None
            classifier = ForumTextClassifier.load(path)
            return classifier if manifest.get("modelVersion") == classifier.model_version else None

        mode = evidence_mode or os.environ.get("FORUM_MODEL_EVIDENCE_MODE", FORUM_REAL_EVALUATED_MODE)
        revision = code_revision or os.environ.get("FORUM_RUNTIME_CODE_REVISION", "")
        documents = [] if registry_documents is None else list(registry_documents)
        compatible = [
            item for item in documents
            if isinstance(item, Mapping)
            and item.get("lifecycleStatus") == "released"
            and item.get("isActive") is True
            and item.get("deploymentScope") == FORUM_CONTROLLED_MODE
        ]
        if mode != FORUM_CONTROLLED_MODE or len(compatible) != 1:
            _log_forum_activation_failure("mode_or_registry_incompatible", manifest, revision)
            return None
        release = compatible[0]
        # The bundled immutable record must be the selected registry record.
        if any(release.get(key) != value for key, value in manifest.items()):
            _log_forum_activation_failure("registry_manifest_mismatch", manifest, revision)
            return None
        if not _controlled_forum_release_valid(manifest, path, manifest_path, revision):
            _log_forum_activation_failure("release_validation_failed", manifest, revision)
            return None
        # joblib is intentionally beyond the complete validation boundary.
        classifier = ForumTextClassifier.load(path)
        if manifest.get("modelVersion") != classifier.model_version:
            _log_forum_activation_failure("classifier_version_mismatch", manifest, revision)
            return None
        classifier.artifact_sha256 = manifest["artifactSha256"]
        classifier.claim_level = manifest["claimLevel"]
        return classifier
    except Exception:
        _log_forum_activation_failure(
            "activation_exception",
            locals().get("manifest"),
            code_revision or "",
        )
        return None


def _log_forum_activation_failure(
    code: str, manifest: object, code_revision: str,
) -> None:
    release_id = manifest.get("releaseId", "unknown") if isinstance(manifest, Mapping) else "unknown"
    LOGGER.warning(
        "forum_model_activation_failed code=%s release_id=%s code_revision=%s",
        code,
        release_id,
        code_revision or "missing",
    )


def _controlled_forum_release_valid(
    manifest: Mapping[str, Any], artifact_path: Path, manifest_path: Path, code_revision: str,
) -> bool:
    from logic_oasis_ai.forum_ai.classifier import NAIVE_BAYES_VARIANTS

    if manifest.get("manifestSchemaVersion") != FORUM_RELEASE_MANIFEST_SCHEMA:
        return False
    if any(manifest.get(key) != value for key, value in _CONTROLLED_RELEASE_VALUES.items()):
        return False
    if manifest.get("modelType") not in NAIVE_BAYES_VARIANTS:
        return False
    if not isinstance(manifest.get("releaseId"), str) or not manifest.get("releaseId"):
        return False
    if not isinstance(manifest.get("releasedBy"), str) or not manifest.get("releasedBy"):
        return False
    released_at = manifest.get("releasedAt")
    if not isinstance(released_at, str) or not released_at.endswith("Z"):
        return False
    rationale = manifest.get("releaseRationale")
    if not isinstance(rationale, str) or "not evaluated on real learner forum responses" not in rationale.casefold():
        return False
    if manifest.get("codeRevision") != code_revision or not code_revision:
        return False
    if manifest.get("codeRevisionKind") != "sha256_bounded_release_sources_v1":
        return False
    if any(
        not isinstance(manifest.get(field), str)
        or not SHA256_PATTERN.fullmatch(manifest[field])
        for field in _SHA256_FIELDS
    ):
        return False
    artifact_bytes = artifact_path.read_bytes()
    if sha256(artifact_bytes).hexdigest() != manifest.get("artifactSha256"):
        return False
    if manifest.get("artifactSizeBytes") != len(artifact_bytes):
        return False
    if manifest.get("candidateGateStatus") != "passed" or manifest.get("failedGates") != []:
        return False
    if manifest.get("semanticReproducibilityStatus") != "verified_same_runtime_contract":
        return False
    if manifest.get("baselineComparisonResult") not in {
        "naive_bayes_advantage_demonstrated", "no_controlled_scenario_advantage_demonstrated",
    }:
        return False
    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, Mapping) or set(dependencies) != {"joblib", "numpy", "scikit-learn"}:
        return False
    if any(importlib.metadata.version(name) != version for name, version in dependencies.items()):
        return False
    source_hashes = manifest.get("sourceRuntimeHashes")
    vendor_hashes = manifest.get("vendorRuntimeHashes")
    if source_hashes != vendor_hashes or not isinstance(vendor_hashes, Mapping):
        return False
    vendor_root = manifest_path.parent / "vendor/logic_oasis_ai/forum_ai"
    if any(
        sha256((vendor_root / name).read_bytes()).hexdigest() != expected
        for name, expected in vendor_hashes.items()
    ):
        return False
    deployment_hashes = manifest.get("deploymentRuntimeHashes")
    if not isinstance(deployment_hashes, Mapping) or set(deployment_hashes) != {"forum_runtime.py", "main.py"}:
        return False
    if any(
        sha256((manifest_path.parent / name).read_bytes()).hexdigest() != expected
        for name, expected in deployment_hashes.items()
    ):
        return False
    bundle_path = manifest_path.parent / "vendor/bundle_manifest.json"
    bundle_bytes = bundle_path.read_bytes()
    if sha256(bundle_bytes).hexdigest() != manifest.get("bundleManifestSha256"):
        return False
    bundle = json.loads(bundle_bytes)
    forum_bundle = bundle.get("forumRuntimeBundle") if isinstance(bundle, dict) else None
    if not isinstance(forum_bundle, Mapping) or forum_bundle.get("bundleSchemaVersion") != "forum-runtime-bundle-v1":
        return False
    if forum_bundle.get("files") != vendor_hashes:
        return False
    vectorizer = manifest.get("vectorizerContract")
    if not isinstance(vectorizer, Mapping) or vectorizer.get("family") != "TfidfVectorizer":
        return False
    if manifest.get("abstentionPolicyVersion") != vectorizer.get("abstentionPolicyVersion"):
        return False
    return True


def _required(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ForumRuntimeError("failed-precondition", f"Forum {key} is missing.")
    return value.strip()


class _MissingSnapshot:
    exists = False

    def to_dict(self) -> dict[str, Any]:
        return {}
