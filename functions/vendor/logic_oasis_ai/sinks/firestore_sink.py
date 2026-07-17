"""Deterministic, safe Firestore projection shapes for U8."""

from __future__ import annotations

from typing import Mapping


def mastery_snapshot_id(student_id: str, subtopic_id: str, skill_id: str) -> str:
    return f"{student_id}_{subtopic_id}_{skill_id}"


def adaptive_assignment_id(student_id: str, subtopic_id: str) -> str:
    return f"{student_id}_{subtopic_id}"


def subtopic_mastery_id(student_id: str, year_level: int, topic_id: str, subtopic_id: str) -> str:
    return f"{student_id}_y{year_level}_{topic_id}_{subtopic_id}"


def safe_status_document(*, attempt: Mapping[str, object], analysis_state: str, display_code: str) -> dict[str, object]:
    return {
        "attemptId": attempt["attemptId"],
        "studentId": attempt["studentId"],
        "sourceAttemptSequence": attempt["sourceAttemptSequence"],
        "analysisState": analysis_state,
        "displayCode": display_code,
    }


def is_newer_projection(candidate: int, existing: Mapping[str, object] | None) -> bool:
    if not existing:
        return True
    previous = existing.get("sourceAttemptSequence")
    if isinstance(previous, bool) or not isinstance(previous, int) or previous < 1:
        return True
    return candidate > previous
