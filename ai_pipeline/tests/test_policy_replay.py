from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from logic_oasis_ai.adaptive_policy import load_adaptive_policy_config
from logic_oasis_ai.policy_evaluation import (
    PolicyArm,
    load_policy_evaluation_manifest,
)
from logic_oasis_ai.sources.csv_source import load_csv_files
from training.export_real_attempts import (
    RealDataRelease,
    export_real_attempts,
)

from evaluation.manifest import OutcomeWindow, build_run_manifest
from evaluation.metrics import compute_metrics
from evaluation.outcomes import attach_outcomes
from evaluation.replay import (
    REPLAY_ARMS,
    ReplayError,
    derive_bank_catalog,
    replay_policies,
    student_grouped_partition,
)
from evaluation.reporting import build_machine_report, render_machine_json
from policy_fixtures import build_dataset, standard_history


CONFIGS = Path(__file__).parents[1] / "configs"
ADAPTIVE_POLICY_PATH = CONFIGS / "adaptive_policy_v1.yaml"
MANIFEST_PATH = CONFIGS / "policy_evaluation_v1.yaml"
UTC = timezone.utc
NOW = datetime(2026, 8, 1, tzinfo=UTC)


def loaded_policy():
    adaptive_policy = load_adaptive_policy_config(ADAPTIVE_POLICY_PATH)
    policy_manifest = load_policy_evaluation_manifest(
        MANIFEST_PATH, adaptive_policy=adaptive_policy
    )
    return adaptive_policy, policy_manifest


def run_manifest_for(
    dataset,
    *,
    seed: int = 7,
    claim_label: str = "pipeline_demo_only",
    window: tuple[int, int] = (5, 90),
    dataset_version: str = "fixture-v1",
):
    adaptive_policy, policy_manifest = loaded_policy()
    return build_run_manifest(
        dataset=dataset,
        dataset_version=dataset_version,
        adaptive_policy_sha256=adaptive_policy.source_sha256,
        policy_evaluation_sha256=policy_manifest.source_sha256,
        outcome_window=OutcomeWindow(
            max_later_attempts=window[0], max_calendar_duration_days=window[1]
        ),
        random_seed=seed,
        claim_label=claim_label,
    )


def replayed(
    dataset,
    *,
    run_manifest=None,
    support_risk_by_attempt=None,
    bank_catalog=None,
    arms=None,
):
    adaptive_policy, policy_manifest = loaded_policy()
    manifest = run_manifest or run_manifest_for(dataset)
    return replay_policies(
        dataset,
        run_manifest=manifest,
        adaptive_policy=adaptive_policy,
        policy_manifest=policy_manifest,
        bank_catalog=bank_catalog or derive_bank_catalog(dataset),
        support_risk_by_attempt=support_risk_by_attempt,
        arms=arms or REPLAY_ARMS,
    )


