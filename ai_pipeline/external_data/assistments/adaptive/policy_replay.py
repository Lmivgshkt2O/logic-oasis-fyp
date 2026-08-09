"""AQC-E5 real external policy replay (one-step, non-propagating, descriptive).

This is the FIRST stage allowed to run P1/P2/P3a on real ASSISTments external
learner states.  It replays the frozen P1/P2/P3a selectors on the exact 2,090
shared policy-ready states established by AQC-E4, with strict row parity, no
future outcome values, no P3b, and no XGBoost/support-risk inference.  All
decisions are one-step and never propagate a counterfactual state into later
observed history.

Reversal history uses ONLY the observed previous proxy tier from E3 (mapped
into the selector's last-transition input as ``move_up_observed`` /
``move_down_observed`` wiring markers; never a prior simulated decision).
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from logic_oasis_ai.adaptive_policy import (
    Difficulty,
    load_adaptive_policy_config,
)
from logic_oasis_ai.policy_evaluation import (
    PolicyArm,
    PolicyDecisionContext,
    load_policy_evaluation_manifest,
    select_policy_decision,
)

from .controlled_mechanics import external_options_for_tiers, to_selector_banks
from .readiness_audit import (
    policy_ready_funnel,
    verify_frozen_lineage,
)


E5_MANIFEST_VERSION = "assistments-e5-policy-replay-manifest-v1"
E4_MANIFEST_HASH = "bf8a0b20c94aea98e5b0d66df9ce0efcac1985f039f7b86e8218d3ed2a6c1b9c"
CLAIM_LEVEL = "external_descriptive_replay"
SHARED_STATE_COUNT = 2090

REPLAY_ARMS = (PolicyArm.P1, PolicyArm.P2, PolicyArm.P3A)
TIERS = ("proxy_easy", "proxy_moderate", "proxy_hard")
DECISION_ROW_FIELDS = (
    "externalStateKey", "externalStudentKey", "sourceSkillCode",
    "currentProxyDifficulty", "correctRate", "bktMasteryProbability",
    "bktEvidenceCount", "previousObservedProxyDifficulty", "policy",
    "scoreDirection", "bktDirection", "proposedDirection",
    "proposedTargetProxyDifficulty", "reasonCode", "selectionEvidenceMode",
    "usedBktFallback", "candidateKind", "externalCandidateKey", "decisionId",
    "provenance",
)


class ReplayError(ValueError):
    """Raised when the E5 policy replay cannot proceed safely."""


@dataclass(frozen=True)
class PolicyDecisionRow:
    external_state_key: str
    external_student_key: str
    source_skill_code: str
    current_proxy_difficulty: str
    correct_rate: float
    bkt_mastery_probability: float
    bkt_evidence_count: int
    previous_observed_proxy_difficulty: str | None
    policy: str
    score_direction: str
    bkt_direction: str
    proposed_direction: str
    proposed_target_proxy_difficulty: str | None
    reason_code: str
    selection_evidence_mode: str
    used_bkt_fallback: bool
    candidate_kind: str
    external_candidate_key: str | None
    decision_id: str
    provenance: str

    def to_csv_row(self) -> dict[str, str]:
        return {
            "externalStateKey": self.external_state_key,
            "externalStudentKey": self.external_student_key,
            "sourceSkillCode": self.source_skill_code,
            "currentProxyDifficulty": self.current_proxy_difficulty,
            "correctRate": f"{self.correct_rate:.8f}",
            "bktMasteryProbability": f"{self.bkt_mastery_probability:.8f}",
            "bktEvidenceCount": str(self.bkt_evidence_count),
            "previousObservedProxyDifficulty": self.previous_observed_proxy_difficulty or "",
            "policy": self.policy,
            "scoreDirection": self.score_direction,
            "bktDirection": self.bkt_direction,
            "proposedDirection": self.proposed_direction,
            "proposedTargetProxyDifficulty": self.proposed_target_proxy_difficulty or "",
            "reasonCode": self.reason_code,
            "selectionEvidenceMode": self.selection_evidence_mode,
            "usedBktFallback": str(self.used_bkt_fallback).lower(),
            "candidateKind": self.candidate_kind,
            "externalCandidateKey": self.external_candidate_key or "",
            "decisionId": self.decision_id,
            "provenance": self.provenance,
        }


def load_shared_states(
    e3_attempts_path: str | Path,
    eligible_skills: frozenset[str],
    *,
    expected_count: int = SHARED_STATE_COUNT,
) -> list[object]:
    """Load the frozen E4 shared policy-ready states (same filter as E4)."""
    from .readiness_audit import load_attempts

    attempts = load_attempts(e3_attempts_path)
    ready, funnel = policy_ready_funnel(attempts, eligible_skills)
    actual = int(funnel["sharedPolicyReady"]["attempts"])
    if actual != expected_count:
        raise ReplayError(
            f"shared policy-ready population changed: expected {expected_count}, got {actual}"
        )
    return ready


def shared_state_document(state) -> dict[str, object]:
    """Canonical per-state identity+evidence document for hashing."""
    return {
        "externalAttemptKey": state.external_attempt_key,
        "externalStudentKey": state.external_student_key,
        "sourceSkillCode": state.source_skill_code,
        "externalAttemptSequence": state.external_attempt_sequence,
        "correctCount": state.correct_count,
        "totalQuestions": state.total_questions,
        "correctRate": state.correct_rate,
        "bktMasteryProbability": state.bkt_mastery_probability,
        "bktEvidenceCount": state.bkt_evidence_count,
        "bktVersion": state.bkt_version,
        "currentProxyDifficulty": state.current_proxy_difficulty,
        "proxyDifficultyPurity": state.proxy_difficulty_purity,
        "previousObservedProxyDifficulty": state.previous_observed_proxy_difficulty,
        "freshProblemFraction": state.fresh_problem_fraction,
        "chronologyAmbiguous": state.chronology_ambiguous,
        "provenance": state.provenance,
    }


def shared_policy_state_hash(states: Sequence[object]) -> str:
    payload = json.dumps(
        [shared_state_document(state) for state in states],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def observed_transition_marker(
    previous_tier: str | None,
    current_tier: str,
) -> str | None:
    """Map observed proxy-tier history into the selector's last-transition input."""
    if previous_tier is None or previous_tier == current_tier:
        return None
    moved_up = TIERS.index(current_tier) > TIERS.index(previous_tier)
    return "move_up_observed" if moved_up else "move_down_observed"


