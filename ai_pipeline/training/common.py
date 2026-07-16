"""Shared, deterministic preparation for the U7 fair model comparison."""

from __future__ import annotations

from random import Random
from typing import Iterable

from logic_oasis_ai.prediction_contract import SupervisedExample, feature_names


def grouped_holdout_split(
    examples: Iterable[SupervisedExample],
    *,
    random_seed: int,
    test_fraction: float = 0.25,
) -> tuple[tuple[SupervisedExample, ...], tuple[SupervisedExample, ...]]:
    rows = tuple(examples)
    if not 0.0 < test_fraction < 1.0:
        raise ValueError("test_fraction must be between zero and one")
    students = sorted({row.student_key for row in rows})
    if len(students) < 2:
        raise ValueError("student-grouped split requires at least two students")
    shuffled = list(students)
    Random(random_seed).shuffle(shuffled)
    test_count = min(len(shuffled) - 1, max(1, round(len(shuffled) * test_fraction)))
    test_students = frozenset(shuffled[:test_count])
    train = tuple(row for row in rows if row.student_key not in test_students)
    test = tuple(row for row in rows if row.student_key in test_students)
    if not train or not test:
        raise ValueError("grouped split produced an empty partition")
    if {row.student_key for row in train} & {row.student_key for row in test}:
        raise ValueError("student leaked across train and test partitions")
    return train, test


def matrix_and_target(
    examples: Iterable[SupervisedExample],
    names: tuple[str, ...] | None = None,
) -> tuple[list[list[float]], list[int], tuple[str, ...]]:
    rows = tuple(examples)
    columns = names or feature_names(rows)
    if not rows:
        raise ValueError("examples are required")
    return (
        [[float(row.features[name]) for name in columns] for row in rows],
        [int(row.target) for row in rows],
        columns,
    )


def validated_training_data(examples: Iterable[SupervisedExample]):
    matrix, targets, names = matrix_and_target(examples)
    require_binary_training_targets(targets)
    return matrix, targets, names


def require_binary_training_targets(targets: Iterable[int]) -> None:
    if set(targets) != {0, 1}:
        raise ValueError("training partition must contain both target classes")
