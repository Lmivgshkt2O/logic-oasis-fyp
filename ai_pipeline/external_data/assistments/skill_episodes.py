"""V2 production core: learner + exact-skill episode reconstruction and pairing.

Implements the approved ``assistments-j2-attempt-label-contract-v2`` delta:
one episode per ``externalStudentKey + externalAssignmentKey + exact
non-null sourceSkillCode``, using only that skill's responses inside the
completed assignment.  All other frozen J2 rules are unchanged.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any, Mapping, Sequence

import pandas as pd

from .assistments_contract import PROVENANCE, SOURCE_DATASET
from .j2_contract import (
    MASTERY_CRITERION,
    MIN_VALID_GRADED_PROBLEMS,
    MIN_VALID_RESPONSE_TIME_PAIRS,
    PRIMARY_SUBJECT,
    REASON_CHRONOLOGY_AMBIGUOUS,
    REASON_IDENTICAL_PROBLEM_SET,
    REASON_INCOMPLETE,
    REASON_INSUFFICIENT_GRADED,
    REASON_INSUFFICIENT_TIMING,
    REASON_NEXT_NOT_OUTCOME_VALID,
    REASON_NO_NEXT,
    REASON_NOT_PRIMARY_COHORT,
    RT_VALID,
)
from .reconstruct_attempts import _normalize_rows, _outcome_from_normalized


EPISODE_FIELDS = (
    "datasetReleaseId",
    "externalEpisodeId",
    "externalStudentKey",
    "externalAssignmentKey",
    "externalSequenceKey",
    "externalSkillCode",
    "externalContentKey",
    "sourceGrade",
    "sourceSubject",
    "episodeStartedAt",
    "episodeEndedAt",
    "completed",
    "cohortEligible",
    "problemCount",
    "gradedProblemCount",
    "correctFirstResponseCount",
    "correct_rate",
    "validResponseTimePairs",
    "mean_response_time_ms",
    "gradedProblemKeys",
    "outcomeValid",
    "featureValid",
    "episodeCensorReason",
    "provenance",
    "sourceDataset",
)

PROBLEM_OUTCOME_FIELDS = (
    "externalStudentKey",
    "externalAssignmentKey",
    "externalSequenceKey",
    "externalSkillCode",
    "externalProblemKey",
    "hasStart",
    "multipleStarts",
    "graded",
    "correct",
    "responseTimeMs",
    "responseTimeStatus",
)

LABEL_FIELDS = (
    "datasetReleaseId",
    "currentEpisodeId",
    "externalStudentKey",
    "externalSkillCode",
    "currentEpisodeStartedAt",
    "nextEpisodeId",
    "nextEpisodeStartedAt",
    "nextCorrectRate",
    "next_attempt_support_needed",
    "censorReason",
    "problemOverlapRate",
    "provenance",
    "sourceDataset",
)


def content_key_of(skill_code: str) -> str:
    digest = sha256(f"assistments_skill:{skill_code}".encode("utf-8")).hexdigest()
    return f"assistments_content_{digest}"


@dataclass(frozen=True)
class EpisodeRecord:
    datasetReleaseId: str
    externalEpisodeId: str
    externalStudentKey: str
    externalAssignmentKey: str
    externalSequenceKey: str
    externalSkillCode: str
    externalContentKey: str
    sourceGrade: str | None
    sourceSubject: str | None
    episodeStartedAt: datetime | None
    episodeEndedAt: datetime | None
    completed: bool
    cohortEligible: bool
    problemCount: int
    gradedProblemCount: int
    correctFirstResponseCount: int
    correct_rate: float | None
    validResponseTimePairs: int
    mean_response_time_ms: float | None
    gradedProblemKeys: tuple[str, ...]
    outcomeValid: bool
    featureValid: bool
    episodeCensorReason: str | None

    @property
    def provenance(self) -> str:
        return PROVENANCE

    @property
    def sourceDataset(self) -> str:
        return SOURCE_DATASET

    def to_csv_row(self) -> dict[str, object]:
        return {
            "datasetReleaseId": self.datasetReleaseId,
            "externalEpisodeId": self.externalEpisodeId,
            "externalStudentKey": self.externalStudentKey,
            "externalAssignmentKey": self.externalAssignmentKey,
            "externalSequenceKey": self.externalSequenceKey,
            "externalSkillCode": self.externalSkillCode,
            "externalContentKey": self.externalContentKey,
            "sourceGrade": self.sourceGrade or "",
            "sourceSubject": self.sourceSubject or "",
            "episodeStartedAt": self.episodeStartedAt.isoformat() if self.episodeStartedAt else "",
            "episodeEndedAt": self.episodeEndedAt.isoformat() if self.episodeEndedAt else "",
            "completed": self.completed,
            "cohortEligible": self.cohortEligible,
            "problemCount": self.problemCount,
            "gradedProblemCount": self.gradedProblemCount,
            "correctFirstResponseCount": self.correctFirstResponseCount,
            "correct_rate": "" if self.correct_rate is None else round(self.correct_rate, 8),
            "validResponseTimePairs": self.validResponseTimePairs,
            "mean_response_time_ms": "" if self.mean_response_time_ms is None else round(self.mean_response_time_ms, 8),
            "gradedProblemKeys": "|".join(self.gradedProblemKeys),
            "outcomeValid": self.outcomeValid,
            "featureValid": self.featureValid,
            "episodeCensorReason": self.episodeCensorReason or "",
            "provenance": self.provenance,
            "sourceDataset": self.sourceDataset,
        }


def episode_id(learner: str, assignment: str, skill_code: str) -> str:
    digest = sha256(f"{learner}|{assignment}|{skill_code}".encode("utf-8")).hexdigest()
    return f"assistments_episode_{digest}"


def build_skill_episodes(
    frame: pd.DataFrame,
    *,
    cohort_grades: Sequence[str],
    release_id: str,
) -> tuple[list[EpisodeRecord], list[dict[str, Any]], Counter[str]]:
    """Reconstruct learner+skill episodes and per-problem outcomes."""
    episodes: list[EpisodeRecord] = []
    outcomes: list[dict[str, Any]] = []
    summary: Counter[str] = Counter()

    for _, group in frame.groupby(["externalAssignmentKey"], observed=True, sort=False):
        rows = _normalize_rows(group.to_dict("records"))
        if not rows:
            continue
        first = rows[0]
        start_times = [r["timestamp"] for r in rows if r["action"] == "assignment_started"]
        if not start_times:
            summary["assignmentsExcludedNoInWindowStart"] += 1
            continue
        started_at = min(start_times)
        finish_times = [r["timestamp"] for r in rows if r["action"] == "assignment_finished" and r["timestamp"] > started_at]
        completed = bool(finish_times)
        ended_at = max(finish_times) if finish_times else None
        grades = {r["grade"] for r in rows if r["grade"]}
        subjects = {r["subject"] for r in rows if r["subject"]}
        cohort_eligible = bool(grades) and grades.issubset(set(cohort_grades)) and subjects == {PRIMARY_SUBJECT}
        grade = grades.pop() if len(grades) == 1 else None
        subject = subjects.pop() if len(subjects) == 1 else None

        problems: dict[str, list[Mapping[str, Any]]] = {}
        for row in rows:
            if row["problem_key"] is not None:
                problems.setdefault(row["problem_key"], []).append(row)

        buckets: dict[str, list[Any]] = {}
        for problem_rows in problems.values():
            outcome = _outcome_from_normalized(problem_rows)
            skill = str(problem_rows[0].get("skill_code") or "").strip() or None
            if skill is None:
                summary["nullSkillProblemsExcluded"] += 1
                continue
            buckets.setdefault(skill, []).append(outcome)
            outcomes.append(
                {
                    "externalStudentKey": first["student_key"],
                    "externalAssignmentKey": first["assignment_key"],
                    "externalSequenceKey": first["sequence_key"],
                    "externalSkillCode": skill,
                    "externalProblemKey": outcome.externalProblemKey,
                    "hasStart": outcome.hasStart,
                    "multipleStarts": outcome.multipleStarts,
                    "graded": outcome.graded,
                    "correct": outcome.correct,
                    "responseTimeMs": outcome.responseTimeMs,
                    "responseTimeStatus": outcome.responseTimeStatus,
                }
            )

        for skill_code, skill_outcomes in buckets.items():
            graded = [o for o in skill_outcomes if o.graded]
            timing = [o for o in skill_outcomes if o.responseTimeStatus == RT_VALID]
            graded_count = len(graded)
            correct_count = sum(1 for o in graded if o.correct)
            correct_rate = correct_count / graded_count if graded_count else None
            mean_rt = sum(o.responseTimeMs for o in timing) / len(timing) if timing else None

            if not completed:
                validity, reason = False, REASON_INCOMPLETE
            elif not cohort_eligible:
                validity, reason = False, REASON_NOT_PRIMARY_COHORT
            elif graded_count < MIN_VALID_GRADED_PROBLEMS:
                validity, reason = False, REASON_INSUFFICIENT_GRADED
            else:
                validity, reason = True, None
            feature_valid = validity and len(timing) >= MIN_VALID_RESPONSE_TIME_PAIRS
            if validity and not feature_valid:
                reason = REASON_INSUFFICIENT_TIMING

            episodes.append(
                EpisodeRecord(
                    datasetReleaseId=release_id,
                    externalEpisodeId=episode_id(first["student_key"], first["assignment_key"], skill_code),
                    externalStudentKey=first["student_key"],
                    externalAssignmentKey=first["assignment_key"],
                    externalSequenceKey=first["sequence_key"],
                    externalSkillCode=skill_code,
                    externalContentKey=content_key_of(skill_code),
                    sourceGrade=grade,
                    sourceSubject=subject,
                    episodeStartedAt=started_at,
                    episodeEndedAt=ended_at,
                    completed=completed,
                    cohortEligible=cohort_eligible,
                    problemCount=len(skill_outcomes),
                    gradedProblemCount=graded_count,
                    correctFirstResponseCount=correct_count,
                    correct_rate=correct_rate,
                    validResponseTimePairs=len(timing),
                    mean_response_time_ms=mean_rt,
                    gradedProblemKeys=tuple(sorted(o.externalProblemKey for o in graded)),
                    outcomeValid=validity,
                    featureValid=feature_valid,
                    episodeCensorReason=reason,
                )
            )
    return episodes, outcomes, summary


@dataclass(frozen=True)
class EpisodePair:
    datasetReleaseId: str
    currentEpisodeId: str
    externalStudentKey: str
    externalSkillCode: str
    currentEpisodeStartedAt: datetime | None
    nextEpisodeId: str | None
    nextEpisodeStartedAt: datetime | None
    nextCorrectRate: float | None
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
            "currentEpisodeId": self.currentEpisodeId,
            "externalStudentKey": self.externalStudentKey,
            "externalSkillCode": self.externalSkillCode,
            "currentEpisodeStartedAt": self.currentEpisodeStartedAt.isoformat() if self.currentEpisodeStartedAt else "",
            "nextEpisodeId": self.nextEpisodeId or "",
            "nextEpisodeStartedAt": self.nextEpisodeStartedAt.isoformat() if self.nextEpisodeStartedAt else "",
            "nextCorrectRate": "" if self.nextCorrectRate is None else round(self.nextCorrectRate, 8),
            "next_attempt_support_needed": "" if self.next_attempt_support_needed is None else str(self.next_attempt_support_needed).lower(),
            "censorReason": self.censorReason or "",
            "problemOverlapRate": "" if self.problemOverlapRate is None else round(self.problemOverlapRate, 8),
            "provenance": self.provenance,
            "sourceDataset": self.sourceDataset,
        }


def build_episode_pairs(
    episodes: Sequence[EpisodeRecord],
    *,
    release_id: str,
) -> tuple[list[EpisodePair], Counter[str]]:
    """Immediate later compatible skill episode pairing per learner + skill."""
    summary: Counter[str] = Counter()
    pairs: list[EpisodePair] = []
    grouped: dict[tuple[str, str], list[EpisodeRecord]] = {}
    for episode in episodes:
        grouped.setdefault((episode.externalStudentKey, episode.externalSkillCode), []).append(episode)

    for key in sorted(grouped):
        ordered = sorted(grouped[key], key=lambda e: (e.episodeStartedAt or datetime.max, e.externalAssignmentKey))
        for index, current in enumerate(ordered):
            if not current.featureValid:
                continue
            next_episode = ordered[index + 1] if index + 1 < len(ordered) else None
            if next_episode is None:
                pairs.append(_pair(current, None, REASON_NO_NEXT, release_id))
                summary["no_next_censors"] += 1
                continue
            summary["candidate_pairs"] += 1
            if current.episodeStartedAt is not None and current.episodeStartedAt == next_episode.episodeStartedAt:
                pairs.append(_pair(current, next_episode, REASON_CHRONOLOGY_AMBIGUOUS, release_id))
                summary["chronology_ambiguous_censors"] += 1
                continue
            if not next_episode.outcomeValid:
                pairs.append(_pair(current, next_episode, REASON_NEXT_NOT_OUTCOME_VALID, release_id))
                summary["next_not_outcome_valid_censors"] += 1
                continue
            current_keys = set(current.gradedProblemKeys)
            next_keys = set(next_episode.gradedProblemKeys)
            if current_keys and current_keys == next_keys:
                pairs.append(_pair(current, next_episode, REASON_IDENTICAL_PROBLEM_SET, release_id))
                summary["identical_problem_set_censors"] += 1
                continue
            if next_episode.correct_rate is None:
                pairs.append(_pair(current, next_episode, REASON_NEXT_NOT_OUTCOME_VALID, release_id))
                summary["next_not_outcome_valid_censors"] += 1
                continue
            target = next_episode.correct_rate < MASTERY_CRITERION
            pairs.append(
                EpisodePair(
                    datasetReleaseId=release_id,
                    currentEpisodeId=current.externalEpisodeId,
                    externalStudentKey=current.externalStudentKey,
                    externalSkillCode=current.externalSkillCode,
                    currentEpisodeStartedAt=current.episodeStartedAt,
                    nextEpisodeId=next_episode.externalEpisodeId,
                    nextEpisodeStartedAt=next_episode.episodeStartedAt,
                    nextCorrectRate=next_episode.correct_rate,
                    next_attempt_support_needed=target,
                    censorReason=None,
                    problemOverlapRate=_overlap_rate(current_keys, next_keys),
                )
            )
            summary["labelled_pairs"] += 1
            summary[f"target_{str(target).lower()}"] += 1
    return pairs, summary


def _pair(
    current: EpisodeRecord,
    next_episode: EpisodeRecord | None,
    reason: str,
    release_id: str,
) -> EpisodePair:
    return EpisodePair(
        datasetReleaseId=release_id,
        currentEpisodeId=current.externalEpisodeId,
        externalStudentKey=current.externalStudentKey,
        externalSkillCode=current.externalSkillCode,
        currentEpisodeStartedAt=current.episodeStartedAt,
        nextEpisodeId=next_episode.externalEpisodeId if next_episode else None,
        nextEpisodeStartedAt=next_episode.episodeStartedAt if next_episode else None,
        nextCorrectRate=next_episode.correct_rate if next_episode else None,
        next_attempt_support_needed=None,
        censorReason=reason,
        problemOverlapRate=None,
    )


def _overlap_rate(current: set[str], next_: set[str]) -> float:
    if not current or not next_:
        return 0.0
    return len(current & next_) / min(len(current), len(next_))
