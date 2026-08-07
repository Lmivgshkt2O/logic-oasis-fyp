from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import evaluation.visualizations as visualizations
from logic_oasis_ai.policy_evaluation import DecisionDirection, PolicyArm
from logic_oasis_ai.prediction_contract import PredictionContract
from logic_oasis_ai.sources.csv_source import load_csv_files
from training.export_real_attempts import (
    PROTECTED_RELEASE_PREFIX,
    RealDataRelease,
    export_real_attempts,
    hmac_pseudonym,
)

from evaluation.manifest import OutcomeWindow
from evaluation.metrics import compute_metrics
from evaluation.outcomes import attach_outcomes
from evaluation.report_templates import (
    assert_claim_safe,
    render_decision_audit_csv,
    render_evidence_markdown,
    report_sha256,
)
from evaluation.visualizations import (
    VisualizationError,
    _oscillation_count,
    _oscillation_rate,
    build_evidence_package,
    derive_claim_level,
)
from policy_fixtures import build_dataset, full_bank_catalog, standard_history

from test_policy_replay import replayed, run_manifest_for


UTC = timezone.utc
NOW = datetime(2026, 8, 1, tzinfo=UTC)
WINDOW = OutcomeWindow(max_later_attempts=5, max_calendar_duration_days=90)
CONFIGS = Path(__file__).resolve().parents[1] / "configs"


def approved_release(release_id: str = "release-aqc3"):
    return RealDataRelease(
        release_id=release_id,
        dataset_version="real_v1_aqc3",
        consent_ethics_reference="ethics-approved-aqc3",
        data_steward="steward@example.edu",
        steward_approved_at=NOW,
        collection_started_at=NOW,
        collection_ended_at=NOW,
        retention_review_at=datetime(2027, 8, 1, tzinfo=UTC),
        storage_path=f"{PROTECTED_RELEASE_PREFIX}{release_id}/",
        export_key_version="logic-oasis-export-pseudonymization-key-v1",
    )


def pseudonymized(dataset):
    """Export and reload a dataset so student keys are HMAC pseudonyms."""
    with TemporaryDirectory() as temporary_directory:
        files = export_real_attempts(
            dataset,
            temporary_directory,
            release=approved_release(),
            pseudonymization_key="aqc3-hmac-key",
        )
        return load_csv_files(
            files["attempts"], files["responses"], provenance="real"
        )


def evidence_for(
    dataset,
    *,
    claim_label: str = "descriptive_replay_only",
    seed: int = 17,
    arms=None,
    support_risk_by_attempt=None,
):
    result = replayed(
        dataset,
        bank_catalog=full_bank_catalog(),
        arms=arms,
        support_risk_by_attempt=support_risk_by_attempt,
    )
    outcomes = attach_outcomes(
        result, dataset, contract=PredictionContract(), outcome_window=WINDOW
    )
    metrics = compute_metrics(
        result,
        outcomes,
        random_seed=seed,
        claim_label=claim_label,
        bootstrap_iterations=500,
    )
    run_manifest = run_manifest_for(
        dataset, seed=seed, claim_label=claim_label
    )
    evidence = build_evidence_package(
        result,
        outcomes,
        metrics,
        run_manifest,
        random_seed=seed,
        bootstrap_iterations=500,
    )
    return evidence, metrics, run_manifest, result, outcomes


def four_student_history():
    history = standard_history()
    history.extend(
        [
            {
                "attempt_id": "c1",
                "student_id": "student-c",
                "difficulty": "Easy",
                "sequence": 1,
                "correct_count": 4,
            },
            {
                "attempt_id": "c2",
                "student_id": "student-c",
                "difficulty": "Easy",
                "bank_id": "easy-2",
                "sequence": 2,
                "correct_count": 3,
                "finalized_at": NOW,
            },
            {
                "attempt_id": "d1",
                "student_id": "student-d",
                "difficulty": "Moderate",
                "bank_id": "moderate-1",
                "sequence": 1,
                "correct_count": 2,
            },
            {
                "attempt_id": "d2",
                "student_id": "student-d",
                "difficulty": "Moderate",
                "bank_id": "moderate-2",
                "sequence": 2,
                "correct_count": 4,
                "finalized_at": NOW,
            },
        ]
    )
    return history


