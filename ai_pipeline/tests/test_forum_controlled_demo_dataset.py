from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import yaml

from forum_controlled_demo.build_forum_dataset import (
    DEFAULT_CATALOGUE_PATH,
    build_forum_dataset,
    verify_generated_dataset,
    write_forum_dataset,
)


class ForumControlledDemoDatasetTests(unittest.TestCase):
    def setUp(self):
        self.document = yaml.safe_load(DEFAULT_CATALOGUE_PATH.read_text(encoding="utf-8"))

    def _catalogue(self, directory: str, document: dict, *, newline: str | None = None) -> Path:
        path = Path(directory) / "catalogue.yaml"
        text = yaml.safe_dump(document, sort_keys=False, allow_unicode=True)
        if newline is not None:
            text = text.replace("\n", newline)
        path.write_text(text, encoding="utf-8", newline="")
        return path

    def test_default_catalogue_is_strict_fictional_multilingual_grouped_evidence(self):
        build = build_forum_dataset()

        self.assertEqual(88, len(build.rows))
        self.assertEqual(
            {"explanation_sufficient", "answer_only_or_insufficient"},
            {row.label for row in build.rows},
        )
        self.assertEqual({"en", "ms", "mixed"}, {row.language for row in build.rows})
        self.assertEqual({"expert_authored_controlled_demo"}, {row.provenance for row in build.rows})
        self.assertEqual(13, build.manifest["scenarioFamilyCount"])
        self.assertEqual("scenarioFamilyId", build.manifest["evaluationGroupKey"])
        self.assertEqual("controlled_demonstration_only", build.manifest["claimLevel"])
        self.assertEqual(
            {"relevant", "irrelevant"},
            set(build.manifest["relevanceCounts"]),
        )
        self.assertEqual(
            {"verified", "should_not_verify", "advisory_only"},
            set(build.manifest["compositeCounts"]),
        )
        self.assertEqual(
            {"linked", "free_form"},
            set(build.manifest["modeCounts"]),
        )
        self.assertGreaterEqual(build.manifest["verifiedEligibleCount"], 8)
        self.assertGreaterEqual(build.manifest["shouldNotVerifyCount"], 8)
        self.assertGreaterEqual(build.manifest["irrelevantCount"], 8)
        self.assertGreaterEqual(build.manifest["relevantControlCount"], 8)
        self.assertFalse(build.manifest["containsLearnerIdentity"])
        self.assertFalse(build.manifest["containsAnswerKeys"])

    def test_identity_answer_key_copied_provenance_real_claims_and_unknown_fields_fail(self):
        mutations = (
            ("studentId", "learner-1", "forbidden"),
            ("answerKey", "42", "forbidden"),
            ("copiedFromForum", True, "forbidden"),
            ("learnerDistributionClaim", "representative", "forbidden"),
            ("unexpected", "value", "exactly"),
        )
        for field, value, error in mutations:
            with self.subTest(field=field), TemporaryDirectory() as directory:
                document = copy.deepcopy(self.document)
                document["scenarioFamilies"][0]["examples"][0][field] = value
                with self.assertRaisesRegex(ValueError, error):
                    build_forum_dataset(self._catalogue(directory, document))

        for field, value in (
            ("trainingDataProvenance", "real"),
            ("evidenceLevel", "real_evaluated"),
        ):
            with self.subTest(field=field), TemporaryDirectory() as directory:
                document = copy.deepcopy(self.document)
                document[field] = value
                with self.assertRaisesRegex(ValueError, "controlled-demo contract"):
                    build_forum_dataset(self._catalogue(directory, document))

    def test_language_label_version_and_family_contracts_are_enforced(self):
        mutations = (
            ("language", "fr"),
            ("label", "correct"),
            ("rubricVersion", "other-rubric"),
            ("expectedRelevance", "maybe"),
            ("expectedComposite", "partially_verified"),
        )
        for field, value in mutations:
            with self.subTest(field=field), TemporaryDirectory() as directory:
                document = copy.deepcopy(self.document)
                if field == "rubricVersion":
                    document[field] = value
                else:
                    document["scenarioFamilies"][0]["examples"][0][field] = value
                with self.assertRaises(ValueError):
                    build_forum_dataset(self._catalogue(directory, document))

    def test_free_form_examples_cannot_declare_correctness_and_linked_must(self):
        with TemporaryDirectory() as directory:
            document = copy.deepcopy(self.document)
            family = next(
                item for item in document["scenarioFamilies"]
                if item["mode"] == "free_form"
            )
            family["examples"][0]["expectedCorrect"] = True
            with self.assertRaisesRegex(ValueError, "cannot declare"):
                build_forum_dataset(self._catalogue(directory, document))

        with TemporaryDirectory() as directory:
            document = copy.deepcopy(self.document)
            family = next(
                item for item in document["scenarioFamilies"]
                if item["mode"] == "linked"
            )
            del family["examples"][0]["expectedCorrect"]
            with self.assertRaisesRegex(ValueError, "exactly"):
                build_forum_dataset(self._catalogue(directory, document))

    def test_composite_labels_must_match_the_frozen_decision_rule(self):
        with TemporaryDirectory() as directory:
            document = copy.deepcopy(self.document)
            linked = next(
                item for item in document["scenarioFamilies"]
                if item["mode"] == "linked"
            )
            verified = next(
                item for item in linked["examples"]
                if (
                    item["expectedComposite"] == "verified"
                    and item["expectedCorrect"] is True
                    and item["expectedRelevance"] == "relevant"
                    and item["label"] == "explanation_sufficient"
                )
            )
            verified["expectedCorrect"] = False
            with self.assertRaisesRegex(ValueError, "failing linked"):
                build_forum_dataset(self._catalogue(directory, document))

        with TemporaryDirectory() as directory:
            document = copy.deepcopy(self.document)
            linked = next(
                item for item in document["scenarioFamilies"]
                if item["mode"] == "linked"
            )
            failing = next(
                item for item in linked["examples"]
                if item["expectedCorrect"] is False
            )
            failing["expectedCorrect"] = True
            failing["expectedRelevance"] = "relevant"
            failing["label"] = "explanation_sufficient"
            failing["expectedComposite"] = "should_not_verify"
            with self.assertRaisesRegex(ValueError, "passing linked"):
                build_forum_dataset(self._catalogue(directory, document))

    def test_verification_catalogue_enforces_r22_support_and_language_coverage(self):
        with TemporaryDirectory() as directory:
            document = copy.deepcopy(self.document)
            document["scenarioFamilies"] = [
                item for item in document["scenarioFamilies"]
                if item["scenarioFamilyId"] in {
                    "addition-regrouping-en-v1",
                    "subtraction-borrowing-ms-v1",
                }
            ]
            with self.assertRaisesRegex(ValueError, "verified-eligible"):
                build_forum_dataset(self._catalogue(directory, document))

        with TemporaryDirectory() as directory:
            document = copy.deepcopy(self.document)
            family = next(
                item for item in document["scenarioFamilies"]
                if item["mode"] == "linked"
            )
            family["promptBm"] = ""
            with self.assertRaisesRegex(ValueError, "non-empty"):
                build_forum_dataset(self._catalogue(directory, document))

    def test_example_text_rejects_obvious_identifiers_credentials_and_answer_keys(self):
        forbidden_texts = (
            "Contact learner@example.com about this fictional response.",
            "Call +60 12-345 6789 to discuss the calculation.",
            "Student ID: STU-2048 submitted this explanation.",
            "The API key: abcdefghijklmnop must remain secret.",
            "Answer key: 42 is included for the reviewer.",
        )
        for text in forbidden_texts:
            with self.subTest(text=text), TemporaryDirectory() as directory:
                document = copy.deepcopy(self.document)
                document["scenarioFamilies"][0]["examples"][0]["text"] = text
                with self.assertRaisesRegex(ValueError, "forbidden"):
                    build_forum_dataset(self._catalogue(directory, document))

    def test_fictional_author_declaration_is_exact(self):
        with TemporaryDirectory() as directory:
            document = copy.deepcopy(self.document)
            document["authorDeclaration"] = "developer-name-or-unreviewed-source"
            with self.assertRaisesRegex(ValueError, "authorDeclaration"):
                build_forum_dataset(self._catalogue(directory, document))

    def test_canonical_rebuild_ignores_line_endings_but_detects_catalogue_or_generated_edits(self):
        with TemporaryDirectory() as directory:
            lf = self._catalogue(directory, self.document, newline="\n")
            first = build_forum_dataset(lf)
            crlf_path = Path(directory) / "catalogue-crlf.yaml"
            crlf_path.write_text(
                yaml.safe_dump(self.document, sort_keys=False, allow_unicode=True).replace("\n", "\r\n"),
                encoding="utf-8",
                newline="",
            )
            second = build_forum_dataset(crlf_path)
            self.assertEqual(first.manifest, second.manifest)
            self.assertEqual(first.jsonl_bytes(), second.jsonl_bytes())

            paths = write_forum_dataset(directory, catalogue_path=lf)
            verify_generated_dataset(lf, paths["dataset"], paths["manifest"])
            paths["dataset"].write_text(
                paths["dataset"].read_text(encoding="utf-8") + "{}\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "generated dataset"):
                verify_generated_dataset(lf, paths["dataset"], paths["manifest"])

            changed = copy.deepcopy(self.document)
            changed["scenarioFamilies"][0]["examples"][0]["text"] += " Tambahan fiksyen."
            changed_build = build_forum_dataset(self._catalogue(directory, changed))
            self.assertNotEqual(first.manifest["catalogueSha256"], changed_build.manifest["catalogueSha256"])
            self.assertNotEqual(first.manifest["datasetSha256"], changed_build.manifest["datasetSha256"])

    def test_emulator_fixture_is_not_a_controlled_demo_input(self):
        fixture = Path(__file__).resolve().parents[1] / "logic_oasis_ai" / "forum_ai" / "data" / "emulator_reviewed_examples.jsonl"
        with self.assertRaisesRegex(ValueError, "catalogue"):
            build_forum_dataset(fixture)

    def test_dataset_pair_preserves_previous_outputs_when_staging_fails(self):
        with TemporaryDirectory() as directory:
            paths = write_forum_dataset(directory)
            before = {key: path.read_bytes() for key, path in paths.items()}
            original_write = Path.write_bytes
            staged_writes = 0

            def fail_second_staged_write(path, content):
                nonlocal staged_writes
                if path.name.startswith("staged-"):
                    staged_writes += 1
                    if staged_writes == 2:
                        raise OSError("injected staging failure")
                return original_write(path, content)

            with patch.object(Path, "write_bytes", fail_second_staged_write):
                with self.assertRaisesRegex(OSError, "injected staging failure"):
                    write_forum_dataset(directory)

            self.assertEqual(before, {key: path.read_bytes() for key, path in paths.items()})
            self.assertEqual([], list(Path(directory).glob(".forum-publication-*")))

    def test_failed_restore_preserves_the_only_backup_for_recovery(self):
        with TemporaryDirectory() as directory:
            paths = write_forum_dataset(directory)
            previous_dataset = paths["dataset"].read_bytes()
            original_replace = os.replace

            def fail_publish_and_restore(source, destination):
                source_path = Path(source)
                destination_path = Path(destination)
                if (
                    source_path.name == "staged-0"
                    and destination_path == paths["dataset"]
                ):
                    raise OSError("injected staged replacement failure")
                if (
                    source_path.name == "backup-0"
                    and destination_path == paths["dataset"]
                ):
                    raise OSError("injected backup restoration failure")
                return original_replace(source, destination)

            with patch(
                "forum_controlled_demo.build_forum_dataset.os.replace",
                side_effect=fail_publish_and_restore,
            ):
                with self.assertRaisesRegex(OSError, "staged replacement failure"):
                    write_forum_dataset(directory)

            staging = list(Path(directory).glob(".forum-publication-*"))
            self.assertEqual(1, len(staging))
            self.assertFalse(paths["dataset"].exists())
            self.assertEqual(previous_dataset, (staging[0] / "backup-0").read_bytes())
            self.assertTrue(paths["manifest"].exists())


if __name__ == "__main__":
    unittest.main()
