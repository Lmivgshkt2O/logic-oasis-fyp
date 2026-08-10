"""AQC-E2 difficulty-calibration tests (ASSISTments Grade 6, frozen rules).

All tests are pure or use tiny synthetic CSVs; none reads the protected raw
data and none executes any policy selector.  They freeze window isolation,
cohort eligibility, graded-response semantics, independent-learner counting,
the smoothing rule, evaluation-learner disjointness, determinism, provenance,
and the no-policy boundary of the E2 path.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from external_data.assistments.adaptive.difficulty_calibration import (
    CALIBRATION_METHOD_VERSION,
    CATALOG_FIELDS,
    CalibrationProblemRecord,
    aggregate_problem_records,
    build_calibration_manifest,
    collect_grade_six_learner_sets,
    exact_grade_six_sequence,
    first_graded_pair,
    split_overlapping_learners,
    stream_calibration_graded_pairs,
    write_catalog_csv,
)
from external_data.assistments.adaptive.proxy_tiers import (
    SKILL_CATALOG_MINIMUM_PER_TIER,
    SKILL_CATALOG_MINIMUM_PROBLEMS,
    evaluate_skill_catalog,
)
from external_data.assistments.adaptive.schemas import (
    CALIBRATION_WINDOW_END,
    CALIBRATION_WINDOW_START,
    EVALUATION_WINDOW_END,
    EVALUATION_WINDOW_START,
    EXTERNAL_PROVENANCE,
    MINIMUM_CALIBRATION_LEARNERS,
    difficulty_score,
    in_calibration_window,
    smoothed_correct_probability,
)
from external_data.assistments.assistments_contract import (
    graded_correctness,
    is_graded_action,
)


RELEASE_ID = "assistments-edm-cup-2023-release-v1"
PSEUDONYM_KEY = b"test-e2-key"


def pairs_for_learners(
    learner_ids: list[str],
    problem_id: str = "problem-1",
    *,
    correct: bool = True,
    start: datetime = CALIBRATION_WINDOW_START,
) -> list[tuple[str, str, datetime, int, bool]]:
    return [
        (learner_id, problem_id, start + timedelta(seconds=index), index, correct)
        for index, learner_id in enumerate(learner_ids)
    ]


class CalibrationWindowTests(unittest.TestCase):
    def test_2022_2023_rows_never_enter_calibration(self) -> None:
        self.assertFalse(in_calibration_window(EVALUATION_WINDOW_START))
        self.assertFalse(in_calibration_window(EVALUATION_WINDOW_END))
        self.assertTrue(in_calibration_window(CALIBRATION_WINDOW_END))

    def test_pre_calibration_start_rows_never_enter(self) -> None:
        before = CALIBRATION_WINDOW_START - timedelta(seconds=1)
        self.assertFalse(in_calibration_window(before))
        self.assertTrue(in_calibration_window(CALIBRATION_WINDOW_START))


class CohortEligibilityTests(unittest.TestCase):
    def test_only_exact_grade_six_enters_primary_calibration(self) -> None:
        metadata = {
            "seq-6": ("6", "Mathematics"),
            "seq-5": ("5", "Mathematics"),
            "seq-7": ("7", "Mathematics"),
        }
        self.assertTrue(exact_grade_six_sequence(metadata, "seq-6"))
        self.assertFalse(exact_grade_six_sequence(metadata, "seq-5"))
        self.assertFalse(exact_grade_six_sequence(metadata, "seq-7"))

    def test_grade_six_accelerated_does_not_silently_enter(self) -> None:
        metadata = {"seq-acc": (None, "Mathematics")}
        self.assertFalse(exact_grade_six_sequence(metadata, "seq-acc"))

    def test_assignment_scan_keeps_grade_six_and_separates_windows(self) -> None:
        metadata = {"seq-6": ("6", "Mathematics")}
        rows = (
            "assignment_log_id,student_id,sequence_id,assignment_start_time\n"
            "a-cal,student-cal,seq-6,1609459199\n"  # 2020-12-31T23:59:59Z
            "a-eval,student-eval,seq-6,1640995200\n"  # 2022-01-01T00:00:00Z
            "a-acc,student-acc,seq-acc,1609459199\n"
            "a-out,student-out,seq-6,1500000000\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assignment_details.csv"
            path.write_text(rows, encoding="utf-8")
            result = collect_grade_six_learner_sets(path, metadata)
        self.assertEqual(
            result["calibrationAssignments"],
            {"a-cal": "student-cal"},
        )
        self.assertEqual(result["calibrationLearners"], {"student-cal"})
        self.assertEqual(result["evaluationLearners"], {"student-eval"})


class GradedResponseTests(unittest.TestCase):
    def test_only_approved_graded_events_are_used(self) -> None:
        self.assertTrue(is_graded_action("correct_response"))
        self.assertTrue(is_graded_action("wrong_response"))
        self.assertFalse(is_graded_action("open_response"))
        self.assertFalse(is_graded_action("problem_started"))

    def test_open_response_is_not_silently_graded(self) -> None:
        self.assertIsNone(graded_correctness("open_response"))
        self.assertIs(graded_correctness("correct_response"), True)
        self.assertIs(graded_correctness("wrong_response"), False)

    def test_first_graded_pair_keeps_chronologically_first(self) -> None:
        base = CALIBRATION_WINDOW_START
        first = first_graded_pair(None, base, 5, True)
        kept = first_graded_pair(first, base + timedelta(seconds=1), 9, False)
        self.assertEqual(kept, (base, 5, True))


class IndependentLearnerTests(unittest.TestCase):
    def test_repeated_encounters_do_not_inflate_learner_or_response_counts(self) -> None:
        base = CALIBRATION_WINDOW_START
        pairs = [
            ("learner-1", "problem-1", base, 0, True),
            ("learner-1", "problem-1", base + timedelta(seconds=10), 1, False),
            ("learner-1", "problem-1", base + timedelta(seconds=20), 2, True),
        ]
        records, counters = aggregate_problem_records(
            pairs, {"problem-1": "6.NS.A.1"}, release_id=RELEASE_ID, pseudonym_key=PSEUDONYM_KEY
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].calibration_learner_count, 1)
        self.assertEqual(records[0].calibration_response_count, 1)
        self.assertEqual(records[0].correct_response_count, 1)

    def test_below_20_learners_is_insufficient(self) -> None:
        records, _ = aggregate_problem_records(
            pairs_for_learners([f"learner-{i}" for i in range(19)]),
            {"problem-1": "6.NS.A.1"},
            release_id=RELEASE_ID,
            pseudonym_key=PSEUDONYM_KEY,
        )
        self.assertEqual(records[0].calibration_status, "insufficient_problem_evidence")
        self.assertIsNone(records[0].proxy_difficulty)

    def test_exactly_20_learners_is_eligible(self) -> None:
        records, _ = aggregate_problem_records(
            pairs_for_learners([f"learner-{i}" for i in range(20)]),
            {"problem-1": "6.NS.A.1"},
            release_id=RELEASE_ID,
            pseudonym_key=PSEUDONYM_KEY,
        )
        self.assertEqual(records[0].calibration_status, "calibrated")
        self.assertEqual(records[0].calibration_learner_count, 20)


class SmoothingTests(unittest.TestCase):
    def test_smoothing_equation_is_exact(self) -> None:
        self.assertEqual(smoothed_correct_probability(7, 20), 8 / 22)
        self.assertEqual(smoothed_correct_probability(0, 20), 1 / 22)

    def test_difficulty_score_is_one_minus_p_correct(self) -> None:
        self.assertEqual(difficulty_score(7, 20), 1 - 8 / 22)


class NullSkillTests(unittest.TestCase):
    def test_null_skill_produces_no_proxy_tier_and_is_counted(self) -> None:
        records, counters = aggregate_problem_records(
            pairs_for_learners([f"learner-{i}" for i in range(20)], problem_id="problem-null"),
            {"problem-null": None},
            release_id=RELEASE_ID,
            pseudonym_key=PSEUDONYM_KEY,
        )
        self.assertEqual(records, [])
        self.assertEqual(counters["problems_null_skill_excluded"], 1)


class DisjointnessTests(unittest.TestCase):
    def test_overlap_check_excludes_evaluation_learners(self) -> None:
        excluded, final = split_overlapping_learners(
            {"learner-a", "learner-b", "learner-c"},
            {"learner-b", "learner-eval-only"},
        )
        self.assertEqual(excluded, {"learner-b"})
        self.assertEqual(final, {"learner-a", "learner-c"})
        self.assertEqual(final & {"learner-b", "learner-eval-only"}, set())


class DeterminismAndGovernanceTests(unittest.TestCase):
    def test_rerun_produces_identical_records_and_catalog_hash(self) -> None:
        pairs = pairs_for_learners([f"learner-{i}" for i in range(20)])
        first, _ = aggregate_problem_records(
            pairs, {"problem-1": "6.NS.A.1"}, release_id=RELEASE_ID, pseudonym_key=PSEUDONYM_KEY
        )
        second, _ = aggregate_problem_records(
            pairs, {"problem-1": "6.NS.A.1"}, release_id=RELEASE_ID, pseudonym_key=PSEUDONYM_KEY
        )
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as directory:
            first_path = write_catalog_csv(first, Path(directory) / "first.csv")
            second_path = write_catalog_csv(second, Path(directory) / "second.csv")
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
            from external_data.assistments.adaptive.difficulty_calibration import file_sha256

            self.assertEqual(file_sha256(first_path), file_sha256(second_path))

    def test_provenance_remains_external_real(self) -> None:
        records, _ = aggregate_problem_records(
            pairs_for_learners([f"learner-{i}" for i in range(20)]),
            {"problem-1": "6.NS.A.1"},
            release_id=RELEASE_ID,
            pseudonym_key=PSEUDONYM_KEY,
        )
        self.assertEqual(records[0].provenance, EXTERNAL_PROVENANCE)

    def test_no_native_bank_or_runtime_fields_in_catalog(self) -> None:
        fields = set(CATALOG_FIELDS)
        for forbidden in (
            "bankId",
            "finalizationStatus",
            "validationStatus",
            "sourceAttemptSequence",
            "contentVersionId",
            "adaptiveAssignmentId",
        ):
            self.assertNotIn(forbidden, fields)
        record_fields = {name for name in CalibrationProblemRecord.__dataclass_fields__}
        self.assertNotIn("bankId", record_fields)

    def test_manifest_contains_raw_identifiers_false_and_no_timestamps(self) -> None:
        manifest = build_calibration_manifest(
            contract_version="assistments-adaptive-contract-v1",
            contract_hash="0" * 64,
            dataset_release_id=RELEASE_ID,
            source_release_hashes={"action_logs.csv": "0" * 64},
            calibration_start=CALIBRATION_WINDOW_START,
            calibration_end=CALIBRATION_WINDOW_END,
            evaluation_start=EVALUATION_WINDOW_START,
            evaluation_end=EVALUATION_WINDOW_END,
            evaluation_learners_excluded_from_calibration=True,
            calibration_evaluation_learner_overlap_count=1,
            possible_pre_2022_grade_six_learners=10,
            final_calibration_learner_count=9,
            smoothing_rule="p_correct = (correct_responses + 1) / (total_graded_responses + 2)",
            minimum_calibration_learners=MINIMUM_CALIBRATION_LEARNERS,
            tiering_scope="exact_sourceSkillCode",
            tier_ordering_tie_rule="p_correct descending, then externalProblemKey ascending",
            tier_algorithm_version=CALIBRATION_METHOD_VERSION,
            tier_assignment_status="blocked_contract_ambiguity_non_divisible_tertiles",
            minimum_problems_per_skill=SKILL_CATALOG_MINIMUM_PROBLEMS,
            minimum_problems_per_tier=SKILL_CATALOG_MINIMUM_PER_TIER,
            problem_counts={"problemsObserved": 5},
            skill_counts={"skillsObserved": 2},
            tier_counts={"proxy_easy": 0, "proxy_moderate": 0, "proxy_hard": 0},
            catalog_sha256="0" * 64,
        )
        self.assertFalse(manifest["containsRawIdentifiers"])
        self.assertFalse(manifest["productionPromotionAllowed"])
        self.assertNotIn("generatedAt", manifest)

    def test_stream_filter_rejects_non_graded_and_out_of_window_rows(self) -> None:
        rows = (
            "assignment_log_id,timestamp,problem_id,action\n"
            f"a-cal,{CALIBRATION_WINDOW_START.timestamp()},problem-1,correct_response\n"
            f"a-cal,{CALIBRATION_WINDOW_START.timestamp()},problem-1,open_response\n"
            f"a-cal,{CALIBRATION_WINDOW_START.timestamp()},problem-null-skill,correct_response\n"
            f"a-cal,{EVALUATION_WINDOW_START.timestamp()},problem-1,correct_response\n"
            f"a-other,{CALIBRATION_WINDOW_START.timestamp()},problem-1,correct_response\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "action_logs.csv"
            path.write_text(rows, encoding="utf-8")
            pairs, counters = stream_calibration_graded_pairs(
                path,
                allowed_assignments={"a-cal": "student-1"},
                excluded_learners=set(),
                problem_skills={"problem-1": "6.NS.A.1", "problem-null-skill": None},
            )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(counters["problems_null_skill_distinct"], 1)
        self.assertGreaterEqual(counters["action_not_graded"], 1)
        self.assertGreaterEqual(counters["action_timestamp_outside_calibration_window"], 1)
        self.assertGreaterEqual(counters["action_assignment_not_calibration_grade_six"], 1)


class NoPolicyBoundaryTests(unittest.TestCase):
    def test_e2_modules_never_call_policy_selectors(self) -> None:
        base = Path(__file__).resolve().parents[1] / "external_data" / "assistments" / "adaptive"
        for filename in (
            "difficulty_calibration.py",
            "proxy_tiers.py",
            "run_difficulty_calibration.py",
        ):
            source = (base / filename).read_text(encoding="utf-8")
            for forbidden in (
                "select_policy_decision",
                "PolicyArm",
                "policy_evaluation",
                "DecisionDirection",
                "false_promotion",
            ):
                self.assertNotIn(forbidden, source, f"{filename} must not reference {forbidden}")

    def test_policy_decision_counters_are_zero_in_runner_summary(self) -> None:
        # The runner's summary contract (verified statically here) declares zero
        # policy decisions; the executed run reports them in the E2 manifest.
        from external_data.assistments.adaptive import run_difficulty_calibration

        source = Path(run_difficulty_calibration.__file__).read_text(encoding="utf-8")
        self.assertIn('"P1": 0', source)
        self.assertIn('"P2": 0', source)
        self.assertIn('"P3a": 0', source)


if __name__ == "__main__":
    unittest.main()
