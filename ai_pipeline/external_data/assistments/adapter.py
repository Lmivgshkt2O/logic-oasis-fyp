"""J1 streaming adapter: normalize eligible 2022-2023 ASSISTments action rows.

The adapter reads only the protected raw CSVs, applies the strict window
filter, joins the minimum audit/grouping metadata, pseudonymizes every source
identity into a project-local stable key, and writes an
``ExternalActionRow`` CSV plus a manifest into the protected processed
directory.  Raw and normalized learner-level files never enter Git.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Any, Iterable, Mapping

import pandas as pd

from .assistments_contract import (
    PROVENANCE,
    SOURCE_DATASET,
    WINDOW_END,
    WINDOW_START,
    grade_from_level_2,
    in_selected_window,
    parse_epoch_seconds,
)
from .manifest import MANIFEST_SCHEMA_VERSION, build_manifest, write_manifest
from .schemas import (
    EXTERNAL_ACTION_ROW_FIELDS,
    EXTERNAL_ACTION_ROWS_SCHEMA_VERSION,
    SOURCE_SUBJECT_MATHEMATICS,
    ExternalActionRow,
    external_pseudonym,
    validate_no_raw_learner_identifiers,
)


ACTION_LOG_COLUMNS = ("assignment_log_id", "timestamp", "problem_id", "action")
ELIGIBLE_TEMP_COLUMNS = ("assignment_log_id", "timestamp", "problem_id", "action")
REQUIRED_RAW_FILES = (
    "action_logs.csv",
    "assignment_details.csv",
    "problem_details.csv",
    "sequence_details.csv",
)


def load_problem_skill_map(path: str | Path) -> dict[str, str | None]:
    """problem_id -> problem_skill_code (or None when the code is absent)."""
    frame = pd.read_csv(path, dtype=str, usecols=["problem_id", "problem_skill_code"])
    result: dict[str, str | None] = {}
    for problem_id, skill_code in zip(frame["problem_id"], frame["problem_skill_code"]):
        problem_id = str(problem_id)
        result[problem_id] = (
            str(skill_code).strip() if isinstance(skill_code, str) and skill_code.strip() else None
        )
    return result


def load_sequence_metadata(path: str | Path) -> dict[str, tuple[str | None, str]]:
    """sequence_id -> (grade from level_2, subject)."""
    frame = pd.read_csv(
        path,
        dtype=str,
        usecols=["sequence_id", "sequence_folder_path_level_2"],
    )
    return {
        str(sequence_id): (grade_from_level_2(level_2), SOURCE_SUBJECT_MATHEMATICS)
        for sequence_id, level_2 in zip(frame["sequence_id"], frame["sequence_folder_path_level_2"])
    }


def load_assignment_lookup(
    path: str | Path,
    required_assignment_ids: Iterable[str],
) -> dict[str, tuple[str, str]]:
    """assignment_log_id -> (student_id, sequence_id) for required ids only."""
    required = set(required_assignment_ids)
    if not required:
        return {}
    lookup: dict[str, tuple[str, str]] = {}
    seen: set[str] = set()
    for chunk in pd.read_csv(
        path,
        dtype=str,
        usecols=list(["assignment_log_id", "student_id", "sequence_id"]),
        chunksize=4_000_000,
    ):
        matched = chunk["assignment_log_id"].astype(str).isin(required)
        for assignment_id, student_id, sequence_id in zip(
            chunk.loc[matched, "assignment_log_id"],
            chunk.loc[matched, "student_id"],
            chunk.loc[matched, "sequence_id"],
        ):
            assignment_id = str(assignment_id)
            seen.add(assignment_id)
            if not student_id or not sequence_id:
                raise ValueError(f"assignment {assignment_id} is missing student or sequence identity")
            lookup[assignment_id] = (str(student_id), str(sequence_id))
    missing = required - seen
    if missing:
        sample = sorted(missing)[:5]
        raise ValueError(f"assignment details are unresolvable for {len(missing)} eligible assignment logs: {sample}")
    return lookup


def normalize_action_row(
    row: Mapping[str, object],
    *,
    release_id: str,
    pseudonym_key: bytes | str,
    assignment_lookup: Mapping[str, tuple[str, str]],
    problem_skills: Mapping[str, str | None],
    sequence_metadata: Mapping[str, tuple[str | None, str]],
    excluded: Counter[str],
    unresolved: Counter[str] | None = None,
) -> ExternalActionRow | None:
    """Normalize one raw action row, or record why it was excluded (None)."""
    timestamp = parse_epoch_seconds(row.get("timestamp"))
    if timestamp is None:
        excluded["unparseable_timestamp"] += 1
        return None
    if not in_selected_window(timestamp):
        excluded["outside_window"] += 1
        return None

    assignment_id = row.get("assignment_log_id")
    if not assignment_id:
        raise ValueError("action row is missing assignment_log_id")
    assignment_id = str(assignment_id)
    if assignment_id not in assignment_lookup:
        raise ValueError(f"action row references an unresolvable assignment log: {assignment_id}")
    student_id, sequence_id = assignment_lookup[assignment_id]
    if sequence_id not in sequence_metadata:
        raise ValueError(f"sequence metadata is unresolvable for sequence {sequence_id}")
    grade, subject = sequence_metadata[sequence_id]

    problem_id = row.get("problem_id")
    problem_key: str | None = None
    content_key: str | None = None
    skill_code: str | None = None
    if problem_id is not None and str(problem_id):
        problem_id = str(problem_id)
        problem_key = external_pseudonym("problem", problem_id, pseudonym_key)
        if problem_id not in problem_skills:
            # Detected source quirk: 819 action-log problem ids are absent from
            # problem_details.  The row's problem identity is still stable, so
            # it is emitted with nullable content/skill metadata and counted
            # rather than silently dropped or fabricated.
            if unresolved is not None:
                unresolved["problem_metadata_unresolved"] += 1
        else:
            skill_code = problem_skills[problem_id]
            content_base = skill_code or problem_id
            content_key = external_pseudonym("content", content_base, pseudonym_key)

    normalized = ExternalActionRow(
        datasetReleaseId=release_id,
        externalStudentKey=external_pseudonym("student", student_id, pseudonym_key),
        externalAssignmentKey=external_pseudonym("assignment", assignment_id, pseudonym_key),
        externalSequenceKey=external_pseudonym("sequence", sequence_id, pseudonym_key),
        externalProblemKey=problem_key,
        externalContentKey=content_key,
        sourceTimestamp=timestamp.isoformat(),
        sourceActionType=str(row.get("action") or ""),
        sourceGrade=grade,
        sourceSubject=subject,
        sourceSkillCode=skill_code,
    )
    validate_no_raw_learner_identifiers(normalized.to_csv_row(), student_id)
    return normalized


def write_eligible_action_rows(raw_dir: Path, temp_path: Path) -> tuple[set[str], Counter[str]]:
    """Pass 1: stream action_logs, keep only in-window rows, collect ids."""
    assignment_ids: set[str] = set()
    totals = Counter()
    first_write = True
    path = raw_dir / "action_logs.csv"
    for chunk in pd.read_csv(path, dtype=str, usecols=list(ACTION_LOG_COLUMNS), chunksize=4_000_000):
        timestamps = pd.to_numeric(chunk["timestamp"], errors="coerce")
        parsed = pd.to_datetime(timestamps, unit="s", utc=True)
        parseable = timestamps.notna()
        in_window = parseable & (parsed >= WINDOW_START) & (parsed <= WINDOW_END)
        eligible = chunk[in_window]
        if not eligible.empty:
            assignment_ids.update(eligible["assignment_log_id"].dropna().astype(str).tolist())
            eligible[list(ELIGIBLE_TEMP_COLUMNS)].to_csv(
                temp_path,
                mode="a",
                header=first_write,
                index=False,
                encoding="utf-8",
            )
            first_write = False
        totals["rows_read"] += len(chunk)
        totals["rows_in_window"] += int(in_window.sum())
        totals["rows_unparseable_timestamp"] += int((~parseable).sum())
        totals["rows_outside_window"] += int((parseable & ~in_window).sum())
    return assignment_ids, totals


def stream_normalized_rows(
    temp_path: Path,
    *,
    release_id: str,
    pseudonym_key: bytes | str,
    assignment_lookup: Mapping[str, tuple[str, str]],
    problem_skills: Mapping[str, str | None],
    sequence_metadata: Mapping[str, tuple[str | None, str]],
    excluded: Counter[str],
    unresolved: Counter[str] | None = None,
) -> Iterable[ExternalActionRow]:
    with temp_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            normalized = normalize_action_row(
                row,
                release_id=release_id,
                pseudonym_key=pseudonym_key,
                assignment_lookup=assignment_lookup,
                problem_skills=problem_skills,
                sequence_metadata=sequence_metadata,
                excluded=excluded,
                unresolved=unresolved,
            )
            if normalized is not None:
                yield normalized


def file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_file_hashes(raw_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(raw_dir.glob("*.csv")):
        hashes[path.name] = file_sha256(path)
    return hashes


def run_adapter(
    raw_dir: str | Path,
    processed_dir: str | Path,
    *,
    release_id: str,
    pseudonym_key: bytes | str,
    source_hashes: Mapping[str, str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Normalize the eligible 2022-2023 action rows and write CSV + manifest."""
    raw = Path(raw_dir)
    processed = Path(processed_dir)
    for filename in REQUIRED_RAW_FILES:
        if not (raw / filename).exists():
            raise FileNotFoundError(f"required source file is missing: {filename}")
    processed.mkdir(parents=True, exist_ok=True)

    output_path = processed / "external_action_rows_v1.csv"
    manifest_path = processed / "manifest.json"
    if (output_path.exists() or manifest_path.exists()) and not force:
        raise FileExistsError("protected processed outputs are immutable; use --force to regenerate")

    temp_path = processed / ".j1-eligible-actions.tmp.csv"
    if temp_path.exists():
        temp_path.unlink()
    staging = Path(mkdtemp(prefix=".j1-staging-", dir=processed))

    try:
        assignment_ids, totals = write_eligible_action_rows(raw, temp_path)
        excluded: Counter[str] = Counter()
        unresolved: Counter[str] = Counter()
        rows_by_action: Counter[str] = Counter()
        rows_by_grade: Counter[str] = Counter()
        unique_students: set[str] = set()
        unique_assignments: set[str] = set()
        unique_problems: set[str] = set()
        emitted = 0

        staged_output = staging / output_path.name
        with staged_output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=EXTERNAL_ACTION_ROW_FIELDS)
            writer.writeheader()
            if temp_path.exists():
                assignment_lookup = load_assignment_lookup(
                    raw / "assignment_details.csv",
                    assignment_ids,
                )
                problem_skills = load_problem_skill_map(raw / "problem_details.csv")
                sequence_metadata = load_sequence_metadata(raw / "sequence_details.csv")
                for normalized in stream_normalized_rows(
                    temp_path,
                    release_id=release_id,
                    pseudonym_key=pseudonym_key,
                    assignment_lookup=assignment_lookup,
                    problem_skills=problem_skills,
                    sequence_metadata=sequence_metadata,
                    excluded=excluded,
                    unresolved=unresolved,
                ):
                    writer.writerow(normalized.to_csv_row())
                    emitted += 1
                    rows_by_action[normalized.sourceActionType] += 1
                    rows_by_grade[normalized.sourceGrade or "none"] += 1
                    unique_students.add(normalized.externalStudentKey)
                    unique_assignments.add(normalized.externalAssignmentKey)
                    if normalized.externalProblemKey:
                        unique_problems.add(normalized.externalProblemKey)

        hashes = dict(source_hashes) if source_hashes else source_file_hashes(raw)
        counts = {
            "rowsRead": totals["rows_read"],
            "rowsInWindow": totals["rows_in_window"],
            "rowsUnparseableTimestampExcluded": totals["rows_unparseable_timestamp"],
            "rowsOutsideWindowExcluded": totals["rows_outside_window"],
            "normalizedRowsEmitted": emitted,
            "rowsWithUnresolvedProblemMetadata": unresolved["problem_metadata_unresolved"],
            "rowsByActionType": dict(rows_by_action.most_common()),
            "rowsBySourceGrade": dict(sorted(rows_by_grade.items())),
            "uniqueExternalStudentKeys": len(unique_students),
            "uniqueExternalAssignmentKeys": len(unique_assignments),
            "uniqueExternalProblemKeys": len(unique_problems),
        }
        manifest = build_manifest(
            release_id=release_id,
            source_hashes=hashes,
            counts=counts,
            action_rows_path=staged_output,
        )
        staged_manifest = staging / manifest_path.name
        write_manifest(manifest, staged_manifest)
        _assert_manifest_safe(manifest, pseudonym_key, processed)
        staged_output.replace(output_path)
        staged_manifest.replace(manifest_path)
        return {"actionRows": output_path, "manifest": manifest_path, "counts": counts}
    finally:
        if temp_path.exists():
            temp_path.unlink()
        rmtree(staging, ignore_errors=True)


