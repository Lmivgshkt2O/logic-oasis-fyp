"""J3A focused tests: skill-episode semantics, leakage, order, censors, gates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

import pandas as pd

from external_data.assistments.j3a_feasibility import (
    assess_candidate_gates,
    build_episode_pairs,
    build_episodes,
)
from external_data.assistments.j2_contract import (
    MASTERY_CRITERION,
    REASON_IDENTICAL_PROBLEM_SET,
    REASON_NEXT_NOT_OUTCOME_VALID,
    REASON_NO_NEXT,
)


BASE = datetime(2022, 1, 1, tzinfo=timezone.utc)


def row(
    action: str,
    offset_seconds: float,
    problem: str | None,
    *,
    skill: str | None = "6.RP.A.3b",
    grade: str = "6",
    student: str = "s1",
    assignment: str = "a1",
    sequence: str = "q6",
) -> dict:
    return {
        "sourceTimestamp": (BASE + timedelta(seconds=offset_seconds)).isoformat(),
        "sourceActionType": action,
        "externalProblemKey": problem or "",
        "sourceSkillCode": skill or "",
        "sourceGrade": grade,
        "sourceSubject": "Mathematics",
        "externalStudentKey": student,
        "externalAssignmentKey": assignment,
        "externalSequenceKey": sequence,
        "provenance": "external_real",
        "sourceDataset": "assistments_edm_cup_2023",
        "sourceWindow": "2022-01-01/2023-12-31",
        "datasetReleaseId": "test",
        "externalContentKey": "",
    }


def assignment_rows(
    assignment: str,
    *,
    start_offset: float,
    problems: list[tuple[str, str, list[tuple[float, str]]]],
    finish_offset: float,
    grade: str = "6",
    student: str = "s1",
    sequence: str = "q6",
) -> list[dict]:
    rows = [row("assignment_started", start_offset, None, grade=grade, student=student, assignment=assignment, sequence=sequence)]
    for index, (problem, skill, graded) in enumerate(problems):
        problem_start = start_offset + 10 + index * 100
        rows.append(row("problem_started", problem_start, problem, skill=skill, grade=grade, student=student, assignment=assignment, sequence=sequence))
        for seconds_after, action in graded:
            rows.append(row(action, problem_start + seconds_after, problem, skill=skill, grade=grade, student=student, assignment=assignment, sequence=sequence))
    rows.append(row("assignment_finished", finish_offset, None, grade=grade, student=student, assignment=assignment, sequence=sequence))
    return rows


def frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


class SkillEpisodeTests(unittest.TestCase):
    def test_skill_episodes_do_not_mix_skills(self):
        rows = assignment_rows(
            "a1",
            start_offset=0,
            problems=[
                ("p1", "6.RP.A.3b", [(5, "correct_response")]),
                ("p2", "6.RP.A.3b", [(6, "wrong_response")]),
                ("p3", "6.RP.A.3b", [(7, "correct_response")]),
                ("p4", "6.NS.B.2", [(8, "correct_response")]),
                ("p5", "6.NS.B.2", [(9, "correct_response")]),
                ("p6", "6.NS.B.2", [(10, "wrong_response")]),
            ],
            finish_offset=100,
        )
        episodes = build_episodes(frame(rows), identity="skill", cohort_grades=("6",), release_id="r")[0]
        by_skill = {e.contentIdentity: e for e in episodes}
        self.assertIn("6.RP.A.3b", by_skill)
        self.assertIn("6.NS.B.2", by_skill)
        rp_keys = set(by_skill["6.RP.A.3b"].gradedProblemKeys)
        ns_keys = set(by_skill["6.NS.B.2"].gradedProblemKeys)
        self.assertFalse(rp_keys & ns_keys)
        self.assertEqual(rp_keys, {"p1", "p2", "p3"})
        self.assertEqual(ns_keys, {"p4", "p5", "p6"})

    def test_future_actions_cannot_enter_current_features(self):
        first = assignment_rows(
            "a1",
            start_offset=0,
            problems=[
                ("p1", "6.RP.A.3b", [(5, "correct_response")]),
                ("p2", "6.RP.A.3b", [(6, "wrong_response")]),
                ("p3", "6.RP.A.3b", [(7, "correct_response")]),
            ],
            finish_offset=100,
        )
        later = assignment_rows(
            "a2",
            start_offset=200,
            problems=[
                ("p4", "6.RP.A.3b", [(205, "wrong_response")]),
                ("p5", "6.RP.A.3b", [(206, "wrong_response")]),
                ("p6", "6.RP.A.3b", [(207, "wrong_response")]),
            ],
            finish_offset=300,
        )
        episodes = build_episodes(frame(first + later), identity="skill", cohort_grades=("6",), release_id="r")[0]
        ordered = sorted(episodes, key=lambda e: e.startedAt)
        self.assertEqual(len(ordered), 2)
        current = ordered[0]
        self.assertAlmostEqual(current.correct_rate, 2 / 3)
        self.assertEqual(set(current.gradedProblemKeys), {"p1", "p2", "p3"})
        self.assertNotIn("p4", current.gradedProblemKeys)

    def test_identical_problem_sets_remain_censored(self):
        rows = (
            assignment_rows(
                "a1",
                start_offset=0,
                problems=[("p1", "6.RP.A.3b", [(5, "correct_response")]), ("p2", "6.RP.A.3b", [(6, "wrong_response")]), ("p3", "6.RP.A.3b", [(7, "correct_response")])],
                finish_offset=100,
            )
            + assignment_rows(
                "a2",
                start_offset=200,
                problems=[("p1", "6.RP.A.3b", [(205, "correct_response")]), ("p2", "6.RP.A.3b", [(206, "wrong_response")]), ("p3", "6.RP.A.3b", [(207, "correct_response")])],
                finish_offset=300,
            )
        )
        episodes = build_episodes(frame(rows), identity="skill", cohort_grades=("6",), release_id="r")[0]
        pairs, summary = build_episode_pairs(episodes, identity_field="contentIdentity")
        self.assertEqual(len(pairs), 2)  # identical-set censor + trailing no-next censor
        self.assertEqual(pairs[0].censorReason, REASON_IDENTICAL_PROBLEM_SET)
        self.assertEqual(summary["identical_problem_set_censors"], 1)

    def test_minimum_evidence_rules_are_independent_per_skill_episode(self):
        two_graded = assignment_rows(
            "a1",
            start_offset=0,
            problems=[
                ("p1", "6.RP.A.3b", [(5, "correct_response")]),
                ("p2", "6.RP.A.3b", [(6, "wrong_response")]),
            ],
            finish_offset=100,
        )
        episodes = build_episodes(frame(two_graded), identity="skill", cohort_grades=("6",), release_id="r")[0]
        self.assertFalse(episodes[0].outcomeValid)
        self.assertEqual(episodes[0].censorReason, "insufficient_valid_graded_problems")

        rows = assignment_rows(
            "a3",
            start_offset=0,
            problems=[
                ("p1", "6.RP.A.3b", [(5, "correct_response")]),
                ("p2", "6.RP.A.3b", [(6, "wrong_response")]),
                ("p3", "6.RP.A.3b", [(1_801, "wrong_response")]),
            ],
            finish_offset=100,
        )
        episodes = build_episodes(frame(rows), identity="skill", cohort_grades=("6",), release_id="r")[0]
        self.assertTrue(episodes[0].outcomeValid)
        self.assertEqual(episodes[0].validResponseTimePairs, 2)
        self.assertFalse(episodes[0].featureValid)

    def test_no_next_episode_is_censored(self):
        rows = assignment_rows(
            "a1",
            start_offset=0,
            problems=[("p1", "6.RP.A.3b", [(5, "correct_response")]), ("p2", "6.RP.A.3b", [(6, "wrong_response")]), ("p3", "6.RP.A.3b", [(7, "correct_response")])],
            finish_offset=100,
        )
        episodes = build_episodes(frame(rows), identity="skill", cohort_grades=("6",), release_id="r")[0]
        pairs, summary = build_episode_pairs(episodes, identity_field="contentIdentity")
        self.assertEqual(pairs[0].censorReason, REASON_NO_NEXT)
        self.assertEqual(summary["no_next_censors"], 1)

    def test_mastery_criterion_stays_zero_six(self):
        self.assertEqual(MASTERY_CRITERION, 0.60)
        rows = (
            assignment_rows(
                "a1",
                start_offset=0,
                problems=[("p1", "6.RP.A.3b", [(5, "correct_response")]), ("p2", "6.RP.A.3b", [(6, "wrong_response")]), ("p3", "6.RP.A.3b", [(7, "correct_response")])],
                finish_offset=100,
            )
            + assignment_rows(
                "a2",
                start_offset=200,
                problems=[
                    ("p4", "6.RP.A.3b", [(5, "correct_response")]),
                    ("p5", "6.RP.A.3b", [(6, "correct_response")]),
                    ("p6", "6.RP.A.3b", [(7, "wrong_response")]),
                    ("p7", "6.RP.A.3b", [(8, "wrong_response")]),
                    ("p8", "6.RP.A.3b", [(9, "wrong_response")]),
                ],
                finish_offset=300,
            )
        )
        episodes = build_episodes(frame(rows), identity="skill", cohort_grades=("6",), release_id="r")[0]
        pairs, _ = build_episode_pairs(episodes, identity_field="contentIdentity")
        self.assertIs(pairs[0].next_attempt_support_needed, True)  # next rate 3/5 < 0.60

    def test_order_is_deterministic(self):
        rows = (
            assignment_rows(
                "a1",
                start_offset=0,
                problems=[("p1", "6.RP.A.3b", [(5, "correct_response")]), ("p2", "6.RP.A.3b", [(6, "wrong_response")]), ("p3", "6.RP.A.3b", [(7, "correct_response")])],
                finish_offset=100,
            )
            + assignment_rows(
                "a2",
                start_offset=200,
                problems=[("p4", "6.RP.A.3b", [(205, "correct_response")]), ("p5", "6.RP.A.3b", [(206, "correct_response")]), ("p6", "6.RP.A.3b", [(207, "correct_response")])],
                finish_offset=300,
            )
        )
        episodes = build_episodes(frame(rows), identity="skill", cohort_grades=("6",), release_id="r")[0]
        first = build_episode_pairs(episodes, identity_field="contentIdentity")[0]
        second = build_episode_pairs(episodes, identity_field="contentIdentity")[0]
        self.assertEqual([(p.currentEpisodeId, p.nextEpisodeId, p.next_attempt_support_needed) for p in first],
                         [(p.currentEpisodeId, p.nextEpisodeId, p.next_attempt_support_needed) for p in second])

    def test_no_model_training_code_is_invoked(self):
        source = Path(__file__).resolve().parents[1] / "external_data" / "assistments" / "j3a_feasibility.py"
        text = source.read_text(encoding="utf-8")
        for forbidden in ("train_decision_tree", "train_xgboost", "train_mlp", "evaluate_models", "sklearn", "xgboost"):
            self.assertNotIn(forbidden, text, f"J3A module must not reference {forbidden}")
        gates = assess_candidate_gates([])
        self.assertEqual(gates["claimLevel"], "NO_GATE")


if __name__ == "__main__":
    unittest.main()
