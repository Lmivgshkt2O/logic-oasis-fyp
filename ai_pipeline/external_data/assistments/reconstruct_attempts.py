"""J2: reconstruct learner-specific in-unit assignment attempts.

One attempt is one learner-specific in-unit assignment.  Problem correctness
uses the first valid graded response after problem start; response time uses
the frozen 30-minute telemetry-quality rule; outcome-valid and feature-valid
levels follow the J2 contract.  All outputs remain pseudonymized external_real
records written to the protected directory.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from .assistments_contract import PROVENANCE, SOURCE_DATASET
from .j2_contract import (
    ASSIGNMENT_FINISH_ACTION,
    ASSIGNMENT_START_ACTION,
    FEATURE_VALID,
    GRADED_ACTIONS,
    INVALID,
    MAX_RESPONSE_TIME_MS,
    MIN_VALID_GRADED_PROBLEMS,
    MIN_VALID_RESPONSE_TIME_PAIRS,
    OUTCOME_VALID,
    PRIMARY_GRADE,
    PRIMARY_SUBJECT,
    PROBLEM_START_ACTION,
    REASON_INCOMPLETE,
    REASON_INSUFFICIENT_GRADED,
    REASON_INSUFFICIENT_TIMING,
    REASON_NO_START,
    REASON_NOT_PRIMARY_COHORT,
    RT_AMBIGUOUS,
    RT_CENSORED_OVER_30_MIN,
    RT_MISSING_GRADED,
    RT_NEGATIVE,
    RT_NO_START,
    RT_VALID,
    RT_ZERO,
    load_j2_contract,
    validate_j2_contract,
)


ATTEMPT_FIELDS = (
    "datasetReleaseId",
    "externalAttemptId",
    "externalStudentKey",
    "externalAssignmentKey",
    "externalSequenceKey",
    "externalContentKey",
    "externalAttemptSequence",
    "attemptStartedAt",
    "attemptEndedAt",
    "completed",
    "cohortEligible",
    "sourceGrade",
    "validityLevel",
    "featureValid",
    "attemptCensorReason",
    "eligibleProblemCount",
    "gradedProblemCount",
    "correctFirstResponseCount",
    "correct_rate",
    "validResponseTimePairs",
    "mean_response_time_ms",
    "unresolvedProblemMetadataCount",
    "multipleStartProblemsCount",
    "gradedProblemKeys",
    "provenance",
    "sourceDataset",
)

PROBLEM_OUTCOME_FIELDS = (
    "externalStudentKey",
    "externalAssignmentKey",
    "externalSequenceKey",
    "externalProblemKey",
    "hasStart",
    "multipleStarts",
    "graded",
    "correct",
    "responseTimeMs",
    "responseTimeStatus",
    "unresolvedMetadata",
)

CATEGORY_COLUMNS = (
    "datasetReleaseId",
    "externalStudentKey",
    "externalAssignmentKey",
    "externalSequenceKey",
    "externalProblemKey",
    "externalContentKey",
    "sourceActionType",
    "sourceGrade",
    "sourceSubject",
    "sourceSkillCode",
    "provenance",
    "sourceDataset",
    "sourceWindow",
)


@dataclass(frozen=True)
class ProblemOutcome:
    externalStudentKey: str
    externalAssignmentKey: str
    externalSequenceKey: str
    externalProblemKey: str
    hasStart: bool
    multipleStarts: bool
    graded: bool
    correct: bool | None
    responseTimeMs: float | None
    responseTimeStatus: str
    unresolvedMetadata: bool

    def to_csv_row(self) -> dict[str, str | int | float | bool | None]:
        return {
            "externalStudentKey": self.externalStudentKey,
            "externalAssignmentKey": self.externalAssignmentKey,
            "externalSequenceKey": self.externalSequenceKey,
            "externalProblemKey": self.externalProblemKey,
            "hasStart": self.hasStart,
            "multipleStarts": self.multipleStarts,
            "graded": self.graded,
            "correct": self.correct,
            "responseTimeMs": self.responseTimeMs,
            "responseTimeStatus": self.responseTimeStatus,
            "unresolvedMetadata": self.unresolvedMetadata,
        }


@dataclass(frozen=True)
class AttemptRecord:
    datasetReleaseId: str
    externalAttemptId: str
    externalStudentKey: str
    externalAssignmentKey: str
    externalSequenceKey: str
    externalContentKey: str
    externalAttemptSequence: int | None
    attemptStartedAt: datetime | None
    attemptEndedAt: datetime | None
    completed: bool
    cohortEligible: bool
    sourceGrade: str | None
    validityLevel: str
    featureValid: bool
    attemptCensorReason: str | None
    eligibleProblemCount: int
    gradedProblemCount: int
    correctFirstResponseCount: int
    correct_rate: float | None
    validResponseTimePairs: int
    mean_response_time_ms: float | None
    unresolvedProblemMetadataCount: int
    multipleStartProblemsCount: int
    gradedProblemKeys: tuple[str, ...]

    @property
    def provenance(self) -> str:
        return PROVENANCE

    @property
    def sourceDataset(self) -> str:
        return SOURCE_DATASET

    def to_csv_row(self) -> dict[str, object]:
        return {
            "datasetReleaseId": self.datasetReleaseId,
            "externalAttemptId": self.externalAttemptId,
            "externalStudentKey": self.externalStudentKey,
            "externalAssignmentKey": self.externalAssignmentKey,
            "externalSequenceKey": self.externalSequenceKey,
            "externalContentKey": self.externalContentKey,
            "externalAttemptSequence": self.externalAttemptSequence,
            "attemptStartedAt": self.attemptStartedAt.isoformat() if self.attemptStartedAt else "",
            "attemptEndedAt": self.attemptEndedAt.isoformat() if self.attemptEndedAt else "",
            "completed": self.completed,
            "cohortEligible": self.cohortEligible,
            "sourceGrade": self.sourceGrade or "",
            "validityLevel": self.validityLevel,
            "featureValid": self.featureValid,
            "attemptCensorReason": self.attemptCensorReason or "",
            "eligibleProblemCount": self.eligibleProblemCount,
            "gradedProblemCount": self.gradedProblemCount,
            "correctFirstResponseCount": self.correctFirstResponseCount,
            "correct_rate": "" if self.correct_rate is None else round(self.correct_rate, 8),
            "validResponseTimePairs": self.validResponseTimePairs,
            "mean_response_time_ms": "" if self.mean_response_time_ms is None else round(self.mean_response_time_ms, 8),
            "unresolvedProblemMetadataCount": self.unresolvedProblemMetadataCount,
            "multipleStartProblemsCount": self.multipleStartProblemsCount,
            "gradedProblemKeys": "|".join(self.gradedProblemKeys),
            "provenance": self.provenance,
            "sourceDataset": self.sourceDataset,
        }


def _normalize_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        raw_ts = row.get("sourceTimestamp")
        if raw_ts is None or raw_ts == "":
            raise ValueError("attempt reconstruction requires a sourceTimestamp on every row")
        timestamp = raw_ts if isinstance(raw_ts, datetime) else pd.to_datetime(raw_ts, utc=True).to_pydatetime()
        problem_key = row.get("externalProblemKey")
        normalized.append(
            {
                "timestamp": timestamp,
                "action": str(row.get("sourceActionType") or ""),
                "problem_key": str(problem_key) if problem_key else None,
                "skill_code": str(row.get("sourceSkillCode") or "").strip() or None,
                "grade": str(row.get("sourceGrade") or "").strip() or None,
                "subject": str(row.get("sourceSubject") or "").strip() or None,
                "student_key": str(row.get("externalStudentKey") or ""),
                "assignment_key": str(row.get("externalAssignmentKey") or ""),
                "sequence_key": str(row.get("externalSequenceKey") or ""),
            }
        )
    return normalized


def build_problem_outcome(problem_rows: Sequence[Mapping[str, Any]]) -> ProblemOutcome:
    """One problem instance inside one assignment."""
    return _outcome_from_normalized(_normalize_rows(problem_rows))


def _outcome_from_normalized(rows: Sequence[Mapping[str, Any]]) -> ProblemOutcome:
    """Build a problem outcome from already-normalized rows."""
    first = rows[0]
    problem_key = first["problem_key"]
    starts = [r["timestamp"] for r in rows if r["action"] == PROBLEM_START_ACTION]
    graded = [(r["timestamp"], r["action"]) for r in rows if r["action"] in GRADED_ACTIONS]
    has_start = bool(starts)
    multiple_starts = len(starts) > 1

    correct: bool | None = None
    graded_flag = False
    response_time_ms: float | None = None
    status: str

    if not has_start:
        status = RT_NO_START
    elif not graded:
        status = RT_MISSING_GRADED
    else:
        anchor = min(starts)
        later_graded = [(t, a) for t, a in graded if t >= anchor]
        if not later_graded:
            status = RT_MISSING_GRADED
        else:
            first_graded = min(later_graded, key=lambda item: item[0])
            graded_flag = True
            correct = first_graded[1] == "correct_response"
            if multiple_starts:
                status = RT_AMBIGUOUS
            else:
                duration_ms = (first_graded[0] - anchor).total_seconds() * 1000.0
                if duration_ms < 0:
                    status = RT_NEGATIVE
                elif duration_ms == 0:
                    status = RT_ZERO
                elif duration_ms > MAX_RESPONSE_TIME_MS:
                    status = RT_CENSORED_OVER_30_MIN
                else:
                    status = RT_VALID
                # Raw computed duration is retained for audit even when
                # censored; feature means use only RT_VALID observations.
                response_time_ms = duration_ms

    unresolved = any(r["skill_code"] is None for r in rows)
    return ProblemOutcome(
        externalStudentKey=first["student_key"],
        externalAssignmentKey=first["assignment_key"],
        externalSequenceKey=first["sequence_key"],
        externalProblemKey=problem_key,
        hasStart=has_start,
        multipleStarts=multiple_starts,
        graded=graded_flag,
        correct=correct,
        responseTimeMs=response_time_ms,
        responseTimeStatus=status,
        unresolvedMetadata=unresolved,
    )


def build_attempt_from_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any],
    release_id: str,
    cohort_grades: Sequence[str] = ("6",),
) -> AttemptRecord:
    """Reconstruct one assignment instance as an external attempt."""
    normalized = _normalize_rows(rows)
    if not normalized:
        raise ValueError("an attempt requires at least one action row")
    first = normalized[0]
    student_key = first["student_key"]
    assignment_key = first["assignment_key"]
    sequence_key = first["sequence_key"]
    if not all(r["student_key"] == student_key and r["assignment_key"] == assignment_key and r["sequence_key"] == sequence_key for r in normalized):
        raise ValueError("attempt rows must share learner/assignment/sequence identity")

    start_times = [r["timestamp"] for r in normalized if r["action"] == ASSIGNMENT_START_ACTION]
    if not start_times:
        return AttemptRecord(
            datasetReleaseId=release_id,
            externalAttemptId=attempt_id(student_key, assignment_key),
            externalStudentKey=student_key,
            externalAssignmentKey=assignment_key,
            externalSequenceKey=sequence_key,
            externalContentKey=sequence_key,
            externalAttemptSequence=None,
            attemptStartedAt=None,
            attemptEndedAt=None,
            completed=False,
            cohortEligible=False,
            sourceGrade=None,
            validityLevel=INVALID,
            featureValid=False,
            attemptCensorReason=REASON_NO_START,
            eligibleProblemCount=0,
            gradedProblemCount=0,
            correctFirstResponseCount=0,
            correct_rate=None,
            validResponseTimePairs=0,
            mean_response_time_ms=None,
            unresolvedProblemMetadataCount=0,
            multipleStartProblemsCount=0,
            gradedProblemKeys=(),
        )

    started_at = min(start_times)
    finish_times = [r["timestamp"] for r in normalized if r["action"] == ASSIGNMENT_FINISH_ACTION and r["timestamp"] > started_at]
    completed = bool(finish_times)
    ended_at = max(finish_times) if finish_times else None

    grades = {r["grade"] for r in normalized if r["grade"]}
    subjects = {r["subject"] for r in normalized if r["subject"]}
    cohort_eligible = grades.issubset(set(cohort_grades)) and subjects == {PRIMARY_SUBJECT}
    source_grade = grades.pop() if len(grades) == 1 else None

    problems: dict[str, list[Mapping[str, Any]]] = {}
    for row in normalized:
        if row["problem_key"] is not None:
            problems.setdefault(row["problem_key"], []).append(row)

    outcomes = [_outcome_from_normalized(problem_rows) for problem_rows in problems.values()]
    graded_outcomes = [outcome for outcome in outcomes if outcome.graded]
    valid_timing = [outcome for outcome in outcomes if outcome.responseTimeStatus == RT_VALID]
    correct_count = sum(1 for outcome in graded_outcomes if outcome.correct)
    graded_count = len(graded_outcomes)
    correct_rate = correct_count / graded_count if graded_count else None
    mean_rt = (
        sum(outcome.responseTimeMs for outcome in valid_timing) / len(valid_timing)
        if valid_timing
        else None
    )

    if not completed:
        validity, reason = INVALID, REASON_INCOMPLETE
    elif not cohort_eligible:
        validity, reason = INVALID, REASON_NOT_PRIMARY_COHORT
    elif graded_count < MIN_VALID_GRADED_PROBLEMS:
        validity, reason = INVALID, REASON_INSUFFICIENT_GRADED
    else:
        validity, reason = OUTCOME_VALID, None

    feature_valid = validity == OUTCOME_VALID and len(valid_timing) >= MIN_VALID_RESPONSE_TIME_PAIRS
    if validity == OUTCOME_VALID and not feature_valid:
        reason = REASON_INSUFFICIENT_TIMING

    return AttemptRecord(
        datasetReleaseId=release_id,
        externalAttemptId=attempt_id(student_key, assignment_key),
        externalStudentKey=student_key,
        externalAssignmentKey=assignment_key,
        externalSequenceKey=sequence_key,
        externalContentKey=sequence_key,
        externalAttemptSequence=None,
        attemptStartedAt=started_at,
        attemptEndedAt=ended_at,
        completed=completed,
        cohortEligible=cohort_eligible,
        sourceGrade=source_grade,
        validityLevel=validity,
        featureValid=feature_valid,
        attemptCensorReason=reason,
        eligibleProblemCount=sum(1 for outcome in outcomes if outcome.hasStart),
        gradedProblemCount=graded_count,
        correctFirstResponseCount=correct_count,
        correct_rate=correct_rate,
        validResponseTimePairs=len(valid_timing),
        mean_response_time_ms=mean_rt,
        unresolvedProblemMetadataCount=sum(1 for outcome in outcomes if outcome.unresolvedMetadata),
        multipleStartProblemsCount=sum(1 for outcome in outcomes if outcome.multipleStarts),
        gradedProblemKeys=tuple(sorted(outcome.externalProblemKey for outcome in graded_outcomes)),
    )


def attempt_id(student_key: str, assignment_key: str) -> str:
    digest = sha256(f"{student_key}|{assignment_key}".encode("utf-8")).hexdigest()
    return f"assistments_attempt_{digest}"


def read_action_rows(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        dtype={column: "category" for column in CATEGORY_COLUMNS},
        keep_default_na=False,
    )
    frame["sourceTimestamp"] = pd.to_datetime(frame["sourceTimestamp"], format="ISO8601", utc=True)
    return frame


def reconstruct_attempts(
    frame: pd.DataFrame,
    *,
    contract: Mapping[str, Any],
    release_id: str,
    cohort_grades: Sequence[str] = ("6",),
) -> tuple[list[AttemptRecord], list[ProblemOutcome], Counter[str]]:
    """Build attempts and problem outcomes from the normalized action rows."""
    records: list[AttemptRecord] = []
    outcomes: list[ProblemOutcome] = []
    summary: Counter[str] = Counter()
    bkt_sequences: set[str] = set()

    for _, group in frame.groupby(["externalAssignmentKey"], observed=True, sort=False):
        rows = group.to_dict("records")
        record = build_attempt_from_rows(rows, contract=contract, release_id=release_id, cohort_grades=cohort_grades)
        if record.attemptCensorReason == REASON_NO_START:
            summary["assignmentsExcludedNoInWindowStart"] += 1
            continue
        records.append(record)
        for outcome in _problem_outcomes_for(record, rows):
            outcomes.append(outcome)
            summary[f"problemStatus_{outcome.responseTimeStatus}"] += 1
            if outcome.unresolvedMetadata:
                summary["unresolvedMetadataProblems"] += 1
            if outcome.graded:
                if any(r.get("sourceSkillCode") for r in rows if r.get("externalProblemKey") == outcome.externalProblemKey):
                    bkt_sequences.add(record.externalSequenceKey)

    ordering: dict[str, list[AttemptRecord]] = {}
    for record in records:
        ordering.setdefault((record.externalStudentKey, record.externalSequenceKey), []).append(record)
    sequenced: list[AttemptRecord] = []
    for key in sorted(ordering):
        ordered = sorted(ordering[key], key=lambda r: (r.attemptStartedAt, r.externalAssignmentKey))
        for index, record in enumerate(ordered, start=1):
            sequenced.append(replace(record, externalAttemptSequence=index))

    summary["assignmentsStarted"] = len(sequenced)
    summary["grade6Started"] = sum(1 for r in sequenced if r.cohortEligible)
    summary["grade6Completed"] = sum(1 for r in sequenced if r.cohortEligible and r.completed)
    summary["outcomeValid"] = sum(1 for r in sequenced if r.validityLevel == OUTCOME_VALID)
    summary["featureValid"] = sum(1 for r in sequenced if r.featureValid)
    summary["outcomeValidInsufficientTiming"] = sum(
        1 for r in sequenced if r.validityLevel == OUTCOME_VALID and not r.featureValid
    )
    summary["bktEligibleSequences"] = len(bkt_sequences)
    summary["uniqueStudents"] = len({r.externalStudentKey for r in sequenced})
    return sequenced, outcomes, summary


def _problem_outcomes_for(record: AttemptRecord, rows: Sequence[Mapping[str, Any]]) -> list[ProblemOutcome]:
    normalized = _normalize_rows(rows)
    problems: dict[str, list[Mapping[str, Any]]] = {}
    for row in normalized:
        if row["problem_key"] is not None:
            problems.setdefault(row["problem_key"], []).append(row)
    return [_outcome_from_normalized(problem_rows) for problem_rows in problems.values()]


def write_attempts_csv(records: Iterable[AttemptRecord], path: str | Path) -> Path:
    destination = Path(path)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv_writer(handle, ATTEMPT_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_csv_row())
    return destination


def write_problem_outcomes_csv(outcomes: Iterable[ProblemOutcome], path: str | Path) -> Path:
    destination = Path(path)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv_writer(handle, PROBLEM_OUTCOME_FIELDS)
        writer.writeheader()
        for outcome in outcomes:
            writer.writerow(outcome.to_csv_row())
    return destination


def csv_writer(handle, fields):
    return csv.DictWriter(handle, fieldnames=fields)


def main() -> None:
    parser = argparse.ArgumentParser(description="J2 attempt reconstruction")
    parser.add_argument("--action-rows", required=True, help="Protected J1 external_action_rows CSV")
    parser.add_argument("--processed-dir", required=True, help="Protected processed output directory")
    parser.add_argument("--contract", default=None, help="J2 contract YAML path (default: repo copy)")
    parser.add_argument("--release-id", default="assistments-edm-cup-2023-release-v1")
    parser.add_argument("--cohort-grades", default="6", help="Comma-separated cohort grades (frozen default 6; predeclared fallback 4,5,6)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parents[2]
    contract_path = Path(args.contract) if args.contract else repo_dir / "external_data" / "assistments" / "assistments_j2_contract_v1.yaml"
    contract = validate_j2_contract(load_j2_contract(contract_path))

    processed = Path(args.processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    attempts_path = processed / "external_attempts_v1.csv"
    outcomes_path = processed / "external_problem_outcomes_v1.csv"
    if (attempts_path.exists() or outcomes_path.exists()) and not args.force:
        raise FileExistsError("protected J2 attempt outputs are immutable; use --force")

    cohort_grades = tuple(grade.strip() for grade in args.cohort_grades.split(",") if grade.strip())
    frame = read_action_rows(args.action_rows)
    records, outcomes, summary = reconstruct_attempts(
        frame,
        contract=contract,
        release_id=args.release_id,
        cohort_grades=cohort_grades,
    )
    write_attempts_csv(records, attempts_path)
    write_problem_outcomes_csv(outcomes, outcomes_path)
    summary_path = processed / "j2_reconstruction_summary.json"
    summary_path.write_text(json.dumps(dict(sorted(summary.items())), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(dict(sorted(summary.items())), indent=2, sort_keys=True))
    print(f"attempts: {attempts_path}")
    print(f"problem outcomes: {outcomes_path}")


if __name__ == "__main__":
    main()
