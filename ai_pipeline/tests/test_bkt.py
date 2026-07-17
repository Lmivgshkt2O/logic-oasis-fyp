from datetime import datetime, timedelta, timezone
import unittest

from logic_oasis_ai.bkt import (
    BKT_MODEL_VERSION,
    DEFAULT_BKT_PARAMETERS,
    build_bkt_ablation_evidence,
    build_bkt_materialization,
    build_mastery_snapshots,
    next_response_probability,
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
    source_attempt_sequence: int | None = 1,
    subtopic_id: str = "subtopic-a",
    correct_count: int = 0,
    minutes: int = 0,
    data_source: str = RUNTIME_CALLABLE_DATA_SOURCE,
):
    return FinalizedQuizAttemptRecord(
        attempt_id=attempt_id,
        session_id=f"session-{attempt_id}",
        student_id="student-1",
        subtopic_id=subtopic_id,
        total_questions=len(response_ids),
        correct_count=correct_count,
        score=0,
        response_ids=response_ids,
        finalization_status=FINALIZED_STATUS,
        validation_status=FINALIZED_STATUS,
        data_source=data_source,
        finalized_at=NOW + timedelta(minutes=minutes),
        source_attempt_sequence=source_attempt_sequence,
    )


def response(
    response_id: str,
    attempt_id: str,
    *,
    skill_id: str = "skill-a",
    is_correct: bool,
    sequence_index: int,
    minutes: int,
    student_id: str = "student-1",
):
    return ValidatedResponseRecord(
        response_id=response_id,
        session_id=f"session-{attempt_id}",
        attempt_id=attempt_id,
        student_id=student_id,
        question_id=f"question-{response_id}",
        skill_id=skill_id,
        sequence_index=sequence_index,
        is_correct=is_correct,
        validation_status=VALIDATED_STATUS,
        created_at=NOW + timedelta(minutes=minutes),
    )