def _score_direction(correct_rate: float) -> str:
    if correct_rate >= 0.80:
        return "up"
    if correct_rate <= 0.40:
        return "down"
    return "neutral"


def _bkt_direction_audit(
    mastery: float,
    evidence: int,
    *,
    move_up_mastery: float,
    move_down_mastery: float,
    move_up_minimum_evidence: int,
) -> str:
    """Descriptive BKT-direction audit field from frozen config thresholds."""
    if mastery <= move_down_mastery:
        return "down"
    if mastery >= move_up_mastery and evidence >= move_up_minimum_evidence:
        return "up"
    return "neutral"


def build_decision_context(state) -> PolicyDecisionContext:
    difficulty = {
        "proxy_easy": Difficulty.EASY,
        "proxy_moderate": Difficulty.MODERATE,
        "proxy_hard": Difficulty.HARD,
    }[state.current_proxy_difficulty]
    return PolicyDecisionContext(
        source_attempt_id=state.external_attempt_key,
        student_id=state.external_student_key,
        subtopic_id=state.source_skill_code,
        current_difficulty=difficulty,
        correct_count=state.correct_count,
        total_questions=state.total_questions,
        mastery_probability=state.bkt_mastery_probability,
        evidence_count=state.bkt_evidence_count,
        support_risk=None,
        compatible_model_available=False,
        last_transition=observed_transition_marker(
            state.previous_observed_proxy_difficulty,
            state.current_proxy_difficulty,
        ),
    )


