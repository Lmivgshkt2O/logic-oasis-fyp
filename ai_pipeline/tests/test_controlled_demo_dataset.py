from __future__ import annotations

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml

from controlled_demo.build_dataset import (
    DEFAULT_CATALOGUE_PATH,
    build_controlled_demo_dataset,
    write_controlled_demo_dataset,
)


class ControlledDemoDatasetTests(unittest.TestCase):
    def setUp(self):
        self.source_document = yaml.safe_load(DEFAULT_CATALOGUE_PATH.read_text(encoding="utf-8"))

    def _write_catalogue(self, directory: str, document: dict) -> Path:
        path = Path(directory) / "catalogue.yaml"
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        return path

    def test_default_catalogue_builds_only_v2_features_and_next_attempt_labels(self):
        build = build_controlled_demo_dataset()

        self.assertEqual(build.manifest["trainingDataProvenance"], "expert_authored_controlled_demo")
        self.assertEqual(
            build.manifest["scenarioAuthorDeclarationReference"],
            "developer-declaration-cdm-catalog-v1",
        )
        self.assertEqual(build.manifest["claimLevel"], "controlled_demonstration_only")
        self.assertEqual(build.manifest["sourceAttemptCount"], 16)
        self.assertEqual(build.manifest["trainingRowCount"], 12)
        self.assertEqual(build.manifest["pairAudit"]["censoredNoLaterAttempt"], 4)
        self.assertEqual(len(build.manifest["scenarioFamilyGroups"]), 4)
        self.assertFalse(build.manifest["containsRawLearnerIdentity"])
        self.assertTrue(all(tuple(row.features) == ("correct_rate", "mean_response_time_ms") for row in build.prediction_dataset.examples))

        first = next(row for row in build.prediction_dataset.examples if row.attempt_id == "steady-recovery-a1")
        self.assertEqual(first.attempt_id, "steady-recovery-a1")
        self.assertTrue(first.target)  # Derived from a2=0.4, not a1=0.8.
        second = next(row for row in build.prediction_dataset.examples if row.attempt_id == "steady-recovery-a2")
        self.assertFalse(second.target)  # Derived from a3=0.8.

    def test_obsolete_catalogue_approval_field_is_rejected(self):
        modified = copy.deepcopy(self.source_document)
        declaration = modified.pop("scenarioAuthorDeclarationReference")
        modified["scenarioAuthorApprovalReference"] = declaration
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "exactly"):
                build_controlled_demo_dataset(self._write_catalogue(directory, modified))

    def test_generation_and_written_documents_are_deterministic(self):
        first = build_controlled_demo_dataset()
        second = build_controlled_demo_dataset()
        self.assertEqual(first.manifest, second.manifest)
        self.assertEqual(first.dataset_document(), second.dataset_document())

        with TemporaryDirectory() as directory:
            paths = write_controlled_demo_dataset(directory)
            self.assertEqual(json.loads(paths["manifest"].read_text(encoding="utf-8")), first.manifest)
            self.assertEqual(json.loads(paths["dataset"].read_text(encoding="utf-8")), first.dataset_document())

    def test_source_change_changes_catalogue_and_dataset_hashes(self):
        modified = copy.deepcopy(self.source_document)
        modified["scenarioFamilies"][0]["attempts"][0]["mean_response_time_ms"] += 1
        with TemporaryDirectory() as directory:
            changed = build_controlled_demo_dataset(self._write_catalogue(directory, modified))
        original = build_controlled_demo_dataset()
        self.assertNotEqual(original.manifest["catalogueSha256"], changed.manifest["catalogueSha256"])
        self.assertNotEqual(original.manifest["datasetSha256"], changed.manifest["datasetSha256"])

    def test_incompatible_and_immediate_repeat_transitions_are_censored(self):
        modified = copy.deepcopy(self.source_document)
        attempts = modified["scenarioFamilies"][0]["attempts"]
        attempts[1]["contentVersion"] = "incompatible-content-v2"
        attempts[2]["questionIds"] = list(attempts[1]["questionIds"])
        with TemporaryDirectory() as directory:
            build = build_controlled_demo_dataset(self._write_catalogue(directory, modified))

        audits = {row.current_attempt_id: row for row in build.prediction_dataset.pair_audits}
        self.assertEqual(audits[attempts[0]["attemptId"]].censor_reason, "incompatible_content_version")
        self.assertEqual(audits[attempts[1]["attemptId"]].censor_reason, "incompatible_content_version")
        self.assertEqual(audits[attempts[2]["attemptId"]].censor_reason, None)

        repeated = copy.deepcopy(self.source_document)
        repeated_attempts = repeated["scenarioFamilies"][0]["attempts"]
        repeated_attempts[1]["questionIds"] = list(repeated_attempts[0]["questionIds"])
        with TemporaryDirectory() as directory:
            repeated_build = build_controlled_demo_dataset(self._write_catalogue(directory, repeated))
        first_audit = next(
            row for row in repeated_build.prediction_dataset.pair_audits
            if row.current_attempt_id == repeated_attempts[0]["attemptId"]
        )
        self.assertEqual(first_audit.censor_reason, "immediate_question_repeat")
        self.assertTrue(first_audit.immediate_question_repeat)

    def test_raw_learner_and_free_text_fields_are_rejected(self):
        for forbidden_field in ("studentId", "studentEmail", "questionText", "answerKey"):
            modified = copy.deepcopy(self.source_document)
            modified["scenarioFamilies"][0][forbidden_field] = "must-not-enter-catalogue"
            with TemporaryDirectory() as directory:
                path = self._write_catalogue(directory, modified)
                with self.assertRaisesRegex(ValueError, "forbidden raw learner fields"):
                    build_controlled_demo_dataset(path)

    def test_current_score_cannot_self_label_and_last_attempt_is_censored(self):
        modified = copy.deepcopy(self.source_document)
        attempts = modified["scenarioFamilies"][0]["attempts"]
        attempts[0]["correct_rate"] = 0.0
        attempts[1]["correct_rate"] = 0.8
        with TemporaryDirectory() as directory:
            build = build_controlled_demo_dataset(self._write_catalogue(directory, modified))
        first = next(row for row in build.prediction_dataset.examples if row.attempt_id == attempts[0]["attemptId"])
        self.assertFalse(first.target)
        last_id = attempts[-1]["attemptId"]
        self.assertNotIn(last_id, {row.attempt_id for row in build.prediction_dataset.examples})

    def test_question_lineage_requires_five_unique_questions(self):
        for invalid_ids in (["one-question"], ["same-question"] * 5):
            modified = copy.deepcopy(self.source_document)
            modified["scenarioFamilies"][0]["attempts"][0]["questionIds"] = invalid_ids
            with TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, "five unique"):
                    build_controlled_demo_dataset(self._write_catalogue(directory, modified))


if __name__ == "__main__":
    unittest.main()