class BktMasteryTests(unittest.TestCase):
    def test_bkt_v1_freezes_documented_priors(self):
        self.assertEqual(0.35, DEFAULT_BKT_PARAMETERS.prior_knowledge)
        self.assertEqual(0.18, DEFAULT_BKT_PARAMETERS.learn_rate)
        self.assertEqual(0.20, DEFAULT_BKT_PARAMETERS.guess_rate)
        self.assertEqual(0.10, DEFAULT_BKT_PARAMETERS.slip_rate)

    def test_known_correct_then_incorrect_sequence_matches_posterior(self):
        first = attempt("a1", ("r1",), source_attempt_sequence=1, correct_count=1, minutes=8)
        second = attempt("a2", ("r2",), source_attempt_sequence=2, minutes=1)
        snapshots = build_mastery_snapshots(
            [second, first],
            {
                "a1": [response("r1", "a1", is_correct=True, sequence_index=0, minutes=9)],
                "a2": [response("r2", "a2", is_correct=False, sequence_index=0, minutes=0)],
            },
        )

        expected = update_probability(
            update_probability(DEFAULT_BKT_PARAMETERS.prior_knowledge, is_correct=True),
            is_correct=False,
        )
        self.assertEqual(len(snapshots), 1)
        self.assertAlmostEqual(snapshots[0].mastery_probability, expected, places=8)
        self.assertEqual(snapshots[0].evidence_count, 2)
        self.assertEqual(snapshots[0].model_version, BKT_MODEL_VERSION)
        self.assertEqual((2, 0), (snapshots[0].source_attempt_sequence, snapshots[0].sequence_index))

    def test_responses_in_one_attempt_replay_by_sequence_index_not_created_at(self):
        source = attempt("a1", ("r1", "r2"), source_attempt_sequence=1, correct_count=1)
        snapshots = build_mastery_snapshots(
            [source],
            {
                "a1": [
                    response("r2", "a1", is_correct=False, sequence_index=1, minutes=0),
                    response("r1", "a1", is_correct=True, sequence_index=0, minutes=20),
                ],
            },
        )
        expected = update_probability(
            update_probability(DEFAULT_BKT_PARAMETERS.prior_knowledge, is_correct=True),
            is_correct=False,
        )
        self.assertAlmostEqual(expected, snapshots[0].mastery_probability, places=8)
        self.assertEqual(("r1", "r2"), snapshots[0].source_response_ids)

    def test_duplicate_source_attempt_is_not_processed_twice(self):
        source = attempt("a1", ("r1",), source_attempt_sequence=1, correct_count=1)
        responses = {"a1": [response("r1", "a1", is_correct=True, sequence_index=0, minutes=1)]}

        once = build_mastery_snapshots([source], responses)
        repeated = build_mastery_snapshots([source, source], responses)

        self.assertEqual(repeated, once)

    def test_conflicting_duplicate_source_attempt_is_rejected(self):
        source = attempt("a1", ("r1",), source_attempt_sequence=1, correct_count=1)
        conflicting = attempt("a1", ("r1",), source_attempt_sequence=2, correct_count=1)
        with self.assertRaisesRegex(ValueError, "conflicting lineage"):
            build_mastery_snapshots(
                [source, conflicting],
                {"a1": [response("r1", "a1", is_correct=True, sequence_index=0, minutes=1)]},
            )

    def test_duplicate_state_ordering_tuple_is_rejected(self):
        first = attempt("a1", ("r1",), source_attempt_sequence=1, correct_count=1)
        second = attempt("a2", ("r2",), source_attempt_sequence=1, correct_count=1)
        with self.assertRaisesRegex(ValueError, "duplicate BKT ordering tuple-key"):
            build_mastery_snapshots(
                [first, second],
                {
                    "a1": [response("r1", "a1", is_correct=True, sequence_index=0, minutes=1)],
                    "a2": [response("r2", "a2", is_correct=True, sequence_index=0, minutes=2)],
                },
            )

    def test_subtopic_and_skill_pairs_keep_independent_mastery_state(self):
        first = attempt("a1", ("r1",), source_attempt_sequence=1, correct_count=1, subtopic_id="subtopic-a")
        second = attempt("a2", ("r2",), source_attempt_sequence=1, subtopic_id="subtopic-b")
        snapshots = build_mastery_snapshots(
            [first, second],
            {
                "a1": [response("r1", "a1", skill_id="shared-skill", is_correct=True, sequence_index=0, minutes=1)],
                "a2": [response("r2", "a2", skill_id="shared-skill", is_correct=False, sequence_index=0, minutes=2)],
            },
        )

        self.assertEqual(
            [(snapshot.subtopic_id, snapshot.skill_id) for snapshot in snapshots],
            [("subtopic-a", "shared-skill"), ("subtopic-b", "shared-skill")],
        )
        self.assertGreater(snapshots[0].mastery_probability, snapshots[1].mastery_probability)

    def test_empty_history_produces_no_snapshot(self):
        self.assertEqual(build_mastery_snapshots([], {}), ())

    def test_seed_foreign_incomplete_and_sequence_less_lineage_are_rejected(self):
        seed = attempt("seed", ("r1",), source_attempt_sequence=1, correct_count=1, data_source="seed_demo")
        with self.assertRaisesRegex(ValueError, "trusted finalized runtime"):
            build_mastery_snapshots(
                [seed], {"seed": [response("r1", "seed", is_correct=True, sequence_index=0, minutes=1)]}
            )

        foreign = attempt("foreign", ("r1",), source_attempt_sequence=1, correct_count=1)
        with self.assertRaisesRegex(ValueError, "another student"):
            build_mastery_snapshots(
                [foreign],
                {"foreign": [response("r1", "foreign", is_correct=True, sequence_index=0, minutes=1, student_id="student-2")]},
            )

        incomplete = attempt("incomplete", ("r1", "r2"), source_attempt_sequence=1, correct_count=1)
        with self.assertRaisesRegex(ValueError, "response count"):
            build_mastery_snapshots(
                [incomplete], {"incomplete": [response("r1", "incomplete", is_correct=True, sequence_index=0, minutes=1)]}
            )

        legacy = attempt("legacy", ("r1",), source_attempt_sequence=None, correct_count=1)
        with self.assertRaisesRegex(ValueError, "legacy_no_sequence"):
            build_mastery_snapshots(
                [legacy], {"legacy": [response("r1", "legacy", is_correct=True, sequence_index=0, minutes=1)]}
            )

        mismatched = attempt("mismatched", ("expected",), source_attempt_sequence=1, correct_count=1)
        with self.assertRaisesRegex(ValueError, "lineage is not ordered"):
            build_mastery_snapshots(
                [mismatched],
                {"mismatched": [response("other", "mismatched", is_correct=True, sequence_index=0, minutes=1)]},
            )

        zero_sequence = attempt("zero", ("r1",), source_attempt_sequence=0, correct_count=1)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            build_mastery_snapshots(
                [zero_sequence], {"zero": [response("r1", "zero", is_correct=True, sequence_index=0, minutes=1)]}
            )

    def test_ablation_evidence_is_one_step_ahead_and_never_uses_future_response(self):
        source = attempt("a1", ("r1", "r2"), source_attempt_sequence=1, correct_count=1)
        responses = {
            "a1": [
                response("r1", "a1", is_correct=True, sequence_index=0, minutes=1),
                response("r2", "a1", is_correct=False, sequence_index=1, minutes=2),
            ],
        }
        evidence = build_bkt_ablation_evidence([source], responses)
        first, second = evidence
        initial_probability = next_response_probability(DEFAULT_BKT_PARAMETERS.prior_knowledge)
        first_after = update_probability(DEFAULT_BKT_PARAMETERS.prior_knowledge, is_correct=True)

        self.assertEqual(("a1", "r1", 1, 0), (
            first.source_attempt_id, first.source_response_id,
            first.source_attempt_sequence, first.sequence_index,
        ))
        self.assertEqual(BKT_MODEL_VERSION, first.model_version)
        self.assertAlmostEqual(initial_probability, first.next_response_probability, places=8)
        self.assertAlmostEqual(first_after, first.p_known_after_attempt, places=8)
        self.assertAlmostEqual(first_after, second.p_known_before_response, places=8)
        self.assertNotEqual(first.next_response_probability, first.p_known_after_attempt)

        materialization = build_bkt_materialization([source], responses)
        snapshot = materialization.snapshots[0]
        self.assertEqual(2, snapshot.evidence_count)
        self.assertEqual((1, 1), (snapshot.source_attempt_sequence, snapshot.sequence_index))
        self.assertEqual(second.p_known_after_attempt, snapshot.p_known_after_attempt)


if __name__ == "__main__":
    unittest.main()
