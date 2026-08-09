"""AQC-E6 CLI runner: matched historical outcome stage (structural + gated).

Verifies every frozen E1-E5 artifact, computes policy-specific structural
direct-next tier matching and censoring WITHOUT reading any outcome value, then
applies the frozen E6 outcome-rate gate.  Because no approved student-clustered
descriptive CI configuration is frozen for the external Stage-B path, the run
stops before computing/viewing any aggregate outcome rate and records the
exact blocker.  No E7 work is started.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .matched_outcomes import (
    E5_DECISION_AUDIT_HASH,
    E5_DECISION_AUDIT_FILE_HASH,
    E5_MANIFEST_HASH,
    OutcomeGateError,
    matched_outcome_summary,
    require_frozen_bootstrap_config,
    structural_matching,
    verify_e6_inputs,
)
from .readiness_audit import load_attempts


def _load_decision_rows(path: str | Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(dict(row))
    return rows


def run_matched_outcomes(
    *,
    e3_attempts_path: str | Path,
    e3_manifest_path: str | Path,
    e4_manifest_path: str | Path,
    e5_decision_audit_path: str | Path,
    e5_manifest_path: str | Path,
    e2_catalog_path: str | Path,
    e2_manifest_path: str | Path,
    contract_path_v1_2: str | Path,
    contract_path_v1_1: str | Path,
    contract_path_v1: str | Path,
    configs_dir: str | Path,
    processed_dir: str | Path,
) -> dict[str, object]:
    """Execute E6 structural matching, then gate aggregate outcome rates."""
    verification = verify_e6_inputs(
        e3_attempts_path=e3_attempts_path,
        e3_manifest_path=e3_manifest_path,
        e4_manifest_path=e4_manifest_path,
        e5_decision_audit_path=e5_decision_audit_path,
        e5_manifest_path=e5_manifest_path,
        e2_catalog_path=e2_catalog_path,
        e2_manifest_path=e2_manifest_path,
        contract_path_v1_2=contract_path_v1_2,
        contract_path_v1_1=contract_path_v1_1,
        contract_path_v1=contract_path_v1,
        configs_dir=configs_dir,
    )
    attempts = load_attempts(e3_attempts_path)
    decisions = _load_decision_rows(e5_decision_audit_path)
    if len(decisions) != 6270:
        raise OutcomeGateError("E5 decision audit row count is not 6,270")
    rows = structural_matching(decisions, attempts)
    summary = matched_outcome_summary(rows)

    try:
        require_frozen_bootstrap_config()
    except OutcomeGateError as error:
        diagnostic = {
            "status": "blocked_outcome_rate_gate",
            "blocker": str(error),
            "verification": verification,
            "structuralSummary": summary,
            "futureOutcomeValuesRead": False,
            "aggregateOutcomeRatesComputed": False,
            "claimLevel": "external_descriptive_replay",
            "containsRawIdentifiers": False,
            "productionPromotionAllowed": False,
            "p3bExecuted": False,
            "causalClaimAllowed": False,
        }
        destination = Path(processed_dir)
        destination.mkdir(parents=True, exist_ok=True)
        summary_path = destination / "e6_structural_diagnostic.json"
        summary_path.write_text(
            json.dumps(diagnostic, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        diagnostic["structuralDiagnosticPath"] = str(summary_path)
        raise OutcomeGateError(str(error)) from None

    raise OutcomeGateError("unreachable: E6 outcome analysis is gated")


def main() -> None:
    parser = argparse.ArgumentParser(description="AQC-E6 matched historical outcomes")
    parser.add_argument("--e3-attempts", required=True, help="Protected E3 external_adaptive_attempts_v1.csv")
    parser.add_argument("--e3-manifest", required=True, help="Protected E3 e3_manifest.json")
    parser.add_argument("--e4-manifest", required=True, help="Protected E4 e4_readiness_manifest.json")
    parser.add_argument("--e5-decisions", required=True, help="Protected E5 external_policy_decisions_v1.csv")
    parser.add_argument("--e5-manifest", required=True, help="Protected E5 e5_manifest.json")
    parser.add_argument("--e2-catalog", required=True, help="Protected E2 problem-difficulty catalog CSV")
    parser.add_argument("--e2-manifest", required=True, help="Protected E2 calibration manifest JSON")
    parser.add_argument(
        "--contract-v1-2",
        default=str(
            Path(__file__).resolve().parents[1]
            / "adaptive"
            / "assistments_adaptive_contract_v1_2.yaml"
        ),
    )
    parser.add_argument(
        "--contract-v1-1",
        default=str(
            Path(__file__).resolve().parents[1]
            / "adaptive"
            / "assistments_adaptive_contract_v1_1.yaml"
        ),
    )
    parser.add_argument(
        "--contract-v1",
        default=str(
            Path(__file__).resolve().parents[1]
            / "adaptive"
            / "assistments_adaptive_contract_v1.yaml"
        ),
    )
    parser.add_argument("--configs-dir", default=str(Path(__file__).resolve().parents[3] / "configs"))
    parser.add_argument("--processed-dir", required=True, help="Protected E6 output directory (outside Git)")
    args = parser.parse_args()

    try:
        result = run_matched_outcomes(
            e3_attempts_path=args.e3_attempts,
            e3_manifest_path=args.e3_manifest,
            e4_manifest_path=args.e4_manifest,
            e5_decision_audit_path=args.e5_decisions,
            e5_manifest_path=args.e5_manifest,
            e2_catalog_path=args.e2_catalog,
            e2_manifest_path=args.e2_manifest,
            contract_path_v1_2=args.contract_v1_2,
            contract_path_v1_1=args.contract_v1_1,
            contract_path_v1=args.contract_v1,
            configs_dir=args.configs_dir,
            processed_dir=args.processed_dir,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    except OutcomeGateError as error:
        summary_path = Path(args.processed_dir) / "e6_structural_diagnostic.json"
        if summary_path.exists():
            diagnostic = json.loads(summary_path.read_text(encoding="utf-8"))
            print(json.dumps(diagnostic, indent=2, sort_keys=True))
        raise SystemExit(f"AQC-E6 BLOCKED: {error}")


if __name__ == "__main__":
    main()
