"""J1 tests for the ASSISTments external action-row adapter and manifest."""

from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from external_data.assistments.adapter import (
    load_assignment_lookup,
    load_problem_skill_map,
    load_sequence_metadata,
    normalize_action_row,
    run_adapter,
)
from external_data.assistments.assistments_contract import WINDOW_END, WINDOW_START
from external_data.assistments.manifest import (
    MANIFEST_SCHEMA_VERSION,
    build_manifest,
    validate_manifest,
    write_manifest,
)
from external_data.assistments.schemas import (
    EXTERNAL_ACTION_ROW_FIELDS,
    ExternalActionRow,
    external_pseudonym,
)


RELEASE_ID = "assistments-edm-cup-2023-release-test-v1"
KEY = "j1-test-key"

ACTION_LOG_HEADER = [
    "assignment_log_id", "timestamp", "problem_id", "max_attempts",
    "available_core_tutoring", "score_viewable", "continuous_score_viewable",
    "action", "hint_id", "explanation_id",
]
ASSIGNMENT_DETAILS_HEADER = [
    "assignment_log_id", "teacher_id", "class_id", "student_id", "sequence_id",
    "assignment_release_date", "assignment_due_date", "assignment_start_time",
    "assignment_end_time",
]
PROBLEM_DETAILS_HEADER = [
    "problem_id", "problem_multipart_id", "problem_multipart_position", "problem_type",
    "problem_skill_code", "problem_skill_description", "problem_contains_image",
    "problem_contains_equation", "problem_contains_video", "problem_text_bert_pca",
]
SEQUENCE_DETAILS_HEADER = [
    "sequence_id", "sequence_folder_path_level_1", "sequence_folder_path_level_2",
    "sequence_folder_path_level_3", "sequence_folder_path_level_4",
    "sequence_folder_path_level_5", "sequence_name", "sequence_problem_ids",
]

IN_WINDOW_TS = 1641069211.542  # 2022-01-01T20:33:31.542Z
BEFORE_WINDOW_TS = 1640908800.0  # 2021-12-31T00:00:00Z


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def tiny_raw_dir(root: Path) -> Path:
    raw = root / "raw"
    raw.mkdir(parents=True)
    write_csv(raw / "action_logs.csv", ACTION_LOG_HEADER, [
        ["A1", str(IN_WINDOW_TS), "P1", "", "", "", "", "problem_started", "", ""],
        ["A1", str(IN_WINDOW_TS + 10), "P1", "", "", "", "", "correct_response", "", ""],
        ["A1", str(IN_WINDOW_TS + 20), "", "", "", "", "", "assignment_started", "", ""],
        ["A1", str(BEFORE_WINDOW_TS), "P1", "", "", "", "", "wrong_response", "", ""],
        ["A1", "not-a-timestamp", "P1", "", "", "", "", "problem_started", "", ""],
    ])
    write_csv(raw / "assignment_details.csv", ASSIGNMENT_DETAILS_HEADER, [
        ["A1", "T1", "C1", "S1", "Q6", "1", "", "1", ""],
    ])
    write_csv(raw / "problem_details.csv", PROBLEM_DETAILS_HEADER, [
        ["P1", "M1", "1", "Multiple Choice", "6.RP.A.3b", "Unit Rate", "0", "0", "0", "[]"],
    ])
    write_csv(raw / "sequence_details.csv", SEQUENCE_DETAILS_HEADER, [
        ["Q6", "Curriculum", "Grade 6", "Module 1", "", "", "Seq", "[P1]"],
    ])
    write_csv(raw / "assignment_relationships.csv", ["unit_test_assignment_log_id", "in_unit_assignment_log_id"], [])
    write_csv(raw / "sequence_relationships.csv", ["unit_test_sequence_id", "in_unit_sequence_id"], [])
    return raw


def base_lookups(root: Path):
    raw = root / "raw"
    return {
        "assignment_lookup": load_assignment_lookup(raw / "assignment_details.csv", ["A1"]),
        "problem_skills": load_problem_skill_map(raw / "problem_details.csv"),
        "sequence_metadata": load_sequence_metadata(raw / "sequence_details.csv"),
    }


