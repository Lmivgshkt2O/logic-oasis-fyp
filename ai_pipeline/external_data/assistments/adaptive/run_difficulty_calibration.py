"""AQC-E2 CLI runner: build the protected problem-difficulty calibration evidence.

The runner verifies the frozen E1 contract before touching any raw data,
streams the protected ASSISTments CSVs, excludes evaluation-cohort learners,
aggregates first-graded (learner, problem) outcomes, and writes a protected
problem-level catalog plus a deterministic manifest.  No policy selector is
imported or called, and no within-skill tier assignment is applied to real
data (blocked by the E1 tertile-boundary ambiguity recorded in the E2 report).
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from statistics import median, quantiles

from ..adapter import (
    load_problem_skill_map,
    load_sequence_metadata,
    source_file_hashes,
)
from .difficulty_calibration import (
    CALIBRATION_METHOD_VERSION,
    CATALOG_VERSION,
    CalibrationError,
    aggregate_problem_records,
    build_calibration_manifest,
    collect_grade_six_learner_sets,
    file_sha256,
    split_overlapping_learners,
    stream_calibration_graded_pairs,
    write_catalog_csv,
    write_manifest,
)
from .external_policy_contract import (
    load_external_adaptive_contract,
    verify_frozen_policy_hashes,
    verify_shared_aqc_constants,
)
from .proxy_tiers import (
    SKILL_CATALOG_MINIMUM_PER_TIER,
    SKILL_CATALOG_MINIMUM_PROBLEMS,
)
from .schemas import (
    CALIBRATION_WINDOW_END,
    CALIBRATION_WINDOW_START,
    EVALUATION_WINDOW_END,
    EVALUATION_WINDOW_START,
    EXTERNAL_PROVENANCE,
    MINIMUM_CALIBRATION_LEARNERS,
    PROXY_DIFFICULTY_VALUES,
)


TIER_ASSIGNMENT_STATUS_BLOCKED = "blocked_contract_ambiguity_non_divisible_tertiles"


def _distribution(values: list[float]) -> dict[str, float]:
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


def run_calibration(
    raw_dir: str | Path,
    processed_dir: str | Path,
    *,
    pseudonym_key: bytes | str,
    contract_path: str | Path,
    configs_dir: str | Path,
    release_id: str,
    source_hashes: dict[str, str] | None = None,
) -> dict[str, object]:
    """Execute the E2 calibration pass; returns aggregate results (no policy)."""
    raw = Path(raw_dir)
    processed = Path(processed_dir)
    contract = load_external_adaptive_contract(contract_path)
    verify_frozen_policy_hashes(contract, configs_dir)
    verify_shared_aqc_constants(contract)
    if contract.provenance != EXTERNAL_PROVENANCE:
        raise CalibrationError("E1 provenance verification failed")
    if not contract.windows_are_disjoint:
        raise CalibrationError("E1 windows are not disjoint")
    if contract.minimum_calibration_learners != MINIMUM_CALIBRATION_LEARNERS:
        raise CalibrationError("E1 minimum calibration learners changed")
    if contract.proxy_difficulty_values != PROXY_DIFFICULTY_VALUES:
        raise CalibrationError("E1 proxy tier vocabulary changed")
    if (
        contract.skill_catalog_minimum_calibrated_problems
        != SKILL_CATALOG_MINIMUM_PROBLEMS
        or contract.skill_catalog_minimum_per_tier != SKILL_CATALOG_MINIMUM_PER_TIER
    ):
        raise CalibrationError("E1 skill catalog gate changed")

    required = ("action_logs.csv", "assignment_details.csv", "problem_details.csv", "sequence_details.csv")
    for filename in required:
        if not (raw / filename).exists():
            raise FileNotFoundError(f"required source file is missing: {filename}")
    processed.mkdir(parents=True, exist_ok=True)

    sequence_metadata = load_sequence_metadata(raw / "sequence_details.csv")
    problem_skills = load_problem_skill_map(raw / "problem_details.csv")
    sets = collect_grade_six_learner_sets(raw / "assignment_details.csv", sequence_metadata)
    calibration_assignments = dict(sets["calibrationAssignments"])
    calibration_learners = set(sets["calibrationLearners"])
    evaluation_learners = set(sets["evaluationLearners"])
    assignment_counters = Counter(sets["counters"])

    excluded, final_calibration_learners = split_overlapping_learners(
        calibration_learners, evaluation_learners
    )
    allowed_assignments = {
        assignment_id: student_id
        for assignment_id, student_id in calibration_assignments.items()
        if student_id in final_calibration_learners
    }

    pairs, action_counters = stream_calibration_graded_pairs(
        raw / "action_logs.csv",
        allowed_assignments=allowed_assignments,
        excluded_learners=excluded,
        problem_skills=problem_skills,
    )
    records, aggregation_counters = aggregate_problem_records(
        pairs,
        problem_skills,
        release_id=release_id,
        pseudonym_key=pseudonym_key,
    )

    catalog_path = processed / "assistments_problem_difficulty_proxy_v1.csv"
    write_catalog_csv(records, catalog_path)
    catalog_hash = file_sha256(catalog_path)

    null_skill_excluded = aggregation_counters["problems_null_skill_excluded"]
    null_skill_distinct = action_counters["problems_null_skill_distinct"]
    with_skill = aggregation_counters["problems_observed_with_skill"]
    calibrated = aggregation_counters["problems_calibrated"]
    insufficient = aggregation_counters["problems_insufficient"]
    skills_observed = len({record.source_skill_code for record in records})
    skills_with_calibrated = len(
        {
            record.source_skill_code
            for record in records
            if record.calibration_status == "calibrated"
        }
    )

    p_correct_values = [record.smoothed_correct_probability for record in records]
    difficulty_values = [record.difficulty_score for record in records]
    learner_counts = [record.calibration_learner_count for record in records]
    calibrated_records = [record for record in records if record.calibration_status == "calibrated"]
    calibrated_p_correct = [record.smoothed_correct_probability for record in calibrated_records]

    manifest = build_calibration_manifest(
        contract_version=contract.contract_version,
        contract_hash=contract.contract_sha256,
        dataset_release_id=release_id,
        source_release_hashes=source_hashes or source_file_hashes(raw),
        calibration_start=CALIBRATION_WINDOW_START,
        calibration_end=CALIBRATION_WINDOW_END,
        evaluation_start=EVALUATION_WINDOW_START,
        evaluation_end=EVALUATION_WINDOW_END,
        evaluation_learners_excluded_from_calibration=bool(excluded),
        calibration_evaluation_learner_overlap_count=len(excluded),
        possible_pre_2022_grade_six_learners=len(calibration_learners),
        final_calibration_learner_count=len(final_calibration_learners),
        smoothing_rule="p_correct = (correct_responses + 1) / (total_graded_responses + 2)",
        minimum_calibration_learners=MINIMUM_CALIBRATION_LEARNERS,
        tiering_scope="exact_sourceSkillCode",
        tier_ordering_tie_rule="p_correct descending, then externalProblemKey ascending",
        tier_algorithm_version=CALIBRATION_METHOD_VERSION,
        tier_assignment_status=TIER_ASSIGNMENT_STATUS_BLOCKED,
        minimum_problems_per_skill=SKILL_CATALOG_MINIMUM_PROBLEMS,
        minimum_problems_per_tier=SKILL_CATALOG_MINIMUM_PER_TIER,
        problem_counts={
            "problemsObserved": null_skill_distinct + with_skill,
            "problemsExactSkillEligible": with_skill,
            "problemsCalibrated": calibrated,
            "problemsInsufficientEvidence": insufficient,
            "problemsNullSkillExcluded": null_skill_distinct,
        },
        skill_counts={
            "skillsObserved": skills_observed,
            "skillsWithCalibratedProblems": skills_with_calibrated,
            "skillsFullThreeTierEligible": 0,
            "skillsInsufficientCatalog": 0,
        },
        tier_counts={
            "proxy_easy": 0,
            "proxy_moderate": 0,
            "proxy_hard": 0,
        },
        catalog_sha256=catalog_hash,
    )
    manifest_path = processed / "e2_calibration_manifest.json"
    write_manifest(manifest, manifest_path)

    summary = {
        "catalog": str(catalog_path),
        "manifest": str(manifest_path),
        "catalogSha256": catalog_hash,
        "contractVersion": contract.contract_version,
        "contractHash": contract.contract_sha256,
        "assignmentCounters": dict(sorted(assignment_counters.items())),
        "actionCounters": dict(sorted(action_counters.items())),
        "aggregationCounters": dict(sorted(aggregation_counters.items())),
        "calibrationLearners": {
            "possiblePre2022GradeSix": len(calibration_learners),
            "excludedEvaluationCohort": len(excluded),
            "finalCalibration": len(final_calibration_learners),
            "overlapAfterExclusion": len(
                final_calibration_learners & evaluation_learners
            ),
        },
        "problems": {
            "observed": null_skill_distinct + with_skill,
            "exactSkillEligible": with_skill,
            "calibrated": calibrated,
            "insufficientEvidence": insufficient,
        },
        "skills": {
            "observed": skills_observed,
            "withCalibratedProblems": skills_with_calibrated,
        },
        "distributions": {
            "calibrationLearnersPerProblem": _distribution(learner_counts),
            "pCorrectAllEligible": _distribution(p_correct_values),
            "difficultyScoreAllEligible": _distribution(difficulty_values),
            "pCorrectCalibratedOnly": _distribution(calibrated_p_correct),
        },
        "tierAssignmentStatus": TIER_ASSIGNMENT_STATUS_BLOCKED,
        "tierCounts": {"proxy_easy": 0, "proxy_moderate": 0, "proxy_hard": 0},
        "policyDecisionsComputed": {"P1": 0, "P2": 0, "P3a": 0},
        "matchedOutcomes": 0,
        "policyComparisonReports": 0,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="AQC-E2 problem-difficulty calibration")
    parser.add_argument("--raw-dir", required=True, help="Protected raw CSV directory (outside Git)")
    parser.add_argument("--processed-dir", required=True, help="Protected E2 output directory (outside Git)")
    parser.add_argument(
        "--contract-path",
        default=str(
            Path(__file__).resolve().parents[1]
            / "adaptive"
            / "assistments_adaptive_contract_v1.yaml"
        ),
    )
    parser.add_argument(
        "--configs-dir",
        default=str(Path(__file__).resolve().parents[3] / "configs"),
    )
    parser.add_argument("--release-id", default="assistments-edm-cup-2023-release-v1")
    parser.add_argument(
        "--pseudonym-key",
        default=os.environ.get("LOGIC_OASIS_ASSISTMENTS_PSEUDONYM_KEY"),
        help="Project-local HMAC key; prefer the environment variable.",
    )
    parser.add_argument(
        "--source-hashes",
        help="Optional JSON with source file SHA-256 values (e.g. the protected j0 scan summary)",
    )
    args = parser.parse_args()
    if not args.pseudonym_key:
        parser.error("pseudonym key is required (--pseudonym-key or LOGIC_OASIS_ASSISTMENTS_PSEUDONYM_KEY)")
    source_hashes = None
    if args.source_hashes:
        with Path(args.source_hashes).open(encoding="utf-8") as handle:
            summary = json.load(handle)
        source_hashes = {
            name: info["sha256"]
            for name, info in summary.get("fileInventory", {}).items()
            if info.get("sha256")
        }
    result = run_calibration(
        args.raw_dir,
        args.processed_dir,
        pseudonym_key=args.pseudonym_key,
        contract_path=args.contract_path,
        configs_dir=args.configs_dir,
        release_id=args.release_id,
        source_hashes=source_hashes,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
