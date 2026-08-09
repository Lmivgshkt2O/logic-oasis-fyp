"""J0 schema-contract tests for the ASSISTments EDM Cup 2023 external path.

All tests are pure: they validate the versioned physical -> semantic mapping,
the fail-closed window rule, action semantics, response-time derivation rules,
the Grade 6 filter, and the external_real provenance boundary.  They never
touch the protected raw CSVs.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from external_data.assistments.assistments_contract import (
    FORBIDDEN_NATIVE_FIELDS,
    FORBIDDEN_NATIVE_PROVENANCE_VALUES,
    GRADED_ACTIONS,
    PROVENANCE,
    SCHEMA_MAPPING_VERSION,
    detect_forbidden_native_terms,
    first_graded_response,
    grade_from_level_2,
    grade_from_skill_code,
    graded_correctness,
    in_selected_window,
    is_graded_action,
    is_primary_grade_six_level_2,
    load_schema_mapping,
    ordered_events,
    pair_problem_duration,
    parse_epoch_seconds,
    response_time_ms,
    validate_provenance_external_real,
    validate_schema_mapping,
)


EXTERNAL_DATA_DIR = Path(__file__).resolve().parents[1] / "external_data" / "assistments"
MAPPING_PATH = EXTERNAL_DATA_DIR / "assistments_schema_mapping_v1.yaml"

# Physical headers detected on 2026-08-07 from the downloaded Kaggle release.
DETECTED_HEADERS = {
    "action_logs.csv": [
        "assignment_log_id", "timestamp", "problem_id", "max_attempts",
        "available_core_tutoring", "score_viewable", "continuous_score_viewable",
        "action", "hint_id", "explanation_id",
    ],
    "assignment_details.csv": [
        "assignment_log_id", "teacher_id", "class_id", "student_id", "sequence_id",
        "assignment_release_date", "assignment_due_date", "assignment_start_time",
        "assignment_end_time",
    ],
    "problem_details.csv": [
        "problem_id", "problem_multipart_id", "problem_multipart_position", "problem_type",
        "problem_skill_code", "problem_skill_description", "problem_contains_image",
        "problem_contains_equation", "problem_contains_video", "problem_text_bert_pca",
    ],
    "sequence_details.csv": [
        "sequence_id", "sequence_folder_path_level_1", "sequence_folder_path_level_2",
        "sequence_folder_path_level_3", "sequence_folder_path_level_4",
        "sequence_folder_path_level_5", "sequence_name", "sequence_problem_ids",
    ],
    "assignment_relationships.csv": ["unit_test_assignment_log_id", "in_unit_assignment_log_id"],
    "sequence_relationships.csv": ["unit_test_sequence_id", "in_unit_sequence_id"],
}


def mapping() -> dict:
    return load_schema_mapping(MAPPING_PATH)


class SchemaMappingTests(unittest.TestCase):
    def test_mapping_loads_and_passes_fail_closed_validation(self):
        loaded = mapping()
        self.assertEqual(loaded["schemaMappingVersion"], SCHEMA_MAPPING_VERSION)
        validate_schema_mapping(loaded)

    def test_required_semantic_concepts_resolve_to_detected_physical_columns(self):
        loaded = mapping()
        for concept, entry in loaded["semanticConcepts"].items():
            table = entry.get("physicalTable")
            field = entry.get("physicalField")
            fields = entry.get("physicalFields")
            self.assertIn(table, DETECTED_HEADERS, f"concept {concept} table not detected")
            candidates = [field] if field else fields
            self.assertTrue(candidates, f"concept {concept} has no physical field")
            for candidate in candidates:
                self.assertIn(
                    candidate,
                    DETECTED_HEADERS[table],
                    f"concept {concept} field {candidate} not in detected {table} header",
                )

    def test_detected_columns_match_the_mapping_file(self):
        loaded = mapping()
        for filename, detected in DETECTED_HEADERS.items():
            entry = loaded["physicalFiles"][filename]
            self.assertEqual(entry["detectedColumns"], detected, filename)

    def test_base_u7_files_are_required_and_excluded_tables_are_not_features(self):
        loaded = mapping()
        for filename in ("action_logs.csv", "assignment_details.csv", "problem_details.csv", "sequence_details.csv"):
            self.assertTrue(loaded["physicalFiles"][filename]["requiredForBaseU7"])
            self.assertFalse(loaded["physicalFiles"][filename]["excludedFromBaseFeatures"])
        for filename in (
            "training_unit_test_scores.csv",
            "evaluation_unit_test_scores.csv",
            "hint_details.csv",
            "explanation_details.csv",
        ):
            self.assertTrue(loaded["physicalFiles"][filename]["excludedFromBaseFeatures"])
            self.assertFalse(loaded["physicalFiles"][filename]["requiredForBaseU7"])
        self.assertEqual(loaded["featureContract"]["baseSchema"], "quiz-attempt-features-v2")
        self.assertEqual(loaded["featureContract"]["baseFeatures"], ["correct_rate", "mean_response_time_ms"])

    def test_missing_required_concept_is_rejected(self):
        broken = deepcopy(mapping())
        del broken["semanticConcepts"]["learner"]
        with self.assertRaisesRegex(ValueError, "learner"):
            validate_schema_mapping(broken)

    def test_empty_physical_field_is_rejected(self):
        broken = deepcopy(mapping())
        broken["semanticConcepts"]["assignment"] = {
            "semantic": "assignment",
            "physicalTable": "assignment_details.csv",
            "physicalField": "",
        }
        with self.assertRaisesRegex(ValueError, "physicalField"):
            validate_schema_mapping(broken)

    def test_missing_required_file_is_rejected(self):
        broken = deepcopy(mapping())
        broken["physicalFiles"]["action_logs.csv"]["requiredForBaseU7"] = False
        with self.assertRaisesRegex(ValueError, "action_logs.csv"):
            validate_schema_mapping(broken)

    def test_action_semantics_match_detected_graded_values_exactly(self):
        loaded = mapping()["actionSemantics"]
        for action, correct in GRADED_ACTIONS.items():
            self.assertIn(action, loaded)
            self.assertEqual(loaded[action]["semantic"], "graded correct first response (correct = 1)" if correct else "graded incorrect first response (correct = 0)")
        self.assertIn("problem_started", loaded)
        self.assertIn("open_response", loaded)
        self.assertEqual(loaded["open_response"]["usedFor"], "none")


class DateWindowTests(unittest.TestCase):
    def test_lower_boundary(self):
        self.assertFalse(in_selected_window(datetime(2021, 12, 31, 23, 59, 59, tzinfo=timezone.utc)))
        self.assertTrue(in_selected_window(datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)))

    def test_upper_boundary(self):
        self.assertTrue(in_selected_window(datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc)))
        self.assertFalse(in_selected_window(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)))

    def test_missing_and_unparseable_timestamps_are_excluded(self):
        self.assertFalse(in_selected_window(None))
        self.assertIsNone(parse_epoch_seconds(None))
        self.assertIsNone(parse_epoch_seconds(""))
        self.assertIsNone(parse_epoch_seconds("not-a-timestamp"))
        self.assertFalse(in_selected_window(parse_epoch_seconds("not-a-timestamp")))

    def test_epoch_seconds_parse_is_utc(self):
        parsed = parse_epoch_seconds("1641069211.542")
        self.assertEqual(parsed, datetime(2022, 1, 1, 20, 33, 31, 542000, tzinfo=timezone.utc))
        self.assertTrue(in_selected_window(parsed))

    def test_timezone_naive_timestamp_is_not_eligible(self):
        self.assertFalse(in_selected_window(datetime(2022, 6, 1)))


class CorrectnessContractTests(unittest.TestCase):
    def test_graded_action_recognition(self):
        self.assertIs(graded_correctness("correct_response"), True)
        self.assertIs(graded_correctness("wrong_response"), False)

    def test_ungraded_and_auxiliary_actions_are_not_graded(self):
        for action in ("open_response", "answer_requested", "problem_started", "hint_requested"):
            self.assertIsNone(graded_correctness(action))
            self.assertFalse(is_graded_action(action))

    def test_capitalization_is_exact(self):
        self.assertIsNone(graded_correctness("Correct_Response"))
        self.assertIsNone(graded_correctness("correct"))

    def test_first_graded_response_wins(self):
        base = datetime(2022, 1, 1, tzinfo=timezone.utc)
        events = [
            (base, "problem_started"),
            (base + timedelta(seconds=5), "wrong_response"),
            (base + timedelta(seconds=9), "answer_requested"),
            (base + timedelta(seconds=12), "correct_response"),
        ]
        self.assertEqual(first_graded_response(events), (base + timedelta(seconds=5), "wrong_response"))


class ResponseTimeContractTests(unittest.TestCase):
    def test_unit_conversion_to_milliseconds(self):
        start = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        graded = datetime(2022, 1, 1, 0, 0, 1, 500000, tzinfo=timezone.utc)
        self.assertEqual(response_time_ms(start, graded), 1500.0)

    def test_negative_response_time_is_rejected(self):
        start = datetime(2022, 1, 1, 0, 0, 2, tzinfo=timezone.utc)
        graded = datetime(2022, 1, 1, 0, 0, 1, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "negative response time"):
            response_time_ms(start, graded)

    def test_missing_start_or_graded_response_pairing(self):
        base = datetime(2022, 1, 1, tzinfo=timezone.utc)
        paired, duration, reason = pair_problem_duration([], [(base, "correct_response")])
        self.assertFalse(paired)
        self.assertEqual(reason, "missing_problem_start")
        paired, duration, reason = pair_problem_duration([(base, "problem_started")], [(base, "answer_requested")])
        self.assertFalse(paired)
        self.assertEqual(reason, "missing_graded_response")

    def test_valid_pairing_produces_duration(self):
        start = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        events = [
            (start, "problem_started"),
            (start + timedelta(seconds=3), "wrong_response"),
            (start + timedelta(seconds=10), "correct_response"),
        ]
        paired, duration, reason = pair_problem_duration([(start, "problem_started")], events)
        self.assertTrue(paired)
        self.assertEqual(duration, 3000.0)
        self.assertIsNone(reason)


class GradeSixFilterTests(unittest.TestCase):
    def test_exact_grade_six_token(self):
        self.assertEqual(grade_from_level_2("Grade 6"), "6")
        self.assertTrue(is_primary_grade_six_level_2("Grade 6"))

    def test_accelerated_variant_is_not_merged_into_primary(self):
        self.assertIsNone(grade_from_level_2("Grade 6 Accelerated"))
        self.assertFalse(is_primary_grade_six_level_2("Grade 6 Accelerated"))

    def test_other_grades_and_missing_values(self):
        self.assertEqual(grade_from_level_2("Grade 7"), "7")
        self.assertEqual(grade_from_level_2("Grade 1"), "1")
        self.assertIsNone(grade_from_level_2("Algebra I"))
        self.assertIsNone(grade_from_level_2(None))

    def test_skill_code_corroboration(self):
        self.assertEqual(grade_from_skill_code("6.RP.A.3b"), "6")
        self.assertEqual(grade_from_skill_code("8.EE.A.1-1"), "8")
        self.assertIsNone(grade_from_skill_code(None))


class ProvenanceAndGovernanceTests(unittest.TestCase):
    def test_provenance_is_external_real(self):
        self.assertEqual(PROVENANCE, "external_real")
        self.assertEqual(validate_provenance_external_real("external_real"), "external_real")

    def test_native_runtime_provenance_substitution_is_rejected(self):
        for forbidden in ("runtime_callable", "real", "logic_oasis_runtime_real", "native_logic_oasis_quizAttempts"):
            with self.assertRaisesRegex(ValueError, "provenance"):
                validate_provenance_external_real(forbidden)

    def test_mapping_forbids_native_field_fabrication(self):
        loaded = mapping()
        governance = loaded["governance"]
        self.assertEqual(governance["provenance"], "external_real")
        for native_field in FORBIDDEN_NATIVE_FIELDS:
            self.assertIn(native_field, governance["neverFabricateNativeFields"])
        for native_value in FORBIDDEN_NATIVE_PROVENANCE_VALUES:
            self.assertIn(native_value, governance["neverRelabelAs"])
        self.assertFalse(detect_forbidden_native_terms("external_real source rows"), "clean text should have no native terms")

    def test_native_terms_are_detected_when_present(self):
        found = detect_forbidden_native_terms("row has finalizationStatus and validationStatus")
        self.assertIn("finalizationStatus", found)
        self.assertIn("validationStatus", found)


class BktOrderingTests(unittest.TestCase):
    def test_ordered_events_are_deterministic_and_drop_unparseable(self):
        base = datetime(2022, 1, 1, tzinfo=timezone.utc)
        events = [
            ("bad-timestamp", "problem_started"),
            (str(base.timestamp() + 2), "wrong_response"),
            (str(base.timestamp() + 1), "problem_started"),
            (str(base.timestamp() + 3), "correct_response"),
        ]
        ordered = ordered_events(events)
        self.assertEqual([action for _, action in ordered], ["problem_started", "wrong_response", "correct_response"])
        self.assertTrue(all(timestamp.tzinfo == timezone.utc for timestamp, _ in ordered))


if __name__ == "__main__":
    unittest.main()
