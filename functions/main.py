"""Python callable endpoints for server-authoritative Logic Oasis quizzes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from hashlib import sha256
import os
from pathlib import Path
import sys
from typing import Any, Callable
from uuid import uuid4

import firebase_admin
from firebase_admin import auth as admin_auth
from firebase_admin import firestore
from firebase_functions import https_fn
from firebase_functions import params
from firebase_functions import firestore_fn

# Deployments import only the generated vendor bundle.  The source-tree fallback
# is intentionally development/emulator-only and lets focused tests exercise
# the exact handler before the bundle has been built.
_FUNCTIONS_ROOT = Path(__file__).resolve().parent
_VENDOR_ROOT = _FUNCTIONS_ROOT / "vendor"
_AI_SOURCE_ROOT = _FUNCTIONS_ROOT.parent / "ai_pipeline"
_PACKAGE_ROOT = _VENDOR_ROOT if _VENDOR_ROOT.exists() else _AI_SOURCE_ROOT
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

from ai_runtime import AI_RUNTIME_SERVICE_ACCOUNT, FirestoreRuntimeGateway, RuntimeBundle, process_finalized_attempt
from logic_oasis_ai.sinks.firestore_sink import adaptive_assignment_id, subtopic_mastery_id
from parent_link_admin import (
    PARENT_LINK_ADMIN_SERVICE_ACCOUNT,
    ParentLinkAdminError,
    manage_parent_link,
    revoke_parent_link,
    verify_parent_link_admin,
)
from parent_link_context import (
    ParentLinkContextError,
    list_active_linked_children,
    verify_authenticated_parent,
)
from parent_link_email_delivery import deliver_parent_invitation
from parent_link_invitation import (
    PARENT_INVITATION_SERVICE_ACCOUNT,
    ParentInvitationError,
    VerifiedInvitationActor,
    accept_parent_link_invitation,
    create_parent_link_invitation,
    decline_parent_link_invitation,
    unlink_own_parent_link,
)

from quiz_session import (
    CLIENT_REPORTED_UNVERIFIED,
    HINT_TELEMETRY_NOT_SUPPORTED,
    MAX_RESPONSE_TIME_MS,
    QuizSessionError,
    client_completion,
    client_response,
    client_session,
    response_document_id,
)


QUESTION_COUNT = 5
MIN_BANK_QUESTION_COUNT = 8
MAX_BANK_QUESTION_COUNT = 10
SESSION_TTL_MINUTES = 30
FUNCTION_REGION = "asia-southeast1"
_TELEMETRY_FIELDS = frozenset({
    "responseTimeMs",
    "hintCount",
    "responseTimeQuality",
    "hintTelemetryStatus",
})
PARENT_INVITATION_EMAIL_HMAC_KEY = params.SecretParam(
    "PARENT_INVITATION_EMAIL_HMAC_KEY"
)
PARENT_INVITATION_SMTP_PASSWORD = params.SecretParam(
    "PARENT_INVITATION_SMTP_PASSWORD"
)
PARENT_INVITATION_CONTINUE_URL = params.StringParam(
    "PARENT_INVITATION_CONTINUE_URL",
    default="https://logic-oasis-fyp.web.app/parent-invitation",
)
PARENT_INVITATION_ANDROID_PACKAGE = params.StringParam(
    "PARENT_INVITATION_ANDROID_PACKAGE", default="com.example.logic_oasis"
)
# SMTP values deliberately have no source-controlled defaults. Firebase CLI
# requests them during deployment (or reads a local ignored functions/.env).
PARENT_INVITATION_SMTP_HOST = params.StringParam("PARENT_INVITATION_SMTP_HOST")
PARENT_INVITATION_SMTP_PORT = params.StringParam("PARENT_INVITATION_SMTP_PORT")
PARENT_INVITATION_SMTP_USERNAME = params.StringParam(
    "PARENT_INVITATION_SMTP_USERNAME"
)
PARENT_INVITATION_SMTP_FROM = params.StringParam("PARENT_INVITATION_SMTP_FROM")

try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

_db: Any | None = None


def firestore_db() -> Any:
    """Create the Admin client only when a callable actually executes.

    Firebase imports this module to discover functions before a local emulator
    or deploy process has Application Default Credentials. Deferring the client
    keeps discovery credential-free while production invocation still uses the
    function service account.
    """
    global _db
    if _db is None:
        _db = firestore.client()
    return _db


@lru_cache(maxsize=2)
def _runtime_bundle(runtime_root: Path) -> RuntimeBundle:
    """Hash one immutable deployed bundle once per warm Functions instance."""
    return RuntimeBundle.from_runtime_root(runtime_root)


def _auth_uid(request: https_fn.CallableRequest) -> str:
    if request.auth is None or not request.auth.uid:
        raise QuizSessionError("unauthenticated", "Sign in before starting a quiz.")
    return request.auth.uid


def _student_auth_uid(request: https_fn.CallableRequest) -> str:
    """Quiz callables accept only server-profiled learner identities."""
    uid = _auth_uid(request)
    snapshot = firestore_db().collection("users").document(uid).get()
    profile = snapshot.to_dict() if snapshot.exists else None
    if not isinstance(profile, dict) or profile.get("role") != "student":
        raise QuizSessionError("permission-denied", "Only a student account can take a quiz.")
    return uid


def _data(request: https_fn.CallableRequest) -> dict[str, Any]:
    if not isinstance(request.data, dict):
        raise QuizSessionError("invalid-argument", "Quiz request data must be an object.")
    return request.data


def _string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise QuizSessionError("invalid-argument", f"{key} is required.")
    return value


def _int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool):
        raise QuizSessionError("invalid-argument", f"{key} must be an integer.")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        # Callable JSON numbers can arrive as 4.0 even when Flutter supplied
        # an integer. Keep the trust boundary strict by accepting only values
        # with no fractional component.
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        # The Android callable bridge may serialize a whole number as text.
        # Accept only digits; fractional, signed, and arbitrary strings remain
        # invalid at this boundary.
        return int(value.strip())
    raise QuizSessionError("invalid-argument", f"{key} must be an integer.")


def _response_time_ms(data: dict[str, Any]) -> int:
    """Validate the only client-observed telemetry accepted by U3-R."""
    value = _int(data, "responseTimeMs")
    if value < 0 or value > MAX_RESPONSE_TIME_MS:
        raise QuizSessionError(
            "invalid-argument",
            f"responseTimeMs must be between 0 and {MAX_RESPONSE_TIME_MS}.",
        )
    return value


def _reject_finalization_telemetry(data: dict[str, Any]) -> None:
    """Finalization consumes sealed responses; it never accepts telemetry."""
    supplied = sorted(_TELEMETRY_FIELDS.intersection(data))
    if supplied:
        raise QuizSessionError(
            "invalid-argument",
            "finalizeQuizSession does not accept response telemetry.",
        )


def _bank_questions(
    bank: dict[str, Any],
    *,
    topic_id: str,
    subtopic_id: str,
    year_level: int,
    database: Any,
) -> list[dict[str, Any]]:
    """Return a complete, internally consistent server-owned bank only."""
    bank_id = bank.get("bankId")
    version = bank.get("version")
    difficulty = bank.get("difficultyLevel")
    if (
        not isinstance(bank_id, str)
        or not bank_id
        or not isinstance(version, str)
        or not version
        or difficulty not in {"Easy", "Moderate", "Hard"}
        or bank.get("topicId") != topic_id
        or bank.get("subtopicId") != subtopic_id
        or bank.get("yearLevel") != year_level
        or bank.get("isActive") is not True
    ):
        raise QuizSessionError("failed-precondition", "The selected question bank is not compatible.")

    question_ids = bank.get("questionIds")
    if (
        not isinstance(question_ids, list)
        or len(question_ids) < MIN_BANK_QUESTION_COUNT
        or len(question_ids) > MAX_BANK_QUESTION_COUNT
        or any(not isinstance(item, str) or not item for item in question_ids)
        or len(set(question_ids)) != len(question_ids)
    ):
        raise QuizSessionError("failed-precondition", "The active question bank is incomplete.")
    snapshots = database.get_all(
        [database.collection("questions").document(question_id) for question_id in question_ids]
    )
    questions = []
    for snapshot in snapshots:
        if snapshot.exists:
            question = dict(snapshot.to_dict() or {})
            question["questionId"] = snapshot.id
            questions.append(question)
    questions = [
        question for question in questions
        if question.get("bankId") == bank_id
        and question.get("topicId") == topic_id
        and question.get("subtopicId") == subtopic_id
        and question.get("yearLevel") == year_level
        and question.get("difficultyLevel") == difficulty
        and question.get("contentVersion") == version
        and question.get("isActive") is True
    ]
    if {question["questionId"] for question in questions} != set(question_ids):
        raise QuizSessionError("failed-precondition", "The active question bank has too few valid prompts.")
    if any(
        isinstance(question.get("order"), bool)
        or not isinstance(question.get("order"), int)
        or question["order"] < 0
        for question in questions
    ):
        raise QuizSessionError("failed-precondition", "The active question bank has invalid prompt order.")
    questions.sort(key=lambda item: (item["order"], item["questionId"]))
    skill_ids = {question.get("skillId") for question in questions}
    if (
        len(skill_ids) != 1
        or any(not isinstance(skill_id, str) or not skill_id for skill_id in skill_ids)
    ):
        raise QuizSessionError(
            "failed-precondition",
            "The active question bank must contain one skill per quiz session.",
        )
    key_snapshots = database.get_all(
        [database.collection("questionAnswerKeys").document(question["questionId"]) for question in questions]
    )
    keys = {snapshot.id: dict(snapshot.to_dict() or {}) for snapshot in key_snapshots if snapshot.exists}
    for question in questions:
        options = question.get("options")
        options_bm = question.get("optionsBm")
        key = keys.get(question["questionId"])
        answer_index = key.get("answerIndex") if key else None
        if (
            not isinstance(options, list)
            or not isinstance(options_bm, list)
            or len(options) != 4
            or len(options_bm) != 4
            or any(not isinstance(option, str) or not option for option in [*options, *options_bm])
            or not key
            or key.get("questionId") != question["questionId"]
            or key.get("contentVersion") != version
            or key.get("isActive") is not True
            or isinstance(answer_index, bool)
            or not isinstance(answer_index, int)
            or answer_index < 0
            or answer_index >= len(options)
            or not isinstance(key.get("explanation"), str)
            or not key.get("explanation")
            or not isinstance(key.get("explanationBm"), str)
            or not key.get("explanationBm")
        ):
            raise QuizSessionError("failed-precondition", "The active question bank has invalid answer content.")
    return questions


def _select_question_form(questions: list[dict[str, Any]], source_sequence: int) -> list[dict[str, Any]]:
    """Produce a bounded deterministic form from server-owned attempt order."""
    offset = (max(0, source_sequence - 1) * QUESTION_COUNT) % len(questions)
    rotated = [*questions[offset:], *questions[:offset]]
    return rotated[:QUESTION_COUNT]


def _next_form_sequence(student_id: str, subtopic_id: str, database: Any) -> int:
    """Read the server-owned completed-attempt counter without allocating it."""
    snapshot = (
        database.collection("studentSubtopicSequenceStates")
        .document(student_id)
        .collection("subtopics")
        .document(subtopic_id)
        .get()
    )
    if not snapshot.exists:
        return 1
    last_allocated = (snapshot.to_dict() or {}).get("lastAllocatedSequence")
    if isinstance(last_allocated, bool) or not isinstance(last_allocated, int) or last_allocated < 0:
        return 1
    return last_allocated + 1


def _active_easy_bank(topic_id: str, subtopic_id: str, year_level: int, *, database: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bank_docs = list(
        database.collection("questionBanks")
        .where("topicId", "==", topic_id)
        .where("subtopicId", "==", subtopic_id)
        .where("yearLevel", "==", year_level)
        .where("difficultyLevel", "==", "Easy")
        .where("isActive", "==", True)
        .stream()
    )
    for snapshot in sorted(bank_docs, key=lambda item: item.id):
        bank = dict(snapshot.to_dict() or {})
        bank["bankId"] = snapshot.id
        try:
            return bank, _bank_questions(
                bank,
                topic_id=topic_id,
                subtopic_id=subtopic_id,
                year_level=year_level,
                database=database,
            )
        except QuizSessionError:
            continue
    raise QuizSessionError("failed-precondition", "No complete active Easy question bank is available.")


def _compatible_adaptive_assignment(
    *,
    student_id: str,
    topic_id: str,
    subtopic_id: str,
    year_level: int,
    database: Any,
) -> dict[str, Any] | None:
    """Accept only a current U8 runtime-created assignment for this learner.

    A document is not treated as trustworthy merely because it occupies the
    predictable projection path. Its source must be the matching finalized
    runtime attempt, and its sequence must still match the current safe
    mastery projection. This prevents seed/demo or stale data from becoming a
    normal quiz-start path.
    """
    assignment_id = adaptive_assignment_id(student_id, subtopic_id)
    snapshot = database.collection("adaptiveAssignments").document(assignment_id).get()
    if not snapshot.exists:
        return None
    assignment = dict(snapshot.to_dict() or {})
    source_attempt_id = assignment.get("sourceAttemptId")
    source_sequence = assignment.get("sourceAttemptSequence")
    bank_id = assignment.get("bankId")
    policy_version = assignment.get("policyVersion")
    difficulty = assignment.get("difficultyLevel")
    if (
        assignment.get("studentId") != student_id
        or assignment.get("subtopicId") != subtopic_id
        or assignment.get("status") != "assigned"
        or assignment.get("dataSource") != "runtime_callable"
        or not isinstance(source_attempt_id, str)
        or not source_attempt_id
        or isinstance(source_sequence, bool)
        or not isinstance(source_sequence, int)
        or source_sequence < 1
        or not isinstance(bank_id, str)
        or not bank_id
        or difficulty not in {"Easy", "Moderate", "Hard"}
        or not isinstance(policy_version, str)
        or not policy_version
    ):
        return None

    attempt_snapshot = database.collection("quizAttempts").document(source_attempt_id).get()
    if not attempt_snapshot.exists:
        return None
    attempt = dict(attempt_snapshot.to_dict() or {})
    if (
        attempt.get("attemptId") != source_attempt_id
        or attempt.get("studentId") != student_id
        or attempt.get("topicId") != topic_id
        or attempt.get("subtopicId") != subtopic_id
        or attempt.get("yearLevel") != year_level
        or attempt.get("sourceAttemptSequence") != source_sequence
        or attempt.get("validationStatus") != "finalized"
        or attempt.get("finalizationStatus") != "finalized"
        or attempt.get("dataSource") != "runtime_callable"
    ):
        return None

    mastery_id = subtopic_mastery_id(student_id, year_level, topic_id, subtopic_id)
    mastery_snapshot = database.collection("subtopicMastery").document(mastery_id).get()
    if not mastery_snapshot.exists:
        return None
    mastery = dict(mastery_snapshot.to_dict() or {})
    if (
        mastery.get("studentId") != student_id
        or mastery.get("yearLevel") != year_level
        or mastery.get("topicId") != topic_id
        or mastery.get("subtopicId") != subtopic_id
        or mastery.get("lastSourceAttemptId") != source_attempt_id
        or mastery.get("sourceAttemptSequence") != source_sequence
    ):
        return None

    return {
        "assignmentId": assignment_id,
        "assignmentSource": "runtime_adaptive",
        "adaptivePolicyVersion": policy_version,
        "bankId": bank_id,
        "difficultyLevel": difficulty,
        "assignedFromAttemptId": source_attempt_id,
        "assignedFromAttemptSequence": source_sequence,
        "formSequence": source_sequence + 1,
    }


def _start_bank_selection(
    *,
    student_id: str,
    topic_id: str,
    subtopic_id: str,
    year_level: int,
    database: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    assignment = _compatible_adaptive_assignment(
        student_id=student_id,
        topic_id=topic_id,
        subtopic_id=subtopic_id,
        year_level=year_level,
        database=database,
    )
    if assignment is not None:
        try:
            snapshot = database.collection("questionBanks").document(assignment["bankId"]).get()
            if snapshot.exists:
                bank = dict(snapshot.to_dict() or {})
                bank["bankId"] = snapshot.id
                if bank.get("difficultyLevel") == assignment["difficultyLevel"]:
                    questions = _bank_questions(
                        bank,
                        topic_id=topic_id,
                        subtopic_id=subtopic_id,
                        year_level=year_level,
                        database=database,
                    )
                    return bank, questions, assignment
        except QuizSessionError:
            # A malformed/stale server projection must not block the learner or
            # turn into a client-controlled bank choice.
            pass

    bank, questions = _active_easy_bank(
        topic_id,
        subtopic_id,
        year_level,
        database=database,
    )
    return bank, questions, {
        "assignmentId": "cold_start_easy",
        "assignmentSource": "cold_start_easy",
        "adaptivePolicyVersion": "adaptive-policy-v1",
        "bankId": bank["bankId"],
        "difficultyLevel": "Easy",
        "assignedFromAttemptId": None,
        "assignedFromAttemptSequence": None,
        "formSequence": _next_form_sequence(student_id, subtopic_id, database),
    }


def _active_session_reservation_id(
    *, student_id: str, topic_id: str, subtopic_id: str, year_level: int
) -> str:
    """Return an opaque server-owned key for one learner's active quiz scope."""
    material = "\x00".join((student_id, topic_id, subtopic_id, str(year_level)))
    return sha256(material.encode("utf-8")).hexdigest()