class ExternalActionRowContractTests(unittest.TestCase):
    def test_field_contract_matches_plan_9_1(self):
        self.assertEqual(EXTERNAL_ACTION_ROW_FIELDS, (
            "datasetReleaseId", "externalStudentKey", "externalAssignmentKey",
            "externalSequenceKey", "externalProblemKey", "externalContentKey",
            "sourceTimestamp", "sourceActionType", "sourceGrade", "sourceSubject",
            "sourceSkillCode", "provenance", "sourceDataset", "sourceWindow",
        ))
        row = ExternalActionRow(
            datasetReleaseId=RELEASE_ID,
            externalStudentKey="student-key",
            externalAssignmentKey="assignment-key",
            externalSequenceKey=None,
            externalProblemKey=None,
            externalContentKey=None,
            sourceTimestamp="2022-01-01T00:00:00+00:00",
            sourceActionType="assignment_started",
            sourceGrade=None,
            sourceSubject="Mathematics",
            sourceSkillCode=None,
        )
        self.assertEqual(row.provenance, "external_real")
        self.assertEqual(row.sourceDataset, "assistments_edm_cup_2023")
        self.assertEqual(row.sourceWindow, "2022-01-01/2023-12-31")

    def test_csv_row_contains_only_contract_fields_and_no_raw_learner_id(self):
        row = ExternalActionRow(
            datasetReleaseId=RELEASE_ID,
            externalStudentKey="assistments_student_abc",
            externalAssignmentKey="assistments_assignment_abc",
            externalSequenceKey=None,
            externalProblemKey=None,
            externalContentKey=None,
            sourceTimestamp="2022-01-01T00:00:00+00:00",
            sourceActionType="assignment_started",
            sourceGrade=None,
            sourceSubject=None,
            sourceSkillCode=None,
        )
        csv_row = row.to_csv_row()
        self.assertEqual(tuple(csv_row), EXTERNAL_ACTION_ROW_FIELDS)
        for forbidden in ("finalizationStatus", "validationStatus", "sourceAttemptSequence", "student_id"):
            self.assertNotIn(forbidden, csv_row)
        self.assertEqual(csv_row["externalSequenceKey"], "")

    def test_native_provenance_substitution_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "external_real"):
            ExternalActionRow(
                datasetReleaseId=RELEASE_ID,
                externalStudentKey="s",
                externalAssignmentKey="a",
                externalSequenceKey=None,
                externalProblemKey=None,
                externalContentKey=None,
                sourceTimestamp="2022-01-01T00:00:00+00:00",
                sourceActionType="problem_started",
                sourceGrade=None,
                sourceSubject=None,
                sourceSkillCode=None,
                provenance="runtime_callable",
            )

    def test_external_pseudonyms_are_stable_and_do_not_expose_raw_ids(self):
        first = external_pseudonym("student", "S1", KEY)
        self.assertEqual(first, external_pseudonym("student", "S1", KEY))
        self.assertNotEqual(first, external_pseudonym("student", "S2", KEY))
        self.assertNotEqual(first, external_pseudonym("student", "S1", "other-key"))
        self.assertNotIn("S1", first)


class NormalizeActionRowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        tiny_raw_dir(self.root)
        self.lookups = base_lookups(self.root)
        self.excluded: Counter[str] = Counter()
        self.unresolved: Counter[str] = Counter()

    def _normalize(self, **row):
        values = {
            "assignment_log_id": "A1",
            "timestamp": str(IN_WINDOW_TS),
            "problem_id": "P1",
            "action": "problem_started",
        }
        values.update(row)
        return normalize_action_row(
            values,
            release_id=RELEASE_ID,
            pseudonym_key=KEY,
            excluded=self.excluded,
            unresolved=self.unresolved,
            **self.lookups,
        )

    def test_eligible_problem_row_is_normalized(self):
        normalized = self._normalize()
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized.sourceTimestamp, "2022-01-01T20:33:31.542000+00:00")
        self.assertEqual(normalized.sourceActionType, "problem_started")
        self.assertEqual(normalized.sourceGrade, "6")
        self.assertEqual(normalized.sourceSubject, "Mathematics")
        self.assertEqual(normalized.sourceSkillCode, "6.RP.A.3b")
        self.assertEqual(normalized.externalProblemKey, external_pseudonym("problem", "P1", KEY))
        self.assertEqual(normalized.externalContentKey, external_pseudonym("content", "6.RP.A.3b", KEY))
        self.assertNotIn("S1", normalized.to_csv_row()["externalStudentKey"])

    def test_assignment_level_row_has_null_problem_fields(self):
        normalized = self._normalize(problem_id="", action="assignment_started")
        self.assertIsNotNone(normalized)
        self.assertIsNone(normalized.externalProblemKey)
        self.assertIsNone(normalized.externalContentKey)
        self.assertIsNone(normalized.sourceSkillCode)

    def test_outside_window_row_is_excluded_and_counted(self):
        self.assertIsNone(self._normalize(timestamp=str(BEFORE_WINDOW_TS), action="wrong_response"))
        self.assertEqual(self.excluded["outside_window"], 1)

    def test_unparseable_timestamp_is_excluded_and_counted(self):
        self.assertIsNone(self._normalize(timestamp="garbage"))
        self.assertEqual(self.excluded["unparseable_timestamp"], 1)

    def test_window_boundaries_are_inclusive(self):
        start_ts = WINDOW_START.timestamp()
        end_ts = WINDOW_END.timestamp()
        self.assertIsNotNone(self._normalize(timestamp=str(start_ts)))
        self.assertIsNotNone(self._normalize(timestamp=str(end_ts)))
        self.assertIsNone(self._normalize(timestamp=str(end_ts + 1)))

    def test_unresolvable_assignment_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unresolvable assignment"):
            self._normalize(assignment_log_id="A2")

    def test_unresolvable_problem_metadata_is_emitted_as_null_and_counted(self):
        normalized = self._normalize(problem_id="P999")
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized.externalProblemKey, external_pseudonym("problem", "P999", KEY))
        self.assertIsNone(normalized.externalContentKey)
        self.assertIsNone(normalized.sourceSkillCode)
        self.assertEqual(self.unresolved["problem_metadata_unresolved"], 1)

    def test_unresolvable_sequence_fails_closed(self):
        lookups = dict(self.lookups)
        lookups["sequence_metadata"] = {}
        with self.assertRaisesRegex(ValueError, "sequence metadata"):
            normalize_action_row(
                {"assignment_log_id": "A1", "timestamp": str(IN_WINDOW_TS), "problem_id": "P1", "action": "problem_started"},
                release_id=RELEASE_ID,
                pseudonym_key=KEY,
                excluded=self.excluded,
                **lookups,
            )


