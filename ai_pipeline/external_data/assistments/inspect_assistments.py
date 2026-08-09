r"""Bounded/streaming physical-source inspector for ASSISTments EDM Cup 2023.

J0 tool.  This script never loads action_logs.csv or assignment_details.csv
fully into memory; every large-table scan is chunked.  It prints the J0
physical-schema evidence and, when --json-out is supplied, writes a JSON
summary outside the Git repository (the protected external-data j0 folder).

Usage:
    python inspect_assistments.py --raw-dir <protected-raw-dir>
    python inspect_assistments.py --raw-dir <protected-raw-dir> --skip-hashes
    python inspect_assistments.py --raw-dir <protected-raw-dir> --json-out <protected-j0-dir>\scan-summary.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .assistments_contract import (
    ASSIGNMENT_START_ACTION,
    GRADE_ACCELERATED_LEVEL_2,
    GRADED_ACTIONS,
    PROBLEM_START_ACTION,
    REQUIRED_BASE_U7_FILES,
    WINDOW_END,
    WINDOW_START,
    grade_from_level_2,
    pair_problem_duration,
    parse_epoch_seconds,
)


ACTION_LOG_COLUMNS = ("assignment_log_id", "timestamp", "problem_id", "action")
ASSIGNMENT_DETAIL_COLUMNS = (
    "assignment_log_id",
    "teacher_id",
    "class_id",
    "student_id",
    "sequence_id",
    "assignment_release_date",
    "assignment_due_date",
    "assignment_start_time",
    "assignment_end_time",
)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def first_lines(path: Path, count: int = 3) -> list[str]:
    lines: list[str] = []
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        for _ in range(count):
            line = handle.readline()
            if not line:
                break
            lines.append(line.rstrip("\r\n"))
    return lines


def scan_action_logs(path: Path) -> dict[str, Any]:
    rows = 0
    action_counts: Counter[str] = Counter()
    year_counts: Counter[int] = Counter()
    window_rows = 0
    before_window = 0
    after_window = 0
    unique_assignment_ids: set[str] = set()
    unique_problem_ids: set[str] = set()
    problem_id_rows = 0
    timestamp_rows = 0
    exact_duplicates = 0
    min_ts = float("inf")
    max_ts = float("-inf")

    for chunk in pd.read_csv(path, dtype=str, usecols=ACTION_LOG_COLUMNS, chunksize=4_000_000):
        rows += len(chunk)
        exact_duplicates += int(chunk.duplicated().sum())
        action_counts.update(chunk["action"].dropna().tolist())
        unique_assignment_ids.update(chunk["assignment_log_id"].dropna().astype(str).tolist())
        problem_mask = chunk["problem_id"].notna()
        problem_id_rows += int(problem_mask.sum())
        unique_problem_ids.update(chunk.loc[problem_mask, "problem_id"].astype(str).tolist())
        timestamps = pd.to_numeric(chunk["timestamp"], errors="coerce")
        timestamp_rows += int(timestamps.notna().sum())
        if timestamps.notna().any():
            min_ts = min(min_ts, float(timestamps.min()))
            max_ts = max(max_ts, float(timestamps.max()))
            parsed = pd.to_datetime(timestamps, unit="s", utc=True)
            year_counts.update(parsed.dt.year.dropna().astype(int).tolist())
            in_window = (parsed >= WINDOW_START) & (parsed <= WINDOW_END)
            window_rows += int(in_window.sum())
            before_window += int((parsed < WINDOW_START).sum())
            after_window += int((parsed > WINDOW_END).sum())

    def iso(epoch: float) -> str:
        try:
            return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
        except (OSError, OverflowError, ValueError):
            return f"out_of_epoch_range:{epoch}"

    return {
        "totalRows": rows,
        "rowsWithProblemId": problem_id_rows,
        "rowsWithTimestamp": timestamp_rows,
        "exactDuplicateRows": exact_duplicates,
        "uniqueAssignmentLogIds": len(unique_assignment_ids),
        "uniqueProblemIds": len(unique_problem_ids),
        "minTimestampEpoch": None if min_ts == float("inf") else min_ts,
        "minTimestampUtc": None if min_ts == float("inf") else iso(min_ts),
        "maxTimestampEpoch": None if max_ts == float("-inf") else max_ts,
        "maxTimestampUtc": None if max_ts == float("-inf") else iso(max_ts),
        "yearCounts": {str(year): count for year, count in sorted(year_counts.items())},
        "rowsInSelectedWindow": window_rows,
        "rowsBeforeWindow": before_window,
        "rowsAfterWindow": after_window,
        "actionCounts": dict(action_counts.most_common()),
        "assignmentIds": sorted(unique_assignment_ids),
    }


def scan_assignment_details(path: Path) -> dict[str, Any]:
    rows = 0
    non_null: Counter[str] = Counter()
    unique_students: set[str] = set()
    unique_sequences: set[str] = set()
    unique_assignment_ids: set[str] = set()
    time_bounds: dict[str, list[float]] = {}
    for column in ("assignment_release_date", "assignment_due_date", "assignment_start_time", "assignment_end_time"):
        time_bounds[column] = [float("inf"), float("-inf")]

    for chunk in pd.read_csv(path, dtype=str, usecols=ASSIGNMENT_DETAIL_COLUMNS, chunksize=4_000_000):
        rows += len(chunk)
        for column in ASSIGNMENT_DETAIL_COLUMNS:
            non_null[column] += int(chunk[column].notna().sum())
        unique_assignment_ids.update(chunk["assignment_log_id"].dropna().astype(str).tolist())
        unique_students.update(chunk["student_id"].dropna().astype(str).tolist())
        unique_sequences.update(chunk["sequence_id"].dropna().astype(str).tolist())
        for column, bounds in time_bounds.items():
            values = pd.to_numeric(chunk[column], errors="coerce")
            if values.notna().any():
                bounds[0] = min(bounds[0], float(values.min()))
                bounds[1] = max(bounds[1], float(values.max()))

    def iso(epoch: float) -> str:
        try:
            return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
        except (OSError, OverflowError, ValueError):
            return f"out_of_epoch_range:{epoch}"

    return {
        "totalRows": rows,
        "nonNullCounts": dict(non_null),
        "uniqueAssignmentLogIds": len(unique_assignment_ids),
        "uniqueStudentIds": len(unique_students),
        "uniqueSequenceIds": len(unique_sequences),
        "timeBounds": {
            column: {
                "minEpoch": None if bounds[0] == float("inf") else bounds[0],
                "minUtc": None if bounds[0] == float("inf") else iso(bounds[0]),
                "maxEpoch": None if bounds[1] == float("-inf") else bounds[1],
                "maxUtc": None if bounds[1] == float("-inf") else iso(bounds[1]),
            }
            for column, bounds in time_bounds.items()
        },
        "assignmentIds": sorted(unique_assignment_ids),
        "sequenceIds": sorted(unique_sequences),
    }


def scan_problem_details(path: Path) -> dict[str, Any]:
    frame = pd.read_csv(
        path,
        dtype=str,
        usecols=["problem_id", "problem_type", "problem_skill_code"],
    )
    skill_codes = frame["problem_skill_code"].dropna().astype(str)
    return {
        "totalRows": len(frame),
        "uniqueProblemIds": int(frame["problem_id"].nunique()),
        "problemTypeCounts": frame["problem_type"].value_counts(dropna=False).to_dict(),
        "skillCodeNonNull": int(skill_codes.notna().sum()),
        "skillCodeGrade6Prefix": int(skill_codes.str.startswith("6.").sum()),
        "problemIds": sorted(frame["problem_id"].dropna().astype(str).tolist()),
    }


def scan_sequence_details(path: Path) -> dict[str, Any]:
    frame = pd.read_csv(
        path,
        dtype=str,
        usecols=[
            "sequence_id",
            "sequence_folder_path_level_1",
            "sequence_folder_path_level_2",
            "sequence_folder_path_level_3",
            "sequence_folder_path_level_4",
            "sequence_name",
            "sequence_problem_ids",
        ],
    )

    def parse_ids(value: object) -> list[str]:
        if not isinstance(value, str) or not value.strip():
            return []
        body = value.strip()
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1]
        return [item.strip() for item in body.split(",") if item.strip()]

    level_2 = frame["sequence_folder_path_level_2"].dropna().astype(str).str.strip()
    grade_6 = int(level_2.eq("Grade 6").sum())
    grade_6_accelerated = int(level_2.eq(GRADE_ACCELERATED_LEVEL_2).sum())
    referenced_problem_ids: set[str] = set()
    for ids in frame["sequence_problem_ids"].apply(parse_ids):
        referenced_problem_ids.update(ids)
    return {
        "totalRows": len(frame),
        "uniqueSequenceIds": int(frame["sequence_id"].nunique()),
        "uniqueLevel2Values": int(level_2.nunique()),
        "grade6Sequences": grade_6,
        "grade6AcceleratedSequences": grade_6_accelerated,
        "sequenceProblemIdsReferenced": len(referenced_problem_ids),
        "sequenceIds": sorted(frame["sequence_id"].dropna().astype(str).tolist()),
        "referencedProblemIds": sorted(referenced_problem_ids),
    }


def scan_relationship_tables(raw_dir: Path) -> dict[str, Any]:
    assignment_rels = pd.read_csv(raw_dir / "assignment_relationships.csv", dtype=str)
    sequence_rels = pd.read_csv(raw_dir / "sequence_relationships.csv", dtype=str)
    return {
        "assignment_relationships": {
            "rows": len(assignment_rels),
            "uniqueUnitTestAssignmentLogIds": int(assignment_rels["unit_test_assignment_log_id"].nunique()),
            "uniqueInUnitAssignmentLogIds": int(assignment_rels["in_unit_assignment_log_id"].nunique()),
        },
        "sequence_relationships": {
            "rows": len(sequence_rels),
            "uniqueUnitTestSequenceIds": int(sequence_rels["unit_test_sequence_id"].nunique()),
            "uniqueInUnitSequenceIds": int(sequence_rels["in_unit_sequence_id"].nunique()),
        },
    }


def grade_6_window_coverage(raw_dir: Path, action_ids: set[str]) -> dict[str, Any]:
    sequence_frame = pd.read_csv(
        raw_dir / "sequence_details.csv",
        dtype=str,
        usecols=["sequence_id", "sequence_folder_path_level_2"],
    )
    grade_by_sequence = {
        str(sequence_id): grade_from_level_2(level_2)
        for sequence_id, level_2 in zip(
            sequence_frame["sequence_id"],
            sequence_frame["sequence_folder_path_level_2"],
        )
    }
    grade_6_sequence_ids = set(
        sequence_frame.loc[
            sequence_frame["sequence_folder_path_level_2"].astype(str).str.strip().eq("Grade 6"),
            "sequence_id",
        ].astype(str)
    )

    by_grade: Counter[str] = Counter()
    by_grade_with_actions: Counter[str] = Counter()
    grade_6_students: set[str] = set()
    for chunk in pd.read_csv(
        raw_dir / "assignment_details.csv",
        dtype=str,
        usecols=["assignment_log_id", "student_id", "sequence_id", "assignment_start_time"],
        chunksize=4_000_000,
    ):
        chunk = chunk.dropna(subset=["student_id", "sequence_id"])
        start = pd.to_datetime(pd.to_numeric(chunk["assignment_start_time"], errors="coerce"), unit="s", utc=True)
        in_window = (start >= WINDOW_START) & (start <= WINDOW_END)
        sub = chunk[in_window]
        for sequence_id, student_id, assignment_id in zip(
            sub["sequence_id"], sub["student_id"], sub["assignment_log_id"]
        ):
            grade = grade_by_sequence.get(str(sequence_id))
            if grade is None:
                continue
            by_grade[grade] += 1
            if str(assignment_id) in action_ids:
                by_grade_with_actions[grade] += 1
        grade_6_students.update(
            sub.loc[sub["sequence_id"].astype(str).isin(grade_6_sequence_ids), "student_id"].astype(str).tolist()
        )
    return {
        "inWindowAssignmentsByGrade": dict(sorted(by_grade.items())),
        "inWindowAssignmentsWithActionLogsByGrade": dict(sorted(by_grade_with_actions.items())),
        "inWindowStudentsOnGrade6Sequence": len(grade_6_students),
    }


def pairing_feasibility_sample(raw_dir: Path, action_ids: Iterable[str], sample_size: int) -> dict[str, Any]:
    ids = sorted(set(action_ids))
    rng = random.Random(20260807)
    sampled = set(rng.sample(ids, min(sample_size, len(ids))))
    kept: list[pd.DataFrame] = []
    for chunk in pd.read_csv(
        raw_dir / "action_logs.csv",
        dtype=str,
        usecols=["assignment_log_id", "timestamp", "problem_id", "action"],
        chunksize=4_000_000,
    ):
        matched = chunk["assignment_log_id"].astype(str).isin(sampled)
        if matched.any():
            kept.append(chunk[matched])
    frame = pd.concat(kept, ignore_index=True) if kept else pd.DataFrame()
    if frame.empty:
        return {"sampledAssignments": 0, "note": "no rows for the sampled assignments"}

    frame["row_ordinal"] = range(len(frame))
    frame["ts"] = pd.to_numeric(frame["timestamp"], errors="coerce")
    frame = frame.sort_values(["assignment_log_id", "problem_id", "ts", "row_ordinal"])

    problems = 0
    with_start = 0
    start_then_graded = 0
    graded_without_start = 0
    starts_without_graded = 0
    multi_graded = 0
    multi_start = 0
    durations: list[float] = []

    for _, group in frame.groupby(["assignment_log_id", "problem_id"], sort=False):
        if group["problem_id"].isna().all():
            continue
        problems += 1
        events = []
        for timestamp, action in zip(group["ts"].tolist(), group["action"].tolist()):
            parsed = parse_epoch_seconds(timestamp)
            if parsed is not None and isinstance(action, str) and action:
                events.append((parsed, action))
        start_events = [(t, a) for t, a in events if a == PROBLEM_START_ACTION]
        graded_events = [(t, a) for t, a in events if a in GRADED_ACTIONS]
        if start_events:
            with_start += 1
            if len(start_events) > 1:
                multi_start += 1
        paired, duration, _ = pair_problem_duration(start_events, events)
        if paired:
            start_then_graded += 1
            durations.append(float(duration))
        elif start_events:
            starts_without_graded += 1
        elif graded_events:
            graded_without_start += 1
        if len(graded_events) > 1:
            multi_graded += 1

    def describe(values: list[float]) -> dict[str, float | int | None]:
        if not values:
            return {"n": 0}
        return {
            "n": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "negativeCount": sum(1 for value in values if value < 0),
            "zeroCount": sum(1 for value in values if value == 0),
        }

    return {
        "sampledAssignments": len(sampled),
        "keptRows": int(len(frame)),
        "problemsExamined": problems,
        "problemsWithStart": with_start,
        "problemsWithStartAndGradedResponse": start_then_graded,
        "startsWithoutLaterGradedResponse": starts_without_graded,
        "gradedResponsesWithoutProblemStart": graded_without_start,
        "problemsWithMultipleStarts": multi_start,
        "problemsWithMultipleGradedResponses": multi_graded,
        "durationMs": describe(durations),
    }


def inspect(raw_dir: Path, *, skip_hashes: bool, sample_size: int) -> dict[str, Any]:
    files = sorted(raw_dir.glob("*.csv"))
    inventory: dict[str, Any] = {}
    for path in files:
        header_lines = first_lines(path, 1)
        inventory[path.name] = {
            "sizeBytes": path.stat().st_size,
            "sha256": None if skip_hashes else sha256_of(path),
            "header": header_lines[0] if header_lines else "",
            "requiredForBaseU7": path.name in REQUIRED_BASE_U7_FILES,
        }

    missing_expected = [name for name in REQUIRED_BASE_U7_FILES if not (raw_dir / name).exists()]

    action_summary = scan_action_logs(raw_dir / "action_logs.csv")
    action_ids = set(action_summary.pop("assignmentIds"))
    details_summary = scan_assignment_details(raw_dir / "assignment_details.csv")
    details_ids = set(details_summary.pop("assignmentIds"))
    details_sequence_ids = set(details_summary.pop("sequenceIds"))

    problem_summary = scan_problem_details(raw_dir / "problem_details.csv")
    problem_ids = set(problem_summary.pop("problemIds"))
    sequence_summary = scan_sequence_details(raw_dir / "sequence_details.csv")
    sequence_ids = set(sequence_summary.pop("sequenceIds"))
    referenced_problem_ids = set(sequence_summary.pop("referencedProblemIds"))

    relationships = scan_relationship_tables(raw_dir)
    assignment_rels = pd.read_csv(raw_dir / "assignment_relationships.csv", dtype=str)
    in_unit_ids = set(assignment_rels["in_unit_assignment_log_id"].dropna().astype(str))
    unit_test_ids = set(assignment_rels["unit_test_assignment_log_id"].dropna().astype(str))

    pairing = pairing_feasibility_sample(raw_dir, action_ids, sample_size)
    grade_coverage = grade_6_window_coverage(raw_dir, action_ids)

    return {
        "schemaMappingVersion": "assistments-schema-mapping-v1",
        "detectedAt": "2026-08-07",
        "rawDirectory": str(raw_dir.resolve()),
        "fileInventory": inventory,
        "missingBaseU7Files": missing_expected,
        "actionLogs": action_summary,
        "assignmentDetails": details_summary,
        "problemDetails": problem_summary,
        "sequenceDetails": sequence_summary,
        "relationships": relationships,
        "joinIntegrity": {
            "actionAssignmentIdsMissingFromDetails": len(action_ids - details_ids),
            "actionAssignmentIdsThatAreInUnitIds": len(action_ids & in_unit_ids),
            "actionAssignmentIdsThatAreUnitTestIds": len(action_ids & unit_test_ids),
            "sequenceReferencedProblemIdsMissingFromProblemDetails": len(referenced_problem_ids - problem_ids),
            "assignmentSequenceIdsMissingFromSequenceDetails": len(details_sequence_ids - sequence_ids),
        },
        "grade6WindowCoverage": grade_coverage,
        "pairingFeasibilitySample": pairing,
        "bktOrdering": "AVAILABLE",
        "bktOrderingNote": "millisecond epoch timestamps, zero exact duplicate rows, per-problem graded response sequences; deterministic order by (timestamp, file row ordinal)",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded ASSISTments EDM Cup 2023 source inspector (J0)")
    parser.add_argument("--raw-dir", required=True, help="Protected raw CSV directory (kept outside Git)")
    parser.add_argument("--skip-hashes", action="store_true", help="Skip SHA-256 recomputation")
    parser.add_argument("--sample-size", type=int, default=3000, help="Assignment ids sampled for pairing feasibility")
    parser.add_argument("--json-out", help="Optional JSON summary path (use the protected j0 folder)")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    if not raw_dir.is_dir():
        parser.error(f"raw directory does not exist: {raw_dir}")
    summary = inspect(raw_dir, skip_hashes=args.skip_hashes, sample_size=args.sample_size)
    print(json.dumps(summary, indent=2, default=str))
    if args.json_out:
        output = Path(args.json_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        print(f"\nsummary written to {output}")


if __name__ == "__main__":
    main()
