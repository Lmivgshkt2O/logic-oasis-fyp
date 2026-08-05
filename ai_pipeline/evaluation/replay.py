"""Deterministic chronological reconstruction of P1/P2/P3 decisions.

Stage B reconstruction asks each declared policy what it would have decided at
every eligible historical decision point.  Only state visible before the later
attempt is ever read; later attempts are consumed exclusively by the outcome
module.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from random import Random
from typing import Iterable, Mapping

from logic_oasis_ai.adaptive_policy import (
    AdaptivePolicyConfig,
    Difficulty,
    EligibleBank,
)
from logic_oasis_ai.bkt import build_bkt_ablation_evidence
from logic_oasis_ai.policy_evaluation import (
    DecisionDirection,
    PolicyArm,
    PolicyDecisionContext,
    PolicyEvaluationManifest,
    select_policy_decision,
)
from logic_oasis_ai.schemas import FinalizedQuizAttemptRecord
from logic_oasis_ai.sources.firestore_source import SourceDataset

from .manifest import EvaluationRunManifest


REPLAY_ARMS = (PolicyArm.P1, PolicyArm.P2, PolicyArm.P3A)


class ReplayError(ValueError):
    """Raised when trusted histories cannot be reconstructed safely."""


@dataclass(frozen=True)
class ReplayDecision:
    """One counterfactual policy decision at one historical decision point."""

    decision_id: str
    source_attempt_id: str
    student_key: str
    subtopic_id: str
    source_attempt_sequence: int
    arm: PolicyArm
    policy_version: str
    evidence_mode: str
    claim_label: str
    direction: DecisionDirection
    selected_bank_id: str | None
    selected_difficulty: Difficulty | None
    reason_code: str
    used_bkt_fallback: bool
    current_difficulty: Difficulty
    score_rate: float
    mastery_probability: float
    evidence_count: int
    outcome_status: str

    @property
    def is_assignable(self) -> bool:
        return self.selected_bank_id is not None and self.selected_difficulty is not None

    def to_document(self) -> dict[str, object]:
        return {
            "decisionId": self.decision_id,
            "sourceAttemptId": self.source_attempt_id,
            "studentKey": self.student_key,
            "subtopicId": self.subtopic_id,
            "sourceAttemptSequence": self.source_attempt_sequence,
            "arm": self.arm.value,
            "policyVersion": self.policy_version,
            "evidenceMode": self.evidence_mode,
            "claimLabel": self.claim_label,
            "direction": self.direction.value,
            "selectedBankId": self.selected_bank_id,
            "selectedDifficulty": (
                self.selected_difficulty.value if self.selected_difficulty else None
            ),
            "reasonCode": self.reason_code,
            "usedBktFallback": self.used_bkt_fallback,
            "currentDifficulty": self.current_difficulty.value,
            "scoreRate": self.score_rate,
            "masteryProbability": self.mastery_probability,
            "evidenceCount": self.evidence_count,
            "outcomeStatus": self.outcome_status,
        }


@dataclass(frozen=True)
class ReplayResult:
    decisions: tuple[ReplayDecision, ...]
    arms: tuple[PolicyArm, ...]
    dataset_sha256: str

    def decisions_for(self, arm: PolicyArm) -> tuple[ReplayDecision, ...]:
        return tuple(decision for decision in self.decisions if decision.arm is arm)


def replay_policies(
    dataset: SourceDataset,
    *,
    run_manifest: EvaluationRunManifest,
    adaptive_policy: AdaptivePolicyConfig,
    policy_manifest: PolicyEvaluationManifest,
    bank_catalog: Mapping[str, tuple[EligibleBank, ...]],
    arms: Iterable[PolicyArm] = REPLAY_ARMS,
    support_risk_by_attempt: Mapping[str, float] | None = None,
) -> ReplayResult:
    """Reconstruct every declared arm's decision from pre-later-attempt state."""
    _validate_run_bindings(dataset, run_manifest, adaptive_policy, policy_manifest)
    selected_arms = tuple(arms)
    if not selected_arms:
        raise ReplayError("at least one policy arm is required")
    if any(arm not in PolicyArm for arm in selected_arms):
        raise ReplayError("unknown policy arm in replay request")
    if PolicyArm.P3B in selected_arms and support_risk_by_attempt is None:
        raise ReplayError("P3b requires compatible model-assisted support-risk evidence")

    bkt_evidence = _bkt_evidence_by_attempt(dataset)
    ordered = _ordered_attempts(dataset)
    decisions: list[ReplayDecision] = []
    previous_by_arm: dict[PolicyArm, ReplayDecision] = {}
    for attempt in ordered:
        key = _student_key(dataset, attempt.student_id)
        subtopic = attempt.subtopic_id
        for arm in selected_arms:
            support_risk = None
            if arm is PolicyArm.P3B:
                support_risk = support_risk_by_attempt.get(attempt.attempt_id)
                if support_risk is None:
                    raise ReplayError(
                        f"P3b requires support risk for attempt {attempt.attempt_id}"
                    )
            previous = previous_by_arm.get(arm)
            context = PolicyDecisionContext(
                source_attempt_id=_attempt_key(dataset, attempt.attempt_id),
                student_id=key,
                subtopic_id=subtopic,
                current_difficulty=_difficulty(dataset, attempt.attempt_id),
                correct_count=attempt.correct_count,
                total_questions=attempt.total_questions,
                mastery_probability=bkt_evidence[attempt.attempt_id].mastery_probability,
                evidence_count=bkt_evidence[attempt.attempt_id].evidence_count,
                support_risk=support_risk,
                compatible_model_available=support_risk is not None,
                last_transition=_last_transition(previous),
            )
            banks = _banks_for(
                dataset,
                bank_catalog,
                student_key=key,
                subtopic_id=subtopic,
                attempt_id=attempt.attempt_id,
            )
            decision = select_policy_decision(
                arm,
                context,
                banks,
                manifest=policy_manifest,
                adaptive_policy=adaptive_policy,
            )
            replayed = ReplayDecision(
                decision_id=decision.decision_id,
                source_attempt_id=_attempt_key(dataset, attempt.attempt_id),
                student_key=key,
                subtopic_id=subtopic,
                source_attempt_sequence=attempt.source_attempt_sequence or 0,
                arm=decision.arm,
                policy_version=decision.policy_version,
                evidence_mode=decision.evidence_mode.value,
                claim_label=decision.claim_label,
                direction=decision.direction,
                selected_bank_id=decision.selected_bank_id,
                selected_difficulty=decision.selected_difficulty,
                reason_code=decision.reason_code,
                used_bkt_fallback=decision.used_bkt_fallback,
                current_difficulty=context.current_difficulty,
                score_rate=context.score_rate,
                mastery_probability=context.mastery_probability,
                evidence_count=context.evidence_count,
                outcome_status=decision.outcome_status,
            )
            decisions.append(replayed)
            previous_by_arm[arm] = replayed
    return ReplayResult(
        decisions=tuple(decisions),
        arms=selected_arms,
        dataset_sha256=run_manifest.dataset_sha256,
    )


