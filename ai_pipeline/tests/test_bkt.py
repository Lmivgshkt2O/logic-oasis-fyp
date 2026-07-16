from datetime import datetime, timedelta, timezone
import unittest

from logic_oasis_ai.bkt import (
    BKT_MODEL_VERSION,
    DEFAULT_BKT_PARAMETERS,
    build_mastery_snapshots,
    update_probability,
)
from logic_oasis_ai.schemas import (
    FinalizedQuizAttemptRecord,
    ValidatedResponseRecord,
)
from logic_oasis_ai.validators import (
    FINALIZED_STATUS,
    RUNTIME_CALLABLE_DATA_SOURCE,
    VALIDATED_STATUS,
)


NOW = datetime(2026, 7, 16, tzinfo=timezone.utc)


def attempt(
    attempt_id: str,
    response_ids: tuple[str, ...],
    *,
    correct_count: int = 0,
    minutes: int = 0,
):
    return FinalizedQuizAttemptRecord(
        attempt_id=attempt_id,
        session_id=f"session-{attempt_id}",
        student_id="student-1",
        total_questions=len(response_ids),
        correct_count=correct_count,
        score=0,
        response_ids=response_ids,
        finalization_status=FINALIZED_STATUS,
        validation_status=FINALIZED_STATUS,
        data_source=RUNTIME_CALLABLE_DATA_SOURCE,
        finalized_at=NOW + timedelta(minutes=minutes),
    )


def response(
    response_id: str,
    attempt_id: str,
    *,
    skill_id: str = "skill-a",
    is_correct: bool,
    sequence_index: int,
    minutes: int,
):
    return ValidatedResponseRecord(
        response_id=response_id,
        session_id=f"session-{attempt_id}",
        attempt_id=attempt_id,
        student_id="student-1",
        question_id=f"question-{response_id}",
        skill_id=skill_id,
        sequence_index=sequence_index,
        is_correct=is_correct,
        validation_status=VALIDATED_STATUS,
        created_at=NOW + timedelta(minutes=minutes),
    )


class BktMasteryTests(unittest.TestCase):
    def test_known_correct_then_incorrect_sequence_matches_posterior(self):
        first = attempt("a1", ("r1",), correct_count=1, minutes=2)
        second = attempt("a2", ("r2",), minutes=4)
        snapshots = build_mastery_snapshots(
            [first, second],
            {
                "a1": [response("r1", "a1", is_correct=True, sequence_index=0, minutes=1)],
                "a2": [response("r2", "a2", is_correct=False, sequence_index=0, minutes=3)],
            },
        )

        expected = update_probability(
            update_probability(
                DEFAULT_BKT_PARAMETERS.prior_knowledge,
                is_correct=True,
            ),
            is_correct=False,
        )
        self.assertEqual(len(snapshots), 1)
        self.assertAlmostEqual(snapshots[0].mastery_probability, expected, places=8)
        self.assertEqual(snapshots[0].evidence_count, 2)
        self.assertEqual(snapshots[0].model_version, BKT_MODEL_VERSION)

    def test_out_of_order_inputs_are_sorted_by_server_timestamp(self):
        old = attempt("old", ("old-response",), correct_count=1, minutes=2)
        new = attempt("new", ("new-response",), minutes=4)
        snapshots = build_mastery_snapshots(
            [new, old],
            {
                "new": [response("new-response", "new", is_correct=False, sequence_index=0, minutes=3)],
                "old": [response("old-response", "old", is_correct=True, sequence_index=0, minutes=1)],
            },
        )

        self.assertEqual(snapshots[0].source_attempt_ids, ("old", "new"))

    def test_duplicate_source_attempt_is_not_processed_twice(self):
        source = attempt("a1", ("r1",), correct_count=1, minutes=2)
        responses = {"a1": [response("r1", "a1", is_correct=True, sequence_index=0, minutes=1)]}

        once = build_mastery_snapshots([source], responses)
        repeated = build_mastery_snapshots([source, source], responses)

        self.assertEqual(repeated, once)

    def test_skills_keep_independent_mastery_state(self):
        source = attempt("a1", ("r1", "r2"), correct_count=1, minutes=3)
        snapshots = build_mastery_snapshots(
            [source],
            {
                "a1": [
                    response("r1", "a1", skill_id="skill-a", is_correct=True, sequence_index=0, minutes=1),
                    response("r2", "a1", skill_id="skill-b", is_correct=False, sequence_index=1, minutes=2),
                ],
            },
        )

        self.assertEqual([snapshot.skill_id for snapshot in snapshots], ["skill-a", "skill-b"])
        self.assertGreater(snapshots[0].mastery_probability, snapshots[1].mastery_probability)

    def test_empty_history_produces_no_snapshot(self):
        self.assertEqual(build_mastery_snapshots([], {}), ())

    def test_untrusted_attempt_is_rejected(self):
        source = attempt("a1", ("r1",), minutes=2)
        untrusted = FinalizedQuizAttemptRecord(
            **{**source.__dict__, "data_source": "legacy_client"},
        )

        with self.assertRaisesRegex(ValueError, "trusted finalized runtime"):
            build_mastery_snapshots(
                [untrusted],
                {"a1": [response("r1", "a1", is_correct=True, sequence_index=0, minutes=1)]},
            )


if __name__ == "__main__":
    unittest.main()
