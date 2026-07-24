from __future__ import annotations

from dataclasses import replace
import json
from math import exp
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from logic_oasis_ai.features import BASE_FEATURE_NAMES
from training.common import grouped_holdout_split
from training.evaluate_models import RANDOM_SEED, evaluate_fair_comparison
from training.publish_controlled_demo_bundle import (
    SHAP_RECONSTRUCTION_TOLERANCE,
    load_controlled_demo_bundle,
    publish_controlled_demo_bundle,
    write_controlled_demo_report,
)
from training.train_controlled_demo_xgboost import train_controlled_demo_xgboost


class ControlledDemoEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evaluation = train_controlled_demo_xgboost()

    def test_all_models_share_grouped_rows_and_exact_v2_columns(self):
        report = self.evaluation.report

        self.assertEqual(report.evaluation_status, "evaluated")
        self.assertEqual(report.data_sufficiency.claim_level, "controlled_demonstration_only")
        self.assertEqual([result.algorithm for result in report.results], ["decision_tree", "xgboost", "mlp"])
        self.assertTrue(all(result.feature_names == BASE_FEATURE_NAMES for result in report.results))
        self.assertFalse(set(report.train_evaluation_group_keys) & set(report.test_evaluation_group_keys))
        self.assertEqual(
            set(report.train_evaluation_group_keys) | set(report.test_evaluation_group_keys),
            set(self.evaluation.dataset.manifest["scenarioFamilyGroups"]),
        )
        rows = self.evaluation.dataset.prediction_dataset.examples
        train_groups = {row.evaluation_group_key for row in rows if row.attempt_id in report.train_attempt_ids}
        test_groups = {row.evaluation_group_key for row in rows if row.attempt_id in report.test_attempt_ids}
        self.assertEqual(train_groups, set(report.train_evaluation_group_keys))
        self.assertEqual(test_groups, set(report.test_evaluation_group_keys))
        self.assertEqual({row.target for row in rows if row.attempt_id in report.train_attempt_ids}, {False, True})
        self.assertEqual({row.target for row in rows if row.attempt_id in report.test_attempt_ids}, {False, True})

    def test_one_class_or_insufficient_groups_fail_closed_without_models(self):
        rows = tuple(replace(row, target=False) for row in self.evaluation.dataset.prediction_dataset.examples)

        report = evaluate_fair_comparison(rows, random_seed=RANDOM_SEED, allow_controlled_demo=True)

        self.assertEqual(report.evaluation_status, "catalogue_insufficient")
        self.assertEqual(report.results, ())

        globally_binary_but_unpartitionable = tuple(
            replace(
                row,
                target=index == 0,
                evaluation_group_key=("positive-only" if index == 0 else f"negative-{index}"),
            )
            for index, row in enumerate(self.evaluation.dataset.prediction_dataset.examples[:3])
        )
        report = evaluate_fair_comparison(
            globally_binary_but_unpartitionable,
            random_seed=RANDOM_SEED,
            allow_controlled_demo=True,
        )
        self.assertEqual(report.evaluation_status, "catalogue_insufficient")
        self.assertEqual(report.results, ())

        one_group = tuple(
            replace(row, evaluation_group_key="only-family")
            for row in self.evaluation.dataset.prediction_dataset.examples
        )
        report = evaluate_fair_comparison(one_group, random_seed=RANDOM_SEED, allow_controlled_demo=True)
        self.assertEqual(report.evaluation_status, "catalogue_insufficient")
        self.assertEqual(report.results, ())
        self.assertEqual(report.train_attempt_ids, ())
        self.assertIn("catalogue insufficient", report.data_sufficiency.reason)

    def test_evaluation_group_not_student_key_controls_isolation(self):
        rows = tuple(
            replace(row, student_key=f"student-{index}")
            for index, row in enumerate(self.evaluation.dataset.prediction_dataset.examples)
        )

        train, test = grouped_holdout_split(rows, random_seed=RANDOM_SEED)

        self.assertFalse(
            {row.evaluation_group_key for row in train}
            & {row.evaluation_group_key for row in test}
        )

    def test_bundle_manifest_and_tree_shap_are_reproducible(self):
        second_evaluation = train_controlled_demo_xgboost()
        with TemporaryDirectory() as first_directory, TemporaryDirectory() as second_directory:
            first = publish_controlled_demo_bundle(self.evaluation, first_directory)
            second = publish_controlled_demo_bundle(second_evaluation, second_directory)

            self.assertEqual(first.artifact.artifact_sha256, second.artifact.artifact_sha256)
            self.assertEqual(first.manifest_sha256, second.manifest_sha256)
            self.assertEqual(first.manifest, second.manifest)
            self.assertEqual(first.manifest["claimLevel"], "controlled_demonstration_only")
            self.assertEqual(first.manifest["randomSeed"], RANDOM_SEED)
            self.assertEqual(first.manifest["featureNames"], list(BASE_FEATURE_NAMES))
            self.assertEqual(len(first.shap_integrity), 3)
            self.assertEqual([case["riskTier"] for case in first.shap_integrity], ["low", "medium", "high"])
            for case in first.shap_integrity:
                self.assertEqual(set(case["shapValues"]), set(BASE_FEATURE_NAMES))
                self.assertTrue(any(abs(value) > 0 for value in case["shapValues"].values()))
                self.assertLessEqual(case["absoluteError"], SHAP_RECONSTRUCTION_TOLERANCE)

            model, manifest = load_controlled_demo_bundle(first.artifact_path, first.manifest_path)
            self.assertTrue(hasattr(model, "predict_proba"))
            self.assertEqual(manifest["artifactSha256"], first.artifact.artifact_sha256)
            rows_by_attempt = {
                row.attempt_id: row
                for row in self.evaluation.dataset.prediction_dataset.examples
            }
            for case in first.shap_integrity:
                row = rows_by_attempt[case["attemptId"]]
                matrix = [[float(row.features[name]) for name in BASE_FEATURE_NAMES]]
                predicted = float(model.predict_proba(matrix)[0][1])
                reconstructed = 1.0 / (
                    1.0 + exp(-(case["expectedValue"] + sum(case["shapValues"].values())))
                )
                self.assertAlmostEqual(predicted, case["supportRisk"], places=7)
                self.assertLessEqual(
                    abs(reconstructed - case["supportRisk"]),
                    SHAP_RECONSTRUCTION_TOLERANCE,
                )
            with self.assertRaisesRegex(ValueError, "output already exists"):
                publish_controlled_demo_bundle(self.evaluation, first_directory)

    def test_publication_rejects_unsafe_versions_and_recovers_from_stale_staging(self):
        with TemporaryDirectory() as directory:
            for unsafe_version in ("../outside", "C:/outside", "UPPERCASE"):
                with self.assertRaisesRegex(ValueError, "safe lowercase"):
                    publish_controlled_demo_bundle(
                        self.evaluation,
                        directory,
                        model_version=unsafe_version,
                    )

            stale = Path(directory) / ".controlled-demo-xgboost-v1.stale"
            stale.mkdir()
            (stale / "partial").write_text("interrupted", encoding="utf-8")
            published = publish_controlled_demo_bundle(self.evaluation, directory)
            self.assertTrue(published.artifact_path.is_file())
            self.assertEqual((stale / "partial").read_text(encoding="utf-8"), "interrupted")

    def test_loader_rejects_tampering_and_incomplete_manifests(self):
        with TemporaryDirectory() as directory:
            published = publish_controlled_demo_bundle(self.evaluation, directory)
            original_bytes = published.artifact_path.read_bytes()
            published.artifact_path.write_bytes(original_bytes[:-1] + bytes([original_bytes[-1] ^ 1]))
            with self.assertRaisesRegex(ValueError, "hash does not match"):
                load_controlled_demo_bundle(published.artifact_path, published.manifest_path)
            published.artifact_path.write_bytes(original_bytes)

            incomplete = dict(published.manifest)
            incomplete.pop("scenarioCatalogueSha256")
            incomplete_path = Path(directory) / "incomplete.manifest.json"
            incomplete_path.write_text(json.dumps(incomplete), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "complete controlled-demo schema"):
                load_controlled_demo_bundle(published.artifact_path, incomplete_path)

    def test_legacy_and_v1_manifests_are_rejected(self):
        with TemporaryDirectory() as directory:
            published = publish_controlled_demo_bundle(self.evaluation, directory)
            legacy_manifest = dict(published.manifest)
            legacy_manifest["featureSchemaVersion"] = "quiz-attempt-features-v1"
            manifest_path = Path(directory) / "legacy.manifest.json"
            manifest_path.write_text(json.dumps(legacy_manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                load_controlled_demo_bundle(published.artifact_path, manifest_path)

            missing_manifest = Path(directory) / "missing.manifest.json"
            with self.assertRaisesRegex(ValueError, "unavailable or malformed"):
                load_controlled_demo_bundle(published.artifact_path, missing_manifest)

    def test_report_records_hashes_parameters_and_safe_claim_boundary(self):
        with TemporaryDirectory() as directory:
            published = publish_controlled_demo_bundle(self.evaluation, directory)
            report_path = Path(directory) / "report.md"
            write_controlled_demo_report(self.evaluation, published, report_path)
            report = report_path.read_text(encoding="utf-8")

        self.assertIn("controlled_demonstration_only", report)
        self.assertIn(self.evaluation.config_sha256, report)
        self.assertIn(published.artifact.artifact_sha256, report)
        self.assertIn("not real-world performance or superiority evidence", report)
        self.assertIn("Tree SHAP integrity", report)
        committed_report = Path(__file__).resolve().parents[1] / "reports" / "controlled_demo_model_report.md"
        self.assertEqual(committed_report.read_text(encoding="utf-8"), report)


if __name__ == "__main__":
    unittest.main()
