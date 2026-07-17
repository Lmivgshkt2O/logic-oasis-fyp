from datetime import datetime, timedelta, timezone
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from logic_oasis_ai.features import AttemptFeatureRow, FEATURE_SCHEMA_VERSION
from logic_oasis_ai.model_registry import ModelArtifact, ModelRegistry
from logic_oasis_ai.prediction_contract import (
    BktAttemptEvidence, PredictionContract, SupervisedExample, assess_data_sufficiency,
    build_prediction_dataset, build_supervised_examples, feature_names,
)
from training.common import grouped_holdout_split
from training.evaluate_models import (
    RANDOM_SEED, evaluate_bkt_ablation, evaluate_fair_comparison, load_xgboost_bundle,
    save_xgboost_bundle,
)
from training.train_mlp import train_mlp


NOW = datetime(2026, 7, 16, tzinfo=timezone.utc)


def feature_attempt(student: int, sequence: int, correct_rate: float, **overrides) -> AttemptFeatureRow:
    values = dict(
        attempt_id=f"attempt-{student}-{sequence}", student_key=f"synthetic-student-{student}",
        topic_id="topic-1", subtopic_id="subtopic-1", bank_id="bank-1", difficulty_level="Easy",
        content_version="content-v1", finalized_at=(NOW + timedelta(days=sequence)).isoformat(),
        total_questions=5, correct_count=round(correct_rate * 5), correct_rate=correct_rate,
        mean_response_time_ms=1000.0 + student, mean_hint_count=0.0, provenance="synthetic_test",
        source_attempt_sequence=sequence + 1, year_level=4, assignment_source="adaptive",
        adaptive_policy_version="adaptive-policy-v1", skill_ids=("skill-1",),
        question_ids=(f"question-{student}-{sequence}",), response_ids=(f"response-{student}-{sequence}",),
        question_versions=("content-v1",),
    )
    values.update(overrides)
    return AttemptFeatureRow(**values)


def fixture_attempts(student_count: int = 4):
    rows = []
    for student in range(student_count):
        rows.extend((
            feature_attempt(student, 0, 0.8),
            feature_attempt(student, 1, 0.4),
            feature_attempt(student, 2, 0.8),
        ))
    return tuple(rows)


def synthetic_examples(rows=None):
    return build_supervised_examples(rows or fixture_attempts(), allow_synthetic_test=True)


