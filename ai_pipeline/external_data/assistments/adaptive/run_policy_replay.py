"""AQC-E5 CLI runner: real external P1/P2/P3a one-step policy replay.

Replays the frozen selectors on the exact 2,090 shared policy-ready states
from AQC-E4, writes a protected learner-level decision audit and a
deterministic E5 manifest, and reports descriptive direction/agreement
metrics.  No future outcome value is loaded, P3b/XGBoost is never executed,
and no policy selection decision is made.
"""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from .controlled_mechanics import ControlledMechanicsConfig
from .policy_replay import (
    E4_MANIFEST_HASH,
    CLAIM_LEVEL,
    SHARED_STATE_COUNT,
    ReplayError,
    agreement_metrics,
    build_e5_manifest,
    decision_rows_hash,
    direction_counts,
    eb_metrics,
    load_shared_states,
    reason_counts,
    replay_policies,
    reversal_signal_metrics,
    shared_policy_state_hash,
    tier_specific_directions,
    write_decision_rows_csv,
    write_manifest,
)
from .readiness_audit import verify_frozen_lineage


def _file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_policy_replay(
    *,
    e3_attempts_path: str | Path,
    e3_manifest_path: str | Path,
    e2_catalog_path: str | Path,
    e2_manifest_path: str | Path,
    e4_manifest_path: str | Path,
    contract_path_v1_2: str | Path,
    contract_path_v1_1: str | Path,
    contract_path_v1: str | Path,
    configs_dir: str | Path,
    processed_dir: str | Path,
) -> dict[str, object]:
    """Execute the E5 replay and write protected decision audit + manifest."""
    verification = verify_frozen_lineage(
        contract_path_v1_2=contract_path_v1_2,
        contract_path_v1_1=contract_path_v1_1,
        contract_path_v1=contract_path_v1,
        e2_catalog_path=e2_catalog_path,
        e2_manifest_path=e2_manifest_path,
        e3_attempts_path=e3_attempts_path,
        e3_manifest_path=e3_manifest_path,
        configs_dir=configs_dir,
    )
    e4_hash = _file_sha256(e4_manifest_path)
    if e4_hash != E4_MANIFEST_HASH:
        raise ReplayError("E4 readiness manifest hash changed since the E4 freeze")
    e4_manifest = json.loads(Path(e4_manifest_path).read_text(encoding="utf-8"))
    if int(e4_manifest["funnel"]["sharedPolicyReady"]["attempts"]) != SHARED_STATE_COUNT:
        raise ReplayError("E4 shared policy-ready count is not 2,090")

    config = ControlledMechanicsConfig(
        adaptive_policy_path=Path(configs_dir) / "adaptive_policy_v1.yaml",
        policy_manifest_path=Path(configs_dir) / "policy_evaluation_v1.yaml",
    )
    states = load_shared_states(
        e3_attempts_path,
        frozenset(verification["eligibleSkills"]),
    )
    state_hash = shared_policy_state_hash(states)
    rows, parity = replay_policies(states, config=config)

    direction = direction_counts(rows)
    tier_directions = tier_specific_directions(rows)
    reasons = reason_counts(rows)
    agreement = agreement_metrics(rows)
    eb = eb_metrics(rows)
    reversal = reversal_signal_metrics(rows)
    audit_hash = decision_rows_hash(rows)

    policy_bundle = {
        "adaptivePolicySha256": _file_sha256(config.adaptive_policy_path),
        "policyEvaluationSha256": _file_sha256(config.policy_manifest_path),
    }
    verification = dict(verification)
    verification["policyEvaluationSha256"] = policy_bundle["policyEvaluationSha256"]

    manifest = build_e5_manifest(
        verification=verification,
        shared_state_hash=state_hash,
        direction=direction,
        tier_directions=tier_directions,
        reasons=reasons,
        agreement=agreement,
        eb=eb,
        reversal=reversal,
        decision_audit_hash=audit_hash,
    )
    destination = Path(processed_dir)
    destination.mkdir(parents=True, exist_ok=True)
    audit_path = destination / "external_policy_decisions_v1.csv"
    write_decision_rows_csv(rows, audit_path)
    manifest_path = destination / "e5_manifest.json"
    write_manifest(manifest, manifest_path)

    return {
        "status": "completed",
        "claimLevel": CLAIM_LEVEL,
        "sharedPolicyStateHash": state_hash,
        "rowParity": parity,
        "decisionAuditPath": str(audit_path),
        "decisionAuditSha256": audit_hash,
        "manifestPath": str(manifest_path),
        "manifestSha256": _file_sha256(manifest_path),
        "policyBundleHashes": policy_bundle,
        "directionCountsByPolicy": direction,
        "tierSpecificDirectionCounts": tier_directions,
        "reasonCountsByPolicy": reasons,
        "agreementCounts": agreement,
        "ebMetrics": eb,
        "reversalSignalCounts": reversal,
        "p3bExecuted": False,
        "futureOutcomeValuesUsed": False,
        "policySelectionMade": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AQC-E5 real external policy replay")
    parser.add_argument("--e3-attempts", required=True, help="Protected E3 external_adaptive_attempts_v1.csv")
    parser.add_argument("--e3-manifest", required=True, help="Protected E3 e3_manifest.json")
    parser.add_argument("--e2-catalog", required=True, help="Protected E2 problem-difficulty catalog CSV")
    parser.add_argument("--e2-manifest", required=True, help="Protected E2 calibration manifest JSON")
    parser.add_argument("--e4-manifest", required=True, help="Protected E4 e4_readiness_manifest.json")
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
    parser.add_argument("--processed-dir", required=True, help="Protected E5 output directory (outside Git)")
    args = parser.parse_args()

    result = run_policy_replay(
        e3_attempts_path=args.e3_attempts,
        e3_manifest_path=args.e3_manifest,
        e2_catalog_path=args.e2_catalog,
        e2_manifest_path=args.e2_manifest,
        e4_manifest_path=args.e4_manifest,
        contract_path_v1_2=args.contract_v1_2,
        contract_path_v1_1=args.contract_v1_1,
        contract_path_v1=args.contract_v1,
        configs_dir=args.configs_dir,
        processed_dir=args.processed_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
