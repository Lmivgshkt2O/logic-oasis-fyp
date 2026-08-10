"""AQC-E6 CLI runner: matched historical outcome analysis (v1.3 frozen).

Verifies every frozen E1-E5 artifact plus the v1.3 statistical reporting
contract, computes policy-specific structural matching, attaches the frozen U7
outcome ONLY for tier-matched rows, applies the frozen student-clustered
bootstrap CI (>=10 independent learners) with sparse suppression, computes
EB4 and policy-independent BKT calibration, and writes a protected matched
outcomes CSV plus a deterministic E6 manifest.  No E7 work is started.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .matched_outcomes import (
    attach_outcomes,
    bkt_calibration,
    build_e6_manifest,
    eb4_metrics,
    matched_outcome_results_hash,
    matched_outcome_summary,
    policy_direction_outcome_summary,
    require_frozen_bootstrap_config,
    structural_matching,
    verify_e6_inputs,
    write_matched_outcomes_csv,
)
from .readiness_audit import load_attempts


def _load_decision_rows(path: str | Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(dict(row))
    return rows


def _file_sha256(path: str | Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_matched_outcomes(
    *,
    e3_attempts_path: str | Path,
    e3_manifest_path: str | Path,
    e4_manifest_path: str | Path,
    e5_decision_audit_path: str | Path,
    e5_manifest_path: str | Path,
    e2_catalog_path: str | Path,
    e2_manifest_path: str | Path,
    contract_path_v1_3: str | Path,
    contract_path_v1_2: str | Path,
    contract_path_v1_1: str | Path,
    contract_path_v1: str | Path,
    configs_dir: str | Path,
    processed_dir: str | Path,
) -> dict[str, object]:
    """Execute the v1.3 E6 outcome analysis and write protected artifacts."""
    verification = verify_e6_inputs(
        e3_attempts_path=e3_attempts_path,
        e3_manifest_path=e3_manifest_path,
        e4_manifest_path=e4_manifest_path,
        e5_decision_audit_path=e5_decision_audit_path,
        e5_manifest_path=e5_manifest_path,
        e2_catalog_path=e2_catalog_path,
        e2_manifest_path=e2_manifest_path,
        contract_path_v1_3=contract_path_v1_3,
        contract_path_v1_2=contract_path_v1_2,
        contract_path_v1_1=contract_path_v1_1,
        contract_path_v1=contract_path_v1,
        configs_dir=configs_dir,
    )
    bootstrap_config = require_frozen_bootstrap_config(
        _load_v13_contract(contract_path_v1_3)
    )
    attempts = load_attempts(e3_attempts_path)
    decisions = _load_decision_rows(e5_decision_audit_path)
    if len(decisions) != 6270:
        raise ValueError("E5 decision audit row count is not 6,270")
    rows = structural_matching(decisions, attempts)
    structural = matched_outcome_summary(rows)
    results = attach_outcomes(rows, attempts)
    outcome_summary = policy_direction_outcome_summary(results, bootstrap_config)
    eb4 = eb4_metrics(outcome_summary)
    shared_state_keys = sorted({str(d["externalStateKey"]) for d in decisions})
    if len(shared_state_keys) != 2090:
        raise ValueError("shared state key count is not 2,090")
    bkt_cal = bkt_calibration(attempts, shared_state_keys, bootstrap_config)
    matched_hash = matched_outcome_results_hash(results)

    policy_up = {
        "P1": 728,
        "P2": 691,
        "P3a": 1077,
    }
    policy_hold = {"P1": 1362, "P2": 1319, "P3a": 888}
    policy_down = {"P1": 0, "P2": 80, "P3a": 125}
    coverage = {
        policy: {
            "matchedOutcomeCoverage": structural[policy]["matchedOutcomeCoverage"],
            "matchedUpCoverage": _rate(
                structural[policy]["matchedByDirection"]["up"], policy_up[policy]
            ),
            "matchedHoldCoverage": _rate(
                structural[policy]["matchedByDirection"]["hold"], policy_hold[policy]
            ),
            "matchedDownCoverage": _rate(
                structural[policy]["matchedByDirection"]["down"], policy_down[policy]
            ),
        }
        for policy in ("P1", "P2", "P3a")
    }

    manifest = build_e6_manifest(
        verification=verification,
        structural_summary=structural,
        outcome_summary=outcome_summary,
        eb4=eb4,
        bkt_cal=bkt_cal,
        coverage=coverage,
        bootstrap_config=bootstrap_config,
        matched_outcomes_hash=matched_hash,
    )
    destination = Path(processed_dir)
    destination.mkdir(parents=True, exist_ok=True)
    outcomes_path = destination / "external_policy_matched_outcomes_v1.csv"
    write_matched_outcomes_csv(results, outcomes_path)
    manifest_path = destination / "e6_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "status": "completed",
        "claimLevel": "external_descriptive_replay",
        "matchedOutcomesSha256": matched_hash,
        "matchedOutcomesFileSha256": _file_sha256(outcomes_path),
        "e6ManifestSha256": _file_sha256(manifest_path),
        "structuralSummary": structural,
        "outcomeSummary": outcome_summary,
        "eb4": eb4,
        "bktCalibration": bkt_cal,
        "coverageMetrics": coverage,
        "bootstrapConfig": {
            "unit": "externalStudentKey",
            "resamples": bootstrap_config.iterations,
            "seed": bootstrap_config.seed,
            "confidenceLevel": bootstrap_config.confidence_level,
        },
        "p3bExecuted": False,
        "causalClaimAllowed": False,
    }


def _load_v13_contract(path: str | Path):
    from .external_policy_contract import (
        EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION,
        load_external_adaptive_contract,
    )

    return load_external_adaptive_contract(
        path, version=EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION
    )


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 8)


def main() -> None:
    parser = argparse.ArgumentParser(description="AQC-E6 matched historical outcomes (v1.3)")
    parser.add_argument("--e3-attempts", required=True, help="Protected E3 external_adaptive_attempts_v1.csv")
    parser.add_argument("--e3-manifest", required=True, help="Protected E3 e3_manifest.json")
    parser.add_argument("--e4-manifest", required=True, help="Protected E4 e4_readiness_manifest.json")
    parser.add_argument("--e5-decisions", required=True, help="Protected E5 external_policy_decisions_v1.csv")
    parser.add_argument("--e5-manifest", required=True, help="Protected E5 e5_manifest.json")
    parser.add_argument("--e2-catalog", required=True, help="Protected E2 problem-difficulty catalog CSV")
    parser.add_argument("--e2-manifest", required=True, help="Protected E2 calibration manifest JSON")
    parser.add_argument(
        "--contract-v1-3",
        default=str(
            Path(__file__).resolve().parents[1]
            / "adaptive"
            / "assistments_adaptive_contract_v1_3.yaml"
        ),
    )
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

    result = run_matched_outcomes(
        e3_attempts_path=args.e3_attempts,
        e3_manifest_path=args.e3_manifest,
        e4_manifest_path=args.e4_manifest,
        e5_decision_audit_path=args.e5_decisions,
        e5_manifest_path=args.e5_manifest,
        e2_catalog_path=args.e2_catalog,
        e2_manifest_path=args.e2_manifest,
        contract_path_v1_3=args.contract_v1_3,
        contract_path_v1_2=args.contract_v1_2,
        contract_path_v1_1=args.contract_v1_1,
        contract_path_v1=args.contract_v1,
        configs_dir=args.configs_dir,
        processed_dir=args.processed_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