def _session_questions(session: dict[str, Any], database: Any) -> list[dict[str, Any]]:
    """Rehydrate the already sealed prompt order for an idempotent start retry."""
    question_ids = session.get("questionIds")
    expected_count = session.get("expectedResponseCount")
    if (
        not isinstance(question_ids, list)
        or not question_ids
        or any(not isinstance(question_id, str) or not question_id for question_id in question_ids)
        or len(set(question_ids)) != len(question_ids)
        or expected_count != len(question_ids)
    ):
        raise QuizSessionError("failed-precondition", "The active quiz session is invalid. Start a new quiz.")
    snapshots = database.get_all(
        [database.collection("questions").document(question_id) for question_id in question_ids]
    )
    by_id = {
        snapshot.id: {**dict(snapshot.to_dict() or {}), "questionId": snapshot.id}
        for snapshot in snapshots
        if snapshot.exists
    }
    if set(by_id) != set(question_ids):
        raise QuizSessionError("failed-precondition", "The active quiz content is unavailable. Start a new quiz.")
    return [by_id[question_id] for question_id in question_ids]


def _is_active_session(session: dict[str, Any], *, now: datetime) -> bool:
    expires_at = session.get("expiresAt")
    return (
        session.get("status") == "active"
        and isinstance(expires_at, datetime)
        and now < expires_at
    )


