"""AQC-2 CLI runner: deterministic offline policy comparison (Stage B).

Example:
    py -3.11 -m evaluation.run_policy_comparison \\
        --attempts-csv attempts.csv --responses-csv responses.csv \\
        --provenance real --dataset-version real_v1_2026-08 \\
        --output-dir outputs/policy_comparison
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from logic_oasis_ai.adaptive_policy import load_adaptive_policy_config
from logic_oasis_ai.policy_evaluation import (
    PolicyArm,
    load_policy_evaluation_manifest,
)
from logic_oasis_ai.prediction_contract import PredictionContract
from logic_oasis_ai.sources.csv_source import load_csv_files

from .manifest import (
    OutcomeWindow,
    build_run_manifest,
    load_run_manifest,
    write_run_manifest,
)
from .metrics import compute_metrics
from .outcomes import attach_outcomes
from .replay import derive_bank_catalog, load_bank_catalog_csv, replay_policies
from .reporting import build_markdown_report, build_machine_report, render_machine_json
from .report_templates import render_decision_audit_csv, render_evidence_markdown
from .visualizations import build_evidence_package


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage B offline policy comparison")
    parser.add_argument("--attempts-csv", required=True)
    parser.add_argument("--responses-csv", required=True)
    parser.add_argument("--bank-catalog-csv", default=None)
    parser.add_argument("--run-manifest", default=None, help="Frozen run manifest JSON")
    parser.add_argument(
        "--policy-evaluation-manifest",
        default="configs/policy_evaluation_v1.yaml",
    )
    parser.add_argument(
        "--adaptive-policy-config",
        default="configs/adaptive_policy_v1.yaml",
    )
    parser.add_argument("--provenance", default="real", choices=("real", "emulator_verified", "synthetic_test"))
    parser.add_argument("--dataset-version", default=None)
    parser.add_argument("--hmac-namespace", default="policy-evaluation-replay-v1")
    parser.add_argument("--random-seed", type=int, default=20260722)
    parser.add_argument("--max-later-attempts", type=int, default=5)
    parser.add_argument("--max-window-days", type=int, default=90)
    parser.add_argument(
        "--claim-label",
        default="pipeline_demo_only",
        choices=("pipeline_demo_only", "descriptive_replay_only"),
    )
    parser.add_argument("--support-risk-csv", default=None)
    parser.add_argument("--output-dir", default="outputs/policy_comparison")
    parser.add_argument("--allow-emulator", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv or ())
    dataset = load_csv_files(
        args.attempts_csv,
        args.responses_csv,
        provenance=args.provenance,
        allow_emulator_records=args.allow_emulator,
    )
    adaptive_policy = load_adaptive_policy_config(args.adaptive_policy_config)
    policy_manifest = load_policy_evaluation_manifest(
        args.policy_evaluation_manifest,
        adaptive_policy=adaptive_policy,
    )
    if args.run_manifest:
        run_manifest = load_run_manifest(args.run_manifest)
    else:
        if not args.dataset_version:
            raise SystemExit("--dataset-version is required when no --run-manifest is supplied")
        run_manifest = build_run_manifest(
            dataset=dataset,
            dataset_version=args.dataset_version,
            adaptive_policy_sha256=adaptive_policy.source_sha256,
            policy_evaluation_sha256=policy_manifest.source_sha256,
            outcome_window=OutcomeWindow(
                max_later_attempts=args.max_later_attempts,
                max_calendar_duration_days=args.max_window_days,
            ),
            random_seed=args.random_seed,
            claim_label=args.claim_label,
            hmac_namespace=args.hmac_namespace,
        )

    bank_catalog = (
        load_bank_catalog_csv(args.bank_catalog_csv)
        if args.bank_catalog_csv
        else derive_bank_catalog(dataset)
    )
    support_risk_by_attempt = _load_support_risks(args.support_risk_csv)
    arms = (
        (PolicyArm.P1, PolicyArm.P2, PolicyArm.P3A)
        if support_risk_by_attempt is None
        else (PolicyArm.P1, PolicyArm.P2, PolicyArm.P3A, PolicyArm.P3B)
    )
    replay_result = replay_policies(
        dataset,
        run_manifest=run_manifest,
        adaptive_policy=adaptive_policy,
        policy_manifest=policy_manifest,
        bank_catalog=bank_catalog,
        arms=arms,
        support_risk_by_attempt=support_risk_by_attempt,
    )
    outcome_result = attach_outcomes(
        replay_result,
        dataset,
        contract=PredictionContract(),
        outcome_window=run_manifest.outcome_window,
    )
    metrics = compute_metrics(
        replay_result,
        outcome_result,
        random_seed=run_manifest.random_seed,
        claim_label=run_manifest.claim_label,
    )

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "run_manifest.json"
    machine_path = output / "machine_report.json"
    markdown_path = output / "policy_comparison_report.md"
    evidence_path = output / "evidence_package.json"
    evidence_markdown_path = output / "policy_comparison_evidence.md"
    audit_csv_path = output / "decision_audit.csv"
    write_run_manifest(run_manifest, manifest_path)
    machine_report = build_machine_report(
        run_manifest,
        metrics,
        attempt_count=len(dataset.attempts),
    )
    machine_path.write_text(render_machine_json(machine_report), encoding="utf-8")
    markdown_path.write_text(
        build_markdown_report(
            run_manifest,
            metrics,
            attempt_count=len(dataset.attempts),
        ),
        encoding="utf-8",
    )
    evidence_package = build_evidence_package(
        replay_result,
        outcome_result,
        metrics,
        run_manifest,
        random_seed=run_manifest.random_seed,
    )
    evidence_path.write_text(
        render_machine_json(evidence_package), encoding="utf-8"
    )
    evidence_markdown_path.write_text(
        render_evidence_markdown(evidence_package, run_manifest, metrics),
        encoding="utf-8",
    )
    audit_csv_path.write_text(
        render_decision_audit_csv(evidence_package), encoding="utf-8"
    )
    print(f"claimLevel={metrics.claim_label}")
    print(f"manifest={manifest_path}")
    print(f"machineReport={machine_path}")
    print(f"markdownReport={markdown_path}")
    print(f"evidencePackage={evidence_path}")
    print(f"evidenceMarkdown={evidence_markdown_path}")
    print(f"decisionAuditCsv={audit_csv_path}")
    return 0


def _load_support_risks(path: str | None) -> dict[str, float] | None:
    if not path:
        return None
    import csv

    result: dict[str, float] = {}
    with Path(path).open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            attempt_key = row.get("attemptKey")
            raw_risk = row.get("supportRisk")
            if not attempt_key or raw_risk is None:
                raise SystemExit("support-risk CSV requires attemptKey and supportRisk")
            risk = float(raw_risk)
            if not 0.0 <= risk <= 1.0:
                raise SystemExit(f"supportRisk must be between zero and one: {attempt_key}")
            result[attempt_key] = risk
    return result


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
