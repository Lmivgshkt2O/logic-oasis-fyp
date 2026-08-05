from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from logic_oasis_ai.adaptive_policy import (
    Difficulty,
    EligibleBank,
    load_adaptive_policy_config,
)
from logic_oasis_ai.policy_evaluation import (
    DecisionAuditPayload,
    DecisionDirection,
    PolicyArm,
    PolicyDecisionContext,
    PolicyEvaluationConfigurationError,
    SelectionEvidenceMode,
    StudyStatus,
    load_policy_evaluation_manifest,
    select_policy_decision,
)


CONFIGS = Path(__file__).parents[1] / "configs"
ADAPTIVE_POLICY_PATH = CONFIGS / "adaptive_policy_v1.yaml"
MANIFEST_PATH = CONFIGS / "policy_evaluation_v1.yaml"
BANKS = (
    EligibleBank("easy-seen", Difficulty.EASY, exposure_count=3),
    EligibleBank("easy-fresh", Difficulty.EASY),
    EligibleBank("moderate-seen", Difficulty.MODERATE, exposure_count=2),
    EligibleBank("moderate-fresh", Difficulty.MODERATE),
    EligibleBank("hard-fresh", Difficulty.HARD),
)


def context(**overrides) -> PolicyDecisionContext:
    values = {
        "source_attempt_id": "attempt-1",
        "student_id": "student-1",
        "subtopic_id": "read_write_numbers",
        "current_difficulty": Difficulty.EASY,
        "correct_count": 3,
        "total_questions": 5,
        "mastery_probability": 0.60,
        "evidence_count": 3,
        "support_risk": None,
        "compatible_model_available": False,
        "last_transition": None,
    }
    values.update(overrides)
    return PolicyDecisionContext(**values)


class PolicyEvaluationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adaptive_policy = load_adaptive_policy_config(ADAPTIVE_POLICY_PATH)
        cls.manifest = load_policy_evaluation_manifest(
            MANIFEST_PATH, adaptive_policy=cls.adaptive_policy
        )

    def choose(self, arm, decision_context, banks=BANKS):
        return select_policy_decision(
            arm,
            decision_context,
            banks,
            manifest=self.manifest,
            adaptive_policy=self.adaptive_policy,
        )

    def test_manifest_is_draft_hash_bound_and_immutable(self) -> None:
        self.assertEqual(self.manifest.study.status, StudyStatus.DRAFT)
        self.assertFalse(self.manifest.study.may_enrol)
        self.assertEqual(len(self.manifest.source_sha256), 64)
        self.assertEqual(
            self.manifest.adaptive_policy_sha256,
            self.adaptive_policy.source_sha256,
        )
        self.assertEqual(self.manifest.frozen_prediction_target, "next_attempt_support_needed")
        with self.assertRaises(AttributeError):
            self.manifest.primary_metric = "changed"  # type: ignore[misc]

    def test_missing_altered_and_implicitly_active_manifests_fail_closed(self) -> None:
        with self.assertRaises(PolicyEvaluationConfigurationError):
            load_policy_evaluation_manifest(
                MANIFEST_PATH.with_name("missing.yaml"),
                adaptive_policy=self.adaptive_policy,
            )
        original = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
        variants = []
        missing = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
        del missing["scoreRules"]["promotionAtLeast"]
        variants.append(missing)
        altered = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
        altered["adaptivePolicy"]["sourceSha256"] = "0" * 64
        variants.append(altered)
        altered_threshold = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
        altered_threshold["scoreRules"]["promotionAtLeast"] = 0.81
        variants.append(altered_threshold)
        active = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
        active["study"]["status"] = "active"
        variants.append(active)
        extra = original
        extra["implementationDefault"] = True
        variants.append(extra)
        with tempfile.TemporaryDirectory() as temporary_directory:
            for index, variant in enumerate(variants):
                path = Path(temporary_directory) / f"invalid-{index}.yaml"
                path.write_text(yaml.safe_dump(variant, sort_keys=False), encoding="utf-8")
                with self.subTest(index=index), self.assertRaises(
                    PolicyEvaluationConfigurationError
                ):
                    load_policy_evaluation_manifest(
                        path, adaptive_policy=self.adaptive_policy
                    )

    def test_p1_threshold_is_inclusive_and_below_threshold_holds(self) -> None:
        at_threshold = self.choose(PolicyArm.P1, context(correct_count=4))
        below_threshold = self.choose(PolicyArm.P1, context(correct_count=3))

        self.assertEqual(at_threshold.direction, DecisionDirection.UP)
        self.assertEqual(at_threshold.selected_difficulty, Difficulty.MODERATE)
        self.assertEqual(at_threshold.reason_code, "p1_score_promote")
        self.assertEqual(below_threshold.direction, DecisionDirection.HOLD)
        self.assertEqual(below_threshold.selected_difficulty, Difficulty.EASY)
        self.assertEqual(below_threshold.reason_code, "p1_score_hold")

    def test_p1_cannot_jump_and_holds_at_upper_bound(self) -> None:
        moderate = self.choose(
            PolicyArm.P1,
            context(current_difficulty=Difficulty.MODERATE, correct_count=5),
        )
        hard = self.choose(
            PolicyArm.P1,
            context(current_difficulty=Difficulty.HARD, correct_count=5),
        )

        self.assertEqual(moderate.selected_difficulty, Difficulty.HARD)
        self.assertEqual(hard.direction, DecisionDirection.HOLD)
        self.assertEqual(hard.selected_difficulty, Difficulty.HARD)
        self.assertEqual(hard.reason_code, "difficulty_upper_bound_hold")

    def test_unavailable_target_holds_at_current_level(self) -> None:
        banks = tuple(bank for bank in BANKS if bank.difficulty is not Difficulty.MODERATE)
        decision = self.choose(PolicyArm.P1, context(correct_count=5), banks)

        self.assertEqual(decision.direction, DecisionDirection.HOLD)
        self.assertEqual(decision.selected_difficulty, Difficulty.EASY)
        self.assertEqual(decision.selected_bank_id, "easy-fresh")
        self.assertEqual(decision.reason_code, "no_eligible_bank")

    def test_p2_only_moves_when_bkt_and_score_agree(self) -> None:
        promote = self.choose(
            PolicyArm.P2,
            context(correct_count=4, mastery_probability=0.80),
        )
        promotion_disagreement = self.choose(
            PolicyArm.P2,
            context(correct_count=3, mastery_probability=0.80),
        )
        demote = self.choose(
            PolicyArm.P2,
            context(
                current_difficulty=Difficulty.MODERATE,
                correct_count=2,
                mastery_probability=0.40,
            ),
        )
        demotion_disagreement = self.choose(
            PolicyArm.P2,
            context(
                current_difficulty=Difficulty.MODERATE,
                correct_count=3,
                mastery_probability=0.40,
            ),
        )

        self.assertEqual(promote.reason_code, "p2_agreement_promote")
        self.assertEqual(promote.direction, DecisionDirection.UP)
        self.assertEqual(promotion_disagreement.reason_code, "p2_disagreement_hold")
        self.assertEqual(promotion_disagreement.direction, DecisionDirection.HOLD)
        self.assertEqual(demote.reason_code, "p2_agreement_demote")
        self.assertEqual(demote.direction, DecisionDirection.DOWN)
        self.assertEqual(demotion_disagreement.reason_code, "p2_disagreement_hold")

    def test_p2_neutral_hard_evidence_and_reversal_branches(self) -> None:
        neutral = self.choose(PolicyArm.P2, context())
        hard_evidence = self.choose(
            PolicyArm.P2,
            context(
                current_difficulty=Difficulty.MODERATE,
                correct_count=5,
                mastery_probability=0.90,
                evidence_count=3,
            ),
        )
        reversal = self.choose(
            PolicyArm.P2,
            context(
                correct_count=5,
                mastery_probability=0.90,
                last_transition="move_down_support",
            ),
        )

        self.assertEqual(neutral.reason_code, "p2_neutral_hold")
        self.assertEqual(hard_evidence.reason_code, "hard_requires_more_evidence")
        self.assertEqual(hard_evidence.direction, DecisionDirection.HOLD)
        self.assertEqual(reversal.reason_code, "anti_oscillation_hold")

    def test_p3a_bypasses_model_and_p3b_is_distinct(self) -> None:
        assisted_context = context(
            correct_count=5,
            mastery_probability=0.90,
            support_risk=0.20,
            compatible_model_available=True,
        )
        p3a = self.choose(PolicyArm.P3A, assisted_context)
        p3b = self.choose(PolicyArm.P3B, assisted_context)

        self.assertEqual(p3a.evidence_mode, SelectionEvidenceMode.BKT_ONLY_STUDY)
        self.assertTrue(p3a.used_bkt_fallback)
        self.assertEqual(p3a.reason_code, "p3_move_up_bkt_fallback")
        self.assertEqual(p3b.evidence_mode, SelectionEvidenceMode.MODEL_ASSISTED)
        self.assertFalse(p3b.used_bkt_fallback)
        self.assertEqual(p3b.reason_code, "p3_move_up_mastery")
        self.assertNotEqual(p3a.claim_label, p3b.claim_label)
        self.assertNotEqual(p3a.policy_version, p3b.policy_version)
        with self.assertRaises(ValueError):
            self.choose(PolicyArm.P3B, context(mastery_probability=0.90))

    def test_p3_unavailable_target_uses_same_current_level_hold(self) -> None:
        banks = tuple(bank for bank in BANKS if bank.difficulty is not Difficulty.MODERATE)
        decision = self.choose(
            PolicyArm.P3A,
            context(correct_count=5, mastery_probability=0.90),
            banks,
        )

        self.assertEqual(decision.direction, DecisionDirection.HOLD)
        self.assertEqual(decision.selected_difficulty, Difficulty.EASY)
        self.assertEqual(decision.selected_bank_id, "easy-fresh")
        self.assertEqual(decision.reason_code, "no_eligible_bank")
        self.assertTrue(decision.used_bkt_fallback)

    def test_decision_id_reason_and_audit_are_deterministic(self) -> None:
        first = self.choose(PolicyArm.P1, context(correct_count=4))
        repeated = self.choose(PolicyArm.P1, context(correct_count=4))
        other_arm = self.choose(PolicyArm.P2, context(correct_count=4))

        self.assertEqual(first, repeated)
        self.assertNotEqual(first.decision_id, other_arm.decision_id)
        audit = DecisionAuditPayload.from_decision(first, self.manifest)
        self.assertEqual(audit.to_document()["decisionId"], first.decision_id)
        self.assertEqual(audit.to_document()["manifestSha256"], self.manifest.source_sha256)
        self.assertEqual(
            audit.to_document()["adaptivePolicySha256"],
            self.adaptive_policy.source_sha256,
        )
        self.assertEqual(audit.reason_code, first.reason_code)

    def test_inactive_banks_are_never_selected(self) -> None:
        banks = BANKS + (
            EligibleBank("moderate-inactive", Difficulty.MODERATE, is_active=False),
        )
        decision = self.choose(PolicyArm.P1, context(correct_count=5), banks)
        self.assertEqual(decision.selected_bank_id, "moderate-fresh")


if __name__ == "__main__":
    unittest.main()