def _active_session_from_reservation(
    *,
    reservation: dict[str, Any],
    student_id: str,
    topic_id: str,
    subtopic_id: str,
    year_level: int,
    now: datetime,
    database: Any,
    transaction: Any | None = None,
) -> dict[str, Any] | None:
    """Return only a still-live reservation whose server-owned scope matches."""
    session_id = reservation.get("sessionId")
    if (
        reservation.get("studentId") != student_id
        or reservation.get("topicId") != topic_id
        or reservation.get("subtopicId") != subtopic_id
        or reservation.get("yearLevel") != year_level
        or not isinstance(session_id, str)
        or not session_id
    ):
        return None
    session_ref = database.collection("quizSessions").document(session_id)
    snapshot = session_ref.get(transaction=transaction) if transaction is not None else session_ref.get()
    if not snapshot.exists:
        return None
    session = dict(snapshot.to_dict() or {})
    if (
        session.get("sessionId") != session_id
        or session.get("studentId") != student_id
        or session.get("topicId") != topic_id
        or session.get("subtopicId") != subtopic_id
        or session.get("yearLevel") != year_level
        or not _is_active_session(session, now=now)
    ):
        return None
    return session


def _reserve_or_reuse_active_session(
    *,
    session: dict[str, Any],
    student_id: str,
    topic_id: str,
    subtopic_id: str,
    year_level: int,
    now: datetime,
    database: Any,
) -> tuple[dict[str, Any], bool]:
    """Atomically create one active session or return the existing retry target."""
    reservation_ref = database.collection("activeQuizSessionStarts").document(
        _active_session_reservation_id(
            student_id=student_id,
            topic_id=topic_id,
            subtopic_id=subtopic_id,
            year_level=year_level,
        )
    )
    session_ref = database.collection("quizSessions").document(session["sessionId"])
    reservation = {
        "sessionId": session["sessionId"],
        "studentId": student_id,
        "topicId": topic_id,
        "subtopicId": subtopic_id,
        "yearLevel": year_level,
        "expiresAt": session["expiresAt"],
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }

    @firestore.transactional
    def reserve(transaction: firestore.Transaction) -> tuple[dict[str, Any], bool]:
        current_snapshot = reservation_ref.get(transaction=transaction)
        if current_snapshot.exists:
            existing = _active_session_from_reservation(
                reservation=dict(current_snapshot.to_dict() or {}),
                student_id=student_id,
                topic_id=topic_id,
                subtopic_id=subtopic_id,
                year_level=year_level,
                now=now,
                database=database,
                transaction=transaction,
            )
            if existing is not None:
                return existing, False
        transaction.create(session_ref, session)
        transaction.set(reservation_ref, reservation)
        return session, True

    return reserve(database.transaction())


