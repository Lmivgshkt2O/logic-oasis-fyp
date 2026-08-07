"""J3 tests: exact U7 model-table contract, gates, and grouped split (pure)."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from external_data.assistments.build_u7_dataset import (
    AUDIT_FIELDS,
    MODEL_TABLE_FIELDS,
    assess_sufficiency_gates,
    build_student_grouped_split,
    build_u7_rows,
    write_audit_table,
    write_model_table,
)
from external_data.assistments.j2_contract import J2_CONTRACT_VERSION


RELEASE_ID = "assistments-edm-cup-2023-release-test-v1"


def attempt(
    attempt_id: str,
    *,
    student: str = "s1",
    sequence: str = "q6",
    grade: str = "6",
    rate: float = 0.8,
    mean_rt: float = 60_000.0,
    problems: str = "p1|p2|p3",
) -> dict:
    return {
        "externalAttemptId": attempt_id,
        "externalStudentKey": student,
        "externalAssignmentKey": f"assignment-{attempt_id}",
        "externalSequenceKey": sequence,
        "sourceGrade": grade,
        "correct_rate": rate,
        "mean_response_time_ms": mean_rt,
        "gradedProblemKeys": problems,
        "featureValid": True,
    }


def label(
    current_id: str,
    *,
    next_id: str = "a2",
    target: bool = True,
    overlap: float = 0.0,
    censor: str = "",
) -> dict:
    return {
        "currentAttemptId": current_id,
        "externalStudentKey": "s1",
        "externalSequenceKey": "q6",
        "currentAttemptStartedAt": "2022-01-01T00:00:00+00:00",
        "nextAttemptId": next_id,
        "nextAttemptStartedAt": "2022-01-02T00:00:00+00:00",
        "nextCorrectRate": 0.5,
        "nextAttemptCensorReason": "",
        "next_attempt_support_needed": str(target).lower() if not censor else "",
        "censorReason": censor,
        "problemOverlapRate": overlap,
        "provenance": "external_real",
        "sourceDataset": "assistments_edm_cup_2023",
    }


def build_rows(
    attempts: list[dict],
    labels: list[dict],
) -> tuple[list[dict], list[str]]:
    attempts_by_id = {row["externalAttemptId"]: row for row in attempts}
    return build_u7_rows(
        labels,
        attempts_by_id,
        release_id=RELEASE_ID,
        contract_version=J2_CONTRACT_VERSION,
    )


class ModelTableContractTests(unittest.TestCase):
    def test_model_table_has_exactly_the_three_frozen_fields(self):
        self.assertEqual(MODEL_TABLE_FIELDS, ("correct_rate", "mean_response_time_ms", "next_attempt_support_needed"))

    def test_audit_metadata_is_kept_separate_from_model_matrix(self):
        rows, errors = build_rows(
            [
                attempt("a1", student="s1", grade="4", rate=0.8, mean_rt=50_000.0),
                attempt("a2", student="s1", grade="4", rate=0.4, mean_rt=40_000.0),
            ],
            [label("a1", target=True)],
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 1)
        model_keys = {key for key in rows[0] if key in MODEL_TABLE_FIELDS}
        self.assertEqual(model_keys, set(MODEL_TABLE_FIELDS))
        for field in AUDIT_FIELDS:
            self.assertIn(field, rows[0])
        self.assertNotIn("externalStudentKey", MODEL_TABLE_FIELDS)

    def test_model_table_never_contains_learner_identity(self):
        with TemporaryDirectory() as temporary_directory:
            rows, _ = build_rows(
                [
                    attempt("a1", student="s1", rate=0.8),
                    attempt("a2", student="s1", rate=0.4),
                ],
                [label("a1", target=True)],
            )
            model_path = Path(temporary_directory) / "model.csv"
            write_model_table(rows, model_path)
            with model_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, list(MODEL_TABLE_FIELDS))
                content = model_path.read_text(encoding="utf-8")
            self.assertNotIn("s1", content)

    def test_audit_table_carries_grade_sequence_and_overlap_audit(self):
        rows, _ = build_rows(
            [
                attempt("a1", student="s1", sequence="q6", grade="4", problems="p1|p2|p3"),
                attempt("a2", student="s1", sequence="q6", grade="4", problems="p2|p3|p4"),
            ],
            [label("a1", target=False, overlap=0.6667)],
        )
        audit = rows[0]
        self.assertEqual(audit["externalStudentKey"], "s1")
        self.assertEqual(audit["sourceGrade"], "4")
        self.assertEqual(audit["externalSequenceKey"], "q6")
        self.assertEqual(audit["nextGradedProblemKeys"], "p2|p3|p4")
        self.assertEqual(audit["problemOverlapRate"], "0.6667")
        self.assertEqual(audit["provenance"], "external_real")
        self.assertEqual(audit["contractVersion"], J2_CONTRACT_VERSION)

    def test_censored_rows_never_enter_the_model_table(self):
        rows, _ = build_rows(
            [attempt("a1", rate=0.8), attempt("a2", rate=0.4)],
            [label("a1", censor="no_next_attempt")],
        )
        self.assertEqual(rows, [])

    def test_invalid_features_are_rejected_with_audit_error(self):
        rows, errors = build_rows(
            [
                attempt("a1", rate=1.2, mean_rt=60_000.0),
                attempt("a2", rate=0.4, mean_rt=40_000.0),
            ],
            [label("a1", target=True)],
        )
        self.assertEqual(rows, [])
        self.assertTrue(any("correct_rate must be finite" in error for error in errors))

        rows, errors = build_rows(
            [
                attempt("a1", rate=0.8, mean_rt=1_900_000.0),
                attempt("a2", rate=0.4, mean_rt=40_000.0),
            ],
            [label("a1", target=True)],
        )
        self.assertEqual(rows, [])
        self.assertTrue(any("mean_response_time_ms must be finite" in error for error in errors))

    def test_boundary_features_are_accepted(self):
        rows, errors = build_rows(
            [
                attempt("a1", rate=0.0, mean_rt=1.0),
                attempt("a2", rate=0.4, mean_rt=40_000.0),
            ],
            [label("a1", target=True)],
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 1)


class SufficiencyGateTests(unittest.TestCase):
    def test_zero_labelled_rows_is_insufficient(self):
        gates = assess_sufficiency_gates([])
        self.assertEqual(gates["claimLevel"], "INSUFFICIENT_FOR_MODEL_COMPARISON")
        self.assertIs(gates["canCompare"], False)

    def test_single_class_is_pipeline_demo_only(self):
        rows, _ = build_rows(
            [
                attempt("a1", student="s1", rate=0.8),
                attempt("a2", student="s1", rate=0.4),
                attempt("b1", student="s2", rate=0.8),
                attempt("b2", student="s2", rate=0.4),
            ],
            [
                label("a1", target=True),
                label("b1", target=True),
            ],
        )
        gates = assess_sufficiency_gates(rows)
        self.assertEqual(gates["claimLevel"], "PIPELINE_DEMO_ONLY")
        self.assertIs(gates["canCompare"], False)

    def test_both_classes_two_learners_is_preliminary_only(self):
        rows, _ = build_rows(
            [
                attempt("a1", student="s1", rate=0.8),
                attempt("a2", student="s1", rate=0.4),
                attempt("b1", student="s2", rate=0.8),
                attempt("b2", student="s2", rate=0.4),
            ],
            [
                label("a1", target=True),
                label("b1", target=False),
            ],
        )
        gates = assess_sufficiency_gates(rows)
        self.assertEqual(gates["claimLevel"], "PRELIMINARY_COMPARISON")
        self.assertIs(gates["canCompare"], True)

    def test_both_classes_three_learners_can_reach_held_out(self):
        rows, _ = build_rows(
            [
                attempt("a1", student="s1", rate=0.8),
                attempt("a2", student="s1", rate=0.4),
                attempt("b1", student="s2", rate=0.8),
                attempt("b2", student="s2", rate=0.4),
                attempt("c1", student="s3", rate=0.8),
                attempt("c2", student="s3", rate=0.4),
            ],
            [
                label("a1", target=True),
                label("b1", target=True),
                label("c1", target=False),
            ],
        )
        gates = assess_sufficiency_gates(rows)
        self.assertIn(gates["claimLevel"], ("PRELIMINARY_COMPARISON", "HELD_OUT_COMPARISON"))


class GroupedSplitTests(unittest.TestCase):
    def test_split_is_student_grouped_with_both_classes_and_seed(self):
        rows, _ = build_rows(
            [
                attempt("a1", student="s1", rate=0.8),
                attempt("a2", student="s1", rate=0.4),
                attempt("b1", student="s2", rate=0.8),
                attempt("b2", student="s2", rate=0.4),
                attempt("c1", student="s3", rate=0.8),
                attempt("c2", student="s3", rate=0.4),
                attempt("d1", student="s4", rate=0.8),
                attempt("d2", student="s4", rate=0.4),
            ],
            [
                label("a1", target=True),
                label("b1", target=False),
                label("c1", target=True),
                label("d1", target=False),
            ],
        )
        partition = build_student_grouped_split(rows)
        self.assertIsNotNone(partition)
        train, test = partition
        self.assertTrue(train["rows"] > 0 and test["rows"] > 0)
        self.assertFalse(set(train["learnerKeys"]) & set(test["learnerKeys"]))
        self.assertTrue(train["target_true"] > 0 and train["target_false"] > 0)
        self.assertTrue(test["target_true"] > 0 and test["target_false"] > 0)
        again = build_student_grouped_split(rows)
        self.assertEqual(partition, again)

    def test_no_split_when_no_labelled_rows(self):
        self.assertIsNone(build_student_grouped_split([]))


if __name__ == "__main__":
    unittest.main()

