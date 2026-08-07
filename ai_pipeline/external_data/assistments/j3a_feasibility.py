"""J3A diagnostic: content-compatibility amendment feasibility analysis.

Diagnostic only.  No model is trained, no metrics are produced, and the frozen
J2 contract is NOT modified.  Candidate A maps the prediction unit to one
learner + exact source skill episode; Candidate B (cluster family) is evaluated
only when A is structurally unusable; Candidate C is sensitivity-only.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import pandas as pd

from logic_oasis_ai.prediction_contract import SupervisedExample

from .assistments_contract import PROVENANCE, SOURCE_DATASET
from .j2_contract import (
    MASTERY_CRITERION,
    MAX_RESPONSE_TIME_MS,
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
from .reconstruct_attempts import _normalize_rows, _outcome_from_normalized, read_action_rows
from training.common import grouped_binary_holdout_split, grouped_holdout_split


SPLIT_SEED = 20260716


def skill_code_of(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def cluster_of(skill_code: str) -> str:
    parts = skill_code.split(".")
    return ".".join(parts[:3]) if len(parts) >= 3 else skill_code


def domain_of(skill_code: str) -> str:
    parts = skill_code.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else skill_code


IDENTITY_FUNCTIONS: dict[str, Callable[[str], str]] = {
    "skill": lambda code: code,
    "cluster": cluster_of,
    "domain": domain_of,
}


@dataclass(frozen=True)
class EpisodeRecord:
    episode_id: str
    externalStudentKey: str
    externalAssignmentKey: str
    externalSequenceKey: str
    contentIdentity: str
    sourceGrade: str | None
    startedAt: datetime | None
    endedAt: datetime | None
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
    censorReason: str | None


def episode_id(learner: str, assignment: str, identity: str) -> str:
    digest = sha256(f"{learner}|{assignment}|{identity}".encode("utf-8")).hexdigest()
    return f"assistments_episode_{digest}"


def build_episodes(
    frame: pd.DataFrame,
    *,
    identity: str,
    cohort_grades: Sequence[str],
    release_id: str,
) -> tuple[list[EpisodeRecord], Counter[str]]:
    """Reconstruct learner+content episodes inside completed assignments."""
    identity_fn = IDENTITY_FUNCTIONS[identity]
    episodes: list[EpisodeRecord] = []
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
        cohort_eligible = grades.issubset(set(cohort_grades)) and subjects == {PRIMARY_SUBJECT}
        grade = grades.pop() if len(grades) == 1 else None

        problems: dict[str, list[Mapping[str, Any]]] = {}
        for row in rows:
            if row["problem_key"] is not None:
                problems.setdefault(row["problem_key"], []).append(row)

        buckets: dict[str, list[Any]] = {}
        for problem_rows in problems.values():
            outcome = _outcome_from_normalized(problem_rows)
            skill = skill_code_of(problem_rows[0].get("skill_code"))
            if skill is None:
                summary["problemsWithoutSkill"] += 1
                continue
            key = identity_fn(skill)
            buckets.setdefault(key, []).append(outcome)
            summary["eligibleProblemResponses"] += 1

        for content_identity, outcomes in buckets.items():
            graded = [o for o in outcomes if o.graded]
            timing = [o for o in outcomes if o.responseTimeStatus == RT_VALID]
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
                    episode_id=episode_id(first["student_key"], first["assignment_key"], content_identity),
                    externalStudentKey=first["student_key"],
                    externalAssignmentKey=first["assignment_key"],
                    externalSequenceKey=first["sequence_key"],
                    contentIdentity=content_identity,
                    sourceGrade=grade,
                    startedAt=started_at,
                    endedAt=ended_at,
                    completed=completed,
                    cohortEligible=cohort_eligible,
                    problemCount=len(outcomes),
                    gradedProblemCount=graded_count,
                    correctFirstResponseCount=correct_count,
                    correct_rate=correct_rate,
                    validResponseTimePairs=len(timing),
                    mean_response_time_ms=mean_rt,
                    gradedProblemKeys=tuple(sorted(o.externalProblemKey for o in graded)),
                    outcomeValid=validity,
                    featureValid=feature_valid,
                    censorReason=reason,
                )
            )
    return episodes, summary


@dataclass(frozen=True)
class EpisodePair:
    currentEpisodeId: str
    externalStudentKey: str
    contentIdentity: str
    currentStartedAt: datetime | None
    nextEpisodeId: str | None
    nextCorrectRate: float | None
    next_attempt_support_needed: bool | None
    censorReason: str | None


def build_episode_pairs(
    episodes: Sequence[EpisodeRecord],
    *,
    identity_field: str,
) -> tuple[list[EpisodePair], Counter[str]]:
    """Immediate later valid episode pairing per learner + content identity."""
    summary: Counter[str] = Counter()
    pairs: list[EpisodePair] = []
    grouped: dict[tuple[str, str], list[EpisodeRecord]] = {}
    for episode in episodes:
        grouped.setdefault((episode.externalStudentKey, getattr(episode, identity_field)), []).append(episode)

    for key in sorted(grouped):
        ordered = sorted(grouped[key], key=lambda e: (e.startedAt or datetime.max, e.externalAssignmentKey))
        for index, current in enumerate(ordered):
            if not current.featureValid:
                continue
            next_episode = ordered[index + 1] if index + 1 < len(ordered) else None
            if next_episode is None:
                pairs.append(_pair(current, None, REASON_NO_NEXT))
                summary["no_next_censors"] += 1
                continue
            summary["candidate_pairs"] += 1
            if current.startedAt is not None and current.startedAt == next_episode.startedAt:
                pairs.append(_pair(current, next_episode, REASON_CHRONOLOGY_AMBIGUOUS))
                summary["chronology_ambiguous_censors"] += 1
                continue
            if not next_episode.outcomeValid:
                pairs.append(_pair(current, next_episode, REASON_NEXT_NOT_OUTCOME_VALID))
                summary["next_not_outcome_valid_censors"] += 1
                continue
            current_keys = set(current.gradedProblemKeys)
            next_keys = set(next_episode.gradedProblemKeys)
            if current_keys and current_keys == next_keys:
                pairs.append(_pair(current, next_episode, REASON_IDENTICAL_PROBLEM_SET))
                summary["identical_problem_set_censors"] += 1
                continue
            if next_episode.correct_rate is None:
                pairs.append(_pair(current, next_episode, REASON_NEXT_NOT_OUTCOME_VALID))
                summary["next_not_outcome_valid_censors"] += 1
                continue
            target = next_episode.correct_rate < MASTERY_CRITERION
            pairs.append(
                EpisodePair(
                    currentEpisodeId=current.episode_id,
                    externalStudentKey=current.externalStudentKey,
                    contentIdentity=getattr(current, identity_field),
                    currentStartedAt=current.startedAt,
                    nextEpisodeId=next_episode.episode_id,
                    nextCorrectRate=next_episode.correct_rate,
                    next_attempt_support_needed=target,
                    censorReason=None,
                )
            )
            summary["labelled_pairs"] += 1
            summary[f"target_{str(target).lower()}"] += 1
    return pairs, summary


def _pair(
    current: EpisodeRecord,
    next_episode: EpisodeRecord | None,
    reason: str,
) -> EpisodePair:
    return EpisodePair(
        currentEpisodeId=current.episode_id,
        externalStudentKey=current.externalStudentKey,
        contentIdentity=current.contentIdentity,
        currentStartedAt=current.startedAt,
        nextEpisodeId=next_episode.episode_id if next_episode else None,
        nextCorrectRate=next_episode.correct_rate if next_episode else None,
        next_attempt_support_needed=None,
        censorReason=reason,
    )


def feasibility_summary(
    episodes: Sequence[EpisodeRecord],
    pairs: Sequence[EpisodePair],
    problem_summary: Counter[str],
    *,
    cohort_label: str,
) -> dict[str, Any]:
    outcome_valid = [e for e in episodes if e.outcomeValid]
    feature_valid = [e for e in episodes if e.featureValid]
    labelled = [p for p in pairs if p.next_attempt_support_needed is not None]
    true_learners = {p.externalStudentKey for p in labelled if p.next_attempt_support_needed}
    false_learners = {p.externalStudentKey for p in labelled if not p.next_attempt_support_needed}
    return {
        "cohort": cohort_label,
        "eligibleProblemResponses": sum(e.problemCount for e in episodes),
        "skillGroups": len({e.contentIdentity for e in episodes}),
        "uniqueLearners": len({e.externalStudentKey for e in episodes}),
        "reconstructedEpisodes": len(episodes),
        "outcomeValidEpisodes": len(outcome_valid),
        "featureValidEpisodes": len(feature_valid),
        "candidatePairs": sum(1 for p in pairs if p.censorReason is not None and p.censorReason != REASON_NO_NEXT or p.next_attempt_support_needed is not None),
        "identicalProblemSetCensors": sum(1 for p in pairs if p.censorReason == REASON_IDENTICAL_PROBLEM_SET),
        "nextNotOutcomeValidCensors": sum(1 for p in pairs if p.censorReason == REASON_NEXT_NOT_OUTCOME_VALID),
        "noNextCensors": sum(1 for p in pairs if p.censorReason == REASON_NO_NEXT),
        "chronologyAmbiguities": sum(1 for p in pairs if p.censorReason == REASON_CHRONOLOGY_AMBIGUOUS),
        "labelledPairs": len(labelled),
        "targetTrue": sum(1 for p in labelled if p.next_attempt_support_needed),
        "targetFalse": sum(1 for p in labelled if not p.next_attempt_support_needed),
        "learnersWithLabelledPairs": len({p.externalStudentKey for p in labelled}),
        "learnersTrueClass": len(true_learners),
        "learnersFalseClass": len(false_learners),
        "problemsWithoutSkill": problem_summary.get("problemsWithoutSkill", 0),
    }


def assess_candidate_gates(pairs: Sequence[EpisodePair]) -> dict[str, Any]:
    labelled = [p for p in pairs if p.next_attempt_support_needed is not None]
    if not labelled:
        return {"claimLevel": "NO_GATE", "gate": "none", "reason": "zero labelled pairs", "canCompare": False}
    targets = Counter(bool(p.next_attempt_support_needed) for p in labelled)
    true_learners = {p.externalStudentKey for p in labelled if p.next_attempt_support_needed}
    false_learners = {p.externalStudentKey for p in labelled if not p.next_attempt_support_needed}
    learners = true_learners | false_learners
    if len(targets) < 2 or not true_learners or not false_learners:
        return {"claimLevel": "PIPELINE_DEMO", "gate": "pipeline_demo", "reason": "both target classes across multiple learners required", "canCompare": False}
    if len(learners) < 2:
        return {"claimLevel": "PIPELINE_DEMO", "gate": "pipeline_demo", "reason": "grouped validation requires more than one learner", "canCompare": False}
    examples = tuple(
        SupervisedExample(
            attempt_id=p.currentEpisodeId,
            student_key=p.externalStudentKey,
            subtopic_id=p.contentIdentity,
            observed_at=p.currentStartedAt or datetime.now(),
            features={"correct_rate": 0.0, "mean_response_time_ms": 1.0},
            target=bool(p.next_attempt_support_needed),
            contract=None,
            provenance=PROVENANCE,
            evaluation_group_key=p.externalStudentKey,
        )
        for p in labelled
    )
    try:
        grouped_holdout_split(examples, random_seed=SPLIT_SEED)
    except ValueError:
        return {"claimLevel": "PIPELINE_DEMO", "gate": "pipeline_demo", "reason": "student-grouped validation split not feasible", "canCompare": False}
    if grouped_binary_holdout_split(examples, random_seed=SPLIT_SEED) is None:
        return {"claimLevel": "PRELIMINARY_COMPARISON", "gate": "preliminary_comparison", "reason": "no held-out split with both classes", "canCompare": True}
    return {"claimLevel": "POTENTIAL_HELD_OUT_COMPARISON", "gate": "held_out_comparison", "reason": "student-grouped held-out split feasible", "canCompare": True}


def candidate_c_sensitivity(j2_labels_path: str | Path) -> dict[str, Any]:
    """Candidate C: descriptive counts of identical-set sequence-level pairs."""
    labels = pd.read_csv(j2_labels_path, dtype=str, keep_default_na=False)
    identical = labels[labels["censorReason"] == REASON_IDENTICAL_PROBLEM_SET]
    next_rate = pd.to_numeric(identical["nextCorrectRate"], errors="coerce")
    below = int((next_rate < MASTERY_CRITERION).sum())
    above = int((next_rate >= MASTERY_CRITERION).sum())
    return {
        "identicalProblemSetPairs": len(identical),
        "nextRateBelowMastery": below,
        "nextRateAtOrAboveMastery": above,
        "limitation": "same-question retest evidence does not demonstrate generalization to a fresh compatible problem set",
    }


def run_analysis(
    action_rows_path: str | Path,
    *,
    identity: str,
    cohort_grades: Sequence[str],
    release_id: str,
) -> dict[str, Any]:
    frame = read_action_rows(action_rows_path)
    episodes, problem_summary = build_episodes(
        frame,
        identity=identity,
        cohort_grades=cohort_grades,
        release_id=release_id,
    )
    cohort_episodes = [episode for episode in episodes if episode.cohortEligible]
    pairs, _ = build_episode_pairs(cohort_episodes, identity_field="contentIdentity")
    cohort_label = "Grade 6" if tuple(cohort_grades) == ("6",) else "Grades 4-6"
    return {
        "identity": identity,
        "cohort": cohort_label,
        "summary": feasibility_summary(cohort_episodes, pairs, problem_summary, cohort_label=cohort_label),
        "gates": assess_candidate_gates(pairs),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="J3A compatibility feasibility (diagnostic only)")
    parser.add_argument("--action-rows", required=True)
    parser.add_argument("--processed-dir", required=True, help="Protected J3A output directory")
    parser.add_argument("--identity", default="skill", choices=sorted(IDENTITY_FUNCTIONS))
    parser.add_argument("--cohort-grades", default="6")
    parser.add_argument("--j2-labels-g6", help="Protected J2 Grade 6 labels CSV for Candidate C")
    parser.add_argument("--j2-labels-fallback", help="Protected J2 Grades 4-6 labels CSV for Candidate C")
    parser.add_argument("--release-id", default="assistments-edm-cup-2023-release-v1")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    processed = Path(args.processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    out_path = processed / f"j3a_{args.identity}_{args.cohort_grades.replace(',', '_')}.json"
    if out_path.exists() and not args.force:
        raise FileExistsError("protected J3A outputs are immutable; use --force")

    cohort_grades = tuple(grade.strip() for grade in args.cohort_grades.split(",") if grade.strip())
    result = run_analysis(
        args.action_rows,
        identity=args.identity,
        cohort_grades=cohort_grades,
        release_id=args.release_id,
    )
    if args.j2_labels_g6 or args.j2_labels_fallback:
        result["candidateC"] = {
            "grade6": candidate_c_sensitivity(args.j2_labels_g6) if args.j2_labels_g6 else None,
            "grades456": candidate_c_sensitivity(args.j2_labels_fallback) if args.j2_labels_fallback else None,
        }
    result["diagnosticOnly"] = True
    result["contractUnchanged"] = "assistments-j2-attempt-label-contract-v1"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    print(f"written: {out_path}")


if __name__ == "__main__":
    main()
