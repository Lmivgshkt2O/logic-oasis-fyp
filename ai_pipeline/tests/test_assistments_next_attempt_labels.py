"""J2 next-compatible-attempt label and censoring tests (pure, synthetic)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from external_data.assistments.build_labels import LABEL_FIELDS, LabelRow, build_label_rows
from external_data.assistments.j2_contract import (
    OUTCOME_VALID,
    REASON_CHRONOLOGY_AMBIGUOUS,
    REASON_IDENTICAL_PROBLEM_SET,
    REASON_NEXT_NOT_OUTCOME_VALID,
    REASON_NO_NEXT,
)


RELEASE_ID = "assistments-edm-cup-2023-release-test-v1"
BASE = datetime(2022, 1, 1, tzinfo=timezone.utc)


def attempt(
    attempt_id: str,
    started_offset: float,
    *,
    validity: str = OUTCOME_VALID,
    feature: bool = True,
    rate: float | None = 0.8,
    problems: tuple[str, ...] = ("p1", "p2", "p3"),
    student: str = "s1",
    sequence: str = "q6",
    assignment: str | None = None,
    censor_reason: str = "",
) -> dict:
    return {
        "externalAttemptId": attempt_id,
        "externalStudentKey": student,
        "externalSequenceKey": sequence,
        "externalAssignmentKey": assignment or attempt_id,
        "attemptStartedAt": (BASE + timedelta(seconds=started_offset)).isoformat(),
        "attemptEndedAt": (BASE + timedelta(seconds=started_offset + 60)).isoformat(),
        "validityLevel": validity,
        "featureValid": feature,
        "correct_rate": "" if rate is None else rate,
        "gradedProblemKeys": "|".join(problems),
        "attemptCensorReason": censor_reason,
    }


def labelled(row: LabelRow) -> bool:
    return row.next_attempt_support_needed is not None


class NextAttemptLabelTests(unittest.TestCase):
    def test_immediate_next_outcome_valid_pair_is_labelled(self):
        rows, summary = build_label_rows(
            [
                attempt("a1", 0, rate=0.8),
                attempt("a2", 100, rate=0.4, feature=False, problems=("p4", "p5", "p6")),
                attempt("a3", 200, rate=0.9, feature=False, problems=("p7", "p8", "p9")),
            ],
            contract={},
            release_id=RELEASE_ID,
        )
        self.assertEqual(len(rows), 1)
        self.assertTrue(labelled(rows[0]))
        self.assertIs(rows[0].next_attempt_support_needed, True)
        self.assertEqual(rows[0].nextAttemptId, "a2")
        self.assertIsNone(rows[0].censorReason)
        self.assertEqual(summary["labelledPairs"], 1)
        self.assertEqual(summary["target_true"], 1)
        self.assertEqual(summary["candidatePairs"], 1)

    def test_mastery_boundary_zero_six(self):
        rows, _ = build_label_rows(
            [
                attempt("a1", 0, rate=0.8),
                attempt("a2", 100, rate=0.6, feature=False, problems=("p4", "p5", "p6")),
            ],
            contract={},
            release_id=RELEASE_ID,
        )
        self.assertIs(rows[0].next_attempt_support_needed, False)

        rows, _ = build_label_rows(
            [
                attempt("a1", 0, rate=0.8),
                attempt("a2", 100, rate=0.5999, feature=False, problems=("p4", "p5", "p6")),
            ],
            contract={},
            release_id=RELEASE_ID,
        )
        self.assertIs(rows[0].next_attempt_support_needed, True)

    def test_missing_next_is_censored_not_labelled(self):
        rows, summary = build_label_rows([attempt("a1", 0)], contract={}, release_id=RELEASE_ID)
        self.assertEqual(len(rows), 1)
        self.assertFalse(labelled(rows[0]))
        self.assertEqual(rows[0].censorReason, REASON_NO_NEXT)
        self.assertEqual(summary["censored_no_next_attempt"], 1)

    def test_intervening_incomplete_assignment_is_not_skipped(self):
        rows, summary = build_label_rows(
            [
                attempt("a1", 0, rate=0.8),
                attempt("a2", 100, validity="invalid", feature=False, censor_reason="assignment_not_completed"),
                attempt("a3", 200, rate=0.3, feature=False, problems=("p4", "p5", "p6")),
            ],
            contract={},
            release_id=RELEASE_ID,
        )
        self.assertEqual(len(rows), 1)
        self.assertFalse(labelled(rows[0]))
        self.assertEqual(rows[0].censorReason, REASON_NEXT_NOT_OUTCOME_VALID)
        self.assertEqual(rows[0].nextAttemptId, "a2")
        self.assertEqual(rows[0].nextAttemptCensorReason, "assignment_not_completed")
        self.assertEqual(summary["censored_next_not_outcome_valid"], 1)
        self.assertEqual(summary["candidatePairs"], 1)

    def test_next_insufficient_evidence_is_censored(self):
        rows, _ = build_label_rows(
            [
                attempt("a1", 0, rate=0.8),
                attempt("a2", 100, validity="invalid", feature=False, rate=None, problems=("p1",)),
            ],
            contract={},
            release_id=RELEASE_ID,
        )
        self.assertFalse(labelled(rows[0]))
        self.assertEqual(rows[0].censorReason, REASON_NEXT_NOT_OUTCOME_VALID)

    def test_chronology_ambiguous_tie_is_censored(self):
        rows, summary = build_label_rows(
            [
                attempt("a1", 0, rate=0.8),
                attempt("a2", 0, rate=0.4, feature=False),
            ],
            contract={},
            release_id=RELEASE_ID,
        )
        self.assertFalse(labelled(rows[0]))
        self.assertEqual(rows[0].censorReason, REASON_CHRONOLOGY_AMBIGUOUS)
        self.assertEqual(summary["chronologyAmbiguousPairs"], 1)

    def test_identical_problem_set_is_censored(self):
        rows, summary = build_label_rows(
            [
                attempt("a1", 0, rate=0.8, problems=("p1", "p2", "p3")),
                attempt("a2", 100, rate=0.5, problems=("p1", "p2", "p3"), feature=False),
            ],
            contract={},
            release_id=RELEASE_ID,
        )
        self.assertFalse(labelled(rows[0]))
        self.assertEqual(rows[0].censorReason, REASON_IDENTICAL_PROBLEM_SET)
        self.assertEqual(summary["censored_identical_problem_set_repeat"], 1)

    def test_partial_overlap_is_kept_with_audit_rate(self):
        rows, _ = build_label_rows(
            [
                attempt("a1", 0, rate=0.8, problems=("p1", "p2", "p3")),
                attempt("a2", 100, rate=0.5, problems=("p2", "p3", "p4"), feature=False),
            ],
            contract={},
            release_id=RELEASE_ID,
        )
        self.assertTrue(labelled(rows[0]))
        self.assertAlmostEqual(rows[0].problemOverlapRate, 2 / 3)

    def test_only_feature_valid_attempts_are_currents(self):
        rows, _ = build_label_rows(
            [
                attempt("a1", 0, feature=False, rate=0.8),
                attempt("a2", 100, feature=False, rate=0.4),
            ],
            contract={},
            release_id=RELEASE_ID,
        )
        self.assertEqual(rows, [])

    def test_groups_are_isolated_by_student_and_sequence(self):
        rows, _ = build_label_rows(
            [
                attempt("a1", 0, rate=0.8, student="s1", sequence="q6"),
                attempt("a2", 100, rate=0.4, student="s1", sequence="q6", feature=False, problems=("p4", "p5", "p6")),
                attempt("b1", 0, rate=0.8, student="s2", sequence="q6"),
                attempt("b2", 100, rate=0.4, student="s2", sequence="q6", feature=False, problems=("p4", "p5", "p6")),
                attempt("c1", 0, rate=0.8, student="s1", sequence="q7"),
                attempt("c2", 100, rate=0.4, student="s1", sequence="q7", feature=False, problems=("p4", "p5", "p6")),
            ],
            contract={},
            release_id=RELEASE_ID,
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(summary_targets(rows), [True, True, True])

    def test_censored_rows_never_convert_to_a_class(self):
        rows, _ = build_label_rows(
            [
                attempt("a1", 0, rate=0.8),
                attempt("a2", 100, validity="invalid", feature=False),
            ],
            contract={},
            release_id=RELEASE_ID,
        )
        self.assertFalse(labelled(rows[0]))
        self.assertEqual(rows[0].to_csv_row()["next_attempt_support_needed"], "")

    def test_label_row_contract_and_provenance(self):
        rows, _ = build_label_rows(
            [
                attempt("a1", 0, rate=0.8),
                attempt("a2", 100, rate=0.4, feature=False, problems=("p4", "p5", "p6")),
            ],
            contract={},
            release_id=RELEASE_ID,
        )
        csv_row = rows[0].to_csv_row()
        self.assertEqual(tuple(csv_row), LABEL_FIELDS)
        self.assertEqual(csv_row["provenance"], "external_real")
        self.assertEqual(csv_row["sourceDataset"], "assistments_edm_cup_2023")
        self.assertNotIn("finalizationStatus", csv_row)
        self.assertNotIn("validationStatus", csv_row)


def summary_targets(rows: list[LabelRow]) -> list[bool]:
    return [row.next_attempt_support_needed for row in rows if row.next_attempt_support_needed is not None]


if __name__ == "__main__":
    unittest.main()
