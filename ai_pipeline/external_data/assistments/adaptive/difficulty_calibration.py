"""AQC-E2 streaming problem-difficulty calibration for ASSISTments Grade 6.

This module builds the protected problem-level difficulty calibration evidence
for the external Stage-B pathway under the frozen
``assistments-adaptive-contract-v1`` rules.  It processes only
pre-evaluation (2019-02-25..2021-12-31) exact Grade 6 Mathematics evidence,
excludes learners who also belong to the frozen 2022-2023 evaluation cohort,
and aggregates one first-graded outcome per (learner, problem) so repeated
encounters never inflate the independent-learner threshold.

No policy selector is imported or called here; no P1/P2/P3a decision is
computed.  Final within-skill proxy-tier assignment is NOT performed by this
module (see ``proxy_tiers.py`` and the E2 report for the frozen boundary-rule
status).
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable, Mapping

from ..assistments_contract import (
    graded_correctness,
    is_graded_action,
    parse_epoch_seconds,
)
from ..schemas import external_pseudonym
from .schemas import (
    CALIBRATION_WINDOW_END,
    CALIBRATION_WINDOW_START,
    EVALUATION_WINDOW_END,
    EVALUATION_WINDOW_START,
    EXTERNAL_PROVENANCE,
    MINIMUM_CALIBRATION_LEARNERS,
    ExternalContractError,
    difficulty_score,
    in_calibration_window,
    in_evaluation_window,
    smoothed_correct_probability,
)


CALIBRATION_METHOD_VERSION = "proxy-difficulty-v1"
CATALOG_VERSION = "assistments_problem_difficulty_proxy_v1"
CATALOG_FIELDS = (
    "datasetReleaseId",
    "externalProblemKey",
    "sourceSkillCode",
    "calibrationStart",
    "calibrationEnd",
    "calibrationLearnerCount",
    "calibrationResponseCount",
    "correctResponseCount",
    "smoothedCorrectProbability",
    "difficultyScore",
    "proxyDifficulty",
    "calibrationStatus",
    "provenance",
)


class CalibrationError(ValueError):
    """Raised when calibration evidence cannot be built safely."""


@dataclass(frozen=True)
class CalibrationProblemRecord:
    """One protected problem-level calibration record (schema-compatible)."""

    dataset_release_id: str
    external_problem_key: str
    source_skill_code: str
    calibration_start: datetime
    calibration_end: datetime
    calibration_learner_count: int
    calibration_response_count: int
    correct_response_count: int
    smoothed_correct_probability: float
    difficulty_score: float
    proxy_difficulty: str | None
    calibration_status: str
    provenance: str

    def __post_init__(self) -> None:
        if self.provenance != EXTERNAL_PROVENANCE:
            raise CalibrationError("calibration records must use provenance external_real")
        if not self.dataset_release_id or not self.external_problem_key or not self.source_skill_code:
            raise CalibrationError("release id, problem key, and skill code are required")
        if self.calibration_learner_count < 1 or self.calibration_response_count < 1:
            raise CalibrationError("calibration counts must be positive")
        if not 0 <= self.correct_response_count <= self.calibration_response_count:
            raise CalibrationError("correct counts are invalid")
        if self.calibration_status not in ("calibrated", "insufficient_problem_evidence"):
            raise CalibrationError("calibrationStatus is not in the frozen vocabulary")
        if self.calibration_status == "calibrated":
            if self.calibration_learner_count < MINIMUM_CALIBRATION_LEARNERS:
                raise CalibrationError(
                    "calibrated problems require the frozen minimum independent learners"
                )
        else:
            if self.calibration_learner_count >= MINIMUM_CALIBRATION_LEARNERS:
                raise CalibrationError(
                    "insufficient_problem_evidence requires fewer than 20 learners"
                )

    def to_csv_row(self) -> dict[str, str]:
        return {
            "datasetReleaseId": self.dataset_release_id,
            "externalProblemKey": self.external_problem_key,
            "sourceSkillCode": self.source_skill_code,
            "calibrationStart": self.calibration_start.isoformat(),
            "calibrationEnd": self.calibration_end.isoformat(),
            "calibrationLearnerCount": str(self.calibration_learner_count),
            "calibrationResponseCount": str(self.calibration_response_count),
            "correctResponseCount": str(self.correct_response_count),
            "smoothedCorrectProbability": f"{self.smoothed_correct_probability:.10f}",
            "difficultyScore": f"{self.difficulty_score:.10f}",
            "proxyDifficulty": self.proxy_difficulty or "",
            "calibrationStatus": self.calibration_status,
            "provenance": self.provenance,
        }


def exact_grade_six_sequence(
    sequence_metadata: Mapping[str, tuple[str | None, str]],
    sequence_id: object,
) -> bool:
    """Exact Grade 6 membership via ``sequence_folder_path_level_2 == "Grade 6"``."""
    grade, _subject = sequence_metadata.get(str(sequence_id), (None, None))
    return grade == "6"


def assignment_started_at(value: object) -> datetime | None:
    """Parse ``assignment_start_time`` epoch seconds (UTC) or fail closed."""
    return parse_epoch_seconds(value)


def collect_grade_six_learner_sets(
    assignment_path: str | Path,
    sequence_metadata: Mapping[str, tuple[str | None, str]],
    *,
    calibration_start: datetime = CALIBRATION_WINDOW_START,
    calibration_end: datetime = CALIBRATION_WINDOW_END,
    evaluation_start: datetime = EVALUATION_WINDOW_START,
    evaluation_end: datetime = EVALUATION_WINDOW_END,
) -> dict[str, object]:
    """Scan assignment_details once and return calibration/evaluation sets.

    Returns:
        calibrationAssignments: assignment_log_id -> student_id for exact
            Grade 6 assignments started inside the calibration window.
        calibrationLearners: raw student ids for those assignments.
        evaluationLearners: raw student ids for exact Grade 6 assignments
            started inside the evaluation window.
        counters: audit counters for unparseable starts and non-Grade-6 rows.
    """
    import pandas as pd

    calibration_assignments: dict[str, str] = {}
    calibration_learners: set[str] = set()
    evaluation_learners: set[str] = set()
    counters: Counter[str] = Counter()
    for chunk in pd.read_csv(
        assignment_path,
        dtype=str,
        usecols=["assignment_log_id", "student_id", "sequence_id", "assignment_start_time"],
        chunksize=4_000_000,
    ):
        for assignment_id, student_id, sequence_id, start_value in zip(
            chunk["assignment_log_id"],
            chunk["student_id"],
            chunk["sequence_id"],
            chunk["assignment_start_time"],
        ):
            assignment_id = str(assignment_id)
            if not assignment_id or not student_id or not sequence_id:
                counters["assignment_identity_missing"] += 1
                continue
            if not exact_grade_six_sequence(sequence_metadata, sequence_id):
                counters["assignment_not_grade_six"] += 1
                continue
            start = assignment_started_at(start_value)
            if start is None:
                counters["assignment_start_unparseable"] += 1
                continue
            if calibration_start <= start <= calibration_end:
                calibration_assignments[assignment_id] = str(student_id)
                calibration_learners.add(str(student_id))
                counters["assignment_calibration_grade_six"] += 1
            elif evaluation_start <= start <= evaluation_end:
                evaluation_learners.add(str(student_id))
                counters["assignment_evaluation_grade_six"] += 1
            else:
                counters["assignment_outside_windows"] += 1
    return {
        "calibrationAssignments": calibration_assignments,
        "calibrationLearners": calibration_learners,
        "evaluationLearners": evaluation_learners,
        "counters": counters,
    }


def split_overlapping_learners(
    calibration_learners: Iterable[str],
    evaluation_learners: Iterable[str],
) -> tuple[set[str], set[str]]:
    """Return (excluded, final_calibration) with zero overlap after exclusion."""
    calibration = set(calibration_learners)
    evaluation = set(evaluation_learners)
    excluded = calibration & evaluation
    return excluded, calibration - excluded


def first_graded_pair(
    existing: tuple[datetime, int, bool] | None,
    candidate_timestamp: datetime,
    candidate_ordinal: int,
    candidate_correct: bool,
) -> tuple[datetime, int, bool]:
    """Keep the chronologically first graded outcome; (timestamp, ordinal) order."""
    if existing is None:
        return candidate_timestamp, candidate_ordinal, candidate_correct
    if (candidate_timestamp, candidate_ordinal) < (existing[0], existing[1]):
        return candidate_timestamp, candidate_ordinal, candidate_correct
    return existing


def aggregate_problem_records(
    graded_pairs: Iterable[tuple[str, str, datetime, int, bool]],
    problem_skills: Mapping[str, str | None],
    *,
    release_id: str,
    pseudonym_key: bytes | str,
    calibration_start: datetime = CALIBRATION_WINDOW_START,
    calibration_end: datetime = CALIBRATION_WINDOW_END,
) -> tuple[list[CalibrationProblemRecord], Counter[str]]:
    """Aggregate first-graded (student, problem) outcomes into problem records.

    ``graded_pairs`` are already window/cohort filtered tuples of
    (raw_student_id, raw_problem_id, timestamp, ordinal, correct).
    Problems without an exact non-null sourceSkillCode are excluded from the
    catalog and counted (never assigned a skill).
    """
    first_by_pair: dict[tuple[str, str], tuple[datetime, int, bool]] = {}
    for student_id, problem_id, timestamp, ordinal, correct in graded_pairs:
        if not student_id or not problem_id:
            continue
        key = (str(student_id), str(problem_id))
        first_by_pair[key] = first_graded_pair(
            first_by_pair.get(key), timestamp, ordinal, correct
        )

    grouped: dict[str, list[tuple[str, bool]]] = {}
    for (student_id, problem_id), (timestamp, ordinal, correct) in first_by_pair.items():
        grouped.setdefault(problem_id, []).append((student_id, correct))

    records: list[CalibrationProblemRecord] = []
    counters: Counter[str] = Counter()
    for problem_id, outcomes in sorted(grouped.items()):
        skill_code = problem_skills.get(problem_id)
        if not skill_code:
            counters["problems_null_skill_excluded"] += 1
            continue
        learners = {learner for learner, _correct in outcomes}
        correct_count = sum(1 for _learner, correct in outcomes if correct)
        response_count = len(outcomes)
        p_correct = smoothed_correct_probability(correct_count, response_count)
        difficulty = difficulty_score(correct_count, response_count)
        status = (
            "calibrated"
            if len(learners) >= MINIMUM_CALIBRATION_LEARNERS
            else "insufficient_problem_evidence"
        )
        records.append(
            CalibrationProblemRecord(
                dataset_release_id=release_id,
                external_problem_key=external_pseudonym(
                    "problem", problem_id, pseudonym_key
                ),
                source_skill_code=skill_code,
                calibration_start=calibration_start,
                calibration_end=calibration_end,
                calibration_learner_count=len(learners),
                calibration_response_count=response_count,
                correct_response_count=correct_count,
                smoothed_correct_probability=p_correct,
                difficulty_score=difficulty,
                proxy_difficulty=None,
                calibration_status=status,
                provenance=EXTERNAL_PROVENANCE,
            )
        )
        counters["problems_observed_with_skill"] += 1
        counters["problems_calibrated" if status == "calibrated" else "problems_insufficient"] += 1
    return records, counters


def stream_calibration_graded_pairs(
    action_path: str | Path,
    *,
    allowed_assignments: Mapping[str, str],
    excluded_learners: set[str],
    problem_skills: Mapping[str, str | None],
) -> tuple[list[tuple[str, str, datetime, int, bool]], Counter[str]]:
    """Stream action_logs and emit first-graded (learner, problem) evidence.

    Only rows whose assignment is in ``allowed_assignments`` (exact Grade 6,
    calibration-window assignment start), whose learner is not excluded, whose
    action is an approved graded response, and whose timestamp falls inside the
    calibration window may contribute.  Only problems with an exact non-null
    skill code are tracked.
    """
    import pandas as pd

    eligible: list[tuple[str, str, datetime, int, bool]] = []
    counters: Counter[str] = Counter()
    null_skill_problems: set[str] = set()
    row_ordinal = 0
    for chunk in pd.read_csv(
        action_path,
        dtype=str,
        usecols=["assignment_log_id", "timestamp", "problem_id", "action"],
        chunksize=4_000_000,
    ):
        for offset, (assignment_id, timestamp_value, problem_id, action) in enumerate(
            zip(
                chunk["assignment_log_id"],
                chunk["timestamp"],
                chunk["problem_id"],
                chunk["action"],
            )
        ):
            ordinal = row_ordinal + offset
            counters["action_rows_read"] += 1
            assignment_id = str(assignment_id)
            student_id = allowed_assignments.get(assignment_id)
            if student_id is None:
                counters["action_assignment_not_calibration_grade_six"] += 1
                continue
            if student_id in excluded_learners:
                counters["action_learner_excluded_evaluation_cohort"] += 1
                continue
            timestamp = parse_epoch_seconds(timestamp_value)
            if timestamp is None:
                counters["action_timestamp_unparseable"] += 1
                continue
            if not in_calibration_window(timestamp):
                counters["action_timestamp_outside_calibration_window"] += 1
                continue
            if not is_graded_action(action):
                counters["action_not_graded"] += 1
                continue
            if not problem_id or not str(problem_id):
                counters["action_problem_missing"] += 1
                continue
            if not problem_skills.get(str(problem_id)):
                counters["action_problem_null_skill"] += 1
                null_skill_problems.add(str(problem_id))
                continue
            correct = bool(graded_correctness(action))
            eligible.append((student_id, str(problem_id), timestamp, ordinal, correct))
        row_ordinal += len(chunk)
    counters["problems_null_skill_distinct"] = len(null_skill_problems)
    return eligible, counters


def write_catalog_csv(
    records: Iterable[CalibrationProblemRecord],
    path: str | Path,
) -> Path:
    """Write the protected problem-level catalog deterministically."""
    destination = Path(path)
    rows = sorted(records, key=lambda record: (record.source_skill_code, record.external_problem_key))
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATALOG_FIELDS)
        writer.writeheader()
        for record in rows:
            writer.writerow(record.to_csv_row())
    return destination


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_calibration_manifest(
    *,
    contract_version: str,
    contract_hash: str,
    dataset_release_id: str,
    source_release_hashes: Mapping[str, str],
    calibration_start: datetime,
    calibration_end: datetime,
    evaluation_start: datetime,
    evaluation_end: datetime,
    evaluation_learners_excluded_from_calibration: bool,
    calibration_evaluation_learner_overlap_count: int,
    possible_pre_2022_grade_six_learners: int,
    final_calibration_learner_count: int,
    smoothing_rule: str,
    minimum_calibration_learners: int,
    tiering_scope: str,
    tier_ordering_tie_rule: str,
    tier_algorithm_version: str,
    tier_assignment_status: str,
    tertile_boundary_rule: Mapping[str, object] | None = None,
    predecessor_contract_version: str | None = None,
    predecessor_contract_sha256: str | None = None,
    amendment_reason: str | None = None,
    minimum_problems_per_skill: int,
    minimum_problems_per_tier: int,
    problem_counts: Mapping[str, int],
    skill_counts: Mapping[str, int],
    tier_counts: Mapping[str, int],
    catalog_sha256: str,
) -> dict[str, object]:
    """Deterministic E2 manifest (no timestamps; rerun reproduces the hash)."""
    manifest: dict[str, object] = {
        "manifestSchemaVersion": "assistments-e2-calibration-manifest-v1",
        "contractVersion": contract_version,
        "contractHash": contract_hash,
        "datasetReleaseId": dataset_release_id,
        "sourceReleaseHashes": dict(sorted(source_release_hashes.items())),
        "provenance": EXTERNAL_PROVENANCE,
        "calibrationStart": calibration_start.isoformat(),
        "calibrationEnd": calibration_end.isoformat(),
        "evaluationStart": evaluation_start.isoformat(),
        "evaluationEnd": evaluation_end.isoformat(),
        "evaluationLearnersExcludedFromCalibration": evaluation_learners_excluded_from_calibration,
        "calibrationEvaluationLearnerOverlapCount": calibration_evaluation_learner_overlap_count,
        "possiblePre2022GradeSixLearners": possible_pre_2022_grade_six_learners,
        "finalCalibrationLearnerCount": final_calibration_learner_count,
        "smoothingRule": smoothing_rule,
        "minimumCalibrationLearners": minimum_calibration_learners,
        "tieringScope": tiering_scope,
        "tierOrderingTieRule": tier_ordering_tie_rule,
        "tierAlgorithmVersion": tier_algorithm_version,
        "tierAssignmentStatus": tier_assignment_status,
        "minimumProblemsPerSkill": minimum_problems_per_skill,
        "minimumProblemsPerTier": minimum_problems_per_tier,
        "problemCounts": dict(sorted(problem_counts.items())),
        "skillCounts": dict(sorted(skill_counts.items())),
        "tierCounts": dict(sorted(tier_counts.items())),
        "catalogSha256": catalog_sha256,
        "containsRawIdentifiers": False,
        "productionPromotionAllowed": False,
    }
    if tertile_boundary_rule is not None:
        manifest["tertileBoundaryRule"] = dict(tertile_boundary_rule)
    if predecessor_contract_version is not None:
        manifest["predecessorContractVersion"] = predecessor_contract_version
    if predecessor_contract_sha256 is not None:
        manifest["predecessorContractSha256"] = predecessor_contract_sha256
    if amendment_reason is not None:
        manifest["amendmentReason"] = amendment_reason
    return manifest


def write_manifest(manifest: Mapping[str, object], path: str | Path) -> Path:
    destination = Path(path)
    destination.write_text(
        json.dumps(dict(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return destination
