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
    from logic_oasis_ai.forum_ai.relevance import ForumRelevanceClassifier
LOGGER = logging.getLogger(__name__)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")

FORUM_RUNTIME_SERVICE_ACCOUNT = "logic-oasis-forum-runtime@logic-oasis-fyp.iam.gserviceaccount.com"
FORUM_MODEL_PATH = Path(__file__).resolve().parent / "forum_model.joblib"
FORUM_MODEL_MANIFEST_PATH = Path(__file__).resolve().parent / "forum_model_manifest.json"
KUALA_LUMPUR = ZoneInfo("Asia/Kuala_Lumpur")
COUNTER_FIELDS = ("questionsPostedCount", "answersSubmittedCount", "acceptedAnswersCount", "helpfulReceivedCount")
FORUM_AI_POLICY_VERSION = "forum-advisory-policy-v1"
FORUM_COMPOSITE_POLICY_VERSION = "forum-composite-policy-v1"
FORUM_AI_LEASE_DURATION = timedelta(minutes=5)
FORUM_AI_MAX_ATTEMPTS = 3
FORUM_RELEASE_MANIFEST_SCHEMA = "forum-model-release-manifest-v1"
FORUM_RELEASE_MANIFEST_SCHEMA_V2 = "forum-model-release-manifest-v2"
FORUM_CONTROLLED_MODE = "controlled_demo"
FORUM_REAL_EVALUATED_MODE = "real_evaluated_only"
FORUM_CONTROLLED_CLAIM_LEVEL = "controlled_demonstration_only"
FORUM_UNVALIDATED_CLAIM_LEVEL = "unvalidated_model_output"
FORUM_FALLBACK_CLAIM_LEVEL = "safe_fallback_only"
FORUM_MODE_FREE_FORM = "free_form"
FORUM_MODE_LINKED = "linked"
LINKED_DISCUSSION_PREFIX = "linked_"
LINKED_OPTION_COUNT = 4
FORUM_LINKED_EXPLANATION_MIN_LENGTH = 8
FORUM_LINKED_EXPLANATION_MAX_LENGTH = 4000
FORUM_PUBLIC_STATE_NONE = "none"
FORUM_PUBLIC_STATE_VERIFIED = "verified"
FORUM_PUBLIC_STATE_MAY_BE_IRRELEVANT = "may_be_irrelevant"
FORUM_PRIVATE_FEEDBACK_COLLECTION = "forumAiFeedback"
FORUM_REASONING_MODEL_VERSION = "forum-controlled-demo-nb-v1"
FORUM_RELEVANCE_MODEL_VERSION = "forum-relevance-nb-v1"
REASONING_ABSTENTION_THRESHOLD = 0.60
RELEVANCE_POSITIVE_THRESHOLD = 0.65
RELEVANCE_NEGATIVE_THRESHOLD = 0.80
COMPOSITE_POLICY_CONTRACT = {
    "policyVersion": FORUM_COMPOSITE_POLICY_VERSION,
    "correctness": "deterministic_protected_answer_key_v1",
    "relevancePositiveThreshold": RELEVANCE_POSITIVE_THRESHOLD,
    "relevanceNegativeThreshold": RELEVANCE_NEGATIVE_THRESHOLD,
    "reasoningAbstentionThreshold": REASONING_ABSTENTION_THRESHOLD,
    "freeFormNeverVerified": True,
    "withholdOnAnyAbstention": True,
    "noPublicNegativeCorrectnessLabel": True,
}
LEGACY_EMBEDDED_FEEDBACK_ALLOWED = frozenset({"state", "label", "revision"})
LEGACY_EMBEDDED_FEEDBACK_DISALLOWED = frozenset({
    "message", "probability", "modelVersion", "calibrationState",
    "logicalInferenceId", "updatedAt", "policyVersion", "claimLevel",
})
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

_V2_SHA256_FIELDS = (
    "reasoningArtifactSha256", "relevanceArtifactSha256", "catalogueSha256",
    "datasetSha256", "datasetManifestSha256", "splitManifestSha256",
    "rubricSha256", "evaluationReportSha256", "candidateManifestSha256",
    "bundleManifestSha256", "dependencyLockSha256",
)


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


@dataclass(frozen=True)
class ForumAiBundle:
    reasoning: Any
    relevance: Any
    policy: Mapping[str, Any]
    release_id: str
    reasoning_artifact_identity: str
    relevance_artifact_identity: str
    claim_level: str = FORUM_CONTROLLED_CLAIM_LEVEL


@dataclass(frozen=True)
class ForumOutcome:
    """One completed composite (or legacy advisory) result for an answer."""
    public_state: str
    private: Mapping[str, Any]
    run_bindings: Mapping[str, Any]
    state: str = "completed"


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


def _answer_analysis_text(data: Mapping[str, Any]) -> str | None:
    """Return the text the advisory runtime should analyse for an answer.

    Linked answers carry a structured final-answer selector plus a separate
    explanation; the reasoning classifier reads the explanation. Free-form
    answers keep the legacy single ``text`` field.
    """
    if data.get("mode") == FORUM_MODE_LINKED:
        value = data.get("explanation")
    else:
        value = data.get("text")
    return value.strip() if isinstance(value, str) else None


