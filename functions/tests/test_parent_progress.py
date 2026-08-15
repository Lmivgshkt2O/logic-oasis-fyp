from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

FUNCTIONS_ROOT = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_ROOT) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_ROOT))

from parent_progress import (
    PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION,
    PARENT_PRACTICE_TIMEZONE,
    ParentPracticeError,
    initialize_practice_week,
    malaysia_week_start,
    malaysia_weekday_index,
    merge_practice_event,
)

STUDENT_ID = "student_a"


def week_start_of_monday_2026_08_10() -> datetime:
    # Monday 2026-08-10 00:00 in Asia/Kuala_Lumpur is 2026-08-09 16:00 UTC.
    return datetime(2026, 8, 9, 16, tzinfo=timezone.utc)


class ParentProgressTests(unittest.TestCase):
    def test_malaysia_week_and_weekday_are_deterministic(self) -> None:
        sunday_late = datetime(2026, 8, 9, 15, 59, 59, tzinfo=timezone.utc)
        monday_start = week_start_of_monday_2026_08_10()
        wednesday = datetime(2026, 8, 12, 4, tzinfo=timezone.utc)

        self.assertEqual(6, malaysia_weekday_index(sunday_late))
        self.assertEqual(
            datetime(2026, 8, 2, 16, tzinfo=timezone.utc),
            malaysia_week_start(sunday_late),
        )
        self.assertEqual(0, malaysia_weekday_index(monday_start))
        self.assertEqual(monday_start, malaysia_week_start(monday_start))
        self.assertEqual(2, malaysia_weekday_index(wednesday))
        self.assertEqual(monday_start, malaysia_week_start(wednesday))

    def test_one_trusted_attempt_increments_the_correct_weekday_and_totals(
        self,
    ) -> None:
        event = datetime(2026, 8, 12, 4, tzinfo=timezone.utc)
        payload = merge_practice_event(
            None,
            student_id=STUDENT_ID,
            event_instant=event,
            updated_at=event,
        )

        self.assertEqual(PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION, payload["schemaVersion"])
        self.assertEqual(STUDENT_ID, payload["studentId"])
        self.assertEqual(PARENT_PRACTICE_TIMEZONE, payload["timezone"])
        self.assertEqual(week_start_of_monday_2026_08_10(), payload["weekStart"])
        self.assertEqual([0, 0, 1, 0, 0, 0, 0], payload["dailyCompletionCounts"])
        self.assertEqual(1, payload["completedPracticeCount"])
        self.assertEqual(1, payload["activeDayCount"])
        self.assertEqual(event, payload["lastPracticeAt"])
        self.assertNotIn("previousWeekCompletedPracticeCount", payload)

    def test_two_attempts_on_one_day_keep_one_active_day(self) -> None:
        event = datetime(2026, 8, 12, 4, tzinfo=timezone.utc)
        first = merge_practice_event(
            None,
            student_id=STUDENT_ID,
            event_instant=event,
            updated_at=event,
        )
        second = merge_practice_event(
            first,
            student_id=STUDENT_ID,
            event_instant=event,
            updated_at=event,
        )

        self.assertEqual([0, 0, 2, 0, 0, 0, 0], second["dailyCompletionCounts"])
        self.assertEqual(2, second["completedPracticeCount"])
        self.assertEqual(1, second["activeDayCount"])

    def test_monday_rollover_carries_only_the_immediately_preceding_week(
        self,
    ) -> None:
        previous_week = week_start_of_monday_2026_08_10() - timedelta(days=7)
        existing = {
            "schemaVersion": PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION,
            "studentId": STUDENT_ID,
            "timezone": PARENT_PRACTICE_TIMEZONE,
            "weekStart": previous_week,
            "dailyCompletionCounts": [1, 0, 0, 0, 2, 0, 1],
            "completedPracticeCount": 4,
            "activeDayCount": 3,
        }
        monday_event = datetime(2026, 8, 9, 16, tzinfo=timezone.utc)

        rolled = merge_practice_event(
            existing,
            student_id=STUDENT_ID,
            event_instant=monday_event,
            updated_at=monday_event,
        )

        self.assertEqual(week_start_of_monday_2026_08_10(), rolled["weekStart"])
        self.assertEqual([1, 0, 0, 0, 0, 0, 0], rolled["dailyCompletionCounts"])
        self.assertEqual(1, rolled["completedPracticeCount"])
        self.assertEqual(4, rolled["previousWeekCompletedPracticeCount"])

    def test_multi_week_gap_leaves_the_prior_comparison_null(self) -> None:
        old_week = week_start_of_monday_2026_08_10() - timedelta(days=14)
        existing = {
            "schemaVersion": PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION,
            "studentId": STUDENT_ID,
            "timezone": PARENT_PRACTICE_TIMEZONE,
            "weekStart": old_week,
            "dailyCompletionCounts": [1, 0, 0, 0, 0, 0, 0],
            "completedPracticeCount": 1,
            "activeDayCount": 1,
        }
        event = datetime(2026, 8, 12, 4, tzinfo=timezone.utc)

        payload = merge_practice_event(
            existing,
            student_id=STUDENT_ID,
            event_instant=event,
            updated_at=event,
        )

        self.assertNotIn("previousWeekCompletedPracticeCount", payload)

    def test_retry_across_malaysia_midnight_uses_the_captured_instant(
        self,
    ) -> None:
        captured = datetime(2026, 8, 9, 15, 59, 59, tzinfo=timezone.utc)
        first_attempt = merge_practice_event(
            None,
            student_id=STUDENT_ID,
            event_instant=captured,
            updated_at=captured,
        )
        # A transaction retry after the failed first write reuses the same
        # captured instant, so the completion stays in the Sunday week and is
        # counted exactly once.
        retry = merge_practice_event(
            None,
            student_id=STUDENT_ID,
            event_instant=captured,
            updated_at=captured,
        )
        self.assertEqual(first_attempt, retry)
        self.assertEqual(
            datetime(2026, 8, 2, 16, tzinfo=timezone.utc),
            retry["weekStart"],
        )
        self.assertEqual([0, 0, 0, 0, 0, 0, 1], retry["dailyCompletionCounts"])

    def test_malformed_stored_documents_fail_closed(self) -> None:
        event = datetime(2026, 8, 12, 4, tzinfo=timezone.utc)
        week = week_start_of_monday_2026_08_10()

        def stored(**overrides: object) -> dict:
            data: dict = {
                "schemaVersion": PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION,
                "studentId": STUDENT_ID,
                "timezone": PARENT_PRACTICE_TIMEZONE,
                "weekStart": week,
                "dailyCompletionCounts": [1, 0, 0, 0, 0, 0, 0],
                "completedPracticeCount": 1,
                "activeDayCount": 1,
            }
            data.update(overrides)
            return data

        cases: list[dict] = [
            stored(schemaVersion="u13-legacy"),
            stored(studentId="other_student"),
            stored(timezone="UTC"),
            stored(weekStart=datetime(2026, 8, 10, 2, tzinfo=timezone.utc)),
            stored(dailyCompletionCounts=[-1, 0, 0, 0, 0, 0, 0]),
            stored(dailyCompletionCounts=[1, 2]),
            stored(completedPracticeCount=2),
            stored(activeDayCount=0),
            stored(previousWeekCompletedPracticeCount=-1),
            # A stored week newer than the event must never regress.
            stored(weekStart=week + timedelta(days=7)),
        ]
        for data in cases:
            with self.subTest(data=data):
                with self.assertRaises(ParentPracticeError):
                    merge_practice_event(
                        data,
                        student_id=STUDENT_ID,
                        event_instant=event,
                        updated_at=event,
                    )

    def test_initialize_practice_week_creates_a_neutral_zero_state(self) -> None:
        now = datetime(2026, 8, 12, 4, tzinfo=timezone.utc)

        created = initialize_practice_week(
            None,
            student_id=STUDENT_ID,
            now=now,
            updated_at=now,
        )

        self.assertIsNotNone(created)
        self.assertEqual(week_start_of_monday_2026_08_10(), created["weekStart"])
        self.assertEqual([0, 0, 0, 0, 0, 0, 0], created["dailyCompletionCounts"])
        self.assertEqual(0, created["completedPracticeCount"])
        self.assertEqual(0, created["activeDayCount"])
        self.assertNotIn("previousWeekCompletedPracticeCount", created)
        self.assertNotIn("lastPracticeAt", created)

    def test_initialize_practice_week_preserves_a_valid_current_week(
        self,
    ) -> None:
        now = datetime(2026, 8, 12, 4, tzinfo=timezone.utc)
        existing = {
            "schemaVersion": PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION,
            "studentId": STUDENT_ID,
            "timezone": PARENT_PRACTICE_TIMEZONE,
            "weekStart": week_start_of_monday_2026_08_10(),
            "dailyCompletionCounts": [0, 0, 3, 0, 0, 0, 0],
            "completedPracticeCount": 3,
            "activeDayCount": 1,
        }

        self.assertIsNone(
            initialize_practice_week(
                existing,
                student_id=STUDENT_ID,
                now=now,
                updated_at=now,
            )
        )

    def test_initialize_practice_week_rolls_a_previous_week_and_fails_closed(
        self,
    ) -> None:
        now = datetime(2026, 8, 12, 4, tzinfo=timezone.utc)
        previous = {
            "schemaVersion": PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION,
            "studentId": STUDENT_ID,
            "timezone": PARENT_PRACTICE_TIMEZONE,
            "weekStart": week_start_of_monday_2026_08_10() - timedelta(days=7),
            "dailyCompletionCounts": [2, 0, 0, 0, 0, 0, 0],
            "completedPracticeCount": 2,
            "activeDayCount": 1,
        }
        rolled = initialize_practice_week(
            previous,
            student_id=STUDENT_ID,
            now=now,
            updated_at=now,
        )
        self.assertEqual(2, rolled["previousWeekCompletedPracticeCount"])

        malformed = dict(previous)
        malformed["dailyCompletionCounts"] = [0, 0, 0, 0, 0, 0]
        with self.assertRaises(ParentPracticeError):
            initialize_practice_week(
                malformed,
                student_id=STUDENT_ID,
                now=now,
                updated_at=now,
            )

    def test_initialize_practice_week_rejects_a_stored_future_week(self) -> None:
        now = datetime(2026, 8, 12, 4, tzinfo=timezone.utc)
        future = {
            "schemaVersion": PARENT_PRACTICE_SUMMARY_SCHEMA_VERSION,
            "studentId": STUDENT_ID,
            "timezone": PARENT_PRACTICE_TIMEZONE,
            "weekStart": week_start_of_monday_2026_08_10() + timedelta(days=7),
            "dailyCompletionCounts": [0, 0, 0, 0, 0, 0, 0],
            "completedPracticeCount": 0,
            "activeDayCount": 0,
        }

        with self.assertRaises(ParentPracticeError) as raised:
            initialize_practice_week(
                future,
                student_id=STUDENT_ID,
                now=now,
                updated_at=now,
            )

        self.assertEqual("failed-precondition", raised.exception.code)


if __name__ == "__main__":
    unittest.main()
