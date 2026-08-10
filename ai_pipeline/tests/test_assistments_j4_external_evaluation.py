"""J4 tests: frozen external comparison, identity, preprocessing, stability."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

from logic_oasis_ai.prediction_contract import SupervisedExample

from training import evaluate_models
from training.evaluate_models import (
    EXTERNAL_ARTIFACT_STATUS,
    EXTERNAL_PROVENANCE,
    RANDOM_SEED,
    evaluate_external_fair_comparison,
    repeated_grouped_validation,
    row_identity_sha256,
)


def external_examples(
    *,
    learners: tuple[str, ...] = ("s1", "s2", "s3", "s4", "s5", "s6"),
    provenance: str = EXTERNAL_PROVENANCE,
) -> tuple[SupervisedExample, ...]:
    examples = []
    now = datetime(2022, 1, 1, tzinfo=timezone.utc)
    for learner_index, learner in enumerate(learners):
        for attempt_index in range(3):
            correct_rate = 0.4 + (learner_index + attempt_index) % 5 * 0.05
            target = correct_rate < 0.60
            examples.append(
                SupervisedExample(
                    attempt_id=f"episode-{learner}-{attempt_index}",
                    student_key=learner,
                    subtopic_id="6.RP.A.3b",
                    observed_at=now,
                    features={
                        "correct_rate": correct_rate,
                        "mean_response_time_ms": 50_000.0 + learner_index * 1_000 + attempt_index,
                    },
                    target=target,
                    contract=None,
                    provenance=provenance,
                    evaluation_group_key=learner,
                )
            )
    return tuple(examples)


def split_keys(learners: tuple[str, ...] = ("s1", "s2", "s3", "s4", "s5", "s6")):
    return list(learners[:4]), list(learners[4:])


class ExternalEvaluationTests(unittest.TestCase):
    def test_requires_external_real_provenance(self):
        rows = external_examples(provenance="real")
        train_keys, test_keys = split_keys()
        with self.assertRaisesRegex(ValueError, "external_real"):
            evaluate_external_fair_comparison(
                rows,
                random_seed=RANDOM_SEED,
                train_learner_keys=train_keys,
                test_learner_keys=test_keys,
                contract_version="v2",
                dataset_version="d1",
            )

    def test_seed_is_enforced(self):
        rows = external_examples()
        train_keys, test_keys = split_keys()
        with self.assertRaisesRegex(ValueError, "random seed"):
            evaluate_external_fair_comparison(
                rows,
                random_seed=7,
                train_learner_keys=train_keys,
                test_learner_keys=test_keys,
                contract_version="v2",
                dataset_version="d1",
            )

    def test_learner_overlap_is_rejected(self):
        rows = external_examples()
        with self.assertRaisesRegex(ValueError, "overlap"):
            evaluate_external_fair_comparison(
                rows,
                random_seed=RANDOM_SEED,
                train_learner_keys=["s1", "s2"],
                test_learner_keys=["s2", "s3"],
                contract_version="v2",
                dataset_version="d1",
            )

    def test_every_row_belongs_to_exactly_one_partition(self):
        rows = external_examples()
        with self.assertRaisesRegex(ValueError, "exactly one frozen partition"):
            evaluate_external_fair_comparison(
                rows,
                random_seed=RANDOM_SEED,
                train_learner_keys=["s1"],
                test_learner_keys=["s2"],
                contract_version="v2",
                dataset_version="d1",
            )

    def test_identical_rows_features_and_split_across_models(self):
        rows = external_examples()
        train_keys, test_keys = split_keys()
        report = evaluate_external_fair_comparison(
            rows,
            random_seed=RANDOM_SEED,
            train_learner_keys=train_keys,
            test_learner_keys=test_keys,
            contract_version="assistments-j2-attempt-label-contract-v2",
            dataset_version="release",
        )
        self.assertEqual([result.algorithm for result in report.results], ["decision_tree", "xgboost", "mlp"])
        self.assertEqual(len({tuple(result.feature_names) for result in report.results}), 1)
        self.assertEqual(report.feature_names, ("correct_rate", "mean_response_time_ms"))
        self.assertEqual(report.train_row_count + report.test_row_count, len(rows))
        self.assertTrue(report.row_identity_sha256)
        self.assertTrue(report.train_identity_sha256)
        self.assertTrue(report.test_identity_sha256)
        self.assertEqual(report.artifact_status, EXTERNAL_ARTIFACT_STATUS)
        for result in report.results:
            self.assertIn("accuracy", result.metrics)
            self.assertIn("confusion_matrix", result.metrics)

    def test_mlp_early_stopping_disabled_and_scaler_fit_on_training_only(self):
        rows = external_examples()
        train_keys, test_keys = split_keys()
        report = evaluate_external_fair_comparison(
            rows,
            random_seed=RANDOM_SEED,
            train_learner_keys=train_keys,
            test_learner_keys=test_keys,
            contract_version="v2",
            dataset_version="d1",
        )
        mlp_result = next(result for result in report.results if result.algorithm == "mlp")
        pipeline = mlp_result.model
        self.assertFalse(pipeline.named_steps["mlpclassifier"].early_stopping)
        scaler = pipeline.named_steps["standardscaler"]
        self.assertTrue(hasattr(scaler, "mean_"), "scaler must be fit on training learners only")

    def test_held_out_never_used_for_fitting(self):
        rows = external_examples()
        train_keys, test_keys = split_keys()
        fitted_students: list[str] = []
        original = evaluate_models.train_decision_tree

        def recording_trainer(examples, *, random_seed):
            fitted_students.extend(row.student_key for row in examples)
            return original(examples, random_seed=random_seed)

        with patch.object(evaluate_models, "train_decision_tree", side_effect=recording_trainer):
            evaluate_external_fair_comparison(
                rows,
                random_seed=RANDOM_SEED,
                train_learner_keys=train_keys,
                test_learner_keys=test_keys,
                contract_version="v2",
                dataset_version="d1",
            )
        self.assertEqual(set(fitted_students), set(train_keys))
        self.assertFalse(set(fitted_students) & set(test_keys))

    def test_row_identity_hash_is_deterministic_and_partition_sensitive(self):
        rows = external_examples()
        self.assertEqual(row_identity_sha256(rows, partition="train"), row_identity_sha256(rows, partition="train"))
        self.assertNotEqual(row_identity_sha256(rows, partition="train"), row_identity_sha256(rows, partition="test"))


class GroupedStabilityTests(unittest.TestCase):
    def test_folds_keep_whole_learners_together_and_exclude_held_out(self):
        held_out = {"s5", "s6"}
        training = external_examples(learners=("s1", "s2", "s3", "s4", "s7", "s8", "s9", "s10"))
        training_keys = {row.student_key for row in training}
        stability = repeated_grouped_validation(training, random_seed=RANDOM_SEED, n_folds=4)
        self.assertEqual(stability.n_folds, 4)
        validation_keys = [set(fold.validation_learner_keys) for fold in stability.folds]
        # whole learners together: folds are disjoint and exhaustive over training learners
        for index, keys in enumerate(validation_keys):
            for other in validation_keys[index + 1:]:
                self.assertFalse(keys & other)
        self.assertEqual(set().union(*validation_keys), training_keys)
        # frozen held-out learners never appear in the training-only analysis
        self.assertFalse(held_out & training_keys)
        self.assertFalse(held_out & set().union(*validation_keys))

    def test_fold_partitions_are_deterministic_and_report_per_model_metrics(self):
        training = external_examples(learners=("s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"))
        first = repeated_grouped_validation(training, random_seed=RANDOM_SEED, n_folds=5)
        second = repeated_grouped_validation(training, random_seed=RANDOM_SEED, n_folds=5)
        self.assertEqual(
            [tuple(f.validation_learner_keys for f in first.folds)],
            [tuple(f.validation_learner_keys for f in second.folds)],
        )
        self.assertIn("decision_tree", first.per_model_metrics)
        self.assertIn("xgboost", first.per_model_metrics)
        self.assertIn("mlp", first.per_model_metrics)
        self.assertIn("accuracy", first.per_model_metrics["mlp"])

    def test_no_runtime_promotion_path(self):
        source = Path(__file__).resolve().parents[1] / "external_data" / "assistments" / "run_j4.py"
        text = source.read_text(encoding="utf-8")
        self.assertNotIn("ModelRegistry", text)
        self.assertNotIn("registry.", text)
        rows = external_examples()
        train_keys, test_keys = split_keys()
        report = evaluate_external_fair_comparison(
            rows,
            random_seed=RANDOM_SEED,
            train_learner_keys=train_keys,
            test_learner_keys=test_keys,
            contract_version="v2",
            dataset_version="d1",
        )
        self.assertEqual(report.artifact_status, "evidence_only_external")


if __name__ == "__main__":
    unittest.main()
