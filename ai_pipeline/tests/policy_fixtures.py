"""Shared AQC-2 test fixtures: trusted multi-attempt learner histories."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from logic_oasis_ai.sources.firestore_source import load_firestore_dataset


UTC = timezone.utc
START = datetime(2026, 8, 1, 8, 0, tzinfo=UTC)


def attempt_document(
    attempt_id: str,
    student_id: str,
    *,
    subtopic_id: str = "read_write_numbers",
    bank_id: str = "easy-1",
    difficulty: str = "Easy",
    sequence: int,
    correct_count: int,
    total_questions: int = 5,
    finalized_at: datetime = START,
    content_version: str = "v1",
    year_level: int = 4,
    skill_id: str = "read_write_numbers",
    **overrides,
) -> dict:
    response_ids = [
        f"response-{attempt_id}-{index}"
        for index in range(total_questions)
    ]
    document = {
        "id": attempt_id,
        "attemptId": attempt_id,
        "sessionId": f"session-{student_id}-{sequence}",
        "studentId": student_id,
        "totalQuestions": total_questions,
        "correctCount": correct_count,
        "score": round(100 * correct_count / total_questions),
        "responseIds": response_ids,
        "finalizationStatus": "finalized",
        "validationStatus": "finalized",
        "dataSource": "runtime_callable",
        "sourceAttemptSequence": sequence,
        "finalizedAt": finalized_at,
        "topicId": "topic-numbers",
        "subtopicId": subtopic_id,
        "bankId": bank_id,
        "difficultyLevel": difficulty,
        "contentVersion": content_version,
        "yearLevel": year_level,
        "assignmentId": f"assignment-{attempt_id}",
        "assignmentSource": "adaptive_assignment",
        "adaptivePolicyVersion": "adaptive-policy-v1",
        "skillId": skill_id,
    }
    document.update(overrides)
    return document


def response_documents(
    attempt_id: str,
    student_id: str,
    *,
    session_id: str | None = None,
    correct_count: int,
    total_questions: int = 5,
    finalized_at: datetime = START,
    content_version: str = "v1",
    skill_id: str = "read_write_numbers",
    question_id_prefix: str = "q",
) -> list[dict]:
    documents = []
    for index in range(total_questions):
        response_id = f"response-{attempt_id}-{index}"
        documents.append(
            {
                "id": response_id,
                "responseId": response_id,
                "sessionId": session_id or f"session-{student_id}",
                "attemptId": attempt_id,
                "studentId": student_id,
                "questionId": f"{question_id_prefix}-{attempt_id}-{index}",
                "skillId": skill_id,
                "sequenceIndex": index,
                "serverIsCorrect": index < correct_count,
                "validationStatus": "validated",
                "createdAt": finalized_at + timedelta(minutes=index),
                "responseTimeMs": 1000 + index,
                "responseTimeQuality": "client_reported_unverified",
                "hintCount": 0,
                "hintTelemetryStatus": "not_supported",
                "questionVersion": content_version,
                "contentVersion": content_version,
                "priorExposureCount": None,
            }
        )
    return documents


def build_dataset(
    rows,
    *,
    provenance: str = "real",
    allow_emulator_records: bool = False,
):
    """Build a SourceDataset from a list of attempt spec dicts.

    Each row supports the attempt_document keys plus ``correctCount``,
    ``totalQuestions``, ``skillId``, and optional ``questionIdPrefix``.
    """
    attempt_documents = []
    response_documents_all = []
    for row in rows:
        values = dict(row)
        attempt_id = values.pop("attempt_id")
        student_id = values.pop("student_id")
        correct_count = values.pop("correct_count", 3)
        total_questions = values.pop("total_questions", 5)
        skill_id = values.pop("skill_id", "read_write_numbers")
        question_prefix = values.pop("question_id_prefix", "q")
        sequence = values.pop("sequence", 1)
        attempt = attempt_document(
            attempt_id,
            student_id,
            sequence=sequence,
            correct_count=correct_count,
            total_questions=total_questions,
            skill_id=skill_id,
            **values,
        )
        attempt_documents.append(attempt)
        response_documents_all.extend(
            response_documents(
                attempt_id,
                student_id,
                session_id=attempt["sessionId"],
                correct_count=correct_count,
                total_questions=total_questions,
                skill_id=skill_id,
                content_version=attempt["contentVersion"],
                finalized_at=attempt["finalizedAt"],
                question_id_prefix=question_prefix,
            )
        )
    return load_firestore_dataset(
        attempt_documents,
        response_documents_all,
        provenance=provenance,
        allow_emulator_records=allow_emulator_records,
    )


def standard_history():
    """Two learners with promotion/hold/demotion-relevant score patterns."""
    return [
        {
            "attempt_id": "a1",
            "student_id": "student-a",
            "bank_id": "easy-1",
            "difficulty": "Easy",
            "sequence": 1,
            "correct_count": 5,
        },
        {
            "attempt_id": "a2",
            "student_id": "student-a",
            "bank_id": "moderate-1",
            "difficulty": "Moderate",
            "sequence": 2,
            "correct_count": 2,
            "finalized_at": START + timedelta(days=2),
        },
        {
            "attempt_id": "a3",
            "student_id": "student-a",
            "bank_id": "moderate-2",
            "difficulty": "Moderate",
            "sequence": 3,
            "correct_count": 4,
            "finalized_at": START + timedelta(days=4),
        },
        {
            "attempt_id": "a4",
            "student_id": "student-a",
            "bank_id": "easy-2",
            "difficulty": "Easy",
            "sequence": 4,
            "correct_count": 5,
            "finalized_at": START + timedelta(days=6),
        },
        {
            "attempt_id": "b1",
            "student_id": "student-b",
            "bank_id": "easy-1",
            "difficulty": "Easy",
            "sequence": 1,
            "correct_count": 2,
        },
        {
            "attempt_id": "b2",
            "student_id": "student-b",
            "bank_id": "easy-2",
            "difficulty": "Easy",
            "sequence": 2,
            "correct_count": 3,
            "finalized_at": START + timedelta(days=1),
        },
        {
            "attempt_id": "b3",
            "student_id": "student-b",
            "bank_id": "moderate-1",
            "difficulty": "Moderate",
            "sequence": 3,
            "correct_count": 5,
            "finalized_at": START + timedelta(days=3),
        },
    ]


def full_bank_catalog():
    """Server-owned style catalogue covering Easy/Moderate/Hard banks."""
    from logic_oasis_ai.adaptive_policy import Difficulty, EligibleBank

    return {
        "read_write_numbers": (
            EligibleBank("easy-1", Difficulty.EASY),
            EligibleBank("easy-2", Difficulty.EASY),
            EligibleBank("moderate-1", Difficulty.MODERATE),
            EligibleBank("moderate-2", Difficulty.MODERATE),
            EligibleBank("hard-1", Difficulty.HARD),
        )
    }