def derive_bank_catalog(
    dataset: SourceDataset,
) -> dict[str, tuple[EligibleBank, ...]]:
    """Derive per-subtopic bank metadata from observed trusted attempts.

    Banks observed in trusted attempts are treated as active.  A caller with a
    server-owned bank catalogue should pass that catalogue instead; this helper
    exists for pipeline demonstration and tests.
    """
    grouped: dict[str, dict[tuple[str, str], None]] = {}
    for attempt in dataset.attempts:
        context = dataset.attempt_context_by_id[attempt.attempt_id]
        grouped.setdefault(context.subtopic_id, {}).setdefault(
            (context.bank_id, context.difficulty_level), None
        )
    return {
        subtopic_id: tuple(
            EligibleBank(
                bank_id=bank_id,
                difficulty=Difficulty(difficulty_level),
                is_active=True,
            )
            for (bank_id, difficulty_level) in sorted(entries)
        )
        for subtopic_id, entries in sorted(grouped.items())
    }


def load_bank_catalog_csv(path: str | object) -> dict[str, tuple[EligibleBank, ...]]:
    """Load a server-owned bank catalogue CSV.

    Columns: subtopicId, bankId, difficultyLevel, isActive.
    """
    import csv

    from pathlib import Path

    catalog: dict[str, dict[tuple[str, str], EligibleBank]] = {}
    with Path(path).open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            subtopic_id = _required(row, "subtopicId")
            bank_id = _required(row, "bankId")
            difficulty = Difficulty(_required(row, "difficultyLevel"))
            is_active = _required(row, "isActive").strip().lower() == "true"
            entries = catalog.setdefault(subtopic_id, {})
            if (bank_id, difficulty.value) in entries:
                raise ReplayError(f"duplicate bank in catalogue: {bank_id}")
            entries[(bank_id, difficulty.value)] = EligibleBank(
                bank_id=bank_id, difficulty=difficulty, is_active=is_active
            )
    return {
        subtopic_id: tuple(entries[item] for item in sorted(entries))
        for subtopic_id, entries in sorted(catalog.items())
    }


