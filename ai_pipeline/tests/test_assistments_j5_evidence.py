"""J5 tests: SHAP contract, operational evidence, and BKT lineage/ablation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from logic_oasis_ai.prediction_contract import SupervisedExample

from external_data.assistments.bkt_external import (
    bkt_lineage_gate,
    build_graded_observations,
    build_mastery_at_episodes,
)
from external_data.assistments.run_j5 import (
    BKT_FEATURE_NAME,
    bkt_ablation,
    feature_matrix,
    operational_evidence,
    shap_global_summary,
    shap_local_examples,
)
from training.train_decision_tree import train_decision_tree
from training.train_mlp import train_mlp
from training.train_xgboost import train_xgboost


BASE = datetime(2022, 1, 1, tzinfo=timezone.utc)
EXTERNAL_COLUMNS = ("correct_rate", "mean_response_time_ms")


def external_examples(count: int = 12) -> tuple[SupervisedExample, ...]:
    rows = []
    for index in range(count):
        rate = 0.5 if index % 2 else 0.8
        rows.append(
            SupervisedExample(
                attempt_id=f"ep-{index}",
                student_key=f"s{index % 4}",
                subtopic_id="6.RP.A.3b",
                observed_at=BASE,
                features={"correct_rate": rate, "mean_response_time_ms": 50_000.0 + index * 100},
                target=rate < 0.6,
                contract=None,
                provenance="external_real",
                evaluation_group_key=f"s{index % 4}",
            )
        )
    return tuple(rows)


def action_row(
    action: str,
    offset: float,
    problem: str | None,
    *,
    skill: str = "6.RP.A.3b",
    student: str = "s1",
    assignment: str = "a1",
    sequence: str = "q6",
) -> dict:
    return {
        "sourceTimestamp": (BASE + timedelta(seconds=offset)).isoformat(),
        "sourceActionType": action,
        "externalProblemKey": problem or "",
        "sourceSkillCode": skill,
        "sourceGrade": "6",
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


def skill_episode_rows(
    assignment: str,
    start_offset: float,
    problems: list[tuple[str, list[tuple[float, str]]]],
    *,
    skill: str = "6.RP.A.3b",
    student: str = "s1",
) -> list[dict]:
    rows = [action_row("assignment_started", start_offset, None, skill=skill, student=student, assignment=assignment)]
    for index, (problem, graded) in enumerate(problems):
        problem_start = start_offset + 10 + index * 100
        rows.append(action_row("problem_started", problem_start, problem, skill=skill, student=student, assignment=assignment))
        for seconds_after, action in graded:
            rows.append(action_row(action, problem_start + seconds_after, problem, skill=skill, student=student, assignment=assignment))
    rows.append(action_row("assignment_finished", start_offset + 1000, None, skill=skill, student=student, assignment=assignment))
    return rows


class ShapAndOperationalTests(unittest.TestCase):
    def setUp(self):
        examples = external_examples()
        self.model = train_xgboost(examples, random_seed=20260716)[0]
        self.dt = train_decision_tree(examples, random_seed=20260716)[0]
        self.mlp = train_mlp(examples, random_seed=20260716)[0]
        self.examples = examples

    def test_shap_uses_frozen_xgboost_and_exact_two_features(self):
        summary = shap_global_summary(self.model, self.examples, EXTERNAL_COLUMNS)
        self.assertEqual(summary["featureNames"], ["correct_rate", "mean_response_time_ms"])
        self.assertEqual(set(summary["perFeature"]), set(EXTERNAL_COLUMNS))
        self.assertEqual(summary["rankingByMeanAbsShap"], sorted(EXTERNAL_COLUMNS, key=lambda n: summary["perFeature"][n]["meanAbsShap"], reverse=True))
        self.assertIn("not causal", summary["interpretationBoundary"])

    def test_shap_input_contains_no_audit_metadata(self):
        matrix = feature_matrix(self.examples, EXTERNAL_COLUMNS)
        self.assertEqual(matrix.shape[1], 2)
        self.assertNotIn("externalStudentKey", self.examples[0].features)

    def test_local_examples_are_non_identifying(self):
        exported = shap_local_examples(self.model, self.examples, EXTERNAL_COLUMNS)
        self.assertEqual([item["rule"] for item in exported], ["lowest_predicted_risk", "median_predicted_risk", "highest_predicted_risk"])
        serialized = str(exported)
        self.assertNotIn("ep-", serialized)
        self.assertNotIn("s0", serialized)
        self.assertTrue(all(item["disclaimer"] for item in exported))

    def test_operational_measurements_share_one_input_contract(self):
        evidence = operational_evidence(
            {"decision_tree": self.dt, "xgboost": self.model, "mlp": self.mlp},
            self.examples,
            EXTERNAL_COLUMNS,
        )
        names = {tuple(item["featureNames"]) for item in evidence.values()}
        self.assertEqual(names, {("correct_rate", "mean_response_time_ms")})
        rows = {item["inputRows"] for item in evidence.values()}
        self.assertEqual(len(rows), 1)
        self.assertTrue(all(item["invalidPredictions"] == 0 for item in evidence.values()))
        self.assertTrue(all(item["serializedSizeBytes"] > 0 for item in evidence.values()))


class BktLineageTests(unittest.TestCase):
    def test_chronology_uses_only_past_and_current_responses(self):
        first = skill_episode_rows(
            "a1", 0,
            [("p1", [(5, "correct_response")]), ("p2", [(6, "wrong_response")]), ("p3", [(7, "correct_response")])],
        )
        later = skill_episode_rows(
            "a2", 2000,
            [("p4", [(5, "wrong_response")]), ("p5", [(6, "wrong_response")]), ("p6", [(7, "wrong_response")])],
        )
        observations_only_first, _ = build_graded_observations(first)
        observations_with_later, _ = build_graded_observations(first + later)
        episode_meta = [
            {"currentEpisodeId": "a1-ep", "externalStudentKey": "s1", "externalAssignmentKey": "a1", "externalSkillCode": "6.RP.A.3b"},
            {"currentEpisodeId": "a2-ep", "externalStudentKey": "s1", "externalAssignmentKey": "a2", "externalSkillCode": "6.RP.A.3b"},
        ]
        states_first = build_mastery_at_episodes(observations_only_first, episode_meta[:1])
        states_all = build_mastery_at_episodes(observations_with_later, episode_meta)
        # adding the later episode must not change the earlier episode's state
        self.assertEqual(states_first["a1-ep"].mastery_probability, states_all["a1-ep"].mastery_probability)
        self.assertNotEqual(states_all["a1-ep"].mastery_probability, states_all["a2-ep"].mastery_probability)

    def test_different_skills_never_share_bkt_state(self):
        rows = skill_episode_rows(
            "a1", 0,
            [("p1", [(5, "correct_response")]), ("p2", [(6, "correct_response")]), ("p3", [(7, "correct_response")])],
            skill="6.RP.A.3b",
        ) + skill_episode_rows(
            "a2", 100,
            [("p4", [(5, "wrong_response")]), ("p5", [(6, "wrong_response")]), ("p6", [(7, "wrong_response")])],
            skill="6.NS.B.2",
        )
        observations, _ = build_graded_observations(rows)
        gate = bkt_lineage_gate(observations)
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["learnerSkillStateCount"], 2)
        episode_meta = [
            {"currentEpisodeId": "a1-ep", "externalStudentKey": "s1", "externalAssignmentKey": "a1", "externalSkillCode": "6.RP.A.3b"},
        ]
        states = build_mastery_at_episodes(observations, episode_meta)
        # skill A mastery must not be contaminated by skill B wrong answers
        self.assertEqual(states["a1-ep"].externalSkillCode, "6.RP.A.3b")
        self.assertGreater(states["a1-ep"].mastery_probability, 0.9)

    def test_future_injection_changes_no_earlier_state(self):
        base_rows = skill_episode_rows(
            "a1", 0,
            [("p1", [(5, "correct_response")]), ("p2", [(6, "wrong_response")]), ("p3", [(7, "correct_response")])],
        )
        future_rows = skill_episode_rows(
            "a9", 999_999,
            [("p7", [(5, "correct_response")]), ("p8", [(6, "correct_response")]), ("p9", [(7, "correct_response")])],
        )
        episode_meta = [
            {"currentEpisodeId": "a1-ep", "externalStudentKey": "s1", "externalAssignmentKey": "a1", "externalSkillCode": "6.RP.A.3b"},
        ]
        before = build_mastery_at_episodes(build_graded_observations(base_rows)[0], episode_meta)["a1-ep"]
        injected = build_mastery_at_episodes(build_graded_observations(base_rows + future_rows)[0], episode_meta)["a1-ep"]
        self.assertEqual(before.mastery_probability, injected.mastery_probability)


class BktAblationTests(unittest.TestCase):
    def test_ablation_rows_identical_except_bkt_feature(self):
        examples = tuple(
            SupervisedExample(
                attempt_id=f"ep-{index}",
                student_key=f"s{index % 6}",
                subtopic_id="6.RP.A.3b",
                observed_at=BASE,
                features={"correct_rate": 0.5 if index % 2 else 0.8, "mean_response_time_ms": 50_000.0 + index},
                target=index % 2 == 0,
                contract=None,
                provenance="external_real",
                evaluation_group_key=f"s{index % 6}",
            )
            for index in range(24)
        )
        bkt_rows = {row.attempt_id: {"bkt_mastery_probability": 0.5 + index * 0.001} for index, row in enumerate(examples)}
        train_keys = [f"s{i}" for i in range(6)]
        test_keys = []
        result = bkt_ablation(examples, bkt_rows, train_keys=train_keys, test_keys=test_keys)
        self.assertEqual(result["eligibleRows"], 24)
        self.assertTrue(result["sameRowsIdenticalExceptBkt"])
        self.assertIn("xgboost", result["delta"])
        self.assertIn("roc_auc", result["delta"]["xgboost"])

    def test_no_registry_promotion_path(self):
        source = Path(__file__).resolve().parents[1] / "external_data" / "assistments" / "run_j5.py"
        text = source.read_text(encoding="utf-8")
        self.assertNotIn("ModelRegistry", text)
        self.assertNotIn("registry.", text)


if __name__ == "__main__":
    unittest.main()
