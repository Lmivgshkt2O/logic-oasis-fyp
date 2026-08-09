"""AQC-A controlled mechanics regression (pipeline_demo_only fixtures).

This module verifies that the authoritative P1/P2/P3a selectors and the
external proxy-tier difficulty-candidate abstraction behave exactly as
intended, using ONLY small deterministic controlled fixtures.  It never reads
real ASSISTments learner rows, never computes a policy rate, and never claims
any external evidence mode.  All fixture evidence is labelled
``pipeline_demo_only``.

The external candidates pass through the SAME selection boundary E5 will use:
``EvaluationDifficultyOption`` (candidateKind=external_proxy_tier,
nativeBankId=null) is bridged into the selector's bank identity slot using the
namespaced ``externalCandidateKey`` (``external_proxy_*``), which is never a
native bankId.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable, Sequence

from logic_oasis_ai.adaptive_policy import (
    Difficulty,
    EligibleBank,
    load_adaptive_policy_config,
)
from logic_oasis_ai.policy_evaluation import (
    DecisionDirection,
    PolicyArm,
    PolicyDecisionContext,
    load_policy_evaluation_manifest,
    select_policy_decision,
)

from .schemas import (
    CandidateKind,
    EvaluationDifficultyOption,
    ProxyDifficulty,
    external_proxy_candidate,
    native_bank_candidate,
)


FIXTURE_EVIDENCE_MODE = "pipeline_demo_only"
FORBIDDEN_FIXTURE_CLAIMS = frozenset(
    {
        "external_descriptive_replay",
        "external_real",
        "superiority",
        "causal_effect",
        "KSSR_validated",
        "production_validated",
    }
)

PROXY_TIERS = ("proxy_easy", "proxy_moderate", "proxy_hard")


class ControlledMechanicsError(ValueError):
    """Raised when a controlled fixture cannot be run safely."""


@dataclass(frozen=True)
class ControlledFixtureResult:
    fixture_id: str
    arm: str
    direction: str
    reason_code: str
    selected_difficulty: str | None
    selected_identity: str | None
    used_bkt_fallback: bool
    decision_id: str
    decision_claim_label: str
    fixture_evidence_mode: str

    def to_document(self) -> dict[str, object]:
        return {
            "fixtureId": self.fixture_id,
            "arm": self.arm,
            "direction": self.direction,
            "reasonCode": self.reason_code,
            "selectedDifficulty": self.selected_difficulty,
            "selectedIdentity": self.selected_identity,
            "usedBktFallback": self.used_bkt_fallback,
            "decisionId": self.decision_id,
            "decisionClaimLabel": self.decision_claim_label,
            "fixtureEvidenceMode": self.fixture_evidence_mode,
        }


@dataclass(frozen=True)
class ControlledMechanicsConfig:
    adaptive_policy_path: Path
    policy_manifest_path: Path


def default_config() -> ControlledMechanicsConfig:
    ai_pipeline = Path(__file__).resolve().parents[3]
    return ControlledMechanicsConfig(
        adaptive_policy_path=ai_pipeline / "configs" / "adaptive_policy_v1.yaml",
        policy_manifest_path=ai_pipeline / "configs" / "policy_evaluation_v1.yaml",
    )


def external_options_for_tiers(
    available: Iterable[str] = PROXY_TIERS,
) -> tuple[EvaluationDifficultyOption, ...]:
    """Three external proxy-tier candidates (nativeBankId always null)."""
    available_set = set(available)
    return tuple(
        external_proxy_candidate(
            ProxyDifficulty(tier),
            available=tier in available_set,
        )
        for tier in PROXY_TIERS
    )


def native_options_for_tiers() -> tuple[EvaluationDifficultyOption, ...]:
    """Three native runtime candidates with concrete bank ids (parity control)."""
    return tuple(
        native_bank_candidate(
            {
                "proxy_easy": Difficulty.EASY,
                "proxy_moderate": Difficulty.MODERATE,
                "proxy_hard": Difficulty.HARD,
            }[tier],
            bank_id=f"bank-{tier}",
        )
        for tier in PROXY_TIERS
    )


def to_selector_banks(
    options: Sequence[EvaluationDifficultyOption],
) -> tuple[EligibleBank, ...]:
    """Bridge EvaluationDifficultyOption into the selector's bank identity slot.

    For external candidates the identity slot carries the namespaced
    externalCandidateKey (``external_proxy_*``) - never a native bankId.
    """
    banks: list[EligibleBank] = []
    for option in options:
        identity = (
            option.external_candidate_key
            if option.candidate_kind is CandidateKind.EXTERNAL_PROXY_TIER
            else option.native_bank_id
        )
        if not identity:
            raise ControlledMechanicsError("candidate option is missing an identity")
        banks.append(
            EligibleBank(
                bank_id=identity,
                difficulty=option.difficulty,
                is_active=option.available,
            )
        )
    return tuple(banks)


def controlled_context(
    *,
    current_tier: str,
    correct: int,
    total: int,
    mastery: float,
    evidence: int,
    last_transition: str | None = None,
    attempt_id: str = "fixture-attempt",
    student_id: str = "fixture-student",
) -> PolicyDecisionContext:
    """Deterministic controlled state using proxy-tier -> Difficulty mapping."""
    difficulty = {
        "proxy_easy": Difficulty.EASY,
        "proxy_moderate": Difficulty.MODERATE,
        "proxy_hard": Difficulty.HARD,
    }[current_tier]
    return PolicyDecisionContext(
        source_attempt_id=attempt_id,
        student_id=student_id,
        subtopic_id="fixture-skill",
        current_difficulty=difficulty,
        correct_count=correct,
        total_questions=total,
        mastery_probability=mastery,
        evidence_count=evidence,
        support_risk=None,
        compatible_model_available=False,
        last_transition=last_transition,
    )


def run_fixture(
    fixture_id: str,
    arm: PolicyArm,
    context: PolicyDecisionContext,
    options: Sequence[EvaluationDifficultyOption],
    *,
    config: ControlledMechanicsConfig | None = None,
) -> ControlledFixtureResult:
    """Run one controlled fixture through the authoritative selector."""
    config = config or default_config()
    adaptive_policy = load_adaptive_policy_config(config.adaptive_policy_path)
    manifest = load_policy_evaluation_manifest(
        config.policy_manifest_path,
        adaptive_policy=adaptive_policy,
    )
    decision = select_policy_decision(
        arm,
        context,
        to_selector_banks(options),
        manifest=manifest,
        adaptive_policy=adaptive_policy,
    )
    selected_identity = decision.selected_bank_id
    if decision.selected_bank_id is not None:
        matching = [
            option
            for option in options
            if option.external_candidate_key == decision.selected_bank_id
            or option.native_bank_id == decision.selected_bank_id
        ]
        if matching and matching[0].candidate_kind is CandidateKind.EXTERNAL_PROXY_TIER:
            selected_identity = f"external:{matching[0].external_candidate_key}"
    return ControlledFixtureResult(
        fixture_id=fixture_id,
        arm=arm.value,
        direction=decision.direction.value,
        reason_code=decision.reason_code,
        selected_difficulty=(
            decision.selected_difficulty.value if decision.selected_difficulty else None
        ),
        selected_identity=selected_identity,
        used_bkt_fallback=decision.used_bkt_fallback,
        decision_id=decision.decision_id,
        decision_claim_label=decision.claim_label,
        fixture_evidence_mode=FIXTURE_EVIDENCE_MODE,
    )


def run_all_fixtures(
    *,
    config: ControlledMechanicsConfig | None = None,
) -> tuple[ControlledFixtureResult, ...]:
    """Run the 15 controlled scenarios (S1..S15) deterministically."""
    all_tiers = external_options_for_tiers()
    no_moderate = external_options_for_tiers(
        available=("proxy_easy", "proxy_hard")
    )

    fixtures: list[tuple[str, PolicyArm, PolicyDecisionContext, tuple[EvaluationDifficultyOption, ...]]] = [
        # S1: P1 score 0.79 -> HOLD
        ("S1", PolicyArm.P1, controlled_context(current_tier="proxy_easy", correct=79, total=100, mastery=0.60, evidence=3), all_tiers),
        # S2: P1 score 0.80 -> UP
        ("S2", PolicyArm.P1, controlled_context(current_tier="proxy_easy", correct=80, total=100, mastery=0.60, evidence=3), all_tiers),
        # S3: P1 at Hard with high score -> HOLD (upper boundary)
        ("S3", PolicyArm.P1, controlled_context(current_tier="proxy_hard", correct=80, total=100, mastery=0.60, evidence=8), all_tiers),
        # S4: P2 score UP + BKT UP -> UP
        ("S4", PolicyArm.P2, controlled_context(current_tier="proxy_moderate", correct=80, total=100, mastery=0.80, evidence=8), all_tiers),
        # S5: P2 score UP + BKT neutral -> HOLD
        ("S5", PolicyArm.P2, controlled_context(current_tier="proxy_moderate", correct=80, total=100, mastery=0.60, evidence=5), all_tiers),
        # S6: P2 score DOWN + BKT DOWN -> DOWN
        ("S6", PolicyArm.P2, controlled_context(current_tier="proxy_moderate", correct=40, total=100, mastery=0.40, evidence=5), all_tiers),
        # S7: P2 score DOWN + BKT neutral -> HOLD
        ("S7", PolicyArm.P2, controlled_context(current_tier="proxy_moderate", correct=40, total=100, mastery=0.60, evidence=5), all_tiers),
        # S8: P3a insufficient evidence -> guarded HOLD
        ("S8", PolicyArm.P3A, controlled_context(current_tier="proxy_easy", correct=80, total=100, mastery=0.80, evidence=1), all_tiers),
        # S9: P3a sufficient evidence -> permitted one-level movement
        ("S9", PolicyArm.P3A, controlled_context(current_tier="proxy_easy", correct=80, total=100, mastery=0.80, evidence=3), all_tiers),
        # S10: P3a reversal protection (observed prior move up, current DOWN requested)
        ("S10", PolicyArm.P3A, controlled_context(current_tier="proxy_moderate", correct=40, total=100, mastery=0.40, evidence=5, last_transition="move_up_mastery"), all_tiers),
        # S11: cold history (no previous observed tier) remains valid
        ("S11", PolicyArm.P1, controlled_context(current_tier="proxy_easy", correct=80, total=100, mastery=0.60, evidence=3, last_transition=None), all_tiers),
        # S12: unavailable adjacent tier -> HOLD
        ("S12", PolicyArm.P1, controlled_context(current_tier="proxy_easy", correct=80, total=100, mastery=0.60, evidence=3), no_moderate),
        # S13: no two-level jump (P1 at Easy, perfect score -> one level only)
        ("S13", PolicyArm.P1, controlled_context(current_tier="proxy_easy", correct=100, total=100, mastery=0.60, evidence=3), all_tiers),
        # S14: future leakage (earlier decision must not change with later context)
        ("S14", PolicyArm.P1, controlled_context(current_tier="proxy_easy", correct=80, total=100, mastery=0.60, evidence=3), all_tiers),
        # S15: one-step non-propagation (observed next state, not counterfactual)
        ("S15", PolicyArm.P1, controlled_context(current_tier="proxy_moderate", correct=60, total=100, mastery=0.60, evidence=5), all_tiers),
    ]
    return tuple(
        run_fixture(fixture_id, arm, context, options, config=config)
        for fixture_id, arm, context, options in fixtures
    )


def fixture_results_hash(results: Sequence[ControlledFixtureResult]) -> str:
    payload = json.dumps(
        [result.to_document() for result in results],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest()