def student_grouped_partition(
    decisions: Iterable[ReplayDecision],
    *,
    random_seed: int,
    test_fraction: float = 0.25,
) -> tuple[tuple[ReplayDecision, ...], tuple[ReplayDecision, ...]]:
    """Partition decisions by whole student keys; no student may split."""
    rows = tuple(decisions)
    if not 0.0 < test_fraction < 1.0:
        raise ReplayError("test_fraction must be between zero and one")
    groups = sorted({decision.student_key for decision in rows})
    if len(groups) < 2:
        raise ReplayError("partition requires at least two students")
    shuffled = list(groups)
    Random(random_seed).shuffle(shuffled)
    test_count = min(len(shuffled) - 1, max(1, round(len(shuffled) * test_fraction)))
    test_groups = frozenset(shuffled[:test_count])
    train = tuple(row for row in rows if row.student_key not in test_groups)
    test = tuple(row for row in rows if row.student_key in test_groups)
    if not train or not test:
        raise ReplayError("partition produced an empty side")
    if {row.student_key for row in train} & {row.student_key for row in test}:
        raise ReplayError("student leaked across partitions")
    return train, test


def _validate_run_bindings(
    dataset: SourceDataset,
    run_manifest: EvaluationRunManifest,
    adaptive_policy: AdaptivePolicyConfig,
    policy_manifest: PolicyEvaluationManifest,
) -> None:
    if dataset.provenance != run_manifest.provenance:
        raise ReplayError("dataset provenance does not match the run manifest")
    if dataset.schema_version != run_manifest.source_schema_version:
        raise ReplayError("source schema version does not match the run manifest")
    if run_manifest.dataset_sha256 != _dataset_sha256_for(dataset):
        raise ReplayError("dataset hash does not match the frozen run manifest")
    if adaptive_policy.source_sha256 != run_manifest.adaptive_policy_sha256:
        raise ReplayError("adaptive policy hash does not match the run manifest")
    if policy_manifest.source_sha256 != run_manifest.policy_evaluation_sha256:
        raise ReplayError("policy evaluation manifest hash does not match the run manifest")
    if policy_manifest.adaptive_policy_sha256 != adaptive_policy.source_sha256:
        raise ReplayError("policy evaluation manifest does not bind this adaptive policy")


def _dataset_sha256_for(dataset: SourceDataset) -> str:
    from .manifest import dataset_sha256

    return dataset_sha256(dataset)


def _bkt_evidence_by_attempt(
    dataset: SourceDataset,
) -> dict[str, "BktReplayEvidence"]:
    evidence_rows = build_bkt_ablation_evidence(
        dataset.attempts, dataset.responses_by_attempt
    )
    by_attempt: dict[str, list[object]] = {}
    for row in evidence_rows:
        by_attempt.setdefault(row.source_attempt_id, []).append(row)
    result: dict[str, BktReplayEvidence] = {}
    for attempt in dataset.attempts:
        rows = by_attempt.get(attempt.attempt_id)
        if not rows:
            raise ReplayError(f"missing BKT lineage for attempt {attempt.attempt_id}")
        latest = max(rows, key=lambda row: row.sequence_index)
        result[attempt.attempt_id] = BktReplayEvidence(
            mastery_probability=latest.p_known_after_attempt,
            evidence_count=latest.observation_count,
        )
    return result