def start_quiz_session(data: dict[str, Any], student_id: str) -> dict[str, Any]:
    topic_id = _string(data, "topicId")
    subtopic_id = _string(data, "subtopicId")
    year_level = _int(data, "yearLevel")
    database = firestore_db()
    now = datetime.now(timezone.utc)
    reservation_ref = database.collection("activeQuizSessionStarts").document(
        _active_session_reservation_id(
            student_id=student_id,
            topic_id=topic_id,
            subtopic_id=subtopic_id,
            year_level=year_level,
        )
    )
    existing_reservation = reservation_ref.get()
    if existing_reservation.exists:
        existing = _active_session_from_reservation(
            reservation=dict(existing_reservation.to_dict() or {}),
            student_id=student_id,
            topic_id=topic_id,
            subtopic_id=subtopic_id,
            year_level=year_level,
            now=now,
            database=database,
        )
        if existing is not None:
            return client_session(existing, _session_questions(existing, database))
    bank, questions, assignment = _start_bank_selection(
        student_id=student_id,
        topic_id=topic_id,
        subtopic_id=subtopic_id,
        year_level=year_level,
        database=database,
    )
    selected_questions = _select_question_form(questions, assignment["formSequence"])
    session_id = f"session_{uuid4().hex}"
    session = {
        "sessionId": session_id,
        "attemptId": f"attempt_{uuid4().hex}",
        "studentId": student_id,
        "assignmentId": assignment["assignmentId"],
        "assignmentSource": assignment["assignmentSource"],
        # The policy version is selected only from the trusted runtime
        # assignment; clients cannot choose a policy or bank.
        "adaptivePolicyVersion": assignment["adaptivePolicyVersion"],
        "assignedFromAttemptId": assignment["assignedFromAttemptId"],
        "assignedFromAttemptSequence": assignment["assignedFromAttemptSequence"],
        "formSequence": assignment["formSequence"],
        "bankId": bank["bankId"],
        "topicId": topic_id,
        "subtopicId": subtopic_id,
        "yearLevel": year_level,
        "difficultyLevel": assignment["difficultyLevel"],
        "contentVersion": bank["version"],
        "questionIds": [question["questionId"] for question in selected_questions],
        "expectedResponseCount": len(selected_questions),
        "status": "active",
        "validatedResponseCount": 0,
        "startedAt": now,
        "expiresAt": now + timedelta(minutes=SESSION_TTL_MINUTES),
        "finalizedAt": None,
    }
    active_session, created = _reserve_or_reuse_active_session(
        session=session,
        student_id=student_id,
        topic_id=topic_id,
        subtopic_id=subtopic_id,
        year_level=year_level,
        now=now,
        database=database,
    )
    if not created:
        return client_session(active_session, _session_questions(active_session, database))
    return client_session(active_session, selected_questions)


