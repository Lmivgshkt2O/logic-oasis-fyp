"""J2: current -> immediate compatible next-attempt labels and censoring.

For every feature-valid current attempt, the immediate chronological next
assignment for the same learner + sequence is located without skipping
intervening assignments.  The label is derived only from the next outcome-valid
attempt's correct_rate against the frozen masteryCriterion (0.60); every other
case is censored and never converted into either class.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from .assistments_contract import PROVENANCE, SOURCE_DATASET
from .j2_contract import (
    FEATURE_VALID,
    MASTERY_CRITERION,
    OUTCOME_VALID,
    REASON_CHRONOLOGY_AMBIGUOUS,
    REASON_IDENTICAL_PROBLEM_SET,
    REASON_NEXT_NOT_OUTCOME_VALID,
    REASON_NO_NEXT,
    load_j2_contract,
    validate_j2_contract,
)
from .reconstruct_attempts import ATTEMPT_FIELDS


LABEL_FIELDS = (
    "datasetReleaseId",
    "currentAttemptId",
    "externalStudentKey",
    "externalSequenceKey",
    "currentAttemptStartedAt",
    "nextAttemptId",
    "nextAttemptStartedAt",
    "nextCorrectRate",
    "nextAttemptCensorReason",
    "next_attempt_support_needed",
    "censorReason",
    "problemOverlapRate",
    "provenance",
    "sourceDataset",
)

CATEGORY_COLUMNS = (
    "datasetReleaseId",
    "externalStudentKey",
    "externalAssignmentKey",
    "externalSequenceKey",
    "externalContentKey",
    "externalAttemptId",
    "validityLevel",
    "attemptCensorReason",
    "provenance",
    "sourceDataset",
)


@dataclass(frozen=True)
class LabelRow:
    datasetReleaseId: str
    currentAttemptId: str
    externalStudentKey: str
    externalSequenceKey: str
    currentAttemptStartedAt: datetime
    nextAttemptId: str | None
    nextAttemptStartedAt: datetime | None
    nextCorrectRate: float | None
    nextAttemptCensorReason: str | None
    next_attempt_support_needed: bool | None
    censorReason: str | None
    problemOverlapRate: float | None

    @property
    def provenance(self) -> str:
        return PROVENANCE

    @property
    def sourceDataset(self) -> str:
        return SOURCE_DATASET

    def to_csv_row(self) -> dict[str, object]:
        return {
            "datasetReleaseId": self.datasetReleaseId,
            "currentAttemptId": self.currentAttemptId,
            "externalStudentKey": self.externalStudentKey,
            "externalSequenceKey": self.externalSequenceKey,
            "currentAttemptStartedAt": self.currentAttemptStartedAt.isoformat(),
            "nextAttemptId": self.nextAttemptId or "",
            "nextAttemptStartedAt": self.nextAttemptStartedAt.isoformat() if self.nextAttemptStartedAt else "",
            "nextCorrectRate": "" if self.nextCorrectRate is None else round(self.nextCorrectRate, 8),
            "nextAttemptCensorReason": self.nextAttemptCensorReason or "",
            "next_attempt_support_needed": "" if self.next_attempt_support_needed is None else str(self.next_attempt_support_needed).lower(),
            "censorReason": self.censorReason or "",
            "problemOverlapRate": "" if self.problemOverlapRate is None else round(self.problemOverlapRate, 8),
            "provenance": self.provenance,
            "sourceDataset": self.sourceDataset,
        }


def _parse_started_at(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _problem_key_set(graded_problem_keys: object) -> tuple[str, ...]:
    if not isinstance(graded_problem_keys, str) or not graded_problem_keys:
        return ()
    return tuple(sorted(item for item in graded_problem_keys.split("|") if item))


def build_label_rows(
    attempts: Sequence[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any],
    release_id: str,
) -> tuple[list[LabelRow], Counter[str]]:
    """Pair every feature-valid current attempt with its immediate next."""
    summary: Counter[str] = Counter()
    rows: list[LabelRow] = []

    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for attempt in attempts:
        if not attempt.get("externalStudentKey") or not attempt.get("externalSequenceKey"):
            continue
        grouped.setdefault((str(attempt["externalStudentKey"]), str(attempt["externalSequenceKey"])), []).append(attempt)

    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda item: (_parse_started_at(item.get("attemptStartedAt")) or datetime.max, str(item.get("externalAssignmentKey"))),
        )
        for index, current in enumerate(ordered):
            if str(current.get("featureValid", "")).lower() != "true" and current.get("featureValid") is not True:
                continue
            current_id = str(current["externalAttemptId"])
            current_started = _parse_started_at(current.get("attemptStartedAt"))
            next_attempt = ordered[index + 1] if index + 1 < len(ordered) else None
            if next_attempt is None:
                rows.append(_censor(current_id, current, None, REASON_NO_NEXT, contract, release_id))
                summary["censored_no_next_attempt"] += 1
                continue
            summary["candidatePairs"] += 1

            next_started = _parse_started_at(next_attempt.get("attemptStartedAt"))
            if current_started is not None and next_started is not None and current_started == next_started:
                rows.append(_censor(current_id, current, next_attempt, REASON_CHRONOLOGY_AMBIGUOUS, contract, release_id))
                summary["censored_chronology_ambiguous"] += 1
                summary["chronologyAmbiguousPairs"] += 1
                continue

            next_validity = str(next_attempt.get("validityLevel", ""))
            if next_validity != OUTCOME_VALID:
                rows.append(_censor(current_id, current, next_attempt, REASON_NEXT_NOT_OUTCOME_VALID, contract, release_id))
                summary["censored_next_not_outcome_valid"] += 1
                continue

            current_problems = set(_problem_key_set(current.get("gradedProblemKeys")))
            next_problems = set(_problem_key_set(next_attempt.get("gradedProblemKeys")))
            if current_problems and current_problems == next_problems:
                rows.append(_censor(current_id, current, next_attempt, REASON_IDENTICAL_PROBLEM_SET, contract, release_id))
                summary["censored_identical_problem_set_repeat"] += 1
                continue

            next_correct_rate = _to_float(next_attempt.get("correct_rate"))
            if next_correct_rate is None:
                rows.append(_censor(current_id, current, next_attempt, REASON_NEXT_NOT_OUTCOME_VALID, contract, release_id))
                summary["censored_next_not_outcome_valid"] += 1
                continue

            overlap_rate = _overlap_rate(current_problems, next_problems)
            target = next_correct_rate < MASTERY_CRITERION
            rows.append(
                LabelRow(
                    datasetReleaseId=release_id,
                    currentAttemptId=current_id,
                    externalStudentKey=str(current["externalStudentKey"]),
                    externalSequenceKey=str(current["externalSequenceKey"]),
                    currentAttemptStartedAt=current_started or datetime.min,
                    nextAttemptId=str(next_attempt["externalAttemptId"]),
                    nextAttemptStartedAt=next_started,
                    nextCorrectRate=next_correct_rate,
                    nextAttemptCensorReason=None,
                    next_attempt_support_needed=target,
                    censorReason=None,
                    problemOverlapRate=overlap_rate,
                )
            )
            summary["labelledPairs"] += 1
            summary[f"target_{str(target).lower()}"] += 1

    summary["featureValidCurrents"] = sum(
        1 for attempt in attempts if attempt.get("featureValid") is True or str(attempt.get("featureValid", "")).lower() == "true"
    )
    summary["uniqueLearnersLabelled"] = len({row.externalStudentKey for row in rows if row.next_attempt_support_needed is not None})
    return rows, summary


def _censor(
    current_id: str,
    current: Mapping[str, Any],
    next_attempt: Mapping[str, Any] | None,
    reason: str,
    contract: Mapping[str, Any],
    release_id: str,
) -> LabelRow:
    next_started = _parse_started_at(next_attempt.get("attemptStartedAt")) if next_attempt else None
    next_correct_rate = _to_float(next_attempt.get("correct_rate")) if next_attempt else None
    return LabelRow(
        datasetReleaseId=release_id,
        currentAttemptId=current_id,
        externalStudentKey=str(current["externalStudentKey"]),
        externalSequenceKey=str(current["externalSequenceKey"]),
        currentAttemptStartedAt=_parse_started_at(current.get("attemptStartedAt")) or datetime.min,
        nextAttemptId=str(next_attempt["externalAttemptId"]) if next_attempt else None,
        nextAttemptStartedAt=next_started,
        nextCorrectRate=next_correct_rate,
        nextAttemptCensorReason=str(next_attempt.get("attemptCensorReason") or "") if next_attempt else None,
        next_attempt_support_needed=None,
        censorReason=reason,
        problemOverlapRate=None,
    )


def _overlap_rate(current: set[str], next_: set[str]) -> float:
    if not current or not next_:
        return 0.0
    return len(current & next_) / min(len(current), len(next_))


def _to_float(value: object) -> float | None:
    if value is None or value == "" or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_attempts(path: str | Path) -> list[dict[str, Any]]:
    frame = pd.read_csv(
        path,
        dtype={column: "category" for column in CATEGORY_COLUMNS},
        keep_default_na=False,
    )
    for column in ("attemptStartedAt", "attemptEndedAt"):
        frame[column] = pd.to_datetime(frame[column], format="ISO8601", utc=True, errors="coerce")
    return frame.to_dict("records")


def write_labels_csv(rows: Iterable[LabelRow], path: str | Path) -> Path:
    import csv

    destination = Path(path)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())
    return destination


def build_j2_manifest(
    *,
    release_id: str,
    contract_version: str,
    action_rows_hash: str,
    attempts_hash: str,
    outcomes_hash: str,
    labels_hash: str,
    reconstruction_summary: Mapping[str, int],
    label_summary: Mapping[str, int],
) -> dict[str, Any]:
    from datetime import datetime, timezone

    return {
        "manifestSchemaVersion": "assistments-j2-manifest-v1",
        "contractVersion": contract_version,
        "releaseId": release_id,
        "dataset": SOURCE_DATASET,
        "provenance": PROVENANCE,
        "masteryCriterion": MASTERY_CRITERION,
        "sourceWindow": "2022-01-01/2023-12-31",
        "usageTerms": "ASSISTments Data Terms of Use effective 2020-10-30",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "fileSha256": {
            "external_action_rows_v1.csv": action_rows_hash,
            "external_attempts_v1.csv": attempts_hash,
            "external_problem_outcomes_v1.csv": outcomes_hash,
            "external_labels_v1.csv": labels_hash,
        },
        "reconstruction": dict(reconstruction_summary),
        "labels": dict(label_summary),
        "containsRawIdentifiers": False,
        "containsSecretMaterial": False,
    }


def file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="J2 label construction and J2 manifest")
    parser.add_argument("--attempts", required=True, help="Protected J2 external_attempts CSV")
    parser.add_argument("--action-rows", required=True, help="Protected J1 external_action_rows CSV")
    parser.add_argument("--problem-outcomes", required=True, help="Protected J2 problem outcomes CSV")
    parser.add_argument("--processed-dir", required=True, help="Protected processed output directory")
    parser.add_argument("--contract", default=None)
    parser.add_argument("--release-id", default="assistments-edm-cup-2023-release-v1")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parents[2]
    contract_path = Path(args.contract) if args.contract else repo_dir / "external_data" / "assistments" / "assistments_j2_contract_v1.yaml"
    contract = validate_j2_contract(load_j2_contract(contract_path))

    processed = Path(args.processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    labels_path = processed / "external_labels_v1.csv"
    manifest_path = processed / "j2_manifest.json"
    if (labels_path.exists() or manifest_path.exists()) and not args.force:
        raise FileExistsError("protected J2 label outputs are immutable; use --force")

    attempts = read_attempts(args.attempts)
    rows, label_summary = build_label_rows(attempts, contract=contract, release_id=args.release_id)
    write_labels_csv(rows, labels_path)

    reconstruction_summary: dict[str, int] = {}
    summary_path = processed / "j2_reconstruction_summary.json"
    if summary_path.exists():
        reconstruction_summary = json.loads(summary_path.read_text(encoding="utf-8"))

    manifest = build_j2_manifest(
        release_id=args.release_id,
        contract_version=contract["contractVersion"],
        action_rows_hash=file_sha256(Path(args.action_rows)),
        attempts_hash=file_sha256(Path(args.attempts)),
        outcomes_hash=file_sha256(Path(args.problem_outcomes)),
        labels_hash=file_sha256(labels_path),
        reconstruction_summary=reconstruction_summary,
        label_summary=dict(sorted(label_summary.items())),
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(dict(sorted(label_summary.items())), indent=2, sort_keys=True))
    print(f"labels: {labels_path}")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
