"""J2-v2 CLI: reconstruct learner+skill episodes and problem outcomes.

Protected outputs (never committed): ``external_skill_attempts_v2.csv``,
``external_skill_problem_outcomes_v2.csv``, and
``j2_v2_reconstruction_summary.json``.  The v1 protected release is never
touched.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Iterable

from .j2_contract import J2_CONTRACT_VERSION_V2, load_j2_contract, validate_j2_contract_v2
from .reconstruct_attempts import read_action_rows
from .skill_episodes import (
    EPISODE_FIELDS,
    PROBLEM_OUTCOME_FIELDS,
    EpisodeRecord,
    build_skill_episodes,
)


def write_episodes_csv(records: Iterable[EpisodeRecord], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EPISODE_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_csv_row())


def write_outcomes_csv(outcomes: Iterable[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PROBLEM_OUTCOME_FIELDS)
        writer.writeheader()
        for outcome in outcomes:
            writer.writerow(outcome)


def main() -> None:
    parser = argparse.ArgumentParser(description="J2-v2 skill-episode reconstruction")
    parser.add_argument("--action-rows", required=True, help="Protected J1 external_action_rows CSV")
    parser.add_argument("--processed-dir", required=True, help="Protected v2 output directory")
    parser.add_argument("--contract", default=None)
    parser.add_argument("--cohort-grades", default="6")
    parser.add_argument("--release-id", default="assistments-edm-cup-2023-release-v1")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parents[2]
    contract_path = Path(args.contract) if args.contract else repo_dir / "external_data" / "assistments" / "assistments_j2_contract_v2.yaml"
    contract = validate_j2_contract_v2(load_j2_contract(contract_path))
    if contract["contractVersion"] != J2_CONTRACT_VERSION_V2:
        raise ValueError("reconstruction requires the v2 contract")

    processed = Path(args.processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    episodes_path = processed / "external_skill_attempts_v2.csv"
    outcomes_path = processed / "external_skill_problem_outcomes_v2.csv"
    summary_path = processed / "j2_v2_reconstruction_summary.json"
    if any(path.exists() for path in (episodes_path, outcomes_path, summary_path)) and not args.force:
        raise FileExistsError("protected v2 outputs are immutable; use --force")

    cohort_grades = tuple(grade.strip() for grade in args.cohort_grades.split(",") if grade.strip())
    frame = read_action_rows(args.action_rows)
    episodes, outcomes, summary = build_skill_episodes(
        frame,
        cohort_grades=cohort_grades,
        release_id=args.release_id,
    )
    summary["contractVersion"] = contract["contractVersion"]
    summary["cohort"] = ",".join(cohort_grades)
    summary["episodes"] = len(episodes)
    summary["outcomeValidEpisodes"] = sum(1 for e in episodes if e.outcomeValid)
    summary["featureValidEpisodes"] = sum(1 for e in episodes if e.featureValid)
    summary["uniqueStudents"] = len({e.externalStudentKey for e in episodes})
    summary["uniqueSkills"] = len({e.externalSkillCode for e in episodes})

    staging = Path(mkdtemp(prefix=".v2-staging-", dir=processed))
    try:
        staged_episodes = staging / episodes_path.name
        staged_outcomes = staging / outcomes_path.name
        write_episodes_csv(episodes, staged_episodes)
        write_outcomes_csv(outcomes, staged_outcomes)
        staged_episodes.replace(episodes_path)
        staged_outcomes.replace(outcomes_path)
    finally:
        rmtree(staging, ignore_errors=True)

    summary_path.write_text(json.dumps(dict(sorted(summary.items())), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(dict(sorted(summary.items())), indent=2, sort_keys=True))
    print(f"episodes: {episodes_path}")
    print(f"outcomes: {outcomes_path}")


if __name__ == "__main__":
    main()

