"""Observed-assignment-matched descriptive outcomes and censoring audit.

Stage B may report a later outcome only where the candidate-selected
difficulty equals the difficulty actually delivered and every compatibility
check passes.  Every other row is censored and never scored.  Later outcomes
label an earlier decision; they never enter the earlier BKT state or feature
vector.

Outcome-window semantics follow the frozen U7 adjacent-pair contract: the
outcome candidate is the immediate next later attempt in the same
learner/subtopic sequence, bounded by the pre-registered calendar duration.
The pre-registered maximum number of later attempts is frozen in the run
manifest (>= 1) and is structurally satisfied by the adjacent-pair design.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Mapping

from logic_oasis_ai.adaptive_policy import Difficulty
from logic_oasis_ai.policy_evaluation import DecisionDirection, PolicyArm
from logic_oasis_ai.prediction_contract import PredictionContract
from logic_oasis_ai.schemas import FinalizedQuizAttemptRecord
from logic_oasis_ai.sources.firestore_source import AttemptContext, SourceDataset

from .manifest import OutcomeWindow
from .replay import ReplayDecision, ReplayResult


OBSERVED = "observed"
CENSORED = "censored"


class OutcomeError(ValueError):
    """Raised when later outcomes cannot be joined safely."""


@dataclass(frozen=True)
class DecisionOutcome:
    """One decision's later-outcome record (observed or censored)."""

    decision_id: str
    source_attempt_id: str
    student_key: str
    subtopic_id: str
    arm: PolicyArm
    direction: DecisionDirection
    selected_bank_id: str | None
    selected_difficulty: Difficulty | None
    delivered_bank_id: str | None
    delivered_difficulty: Difficulty | None
    outcome_status: str
    censored_reason: str | None
    support_needed: bool | None
    stratum: str | None
    later_attempt_id: str | None

    @property
    def observed_assignment_matched(self) -> bool:
        return self.outcome_status == OBSERVED

    def to_document(self) -> dict[str, object]:
        return {
            "decisionId": self.decision_id,
            "sourceAttemptId": self.source_attempt_id,
            "studentKey": self.student_key,
            "subtopicId": self.subtopic_id,
            "arm": self.arm.value,
            "direction": self.direction.value,
            "selectedBankId": self.selected_bank_id,
            "selectedDifficulty": (
                self.selected_difficulty.value if self.selected_difficulty else None
            ),
            "deliveredBankId": self.delivered_bank_id,
            "deliveredDifficulty": (
                self.delivered_difficulty.value if self.delivered_difficulty else None
            ),
            "outcomeStatus": self.outcome_status,
            "censoredReason": self.censored_reason,
            "supportNeeded": self.support_needed,
            "stratum": self.stratum,
            "laterAttemptId": self.later_attempt_id,
        }


@dataclass(frozen=True)
class CensoringAuditRow:
    """A counted, non-scored censor row for one decision."""

    decision_id: str
    arm: PolicyArm
    source_attempt_id: str
    reason: str
    counted: bool = True


@dataclass(frozen=True)
class OutcomeResult:
    outcomes: tuple[DecisionOutcome, ...]
    censoring_audit: tuple[CensoringAuditRow, ...]

    def outcomes_for(self, arm: PolicyArm) -> tuple[DecisionOutcome, ...]:
        return tuple(outcome for outcome in self.outcomes if outcome.arm is arm)


def attach_outcomes(
    replay_result: ReplayResult,
    dataset: SourceDataset,
    *,
    contract: PredictionContract = PredictionContract(),
    outcome_window: OutcomeWindow,
) -> OutcomeResult:
    """Attach the first in-window later attempt to every reconstructed decision."""
    grouped = _ordered_sequences(dataset)
    outcomes: list[DecisionOutcome] = []
    audit: list[CensoringAuditRow] = []
    for decision in replay_result.decisions:
        sequence = grouped.get((decision.student_key, decision.subtopic_id))
        if sequence is None:
            raise OutcomeError(
                f"decision references unknown student/subtopic: {decision.student_key}"
            )
        position = _position_of(sequence, decision.source_attempt_id)
        current = sequence[position]
        outcome = _outcome_for(
            decision,
            current,
            sequence[position + 1 :],
            dataset=dataset,
            contract=contract,
            outcome_window=outcome_window,
        )
        outcomes.append(outcome)
        if outcome.outcome_status == CENSORED:
            audit.append(
                CensoringAuditRow(
                    decision_id=outcome.decision_id,
                    arm=outcome.arm,
                    source_attempt_id=outcome.source_attempt_id,
                    reason=outcome.censored_reason or "unknown",
                )
            )
    return OutcomeResult(tuple(outcomes), tuple(audit))


