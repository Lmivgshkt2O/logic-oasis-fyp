"""Frozen, future-facing U7 prediction and pair-audit contract.

The contract deliberately separates current-attempt features from the later
attempt used only to create a label.  It is safe for real evaluation and also
has an explicit synthetic-test route which can never make a performance claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Iterable, Mapping

from .features import AttemptFeatureRow, BASE_FEATURE_NAMES, FEATURE_SCHEMA_VERSION
from .time_utils import parse_timestamp


PREDICTION_TARGET = "next_attempt_support_needed"
PREDICTION_LABEL_VERSION = "next-attempt-support-needed-v1"
DEFAULT_MASTERY_CRITERION = 0.60
BKT_FEATURE_NAME = "bkt_mastery_probability"
RUNTIME_PROVENANCE = "real"
SYNTHETIC_TEST_PROVENANCE = "synthetic_test"


@dataclass(frozen=True)
class PredictionContract:
    target_name: str = PREDICTION_TARGET
    label_version: str = PREDICTION_LABEL_VERSION
    mastery_criterion: float = DEFAULT_MASTERY_CRITERION
    feature_schema_version: str = FEATURE_SCHEMA_VERSION
    compatible_content_version_pairs: frozenset[tuple[str, str]] = frozenset()
    compatible_policy_version_pairs: frozenset[tuple[str, str]] = frozenset()

    def __post_init__(self) -> None:
        if self.target_name != PREDICTION_TARGET:
            raise ValueError("U7 supports only next_attempt_support_needed")
        if self.label_version != PREDICTION_LABEL_VERSION:
            raise ValueError("U7 requires the declared next-attempt label version")
        if self.feature_schema_version != FEATURE_SCHEMA_VERSION:
            raise ValueError("only quiz-attempt-features-v2 may enter a U7 comparison")
        if not 0.0 < self.mastery_criterion < 1.0:
            raise ValueError("mastery_criterion must be between zero and one")


@dataclass(frozen=True)
class BktAttemptEvidence:
    """Typed U4 evidence ending at the current attempt, never a naked float."""

    attempt_id: str
    source_attempt_sequence: int
    student_key: str
    subtopic_id: str
    skill_id: str
    source_response_ids: tuple[str, ...]
    bkt_version: str
    p_known_after_attempt: float

    def __post_init__(self) -> None:
        if not all((self.attempt_id, self.student_key, self.subtopic_id, self.skill_id, self.bkt_version)):
            raise ValueError("BKT evidence lineage fields are required")
        if self.source_attempt_sequence < 1:
            raise ValueError("BKT evidence sourceAttemptSequence must be positive")
        if not self.source_response_ids:
            raise ValueError("BKT evidence must retain source response IDs")
        if not isfinite(self.p_known_after_attempt) or not 0.0 <= self.p_known_after_attempt <= 1.0:
            raise ValueError("BKT evidence pKnownAfterAttempt must be between zero and one")


@dataclass(frozen=True)
class PairAudit:
    current_attempt_id: str
    next_attempt_id: str | None
    student_key: str
    subtopic_id: str
    eligible: bool
    censor_reason: str | None
    stratum: str | None
    immediate_question_repeat: bool
    current_bank_id: str
    next_bank_id: str | None
    current_policy_version: str
    next_policy_version: str | None


@dataclass(frozen=True)
class PairAuditSummary:
    total_current_attempts: int
    eligible_pairs: int
    same_bank_pairs: int
    cross_bank_pairs: int
    immediate_question_repeats: int
    censored_no_later_attempt: int
    censored_incompatible_pairs: int
    censored_policy_pairs: int
    censored_repeated_question_pairs: int

    def to_document(self) -> dict[str, int]:
        return {
            "totalCurrentAttempts": self.total_current_attempts,
            "eligiblePairs": self.eligible_pairs,
            "sameBankPairs": self.same_bank_pairs,
            "crossBankPairs": self.cross_bank_pairs,
            "immediateQuestionRepeats": self.immediate_question_repeats,
            "immediateQuestionRepeatRate": (
                0 if not self.total_current_attempts else round(self.immediate_question_repeats / self.total_current_attempts, 8)
            ),
            "censoredNoLaterAttempt": self.censored_no_later_attempt,
            "censoredIncompatiblePairs": self.censored_incompatible_pairs,
            "censoredPolicyPairs": self.censored_policy_pairs,
            "censoredRepeatedQuestionPairs": self.censored_repeated_question_pairs,
        }


@dataclass(frozen=True)
class SupervisedExample:
    attempt_id: str
    student_key: str
    subtopic_id: str
    observed_at: datetime
    features: Mapping[str, float]
    target: bool
    contract: PredictionContract
    provenance: str


@dataclass(frozen=True)
class PredictionDataset:
    examples: tuple[SupervisedExample, ...]
    pair_audits: tuple[PairAudit, ...]
    pair_audit_summary: PairAuditSummary


@dataclass(frozen=True)
class DataSufficiency:
    claim_level: str
    reason: str
    example_count: int
    student_count: int
    support_needed_count: int
    support_not_needed_count: int

    @property
    def can_compare(self) -> bool:
        return self.claim_level in {"preliminary_comparison", "held_out_comparison"}


def build_prediction_dataset(
    attempts: Iterable[AttemptFeatureRow],
    *,
    contract: PredictionContract = PredictionContract(),
    bkt_evidence_by_attempt_id: Mapping[str, BktAttemptEvidence] | None = None,
    allow_synthetic_test: bool = False,
) -> PredictionDataset:
    """Create direct chronological labels and retain every pair decision for audit."""
    rows = tuple(attempts)
    _validate_rows(rows, contract=contract, allow_synthetic_test=allow_synthetic_test)
    grouped: dict[tuple[str, str], list[AttemptFeatureRow]] = {}
    for row in rows:
        grouped.setdefault((row.student_key, row.subtopic_id), []).append(row)

    examples: list[SupervisedExample] = []
    audits: list[PairAudit] = []
    for (_, _), sequence in sorted(grouped.items()):
        ordered = _ordered_attempts(sequence)
        for index, current in enumerate(ordered):
            if index + 1 == len(ordered):
                audits.append(_audit(current, None, eligible=False, reason="no_later_attempt"))
                continue
            next_attempt = ordered[index + 1]
            eligible, reason = _pair_eligibility(current, next_attempt, contract)
            audits.append(_audit(current, next_attempt, eligible=eligible, reason=reason))
            if not eligible:
                continue
            features = current.to_model_features()
            if bkt_evidence_by_attempt_id is not None:
                evidence = bkt_evidence_by_attempt_id.get(current.attempt_id)
                if evidence is None:
                    raise ValueError("BKT ablation requires typed current-attempt evidence")
                features[BKT_FEATURE_NAME] = _validate_bkt_evidence(current, evidence)
            _validate_current_features(features)
            examples.append(
                SupervisedExample(
                    attempt_id=current.attempt_id,
                    student_key=current.student_key,
                    subtopic_id=current.subtopic_id,
                    observed_at=_parse_timestamp(current.finalized_at),
                    features=features,
                    target=next_attempt.correct_rate < contract.mastery_criterion,
                    contract=contract,
                    provenance=current.provenance,
                )
            )
    return PredictionDataset(tuple(examples), tuple(audits), _summarize_audits(audits))


def build_supervised_examples(
    attempts: Iterable[AttemptFeatureRow],
    *,
    contract: PredictionContract = PredictionContract(),
    bkt_evidence_by_attempt_id: Mapping[str, BktAttemptEvidence] | None = None,
    allow_synthetic_test: bool = False,
) -> tuple[SupervisedExample, ...]:
    """Compatibility convenience wrapper; use ``build_prediction_dataset`` for reports."""
    return build_prediction_dataset(
        attempts,
        contract=contract,
        bkt_evidence_by_attempt_id=bkt_evidence_by_attempt_id,
        allow_synthetic_test=allow_synthetic_test,
    ).examples


def feature_names(examples: Iterable[SupervisedExample]) -> tuple[str, ...]:
    rows = tuple(examples)
    if not rows:
        raise ValueError("at least one supervised example is required")
    names = tuple(rows[0].features)
    _validate_current_features(rows[0].features)
    for row in rows[1:]:
        if tuple(row.features) != names:
            raise ValueError("all models must receive identical feature columns")
        _validate_current_features(row.features)
    return names


def assess_data_sufficiency(examples: Iterable[SupervisedExample]) -> DataSufficiency:
    rows = tuple(examples)
    support_needed_count = sum(row.target for row in rows)
    support_not_needed_count = len(rows) - support_needed_count
    students = {row.student_key for row in rows}
    if any(row.provenance != RUNTIME_PROVENANCE for row in rows):
        return DataSufficiency("synthetic_test_only", "synthetic test rows cannot support a model claim", len(rows), len(students), support_needed_count, support_not_needed_count)
    if not rows:
        return DataSufficiency("pipeline_demo_only", "no observed next attempts", 0, 0, 0, 0)
    if not support_needed_count or not support_not_needed_count:
        return DataSufficiency("pipeline_demo_only", "both target classes are required for comparison", len(rows), len(students), support_needed_count, support_not_needed_count)
    if len(students) < 2:
        return DataSufficiency("pipeline_demo_only", "grouped validation requires more than one student", len(rows), len(students), support_needed_count, support_not_needed_count)
    if len(students) < 4:
        return DataSufficiency("preliminary_comparison", "too few independent students for a stable held-out claim", len(rows), len(students), support_needed_count, support_not_needed_count)
    return DataSufficiency("held_out_comparison", "grouped held-out evaluation is possible; report uncertainty", len(rows), len(students), support_needed_count, support_not_needed_count)


def _validate_rows(rows: tuple[AttemptFeatureRow, ...], *, contract: PredictionContract, allow_synthetic_test: bool) -> None:
    for row in rows:
        if row.feature_schema_version != contract.feature_schema_version:
            raise ValueError("feature schema does not match the prediction contract")
        if row.provenance != RUNTIME_PROVENANCE and not (allow_synthetic_test and row.provenance == SYNTHETIC_TEST_PROVENANCE):
            raise ValueError("only approved real feature rows may enter final evaluation")
        if row.source_attempt_sequence is None:
            raise ValueError("legacy_no_sequence attempts cannot enter U7 evaluation")
        if row.source_attempt_sequence < 1:
            raise ValueError("sourceAttemptSequence must be positive")
        if row.year_level is None or row.year_level < 1 or not row.skill_ids or not row.question_ids:
            raise ValueError("U7 attempt rows require year, skill, and question audit evidence")


def _ordered_attempts(rows: list[AttemptFeatureRow]) -> tuple[AttemptFeatureRow, ...]:
    ordered = tuple(sorted(rows, key=lambda row: (row.source_attempt_sequence or 0, _parse_timestamp(row.finalized_at), row.attempt_id)))
    sequences = [row.source_attempt_sequence for row in ordered]
    if len(set(sequences)) != len(sequences):
        raise ValueError("sourceAttemptSequence must be unique within a student/subtopic")
    return ordered


def _pair_eligibility(current: AttemptFeatureRow, next_attempt: AttemptFeatureRow, contract: PredictionContract) -> tuple[bool, str | None]:
    if current.year_level != next_attempt.year_level or current.topic_id != next_attempt.topic_id or current.subtopic_id != next_attempt.subtopic_id or set(current.skill_ids) != set(next_attempt.skill_ids):
        return False, "incompatible_curriculum"
    if not _versions_compatible(current.content_version, next_attempt.content_version, contract.compatible_content_version_pairs):
        return False, "incompatible_content_version"
    if not _versions_compatible(current.adaptive_policy_version, next_attempt.adaptive_policy_version, contract.compatible_policy_version_pairs):
        return False, "incompatible_policy_version"
    if set(current.question_ids) & set(next_attempt.question_ids):
        return False, "immediate_question_repeat"
    return True, None


def _versions_compatible(current: str, later: str, approved_pairs: frozenset[tuple[str, str]]) -> bool:
    return current == later or (current, later) in approved_pairs


def _audit(current: AttemptFeatureRow, next_attempt: AttemptFeatureRow | None, *, eligible: bool, reason: str | None) -> PairAudit:
    return PairAudit(
        current_attempt_id=current.attempt_id,
        next_attempt_id=next_attempt.attempt_id if next_attempt else None,
        student_key=current.student_key,
        subtopic_id=current.subtopic_id,
        eligible=eligible,
        censor_reason=reason,
        stratum=None if next_attempt is None else ("same_bank" if current.bank_id == next_attempt.bank_id else "cross_bank"),
        immediate_question_repeat=bool(next_attempt and set(current.question_ids) & set(next_attempt.question_ids)),
        current_bank_id=current.bank_id,
        next_bank_id=next_attempt.bank_id if next_attempt else None,
        current_policy_version=current.adaptive_policy_version,
        next_policy_version=next_attempt.adaptive_policy_version if next_attempt else None,
    )


def _summarize_audits(audits: Iterable[PairAudit]) -> PairAuditSummary:
    rows = tuple(audits)
    return PairAuditSummary(
        total_current_attempts=len(rows),
        eligible_pairs=sum(row.eligible for row in rows),
        same_bank_pairs=sum(row.eligible and row.stratum == "same_bank" for row in rows),
        cross_bank_pairs=sum(row.eligible and row.stratum == "cross_bank" for row in rows),
        immediate_question_repeats=sum(row.immediate_question_repeat for row in rows),
        censored_no_later_attempt=sum(row.censor_reason == "no_later_attempt" for row in rows),
        censored_incompatible_pairs=sum(row.censor_reason in {"incompatible_curriculum", "incompatible_content_version"} for row in rows),
        censored_policy_pairs=sum(row.censor_reason == "incompatible_policy_version" for row in rows),
        censored_repeated_question_pairs=sum(row.censor_reason == "immediate_question_repeat" for row in rows),
    )


def _validate_bkt_evidence(current: AttemptFeatureRow, evidence: BktAttemptEvidence) -> float:
    if (
        evidence.attempt_id != current.attempt_id
        or evidence.source_attempt_sequence != current.source_attempt_sequence
        or evidence.student_key != current.student_key
        or evidence.subtopic_id != current.subtopic_id
        or len(current.skill_ids) != 1
        or evidence.skill_id != current.skill_ids[0]
        or tuple(sorted(evidence.source_response_ids)) != tuple(sorted(current.response_ids))
    ):
        raise ValueError("BKT evidence lineage must end at the current attempt")
    return float(evidence.p_known_after_attempt)


def _validate_current_features(values: Mapping[str, float]) -> None:
    allowed = set(BASE_FEATURE_NAMES) | {BKT_FEATURE_NAME}
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(f"future or undeclared features are not allowed: {sorted(unknown)}")
    missing = set(BASE_FEATURE_NAMES) - set(values)
    if missing:
        raise ValueError(f"required current features are missing: {sorted(missing)}")
    if any(not isfinite(float(value)) for value in values.values()):
        raise ValueError("feature values must be finite")


def _parse_timestamp(value: str) -> datetime:
    return parse_timestamp(value, "finalized_at")