def replay_policies(
    states: Sequence[object],
    *,
    config,
) -> tuple[list[PolicyDecisionRow], dict[str, object]]:
    """Replay P1/P2/P3a on every shared state; returns rows and parity proof."""
    adaptive_policy = load_adaptive_policy_config(config.adaptive_policy_path)
    manifest = load_policy_evaluation_manifest(
        config.policy_manifest_path,
        adaptive_policy=adaptive_policy,
    )
    options = external_options_for_tiers()
    banks = to_selector_banks(options)
    state_hash = shared_policy_state_hash(states)

    rows: list[PolicyDecisionRow] = []
    per_policy_keys: dict[str, list[str]] = {arm.value: [] for arm in REPLAY_ARMS}
    for state in states:
        context = build_decision_context(state)
        for arm in REPLAY_ARMS:
            decision = select_policy_decision(
                arm,
                context,
                banks,
                manifest=manifest,
                adaptive_policy=adaptive_policy,
            )
            per_policy_keys[arm.value].append(state.external_attempt_key)
            target_tier = _target_tier(state.current_proxy_difficulty, decision)
            rows.append(
                PolicyDecisionRow(
                    external_state_key=state.external_attempt_key,
                    external_student_key=state.external_student_key,
                    source_skill_code=state.source_skill_code,
                    current_proxy_difficulty=state.current_proxy_difficulty,
                    correct_rate=state.correct_rate,
                    bkt_mastery_probability=state.bkt_mastery_probability,
                    bkt_evidence_count=state.bkt_evidence_count,
                    previous_observed_proxy_difficulty=state.previous_observed_proxy_difficulty,
                    policy=arm.value,
                    score_direction=_score_direction(state.correct_rate),
                    bkt_direction=_bkt_direction_audit(
                        state.bkt_mastery_probability,
                        state.bkt_evidence_count,
                        move_up_mastery=adaptive_policy.thresholds.move_up_mastery,
                        move_down_mastery=adaptive_policy.thresholds.move_down_mastery,
                        move_up_minimum_evidence=adaptive_policy.thresholds.minimum_evidence_for_move_up,
                    ),
                    proposed_direction=decision.direction.value,
                    proposed_target_proxy_difficulty=target_tier,
                    reason_code=decision.reason_code,
                    selection_evidence_mode=decision.evidence_mode.value,
                    used_bkt_fallback=decision.used_bkt_fallback,
                    candidate_kind="external_proxy_tier",
                    external_candidate_key=decision.selected_bank_id,
                    decision_id=decision.decision_id,
                    provenance=state.provenance,
                )
            )
    parity = _row_parity_proof(rows, states, state_hash, per_policy_keys)
    return rows, parity


def _target_tier(current_tier: str, decision) -> str | None:
    if decision.direction.value == "hold":
        return current_tier
    levels = TIERS
    index = levels.index(current_tier)
    movement = 1 if decision.direction.value == "up" else -1
    target_index = max(0, min(index + movement, len(levels) - 1))
    if target_index == index:
        return current_tier
    return levels[target_index]