def _assert_manifest_safe(manifest: Mapping[str, object], key: bytes | str, processed: Path) -> None:
    serialized = json.dumps(manifest, sort_keys=True)
    key_text = key.decode("utf-8", errors="ignore") if isinstance(key, bytes) else key
    if key_text and key_text in serialized:
        raise ValueError("manifest must not contain pseudonym key material")
    if str(processed.resolve()) in serialized or str(Path.cwd().resolve()) in serialized:
        raise ValueError("manifest must not contain a local working path")


def main() -> None:
    parser = argparse.ArgumentParser(description="J1 ASSISTments external action-row adapter")
    parser.add_argument("--raw-dir", required=True, help="Protected raw CSV directory (outside Git)")
    parser.add_argument("--processed-dir", required=True, help="Protected processed output directory (outside Git)")
    parser.add_argument("--release-id", default="assistments-edm-cup-2023-release-v1")
    parser.add_argument(
        "--pseudonym-key",
        default=os.environ.get("LOGIC_OASIS_ASSISTMENTS_PSEUDONYM_KEY"),
        help="Project-local HMAC key; prefer the environment variable. Never written to the manifest.",
    )
    parser.add_argument(
        "--source-hashes",
        help="Optional JSON with source file SHA-256 values (e.g. the protected j0 scan summary)",
    )
    parser.add_argument("--force", action="store_true", help="Regenerate immutable protected outputs")
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

    result = run_adapter(
        args.raw_dir,
        args.processed_dir,
        release_id=args.release_id,
        pseudonym_key=args.pseudonym_key,
        source_hashes=source_hashes,
        force=args.force,
    )
    print(f"action rows: {result['actionRows']}")
    print(f"manifest: {result['manifest']}")
    print(f"counts: {json.dumps(result['counts'], indent=2, sort_keys=True)}")


if __name__ == "__main__":
    main()