class PolicyReportingTests(unittest.TestCase):
    def test_demo_data_claim_is_pipeline_demo_only(self):
        dataset = pseudonymized(build_dataset(standard_history()))
        evidence, metrics, run_manifest, _, _ = evidence_for(
            dataset, claim_label="pipeline_demo_only"
        )
        self.assertEqual(evidence["claimLevel"], "pipeline_demo_only")
        markdown = render_evidence_markdown(evidence, run_manifest, metrics)
        self.assertIn("pipeline_demo_only", markdown)
        self.assertNotIn("superior", markdown)

    def test_small_real_sample_is_preliminary_comparison(self):
        dataset = pseudonymized(build_dataset(standard_history()))
        evidence, _, run_manifest, _, _ = evidence_for(dataset)
        self.assertEqual(evidence["claimLevel"], "preliminary_comparison")
        claim = derive_claim_level(run_manifest, student_count=2)
        self.assertEqual(claim.label, "preliminary_comparison")
        self.assertIn("fewer than four", claim.rationale)

    def test_real_sample_with_four_students_is_descriptive_replay_only(self):
        dataset = pseudonymized(build_dataset(four_student_history()))
        evidence, _, run_manifest, _, _ = evidence_for(dataset)
        self.assertEqual(evidence["claimLevel"], "descriptive_replay_only")
        self.assertIn("claimRationale", evidence)

    def test_rendered_report_never_contains_a_superiority_claim(self):
        dataset = pseudonymized(build_dataset(four_student_history()))
        evidence, metrics, run_manifest, _, _ = evidence_for(dataset)
        markdown = render_evidence_markdown(evidence, run_manifest, metrics)
        self.assertNotIn("superior", markdown)
        self.assertNotIn("outperformed", markdown)
        with self.assertRaises(ValueError):
            assert_claim_safe("P3a is superior to P1 on this dataset")

    def test_forest_plot_machine_and_markdown_outputs_reconcile(self):
        dataset = pseudonymized(build_dataset(four_student_history()))
        evidence, metrics, run_manifest, _, outcomes = evidence_for(dataset)
        markdown = render_evidence_markdown(evidence, run_manifest, metrics)
        self.assertEqual(len(evidence["forestPlot"]), 2)
        for row in evidence["forestPlot"]:
            self.assertIn(row["comparator"], {"P1", "P2"})
            self.assertEqual(len(row["riskDifferenceCi"]), 2)
            self.assertGreater(row["sampleDenominator"], 0)
            self.assertEqual(
                row["sampleDenominator"],
                sum(
                    1
                    for outcome in outcomes.outcomes
                    if outcome.arm.value == "P3a"
                    and outcome.outcome_status == "observed"
                ),
            )
            self.assertIn(f"{row['riskDifference']:.8f}", markdown)
            self.assertIn(f"{row['falseDemotionDelta']:.8f}", markdown)
            self.assertIn(str(row["sampleDenominator"]), markdown)
            self.assertIn("Denominator", markdown)

    def test_calibration_bins_with_few_observations_are_insufficient(self):
        dataset = pseudonymized(build_dataset(standard_history()))
        evidence, _, _, _, _ = evidence_for(dataset)
        bands = evidence["bktReliabilityCurve"]
        self.assertTrue(bands)
        for band in bands:
            if band["observationCount"] < 5:
                self.assertEqual(band["status"], "insufficient")
            else:
                self.assertEqual(band["status"], "reliable")

    def test_report_contains_no_protected_content(self):
        dataset = pseudonymized(build_dataset(four_student_history()))
        evidence, metrics, run_manifest, _, _ = evidence_for(dataset)
        markdown = render_evidence_markdown(evidence, run_manifest, metrics)
        csv_text = render_decision_audit_csv(evidence)
        combined = (markdown + csv_text).lower()
        for token in (
            "student-a",
            "answertext",
            "answerkey",
            "shap",
            "artifactsha256",
            "@example",
            "traceback",
        ):
            self.assertNotIn(token, combined)

    def test_evidence_rejects_raw_student_keys(self):
        dataset = build_dataset(standard_history())
        result = replayed(dataset, bank_catalog=full_bank_catalog())
        outcomes = attach_outcomes(
            result, dataset, contract=PredictionContract(), outcome_window=WINDOW
        )
        metrics = compute_metrics(
            result,
            outcomes,
            random_seed=17,
            claim_label="pipeline_demo_only",
            bootstrap_iterations=500,
        )
        run_manifest = run_manifest_for(dataset, claim_label="pipeline_demo_only")
        with self.assertRaisesRegex(VisualizationError, "pseudonymized"):
            build_evidence_package(
                result,
                outcomes,
                metrics,
                run_manifest,
                random_seed=17,
                bootstrap_iterations=500,
            )

    def test_evidence_totals_reconcile_with_metrics_and_outcomes(self):
        dataset = pseudonymized(build_dataset(four_student_history()))
        evidence, metrics, _, result, outcomes = evidence_for(dataset)
        totals = evidence["totals"]
        self.assertEqual(totals["decisionCount"], metrics.decision_count)
        self.assertEqual(
            totals["observedCount"],
            sum(
                1
                for outcome in outcomes.outcomes
                if outcome.outcome_status == "observed"
            ),
        )
        self.assertEqual(
            totals["censoredCount"],
            sum(count for _, count in metrics.censoring_summary),
        )
        self.assertEqual(len(result.decisions), totals["decisionCount"])

    def test_p3b_is_reported_as_a_separate_stratum(self):
        dataset = pseudonymized(build_dataset(four_student_history()))
        raw_risks = {
            "a1": 0.10,
            "a2": 0.90,
            "a3": 0.20,
            "a4": 0.30,
            "b1": 0.80,
            "b2": 0.70,
            "b3": 0.05,
            "c1": 0.40,
            "c2": 0.35,
            "d1": 0.85,
            "d2": 0.60,
        }
        support_risk_by_attempt = {
            hmac_pseudonym("attempt", attempt_id, "aqc3-hmac-key"): risk
            for attempt_id, risk in raw_risks.items()
        }
        evidence, _, _, _, _ = evidence_for(
            dataset,
            arms=(
                PolicyArm.P1,
                PolicyArm.P2,
                PolicyArm.P3A,
                PolicyArm.P3B,
            ),
            support_risk_by_attempt=support_risk_by_attempt,
        )
        arms = {row["arm"] for row in evidence["safetyBenefitQuadrant"]}
        self.assertIn("P3b", arms)
        self.assertIn("P3a", arms)
        for row in evidence["forestPlot"]:
            self.assertEqual(row["arm"], "P3a")
            self.assertNotEqual(row["comparator"], "P3b")

    def test_evidence_package_is_deterministic(self):
        dataset = pseudonymized(build_dataset(four_student_history()))
        first, _, _, _, _ = evidence_for(dataset, seed=9)
        second, _, _, _, _ = evidence_for(dataset, seed=9)
        self.assertEqual(report_sha256(first), report_sha256(second))
        self.assertEqual(first, second)

    def test_rendered_report_contains_every_template_section(self):
        template_path = (
            Path(__file__).resolve().parents[1] / "reports" / "policy_comparison_template.md"
        )
        template_headings = [
            line.strip("# ").strip()
            for line in template_path.read_text(encoding="utf-8").splitlines()
            if line.startswith("## ")
        ]
        self.assertTrue(template_headings)
        dataset = pseudonymized(build_dataset(four_student_history()))
        evidence, metrics, run_manifest, _, _ = evidence_for(dataset)
        markdown = render_evidence_markdown(evidence, run_manifest, metrics)
        for heading in template_headings:
            self.assertIn(f"## {heading}", markdown, heading)

    def test_oscillation_counts_only_alternating_non_hold_directions(self):
        dataset = pseudonymized(build_dataset(four_student_history()))
        result = replayed(dataset, bank_catalog=full_bank_catalog())
        base = result.decisions_for(PolicyArm.P3A)[0]
        up = replace(
            base,
            source_attempt_sequence=1,
            direction=DecisionDirection.UP,
            decision_id="osc-up-1",
        )
        down = replace(
            base,
            source_attempt_sequence=2,
            direction=DecisionDirection.DOWN,
            decision_id="osc-down-1",
        )
        up_again = replace(
            base,
            source_attempt_sequence=3,
            direction=DecisionDirection.UP,
            decision_id="osc-up-2",
        )
        hold = replace(
            base,
            source_attempt_sequence=4,
            direction=DecisionDirection.HOLD,
            decision_id="osc-hold-1",
        )
        self.assertEqual(_oscillation_count((up, down, up_again)), 2)
        self.assertEqual(_oscillation_count((up, hold, up_again)), 0)
        self.assertEqual(_oscillation_count((up, down, hold, up_again)), 2)
        self.assertEqual(_oscillation_rate((up, down, up_again, hold)), round(2 / 3, 8))

    def test_calibration_band_with_sufficient_observations_is_reliable(self):
        dataset = pseudonymized(build_dataset(four_student_history()))
        baseline, _, _, _, _ = evidence_for(dataset)
        self.assertTrue(baseline["bktReliabilityCurve"])
        with patch.object(
            visualizations,
            "MIN_CALIBRATION_OBSERVATIONS",
            1,
        ):
            lowered, _, _, _, _ = evidence_for(dataset)
        self.assertTrue(
            any(band["status"] == "reliable" for band in lowered["bktReliabilityCurve"])
        )

    def test_cli_runner_emits_the_full_evidence_package(self) -> None:
        import evaluation.run_policy_comparison as runner

        dataset = pseudonymized(build_dataset(four_student_history()))
        with TemporaryDirectory() as csv_directory, TemporaryDirectory() as output_directory:
            export_real_attempts(
                dataset,
                csv_directory,
                release=approved_release(),
                pseudonymization_key="runner-test-key",
            )
            code = runner.main(
                [
                    "--attempts-csv",
                    str(Path(csv_directory) / "attempts.csv"),
                    "--responses-csv",
                    str(Path(csv_directory) / "responses.csv"),
                    "--provenance",
                    "real",
                    "--dataset-version",
                    "runner-v1",
                    "--output-dir",
                    output_directory,
                    "--claim-label",
                    "pipeline_demo_only",
                    "--policy-evaluation-manifest",
                    str(CONFIGS / "policy_evaluation_v1.yaml"),
                    "--adaptive-policy-config",
                    str(CONFIGS / "adaptive_policy_v1.yaml"),
                ]
            )
            self.assertEqual(0, code)
            output = Path(output_directory)
            for name in (
                "run_manifest.json",
                "machine_report.json",
                "policy_comparison_report.md",
                "evidence_package.json",
                "policy_comparison_evidence.md",
                "decision_audit.csv",
            ):
                self.assertTrue((output / name).exists(), name)
            evidence_text = (output / "policy_comparison_evidence.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Claim level", evidence_text)
            self.assertIn("Promotion-safety forest plot data", evidence_text)


if __name__ == "__main__":
    unittest.main()