def submit_quiz_response(data: dict[str, Any], student_id: str) -> dict[str, Any]:
    session_id = _string(data, "sessionId")
    question_id = _string(data, "questionId")
    selected_index = _int(data, "selectedIndex")
    sequence_index = _int(data, "sequenceIndex")
    idempotency_key = _string(data, "idempotencyKey")
    response_time_ms = _response_time_ms(data)
    if selected_index < 0:
        raise QuizSessionError("invalid-argument", "selectedIndex must not be negative.")
    database = firestore_db()
    response_ref = database.collection("questionResponses").document(response_document_id(session_id, sequence_index))
    session_ref = database.collection("quizSessions").document(session_id)

    @firestore.transactional
    def submit(transaction: firestore.Transaction) -> dict[str, Any]:
        session_snapshot = session_ref.get(transaction=transaction)
        if not session_snapshot.exists:
            raise QuizSessionError("not-found", "Quiz session not found.")
        session = dict(session_snapshot.to_dict() or {})
        if session.get("studentId") != student_id:
            raise QuizSessionError("permission-denied", "This quiz session belongs to another student.")
        if session.get("status") != "active":
            raise QuizSessionError("failed-precondition", "Quiz session is not active.")
        expires_at = session.get("expiresAt")
        if isinstance(expires_at, datetime) and datetime.now(timezone.utc) >= expires_at:
            transaction.update(session_ref, {"status": "expired"})
            raise QuizSessionError("deadline-exceeded", "Quiz session expired. Start a new quiz.")
        question_ids = session.get("questionIds")
        if not isinstance(question_ids, list) or sequence_index < 0 or sequence_index >= len(question_ids):
            raise QuizSessionError("invalid-argument", "The response sequence is invalid.")
        if question_ids[sequence_index] != question_id:
            raise QuizSessionError("failed-precondition", "Submit quiz responses in the assigned order.")
        existing = response_ref.get(transaction=transaction)
        if existing.exists:
            response = dict(existing.to_dict() or {})
            if (
                response.get("idempotencyKey") == idempotency_key
                and response.get("questionId") == question_id
                and response.get("selectedIndex") == selected_index
            ):
                return response
            raise QuizSessionError("already-exists", "This question response is already sealed.")
        question_ref = database.collection("questions").document(question_id)
        key_ref = database.collection("questionAnswerKeys").document(question_id)
        prior_response_ref = (
            database.collection("questionResponses").document(
            response_document_id(session_id, sequence_index - 1)
            )
            if sequence_index > 0
            else None
        )
        content_refs = [question_ref, key_ref]
        if prior_response_ref is not None:
            content_refs.append(prior_response_ref)
        content_snapshots = {
            snapshot.reference.path: snapshot
            for snapshot in transaction.get_all(content_refs)
        }
        question_snapshot = content_snapshots[question_ref.path]
        key_snapshot = content_snapshots[key_ref.path]
        if prior_response_ref is not None:
            prior_response = content_snapshots[prior_response_ref.path]
            if not prior_response.exists:
                raise QuizSessionError(
                    "failed-precondition",
                    "Submit quiz responses in sequence.",
                )
        if not question_snapshot.exists or not key_snapshot.exists:
            raise QuizSessionError("failed-precondition", "Quiz content is no longer available.")
        question = dict(question_snapshot.to_dict() or {})
        answer_key = dict(key_snapshot.to_dict() or {})
        if (
            question.get("bankId") != session.get("bankId")
            or question.get("contentVersion") != session.get("contentVersion")
            or answer_key.get("contentVersion") != session.get("contentVersion")
            or not question.get("isActive")
            or not answer_key.get("isActive")
        ):
            raise QuizSessionError("failed-precondition", "The quiz content changed. Start a new quiz.")
        options = question.get("options")
        answer_index = answer_key.get("answerIndex")
        if (
            not isinstance(options, list)
            or selected_index >= len(options)
            or isinstance(answer_index, bool)
            or not isinstance(answer_index, int)
            or answer_index < 0
            or answer_index >= len(options)
        ):
            raise QuizSessionError("failed-precondition", "The quiz answer key is invalid.")
        response = {
            "responseId": response_ref.id,
            "sessionId": session_id,
            "attemptId": session["attemptId"],
            "studentId": student_id,
            "questionId": question_id,
            "skillId": question["skillId"],
            "bankId": session["bankId"],
            "questionVersion": question["contentVersion"],
            "contentVersion": session["contentVersion"],
            # FYP1 does not yet calculate learner-wide exposure.  Persist a
            # server-derived availability marker so exports never invent a
            # zero exposure value from a client request.
            "priorExposureCount": question.get("priorExposureCount"),
            "selectedIndex": selected_index,
            "serverIsCorrect": selected_index == answer_index,
            "explanation": answer_key.get("explanation", ""),
            "explanationBm": answer_key.get("explanationBm", ""),
            "validationStatus": "validated",
            "responseTimeMs": response_time_ms,
            # This is client-observed timing, never trusted correctness data.
            "responseTimeQuality": CLIENT_REPORTED_UNVERIFIED,
            # FYP1 has no auditable hint action. Never accept client hint data.
            "hintCount": 0,
            "hintTelemetryStatus": HINT_TELEMETRY_NOT_SUPPORTED,
            "sequenceIndex": sequence_index,
            "idempotencyKey": idempotency_key,
            "createdAt": firestore.SERVER_TIMESTAMP,
        }
        transaction.create(response_ref, response)
        transaction.update(session_ref, {"validatedResponseCount": firestore.Increment(1)})
        return response

    return client_response(submit(database.transaction()))


