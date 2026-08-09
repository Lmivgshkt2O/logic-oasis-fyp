"""J2-v2 focused tests: skill-episode semantics, chronology, censors, features."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

import pandas as pd

from external_data.assistments.build_u7_dataset_v2 import MODEL_TABLE_FIELDS, build_v2_rows
from external_data.assistments.j2_contract import (
    J2_CONTRACT_VERSION,
    J2_CONTRACT_VERSION_V2,
    MASTERY_CRITERION,
    MAX_RESPONSE_TIME_MS,
    REASON_IDENTICAL_PROBLEM_SET,
    REASON_NEXT_NOT_OUTCOME_VALID,
    REASON_NO_NEXT,
    load_j2_contract,
    validate_j2_contract,
    validate_j2_contract_v2,
)
from external_data.assistments.skill_episodes import (
    EPISODE_FIELDS,
    LABEL_FIELDS,
    build_episode_pairs,
    build_skill_episodes,
)


BASE = datetime(2022, 1, 1, tzinfo=timezone.utc)
V1_CONTRACT_PATH = Path(__file__).resolve().parents[1] / "external_data" / "assistments" / "assistments_j2_contract_v1.yaml"
V2_CONTRACT_PATH = Path(__file__).resolve().parents[1] / "external_data" / "assistments" / "assistments_j2_contract_v2.yaml"
RELEASE_ID = "assistments-edm-cup-2023-release-test-v1"


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


def build(rows: list[dict]):
    episodes, outcomes, summary = build_skill_episodes(frame(rows), cohort_grades=("6",), release_id=RELEASE_ID)
    pairs, pair_summary = build_episode_pairs(episodes, release_id=RELEASE_ID)
    return episodes, outcomes, summary, pairs, pair_summary


class V2ContractTests(unittest.TestCase):
    def test_v2_contract_validates_and_preserves_v1(self):
        v1 = validate_j2_contract(load_j2_contract(V1_CONTRACT_PATH))
        v2 = validate_j2_contract_v2(load_j2_contract(V2_CONTRACT_PATH))
        self.assertEqual(v1["contractVersion"], J2_CONTRACT_VERSION)
        self.assertEqual(v2["contractVersion"], J2_CONTRACT_VERSION_V2)
        self.assertEqual(v2["predecessor"], J2_CONTRACT_VERSION)
        self.assertEqual(v2["amendment"]["motivatedBy"], "source-semantic-mismatch")
        self.assertIs(v2["amendment"]["notMotivatedByModelPerformance"], True)
        self.assertEqual(v2["compatibilityIdentity"]["v2Rule"], "same externalStudentKey AND exact non-null sourceSkillCode")

    def test_frozen_rules_unchanged_in_v2(self):
        v2 = load_j2_contract(V2_CONTRACT_PATH)
        self.assertEqual(v2["masteryCriterionAndTarget"]["masteryCriterion"], 0.60)
        self.assertEqual(v2["responseTimeQualityRule"]["validRangeMilliseconds"], "0 < response_time_ms <= 1800000")
        self.assertEqual(v2["minimumEpisodeEvidence"]["minimumValidGradedProblems"], 3)
        self.assertEqual(v2["minimumEpisodeEvidence"]["minimumValidResponseTimePairs"], 3)
        self.assertEqual(v2["featureConstruction"]["baseFeatures"], ["correct_rate", "mean_response_time_ms"])
        self.assertEqual(v2["featureConstruction"]["baseSchema"], "quiz-attempt-features-v2")
        self.assertEqual(v2["provenancePrivacy"]["provenance"], "external_real")


class SkillEpisodeSemanticsTests(unittest.TestCase):
    def test_different_skills_never_mix_in_one_episode(self):
        rows = assignment_rows(
            "a1",
            start_offset=0,
            problems=[
                ("p1", "6.RP.A.3b", [(5, "correct_response")]),
                ("p2", "6.RP.A.3b", [(6, "wrong_response")]),
                ("p3", "6.RP.A.3b", [(7, "correct_response")]),
                ("p4", "6.NS.B.2", [(5, "correct_response")]),
                ("p5", "6.NS.B.2", [(6, "correct_response")]),
                ("p6", "6.NS.B.2", [(7, "wrong_response")]),
            ],
            finish_offset=100,
        )
        episodes, _, _, _, _ = build(rows)
        by_skill = {e.externalSkillCode: e for e in episodes}
        self.assertFalse(set(by_skill["6.RP.A.3b"].gradedProblemKeys) & set(by_skill["6.NS.B.2"].gradedProblemKeys))
        self.assertEqual(set(by_skill["6.RP.A.3b"].gradedProblemKeys), {"p1", "p2", "p3"})

    def test_null_skill_never_receives_invented_value(self):
        rows = assignment_rows(
            "a1",
            start_offset=0,
            problems=[
                ("p1", "", [(5, "correct_response")]),
                ("p2", "", [(6, "wrong_response")]),
                ("p3", "", [(7, "correct_response")]),
                ("p4", "6.RP.A.3b", [(5, "correct_response")]),
            ],
            finish_offset=100,
        )
        episodes, _, summary, _, _ = build(rows)
        self.assertTrue(all(e.externalSkillCode != "" for e in episodes))
        self.assertFalse(any("invented" in e.externalSkillCode.lower() for e in episodes))
        self.assertGreaterEqual(summary["nullSkillProblemsExcluded"], 3)
        self.assertEqual(len(episodes), 1)  # only the skill-tagged problems form an episode

    def test_empty_grade_is_not_treated_as_grade_six_cohort(self):
        rows = assignment_rows(
            "a1",
            start_offset=0,
            problems=[("p1", "6.RP.A.3b", [(5, "correct_response")]), ("p2", "6.RP.A.3b", [(6, "wrong_response")]), ("p3", "6.RP.A.3b", [(7, "correct_response")])],
            finish_offset=100,
            grade="",
        )
        episodes, _, _, _, _ = build(rows)
        self.assertEqual(len(episodes), 1)
        self.assertFalse(episodes[0].cohortEligible)
        self.assertFalse(episodes[0].featureValid)

    def test_same_learner_same_skill_across_assignments_form_chronology(self):
        rows = (
            assignment_rows("a1", start_offset=0, problems=[("p1", "6.RP.A.3b", [(5, "correct_response")]), ("p2", "6.RP.A.3b", [(6, "wrong_response")]), ("p3", "6.RP.A.3b", [(7, "correct_response")])], finish_offset=100)
            + assignment_rows("a2", start_offset=200, problems=[("p4", "6.RP.A.3b", [(5, "correct_response")]), ("p5", "6.RP.A.3b", [(6, "correct_response")]), ("p6", "6.RP.A.3b", [(7, "correct_response")])], finish_offset=300)
        )
        episodes, _, _, pairs, pair_summary = build(rows)
        self.assertEqual(len(episodes), 2)
        self.assertEqual(pairs[0].currentEpisodeId, episodes[0].externalEpisodeId)
        self.assertEqual(pairs[0].nextEpisodeId, episodes[1].externalEpisodeId)
        self.assertEqual(pair_summary["labelled_pairs"], 1)

    def test_different_skills_never_form_current_next_pairs(self):
        rows = (
            assignment_rows("a1", start_offset=0, problems=[("p1", "6.RP.A.3b", [(5, "correct_response")]), ("p2", "6.RP.A.3b", [(6, "wrong_response")]), ("p3", "6.RP.A.3b", [(7, "correct_response")])], finish_offset=100)
            + assignment_rows("a2", start_offset=200, problems=[("p4", "6.NS.B.2", [(5, "correct_response")]), ("p5", "6.NS.B.2", [(6, "correct_response")]), ("p6", "6.NS.B.2", [(7, "correct_response")])], finish_offset=300)
        )
        episodes, _, _, pairs, pair_summary = build(rows)
        # Two separate skill chains each with a single episode: no pair forms.
        self.assertEqual(len(pairs), 2)
        self.assertTrue(all(pair.censorReason == REASON_NO_NEXT for pair in pairs))
        self.assertEqual(pair_summary["labelled_pairs"], 0)

    def test_current_features_use_only_current_episode_evidence(self):
        rows = (
            assignment_rows("a1", start_offset=0, problems=[("p1", "6.RP.A.3b", [(5, "correct_response")]), ("p2", "6.RP.A.3b", [(6, "wrong_response")]), ("p3", "6.RP.A.3b", [(7, "correct_response")])], finish_offset=100)
            + assignment_rows("a2", start_offset=200, problems=[("p4", "6.RP.A.3b", [(5, "wrong_response")]), ("p5", "6.RP.A.3b", [(6, "wrong_response")]), ("p6", "6.RP.A.3b", [(7, "wrong_response")])], finish_offset=300)
        )
        episodes, _, _, pairs, _ = build(rows)
        current = next(e for e in episodes if e.externalAssignmentKey == "a1")
        self.assertAlmostEqual(current.correct_rate, 2 / 3)
        self.assertNotIn("p4", current.gradedProblemKeys)
        self.assertIs(pairs[0].next_attempt_support_needed, True)  # next rate 0/3 < 0.60

    def test_next_episode_contributes_only_the_target(self):
        rows = (
            assignment_rows("a1", start_offset=0, problems=[("p1", "6.RP.A.3b", [(5, "correct_response")]), ("p2", "6.RP.A.3b", [(6, "wrong_response")]), ("p3", "6.RP.A.3b", [(7, "correct_response")])], finish_offset=100)
            + assignment_rows("a2", start_offset=200, problems=[("p4", "6.RP.A.3b", [(5, "correct_response")]), ("p5", "6.RP.A.3b", [(6, "correct_response")]), ("p6", "6.RP.A.3b", [(7, "correct_response")])], finish_offset=300)
        )
        episodes, _, _, pairs, _ = build(rows)
        labelled = next(p for p in pairs if p.next_attempt_support_needed is not None)
        current = next(e for e in episodes if e.externalEpisodeId == labelled.currentEpisodeId)
        self.assertEqual(labelled.nextCorrectRate, next(e.correct_rate for e in episodes if e.externalEpisodeId == labelled.nextEpisodeId))
        self.assertIs(labelled.next_attempt_support_needed, False)  # 1.0 >= 0.60
        self.assertEqual((current.correct_rate, current.mean_response_time_ms), (2 / 3, 6_000.0))

    def test_identical_full_problem_sets_remain_censored(self):
        rows = (
            assignment_rows("a1", start_offset=0, problems=[("p1", "6.RP.A.3b", [(5, "correct_response")]), ("p2", "6.RP.A.3b", [(6, "wrong_response")]), ("p3", "6.RP.A.3b", [(7, "correct_response")])], finish_offset=100)
            + assignment_rows("a2", start_offset=200, problems=[("p1", "6.RP.A.3b", [(5, "correct_response")]), ("p2", "6.RP.A.3b", [(6, "wrong_response")]), ("p3", "6.RP.A.3b", [(7, "correct_response")])], finish_offset=300)
        )
        _, _, _, pairs, pair_summary = build(rows)
        self.assertEqual(pairs[0].censorReason, REASON_IDENTICAL_PROBLEM_SET)
        self.assertEqual(pair_summary["identical_problem_set_censors"], 1)

    def test_immediate_next_no_skipping_rule_enforced(self):
        rows = (
            assignment_rows("a1", start_offset=0, problems=[("p1", "6.RP.A.3b", [(5, "correct_response")]), ("p2", "6.RP.A.3b", [(6, "wrong_response")]), ("p3", "6.RP.A.3b", [(7, "correct_response")])], finish_offset=100)
            + assignment_rows("a2", start_offset=200, problems=[("p4", "6.RP.A.3b", [(5, "correct_response")])], finish_offset=300)
            + assignment_rows("a3", start_offset=400, problems=[("p5", "6.RP.A.3b", [(5, "correct_response")]), ("p6", "6.RP.A.3b", [(6, "correct_response")]), ("p7", "6.RP.A.3b", [(7, "correct_response")])], finish_offset=500)
        )
        _, _, _, pairs, pair_summary = build(rows)
        self.assertEqual(pairs[0].censorReason, REASON_NEXT_NOT_OUTCOME_VALID)
        self.assertEqual(pair_summary["next_not_outcome_valid_censors"], 1)

    def test_minimum_evidence_and_30_minute_rule_unchanged(self):
        rows = assignment_rows(
            "a1",
            start_offset=0,
            problems=[
                ("p1", "6.RP.A.3b", [(5, "correct_response")]),
                ("p2", "6.RP.A.3b", [(6, "wrong_response")]),
                ("p3", "6.RP.A.3b", [(1_801, "wrong_response")]),
            ],
            finish_offset=100,
        )
        episodes, _, _, _, _ = build(rows)
        episode = episodes[0]
        self.assertTrue(episode.outcomeValid)  # 3 graded
        self.assertEqual(episode.validResponseTimePairs, 2)  # one >30min censored
        self.assertFalse(episode.featureValid)

    def test_base_features_are_exactly_correct_rate_and_mean_response_time(self):
        self.assertEqual(MODEL_TABLE_FIELDS, ("correct_rate", "mean_response_time_ms", "next_attempt_support_needed"))
        self.assertNotIn("externalSkillCode", MODEL_TABLE_FIELDS)
        self.assertNotIn("sourceGrade", MODEL_TABLE_FIELDS)
        self.assertEqual(MASTERY_CRITERION, 0.60)
        self.assertEqual(MAX_RESPONSE_TIME_MS, 1_800_000)

    def test_v1_contract_file_is_untouched(self):
        self.assertTrue(V1_CONTRACT_PATH.exists())
        v1 = validate_j2_contract(load_j2_contract(V1_CONTRACT_PATH))
        self.assertEqual(v1["contractVersion"], J2_CONTRACT_VERSION)
        self.assertNotIn("v2Unit", v1["attemptUnit"])


if __name__ == "__main__":
    unittest.main()
