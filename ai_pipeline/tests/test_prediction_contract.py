from datetime import datetime, timedelta, timezone
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from logic_oasis_ai.features import AttemptFeatureRow, FEATURE_SCHEMA_VERSION
from logic_oasis_ai.model_registry import ModelArtifact, ModelRegistry
from logic_oasis_ai.prediction_contract import (
    PredictionContract, SupervisedExample, assess_data_sufficiency,
    build_supervised_examples, feature_names,
)
from training.common import grouped_holdout_split
from training.evaluate_models import (
    evaluate_bkt_ablation, evaluate_fair_comparison, load_xgboost_bundle,
    save_xgboost_bundle,
)


NOW = datetime(2026, 7, 16, tzinfo=timezone.utc)


def feature_attempt(student: int, sequence: int, correct_rate: float) -> AttemptFeatureRow:
    return AttemptFeatureRow(
        attempt_id=f"attempt-{student}-{sequence}", student_key=f"student-{student}",
        topic_id="topic-1", subtopic_id="subtopic-1", bank_id="bank-1", difficulty_level="Easy",
        content_version="v1", finalized_at=(NOW + timedelta(days=sequence)).isoformat(),
        total_questions=10, correct_count=round(correct_rate * 10), correct_rate=correct_rate,
        mean_response_time_ms=1000.0 + student, mean_hint_count=float(sequence % 2), provenance="real",
    )


def fixture_attempts(student_count: int = 4):
    rows = []
    for student in range(student_count):
        # Each student contributes both outcomes, so grouped partitions remain valid.
        rows.extend((
            feature_attempt(student, 0, 0.8),
            feature_attempt(student, 1, 0.4),
            feature_attempt(student, 2, 0.8),
        ))
    return tuple(rows)


class PredictionContractTests(unittest.TestCase):
    def test_target_uses_next_same_subtopic_attempt_and_censors_last_attempt(self):
        examples = build_supervised_examples(fixture_attempts(1))

        self.assertEqual([row.attempt_id for row in examples], ["attempt-0-0", "attempt-0-1"])
        self.assertEqual([row.target for row in examples], [True, False])

    def test_missing_next_attempt_is_never_auto_labelled(self):
        self.assertEqual(build_supervised_examples((feature_attempt(1, 0, 0.5),)), ())

    def test_future_features_are_rejected(self):
        example = SupervisedExample(
            attempt_id="a", student_key="student", subtopic_id="subtopic", observed_at=NOW,
            features={"total_questions": 5.0, "correct_count": 3.0, "correct_rate": 0.6,
                      "mean_response_time_ms": 1000.0, "mean_hint_count": 0.0, "next_attempt_score": 1.0},
            target=False, contract=PredictionContract(),
        )
        with self.assertRaisesRegex(ValueError, "future or undeclared"):
            feature_names((example,))

    def test_grouped_split_never_shares_a_student(self):
        examples = build_supervised_examples(fixture_attempts())
        train, test = grouped_holdout_split(examples, random_seed=7)

        self.assertFalse({row.student_key for row in train} & {row.student_key for row in test})

    def test_tiny_data_downgrades_claim_to_preliminary(self):
        readiness = assess_data_sufficiency(build_supervised_examples(fixture_attempts(2)))

        self.assertEqual(readiness.claim_level, "preliminary_comparison")

    def test_all_models_use_identical_rows_and_features(self):
        report = evaluate_fair_comparison(build_supervised_examples(fixture_attempts()), random_seed=7)

        self.assertEqual([result.algorithm for result in report.results], ["decision_tree", "xgboost", "mlp"])
        self.assertEqual(len(set(result.feature_names for result in report.results)), 1)
        self.assertEqual(report.data_sufficiency.claim_level, "held_out_comparison")

    def test_bkt_ablation_requires_identical_labelled_rows(self):
        base = build_supervised_examples(fixture_attempts())
        bkt = build_supervised_examples(
            fixture_attempts(),
            bkt_mastery_by_attempt_id={attempt.attempt_id: 0.5 for attempt in fixture_attempts()},
        )
        reports = evaluate_bkt_ablation(base, bkt, random_seed=7)

        self.assertEqual(reports["without_bkt"].train_attempt_ids, reports["with_bkt"].train_attempt_ids)
        self.assertIn("bkt_mastery_probability", reports["with_bkt"].results[0].feature_names)

        changed_base = replace(bkt[0], features={**bkt[0].features, "correct_rate": 0.1})
        with self.assertRaisesRegex(ValueError, "may differ only"):
            evaluate_bkt_ablation(base, (changed_base, *bkt[1:]), random_seed=7)

    def test_evaluated_xgboost_bundle_matches_contract_but_stays_a_candidate(self):
        report = evaluate_fair_comparison(build_supervised_examples(fixture_attempts()), random_seed=7)
        with TemporaryDirectory() as temporary_directory:
            artifact = save_xgboost_bundle(
                report, Path(temporary_directory) / "candidate.joblib",
                model_version="2026-07-16-v1", training_dataset_version="dataset-v1",
            )
            bundle = load_xgboost_bundle(Path(temporary_directory) / "candidate.joblib", contract=PredictionContract())
            self.assertEqual(bundle["manifest"]["targetName"], "next_attempt_support_needed")
            registry = ModelRegistry()
            registry.register_candidate(artifact)
            with self.assertRaisesRegex(ValueError, "promotion gates"):
                registry.promote(artifact.artifact_id, promoted_at=NOW)

    def test_legacy_or_unevaluated_artifacts_cannot_become_active(self):
        registry = ModelRegistry()
        registry.register_candidate(ModelArtifact(
            artifact_id="legacy", model_type="decision_tree", model_version="old",
            feature_schema_version=FEATURE_SCHEMA_VERSION, training_dataset_version="legacy",
            artifact_sha256="legacy-hash",
        ))
        with self.assertRaisesRegex(ValueError, "only evaluated XGBoost"):
            registry.promote("legacy", promoted_at=NOW)

        registry.register_candidate(ModelArtifact(
            artifact_id="legacy-xgb", model_type="xgboost", model_version="old",
            feature_schema_version=FEATURE_SCHEMA_VERSION, training_dataset_version="legacy",
            artifact_sha256="legacy-xgb-hash", prediction_target="masteryLabel",
            evaluation_status="evaluated", evaluation_report_sha256="legacy-report", promotion_gate_status="passed",
        ))
        with self.assertRaisesRegex(ValueError, "prediction contract"):
            registry.promote("legacy-xgb", promoted_at=NOW)

        registry.register_candidate(ModelArtifact(
            artifact_id="stale-schema", model_type="xgboost", model_version="old",
            feature_schema_version="old-schema", training_dataset_version="legacy",
            artifact_sha256="stale-schema-hash", evaluation_status="evaluated",
            evaluation_report_sha256="stale-report", promotion_gate_status="passed",
        ))
        with self.assertRaisesRegex(ValueError, "prediction contract"):
            registry.promote("stale-schema", promoted_at=NOW)


if __name__ == "__main__":
    unittest.main()