def _row_parity_proof(
    rows: Sequence[PolicyDecisionRow],
    states: Sequence[object],
    state_hash: str,
    per_policy_keys: Mapping[str, list[str]],
) -> dict[str, object]:
    by_policy = {arm.value: [row for row in rows if row.policy == arm.value] for arm in REPLAY_ARMS}
    if any(len(value) != len(states) for value in by_policy.values()):
        raise ReplayError("policy decision rows do not match the shared-state count")
    keys = {arm.value: [row.external_state_key for row in by_policy[arm.value]] for arm in REPLAY_ARMS}
    if not (keys["P1"] == keys["P2"] == keys["P3a"] == per_policy_keys["P1"] == per_policy_keys["P2"] == per_policy_keys["P3a"]):
        raise ReplayError("policy row identities differ across arms")
    input_hashes = {
        arm: sha256(
            json.dumps(
                [shared_state_document(state) for state in states],
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        for arm in ("P1", "P2", "P3a")
    }
    if len(set(input_hashes.values())) != 1 or input_hashes["P1"] != state_hash:
        raise ReplayError("policy input hashes differ from the shared state hash")
    return {
        "sharedPolicyStateHash": state_hash,
        "inputHashes": input_hashes,
        "rowCounts": {arm: len(by_policy[arm]) for arm in REPLAY_ARMS},
        "rowParityExact": True,
    }


def direction_counts(rows: Sequence[PolicyDecisionRow]) -> dict[str, object]:
    result: dict[str, object] = {}
    for arm in REPLAY_ARMS:
        arm_rows = [row for row in rows if row.policy == arm.value]
        total = len(arm_rows)
        counts = Counter(row.proposed_direction for row in arm_rows)
        result[arm.value] = {
            "decisionCount": total,
            "learners": len({row.external_student_key for row in arm_rows}),
            "skills": len({row.source_skill_code for row in arm_rows}),
            "upCount": counts["up"],
            "upRate": _rate(counts["up"], total),
            "holdCount": counts["hold"],
            "holdRate": _rate(counts["hold"], total),
            "downCount": counts["down"],
            "downRate": _rate(counts["down"], total),
        }
    return result


def tier_specific_directions(rows: Sequence[PolicyDecisionRow]) -> dict[str, object]:
    result: dict[str, object] = {}
    for arm in REPLAY_ARMS:
        arm_rows = [row for row in rows if row.policy == arm.value]
        tiers: dict[str, object] = {}
        for tier in TIERS:
            tier_rows = [row for row in arm_rows if row.current_proxy_difficulty == tier]
            counts = Counter(row.proposed_direction for row in tier_rows)
            tiers[tier] = {
                "states": len(tier_rows),
                "up": counts["up"],
                "hold": counts["hold"],
                "down": counts["down"],
            }
        result[arm.value] = tiers
    return result


def reason_counts(rows: Sequence[PolicyDecisionRow]) -> dict[str, object]:
    result: dict[str, object] = {}
    for arm in REPLAY_ARMS:
        arm_rows = [row for row in rows if row.policy == arm.value]
        total = len(arm_rows)
        by_reason: dict[str, dict[str, object]] = {}
        for reason, group in _group_by(arm_rows, lambda row: row.reason_code).items():
            by_reason[reason] = {
                "count": len(group),
                "rate": _rate(len(group), total),
                "learners": len({row.external_student_key for row in group}),
            }
        result[arm.value] = by_reason
    return result


def agreement_metrics(rows: Sequence[PolicyDecisionRow]) -> dict[str, object]:
    by_state: dict[str, dict[str, PolicyDecisionRow]] = {}
    for row in rows:
        by_state.setdefault(row.external_state_key, {})[row.policy] = row
    pairs = (("P1", "P2"), ("P1", "P3a"), ("P2", "P3a"))
    pairwise: dict[str, object] = {}
    for arm_a, arm_b in pairs:
        agreed = sum(
            1
            for state_rows in by_state.values()
            if state_rows[arm_a].proposed_direction == state_rows[arm_b].proposed_direction
        )
        pairwise[f"{arm_a}_vs_{arm_b}"] = {
            "agreementCount": agreed,
            "agreementRate": _rate(agreed, len(by_state)),
            "comparedStates": len(by_state),
        }
    all_same = sum(
        1
        for state_rows in by_state.values()
        if len({state_rows[arm].proposed_direction for arm in ("P1", "P2", "P3a")}) == 1
    )
    three_way = {
        "allThreeSame": all_same,
        "allThreeSameRate": _rate(all_same, len(by_state)),
        "atLeastOneDiffers": len(by_state) - all_same,
        "comparedStates": len(by_state),
    }
    return {"pairwise": pairwise, "threeWay": three_way}


def eb_metrics(rows: Sequence[PolicyDecisionRow]) -> dict[str, object]:
    by_state: dict[str, dict[str, PolicyDecisionRow]] = {}
    for row in rows:
        by_state.setdefault(row.external_state_key, {})[row.policy] = row
    p1_up_states = {
        key: state_rows
        for key, state_rows in by_state.items()
        if state_rows["P1"].proposed_direction == "up"
    }
    p3a_hold_where_p1_up = {
        key: state_rows
        for key, state_rows in p1_up_states.items()
        if state_rows["P3a"].proposed_direction == "hold"
    }
    p2_hold_where_p1_up = {
        key: state_rows
        for key, state_rows in p1_up_states.items()
        if state_rows["P2"].proposed_direction == "hold"
    }
    p2_disagreement_hold = {
        key: state_rows
        for key, state_rows in by_state.items()
        if state_rows["P2"].reason_code == "p2_disagreement_hold"
    }
    p3a_guardrail_hold = {
        key: state_rows
        for key, state_rows in by_state.items()
        if state_rows["P3a"].proposed_direction == "hold"
        and state_rows["P3a"].reason_code
        in {
            "p3_stay_build_evidence",
            "anti_oscillation_hold",
            "hard_requires_more_evidence",
            "p3_stay_easy_support",
            "p3_stay_hard_mastery",
            "difficulty_upper_bound_hold",
            "difficulty_lower_bound_hold",
            "no_eligible_bank",
        }
    }
    return {
        "p1UpCount": len(p1_up_states),
        "p3aHoldWhereP1Up": {
            "count": len(p3a_hold_where_p1_up),
            "rateAmongAllStates": _rate(len(p3a_hold_where_p1_up), len(by_state)),
            "rateAmongP1UpStates": _rate(len(p3a_hold_where_p1_up), len(p1_up_states)),
            "learners": len(
                {
                    state_rows["P1"].external_student_key
                    for state_rows in p3a_hold_where_p1_up.values()
                }
            ),
            "skills": len(
                {
                    state_rows["P1"].source_skill_code
                    for state_rows in p3a_hold_where_p1_up.values()
                }
            ),
        },
        "p2HoldWhereP1Up": {
            "count": len(p2_hold_where_p1_up),
            "rateAmongAllStates": _rate(len(p2_hold_where_p1_up), len(by_state)),
            "rateAmongP1UpStates": _rate(len(p2_hold_where_p1_up), len(p1_up_states)),
        },
        "p2DisagreementHoldCount": len(p2_disagreement_hold),
        "p2DisagreementHoldRate": _rate(len(p2_disagreement_hold), len(by_state)),
        "p3aGuardrailHoldCount": len(p3a_guardrail_hold),
        "p3aGuardrailHoldRate": _rate(len(p3a_guardrail_hold), len(by_state)),
    }


def reversal_signal_metrics(
    rows: Sequence[PolicyDecisionRow],
) -> dict[str, object]:
    result: dict[str, object] = {}
    by_state: dict[str, dict[str, PolicyDecisionRow]] = {}
    for row in rows:
        by_state.setdefault(row.external_state_key, {})[row.policy] = row
    previous_tier_states = {
        key: state_rows
        for key, state_rows in by_state.items()
        if state_rows["P1"].previous_observed_proxy_difficulty is not None
    }
    for arm in REPLAY_ARMS:
        same_direction = 0
        reversal_proposed = 0
        reversal_held = 0
        no_movement = 0
        same_tier_no_observed_movement = 0
        for state_rows in previous_tier_states.values():
            row = state_rows[arm.value]
            previous = row.previous_observed_proxy_difficulty
            current = row.current_proxy_difficulty
            if previous == current:
                same_tier_no_observed_movement += 1
                continue
            observed_direction = (
                "up" if TIERS.index(current) > TIERS.index(previous) else "down"
            )
            proposed = row.proposed_direction
            if proposed == observed_direction:
                same_direction += 1
            elif row.reason_code == "anti_oscillation_hold":
                reversal_held += 1
            elif proposed == "hold":
                no_movement += 1
            else:
                reversal_proposed += 1
        result[arm.value] = {
            "statesWithPreviousTier": len(previous_tier_states),
            "sameDirectionAsObservedMovement": same_direction,
            "immediateReversalProposed": reversal_proposed,
            "reversalConvertedToHold": reversal_held,
            "noMovement": no_movement,
            "sameTierNoObservedMovement": same_tier_no_observed_movement,
        }
    return result


def decision_rows_hash(rows: Sequence[PolicyDecisionRow]) -> str:
    payload = json.dumps(
        [row.to_csv_row() for row in sorted(rows, key=lambda row: (row.external_state_key, row.policy))],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def write_decision_rows_csv(rows: Sequence[PolicyDecisionRow], path: str | Path) -> Path:
    destination = Path(path)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DECISION_ROW_FIELDS)
        writer.writeheader()
        for row in sorted(rows, key=lambda row: (row.external_state_key, row.policy)):
            writer.writerow(row.to_csv_row())
    return destination


def build_e5_manifest(
    *,
    verification: Mapping[str, object],
    shared_state_hash: str,
    direction: Mapping[str, object],
    tier_directions: Mapping[str, object],
    reasons: Mapping[str, object],
    agreement: Mapping[str, object],
    eb: Mapping[str, object],
    reversal: Mapping[str, object],
    decision_audit_hash: str,
) -> dict[str, object]:
    return {
        "manifestSchemaVersion": E5_MANIFEST_VERSION,
        "contractVersion": "assistments-adaptive-contract-v1.2",
        "contractHash": verification["contractHashV1_2"],
        "e2DifficultyCatalogHash": verification["e2CatalogHash"],
        "e3AttemptHash": verification["e3AttemptsHash"],
        "e4ReadinessManifestHash": E4_MANIFEST_HASH,
        "policyBundleVersion": "policy-evaluation-v1",
        "policyBundleHash": verification["policyEvaluationSha256"] if "policyEvaluationSha256" in verification else None,
        "p1Version": "score-threshold-v1",
        "p2Version": "bkt-score-agreement-v1",
        "p3aVersion": "guarded-bkt-study-v1",
        "sourceStateCount": SHARED_STATE_COUNT,
        "sourceLearnerCount": direction["P1"]["learners"],
        "sourceSkillCount": direction["P1"]["skills"],
        "sharedPolicyStateHash": shared_state_hash,
        "decisionRowCounts": {arm: direction[arm]["decisionCount"] for arm in ("P1", "P2", "P3a")},
        "decisionAuditHash": decision_audit_hash,
        "directionCountsByPolicy": direction,
        "tierSpecificDirectionCounts": tier_directions,
        "reasonCountsByPolicy": reasons,
        "agreementCounts": agreement["pairwise"],
        "threeWayAgreementCounts": agreement["threeWay"],
        "ebMetrics": eb,
        "reversalSignalCounts": reversal,
        "claimLevel": CLAIM_LEVEL,
        "provenance": "external_real",
        "containsRawIdentifiers": False,
        "productionPromotionAllowed": False,
        "p3bExecuted": False,
        "futureOutcomeValuesUsed": False,
    }


def write_manifest(manifest: Mapping[str, object], path: str | Path) -> Path:
    destination = Path(path)
    destination.write_text(
        json.dumps(dict(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return destination


def _group_by(rows: Sequence[PolicyDecisionRow], key) -> dict[str, list[PolicyDecisionRow]]:
    grouped: dict[str, list[PolicyDecisionRow]] = {}
    for row in rows:
        grouped.setdefault(key(row), []).append(row)
    return grouped


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 8)