def _outcome_for(
    decision: ReplayDecision,
    current: _SequenceEntry,
    later_attempts: tuple[_SequenceEntry, ...],
    *,
    dataset: SourceDataset,
    contract: PredictionContract,
    outcome_window: OutcomeWindow,
) -> DecisionOutcome:
    if not later_attempts:
        return _censored(decision, "no_later_attempt", None, None, None)
    later = later_attempts[0]
    later_attempt = later.attempt
    later_context = later.context
    duration = later_attempt.finalized_at - current.attempt.finalized_at
    if duration > timedelta(days=outcome_window.max_calendar_duration_days):
        return _censored(
            decision,
            "no_later_attempt_in_window",
            later_context.bank_id,
            _difficulty(later_context.difficulty_level),
            later_attempt.attempt_id,
        )

    reason = _incompatibility_reason(
        current,
        later,
        dataset,
        contract,
    )
    if reason is not None:
        return _censored(
            decision,
            reason,
            later_context.bank_id,
            _difficulty(later_context.difficulty_level),
            later_attempt.attempt_id,
        )

    delivered_difficulty = _difficulty(later_context.difficulty_level)
    if decision.selected_difficulty != delivered_difficulty:
        return _censored(
            decision,
            "counterfactual_difficulty_mismatch",
            later_context.bank_id,
            delivered_difficulty,
            later_attempt.attempt_id,
        )

    correct_rate = later_attempt.correct_count / later_attempt.total_questions
    return DecisionOutcome(
        decision_id=decision.decision_id,
        source_attempt_id=decision.source_attempt_id,
        student_key=decision.student_key,
        subtopic_id=decision.subtopic_id,
        arm=decision.arm,
        direction=decision.direction,
        selected_bank_id=decision.selected_bank_id,
        selected_difficulty=decision.selected_difficulty,
        delivered_bank_id=later_context.bank_id,
        delivered_difficulty=delivered_difficulty,
        outcome_status=OBSERVED,
        censored_reason=None,
        support_needed=correct_rate < contract.mastery_criterion,
        stratum=(
            "same_bank"
            if decision.selected_bank_id == later_context.bank_id
            else "cross_bank"
        ),
        later_attempt_id=later_attempt.attempt_id,
    )


def _incompatibility_reason(
    current: _SequenceEntry,
    later: _SequenceEntry,
    dataset: SourceDataset,
    contract: PredictionContract,
) -> str | None:
    current_attempt = current.attempt
    later_attempt = later.attempt
    current_context = current.context
    later_context = later.context
    current_skills = {
        response.skill_id
        for response in dataset.responses_by_attempt[current_attempt.attempt_id]
    }
    later_skills = {
        response.skill_id
        for response in dataset.responses_by_attempt[later_attempt.attempt_id]
    }
    current_questions = {
        response.question_id
        for response in dataset.responses_by_attempt[current_attempt.attempt_id]
    }
    later_questions = {
        response.question_id
        for response in dataset.responses_by_attempt[later_attempt.attempt_id]
    }
    if (
        current_attempt.year_level != later_attempt.year_level
        or current_context.topic_id != later_context.topic_id
        or current_context.subtopic_id != later_context.subtopic_id
        or current_skills != later_skills
    ):
        return "incompatible_curriculum"
    if not _versions_compatible(
        current_context.content_version,
        later_context.content_version,
        contract.compatible_content_version_pairs,
    ):
        return "incompatible_content_version"
    if not _versions_compatible(
        current_context.adaptive_policy_version,
        later_context.adaptive_policy_version,
        contract.compatible_policy_version_pairs,
    ):
        return "incompatible_policy_version"
    if current_questions & later_questions:
        return "immediate_question_repeat"
    return None


def _versions_compatible(
    current: str,
    later: str,
    approved_pairs: Iterable[tuple[str, str]],
) -> bool:
    return current == later or (current, later) in set(approved_pairs)


def _censored(
    decision: ReplayDecision,
    reason: str,
    delivered_bank_id: str | None,
    delivered_difficulty: Difficulty | None,
    later_attempt_id: str | None,
) -> DecisionOutcome:
    return DecisionOutcome(
        decision_id=decision.decision_id,
        source_attempt_id=decision.source_attempt_id,
        student_key=decision.student_key,
        subtopic_id=decision.subtopic_id,
        arm=decision.arm,
        direction=decision.direction,
        selected_bank_id=decision.selected_bank_id,
        selected_difficulty=decision.selected_difficulty,
        delivered_bank_id=delivered_bank_id,
        delivered_difficulty=delivered_difficulty,
        outcome_status=CENSORED,
        censored_reason=reason,
        support_needed=None,
        stratum=None,
        later_attempt_id=later_attempt_id,
    )


@dataclass(frozen=True)
class _SequenceEntry:
    attempt: FinalizedQuizAttemptRecord
    context: AttemptContext


def _ordered_sequences(
    dataset: SourceDataset,
) -> dict[tuple[str, str], tuple[_SequenceEntry, ...]]:
    grouped: dict[tuple[str, str], list[_SequenceEntry]] = {}
    for attempt in dataset.attempts:
        key = (
            dataset.student_key_by_student_id.get(attempt.student_id, attempt.student_id),
            attempt.subtopic_id,
        )
        context = dataset.attempt_context_by_id[attempt.attempt_id]
        grouped.setdefault(key, []).append(_SequenceEntry(attempt, context))
    return {
        key: tuple(
            sorted(
                entries,
                key=lambda entry: (
                    entry.attempt.source_attempt_sequence or 0,
                    entry.attempt.finalized_at,
                    entry.attempt.attempt_id,
                ),
            )
        )
        for key, entries in sorted(grouped.items())
    }


def _position_of(
    sequence: tuple[_SequenceEntry, ...],
    attempt_key: str,
) -> int:
    for index, entry in enumerate(sequence):
        if entry.attempt.attempt_id == attempt_key:
            return index
    raise OutcomeError(f"decision attempt not found in student/subtopic sequence: {attempt_key}")


def _difficulty(value: str) -> Difficulty:
    try:
        return Difficulty(value)
    except ValueError as error:
        raise OutcomeError(f"unknown delivered difficulty: {value}") from error