@dataclass(frozen=True)
class BktReplayEvidence:
    mastery_probability: float
    evidence_count: int

    def __post_init__(self) -> None:
        if not isfinite(self.mastery_probability) or not 0.0 <= self.mastery_probability <= 1.0:
            raise ReplayError("BKT mastery must be between zero and one")
        if self.evidence_count < 1:
            raise ReplayError("BKT evidence count must be positive")


def _ordered_attempts(
    dataset: SourceDataset,
) -> tuple[FinalizedQuizAttemptRecord, ...]:
    attempts = sorted(
        dataset.attempts,
        key=lambda item: (
            item.source_attempt_sequence or 0,
            item.finalized_at,
            item.attempt_id,
        ),
    )
    if any(
        attempt.source_attempt_sequence is None or attempt.source_attempt_sequence < 1
        for attempt in attempts
    ):
        raise ReplayError("legacy attempts without a sequence cannot be replayed")
    grouped: dict[tuple[str, str], list[int]] = {}
    for attempt in attempts:
        key = (
            _student_key(dataset, attempt.student_id),
            attempt.subtopic_id,
        )
        grouped.setdefault(key, []).append(attempt.source_attempt_sequence or 0)
    for key, sequences in grouped.items():
        if len(set(sequences)) != len(sequences):
            raise ReplayError(
                f"sourceAttemptSequence must be unique within a learner/subtopic: {key}"
            )
    return tuple(attempts)


def _banks_for(
    dataset: SourceDataset,
    catalog: Mapping[str, tuple[EligibleBank, ...]],
    *,
    student_key: str,
    subtopic_id: str,
    attempt_id: str,
) -> tuple[EligibleBank, ...]:
    base = catalog.get(subtopic_id, ())
    if not base:
        raise ReplayError(f"no bank catalogue entries for subtopic {subtopic_id}")
    sequence = _sequence_for(dataset, attempt_id)
    exposed: dict[str, int] = {}
    for attempt in dataset.attempts:
        if _student_key(dataset, attempt.student_id) != student_key:
            continue
        if attempt.subtopic_id != subtopic_id:
            continue
        if (attempt.source_attempt_sequence or 0) > sequence:
            continue
        context = dataset.attempt_context_by_id[attempt.attempt_id]
        exposed[context.bank_id] = exposed.get(context.bank_id, 0) + 1
    return tuple(
        EligibleBank(
            bank_id=bank.bank_id,
            difficulty=bank.difficulty,
            exposure_count=exposed.get(bank.bank_id, 0),
            is_active=bank.is_active,
        )
        for bank in base
    )


def _sequence_for(dataset: SourceDataset, attempt_id: str) -> int:
    for attempt in dataset.attempts:
        if attempt.attempt_id == attempt_id:
            return attempt.source_attempt_sequence or 0
    raise ReplayError(f"unknown attempt in replay: {attempt_id}")


def _difficulty(dataset: SourceDataset, attempt_id: str) -> Difficulty:
    context = dataset.attempt_context_by_id.get(attempt_id)
    if context is None:
        raise ReplayError(f"missing attempt context for {attempt_id}")
    try:
        return Difficulty(context.difficulty_level)
    except ValueError as error:
        raise ReplayError(f"unknown difficulty for {attempt_id}") from error


def _last_transition(previous: ReplayDecision | None) -> str | None:
    if previous is None:
        return None
    lowered = previous.reason_code.lower()
    if lowered.startswith(("move_up", "move_down")):
        return previous.reason_code
    return None


def _attempt_key(dataset: SourceDataset, attempt_id: str) -> str:
    return dataset.attempt_key_by_attempt_id.get(attempt_id, attempt_id)


def _student_key(dataset: SourceDataset, student_id: str) -> str:
    return dataset.student_key_by_student_id.get(student_id, student_id)


def _required(row: Mapping[str, str], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise ReplayError(f"{field} is required in bank catalogue")
    return value
