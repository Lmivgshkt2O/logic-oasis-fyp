"""J2 attempt-reconstruction and contract tests (pure, synthetic)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from external_data.assistments.j2_contract import (
    J2_CONTRACT_VERSION,
    MASTERY_CRITERION,
    MAX_RESPONSE_TIME_MS,
    MIN_VALID_GRADED_PROBLEMS,
    MIN_VALID_RESPONSE_TIME_PAIRS,
    OUTCOME_VALID,
    PRIMARY_GRADE,
    PRIMARY_SUBJECT,
    REASON_INCOMPLETE,
    REASON_INSUFFICIENT_GRADED,
    REASON_INSUFFICIENT_TIMING,
    REASON_NO_START,
    REASON_NOT_PRIMARY_COHORT,
    RT_AMBIGUOUS,
    RT_CENSORED_OVER_30_MIN,
    RT_MISSING_GRADED,
    RT_NO_START,
    RT_VALID,
    RT_ZERO,
    load_j2_contract,
    validate_j2_contract,
)
from external_data.assistments.reconstruct_attempts import (
    build_attempt_from_rows,
    build_problem_outcome,
    reconstruct_attempts,
)


J2_CONTRACT_PATH = Path(__file__).resolve().parents[1] / "external_data" / "assistments" / "assistments_j2_contract_v1.yaml"
RELEASE_ID = "assistments-edm-cup-2023-release-test-v1"
BASE = datetime(2022, 1, 1, tzinfo=timezone.utc)


def row(
    action: str,
    offset_seconds: float,
    problem: str | None = None,
    *,
    grade: str | None = "6",
    subject: str | None = "Mathematics",
    skill: str | None = "6.RP.A.3b",
    student: str = "s1",
    assignment: str = "a1",
    sequence: str = "q6",
) -> dict:
    return {
        "sourceTimestamp": (BASE + timedelta(seconds=offset_seconds)).isoformat(),
        "sourceActionType": action,
        "externalProblemKey": problem or "",
        "sourceSkillCode": skill or "",
        "sourceGrade": grade or "",
        "sourceSubject": subject or "",
        "externalStudentKey": student,
        "externalAssignmentKey": assignment,
        "externalSequenceKey": sequence,
    }


def problem_flow(
    problem: str,
    start_offset: float,
    graded: list[tuple[float, str]],
    *,
    skill: str = "6.RP.A.3b",
    extra_starts: int = 0,
    grade: str | None = "6",
    subject: str | None = "Mathematics",
    student: str = "s1",
    assignment: str = "a1",
    sequence: str = "q6",
) -> list[dict]:
    rows = [row("problem_started", start_offset, problem, skill=skill, grade=grade, subject=subject, student=student, assignment=assignment, sequence=sequence)]
    for extra in range(extra_starts):
        rows.append(row("problem_started", start_offset + 0.001 + extra * 0.001, problem, skill=skill, grade=grade, subject=subject, student=student, assignment=assignment, sequence=sequence))
    for offset, action in graded:
        rows.append(row(action, offset, problem, skill=skill, grade=grade, subject=subject, student=student, assignment=assignment, sequence=sequence))
    return rows


class J2ContractTests(unittest.TestCase):
    def test_contract_loads_and_validates(self):
        contract = validate_j2_contract(load_j2_contract(J2_CONTRACT_PATH))
        self.assertEqual(contract["contractVersion"], J2_CONTRACT_VERSION)
        self.assertEqual(contract["masteryCriterionAndTarget"]["masteryCriterion"], 0.60)
        self.assertEqual(contract["primaryCohort"]["sourceGrade"], PRIMARY_GRADE)
        self.assertEqual(contract["primaryCohort"]["sourceSubject"], PRIMARY_SUBJECT)
        self.assertEqual(contract["primaryCohort"]["fallback"]["pooledGrades"], ["4", "5", "6"])

    def test_frozen_constants(self):
        self.assertEqual(MASTERY_CRITERION, 0.60)
        self.assertEqual(MIN_VALID_GRADED_PROBLEMS, 3)
        self.assertEqual(MIN_VALID_RESPONSE_TIME_PAIRS, 3)
        self.assertEqual(MAX_RESPONSE_TIME_MS, 1_800_000)

    def test_contract_rejects_tuning_and_broadening(self):
        contract = load_j2_contract(J2_CONTRACT_PATH)
        broken = dict(contract)
        mastery = dict(contract["masteryCriterionAndTarget"])
        mastery["masteryCriterion"] = 0.7
        broken["masteryCriterionAndTarget"] = mastery
        with self.assertRaisesRegex(ValueError, "masteryCriterion"):
            validate_j2_contract(broken)

        broken = dict(contract)
        cohort = dict(contract["primaryCohort"])
        cohort["sourceGrade"] = "7"
        broken["primaryCohort"] = cohort
        with self.assertRaisesRegex(ValueError, "sourceGrade"):
            validate_j2_contract(broken)


class AttemptCompletionAndCohortTests(unittest.TestCase):
    def test_completed_attempt_requires_start_and_later_finish(self):
        rows = [
            row("assignment_started", 0),
            *problem_flow("p1", 10, [(20, "correct_response")]),
            row("assignment_finished", 30),
        ]
        attempt = build_attempt_from_rows(rows, contract={}, release_id=RELEASE_ID)
        self.assertTrue(attempt.completed)
        self.assertTrue(attempt.cohortEligible)
        self.assertEqual(attempt.attemptStartedAt, BASE)
        self.assertEqual(attempt.attemptEndedAt, BASE + timedelta(seconds=30))

    def test_missing_finish_marks_incomplete(self):
        rows = [row("assignment_started", 0), *problem_flow("p1", 10, [(20, "correct_response")])]
        attempt = build_attempt_from_rows(rows, contract={}, release_id=RELEASE_ID)
        self.assertFalse(attempt.completed)
        self.assertEqual(attempt.attemptCensorReason, REASON_INCOMPLETE)
        self.assertEqual(attempt.validityLevel, "invalid")

    def test_missing_assignment_start_is_no_start(self):
        rows = problem_flow("p1", 10, [(20, "correct_response")])
        attempt = build_attempt_from_rows(rows, contract={}, release_id=RELEASE_ID)
        self.assertEqual(attempt.attemptCensorReason, REASON_NO_START)

    def test_non_grade_six_cohort_is_excluded(self):
        rows = [
            row("assignment_started", 0),
            *problem_flow("p1", 10, [(20, "correct_response")], grade="7"),
            row("assignment_finished", 30),
        ]
        attempt = build_attempt_from_rows(rows, contract={}, release_id=RELEASE_ID)
        self.assertFalse(attempt.cohortEligible)
        self.assertEqual(attempt.attemptCensorReason, REASON_NOT_PRIMARY_COHORT)


class ProblemCorrectnessTests(unittest.TestCase):
    def test_first_graded_response_wins_over_later_corrections(self):
        outcome = build_problem_outcome(problem_flow("p1", 10, [(20, "wrong_response"), (30, "correct_response")]))
        self.assertTrue(outcome.graded)
        self.assertIs(outcome.correct, False)
        self.assertEqual(outcome.responseTimeMs, 10_000.0)
        self.assertEqual(outcome.responseTimeStatus, RT_VALID)

    def test_open_response_and_auxiliary_actions_are_not_graded(self):
        rows = [
            row("problem_started", 10, "p1"),
            row("open_response", 20, "p1"),
            row("answer_requested", 25, "p1"),
        ]
        outcome = build_problem_outcome(rows)
        self.assertFalse(outcome.graded)
        self.assertEqual(outcome.responseTimeStatus, RT_MISSING_GRADED)

    def test_graded_response_before_start_is_not_later(self):
        outcome = build_problem_outcome(problem_flow("p1", 10, [(5, "correct_response")]))
        self.assertFalse(outcome.graded)
        self.assertEqual(outcome.responseTimeStatus, RT_MISSING_GRADED)

    def test_no_problem_start_excludes_problem(self):
        outcome = build_problem_outcome([row("correct_response", 10, "p1")])
        self.assertFalse(outcome.graded)
        self.assertEqual(outcome.responseTimeStatus, RT_NO_START)

    def test_zero_duration_is_rejected(self):
        outcome = build_problem_outcome([row("problem_started", 10, "p1"), row("correct_response", 10, "p1")])
        self.assertTrue(outcome.graded)
        self.assertEqual(outcome.responseTimeStatus, RT_ZERO)
        self.assertEqual(outcome.responseTimeMs, 0.0)

    def test_over_30_minutes_is_censored_but_correctness_kept(self):
        outcome = build_problem_outcome(problem_flow("p1", 10, [(10 + 1_801, "wrong_response")]))
        self.assertTrue(outcome.graded)
        self.assertIs(outcome.correct, False)
        self.assertEqual(outcome.responseTimeStatus, RT_CENSORED_OVER_30_MIN)
        self.assertEqual(outcome.responseTimeMs, 1_801_000.0)

    def test_exactly_30_minutes_is_valid(self):
        outcome = build_problem_outcome(problem_flow("p1", 10, [(10 + 1_800, "correct_response")]))
        self.assertEqual(outcome.responseTimeStatus, RT_VALID)
        self.assertEqual(outcome.responseTimeMs, 1_800_000.0)

    def test_multiple_starts_are_timing_ambiguous_but_correctness_kept(self):
        rows = problem_flow("p1", 10, [(30, "correct_response")], extra_starts=1)
        outcome = build_problem_outcome(rows)
        self.assertTrue(outcome.multipleStarts)
        self.assertTrue(outcome.graded)
        self.assertIs(outcome.correct, True)
        self.assertEqual(outcome.responseTimeStatus, RT_AMBIGUOUS)
        self.assertIsNone(outcome.responseTimeMs)

    def test_unresolved_metadata_problem_still_contributes(self):
        rows = problem_flow("p1", 10, [(20, "correct_response")], skill="")
        outcome = build_problem_outcome(rows)
        self.assertTrue(outcome.unresolvedMetadata)
        self.assertTrue(outcome.graded)
        self.assertEqual(outcome.responseTimeStatus, RT_VALID)


class AttemptMetricsTests(unittest.TestCase):
    def test_correct_rate_and_mean_response_time(self):
        rows = [
            row("assignment_started", 0),
            *problem_flow("p1", 10, [(20, "correct_response")]),
            *problem_flow("p2", 30, [(40, "wrong_response")]),
            *problem_flow("p3", 50, [(60, "correct_response")]),
            row("assignment_finished", 100),
        ]
        attempt = build_attempt_from_rows(rows, contract={}, release_id=RELEASE_ID)
        self.assertEqual(attempt.gradedProblemCount, 3)
        self.assertEqual(attempt.correctFirstResponseCount, 2)
        self.assertAlmostEqual(attempt.correct_rate, 2 / 3)
        self.assertAlmostEqual(attempt.mean_response_time_ms, 10_000.0)
        self.assertEqual(attempt.validResponseTimePairs, 3)
        self.assertEqual(attempt.validityLevel, OUTCOME_VALID)
        self.assertTrue(attempt.featureValid)

    def test_censored_timing_excluded_from_mean_but_kept_in_correctness(self):
        rows = [
            row("assignment_started", 0),
            *problem_flow("p1", 10, [(20, "correct_response")]),
            *problem_flow("p2", 30, [(30 + 1_801, "wrong_response")]),
            *problem_flow("p3", 50, [(60, "correct_response")]),
            row("assignment_finished", 100),
        ]
        attempt = build_attempt_from_rows(rows, contract={}, release_id=RELEASE_ID)
        self.assertEqual(attempt.gradedProblemCount, 3)
        self.assertEqual(attempt.validResponseTimePairs, 2)
        self.assertAlmostEqual(attempt.mean_response_time_ms, 10_000.0)
        self.assertEqual(attempt.validityLevel, OUTCOME_VALID)
        self.assertFalse(attempt.featureValid)
        self.assertEqual(attempt.attemptCensorReason, REASON_INSUFFICIENT_TIMING)

    def test_outcome_valid_requires_three_graded_problems(self):
        rows = [
            row("assignment_started", 0),
            *problem_flow("p1", 10, [(20, "correct_response")]),
            *problem_flow("p2", 30, [(40, "wrong_response")]),
            row("assignment_finished", 100),
        ]
        attempt = build_attempt_from_rows(rows, contract={}, release_id=RELEASE_ID)
        self.assertEqual(attempt.gradedProblemCount, 2)
        self.assertEqual(attempt.attemptCensorReason, REASON_INSUFFICIENT_GRADED)
        self.assertEqual(attempt.validityLevel, "invalid")

    def test_unresolved_metadata_counted(self):
        rows = [
            row("assignment_started", 0),
            *problem_flow("p1", 10, [(20, "correct_response")], skill=""),
            *problem_flow("p2", 30, [(40, "correct_response")]),
            *problem_flow("p3", 50, [(60, "correct_response")]),
            row("assignment_finished", 100),
        ]
        attempt = build_attempt_from_rows(rows, contract={}, release_id=RELEASE_ID)
        self.assertEqual(attempt.unresolvedProblemMetadataCount, 1)
        self.assertEqual(attempt.gradedProblemCount, 3)

    def test_attempt_id_is_deterministic_and_pseudonymous(self):
        rows = [row("assignment_started", 0), row("assignment_finished", 10)]
        first = build_attempt_from_rows(rows, contract={}, release_id=RELEASE_ID)
        second = build_attempt_from_rows(rows, contract={}, release_id=RELEASE_ID)
        self.assertEqual(first.externalAttemptId, second.externalAttemptId)
        self.assertNotIn("s1", first.externalAttemptId)


class AttemptSequenceTests(unittest.TestCase):
    def test_attempt_sequence_assigned_by_start_timestamp(self):
        import pandas as pd

        rows = [
            row("assignment_started", 0, student="s1", assignment="a1"),
            row("assignment_finished", 10, student="s1", assignment="a1"),
            row("assignment_started", 100, student="s1", assignment="a2"),
            row("assignment_finished", 110, student="s1", assignment="a2"),
        ]
        frame = pd.DataFrame(rows)
        frame["sourceTimestamp"] = pd.to_datetime(frame["sourceTimestamp"], utc=True)
        records, _, summary = reconstruct_attempts(frame, contract={}, release_id=RELEASE_ID)
        by_assignment = {r.externalAssignmentKey: r for r in records}
        self.assertEqual(by_assignment["a1"].externalAttemptSequence, 1)
        self.assertEqual(by_assignment["a2"].externalAttemptSequence, 2)
        self.assertEqual(summary["uniqueStudents"], 1)


if __name__ == "__main__":
    unittest.main()