class AdapterIntegrationTests(unittest.TestCase):
    def test_end_to_end_normalization_and_manifest(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            raw = tiny_raw_dir(root)
            processed = root / "processed"
            result = run_adapter(
                raw,
                processed,
                release_id=RELEASE_ID,
                pseudonym_key=KEY,
            )
            output = Path(result["actionRows"])
            manifest_path = Path(result["manifest"])

            with output.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
            self.assertEqual(reader.fieldnames, list(EXTERNAL_ACTION_ROW_FIELDS))
            self.assertEqual(len(rows), 3)
            for row in rows:
                self.assertEqual(row["provenance"], "external_real")
                self.assertNotIn("S1", row["externalStudentKey"])
                self.assertNotIn("S1", json.dumps(rows))

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            validate_manifest(manifest)
            self.assertEqual(manifest["provenance"], "external_real")
            self.assertEqual(manifest["counts"]["normalizedRowsEmitted"], 3)
            self.assertEqual(manifest["counts"]["rowsUnparseableTimestampExcluded"], 1)
            self.assertEqual(manifest["counts"]["rowsOutsideWindowExcluded"], 1)
            self.assertEqual(manifest["counts"]["rowsByActionType"]["problem_started"], 1)
            self.assertEqual(manifest["counts"]["rowsByActionType"]["correct_response"], 1)
            self.assertEqual(manifest["counts"]["rowsByActionType"]["assignment_started"], 1)
            self.assertIs(manifest["containsRawIdentifiers"], False)
            self.assertIs(manifest["containsSecretMaterial"], False)
            self.assertIn("action_logs.csv", manifest["sourceFilesSha256"])
            self.assertIn("external_action_rows_v1.csv", manifest["fileSha256"])
            self.assertNotIn("j1-test-key", json.dumps(manifest))
            self.assertNotIn(str(processed.resolve()), json.dumps(manifest))

    def test_output_is_immutable_without_force(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            raw = tiny_raw_dir(root)
            processed = root / "processed"
            run_adapter(raw, processed, release_id=RELEASE_ID, pseudonym_key=KEY)
            with self.assertRaisesRegex(FileExistsError, "immutable"):
                run_adapter(raw, processed, release_id=RELEASE_ID, pseudonym_key=KEY)

    def test_missing_required_source_file_fails_closed(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            raw = tiny_raw_dir(root)
            (raw / "action_logs.csv").unlink()
            with self.assertRaises(FileNotFoundError):
                run_adapter(raw, root / "processed", release_id=RELEASE_ID, pseudonym_key=KEY)


class ManifestTests(unittest.TestCase):
    def test_manifest_requires_hashes_and_provenance(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            tiny_path = root / "rows.csv"
            tiny_path.write_text("a,b\n1,2\n", encoding="utf-8")
            manifest = build_manifest(
                release_id=RELEASE_ID,
                source_hashes={"action_logs.csv": "a" * 64},
                counts={"normalizedRowsEmitted": 1},
                action_rows_path=tiny_path,
            )
            self.assertEqual(manifest["manifestSchemaVersion"], MANIFEST_SCHEMA_VERSION)
            self.assertIs(manifest["redistributionProhibited"], True)
            self.assertIs(manifest["deAnonymizationProhibited"], True)

            with self.assertRaisesRegex(ValueError, "sourceFilesSha256"):
                validate_manifest({**manifest, "sourceFilesSha256": {}})
            with self.assertRaisesRegex(ValueError, "provenance"):
                validate_manifest({**manifest, "provenance": "runtime_callable"})
            with self.assertRaisesRegex(ValueError, "releaseId"):
                validate_manifest({**manifest, "releaseId": ""})

    def test_write_manifest_round_trip(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            tiny_path = root / "rows.csv"
            tiny_path.write_text("a,b\n1,2\n", encoding="utf-8")
            manifest = build_manifest(
                release_id=RELEASE_ID,
                source_hashes={"action_logs.csv": "a" * 64},
                counts={"normalizedRowsEmitted": 1},
                action_rows_path=tiny_path,
            )
            manifest_path = write_manifest(manifest, root / "manifest.json")
            self.assertTrue(manifest_path.exists())
            validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
