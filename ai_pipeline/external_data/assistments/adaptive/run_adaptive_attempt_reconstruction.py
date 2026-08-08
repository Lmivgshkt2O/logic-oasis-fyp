"""AQC-E3 CLI runner: reconstruct protected 2022-2023 adaptive attempts.

The runner verifies every frozen E1/E2 artifact (v1.1 contract, v1 predecessor,
E2 catalog and manifest hashes, provenance, cohort, windows, learner overlap,
catalog gate, eligible skills, no native fields), then reconstructs exact-skill
attempts from the validated U7-v2 episodes.  Attempt proxy difficulty uses only
the frozen E2 catalog.  If any attempt mixes problems with and without a frozen
tier, the purity denominator is undefined by the contract and the run STOPS
with ``PurityDenominatorAmbiguity`` before writing final E3 outputs (only an
aggregate diagnostic summary is written).  No policy selector is called.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import median, quantiles

from .adaptive_attempts import (
    ATTEMPT_RECONSTRUCTION_VERSION,
    PurityDenominatorAmbiguity,
    build_attempt_records,
    detect_purity_denominator_ambiguity,
    load_frozen_problem_tiers,
    run_bkt_states,
    verify_stage_b_frozen,
)
from .schemas import EVALUATION_WINDOW_END, EVALUATION_WINDOW_START


BLOCKED_REASON = (
    "the frozen contract does not define whether uncalibrated problems belong "
    "in the attempt purity denominator"
)


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
            from datetime import datetime

            started = datetime.fromisoformat(row["episodeStartedAt"].replace("Z", "+00:00"))
            if not (EVALUATION_WINDOW_START <= started <= EVALUATION_WINDOW_END):
                continue
            episodes.append(dict(row))
    return episodes


def run_reconstruction(
    *,
    v2_attempts_path: str | Path,
    action_rows_path: str | Path,
    e2_catalog_path: str | Path,
    e2_manifest_path: str | Path,
    contract_path_v1_1: str | Path,
    contract_path_v1: str | Path,
    configs_dir: str | Path,
    processed_dir: str | Path,
    release_id: str,
) -> dict[str, object]:
    """Execute the E3 reconstruction; stops closed on the purity ambiguity."""
    verification = verify_stage_b_frozen(
        contract_path_v1_1=contract_path_v1_1,
        contract_path_v1=contract_path_v1,
        e2_catalog_path=e2_catalog_path,
        e2_manifest_path=e2_manifest_path,
        configs_dir=configs_dir,
    )
    episodes = _load_episodes(v2_attempts_path)
    tiers = load_frozen_problem_tiers(e2_catalog_path)
    mixed = detect_purity_denominator_ambiguity(episodes, tiers)

    eligible_skills = set(verification["eligibleSkills"])
    by_skill: Counter[str] = Counter(str(episode["externalSkillCode"]) for episode in episodes)
    in_eligible = sum(count for skill, count in by_skill.items() if skill in eligible_skills)
    outside_eligible = len(episodes) - in_eligible
    coverage: Counter[tuple[int, int]] = Counter()
    for episode in episodes:
        keys = [
            item
            for item in str(episode.get("gradedProblemKeys") or "").split("|")
            if item
        ]
        tiered = sum(1 for key in keys if key in tiers)
        coverage[(tiered, len(keys) - tiered)] += 1

    learners = {str(episode["externalStudentKey"]) for episode in episodes}
    skills = {str(episode["externalSkillCode"]) for episode in episodes}
    score_valid = len(episodes)  # outcome-valid episodes always carry a valid score

    if mixed:
        diagnostic = {
            "status": "blocked_purity_denominator_ambiguity",
            "blockedReason": BLOCKED_REASON,
            "reconstructionVersion": ATTEMPT_RECONSTRUCTION_VERSION,
            "verification": verification,
            "attemptCounts": {
                "outcomeValidGrade6Episodes": len(episodes),
                "uniqueLearners": len(learners),
                "uniqueExactSkills": len(skills),
                "attemptsInEligibleSkills": in_eligible,
                "attemptsOutsideEligibleSkills": outside_eligible,
                "scoreValidAttempts": score_valid,
                "mixedTierCoverageAttempts": mixed,
                "tierCoveragePatterns": {
                    f"{tiered}/{untiered}": count
                    for (tiered, untiered), count in sorted(coverage.items())
                },
            },
            "bktReplay": "not_executed_pending_purity_amendment",
            "policyDecisionsComputed": {"P1": 0, "P2": 0, "P3a": 0, "P3b": 0},
            "matchedOutcomes": 0,
            "policyAgreementRows": 0,
            "policyWinnerClaims": 0,
            "containsRawIdentifiers": False,
            "productionPromotionAllowed": False,
        }
        destination = Path(processed_dir)
        destination.mkdir(parents=True, exist_ok=True)
        summary_path = destination / "e3_diagnostic_summary.json"
        summary_path.write_text(
            json.dumps(diagnostic, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        diagnostic["diagnosticSummaryPath"] = str(summary_path)
        raise PurityDenominatorAmbiguity(BLOCKED_REASON) from None

    # Not reachable while the ambiguity is live; kept for the post-amendment run.
    bkt_states = run_bkt_states(action_rows_path, episodes)
    records, summary = build_attempt_records(
        episodes,
        tiers=tiers,
        eligible_skills=frozenset(eligible_skills),
        bkt_states=bkt_states,
        release_id=release_id,
    )
    from .adaptive_attempts import write_attempts_csv

    destination = Path(processed_dir)
    destination.mkdir(parents=True, exist_ok=True)
    attempts_path = destination / "external_adaptive_attempts_v1.csv"
    write_attempts_csv(records, attempts_path)
    return {
        "status": "completed",
        "attemptsPath": str(attempts_path),
        "attemptCount": len(records),
        "summary": dict(sorted(summary.items())),
        "policyDecisionsComputed": {"P1": 0, "P2": 0, "P3a": 0, "P3b": 0},
        "matchedOutcomes": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AQC-E3 adaptive attempt reconstruction")
    parser.add_argument("--v2-attempts", required=True, help="Protected U7-v2 external_skill_attempts_v2.csv")
    parser.add_argument("--action-rows", required=True, help="Protected J1 external_action_rows_v1.csv")
    parser.add_argument("--e2-catalog", required=True, help="Protected E2 problem-difficulty catalog CSV")
    parser.add_argument("--e2-manifest", required=True, help="Protected E2 calibration manifest JSON")
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

    try:
        result = run_reconstruction(
            v2_attempts_path=args.v2_attempts,
            action_rows_path=args.action_rows,
            e2_catalog_path=args.e2_catalog,
            e2_manifest_path=args.e2_manifest,
            contract_path_v1_1=args.contract_v1_1,
            contract_path_v1=args.contract_v1,
            configs_dir=args.configs_dir,
            processed_dir=args.processed_dir,
            release_id=args.release_id,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    except PurityDenominatorAmbiguity as error:
        summary_path = Path(args.processed_dir) / "e3_diagnostic_summary.json"
        if summary_path.exists():
            diagnostic = json.loads(summary_path.read_text(encoding="utf-8"))
            print(json.dumps(diagnostic, indent=2, sort_keys=True))
        raise SystemExit(f"AQC-E3 BLOCKED: {error}")


if __name__ == "__main__":
    main()
