"""AQC-E3 CLI runner: reconstruct and finalize protected 2022-2023 attempts.

The runner verifies every frozen E1/E2 artifact (v1.2 contract, v1.1 and v1
predecessors, E2 catalog and manifest hashes, provenance, cohort, windows,
learner overlap, catalog gate, eligible skills, no native fields), then
reconstructs exact-skill attempts from the validated U7-v2 episodes with the
frozen v1.2 purity rule (proxyDifficultyPurity = dominant_tier_count /
valid_problem_count over ALL valid graded problems).  It writes a protected
attempts CSV plus a deterministic E3 manifest.  No policy selector is called
and no matched outcome is attached.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from statistics import median, quantiles

from .adaptive_attempts import (
    build_attempt_records,
    build_e3_manifest,
    file_sha256,
    load_frozen_problem_tiers,
    run_bkt_states,
    verify_stage_b_frozen,
    write_attempts_csv,
    write_manifest,
)
from .schemas import EVALUATION_WINDOW_END, EVALUATION_WINDOW_START


def _distribution(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "q25": None, "median": None, "q75": None, "max": None}
    ordered = sorted(values)
    quartiles = quantiles(ordered, n=4)
    return {
        "min": ordered[0],
        "q25": quartiles[0],
        "median": median(ordered),
        "q75": quartiles[2],
        "max": ordered[-1],
    }


def _load_episodes(path: str | Path) -> list[dict[str, object]]:
    import csv

    episodes: list[dict[str, object]] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("cohortEligible") != "True" or row.get("outcomeValid") != "True":
                continue
            started = datetime.fromisoformat(row["episodeStartedAt"].replace("Z", "+00:00"))
            if not (EVALUATION_WINDOW_START <= started <= EVALUATION_WINDOW_END):
                continue
            episodes.append(dict(row))
    return episodes


def _distribution_bands(values: list[int], bands: tuple[tuple[str, int, int], ...]) -> dict[str, int]:
    counts = {label: 0 for label, _low, _high in bands}
    for value in values:
        for label, low, high in bands:
            if low <= value <= high:
                counts[label] += 1
                break
    return counts


def run_reconstruction(
    *,
    v2_attempts_path: str | Path,
    action_rows_path: str | Path,
    e2_catalog_path: str | Path,
    e2_manifest_path: str | Path,
    contract_path_v1_2: str | Path,
    contract_path_v1_1: str | Path,
    contract_path_v1: str | Path,
    configs_dir: str | Path,
    processed_dir: str | Path,
    release_id: str,
) -> dict[str, object]:
    """Execute the E3 reconstruction under the v1.2 purity rule."""
    verification = verify_stage_b_frozen(
        contract_path_v1_2=contract_path_v1_2,
        contract_path_v1_1=contract_path_v1_1,
        contract_path_v1=contract_path_v1,
        e2_catalog_path=e2_catalog_path,
        e2_manifest_path=e2_manifest_path,
        configs_dir=configs_dir,
    )
    episodes = _load_episodes(v2_attempts_path)
    tiers = load_frozen_problem_tiers(e2_catalog_path)
    eligible_skills = frozenset(verification["eligibleSkills"])
    bkt_states = run_bkt_states(action_rows_path, episodes)
    records, summary = build_attempt_records(
        episodes,
        tiers=tiers,
        eligible_skills=eligible_skills,
        bkt_states=bkt_states,
        release_id=release_id,
    )

    destination = Path(processed_dir)
    destination.mkdir(parents=True, exist_ok=True)
    attempts_path = destination / "external_adaptive_attempts_v1.csv"
    write_attempts_csv(records, attempts_path)
    attempts_hash = file_sha256(attempts_path)

    in_eligible = sum(1 for record in records if record.skill_proxy_status == "eligible")
    outside = len(records) - in_eligible
    tier_valid = sum(1 for record in records if record.attempt.current_proxy_difficulty is not None)
    zero_tier = sum(1 for record in records if record.attempt.proxy_difficulty_purity == 0.0)
    no_current_tier = len(records) - tier_valid
    previous_tier = sum(1 for record in records if record.attempt.previous_observed_proxy_difficulty is not None)
    cold_history = len(records) - previous_tier
    chronology_ambiguous = sum(1 for record in records if record.chronology_ambiguous)
    tier_counts = {
        "proxy_easy": sum(
            1
            for record in records
            if record.attempt.current_proxy_difficulty is not None
            and record.attempt.current_proxy_difficulty.value == "proxy_easy"
        ),
        "proxy_moderate": sum(
            1
            for record in records
            if record.attempt.current_proxy_difficulty is not None
            and record.attempt.current_proxy_difficulty.value == "proxy_moderate"
        ),
        "proxy_hard": sum(
            1
            for record in records
            if record.attempt.current_proxy_difficulty is not None
            and record.attempt.current_proxy_difficulty.value == "proxy_hard"
        ),
    }
    purity_values = [
        record.attempt.proxy_difficulty_purity
        for record in records
        if record.attempt.proxy_difficulty_purity is not None
    ]
    evidence_values = [record.attempt.bkt_evidence_count for record in records]
    fresh_values = [
        record.attempt.fresh_problem_fraction
        for record in records
        if record.attempt.fresh_problem_fraction is not None
    ]

    counts = {
        "reconstructedAttempts": len(records),
        "uniqueLearners": len({record.attempt.external_student_key for record in records}),
        "uniqueExactSkills": len({record.attempt.source_skill_code for record in records}),
        "attemptsInEligibleSkills": in_eligible,
        "attemptsOutsideEligibleSkills": outside,
        "scoreValidAttempts": len(records),
        "bktValidAttempts": len(records),
        "proxyTierValidAttempts": tier_valid,
        "attemptsWithoutCurrentTier": no_current_tier,
        "mixedSubThresholdAttempts": no_current_tier - zero_tier,
        "zeroTierAttempts": zero_tier,
        "attemptsWithPreviousObservedTier": previous_tier,
        "coldHistoryAttempts": cold_history,
        "chronologyAmbiguousAttempts": chronology_ambiguous,
    }
    manifest = build_e3_manifest(
        contract_version=str(verification["contractVersionV1_2"]),
        contract_hash=str(verification["contractHashV1_2"]),
        predecessor_contract_version=str(verification["predecessorContractVersionV1_1"]),
        predecessor_contract_hash=str(verification["predecessorContractHashV1_1"]),
        amendment_reason="attempt_proxy_difficulty_purity_denominator_clarification",
        purity_denominator_rule=verification["purityDenominatorRule"],
        difficulty_catalog_version="assistments_problem_difficulty_proxy_v1",
        difficulty_catalog_hash=str(verification["e2CatalogHash"]),
        dataset_release_id=release_id,
        source_release_hashes=verification["sourceReleaseHashes"],
        evaluation_start=EVALUATION_WINDOW_START,
        evaluation_end=EVALUATION_WINDOW_END,
        eligible_skill_count=int(verification["eligibleSkillCount"]),
        eligible_skill_codes_hash=str(verification["eligibleSkillCodesHash"]),
        bkt_version=str(records[0].attempt.bkt_version) if records else "bkt-v1",
        attempt_purity_threshold=Fraction(2, 3),
        problem_set_fingerprint_version="external-problem-set-fingerprint-v1",
        fresh_problem_rule=(
            "freshProblemFraction = count(current valid problem keys not seen in "
            "strictly prior attempts for the same learner + exact skill) / "
            "count(current valid problem keys)"
        ),
        chronology_rule=(
            "externalAttemptSequence per learner + exact skill by episodeStartedAt "
            "then externalAssignmentKey; unresolved ties fail closed as chronology_ambiguous"
        ),
        counts=counts,
        tier_counts=tier_counts,
        attempts_sha256=attempts_hash,
    )
    manifest_path = destination / "e3_manifest.json"
    write_manifest(manifest, manifest_path)

    return {
        "status": "completed",
        "attemptsPath": str(attempts_path),
        "manifestPath": str(manifest_path),
        "attemptsSha256": attempts_hash,
        "manifestSha256": file_sha256(manifest_path),
        "counts": counts,
        "tierCounts": tier_counts,
        "distributions": {
            "proxyDifficultyPurity": _distribution(purity_values),
            "bktEvidenceCount": _distribution([float(value) for value in evidence_values]),
            "bktEvidenceBands": _distribution_bands(
                evidence_values,
                (("1-4", 1, 4), ("5-9", 5, 9), ("10-19", 10, 19), ("20+", 20, 10**9)),
            ),
            "freshProblemFraction": _distribution(fresh_values),
        },
        "reconstructionSummary": dict(sorted(summary.items())),
        "policyDecisionsComputed": {"P1": 0, "P2": 0, "P3a": 0, "P3b": 0},
        "policyAgreementRows": 0,
        "matchedOutcomes": 0,
        "policyWinnerClaims": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AQC-E3 adaptive attempt reconstruction")
    parser.add_argument("--v2-attempts", required=True, help="Protected U7-v2 external_skill_attempts_v2.csv")
    parser.add_argument("--action-rows", required=True, help="Protected J1 external_action_rows_v1.csv")
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
    parser.add_argument("--processed-dir", required=True, help="Protected E3 output directory (outside Git)")
    parser.add_argument("--release-id", default="assistments-edm-cup-2023-release-v1")
    args = parser.parse_args()

    result = run_reconstruction(
        v2_attempts_path=args.v2_attempts,
        action_rows_path=args.action_rows,
        e2_catalog_path=args.e2_catalog,
        e2_manifest_path=args.e2_manifest,
        contract_path_v1_2=args.contract_v1_2,
        contract_path_v1_1=args.contract_v1_1,
        contract_path_v1=args.contract_v1,
        configs_dir=args.configs_dir,
        processed_dir=args.processed_dir,
        release_id=args.release_id,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
