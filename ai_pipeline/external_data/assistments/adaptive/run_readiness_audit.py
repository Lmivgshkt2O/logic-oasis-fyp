"""AQC-E4 CLI runner: Stage-B readiness / sufficiency / coverage audit.

E4 audits the frozen E1-E3 lineage and decides whether P1/P2/P3a replay is
structurally justified.  No policy selector is called, no outcome VALUE is used
in the decision, and no E5/E6/E7 work is started.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from logic_oasis_ai.adaptive_policy import load_adaptive_policy_config

from .readiness_audit import (
    ReadinessError,
    adjacent_tier_availability,
    bkt_readiness,
    boundary_opportunity_counts,
    build_e4_manifest,
    censoring_table,
    direct_next_audit,
    fresh_problem_summary,
    load_attempts,
    policy_ready_funnel,
    potential_tier_matches,
    reversal_history_summary,
    tier_stats,
    verify_frozen_lineage,
    write_manifest,
)


READY = "READY_FOR_EXTERNAL_POLICY_REPLAY"
NOT_READY = "NOT_READY_FOR_EXTERNAL_POLICY_REPLAY"


def _decide(
    funnel: dict[str, object],
    tier_stats_: dict[str, object],
    bkt: dict[str, object],
    adjacent: dict[str, object],
    next_counts: dict[str, object],
    match_counts: dict[str, object],
) -> tuple[str, str, str, list[str]]:
    """Structural decision without any policy selector or outcome value."""
    components: list[str] = []
    shared = funnel["sharedPolicyReady"]
    shared_attempts = int(shared["attempts"])
    shared_learners = int(shared["learners"])
    ready_skills = int(funnel["readyUniqueSkills"])
    tiers_present = [
        tier for tier in ("proxy_easy", "proxy_moderate", "proxy_hard")
        if int(tier_stats_[tier]["attempts"]) > 0
    ]

    policy_pass = True
    if shared_attempts < 1:
        policy_pass = False
        components.append("no shared policy-ready states")
    if shared_learners < 2:
        policy_pass = False
        components.append("fewer than two independent learners")
    if len(tiers_present) != 3:
        policy_pass = False
        components.append(f"proxy tiers missing: {sorted(set(('proxy_easy','proxy_moderate','proxy_hard')) - set(tiers_present))}")
    if ready_skills < 2:
        policy_pass = False
        components.append("fewer than two exact eligible skills")
    if int(bkt["bktValidAttempts"]) != shared_attempts:
        policy_pass = False
        components.append("BKT is not valid for the shared population")
    if int(adjacent["missingAdjacentTierAttempts"]) != 0:
        policy_pass = False
        components.append("adjacent-tier catalog availability is incomplete")
    if policy_pass:
        components.append(
            f"shared policy-ready population: {shared_attempts} attempts / "
            f"{shared_learners} learners / {ready_skills} skills / all three tiers"
        )
    policy_readiness = "PASS" if policy_pass else "FAIL"

    valid_next = int(next_counts["valid"])
    match_types = [
        label
        for label in ("potential_up_tier_match", "potential_hold_tier_match", "potential_down_tier_match")
        if int(match_counts[label]["pairs"]) > 0
    ]
    match_learners = sum(int(match_counts[label]["learners"]) for label in match_counts)
    non_adjacent = int(match_counts["non_adjacent_observed_transition"]["pairs"])
    if valid_next == 0 or match_learners == 0:
        matched_readiness = "insufficient"
        components.append("no valid direct-next tier-bearing history for tier matching")
    elif len(match_types) == 3 and match_learners >= 2:
        matched_readiness = "adequate"
        components.append(
            f"potential tier matches present for all three directions "
            f"({valid_next} valid next pairs; {non_adjacent} non-adjacent)"
        )
    else:
        matched_readiness = "limited"
        components.append(
            f"potential tier matches partial ({len(match_types)}/3 directions; "
            f"{valid_next} valid next pairs)"
        )

    if policy_pass and matched_readiness != "insufficient":
        overall = READY
    else:
        overall = NOT_READY
        if not policy_pass:
            components.append("policy replay readiness failed")
        if matched_readiness == "insufficient":
            components.append("matched-outcome readiness is structurally insufficient")
    return policy_readiness, matched_readiness, overall, components


def run_readiness_audit(
    *,
    e3_attempts_path: str | Path,
    e3_manifest_path: str | Path,
    e2_catalog_path: str | Path,
    e2_manifest_path: str | Path,
    contract_path_v1_2: str | Path,
    contract_path_v1_1: str | Path,
    contract_path_v1: str | Path,
    configs_dir: str | Path,
    processed_dir: str | Path,
) -> dict[str, object]:
    """Execute the E4 audit and write the protected readiness manifest."""
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
    attempts = load_attempts(e3_attempts_path)
    eligible_skills = frozenset(verification["eligibleSkills"])
    ready, funnel = policy_ready_funnel(attempts, eligible_skills)
    tier_stats_ = tier_stats(ready)
    adjacent = adjacent_tier_availability(ready, eligible_skills)
    boundary = boundary_opportunity_counts(ready)
    adaptive_policy = load_adaptive_policy_config(Path(configs_dir) / "adaptive_policy_v1.yaml")
    bkt = bkt_readiness(
        ready,
        move_up_minimum_evidence=adaptive_policy.thresholds.minimum_evidence_for_move_up,
        hard_minimum_evidence=adaptive_policy.thresholds.minimum_evidence_for_hard,
    )
    reversal = reversal_history_summary(ready)
    fresh = fresh_problem_summary(ready)
    pairs, next_counts = direct_next_audit(ready, attempts)
    ready_by_key = {a.external_attempt_key: a for a in ready}
    match_counts = potential_tier_matches(pairs, ready_by_key)
    censoring = censoring_table(attempts, ready, eligible_skills, pairs)
    policy_readiness, matched_readiness, overall, components = _decide(
        funnel, tier_stats_, bkt, adjacent, next_counts, match_counts
    )

    manifest = build_e4_manifest(
        verification=verification,
        funnel=funnel,
        tier_stats_=tier_stats_,
        adjacent=adjacent,
        boundary=boundary,
        bkt=bkt,
        reversal=reversal,
        fresh=fresh,
        next_counts=next_counts,
        match_counts=match_counts,
        censoring=censoring,
        policy_replay_readiness=policy_readiness,
        matched_outcome_readiness=matched_readiness,
        overall_decision=overall,
        decision_components=components,
    )
    destination = Path(processed_dir)
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / "e4_readiness_manifest.json"
    write_manifest(manifest, manifest_path)
    from .readiness_audit import _file_sha256

    return {
        "status": "completed",
        "manifestPath": str(manifest_path),
        "manifestSha256": _file_sha256(manifest_path),
        "funnel": funnel,
        "tierStats": tier_stats_,
        "adjacentTierAvailability": adjacent,
        "boundaryOpportunityCounts": boundary,
        "bktReadiness": bkt,
        "reversalHistory": reversal,
        "freshProblem": fresh,
        "directNextEpisodeCounts": next_counts,
        "potentialTierMatchCounts": match_counts,
        "censoringCounts": censoring,
        "policyReplayReadiness": policy_readiness,
        "matchedOutcomeReadiness": matched_readiness,
        "overallDecision": overall,
        "decisionComponents": components,
        "policyDecisionsComputed": {"P1": 0, "P2": 0, "P3a": 0, "P3b": 0},
        "policyAgreementRows": 0,
        "policySpecificMatchedOutcomes": 0,
        "policySpecificPerformanceMetrics": 0,
        "superiorityClaims": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AQC-E4 Stage-B readiness audit")
    parser.add_argument("--e3-attempts", required=True, help="Protected E3 external_adaptive_attempts_v1.csv")
    parser.add_argument("--e3-manifest", required=True, help="Protected E3 e3_manifest.json")
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
    parser.add_argument("--processed-dir", required=True, help="Protected E4 output directory (outside Git)")
    args = parser.parse_args()

    result = run_readiness_audit(
        e3_attempts_path=args.e3_attempts,
        e3_manifest_path=args.e3_manifest,
        e2_catalog_path=args.e2_catalog,
        e2_manifest_path=args.e2_manifest,
        contract_path_v1_2=args.contract_v1_2,
        contract_path_v1_1=args.contract_v1_1,
        contract_path_v1=args.contract_v1,
        configs_dir=args.configs_dir,
        processed_dir=args.processed_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
