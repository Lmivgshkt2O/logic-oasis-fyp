"""Leakage-safe, future-facing target construction for U7 model comparison."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping

from .features import AttemptFeatureRow, FEATURE_SCHEMA_VERSION
from .time_utils import parse_timestamp


PREDICTION_TARGET = "next_attempt_support_needed"
PREDICTION_LABEL_VERSION = "next-attempt-support-needed-v1"
DEFAULT_MASTERY_CRITERION = 0.60
BASE_FEATURE_NAMES = (
    "total_questions",
    "correct_count",
    "correct_rate",
    "mean_response_time_ms",
    "mean_hint_count",
)
BKT_FEATURE_NAME = "bkt_mastery_probability"


@dataclass(frozen=True)
class PredictionContract:
    target_name: str = PREDICTION_TARGET
    label_version: str = PREDICTION_LABEL_VERSION
    mastery_criterion: float = DEFAULT_MASTERY_CRITERION
    feature_schema_version: str = FEATURE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not 0.0 < self.mastery_criterion < 1.0:
            raise ValueError("mastery_criterion must be between zero and one")


@dataclass(frozen=True)
class SupervisedExample:
    attempt_id: str
    student_key: str
    subtopic_id: str
    observed_at: datetime
    features: Mapping[str, float]
    target: bool
    contract: PredictionContract


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


def build_supervised_examples(
    attempts: Iterable[AttemptFeatureRow],
    *,
    contract: PredictionContract = PredictionContract(),
    bkt_mastery_by_attempt_id: Mapping[str, float] | None = None,
) -> tuple[SupervisedExample, ...]:
    """Label an attempt only from its next chronological same-subtopic attempt.

    The final attempt in each student/subtopic sequence is intentionally absent:
    no later result exists, so assigning it a success/failure label would create
    a false training outcome.
    """
    grouped: dict[tuple[str, str], list[AttemptFeatureRow]] = {}
    for attempt in attempts:
        if attempt.provenance != "real":
            raise ValueError("only real approved feature rows may enter final evaluation")
        if attempt.feature_schema_version != contract.feature_schema_version:
            raise ValueError("feature schema does not match the prediction contract")
        grouped.setdefault((attempt.student_key, attempt.subtopic_id), []).append(attempt)

    examples: list[SupervisedExample] = []
    for (_, _), sequence in sorted(grouped.items()):
        ordered = sorted(
            ((_parse_timestamp(row.finalized_at), row) for row in sequence),
            key=lambda item: (item[0], item[1].attempt_id),
        )
        for (observed_at, current), (_, next_attempt) in zip(ordered, ordered[1:]):
            features = current.to_model_features()
            if bkt_mastery_by_attempt_id is not None:
                bkt_mastery = bkt_mastery_by_attempt_id.get(current.attempt_id)
                if bkt_mastery is None:
                    raise ValueError("BKT ablation requires a current-attempt BKT value")
                if not 0.0 <= bkt_mastery <= 1.0:
                    raise ValueError("BKT mastery probability must be between zero and one")
                features[BKT_FEATURE_NAME] = float(bkt_mastery)
            _validate_current_features(features)
            examples.append(
                SupervisedExample(
                    attempt_id=current.attempt_id,
                    student_key=current.student_key,
                    subtopic_id=current.subtopic_id,
                    observed_at=observed_at,
                    features=features,
                    target=next_attempt.correct_rate < contract.mastery_criterion,
                    contract=contract,
                )
            )
    return tuple(examples)


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
    if not rows:
        return DataSufficiency("pipeline_demo_only", "no observed next attempts", 0, 0, 0, 0)
    if not support_needed_count or not support_not_needed_count:
        return DataSufficiency(
            "pipeline_demo_only", "both target classes are required for comparison",
            len(rows), len(students), support_needed_count, support_not_needed_count,
        )
    if len(students) < 2:
        return DataSufficiency(
            "pipeline_demo_only", "grouped validation requires more than one student",
            len(rows), len(students), support_needed_count, support_not_needed_count,
        )
    if len(students) < 4:
        return DataSufficiency(
            "preliminary_comparison", "too few independent students for a stable held-out claim",
            len(rows), len(students), support_needed_count, support_not_needed_count,
        )
    return DataSufficiency(
        "held_out_comparison", "grouped held-out evaluation is possible; report uncertainty",
        len(rows), len(students), support_needed_count, support_not_needed_count,
    )


def _validate_current_features(values: Mapping[str, float]) -> None:
    allowed = set(BASE_FEATURE_NAMES) | {BKT_FEATURE_NAME}
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(f"future or undeclared features are not allowed: {sorted(unknown)}")
    missing = set(BASE_FEATURE_NAMES) - set(values)
    if missing:
        raise ValueError(f"required current features are missing: {sorted(missing)}")


def _parse_timestamp(value: str) -> datetime:
    return parse_timestamp(value, "finalized_at")
