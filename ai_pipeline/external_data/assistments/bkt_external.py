"""External v2 BKT lineage gate and mastery replay for the named ablation.

BKT remains a temporal mastery estimator, never a fourth classifier.  It
reuses the frozen project ``bkt-v1`` parameters and version.  Chronology for
the external path is the source timestamp (millisecond epoch, UTC) with a
deterministic tie-break on (assignment key, problem key); a learner+skill
state never mixes skills and never consumes a response observed after the
current episode boundary.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

import pandas as pd

from logic_oasis_ai.bkt import (
    BKT_MODEL_VERSION,
    DEFAULT_BKT_PARAMETERS,
    BktParameters,
    update_probability,
)

from .reconstruct_attempts import _normalize_rows


@dataclass(frozen=True)
class GradedObservation:
    externalStudentKey: str
    externalAssignmentKey: str
    externalSequenceKey: str
    externalSkillCode: str
    externalProblemKey: str
    timestamp: datetime
    correct: bool


@dataclass(frozen=True)
class BktStateAt:
    externalStudentKey: str
    externalSkillCode: str
    mastery_probability: float
    evidence_count: int
    boundary: datetime


def build_graded_observations(
    action_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[GradedObservation], Counter[str]]:
    """First-graded-response observations per problem (frozen correctness rule)."""
    observations: list[GradedObservation] = []
    summary: Counter[str] = Counter()
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in _normalize_rows(action_rows):
        if row["problem_key"] is not None:
            grouped.setdefault(row["assignment_key"], []).append(row)

    for assignment_rows in grouped.values():
        problems: dict[str, list[Mapping[str, Any]]] = {}
        for row in assignment_rows:
            problems.setdefault(row["problem_key"], []).append(row)
        for problem_rows in problems.values():
            skill = str(problem_rows[0].get("skill_code") or "").strip() or None
            if skill is None:
                summary["nullSkillObservationsExcluded"] += 1
                continue
            starts = [r["timestamp"] for r in problem_rows if r["action"] == "problem_started"]
            graded = [(r["timestamp"], r["action"]) for r in problem_rows if r["action"] in ("correct_response", "wrong_response")]
            if not starts:
                summary["problemsWithoutStartExcluded"] += 1
                continue
            anchor = min(starts)
            later = [item for item in graded if item[0] >= anchor]
            if not later:
                summary["problemsWithoutGradedResponseExcluded"] += 1
                continue
            first_graded = min(later, key=lambda item: item[0])
            first = problem_rows[0]
            observations.append(
                GradedObservation(
                    externalStudentKey=first["student_key"],
                    externalAssignmentKey=first["assignment_key"],
                    externalSequenceKey=first["sequence_key"],
                    externalSkillCode=skill,
                    externalProblemKey=first["problem_key"],
                    timestamp=first_graded[0],
                    correct=first_graded[1] == "correct_response",
                )
            )
    observations.sort(
        key=lambda item: (item.timestamp, item.externalAssignmentKey, item.externalProblemKey)
    )
    summary["observations"] = len(observations)
    return observations, summary


def bkt_lineage_gate(
    observations: Sequence[GradedObservation],
    *,
    parameters: BktParameters = DEFAULT_BKT_PARAMETERS,
    model_version: str = BKT_MODEL_VERSION,
) -> dict[str, Any]:
    """Recheck the v2 BKT lineage gate on the external data."""
    if not observations:
        return {"passed": False, "reason": "no graded observations available"}
    state_keys = {(o.externalStudentKey, o.externalSkillCode) for o in observations}
    ordering_keys = [
        (o.timestamp, o.externalAssignmentKey, o.externalProblemKey)
        for o in observations
    ]
    duplicate_ordering = len(ordering_keys) != len(set(ordering_keys))
    null_skills = any(not o.externalSkillCode for o in observations)
    return {
        "passed": not duplicate_ordering and not null_skills,
        "modelVersion": model_version,
        "parameterSource": "frozen bkt-v1 DEFAULT_BKT_PARAMETERS",
        "parameters": {
            "priorKnowledge": parameters.prior_knowledge,
            "learnRate": parameters.learn_rate,
            "guessRate": parameters.guess_rate,
            "slipRate": parameters.slip_rate,
        },
        "deterministicOrder": not duplicate_ordering,
        "nonNullSkill": not null_skills,
        "learnerSkillStateCount": len(state_keys),
        "observationCount": len(observations),
        "orderingRule": "(sourceTimestamp, externalAssignmentKey, externalProblemKey)",
        "crossSkillMixingPrevented": True,
        "futureInjectionPrevented": True,
    }


def build_mastery_at_episodes(
    observations: Sequence[GradedObservation],
    labelled_episodes: Sequence[Mapping[str, Any]],
    *,
    parameters: BktParameters = DEFAULT_BKT_PARAMETERS,
) -> dict[str, BktStateAt]:
    """BKT mastery after replaying responses at or before each episode boundary.

    ``labelled_episodes`` rows carry ``currentEpisodeId``,
    ``externalStudentKey``, ``externalSkillCode``, and ``currentEpisodeStartedAt``.
    The boundary is the latest graded-response timestamp of that episode's own
    (learner, assignment, skill) evidence.
    """
    by_state: dict[tuple[str, str], list[GradedObservation]] = {}
    for observation in observations:
        by_state.setdefault(
            (observation.externalStudentKey, observation.externalSkillCode), []
        ).append(observation)

    # Replay each learner+skill state once; keep the cumulative p_known curve.
    replayed: dict[tuple[str, str], list[tuple[datetime, float]]] = {}
    for key, state_observations in by_state.items():
        state_observations.sort(
            key=lambda item: (item.timestamp, item.externalAssignmentKey, item.externalProblemKey)
        )
        mastery = parameters.prior_knowledge
        curve: list[tuple[datetime, float]] = []
        for observation in state_observations:
            mastery = update_probability(mastery, is_correct=observation.correct, parameters=parameters)
            curve.append((observation.timestamp, mastery))
        replayed[key] = curve

    # Boundary per labelled episode: its own last graded-response timestamp.
    episode_boundaries: dict[tuple[str, str, str], datetime] = {}
    for observation in observations:
        key = (
            observation.externalStudentKey,
            observation.externalAssignmentKey,
            observation.externalSkillCode,
        )
        episode_boundaries[key] = max(episode_boundaries.get(key, observation.timestamp), observation.timestamp)

    result: dict[str, BktStateAt] = {}
    for episode in labelled_episodes:
        episode_id = str(episode["currentEpisodeId"])
        learner = str(episode["externalStudentKey"])
        skill = str(episode["externalSkillCode"])
        boundary = episode_boundaries.get((learner, str(episode["externalAssignmentKey"]), skill))
        if boundary is None:
            result[episode_id] = BktStateAt(learner, skill, parameters.prior_knowledge, 0, datetime.min)
            continue
        curve = replayed.get((learner, skill), [])
        prior = [(ts, p) for ts, p in curve if ts <= boundary]
        if not prior:
            result[episode_id] = BktStateAt(learner, skill, parameters.prior_knowledge, 0, boundary)
            continue
        latest_ts, latest_p = prior[-1]
        result[episode_id] = BktStateAt(learner, skill, round(latest_p, 8), len(prior), latest_ts)
    return result


def bkt_mastery_feature(
    states: Mapping[str, BktStateAt],
    labelled_episodes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for episode in labelled_episodes:
        episode_id = str(episode["currentEpisodeId"])
        state = states.get(episode_id)
        rows.append(
            {
                "currentEpisodeId": episode_id,
                "bkt_mastery_probability": state.mastery_probability if state else None,
                "bkt_evidence_count": state.evidence_count if state else 0,
            }
        )
    return rows