class PolicyReplayTests(unittest.TestCase):
    def test_replay_is_deterministic_and_decision_ids_repeat(self):
        dataset = build_dataset(standard_history())
        first = replayed(dataset)
        second = replayed(dataset)
        self.assertEqual(first.decisions, second.decisions)
        for decision in first.decisions:
            self.assertTrue(decision.decision_id.startswith("policy-decision-"))
            self.assertIn(decision.arm, (PolicyArm.P1, PolicyArm.P2, PolicyArm.P3A))

    def test_decision_ids_match_the_frozen_policy_contract(self):
        from logic_oasis_ai.policy_evaluation import deterministic_policy_decision_id

        dataset = build_dataset(standard_history())
        result = replayed(dataset)
        _, policy_manifest = loaded_policy()
        for decision in result.decisions:
            self.assertEqual(
                decision.decision_id,
                deterministic_policy_decision_id(
                    decision.source_attempt_id,
                    decision.arm,
                    decision.policy_version,
                    policy_manifest.source_sha256,
                ),
            )

    def test_later_attempt_cannot_change_an_earlier_decision(self):
        baseline_history = standard_history()
        baseline_dataset = build_dataset(baseline_history)
        frozen_catalog = derive_bank_catalog(baseline_dataset)
        baseline = replayed(baseline_dataset, bank_catalog=frozen_catalog)
        mutated = [
            {
                **row,
                **(
                    {
                        "correct_count": 2,
                        "content_version": "v9",
                        "bank_id": "easy-other",
                    }
                    if row["attempt_id"] == "a4"
                    else {}
                ),
            }
            for row in baseline_history
        ]
        mutated_result = replayed(
            build_dataset(mutated), bank_catalog=frozen_catalog
        )

        baseline_earlier = {
            decision.decision_id: decision
            for decision in baseline.decisions
            if decision.source_attempt_id in {"a1", "a2", "a3", "b1", "b2", "b3"}
        }
        mutated_earlier = {
            decision.decision_id: decision
            for decision in mutated_result.decisions
            if decision.source_attempt_id in {"a1", "a2", "a3", "b1", "b2", "b3"}
        }
        self.assertEqual(baseline_earlier, mutated_earlier)
        baseline_a4 = {
            decision.decision_id: decision
            for decision in baseline.decisions
            if decision.source_attempt_id == "a4"
        }
        mutated_a4 = {
            decision.decision_id: decision
            for decision in mutated_result.decisions
            if decision.source_attempt_id == "a4"
        }
        self.assertNotEqual(baseline_a4, mutated_a4)

    def test_student_grouped_partition_never_splits_a_student(self):
        dataset = build_dataset(standard_history())
        result = replayed(dataset)
        train, test = student_grouped_partition(
            result.decisions, random_seed=11, test_fraction=0.5
        )
        train_students = {decision.student_key for decision in train}
        test_students = {decision.student_key for decision in test}
        self.assertFalse(train_students & test_students)
        self.assertEqual(train_students | test_students, {"student-a", "student-b"})
        self.assertTrue(train)
        self.assertTrue(test)

    def test_provenance_and_hash_mismatch_fail_closed(self):
        dataset = build_dataset(standard_history())
        manifest = run_manifest_for(dataset)
        emulator_dataset = build_dataset(
            standard_history(),
            provenance="emulator_verified",
            allow_emulator_records=True,
        )
        with self.assertRaisesRegex(ReplayError, "provenance"):
            replayed(emulator_dataset, run_manifest=manifest)

        tampered = json.loads(json.dumps(manifest.to_document()))
        tampered["datasetSha256"] = "0" * 64
        from evaluation.manifest import EvaluationRunManifest

        with self.assertRaisesRegex(ReplayError, "dataset hash"):
            replayed(dataset, run_manifest=EvaluationRunManifest.from_document(tampered))

    def test_synthetic_provenance_cannot_support_a_real_claim(self):
        from logic_oasis_ai.sources.firestore_source import load_firestore_dataset

        with self.assertRaisesRegex(ValueError, "only approved real records"):
            build_dataset(standard_history(), provenance="synthetic_test")

    def test_missing_response_lineage_is_rejected(self):
        from logic_oasis_ai.sources.firestore_source import load_firestore_dataset
        from policy_fixtures import attempt_document

        attempt = attempt_document(
            "orphan-attempt", "student-x", sequence=1, correct_count=3
        )
        with self.assertRaises((ValueError, ReplayError)):
            load_firestore_dataset(
                [attempt], [], provenance="real"
            )

    def test_identical_trusted_exports_produce_identical_reports(self):
        dataset = build_dataset(standard_history())
        release = RealDataRelease(
            release_id="release-aqc2-1",
            dataset_version="real_v1_aqc2",
            consent_ethics_reference="ethics-approved-aqc2",
            data_steward="steward@example.edu",
            steward_approved_at=NOW,
            collection_started_at=NOW,
            collection_ended_at=NOW,
            retention_review_at=datetime(2027, 8, 1, tzinfo=UTC),
            storage_path="gs://logic-oasis-fyp-protected-data/real-data-releases/release-aqc2-1/",
            export_key_version="logic-oasis-export-pseudonymization-key-v1",
        )

        def machine_report_text(output_directory):
            export_real_attempts(
                dataset,
                output_directory,
                release=release,
                pseudonymization_key="aqc2-hmac-key",
            )
            reloaded = load_csv_files(
                Path(output_directory) / "attempts.csv",
                Path(output_directory) / "responses.csv",
                provenance="real",
            )
            result = replayed(reloaded)
            outcomes = attach_outcomes(
                result,
                reloaded,
                outcome_window=OutcomeWindow(max_later_attempts=5, max_calendar_duration_days=90),
            )
            metrics = compute_metrics(
                result,
                outcomes,
                random_seed=7,
                claim_label="pipeline_demo_only",
            )
            report = build_machine_report(
                run_manifest_for(reloaded, dataset_version="real_v1_aqc2"),
                metrics,
                attempt_count=len(reloaded.attempts),
            )
            return render_machine_json(report)

        with TemporaryDirectory() as first_directory, TemporaryDirectory() as second_directory:
            first = machine_report_text(first_directory)
            second = machine_report_text(second_directory)
        self.assertEqual(first, second)
        self.assertNotIn("student-a", first)
        self.assertNotIn("answerText", first)

    def test_hmac_namespace_changes_pseudonyms_but_raw_ids_stay_hidden(self):
        dataset = build_dataset(standard_history())
        release = RealDataRelease(
            release_id="release-aqc2-hmac",
            dataset_version="real_v1_hmac",
            consent_ethics_reference="ethics-approved-aqc2",
            data_steward="steward@example.edu",
            steward_approved_at=NOW,
            collection_started_at=NOW,
            collection_ended_at=NOW,
            retention_review_at=datetime(2027, 8, 1, tzinfo=UTC),
            storage_path="gs://logic-oasis-fyp-protected-data/real-data-releases/release-aqc2-hmac/",
            export_key_version="logic-oasis-export-pseudonymization-key-v1",
        )
        with TemporaryDirectory() as first_directory, TemporaryDirectory() as second_directory:
            export_real_attempts(
                dataset, first_directory, release=release, pseudonymization_key="key-one"
            )
            export_real_attempts(
                dataset, second_directory, release=release, pseudonymization_key="key-two"
            )
            first_reloaded = load_csv_files(
                Path(first_directory) / "attempts.csv",
                Path(first_directory) / "responses.csv",
                provenance="real",
            )
            second_reloaded = load_csv_files(
                Path(second_directory) / "attempts.csv",
                Path(second_directory) / "responses.csv",
                provenance="real",
            )
        first_keys = {decision.student_key for decision in replayed(first_reloaded).decisions}
        second_keys = {decision.student_key for decision in replayed(second_reloaded).decisions}
        self.assertNotEqual(first_keys, second_keys)
        for key in first_keys | second_keys:
            self.assertNotIn("student-a", key)
            self.assertNotIn("student-b", key)


if __name__ == "__main__":
    unittest.main()
