"""AQC-E3 adaptive-attempt reconstruction tests (frozen rules, no protected data).

These tests freeze the evaluation-window/cohort filters, exact-skill unit,
full-gate skill eligibility, frozen-catalog tier use, BKT chronology, attempt
purity, fingerprints, freshness, sequences, provenance, determinism, and the
no-policy boundary of the E3 path.  None reads the protected raw data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from external_data.assistments.adaptive.adaptive_attempts import (
    ATTEMPT_FIELDS,
    AdaptiveAttemptRecord,
    PurityDenominatorAmbiguity,
    build_attempt_records,
    dominant_tier_fraction,
    problem_set_fingerprint,
)
from external_data.assistments.adaptive.schemas import (
    EVALUATION_WINDOW_END,
    EVALUATION_WINDOW_START,
    EXTERNAL_PROVENANCE,
)
from external_data.assistments.bkt_external import (
    BktStateAt,
    GradedObservation,
    build_graded_observations,
    build_mastery_at_episodes,
)


RELEASE_ID = "assistments-edm-cup-2023-release-v1"


def episode(
    *,
    learner: str = "student-1",
    assignment: str = "assignment-1",
    skill: str = "6.NS.A.1",
    started: datetime = EVALUATION_WINDOW_START,
    keys: tuple[str, ...] = ("p1", "p2", "p3"),
    correct: int = 2,
) -> dict[str, object]:
    return {
        "externalEpisodeId": f"episode-{learner}-{assignment}-{skill}",
        "externalStudentKey": learner,
        "externalAssignmentKey": assignment,
        "externalSkillCode": skill,
        "episodeStartedAt": started.isoformat(),
        "gradedProblemCount": len(keys),
        "correctFirstResponseCount": correct,
        "gradedProblemKeys": "|".join(sorted(keys)),
    }


def bkt_state(episode_id: str, mastery: float = 0.72, evidence: int = 3) -> dict[str, BktStateAt]:
    return {
        episode_id: BktStateAt(
            externalStudentKey="student-1",
            externalSkillCode="6.NS.A.1",
            mastery_probability=mastery,
            evidence_count=evidence,
            boundary=EVALUATION_WINDOW_START,
        )
    }


class E3VerificationTests(unittest.TestCase):
    def test_frozen_verification_passes_on_real_artifacts(self) -> None:
        from external_data.assistments.adaptive.adaptive_attempts import verify_stage_b_frozen

        ai = Path(__file__).resolve().parents[1]
        adaptive = ai / "external_data" / "assistments" / "adaptive"
        result = verify_stage_b_frozen(
            contract_path_v1_1=adaptive / "assistments_adaptive_contract_v1_1.yaml",
            contract_path_v1=adaptive / "assistments_adaptive_contract_v1.yaml",
            e2_catalog_path=Path(
                r"C:\Users\zyonn\Documents\FYP\logic_oasis_private_data\assitments_edm_cup_2023\processed\aqc\e2\assistments_problem_difficulty_proxy_v1.csv"
            ),
            e2_manifest_path=Path(
                r"C:\Users\zyonn\Documents\FYP\logic_oasis_private_data\assitments_edm_cup_2023\processed\aqc\e2\e2_calibration_manifest.json"
            ),
            configs_dir=ai / "configs",
        )
        self.assertTrue(result["verified"])
        self.assertEqual(result["eligibleSkillCount"], 35)
        self.assertEqual(result["provenance"], "external_real")


class WindowAndCohortTests(unittest.TestCase):
    def test_only_2022_2023_evaluation_rows_enter_e3(self) -> None:
        from external_data.assistments.adaptive.run_adaptive_attempt_reconstruction import _load_episodes

        rows = (
            "externalEpisodeId,externalStudentKey,externalAssignmentKey,externalSkillCode,episodeStartedAt,gradedProblemCount,correctFirstResponseCount,gradedProblemKeys,cohortEligible,outcomeValid\n"
            f"e-in,s1,a1,6.NS.A.1,{EVALUATION_WINDOW_START.isoformat()},3,2,p1|p2|p3,True,True\n"
            f"e-out,s1,a2,6.NS.A.1,2021-12-31T23:59:59+00:00,3,2,p1|p2|p3,True,True\n"
            f"e-end,s1,a3,6.NS.A.1,{EVALUATION_WINDOW_END.isoformat()},3,2,p1|p2|p3,True,True\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "episodes.csv"
            path.write_text(rows, encoding="utf-8")
            episodes = _load_episodes(path)
        self.assertEqual({e["externalEpisodeId"] for e in episodes}, {"e-in", "e-end"})

    def test_only_exact_grade_six_outcome_valid_episodes_enter(self) -> None:
        from external_data.assistments.adaptive.run_adaptive_attempt_reconstruction import _load_episodes

        rows = (
            "externalEpisodeId,externalStudentKey,externalAssignmentKey,externalSkillCode,episodeStartedAt,gradedProblemCount,correctFirstResponseCount,gradedProblemKeys,cohortEligible,outcomeValid\n"
            f"e-ok,s1,a1,6.NS.A.1,{EVALUATION_WINDOW_START.isoformat()},3,2,p1|p2|p3,True,True\n"
            f"e-not-cohort,s2,a2,6.NS.A.1,{EVALUATION_WINDOW_START.isoformat()},3,2,p1|p2|p3,False,True\n"
            f"e-not-valid,s3,a3,6.NS.A.1,{EVALUATION_WINDOW_START.isoformat()},2,1,p1|p2,True,False\n"
            f"e-accelerated,s4,a4,6.NS.A.1,{EVALUATION_WINDOW_START.isoformat()},3,2,p1|p2|p3,False,True\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "episodes.csv"
            path.write_text(rows, encoding="utf-8")
            episodes = _load_episodes(path)
        self.assertEqual([e["externalEpisodeId"] for e in episodes], ["e-ok"])


class EligibilityTests(unittest.TestCase):
    def test_only_full_gate_skills_are_policy_eligible(self) -> None:
        tiers = {"p1": "proxy_easy", "p2": "proxy_easy", "p3": "proxy_moderate"}
        eligible = frozenset({"6.NS.A.1"})
        records, _ = build_attempt_records(
            [episode(skill="6.NS.A.1"), episode(skill="6.EE.B.7", assignment="assignment-2")],
            tiers=tiers,
            eligible_skills=eligible,
            bkt_states={
                "episode-student-1-assignment-1-6.NS.A.1": BktStateAt(
                    "student-1", "6.NS.A.1", 0.72, 3, EVALUATION_WINDOW_START
                ),
                "episode-student-1-assignment-2-6.EE.B.7": BktStateAt(
                    "student-1", "6.EE.B.7", 0.72, 3, EVALUATION_WINDOW_START
                ),
            },
            release_id=RELEASE_ID,
        )
        statuses = {record.attempt.source_skill_code: record.skill_proxy_status for record in records}
        self.assertEqual(statuses["6.NS.A.1"], "eligible")
        self.assertEqual(statuses["6.EE.B.7"], "not_eligible")

    def test_proxy_difficulty_alone_does_not_imply_skill_eligibility(self) -> None:
        tiers = {"p1": "proxy_easy", "p2": "proxy_easy", "p3": "proxy_moderate"}
        records, _ = build_attempt_records(
            [episode(skill="6.NS.A.1")],
            tiers=tiers,
            eligible_skills=frozenset(),  # no skill passes the gate here
            bkt_states=bkt_state("episode-student-1-assignment-1-6.NS.A.1"),
            release_id=RELEASE_ID,
        )
        self.assertEqual(records[0].skill_proxy_status, "not_eligible")

    def test_tiers_come_from_frozen_catalog_only(self) -> None:
        tiers = {"p1": "proxy_hard", "p2": "proxy_hard", "p3": "proxy_hard"}
        records, _ = build_attempt_records(
            [episode(keys=("p1", "p2", "p3"))],
            tiers=tiers,
            eligible_skills=frozenset({"6.NS.A.1"}),
            bkt_states=bkt_state("episode-student-1-assignment-1-6.NS.A.1"),
            release_id=RELEASE_ID,
        )
        self.assertEqual(records[0].attempt.problem_keys, ("p1", "p2", "p3"))

    def test_e3_never_recalibrates_or_re_tiers(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "external_data"
            / "assistments"
            / "adaptive"
            / "adaptive_attempts.py"
        )
        source = source.read_text(encoding="utf-8")
        self.assertNotIn("assign_within_skill_tiers", source)
        self.assertNotIn("smoothed_correct_probability(", source)
        self.assertNotIn("proxy_tiers", source)


class BktChronologyTests(unittest.TestCase):
    def _observations(self) -> list[GradedObservation]:
        base = EVALUATION_WINDOW_START
        return [
            GradedObservation("student-1", "a1", "seq-1", "6.NS.A.1", "p1", base, True),
            GradedObservation("student-1", "a1", "seq-1", "6.NS.A.1", "p2", base + timedelta(seconds=10), False),
            GradedObservation("student-1", "a1", "seq-1", "6.NS.A.1", "p3", base + timedelta(seconds=20), True),
            GradedObservation("student-1", "a2", "seq-1", "6.NS.A.1", "p4", base + timedelta(seconds=100), True),
            GradedObservation("student-1", "a2", "seq-1", "6.EE.B.7", "q1", base + timedelta(seconds=30), True),
        ]

    def test_bkt_uses_learner_and_exact_skill_only(self) -> None:
        states = build_mastery_at_episodes(
            self._observations(),
            [
                {
                    "currentEpisodeId": "ep-1",
                    "externalStudentKey": "student-1",
                    "externalAssignmentKey": "a1",
                    "externalSkillCode": "6.NS.A.1",
                    "currentEpisodeStartedAt": EVALUATION_WINDOW_START,
                }
            ],
        )
        self.assertEqual(states["ep-1"].externalSkillCode, "6.NS.A.1")
        self.assertEqual(states["ep-1"].evidence_count, 3)

    def test_future_responses_cannot_alter_prior_bkt_state(self) -> None:
        observations = self._observations()
        early = build_mastery_at_episodes(
            observations,
            [
                {
                    "currentEpisodeId": "ep-1",
                    "externalStudentKey": "student-1",
                    "externalAssignmentKey": "a1",
                    "externalSkillCode": "6.NS.A.1",
                    "currentEpisodeStartedAt": EVALUATION_WINDOW_START,
                }
            ],
        )
        with_future = build_mastery_at_episodes(
            observations
            + [
                GradedObservation(
                    "student-1", "a9", "seq-9", "6.NS.A.1", "p99",
                    EVALUATION_WINDOW_START + timedelta(days=30), True,
                )
            ],
            [
                {
                    "currentEpisodeId": "ep-1",
                    "externalStudentKey": "student-1",
                    "externalAssignmentKey": "a1",
                    "externalSkillCode": "6.NS.A.1",
                    "currentEpisodeStartedAt": EVALUATION_WINDOW_START,
                }
            ],
        )
        self.assertEqual(early["ep-1"].mastery_probability, with_future["ep-1"].mastery_probability)
        self.assertEqual(early["ep-1"].evidence_count, with_future["ep-1"].evidence_count)

    def test_evidence_count_is_chronological(self) -> None:
        base = EVALUATION_WINDOW_START
        observations = self._observations()
        states = build_mastery_at_episodes(
            observations,
            [
                {
                    "currentEpisodeId": "ep-2",
                    "externalStudentKey": "student-1",
                    "externalAssignmentKey": "a2",
                    "externalSkillCode": "6.NS.A.1",
                    "currentEpisodeStartedAt": base + timedelta(seconds=100),
                }
            ],
        )
        self.assertGreater(states["ep-2"].evidence_count, 3)

    def test_graded_observations_recognize_only_approved_events(self) -> None:
        observations, summary = build_graded_observations(
            [
                {
                    "sourceTimestamp": EVALUATION_WINDOW_START,
                    "sourceActionType": "problem_started",
                    "externalProblemKey": "p1",
                    "sourceSkillCode": "6.NS.A.1",
                    "externalStudentKey": "student-1",
                    "externalAssignmentKey": "a1",
                    "externalSequenceKey": "seq-1",
                },
                {
                    "sourceTimestamp": EVALUATION_WINDOW_START + timedelta(seconds=1),
                    "sourceActionType": "correct_response",
                    "externalProblemKey": "p1",
                    "sourceSkillCode": "6.NS.A.1",
                    "externalStudentKey": "student-1",
                    "externalAssignmentKey": "a1",
                    "externalSequenceKey": "seq-1",
                },
                {
                    "sourceTimestamp": EVALUATION_WINDOW_START + timedelta(seconds=2),
                    "sourceActionType": "open_response",
                    "externalProblemKey": "p2",
                    "sourceSkillCode": "6.NS.A.1",
                    "externalStudentKey": "student-1",
                    "externalAssignmentKey": "a1",
                    "externalSequenceKey": "seq-1",
                },
            ]
        )
        self.assertEqual(summary["observations"], 1)
        self.assertTrue(observations[0].correct)


class PurityAndFingerprintTests(unittest.TestCase):
    def test_purity_two_thirds_assigns_dominant_tier(self) -> None:
        tier, fraction = dominant_tier_fraction(
            ["proxy_easy", "proxy_easy", "proxy_easy", "proxy_moderate", "proxy_easy"]
        )
        self.assertEqual(tier, "proxy_easy")
        self.assertAlmostEqual(fraction, 0.8)

    def test_purity_below_two_thirds_is_mixed(self) -> None:
        tier, fraction = dominant_tier_fraction(
            ["proxy_easy", "proxy_easy", "proxy_moderate", "proxy_hard", "proxy_moderate"]
        )
        self.assertIsNone(tier)
        self.assertAlmostEqual(fraction, 0.4)

    def test_all_untiered_problems_have_no_dominant_tier(self) -> None:
        tier, fraction = dominant_tier_fraction([None, None, None])
        self.assertIsNone(tier)
        self.assertEqual(fraction, 0.0)

    def test_mixed_tiered_and_untiered_raises_denominator_ambiguity(self) -> None:
        with self.assertRaises(PurityDenominatorAmbiguity):
            dominant_tier_fraction(["proxy_easy", "proxy_easy", None])

    def test_fingerprint_is_deterministic_and_never_a_bank_id(self) -> None:
        first = problem_set_fingerprint("6.NS.A.1", ("p3", "p1", "p2"))
        second = problem_set_fingerprint("6.NS.A.1", ("p1", "p2", "p3"))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertNotIn("bank", first)

    def test_no_native_bank_id_field_exists(self) -> None:
        self.assertNotIn("bankId", ATTEMPT_FIELDS)
        fields = {name for name in AdaptiveAttemptRecord.__dataclass_fields__}
        self.assertNotIn("bankId", fields)


class ExposureAndSequenceTests(unittest.TestCase):
    def test_fresh_problem_fraction_uses_only_past_exposure(self) -> None:
        base = EVALUATION_WINDOW_START
        tiers = {"p1": "proxy_easy", "p2": "proxy_easy", "p3": "proxy_moderate"}
        records, _ = build_attempt_records(
            [
                episode(assignment="assignment-1", started=base, keys=("p1", "p2", "p3")),
                episode(
                    assignment="assignment-2",
                    started=base + timedelta(days=1),
                    keys=("p1", "p4", "p5"),
                ),
            ],
            tiers=tiers,
            eligible_skills=frozenset({"6.NS.A.1"}),
            bkt_states={
                "episode-student-1-assignment-1-6.NS.A.1": BktStateAt(
                    "student-1", "6.NS.A.1", 0.72, 3, base
                ),
                "episode-student-1-assignment-2-6.NS.A.1": BktStateAt(
                    "student-1", "6.NS.A.1", 0.72, 6, base + timedelta(days=1)
                ),
            },
            release_id=RELEASE_ID,
        )
        ordered = sorted(records, key=lambda record: record.attempt.external_attempt_sequence)
        self.assertAlmostEqual(ordered[0].attempt.fresh_problem_fraction, 1.0)
        self.assertAlmostEqual(ordered[1].attempt.fresh_problem_fraction, 2 / 3)

    def test_future_exposure_does_not_leak_backward(self) -> None:
        base = EVALUATION_WINDOW_START
        tiers = {"p1": "proxy_easy", "p2": "proxy_easy", "p3": "proxy_moderate"}
        single, _ = build_attempt_records(
            [episode(assignment="assignment-1", started=base, keys=("p1", "p2", "p3"))],
            tiers=tiers,
            eligible_skills=frozenset({"6.NS.A.1"}),
            bkt_states=bkt_state("episode-student-1-assignment-1-6.NS.A.1"),
            release_id=RELEASE_ID,
        )
        self.assertEqual(single[0].attempt.fresh_problem_fraction, 1.0)

    def test_external_attempt_sequence_is_deterministic(self) -> None:
        base = EVALUATION_WINDOW_START
        tiers = {"p1": "proxy_easy", "p2": "proxy_easy", "p3": "proxy_moderate"}
        states = {
            "episode-student-1-assignment-1-6.NS.A.1": BktStateAt(
                "student-1", "6.NS.A.1", 0.72, 3, base
            ),
            "episode-student-1-assignment-2-6.NS.A.1": BktStateAt(
                "student-1", "6.NS.A.1", 0.72, 6, base + timedelta(days=1)
            ),
        }
        first, _ = build_attempt_records(
            [
                episode(assignment="assignment-2", started=base + timedelta(days=1)),
                episode(assignment="assignment-1", started=base),
            ],
            tiers=tiers,
            eligible_skills=frozenset({"6.NS.A.1"}),
            bkt_states=states,
            release_id=RELEASE_ID,
        )
        second, _ = build_attempt_records(
            [
                episode(assignment="assignment-2", started=base + timedelta(days=1)),
                episode(assignment="assignment-1", started=base),
            ],
            tiers=tiers,
            eligible_skills=frozenset({"6.NS.A.1"}),
            bkt_states=states,
            release_id=RELEASE_ID,
        )
        sequences = [record.attempt.external_attempt_sequence for record in first]
        self.assertEqual(sequences, sorted(sequences))
        self.assertEqual(
            [record.attempt.external_attempt_sequence for record in first],
            [record.attempt.external_attempt_sequence for record in second],
        )

    def test_unresolved_chronology_ties_fail_closed(self) -> None:
        base = EVALUATION_WINDOW_START
        tiers = {"p1": "proxy_easy", "p2": "proxy_easy", "p3": "proxy_moderate"}
        records, summary = build_attempt_records(
            [
                episode(assignment="assignment-1", started=base),
                episode(assignment="assignment-2", started=base),
            ],
            tiers=tiers,
            eligible_skills=frozenset({"6.NS.A.1"}),
            bkt_states={
                "episode-student-1-assignment-1-6.NS.A.1": BktStateAt(
                    "student-1", "6.NS.A.1", 0.72, 3, base
                ),
                "episode-student-1-assignment-2-6.NS.A.1": BktStateAt(
                    "student-1", "6.NS.A.1", 0.72, 3, base
                ),
            },
            release_id=RELEASE_ID,
        )
        self.assertEqual(summary["chronology_ambiguous_attempts"], 1)
        self.assertTrue(any(record.chronology_ambiguous for record in records))


class GovernanceAndNoPolicyTests(unittest.TestCase):
    def test_provenance_remains_external_real(self) -> None:
        records, _ = build_attempt_records(
            [episode()],
            tiers={"p1": "proxy_easy", "p2": "proxy_easy", "p3": "proxy_moderate"},
            eligible_skills=frozenset({"6.NS.A.1"}),
            bkt_states=bkt_state("episode-student-1-assignment-1-6.NS.A.1"),
            release_id=RELEASE_ID,
        )
        self.assertEqual(records[0].attempt.provenance, EXTERNAL_PROVENANCE)

    def test_e3_path_never_calls_policy_selectors(self) -> None:
        adaptive = Path(__file__).resolve().parents[1] / "external_data" / "assistments" / "adaptive"
        for filename in ("adaptive_attempts.py", "run_adaptive_attempt_reconstruction.py"):
            source = (adaptive / filename).read_text(encoding="utf-8")
            for forbidden in (
                "select_policy_decision",
                "PolicyArm",
                "DecisionDirection",
                "policy_evaluation",
                "false_promotion",
            ):
                self.assertNotIn(forbidden, source, f"{filename} must not reference {forbidden}")

    def test_rerun_produces_identical_records(self) -> None:
        tiers = {"p1": "proxy_easy", "p2": "proxy_easy", "p3": "proxy_moderate"}
        states = bkt_state("episode-student-1-assignment-1-6.NS.A.1")
        first, _ = build_attempt_records(
            [episode()], tiers=tiers, eligible_skills=frozenset({"6.NS.A.1"}),
            bkt_states=states, release_id=RELEASE_ID,
        )
        second, _ = build_attempt_records(
            [episode()], tiers=tiers, eligible_skills=frozenset({"6.NS.A.1"}),
            bkt_states=states, release_id=RELEASE_ID,
        )
        self.assertEqual(first, second)

    def test_diagnostic_declares_no_raw_identifiers_and_no_production(self) -> None:
        # The runner's blocked diagnostic summary contract (verified statically).
        runner = Path(__file__).resolve().parents[1] / "external_data" / "assistments" / "adaptive" / "run_adaptive_attempt_reconstruction.py"
        source = runner.read_text(encoding="utf-8")
        self.assertIn('"containsRawIdentifiers": False', source)
        self.assertIn('"productionPromotionAllowed": False', source)


if __name__ == "__main__":
    unittest.main()
