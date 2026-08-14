"""Trusted weekly Practice projection helpers for U14 (U2).

The parent Practice Effort card reads one server-owned weekly summary per
student. This module owns the Malaysia-week/day calculation and the strict
summary validation so quiz finalization stays decoupled from the forum
runtime. Malformed stored data fails closed; missing data is never turned
into a false zero.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo

PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION = "u14-parent-practice-v1"
PARENT_PRACTICE_TIMEZONE = "Asia/Kuala_Lumpur"
PARENT_PRACTICE_WEEK_DAYS = 7

KUALA_LUMPUR = ZoneInfo(PARENT_PRACTICE_TIMEZONE)


class ParentPracticeError(ValueError):
    """A fail-closed error for the trusted practice projection."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    raise ParentPracticeError("invalid-argument", "A timestamp is required.")


def malaysia_week_start(value: Any) -> datetime:
    """Monday 00:00 in Asia/Kuala_Lumpur for the week containing ``value``."""
    local = _as_datetime(value).astimezone(KUALA_LUMPUR)
    monday = (local - timedelta(days=local.weekday())).date()
    return datetime(monday.year, monday.month, monday.day, tzinfo=KUALA_LUMPUR)


def malaysia_weekday_index(value: Any) -> int:
    """0 = Monday .. 6 = Sunday in Asia/Kuala_Lumpur."""
    return _as_datetime(value).astimezone(KUALA_LUMPUR).weekday()


def _validated_daily_counts(data: Mapping[str, Any]) -> list[int]:
    raw = data.get("dailyCompletionCounts")
    if not isinstance(raw, list) or len(raw) != PARENT_PRACTICE_WEEK_DAYS:
        raise ParentPracticeError(
            "failed-precondition", "Practice summary day counts are invalid."
        )
    counts: list[int] = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ParentPracticeError(
                "failed-precondition", "Practice summary day counts are invalid."
            )
        counts.append(value)
    return counts


def _validated_total(data: Mapping[str, Any], counts: list[int]) -> int:
    total = data.get("completedPracticeCount")
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ParentPracticeError(
            "failed-precondition", "Practice summary total is invalid."
        )
    if total != sum(counts):
        raise ParentPracticeError(
            "failed-precondition", "Practice summary total is inconsistent."
        )
    return total


def _validated_active_days(data: Mapping[str, Any], counts: list[int]) -> int:
    active = data.get("activeDayCount")
    expected = sum(1 for count in counts if count > 0)
    if isinstance(active, bool) or not isinstance(active, int) or active != expected:
        raise ParentPracticeError(
            "failed-precondition", "Practice summary active days are inconsistent."
        )
    return active


def _validated_previous_total(data: Mapping[str, Any]) -> int | None:
    value = data.get("previousWeekCompletedPracticeCount")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ParentPracticeError(
            "failed-precondition", "Practice summary previous total is invalid."
        )
    return value


def _validate_stored_identity(data: Mapping[str, Any], student_id: str) -> datetime:
    if data.get("schemaVersion") != PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION:
        raise ParentPracticeError(
            "failed-precondition", "Practice summary schema version is unsupported."
        )
    if data.get("studentId") != student_id:
        raise ParentPracticeError(
            "failed-precondition", "Practice summary child identity is invalid."
        )
    if data.get("timezone") != PARENT_PRACTICE_TIMEZONE:
        raise ParentPracticeError(
            "failed-precondition", "Practice summary timezone is invalid."
        )
    stored = _as_datetime(data.get("weekStart"))
    if malaysia_week_start(stored) != stored:
        raise ParentPracticeError(
            "failed-precondition", "Practice summary week start is invalid."
        )
    return stored


def _payload(
    student_id: str,
    week_start: datetime,
    daily: list[int],
    previous_total: int | None,
    event_instant: datetime | None,
    updated_at: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schemaVersion": PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION,
        "studentId": student_id,
        "timezone": PARENT_PRACTICE_TIMEZONE,
        "weekStart": week_start,
        "dailyCompletionCounts": daily,
        "completedPracticeCount": sum(daily),
        "activeDayCount": sum(1 for count in daily if count > 0),
        "updatedAt": updated_at,
    }
    if previous_total is not None:
        payload["previousWeekCompletedPracticeCount"] = previous_total
    if event_instant is not None:
        payload["lastPracticeAt"] = event_instant
    return payload


def merge_practice_event(
    existing: Mapping[str, Any] | None,
    *,
    student_id: str,
    event_instant: datetime,
    updated_at: Any,
) -> dict[str, Any]:
    """Roll or increment the weekly summary for one trusted finalized attempt.

    The week and weekday come only from the single captured ``event_instant``,
    so transaction retries across Malaysia Monday midnight stay in one week.
    """
    week_start = malaysia_week_start(event_instant)
    weekday = malaysia_weekday_index(event_instant)
    if not existing:
        daily = [0] * PARENT_PRACTICE_WEEK_DAYS
        daily[weekday] = 1
        return _payload(
            student_id, week_start, daily, None, event_instant, updated_at
        )
    _validate_stored_identity(existing, student_id)
    counts = _validated_daily_counts(existing)
    _validated_total(existing, counts)
    _validated_active_days(existing, counts)
    previous_total = _validated_previous_total(existing)
    stored_week = malaysia_week_start(existing["weekStart"])
    if stored_week == week_start:
        daily = list(counts)
        daily[weekday] += 1
        return _payload(
            student_id, week_start, daily, previous_total, event_instant, updated_at
        )
    if week_start - stored_week == timedelta(days=PARENT_PRACTICE_WEEK_DAYS):
        # Exactly one week gap: carry only the immediately preceding total.
        daily = [0] * PARENT_PRACTICE_WEEK_DAYS
        daily[weekday] = 1
        return _payload(
            student_id,
            week_start,
            daily,
            _validated_total(existing, counts),
            event_instant,
            updated_at,
        )
    if week_start > stored_week:
        # A longer gap starts a fresh current week without a comparison.
        daily = [0] * PARENT_PRACTICE_WEEK_DAYS
        daily[weekday] = 1
        return _payload(
            student_id, week_start, daily, None, event_instant, updated_at
        )
    raise ParentPracticeError(
        "failed-precondition",
        "Stored practice summary is newer than the finalization event.",
    )


def initialize_practice_week(
    existing: Mapping[str, Any] | None,
    *,
    student_id: str,
    now: datetime,
    updated_at: Any,
) -> dict[str, Any] | None:
    """Return a zero current-week payload, or ``None`` to preserve an existing
    valid current-week summary. Malformed stored data always fails closed."""
    current_week = malaysia_week_start(now)
    if not existing:
        return _payload(
            student_id,
            current_week,
            [0] * PARENT_PRACTICE_WEEK_DAYS,
            None,
            None,
            updated_at,
        )
    _validate_stored_identity(existing, student_id)
    counts = _validated_daily_counts(existing)
    _validated_total(existing, counts)
    _validated_active_days(existing, counts)
    stored_week = malaysia_week_start(existing["weekStart"])
    if stored_week == current_week:
        return None
    previous_total = (
        _validated_total(existing, counts)
        if current_week - stored_week == timedelta(days=PARENT_PRACTICE_WEEK_DAYS)
        else None
    )
    return _payload(
        student_id,
        current_week,
        [0] * PARENT_PRACTICE_WEEK_DAYS,
        previous_total,
        None,
        updated_at,
    )
