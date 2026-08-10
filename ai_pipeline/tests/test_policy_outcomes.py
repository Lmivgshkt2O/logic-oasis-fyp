from __future__ import annotations

from datetime import timedelta
import unittest

from logic_oasis_ai.prediction_contract import PredictionContract
from logic_oasis_ai.sources.firestore_source import load_firestore_dataset

from evaluation.manifest import OutcomeWindow
from evaluation.outcomes import CENSORED, OBSERVED, attach_outcomes
from policy_fixtures import (
    START,
    attempt_document,
    build_dataset,
    full_bank_catalog,
    response_documents,
)

from test_policy_replay import replayed


WINDOW = OutcomeWindow(max_later_attempts=5, max_calendar_duration_days=90)


class PolicyOutcomeTests(unittest.TestCase):
    def test_first_later_attempt_is_observed_and_support_needed_is_labeled(self):
        dataset = build_dataset(
            [
                {
                    "attempt_id": "a1",
                    "student_id": "student-a",
                    "difficulty": "Easy",
                    "sequence": 1,
                    "correct_count": 5,
                },
                {
                    "attempt_id": "a2",
                    "student_id": "student-a",
                    "difficulty": "Moderate",
                    "bank_id": "moderate-1",
                    "sequence": 2,
                    "correct_count": 2,
                    "finalized_at": START + timedelta(days=1),
                },
            ]
        )
        outcomes = attach_outcomes(
            replayed(dataset, bank_catalog=full_bank_catalog()),
            dataset,
            contract=PredictionContract(),
            outcome_window=WINDOW,
        )
        p1_first = next(
            outcome
            for outcome in outcomes.outcomes
            if outcome.source_attempt_id == "a1" and outcome.arm.value == "P1"
        )
        self.assertEqual(p1_first.outcome_status, OBSERVED)
        self.assertTrue(p1_first.observed_assignment_matched)
        self.assertIs(p1_first.support_needed, True)
        self.assertEqual(p1_first.stratum, "same_bank")
        self.assertEqual(p1_first.delivered_difficulty.value, "Moderate")

    def test_counterfactual_difficulty_mismatch_is_censored_not_scored(self):
        dataset = build_dataset(
            [
                {
                    "attempt_id": "c1",
                    "student_id": "student-c",
                    "difficulty": "Easy",
                    "sequence": 1,
                    "correct_count": 5,
                },
                {
                    "attempt_id": "c2",
                    "student_id": "student-c",
                    "difficulty": "Easy",
                    "bank_id": "easy-2",
                    "sequence": 2,
                    "correct_count": 3,
                    "finalized_at": START + timedelta(days=1),
                },
            ]
        )
        outcomes = attach_outcomes(
            replayed(dataset, bank_catalog=full_bank_catalog()),
            dataset,
            contract=PredictionContract(),
            outcome_window=WINDOW,
        )
        p1_first = next(
            outcome
            for outcome in outcomes.outcomes
            if outcome.source_attempt_id == "c1" and outcome.arm.value == "P1"
        )
        self.assertEqual(p1_first.outcome_status, CENSORED)
        self.assertEqual(p1_first.censored_reason, "counterfactual_difficulty_mismatch")
        self.assertIsNone(p1_first.support_needed)

    def test_no_later_attempt_is_censored(self):
        dataset = build_dataset(
            [
                {
                    "attempt_id": "d1",
                    "student_id": "student-d",
                    "difficulty": "Easy",
                    "sequence": 1,
                    "correct_count": 4,
                }
            ]
        )
        outcomes = attach_outcomes(
            replayed(dataset), dataset, contract=PredictionContract(), outcome_window=WINDOW
        )
        for outcome in outcomes.outcomes:
            self.assertEqual(outcome.outcome_status, CENSORED)
            self.assertEqual(outcome.censored_reason, "no_later_attempt")

    def test_immediate_question_repeat_is_censored(self):
        first = attempt_document("r1", "student-r", sequence=1, correct_count=4)
        second = attempt_document(
            "r2",
            "student-r",
            bank_id="easy-2",
            sequence=2,
            correct_count=4,
            finalized_at=START + timedelta(days=1),
        )
        first_responses = response_documents(
            "r1", "student-r", session_id=first["sessionId"], correct_count=4
        )
        second_responses = response_documents(
            "r2", "student-r", session_id=second["sessionId"], correct_count=4
        )
        # Force an identical question across attempts.
        second_responses[0]["questionId"] = first_responses[0]["questionId"]
        dataset = load_firestore_dataset(
            [first, second], first_responses + second_responses, provenance="real"
        )
        outcomes = attach_outcomes(
            replayed(dataset, bank_catalog=full_bank_catalog()),
            dataset,
            contract=PredictionContract(),
            outcome_window=WINDOW,
        )
        for outcome in outcomes.outcomes:
            if outcome.source_attempt_id == "r1":
                self.assertEqual(outcome.censored_reason, "immediate_question_repeat")

    def test_incompatible_curriculum_transition_is_censored(self):
        dataset = build_dataset(
            [
                {
                    "attempt_id": "e1",
                    "student_id": "student-e",
                    "difficulty": "Easy",
                    "sequence": 1,
                    "correct_count": 4,
                },
                {
                    "attempt_id": "e2",
                    "student_id": "student-e",
                    "difficulty": "Moderate",
                    "bank_id": "moderate-1",
                    "sequence": 2,
                    "correct_count": 4,
                    "finalized_at": START + timedelta(days=1),
                    "skill_id": "different-skill",
                },
            ]
        )
        outcomes = attach_outcomes(
            replayed(dataset), dataset, contract=PredictionContract(), outcome_window=WINDOW
        )
        for outcome in outcomes.outcomes:
            if outcome.source_attempt_id == "e1":
                self.assertEqual(outcome.censored_reason, "incompatible_curriculum")

    def test_calendar_outcome_window_bounds_are_enforced(self):
        dataset = build_dataset(
            [
                {
                    "attempt_id": "f1",
                    "student_id": "student-f",
                    "difficulty": "Easy",
                    "sequence": 1,
                    "correct_count": 5,
                },
                {
                    "attempt_id": "f2",
                    "student_id": "student-f",
                    "difficulty": "Moderate",
                    "bank_id": "moderate-1",
                    "sequence": 2,
                    "correct_count": 3,
                    "finalized_at": START + timedelta(days=120),
                },
            ]
        )
        narrow_window = OutcomeWindow(max_later_attempts=5, max_calendar_duration_days=30)
        outcomes = attach_outcomes(
            replayed(dataset),
            dataset,
            contract=PredictionContract(),
            outcome_window=narrow_window,
        )
        for outcome in outcomes.outcomes:
            if outcome.source_attempt_id == "f1":
                self.assertEqual(outcome.censored_reason, "no_later_attempt_in_window")

    def test_every_censor_reason_produces_a_counted_non_scored_audit_row(self):
        dataset = build_dataset(
            [
                {
                    "attempt_id": "g1",
                    "student_id": "student-g",
                    "difficulty": "Easy",
                    "sequence": 1,
                    "correct_count": 5,
                },
                {
                    "attempt_id": "g2",
                    "student_id": "student-g",
                    "difficulty": "Easy",
                    "bank_id": "easy-2",
                    "sequence": 2,
                    "correct_count": 3,
                    "finalized_at": START + timedelta(days=1),
                },
            ]
        )
        result = attach_outcomes(
            replayed(dataset, bank_catalog=full_bank_catalog()),
            dataset,
            contract=PredictionContract(),
            outcome_window=WINDOW,
        )
        censored_outcomes = [
            outcome for outcome in result.outcomes if outcome.outcome_status == CENSORED
        ]
        self.assertTrue(censored_outcomes)
        for outcome in censored_outcomes:
            self.assertIsNone(outcome.support_needed)
        reasons = {row.reason for row in result.censoring_audit}
        self.assertIn("counterfactual_difficulty_mismatch", reasons)
        self.assertIn("no_later_attempt", reasons)
        self.assertEqual(
            len(result.censoring_audit),
            sum(1 for outcome in result.outcomes if outcome.outcome_status == CENSORED),
        )

    def test_same_and_cross_bank_strata_are_reported_separately(self):
        dataset = build_dataset(
            [
                {
                    "attempt_id": "h1",
                    "student_id": "student-h",
                    "difficulty": "Easy",
                    "sequence": 1,
                    "correct_count": 5,
                },
                {
                    "attempt_id": "h2",
                    "student_id": "student-h",
                    "difficulty": "Moderate",
                    "bank_id": "moderate-2",
                    "sequence": 2,
                    "correct_count": 3,
                    "finalized_at": START + timedelta(days=1),
                },
                {
                    "attempt_id": "h3",
                    "student_id": "student-h",
                    "difficulty": "Moderate",
                    "bank_id": "moderate-1",
                    "sequence": 3,
                    "correct_count": 4,
                    "finalized_at": START + timedelta(days=2),
                },
            ]
        )
        outcomes = attach_outcomes(
            replayed(dataset, bank_catalog=full_bank_catalog()),
            dataset,
            contract=PredictionContract(),
            outcome_window=WINDOW,
        )
        observed = [outcome for outcome in outcomes.outcomes if outcome.outcome_status == OBSERVED]
        self.assertTrue(any(outcome.stratum == "same_bank" for outcome in observed))
        self.assertTrue(any(outcome.stratum == "cross_bank" for outcome in observed))


if __name__ == "__main__":
    unittest.main()