class PredictionContractTests(unittest.TestCase):
    def test_v2_is_the_only_base_feature_contract(self):
        self.assertEqual(FEATURE_SCHEMA_VERSION, "quiz-attempt-features-v2")
        self.assertEqual(feature_attempt(1, 0, 0.8).to_model_features(), {
            "correct_rate": 0.8, "mean_response_time_ms": 1001.0,
        })
        with self.assertRaisesRegex(ValueError, "only quiz-attempt-features-v2"):
            PredictionContract(feature_schema_version="quiz-attempt-features-v1")

    def test_target_uses_direct_next_eligible_attempt_and_censors_last_attempt(self):
        dataset = build_prediction_dataset(fixture_attempts(1), allow_synthetic_test=True)
        self.assertEqual([row.attempt_id for row in dataset.examples], ["attempt-0-0", "attempt-0-1"])
        self.assertEqual([row.target for row in dataset.examples], [True, False])
        self.assertEqual(dataset.pair_audit_summary.censored_no_later_attempt, 1)

    def test_missing_next_attempt_is_never_auto_labelled(self):
        self.assertEqual(synthetic_examples((feature_attempt(1, 0, 0.5),)), ())

    def test_incompatible_policy_and_immediate_repeats_are_censored_without_skipping_forward(self):
        first = feature_attempt(1, 0, 0.8)
        incompatible = feature_attempt(1, 1, 0.4, adaptive_policy_version="new-semantics")
        later = feature_attempt(1, 2, 0.4, adaptive_policy_version="new-semantics")
        policy_dataset = build_prediction_dataset((first, incompatible, later), allow_synthetic_test=True)
        self.assertEqual([row.attempt_id for row in policy_dataset.examples], ["attempt-1-1"])
        self.assertEqual(policy_dataset.pair_audit_summary.censored_policy_pairs, 1)

        repeated = feature_attempt(1, 1, 0.4, question_ids=first.question_ids)
        repeat_dataset = build_prediction_dataset((first, repeated), allow_synthetic_test=True)
        self.assertEqual(repeat_dataset.examples, ())
        self.assertEqual(repeat_dataset.pair_audit_summary.censored_repeated_question_pairs, 1)
        self.assertEqual(repeat_dataset.pair_audit_summary.immediate_question_repeats, 1)

    def test_pair_audit_reports_same_and_cross_bank_strata(self):
        rows = (feature_attempt(1, 0, 0.8), feature_attempt(1, 1, 0.4, bank_id="bank-2"))
        dataset = build_prediction_dataset(rows, allow_synthetic_test=True)
        self.assertEqual(dataset.pair_audit_summary.cross_bank_pairs, 1)
        self.assertEqual(dataset.pair_audit_summary.same_bank_pairs, 0)

    def test_future_features_and_hint_count_are_rejected(self):
        example = SupervisedExample(
            attempt_id="a", student_key="student", subtopic_id="subtopic", observed_at=NOW,
            features={"correct_rate": 0.6, "mean_response_time_ms": 1000.0, "hint_count": 0.0},
            target=False, contract=PredictionContract(), provenance="synthetic_test",
        )
        with self.assertRaisesRegex(ValueError, "future or undeclared"):
            feature_names((example,))

    def test_grouped_split_never_shares_student_and_uses_declared_seed(self):
        examples = synthetic_examples()
        train, test = grouped_holdout_split(examples, random_seed=RANDOM_SEED)
        self.assertFalse({row.student_key for row in train} & {row.student_key for row in test})

    def test_synthetic_rows_can_exercise_models_but_never_claim_comparison(self):
        examples = synthetic_examples()
        readiness = assess_data_sufficiency(examples)
        self.assertEqual(readiness.claim_level, "synthetic_test_only")
        report = evaluate_fair_comparison(examples, allow_synthetic_test=True)
        self.assertEqual(report.data_sufficiency.claim_level, "synthetic_test_only")
        self.assertEqual([result.algorithm for result in report.results], ["decision_tree", "xgboost", "mlp"])
        self.assertEqual(report.random_seed, RANDOM_SEED)
        self.assertEqual(len(set(result.feature_names for result in report.results)), 1)
        self.assertEqual(set(report.results[0].feature_names), {"correct_rate", "mean_response_time_ms"})

    def test_nondefault_seed_and_unmarked_synthetic_data_are_refused(self):
        with self.assertRaisesRegex(ValueError, "deterministic random seed"):
            evaluate_fair_comparison(synthetic_examples(), random_seed=7, allow_synthetic_test=True)
        with self.assertRaisesRegex(ValueError, "only approved real"):
            build_supervised_examples((replace(feature_attempt(1, 0, 0.5), provenance="emulator_verified"),))

    def test_typed_bkt_ablation_requires_current_lineage_and_identical_rows(self):
        rows = fixture_attempts()
        base = synthetic_examples(rows)
        evidence = {
            row.attempt_id: BktAttemptEvidence(
                attempt_id=row.attempt_id, source_attempt_sequence=row.source_attempt_sequence or 0,
                student_key=row.student_key, subtopic_id=row.subtopic_id, skill_id="skill-1",
                source_response_ids=row.response_ids, bkt_version="bkt-v1", p_known_after_attempt=0.5,
            )
            for row in rows
        }
        bkt = build_supervised_examples(rows, bkt_evidence_by_attempt_id=evidence, allow_synthetic_test=True)
        reports = evaluate_bkt_ablation(base, bkt, allow_synthetic_test=True)
        self.assertEqual(reports["without_bkt"].train_attempt_ids, reports["with_bkt"].train_attempt_ids)
        self.assertIn("bkt_mastery_probability", reports["with_bkt"].results[0].feature_names)
        changed = replace(bkt[0], features={**bkt[0].features, "correct_rate": 0.1})
        with self.assertRaisesRegex(ValueError, "may differ only"):
            evaluate_bkt_ablation(base, (changed, *bkt[1:]), allow_synthetic_test=True)

    def test_mlp_early_stopping_is_disabled(self):
        model, _ = train_mlp(synthetic_examples(), random_seed=RANDOM_SEED)
        self.assertFalse(model.named_steps["mlpclassifier"].early_stopping)

    def test_evaluated_xgboost_bundle_matches_v2_contract_but_stays_candidate(self):
        report = evaluate_fair_comparison(synthetic_examples(), allow_synthetic_test=True)
        with TemporaryDirectory() as temporary_directory:
            artifact = save_xgboost_bundle(
                report, Path(temporary_directory) / "synthetic-candidate.joblib",
                model_version="synthetic-test-v1", training_dataset_version="synthetic-test-v1",
            )
            bundle = load_xgboost_bundle(Path(temporary_directory) / "synthetic-candidate.joblib", contract=PredictionContract())
            self.assertEqual(bundle["manifest"]["targetName"], "next_attempt_support_needed")
            self.assertEqual(bundle["manifest"]["featureSchemaVersion"], "quiz-attempt-features-v2")
            self.assertTrue(artifact.artifact_manifest_sha256)
            registry = ModelRegistry()
            registry.register_candidate(artifact)
            with self.assertRaisesRegex(ValueError, "promotion gates"):
                registry.promote(artifact.artifact_id, promoted_at=NOW)

    def test_legacy_or_unevaluated_artifacts_cannot_become_active(self):
        registry = ModelRegistry()
        registry.register_candidate(ModelArtifact(
            artifact_id="legacy", model_type="decision_tree", model_version="old",
            feature_schema_version="quiz-attempt-features-v1", training_dataset_version="legacy",
            artifact_sha256="legacy-hash",
        ))
        with self.assertRaisesRegex(ValueError, "only evaluated XGBoost"):
            registry.promote("legacy", promoted_at=NOW)
        registry.register_candidate(ModelArtifact(
            artifact_id="legacy-xgb", model_type="xgboost", model_version="old",
            feature_schema_version="quiz-attempt-features-v1", training_dataset_version="legacy",
            artifact_sha256="legacy-xgb-hash", prediction_target="masteryLabel",
            evaluation_status="evaluated", evaluation_report_sha256="legacy-report", promotion_gate_status="passed",
            artifact_manifest_sha256="legacy-manifest",
        ))
        with self.assertRaisesRegex(ValueError, "prediction contract"):
            registry.promote("legacy-xgb", promoted_at=NOW)


if __name__ == "__main__":
    unittest.main()