def finalize_quiz_session(data: dict[str, Any], student_id: str) -> dict[str, Any]:
    session_id = _string(data, "sessionId")
    _reject_finalization_telemetry(data)
    database = firestore_db()
    session_ref = database.collection("quizSessions").document(session_id)

    @firestore.transactional
    def finalize(transaction: firestore.Transaction) -> dict[str, Any]:
        session_snapshot = session_ref.get(transaction=transaction)
        if not session_snapshot.exists:
            raise QuizSessionError("not-found", "Quiz session not found.")
        session = dict(session_snapshot.to_dict() or {})
        if session.get("studentId") != student_id:
            raise QuizSessionError("permission-denied", "This quiz session belongs to another student.")
        attempt_ref = database.collection("quizAttempts").document(session["attemptId"])
        # Idempotent duplicate finalization must return before touching the
        # per-subtopic sequence counter.
        if session.get("status") == "finalized":
            attempt_snapshot = attempt_ref.get(transaction=transaction)
            if not attempt_snapshot.exists:
                raise QuizSessionError("failed-precondition", "Finalized attempt is unavailable.")
            return dict(attempt_snapshot.to_dict() or {})
        if session.get("status") != "active":
            raise QuizSessionError("failed-precondition", "Quiz session is not active.")
        expires_at = session.get("expiresAt")
        if isinstance(expires_at, datetime) and datetime.now(timezone.utc) >= expires_at:
            transaction.update(session_ref, {"status": "expired"})
            raise QuizSessionError("deadline-exceeded", "Quiz session expired. Start a new quiz.")
        question_ids = session.get("questionIds")
        count = session.get("validatedResponseCount")
        expected_response_count = session.get("expectedResponseCount")
        if (
            not isinstance(question_ids, list)
            or expected_response_count != len(question_ids)
            or count != expected_response_count
        ):
            raise QuizSessionError("failed-precondition", "Every question must be securely checked first.")
        response_refs = [
            database.collection("questionResponses").document(response_document_id(session_id, index))
            for index in range(len(question_ids))
        ]
        response_snapshots = {
            snapshot.reference.path: snapshot
            for snapshot in transaction.get_all(response_refs)
        }
        responses = []
        for index, response_ref in enumerate(response_refs):
            response_snapshot = response_snapshots[response_ref.path]
            if not response_snapshot.exists:
                raise QuizSessionError("failed-precondition", "A validated response is missing.")
            response = dict(response_snapshot.to_dict() or {})
            if response.get("validationStatus") != "validated" or response.get("questionId") != question_ids[index]:
                raise QuizSessionError("failed-precondition", "Response lineage is invalid.")
            responses.append(response)
        correct_count = sum(1 for response in responses if response.get("serverIsCorrect") is True)
        total = len(responses)
        sequence_ref = (
            database.collection("studentSubtopicSequenceStates")
            .document(student_id)
            .collection("subtopics")
            .document(session["subtopicId"])
        )
        sequence_snapshot = sequence_ref.get(transaction=transaction)
        sequence_state = dict(sequence_snapshot.to_dict() or {}) if sequence_snapshot.exists else {}
        previous_sequence = sequence_state.get("lastAllocatedSequence", 0)
        if isinstance(previous_sequence, bool) or not isinstance(previous_sequence, int) or previous_sequence < 0:
            raise QuizSessionError("failed-precondition", "Attempt sequence state is invalid.")
        source_attempt_sequence = previous_sequence + 1
        correct_rate = correct_count / total
        mastery_ref = database.collection("subtopicMastery").document(
            f'{student_id}_y{session["yearLevel"]}_{session["topicId"]}_{session["subtopicId"]}'
        )
        mastery_snapshot = mastery_ref.get(transaction=transaction)
        existing_mastery = dict(mastery_snapshot.to_dict() or {}) if mastery_snapshot.exists else {}
        previous_rate = existing_mastery.get("bestCorrectRate", 0.0)
        if isinstance(previous_rate, bool) or not isinstance(previous_rate, (int, float)):
            previous_rate = 0.0
        best_correct_rate = max(float(previous_rate), correct_rate)
        mastery_level = (
            "Strong" if best_correct_rate >= 0.8 else
            "Moderate" if best_correct_rate > 0.5 else
            "Weak" if best_correct_rate > 0 else "New"
        )
        attempt = {
            "attemptId": session["attemptId"], "sessionId": session_id, "studentId": student_id,
            "topicId": session["topicId"], "subtopicId": session["subtopicId"],
            "yearLevel": session["yearLevel"], "bankId": session["bankId"],
            "difficultyLevel": session["difficultyLevel"], "contentVersion": session["contentVersion"],
            "assignmentId": session["assignmentId"],
            "assignmentSource": session["assignmentSource"],
            "adaptivePolicyVersion": session["adaptivePolicyVersion"],
            "assignedFromAttemptId": session.get("assignedFromAttemptId"),
            "assignedFromAttemptSequence": session.get("assignedFromAttemptSequence"),
            "formSequence": session.get("formSequence"),
            "correctCount": correct_count, "totalQuestions": total,
            "score": round(correct_count * 100 / total),
            "trustedCorrectCount": correct_count,
            "trustedScore": round(correct_count * 100 / total),
            "responseCount": total,
            "responseIds": [response["responseId"] for response in responses],
            "validationStatus": "finalized",
            "finalizationStatus": "finalized",
            "processingStatus": "pending",
            "dataSource": "runtime_callable",
            "sourceAttemptSequence": source_attempt_sequence,
            "startedAt": session["startedAt"],
            "deviceSessionId": "not_recorded",
            "createdAt": firestore.SERVER_TIMESTAMP,
            "finalizedAt": firestore.SERVER_TIMESTAMP,
        }
        transaction.create(attempt_ref, attempt)
        # This bounded completion projection is written in the same trusted
        # finalization transaction, so a restart cannot wait for the U8 job to
        # keep progression unlocked. U8 replaces the pending marker with its
        # BKT-derived, client-safe summary for this same attempt sequence.
        transaction.set(
            mastery_ref,
            {
                "studentId": student_id,
                "yearLevel": session["yearLevel"],
                "topicId": session["topicId"],
                "subtopicId": session["subtopicId"],
                "bestCorrectRate": best_correct_rate,
                "completed": best_correct_rate > 0.5,
                "masteryLevel": mastery_level,
                "lastSourceAttemptId": session["attemptId"],
                "sourceAttemptSequence": source_attempt_sequence,
                "projectionStatus": "finalized_pending_ai",
                "updatedAt": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        transaction.set(
            sequence_ref,
            {
                "studentId": student_id,
                "subtopicId": session["subtopicId"],
                "lastAllocatedSequence": source_attempt_sequence,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            },
        )
        transaction.update(session_ref, {"status": "finalized", "finalizedAt": firestore.SERVER_TIMESTAMP})
        return attempt

    return client_completion(finalize(database.transaction()))


_ERROR_CODES: dict[str, https_fn.FunctionsErrorCode] = {
    "unauthenticated": https_fn.FunctionsErrorCode.UNAUTHENTICATED,
    "permission-denied": https_fn.FunctionsErrorCode.PERMISSION_DENIED,
    "invalid-argument": https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
    "not-found": https_fn.FunctionsErrorCode.NOT_FOUND,
    "already-exists": https_fn.FunctionsErrorCode.ALREADY_EXISTS,
    "failed-precondition": https_fn.FunctionsErrorCode.FAILED_PRECONDITION,
    "deadline-exceeded": https_fn.FunctionsErrorCode.DEADLINE_EXCEEDED,
    "resource-exhausted": https_fn.FunctionsErrorCode.RESOURCE_EXHAUSTED,
    "unavailable": https_fn.FunctionsErrorCode.UNAVAILABLE,
}


def _call(handler: Callable[[dict[str, Any], str], dict[str, Any]], request: https_fn.CallableRequest) -> dict[str, Any]:
    try:
        return handler(_data(request), _student_auth_uid(request))
    except QuizSessionError as error:
        raise https_fn.HttpsError(_ERROR_CODES.get(error.code, https_fn.FunctionsErrorCode.INTERNAL), str(error))


@https_fn.on_call(region=FUNCTION_REGION)
def startQuizSession(request: https_fn.CallableRequest) -> dict[str, Any]:
    return _call(start_quiz_session, request)


@https_fn.on_call(region=FUNCTION_REGION)
def submitQuizResponse(request: https_fn.CallableRequest) -> dict[str, Any]:
    return _call(submit_quiz_response, request)


@https_fn.on_call(region=FUNCTION_REGION)
def finalizeQuizSession(request: https_fn.CallableRequest) -> dict[str, Any]:
    return _call(finalize_quiz_session, request)


def _parent_link_call(
    handler: Callable[[dict[str, Any], Any, Any], dict[str, str]],
    request: https_fn.CallableRequest,
) -> dict[str, str]:
    try:
        admin = verify_parent_link_admin(request)
        data = _data(request)
        return handler(data, admin, firestore_db())
    except ParentLinkAdminError as error:
        raise https_fn.HttpsError(
            _ERROR_CODES.get(error.code, https_fn.FunctionsErrorCode.INTERNAL),
            str(error),
        )
    except QuizSessionError as error:
        raise https_fn.HttpsError(
            _ERROR_CODES.get(error.code, https_fn.FunctionsErrorCode.INTERNAL),
            str(error),
        )


def _parent_context_call(request: https_fn.CallableRequest) -> dict[str, Any]:
    try:
        parent = verify_authenticated_parent(request)
        return list_active_linked_children(_data(request), parent, firestore_db())
    except ParentLinkContextError as error:
        raise https_fn.HttpsError(
            _ERROR_CODES.get(error.code, https_fn.FunctionsErrorCode.INTERNAL),
            str(error),
        )


def _parent_invitation_actor(request: https_fn.CallableRequest) -> VerifiedInvitationActor:
    auth_context = getattr(request, "auth", None)
    uid = getattr(auth_context, "uid", None)
    token = getattr(auth_context, "token", {}) or {}
    if not isinstance(uid, str) or not uid:
        raise ParentInvitationError("unauthenticated", "Sign in before using parent invitations.")
    # Callable authentication validates the token before this handler runs,
    # but invitation acceptance changes a durable relationship. Re-check the
    # bearer token with revocation enabled so a revoked account cannot replay
    # a previously opened email link.
    raw_request = getattr(request, "raw_request", None)
    headers = getattr(raw_request, "headers", {}) or {}
    authorization = headers.get("Authorization") or headers.get("authorization")
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        raise ParentInvitationError("unauthenticated", "Refresh your secure sign-in and try again.")
    try:
        verified_token = admin_auth.verify_id_token(
            authorization.removeprefix("Bearer "), check_revoked=True,
        )
    except Exception as error:
        raise ParentInvitationError("unauthenticated", "Refresh your secure sign-in and try again.") from error
    if verified_token.get("uid") != uid:
        raise ParentInvitationError("unauthenticated", "Refresh your secure sign-in and try again.")
    email = token.get("email")
    verified = token.get("email_verified") is True
    profile_snapshot = firestore_db().collection("users").document(uid).get()
    profile = profile_snapshot.to_dict() if profile_snapshot.exists else None
    return VerifiedInvitationActor(
        uid=uid,
        email=email if isinstance(email, str) else "",
        email_verified=verified,
        role=profile.get("role") if isinstance(profile, dict) else None,
    )


def _parent_invitation_call(
    handler: Callable[..., dict[str, Any]], request: https_fn.CallableRequest, *, delivery: bool = False,
) -> dict[str, Any]:
    try:
        actor = _parent_invitation_actor(request)
        kwargs: dict[str, Any] = {"email_hmac_key": os.environ.get("PARENT_INVITATION_EMAIL_HMAC_KEY", "")}
        if delivery:
            kwargs["deliver"] = deliver_parent_invitation
        return handler(_data(request), actor, firestore_db(), **kwargs)
    except ParentInvitationError as error:
        raise https_fn.HttpsError(
            _ERROR_CODES.get(error.code, https_fn.FunctionsErrorCode.INTERNAL), str(error)
        )
    except QuizSessionError as error:
        raise https_fn.HttpsError(
            _ERROR_CODES.get(error.code, https_fn.FunctionsErrorCode.INTERNAL), str(error)
        )


@https_fn.on_call(
    region=FUNCTION_REGION,
    service_account=PARENT_LINK_ADMIN_SERVICE_ACCOUNT,
)
def getLinkedChildren(request: https_fn.CallableRequest) -> dict[str, Any]:
    return _parent_context_call(request)


@https_fn.on_call(
    region=FUNCTION_REGION,
    service_account=PARENT_LINK_ADMIN_SERVICE_ACCOUNT,
)
def manageParentLink(request: https_fn.CallableRequest) -> dict[str, str]:
    return _parent_link_call(manage_parent_link, request)


@https_fn.on_call(
    region=FUNCTION_REGION,
    service_account=PARENT_LINK_ADMIN_SERVICE_ACCOUNT,
)
def revokeParentLink(request: https_fn.CallableRequest) -> dict[str, str]:
    return _parent_link_call(revoke_parent_link, request)


@https_fn.on_call(
    region=FUNCTION_REGION,
    service_account=PARENT_INVITATION_SERVICE_ACCOUNT,
    secrets=[PARENT_INVITATION_EMAIL_HMAC_KEY, PARENT_INVITATION_SMTP_PASSWORD],
)
def createParentLinkInvitation(request: https_fn.CallableRequest) -> dict[str, Any]:
    return _parent_invitation_call(create_parent_link_invitation, request, delivery=True)


@https_fn.on_call(
    region=FUNCTION_REGION,
    service_account=PARENT_INVITATION_SERVICE_ACCOUNT,
    secrets=[PARENT_INVITATION_EMAIL_HMAC_KEY],
)
def acceptParentLinkInvitation(request: https_fn.CallableRequest) -> dict[str, Any]:
    return _parent_invitation_call(accept_parent_link_invitation, request)


@https_fn.on_call(
    region=FUNCTION_REGION,
    service_account=PARENT_INVITATION_SERVICE_ACCOUNT,
    secrets=[PARENT_INVITATION_EMAIL_HMAC_KEY],
)
def declineParentLinkInvitation(request: https_fn.CallableRequest) -> dict[str, Any]:
    return _parent_invitation_call(decline_parent_link_invitation, request)


@https_fn.on_call(
    region=FUNCTION_REGION,
    service_account=PARENT_INVITATION_SERVICE_ACCOUNT,
    secrets=[PARENT_INVITATION_EMAIL_HMAC_KEY],
)
def unlinkOwnParentLink(request: https_fn.CallableRequest) -> dict[str, Any]:
    try:
        actor = _parent_invitation_actor(request)
        return unlink_own_parent_link(_data(request), actor, firestore_db())
    except ParentInvitationError as error:
        raise https_fn.HttpsError(
            _ERROR_CODES.get(error.code, https_fn.FunctionsErrorCode.INTERNAL), str(error)
        )


@firestore_fn.on_document_created(
    document="quizAttempts/{attemptId}",
    region=FUNCTION_REGION,
    service_account=AI_RUNTIME_SERVICE_ACCOUNT,
)
def processFinalizedQuizAttempt(event: firestore_fn.Event[Any]) -> None:
    """Run U8 automatically for a newly finalized trusted quiz attempt."""
    snapshot = event.data
    if snapshot is None or not snapshot.exists:
        return
    # The runtime itself performs the trusted source gate before any model work.
    # The trigger intentionally shares this entry point in emulator and cloud.
    runtime_root = _VENDOR_ROOT if _VENDOR_ROOT.exists() else _AI_SOURCE_ROOT
    process_finalized_attempt(
        snapshot.id,
        gateway=FirestoreRuntimeGateway(firestore_db()),
        bundle=_runtime_bundle(runtime_root),
        provenance="emulator_verified" if os.environ.get("FUNCTIONS_EMULATOR") == "true" else "real",
    )


# firebase-functions-python 0.6 exposes the Firestore trigger retry field in
# the generated manifest but not in ``FirestoreOptions``.  Set the manifest
# flag explicitly so deployed Eventarc delivery retries the same handler; the
# runtime still caps its own server claims at three.
getattr(processFinalizedQuizAttempt, "__firebase_endpoint__").eventTrigger["retry"] = True