def _answer_content_hash(data: Mapping[str, Any]) -> str | None:
    """Revision-bound fingerprint of the analysable answer content.

    Includes the explanation (or legacy free-form text) and, for linked
    answers, the selected option, so a swapped option or edited explanation
    fences the stale run without a re-read of the source document.
    """
    text = _answer_analysis_text(data)
    if text is None:
        return None
    return sha256(json.dumps({
        "text": text,
        "selectedOption": data.get("selectedOption"),
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _linked_discussion_id(question_id: str, content_version: str) -> str:
    return f"{LINKED_DISCUSSION_PREFIX}{question_id}_{content_version}"


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
    message = (
        "Your answer is being reviewed."
        if state == "pending"
        else feedback_for(label)
    )
    return {
        "state": state,
        "label": label,
        "probability": probability,
        "modelVersion": model_version,
        "calibrationState": calibration_state,
        "message": message,
        "revision": revision,
        "logicalInferenceId": logical_inference_id,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }


def _composite_feedback_payload(
    *,
    outcome: Mapping[str, Any],
    revision: int,
    logical_inference_id: str,
    bundle: ForumAiBundle,
    source_question_id: str | None,
    source_content_version: str | None,
    reasoning_probability: float | None,
    relevance_probability: float | None,
) -> dict[str, Any]:
    """Author-only composite guidance projection (never client-written)."""
    return {
        "state": "completed",
        "label": outcome["privateLabel"],
        "message": outcome["message"],
        "probability": reasoning_probability,
        "relevanceProbability": relevance_probability,
        "modelVersion": bundle.reasoning.model_version,
        "relevanceModelVersion": bundle.relevance.model_version,
        "calibrationState": "not_calibrated",
        "revision": revision,
        "logicalInferenceId": logical_inference_id,
        "correctness": outcome["correctness"],
        "relevance": outcome["relevance"],
        "reasoning": outcome["reasoning"],
        "correctnessGuidance": outcome["correctnessGuidance"],
        "relevanceGuidance": outcome["relevanceGuidance"],
        "reasoningGuidance": outcome["reasoningGuidance"],
        "relevancePositiveThreshold": RELEVANCE_POSITIVE_THRESHOLD,
        "relevanceNegativeThreshold": RELEVANCE_NEGATIVE_THRESHOLD,
        "reasoningAbstentionThreshold": REASONING_ABSTENTION_THRESHOLD,
        "policyVersion": FORUM_COMPOSITE_POLICY_VERSION,
        "sourceQuestionId": source_question_id,
        "sourceContentVersion": source_content_version,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }


def _public_answer_projection(
    *, state: str, logical_inference_id: str, revision: int,
) -> dict[str, Any]:
    """Allow-listed public advisory state on the shared answer document.

    Only the advisory enum and the non-sensitive current run/revision
    references are shared. Correctness details, reasoning guidance,
    probabilities, thresholds, and component diagnostics stay in the
    author-only ``forumAiFeedback`` projection.
    """
    public_state = (
        state
        if state in {
            FORUM_PUBLIC_STATE_NONE,
            FORUM_PUBLIC_STATE_VERIFIED,
            FORUM_PUBLIC_STATE_MAY_BE_IRRELEVANT,
        }
        else FORUM_PUBLIC_STATE_NONE
    )
    return {
        "aiPublicState": public_state,
        "aiRunId": logical_inference_id,
        "aiRevision": revision,
    }


def composite_decision(
    *,
    mode: str,
    reasoning_label: str,
    relevance_label: str,
    correctness: str,
) -> dict[str, Any]:
    """Apply the frozen composite policy to one answer.

    ``correctness`` is one of ``correct``, ``incorrect``, ``unavailable``, or
    ``not_applicable``. Public state is emitted only when every applicable
    component is non-abstaining and the protected key is authoritative.
    """
    if mode == FORUM_MODE_FREE_FORM:
        if relevance_label == "irrelevant":
            public_state = FORUM_PUBLIC_STATE_MAY_BE_IRRELEVANT
            private_label = "may_be_irrelevant"
        else:
            public_state = FORUM_PUBLIC_STATE_NONE
            private_label = (
                "needs_reasoning"
                if reasoning_label == "needs_reasoning"
                else "advisory"
            )
        guidance = {
            "correctnessGuidance": None,
            "relevanceGuidance": (
                "This explanation may not address the question directly. "
                "Try explaining how you worked out this question."
                if relevance_label == "irrelevant"
                else None
            ),
            "reasoningGuidance": (
                "Please add the steps or mathematical reason behind your answer "
                "so a peer can learn from it."
                if reasoning_label == "needs_reasoning"
                else None
            ),
        }
        return {
            "publicState": public_state,
            "privateLabel": private_label,
            "correctness": "not_applicable",
            "relevance": relevance_label,
            "reasoning": reasoning_label,
            "message": _composite_message(private_label),
            **guidance,
        }

    if correctness == "unavailable":
        return {
            "publicState": FORUM_PUBLIC_STATE_NONE,
            "privateLabel": "advisory",
            "correctness": "unavailable",
            "relevance": relevance_label,
            "reasoning": reasoning_label,
            "message": (
                "Your answer is saved. Verification is unavailable for this "
                "question version, so no badge can be shown."
            ),
            "correctnessGuidance": None,
            "relevanceGuidance": None,
            "reasoningGuidance": None,
        }
    if (
        reasoning_label == "uncertain"
        or relevance_label == "uncertain"
    ):
        return {
            "publicState": FORUM_PUBLIC_STATE_NONE,
            "privateLabel": "uncertain",
            "correctness": (
                "correct" if correctness == "correct" else "incorrect"
            ),
            "relevance": relevance_label,
            "reasoning": reasoning_label,
            "message": (
                "Your answer is saved. We could not reach a confident "
                "automated decision, so no badge is shown."
            ),
            "correctnessGuidance": None,
            "relevanceGuidance": None,
            "reasoningGuidance": None,
        }
    if correctness == "incorrect":
        return {
            "publicState": FORUM_PUBLIC_STATE_NONE,
            "privateLabel": "correction_needed",
            "correctness": "incorrect",
            "relevance": relevance_label,
            "reasoning": reasoning_label,
            "message": (
                "Your selected final answer does not match the worked answer "
                "key. Check the steps again and edit your answer if you wish."
            ),
            "correctnessGuidance": (
                "Your selected final answer does not match the worked answer "
                "key. No public incorrect label is shown; only you can see this."
            ),
            "relevanceGuidance": None,
            "reasoningGuidance": None,
        }
    if relevance_label == "irrelevant":
        return {
            "publicState": FORUM_PUBLIC_STATE_MAY_BE_IRRELEVANT,
            "privateLabel": "may_be_irrelevant",
            "correctness": "correct",
            "relevance": "irrelevant",
            "reasoning": reasoning_label,
            "message": (
                "This explanation may not address the question directly. "
                "Try explaining how you worked out this question."
            ),
            "correctnessGuidance": None,
            "relevanceGuidance": (
                "A public advisory note may show that this answer may be "
                "irrelevant. Only you can see this private guidance."
            ),
            "reasoningGuidance": None,
        }
    if reasoning_label == "needs_reasoning":
        return {
            "publicState": FORUM_PUBLIC_STATE_NONE,
            "privateLabel": "needs_reasoning",
            "correctness": "correct",
            "relevance": "relevant",
            "reasoning": "needs_reasoning",
            "message": (
                "Please add the steps or mathematical reason behind your "
                "answer so a peer can learn from it."
            ),
            "correctnessGuidance": None,
            "relevanceGuidance": None,
            "reasoningGuidance": (
                "Please add the steps or mathematical reason behind your "
                "answer so a peer can learn from it."
            ),
        }
    return {
        "publicState": FORUM_PUBLIC_STATE_VERIFIED,
        "privateLabel": "verified",
        "correctness": "correct",
        "relevance": "relevant",
        "reasoning": "sufficient_reasoning",
        "message": (
            "Your final answer and explanation passed the system's automated "
            "checks. This is an advisory result, not human verification."
        ),
        "correctnessGuidance": None,
        "relevanceGuidance": None,
        "reasoningGuidance": None,
    }


def _composite_message(private_label: str) -> str:
    if private_label == "may_be_irrelevant":
        return (
            "This explanation may not address the question directly. "
            "Try explaining how you worked out this question."
        )
    if private_label == "needs_reasoning":
        return (
            "Please add the steps or mathematical reason behind your answer "
            "so a peer can learn from it."
        )
    return "Your answer is saved. You can add a little more about how you reached it if you wish."


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
        if data.get("mode") == FORUM_MODE_LINKED:
            # Canonical linked discussions are server content, not student
            # participation; they never move the parent count-only summary.
            return
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
            target_data = target.to_dict()
            if (
                target_type == "question"
                and target_data.get("mode") == FORUM_MODE_LINKED
            ):
                raise ForumRuntimeError(
                    "failed-precondition",
                    "Linked discussions are server-owned and cannot be reported.",
                )
            if _required(target_data, "authorId") == actor_id:
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
            if question_data.get("mode") == FORUM_MODE_LINKED:
                raise ForumRuntimeError(
                    "failed-precondition",
                    "Linked discussions have no question owner to accept answers.",
                )
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

    def open_or_create_linked_discussion(
        self, *, question_id: str, actor_id: str, now: datetime,
    ) -> dict[str, Any]:
        """Create or open the canonical discussion for a question-bank item.

        The callable accepts only the public question ID. Every authority
        decision is derived server-side from ``questions`` and the protected
        ``questionAnswerKeys``; no client-supplied linkage is trusted.
        """
        question_id = _document_id(question_id)
        question_ref = self.database.collection("questions").document(question_id)
        key_ref = self.database.collection("questionAnswerKeys").document(question_id)

        @firestore.transactional
        def open_or_create(transaction: Any) -> dict[str, Any]:
            question_snapshot = _transaction_snapshot(transaction, question_ref) or _MissingSnapshot()
            key_snapshot = _transaction_snapshot(transaction, key_ref) or _MissingSnapshot()
            question = question_snapshot.to_dict() if question_snapshot.exists else {}
            key = key_snapshot.to_dict() if key_snapshot.exists else {}
            content_version = question.get("contentVersion")
            if (
                not question_snapshot.exists
                or question.get("isActive") is not True
                or not isinstance(content_version, str)
                or not content_version
            ):
                raise ForumRuntimeError(
                    "failed-precondition", "The linked question source is not active.",
                )
            if (
                not key_snapshot.exists
                or key.get("questionId") != question_id
                or key.get("contentVersion") != content_version
                or key.get("isActive") is not True
            ):
                raise ForumRuntimeError(
                    "failed-precondition",
                    "The linked question answer key is incompatible.",
                )
            answer_index = key.get("answerIndex")
            options = question.get("options")
            options_bm = question.get("optionsBm")
            if (
                isinstance(answer_index, bool)
                or not isinstance(answer_index, int)
                or answer_index < 0
                or answer_index >= LINKED_OPTION_COUNT
                or not isinstance(options, list)
                or len(options) != LINKED_OPTION_COUNT
                or any(
                    not isinstance(option, str) or not option.strip()
                    for option in options
                )
                or not isinstance(options_bm, list)
                or len(options_bm) != LINKED_OPTION_COUNT
                or any(
                    not isinstance(option, str) or not option.strip()
                    for option in options_bm
                )
            ):
                raise ForumRuntimeError(
                    "failed-precondition",
                    "The linked question source has invalid options.",
                )
            prompt = question.get("questionText")
            prompt_bm = question.get("questionTextBm")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ForumRuntimeError(
                    "failed-precondition",
                    "The linked question source is missing its prompt.",
                )
            if not isinstance(prompt_bm, str) or not prompt_bm.strip():
                raise ForumRuntimeError(
                    "failed-precondition",
                    "The linked question source is missing its Bahasa Melayu prompt.",
                )
            discussion_id = _linked_discussion_id(question_id, content_version)
            discussion_ref = self.database.collection("forumQuestions").document(
                discussion_id
            )
            existing = _transaction_snapshot(transaction, discussion_ref) or _MissingSnapshot()
            if existing.exists:
                existing_data = existing.to_dict()
                if existing_data.get("mode") != FORUM_MODE_LINKED:
                    raise ForumRuntimeError(
                        "already-exists",
                        "The canonical linked discussion ID collides with an existing forum question.",
                    )
                snapshot = existing_data.get("promptSnapshot") or {}
                return {
                    "discussionId": discussion_id,
                    "sourceQuestionId": question_id,
                    "sourceContentVersion": content_version,
                    "promptSnapshot": snapshot,
                    "title": existing_data.get("title", prompt.strip()),
                    "text": existing_data.get("text", prompt.strip()),
                    "createdAt": existing_data.get("createdAt"),
                    "created": False,
                }
            clean_prompt = prompt.strip()
            clean_prompt_bm = prompt_bm.strip()
            snapshot = {
                "questionText": clean_prompt,
                "questionTextBm": clean_prompt_bm,
                "options": [option.strip() for option in options],
                "optionsBm": [option.strip() for option in options_bm],
            }
            transaction.set(discussion_ref, {
                "mode": FORUM_MODE_LINKED,
                "sourceQuestionId": question_id,
                "sourceContentVersion": content_version,
                "promptSnapshot": snapshot,
                "title": clean_prompt[:140],
                "text": clean_prompt,
                "createdAt": now,
                "updatedAt": now,
            })
            return {
                "discussionId": discussion_id,
                "sourceQuestionId": question_id,
                "sourceContentVersion": content_version,
                "promptSnapshot": snapshot,
                "title": clean_prompt[:140],
                "text": clean_prompt,
                "createdAt": now,
                "created": True,
            }

        result = open_or_create(self.database.transaction())
        # A canonical linked discussion is shared server content, but each
        # student who opens it from the Forum or quiz review is posting a
        # thread of their own from the parent count-only perspective. The
        # event identity is per student and per discussion, so reopening the
        # same thread never double counts.
        self._record_participation(
            event_id=f"linked_question:{result['discussionId']}:{actor_id}",
            student_id=actor_id,
            field="questionsPostedCount",
            occurred_at=now,
        )
        return result

    def submit_linked_answer(
        self,
        *,
        discussion_id: str,
        selected_option: Any,
        explanation: str,
        actor_id: str,
        now: datetime,
    ) -> dict[str, Any]:
        discussion_id = _document_id(discussion_id)
        selected_option = self._validate_linked_option(selected_option)
        clean_explanation = self._validate_linked_explanation(explanation)
        discussion_ref = self.database.collection("forumQuestions").document(
            discussion_id
        )

        @firestore.transactional
        def submit(transaction: Any) -> dict[str, Any]:
            discussion = _transaction_snapshot(transaction, discussion_ref) or _MissingSnapshot()
            if not discussion.exists:
                raise ForumRuntimeError("not-found", "Linked discussion not found.")
            if discussion.to_dict().get("mode") != FORUM_MODE_LINKED:
                raise ForumRuntimeError(
                    "failed-precondition",
                    "Only linked discussions accept structured answers.",
                )
            answer_ref = self.database.collection("forumAnswers").document()
            transaction.set(answer_ref, {
                "questionId": discussion_id,
                "authorId": actor_id,
                "mode": FORUM_MODE_LINKED,
                "selectedOption": selected_option,
                "explanation": clean_explanation,
                "revision": 1,
                "aiPublicState": FORUM_PUBLIC_STATE_NONE,
                "createdAt": now,
                "updatedAt": now,
            })
            return {
                "answerId": answer_ref.id,
                "questionId": discussion_id,
                "revision": 1,
            }

        return submit(self.database.transaction())

    def edit_linked_answer(
        self,
        *,
        answer_id: str,
        selected_option: Any,
        explanation: str,
        actor_id: str,
        now: datetime,
    ) -> dict[str, Any]:
        answer_id = _document_id(answer_id)
        selected_option = self._validate_linked_option(selected_option)
        clean_explanation = self._validate_linked_explanation(explanation)
        answer_ref = self.database.collection("forumAnswers").document(answer_id)

        @firestore.transactional
        def edit(transaction: Any) -> dict[str, Any]:
            answer = _transaction_snapshot(transaction, answer_ref) or _MissingSnapshot()
            if not answer.exists:
                raise ForumRuntimeError("not-found", "Answer not found.")
            data = answer.to_dict()
            if data.get("mode") != FORUM_MODE_LINKED:
                raise ForumRuntimeError(
                    "failed-precondition",
                    "Only linked answers can be edited with structured fields.",
                )
            if data.get("authorId") != actor_id:
                raise ForumRuntimeError(
                    "permission-denied", "Only the answer author may edit this answer.",
                )
            if data.get("acceptedAt") is not None:
                raise ForumRuntimeError(
                    "failed-precondition", "An accepted answer cannot be edited.",
                )
            current_revision = data.get("revision", 1)
            if isinstance(current_revision, bool) or not isinstance(current_revision, int):
                current_revision = 1
            revision = current_revision + 1
            transaction.update(answer_ref, {
                "selectedOption": selected_option,
                "explanation": clean_explanation,
                "revision": revision,
                "aiPublicState": FORUM_PUBLIC_STATE_NONE,
                "aiRunId": None,
                "aiRevision": None,
                "updatedAt": now,
            })
            feedback_ref = self.database.collection(
                FORUM_PRIVATE_FEEDBACK_COLLECTION
            ).document(answer_id)
            transaction.set(feedback_ref, {
                "answerId": answer_id,
                "state": "pending",
                "label": "uncertain",
                "message": "Your revised answer is being reviewed.",
                "revision": revision,
                "updatedAt": now,
            })
            return {"answerId": answer_id, "revision": revision}

        return edit(self.database.transaction())

    @staticmethod
    def _validate_linked_option(selected_option: Any) -> int:
        if (
            isinstance(selected_option, bool)
            or not isinstance(selected_option, int)
            or selected_option < 0
            or selected_option >= LINKED_OPTION_COUNT
        ):
            raise ForumRuntimeError(
                "invalid-argument",
                "Linked answer option must be an integer between 0 and 3.",
            )
        return selected_option

    @staticmethod
    def _validate_linked_explanation(explanation: Any) -> str:
        clean = explanation.strip() if isinstance(explanation, str) else ""
        if (
            len(clean) < FORUM_LINKED_EXPLANATION_MIN_LENGTH
            or len(clean) > FORUM_LINKED_EXPLANATION_MAX_LENGTH
        ):
            raise ForumRuntimeError(
                "invalid-argument",
                "Linked answer explanation must be between 8 and 4000 characters.",
            )
        return clean

    def _write_feedback_projections(
        self,
        transaction: Any,
        answer_ref: Any,
        *,
        public_state: str,
        private_payload: Mapping[str, Any],
    ) -> None:
        """Write the public advisory projection and the author-only feedback."""
        transaction.set(
            answer_ref,
            _public_answer_projection(
                state=public_state,
                logical_inference_id=str(private_payload["logicalInferenceId"]),
                revision=int(private_payload["revision"]),
            ),
            merge=True,
        )
        feedback_ref = self.database.collection(
            FORUM_PRIVATE_FEEDBACK_COLLECTION
        ).document(answer_ref.id)
        transaction.set(
            feedback_ref,
            dict(private_payload),
            merge=True,
        )

    def delete_answer(self, *, answer_id: str, actor_id: str) -> dict[str, Any]:
        """Remove the author's own answer and its AI projections.

        The immutable inference run record is deliberately preserved for
        audit; only the public answer and its job/feedback projections are
        removed. An accepted answer cannot be deleted because the question
        thread still points at it.
        """
        answer_id = _document_id(answer_id)
        answer_ref = self.database.collection("forumAnswers").document(answer_id)

        @firestore.transactional
        def delete_answer(transaction: Any) -> dict[str, Any]:
            answer = _transaction_snapshot(transaction, answer_ref) or _MissingSnapshot()
            if not answer.exists:
                raise ForumRuntimeError("not-found", "Answer not found.")
            data = answer.to_dict()
            if _required(data, "authorId") != actor_id:
                raise ForumRuntimeError(
                    "permission-denied",
                    "Only the answer author may delete this answer.",
                )
            question_id = data.get("questionId")
            if isinstance(question_id, str) and question_id:
                question_ref = self.database.collection(
                    "forumQuestions"
                ).document(question_id)
                question = (
                    _transaction_snapshot(transaction, question_ref)
                    or _MissingSnapshot()
                )
                if (
                    question.exists
                    and question.to_dict().get("acceptedAnswerId") == answer_id
                ):
                    raise ForumRuntimeError(
                        "failed-precondition",
                        "An accepted answer cannot be deleted.",
                    )
            transaction.delete(answer_ref)
            transaction.delete(
                self.database.collection("forumAiJobs").document(answer_id)
            )
            transaction.delete(
                self.database.collection(
                    FORUM_PRIVATE_FEEDBACK_COLLECTION
                ).document(answer_id)
            )
            return {"answerId": answer_id, "deleted": True}

        return delete_answer(self.database.transaction())

    def delete_question(
        self, *, question_id: str, actor_id: str, now: datetime,
    ) -> dict[str, Any]:
        """Remove a question the student can see from their own forum view.

        Free-form questions are owned by their author: deleting one removes
        the whole thread, so every answer and its AI job/feedback projections
        are removed in the same transaction while the immutable inference runs
        remain preserved for audit. Canonical linked discussions are shared
        server content that other students also open, so a student may only
        remove one from their own list via a deterministic per-student marker;
        the canonical thread and everyone else's answers stay intact.
        """
        question_id = _document_id(question_id)
        question_ref = self.database.collection("forumQuestions").document(
            question_id
        )

        @firestore.transactional
        def delete_question(transaction: Any) -> dict[str, Any]:
            question = (
                _transaction_snapshot(transaction, question_ref)
                or _MissingSnapshot()
            )
            if not question.exists:
                raise ForumRuntimeError("not-found", "Question not found.")
            data = question.to_dict()
            if data.get("mode") == FORUM_MODE_LINKED:
                marker_ref = self.database.collection(
                    "forumQuestionDeletions"
                ).document(f"{actor_id}_{question_id}")
                transaction.set(marker_ref, {
                    "studentId": actor_id,
                    "questionId": question_id,
                    "deletedAt": now,
                })
                return {
                    "questionId": question_id,
                    "deleted": True,
                    "deletedAnswerCount": 0,
                    "scope": "viewer",
                }
            if _required(data, "authorId") != actor_id:
                raise ForumRuntimeError(
                    "permission-denied",
                    "Only the question author may delete this question.",
                )
            answer_query = self.database.collection("forumAnswers").where(
                "questionId", "==", question_id,
            )
            answer_ids = [
                snapshot.id
                for snapshot in _transaction_snapshots(transaction, answer_query)
            ]
            for answer_id in answer_ids:
                transaction.delete(
                    self.database.collection("forumAnswers").document(answer_id)
                )
                transaction.delete(
                    self.database.collection("forumAiJobs").document(answer_id)
                )
                transaction.delete(
                    self.database.collection(
                        FORUM_PRIVATE_FEEDBACK_COLLECTION
                    ).document(answer_id)
                )
            transaction.delete(question_ref)
            return {
                "questionId": question_id,
                "deleted": True,
                "deletedAnswerCount": len(answer_ids),
            }

        return delete_question(self.database.transaction())

    def _resolve_linked_correctness(
        self, data: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Resolve the protected answer key for a linked answer.

        The key is never copied into the public answer document, model input,
        run records, or guidance; only the deterministic correctness verdict
        and the authoritative source bindings are derived server-side.
        """
        discussion_id = data.get("questionId")
        unavailable = {
            "status": "unavailable", "answerIndex": None,
            "sourceQuestionId": None, "sourceContentVersion": None,
            "prompt": None,
        }
        if not isinstance(discussion_id, str) or not discussion_id:
            return unavailable
        discussion_ref = self.database.collection("forumQuestions").document(
            discussion_id
        )

        @firestore.transactional
        def resolve(transaction: Any) -> dict[str, Any]:
            discussion = _transaction_snapshot(
                transaction, discussion_ref,
            ) or _MissingSnapshot()
            if not discussion.exists:
                return unavailable
            discussion_data = discussion.to_dict()
            if discussion_data.get("mode") != FORUM_MODE_LINKED:
                return unavailable
            source_question_id = discussion_data.get("sourceQuestionId")
            source_content_version = discussion_data.get("sourceContentVersion")
            prompt = (discussion_data.get("promptSnapshot") or {}).get(
                "questionText"
            )
            if (
                not isinstance(source_question_id, str)
                or not source_question_id
                or not isinstance(source_content_version, str)
                or not source_content_version
            ):
                return {
                    **unavailable,
                    "sourceQuestionId": source_question_id,
                    "sourceContentVersion": source_content_version,
                    "prompt": prompt,
                }
            key_ref = self.database.collection(
                "questionAnswerKeys"
            ).document(source_question_id)
            key_snapshot = _transaction_snapshot(
                transaction, key_ref,
            ) or _MissingSnapshot()
            key = key_snapshot.to_dict() if key_snapshot.exists else {}
            answer_index = key.get("answerIndex")
            valid = (
                key_snapshot.exists
                and key.get("questionId") == source_question_id
                and key.get("contentVersion") == source_content_version
                and key.get("isActive") is True
                and isinstance(answer_index, int)
                and not isinstance(answer_index, bool)
                and 0 <= answer_index < LINKED_OPTION_COUNT
            )
            return {
                "status": "valid" if valid else "unavailable",
                "answerIndex": answer_index if valid else None,
                "sourceQuestionId": source_question_id,
                "sourceContentVersion": source_content_version,
                "prompt": prompt,
            }

        return resolve(self.database.transaction())

    def _evaluate_composite(
        self,
        data: Mapping[str, Any],
        bundle: ForumAiBundle,
        *,
        logical_inference_id: str,
    ) -> ForumOutcome:
        """Run deterministic correctness, relevance, and reasoning together."""
        mode = data.get("mode", FORUM_MODE_FREE_FORM)
        source = (
            self._resolve_linked_correctness(data)
            if mode == FORUM_MODE_LINKED
            else {
                "status": "unavailable", "answerIndex": None,
                "sourceQuestionId": None, "sourceContentVersion": None,
                "prompt": None,
            }
        )
        text = _answer_analysis_text(data) or ""
        reasoning_prediction = bundle.reasoning.predict(text)
        reasoning_label = str(reasoning_prediction.label)
        reasoning_code = {
            "sufficient_reasoning": "sufficient_reasoning",
            "needs_reasoning": "needs_reasoning",
            "uncertain": "uncertain",
        }.get(reasoning_label, "uncertain")
        prompt = source.get("prompt") or ""
        relevance_prediction = bundle.relevance.predict(prompt, text)
        relevance_label = str(relevance_prediction.label)
        if mode == FORUM_MODE_LINKED and source["status"] == "valid":
            correctness = (
                "correct"
                if data.get("selectedOption") == source["answerIndex"]
                else "incorrect"
            )
        elif mode == FORUM_MODE_LINKED:
            correctness = "unavailable"
        else:
            correctness = "not_applicable"
        decision = composite_decision(
            mode=mode,
            reasoning_label=reasoning_code,
            relevance_label=relevance_label,
            correctness=correctness,
        )
        private = _composite_feedback_payload(
            outcome=decision,
            revision=int(data.get("revision", 1)),
            logical_inference_id=logical_inference_id,
            bundle=bundle,
            source_question_id=source.get("sourceQuestionId"),
            source_content_version=source.get("sourceContentVersion"),
            reasoning_probability=float(reasoning_prediction.probability),
            relevance_probability=float(relevance_prediction.probability),
        )
        run_bindings: dict[str, Any] = {
            "sourceQuestionId": source.get("sourceQuestionId"),
            "sourceContentVersion": source.get("sourceContentVersion"),
            "selectedOption": data.get("selectedOption"),
            "explanationHash": sha256(text.encode("utf-8")).hexdigest(),
            "reasoningModelVersion": bundle.reasoning.model_version,
            "relevanceModelVersion": bundle.relevance.model_version,
            "reasoningArtifactIdentity": bundle.reasoning_artifact_identity,
            "relevanceArtifactIdentity": bundle.relevance_artifact_identity,
            "policyVersion": FORUM_COMPOSITE_POLICY_VERSION,
            "relevancePositiveThreshold": RELEVANCE_POSITIVE_THRESHOLD,
            "relevanceNegativeThreshold": RELEVANCE_NEGATIVE_THRESHOLD,
            "reasoningAbstentionThreshold": REASONING_ABSTENTION_THRESHOLD,
            "releaseId": bundle.release_id,
            "composite": {
                "publicState": decision["publicState"],
                "correctness": decision["correctness"],
                "relevance": decision["relevance"],
                "reasoning": decision["reasoning"],
                "privateLabel": decision["privateLabel"],
            },
        }
        return ForumOutcome(
            public_state=decision["publicState"],
            private=private,
            run_bindings=run_bindings,
        )

    def process_answer(
        self,
        answer_id: str,
        data: Mapping[str, Any],
        classifier: Any,
        *,
        event_id: str | None = None,
        now: datetime | None = None,
    ) -> str:
        answer_id = _document_id(answer_id)
        now = now or datetime.now(timezone.utc)
        audit_event_id = event_id or f"answer:{answer_id}"
        try:
            text = _answer_analysis_text(data)
            if text is None:
                raise ForumRuntimeError(
                    "failed-precondition", "Forum answer text is invalid.",
                )
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
        if isinstance(classifier, ForumAiBundle):
            reasoning = classifier.reasoning
            model_version = reasoning.model_version
            artifact_identity = str(
                getattr(reasoning, "artifact_sha256", model_version)
            )
            relevance_identity = classifier.relevance_artifact_identity
            claim_level = classifier.claim_level
            policy_version = FORUM_COMPOSITE_POLICY_VERSION
        else:
            reasoning = classifier
            model_version = (
                reasoning.model_version
                if reasoning is not None
                else "safe-fallback-v1"
            )
            artifact_identity = (
                str(getattr(reasoning, "artifact_sha256", model_version))
                if reasoning is not None
                else model_version
            )
            relevance_identity = None
            claim_level = (
                str(
                    getattr(
                        reasoning, "claim_level", FORUM_UNVALIDATED_CLAIM_LEVEL,
                    )
                )
                if reasoning is not None
                else FORUM_FALLBACK_CLAIM_LEVEL
            )
            policy_version = FORUM_AI_POLICY_VERSION
        content_hash = _answer_content_hash(data)
        if content_hash is None:
            raise ForumRuntimeError("failed-precondition", "Forum answer text is invalid.")
        logical_id = sha256(
            json.dumps({
                "answerId": answer_id,
                "revision": revision,
                "contentHash": content_hash,
                "modelVersion": model_version,
                "artifactIdentity": artifact_identity,
                "relevanceArtifactIdentity": relevance_identity,
                "claimLevel": claim_level,
                "policyVersion": policy_version,
            }, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        claim_or_state = self._claim_answer(
            answer_id=answer_id,
            logical_inference_id=logical_id,
            revision=revision,
            text_hash=content_hash,
            model_version=model_version,
            artifact_identity=artifact_identity,
            claim_level=claim_level,
            policy_version=policy_version,
            event_id=audit_event_id,
            now=now,
        )
        if isinstance(claim_or_state, str):
            return claim_or_state
        claim = claim_or_state
        try:
            outcome = self._evaluate_outcome(
                data, classifier, logical_inference_id=logical_id,
            )
            return self._finalize_answer(claim, outcome, now=now)
        except Exception as error:
            permanent = isinstance(error, (ForumRuntimeError, ValueError, TypeError))
            state = self._fail_answer(claim, error, permanent=permanent, now=now)
            if state == "retryable":
                raise
            return state

    def _evaluate_outcome(
        self,
        data: Mapping[str, Any],
        classifier: Any,
        *,
        logical_inference_id: str,
    ) -> ForumOutcome:
        """Return the composite outcome, or the legacy advisory outcome."""
        if isinstance(classifier, ForumAiBundle) and classifier.relevance is not None:
            return self._evaluate_composite(
                data, classifier, logical_inference_id=logical_inference_id,
            )
        if isinstance(classifier, ForumAiBundle):
            predictor = classifier.reasoning
        else:
            predictor = classifier
        text = _answer_analysis_text(data) or ""
        prediction = (
            predictor.predict(text) if predictor is not None else None
        )
        revision = int(data.get("revision", 1))
        if prediction is None:
            return ForumOutcome(
                public_state=FORUM_PUBLIC_STATE_NONE,
                private=_feedback_payload(
                    state="fallback", prediction=None, revision=revision,
                    logical_inference_id=logical_inference_id,
                ),
                run_bindings={},
                state="fallback",
            )
        return ForumOutcome(
            public_state=FORUM_PUBLIC_STATE_NONE,
            private=_feedback_payload(
                state="completed", prediction=prediction, revision=revision,
                logical_inference_id=logical_inference_id,
            ),
            run_bindings={},
        )

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
                or _answer_content_hash(current) != _answer_content_hash(data)
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
        policy_version: str = FORUM_AI_POLICY_VERSION,
    ) -> ForumAiClaim | str:
        answer_ref = self.database.collection("forumAnswers").document(answer_id)
        job_ref = self.database.collection("forumAiJobs").document(answer_id)
        run_ref = self.database.collection("forumAiRuns").document(logical_inference_id)

        @firestore.transactional
        def claim(transaction: Any) -> ForumAiClaim | str:
            answer_snapshot = _transaction_snapshot(transaction, answer_ref) or _MissingSnapshot()
            answer = answer_snapshot.to_dict() if answer_snapshot.exists else {}
            current_content_hash = _answer_content_hash(answer)
            if (
                answer.get("revision", 1) != revision
                or current_content_hash != text_hash
            ):
                return "superseded"
            job_snapshot = _transaction_snapshot(transaction, job_ref) or _MissingSnapshot()
            job = job_snapshot.to_dict() if job_snapshot.exists else {}
            state = job.get("state")
            feedback = answer.get("aiFeedback")
            private_ref = self.database.collection(
                FORUM_PRIVATE_FEEDBACK_COLLECTION
            ).document(answer_id)
            private_snapshot = _transaction_snapshot(transaction, private_ref) or _MissingSnapshot()
            private_feedback = private_snapshot.to_dict() if private_snapshot.exists else {}
            feedback_state = (
                feedback.get("state")
                if isinstance(feedback, Mapping)
                else private_feedback.get("state")
            )
            feedback_revision = (
                feedback.get("revision")
                if isinstance(feedback, Mapping)
                else private_feedback.get("revision")
            )
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
                    self._write_feedback_projections(
                        transaction,
                        answer_ref,
                        public_state=FORUM_PUBLIC_STATE_NONE,
                        private_payload=_feedback_payload(
                            state=state,
                            prediction=prediction,
                            revision=revision,
                            logical_inference_id=logical_inference_id,
                        ),
                    )
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
                "policyVersion": policy_version,
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
            self._write_feedback_projections(
                transaction,
                answer_ref,
                public_state=FORUM_PUBLIC_STATE_NONE,
                private_payload=_feedback_payload(
                    state="pending",
                    prediction=None,
                    revision=revision,
                    logical_inference_id=logical_inference_id,
                ),
            )
            return ForumAiClaim(
                answer_id=answer_id,
                logical_inference_id=logical_inference_id,
                revision=revision,
                text_hash=text_hash,
                model_version=model_version,
                artifact_identity=artifact_identity,
                claim_level=claim_level,
                policy_version=policy_version,
                fencing_generation=fencing_generation,
                attempt_count=attempt_count,
                event_id=event_id,
            )

        return claim(self.database.transaction())

    def _finalize_answer(
        self, claim: ForumAiClaim, outcome: ForumOutcome, *, now: datetime,
    ) -> str:
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
            current_content_hash = _answer_content_hash(answer)
            compatible = (
                job.get("state") == "processing"
                and job.get("logicalInferenceId") == claim.logical_inference_id
                and job.get("fencingGeneration") == claim.fencing_generation
                and job.get("artifactIdentity") == claim.artifact_identity
                and answer.get("revision", 1) == claim.revision
                and current_content_hash == claim.text_hash
            )
            result_state = outcome.state
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
                "contentHash": claim.text_hash,
                "modelVersion": claim.model_version,
                "artifactIdentity": claim.artifact_identity,
                "claimLevel": claim.claim_level,
                "policyVersion": claim.policy_version,
                "fencingGeneration": claim.fencing_generation,
                "claimEventId": claim.event_id,
                "state": run_state,
                "resultState": result_state,
                "prediction": None,
                **outcome.run_bindings,
                "createdAt": firestore.SERVER_TIMESTAMP,
            })
            if not compatible:
                return "superseded"
            self._write_feedback_projections(
                transaction,
                answer_ref,
                public_state=outcome.public_state,
                private_payload=outcome.private,
            )
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
                and _answer_content_hash(answer) == claim.text_hash
            ):
                self._write_feedback_projections(
                    transaction,
                    answer_ref,
                    public_state=FORUM_PUBLIC_STATE_NONE,
                    private_payload=_feedback_payload(
                        state="fallback",
                        prediction=None,
                        revision=claim.revision,
                        logical_inference_id=claim.logical_inference_id,
                    ),
                )
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


def load_forum_bundle(
    reasoning_path: Path = FORUM_MODEL_PATH,
    relevance_path: Path | None = None,
    manifest_path: Path = FORUM_MODEL_MANIFEST_PATH,
    *,
    registry_documents: list[Mapping[str, Any]] | None = None,
    evidence_mode: str | None = None,
    code_revision: str | None = None,
) -> ForumAiBundle | None:
    """Load the verified dual-component composite bundle (release manifest v2).

    The emulator fixture manifest keeps the reasoning-only path; every other
    activation requires a fully bound v2 release with both components, the
    frozen composite policy, and matching source/vendor/runtime/bundle hashes.
    """
    from logic_oasis_ai.forum_ai.classifier import ForumTextClassifier
    from logic_oasis_ai.forum_ai.relevance import ForumRelevanceClassifier

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            return None
        if manifest.get("evidenceState") == "emulator_fixture_only":
            if os.environ.get("FUNCTIONS_EMULATOR") != "true":
                return None
            if (
                manifest.get("artifactSha256")
                != sha256(reasoning_path.read_bytes()).hexdigest()
            ):
                return None
            reasoning = ForumTextClassifier.load(reasoning_path)
            if manifest.get("modelVersion") != reasoning.model_version:
                return None
            return ForumAiBundle(
                reasoning=reasoning,
                relevance=None,
                policy={},
                release_id="emulator-fixture",
                reasoning_artifact_identity=manifest["artifactSha256"],
                relevance_artifact_identity="",
                claim_level="unvalidated_model_output",
            )

        mode = evidence_mode or os.environ.get(
            "FORUM_MODEL_EVIDENCE_MODE", FORUM_REAL_EVALUATED_MODE,
        )
        revision = code_revision or os.environ.get(
            "FORUM_RUNTIME_CODE_REVISION", "",
        )
        documents = [] if registry_documents is None else list(registry_documents)
        compatible = [
            item for item in documents
            if isinstance(item, Mapping)
            and item.get("lifecycleStatus") == "released"
            and item.get("isActive") is True
            and item.get("deploymentScope") == FORUM_CONTROLLED_MODE
            and item.get("releaseId") == manifest.get("releaseId")
        ]
        if mode != FORUM_CONTROLLED_MODE or len(compatible) != 1:
            _log_forum_activation_failure("mode_or_registry_incompatible", manifest, revision)
            return None
        if any(
            compatible[0].get(key) != value
            for key, value in manifest.items()
        ):
            _log_forum_activation_failure("registry_manifest_mismatch", manifest, revision)
            return None
        relevance_path = relevance_path or (
            manifest_path.parent / "forum_relevance_model.joblib"
        )
        if not _controlled_forum_release_v2_valid(
            manifest, reasoning_path, relevance_path, manifest_path, revision,
        ):
            _log_forum_activation_failure("release_validation_failed", manifest, revision)
            return None
        reasoning = ForumTextClassifier.load(reasoning_path)
        relevance = ForumRelevanceClassifier.load(relevance_path)
        if manifest.get("reasoningModelVersion") != reasoning.model_version:
            _log_forum_activation_failure("classifier_version_mismatch", manifest, revision)
            return None
        if manifest.get("relevanceModelVersion") != relevance.model_version:
            _log_forum_activation_failure("classifier_version_mismatch", manifest, revision)
            return None
        reasoning.artifact_sha256 = manifest["reasoningArtifactSha256"]
        reasoning.claim_level = manifest["claimLevel"]
        relevance.artifact_sha256 = manifest["relevanceArtifactSha256"]
        relevance.claim_level = manifest["claimLevel"]
        return ForumAiBundle(
            reasoning=reasoning,
            relevance=relevance,
            policy=dict(COMPOSITE_POLICY_CONTRACT),
            release_id=manifest["releaseId"],
            reasoning_artifact_identity=manifest["reasoningArtifactSha256"],
            relevance_artifact_identity=manifest["relevanceArtifactSha256"],
            claim_level=manifest["claimLevel"],
        )
    except Exception:
        _log_forum_activation_failure(
            "activation_exception",
            locals().get("manifest"),
            code_revision or "",
        )
        return None


def _controlled_forum_release_v2_valid(
    manifest: Mapping[str, Any],
    reasoning_path: Path,
    relevance_path: Path,
    manifest_path: Path,
    code_revision: str,
) -> bool:
    from logic_oasis_ai.forum_ai.classifier import NAIVE_BAYES_VARIANTS

    if manifest.get("manifestSchemaVersion") != FORUM_RELEASE_MANIFEST_SCHEMA_V2:
        return False
    if any(
        manifest.get(key) != value
        for key, value in _CONTROLLED_RELEASE_VALUES.items()
    ):
        return False
    if (
        manifest.get("reasoningModelType") not in NAIVE_BAYES_VARIANTS
        or manifest.get("relevanceModelType") not in NAIVE_BAYES_VARIANTS
    ):
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
        for field in _V2_SHA256_FIELDS
    ):
        return False
    reasoning_bytes = reasoning_path.read_bytes()
    relevance_bytes = relevance_path.read_bytes()
    if sha256(reasoning_bytes).hexdigest() != manifest.get("reasoningArtifactSha256"):
        return False
    if sha256(relevance_bytes).hexdigest() != manifest.get("relevanceArtifactSha256"):
        return False
    if manifest.get("reasoningArtifactSizeBytes") != len(reasoning_bytes):
        return False
    if manifest.get("relevanceArtifactSizeBytes") != len(relevance_bytes):
        return False
    if manifest.get("candidateGateStatus") != "passed" or manifest.get("failedGates") != []:
        return False
    if manifest.get("semanticReproducibilityStatus") != "verified_same_runtime_contract":
        return False
    if manifest.get("baselineComparisonResult") not in {
        "naive_bayes_advantage_demonstrated",
        "no_controlled_scenario_advantage_demonstrated",
    }:
        return False
    if manifest.get("compositePolicy") != dict(COMPOSITE_POLICY_CONTRACT):
        return False
    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, Mapping) or set(dependencies) != {"joblib", "numpy", "scikit-learn"}:
        return False
    if any(
        importlib.metadata.version(name) != version
        for name, version in dependencies.items()
    ):
        return False
    vectorizer = manifest.get("vectorizerContract")
    relevance_vectorizer = manifest.get("relevanceVectorizerContract")
    if (
        not isinstance(vectorizer, Mapping)
        or vectorizer.get("family") != "TfidfVectorizer"
        or not isinstance(relevance_vectorizer, Mapping)
        or relevance_vectorizer.get("family") != "TfidfVectorizer"
        or float(relevance_vectorizer.get("positiveThreshold"))
        != RELEVANCE_POSITIVE_THRESHOLD
        or float(relevance_vectorizer.get("negativeThreshold"))
        != RELEVANCE_NEGATIVE_THRESHOLD
    ):
        return False
    source_hashes = manifest.get("sourceRuntimeHashes")
    vendor_hashes = manifest.get("vendorRuntimeHashes")
    if (
        source_hashes != vendor_hashes
        or not isinstance(vendor_hashes, Mapping)
        or set(vendor_hashes) != {"__init__.py", "classifier.py", "relevance.py"}
    ):
        return False
    vendor_root = manifest_path.parent / "vendor/logic_oasis_ai/forum_ai"
    if any(
        sha256((vendor_root / name).read_bytes()).hexdigest() != expected
        for name, expected in vendor_hashes.items()
    ):
        return False
    deployment_hashes = manifest.get("deploymentRuntimeHashes")
    if (
        not isinstance(deployment_hashes, Mapping)
        or set(deployment_hashes) != {"forum_runtime.py", "main.py"}
    ):
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
    if (
        not isinstance(forum_bundle, Mapping)
        or forum_bundle.get("bundleSchemaVersion") != "forum-runtime-bundle-v1"
        or forum_bundle.get("files") != vendor_hashes
    ):
        return False
    return True


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
