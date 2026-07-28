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
    groups = sorted({row.evaluation_group_key for row in rows})
    if len(groups) < 2:
        raise ValueError("grouped split requires at least two evaluation groups")
    shuffled = list(groups)
    Random(random_seed).shuffle(shuffled)
    test_count = min(len(shuffled) - 1, max(1, round(len(shuffled) * test_fraction)))
    test_groups = frozenset(shuffled[:test_count])
    train, test = _partition_by_evaluation_groups(rows, test_groups)
    if not train or not test:
        raise ValueError("grouped split produced an empty partition")
    if {row.evaluation_group_key for row in train} & {row.evaluation_group_key for row in test}:
        raise ValueError("evaluation group leaked across train and test partitions")
    return train, test


def grouped_binary_holdout_split(
    examples: Iterable[SupervisedExample],
    *,
    random_seed: int,
    test_fraction: float = 0.25,
) -> tuple[tuple[SupervisedExample, ...], tuple[SupervisedExample, ...]] | None:
    """Find a deterministic group-isolated split containing both classes on both sides."""
    from itertools import combinations

    rows = tuple(examples)
    groups = sorted({row.evaluation_group_key for row in rows})
    if len(groups) < 2 or not 0.0 < test_fraction < 1.0:
        return None
    target_count = min(len(groups) - 1, max(1, round(len(groups) * test_fraction)))
    sizes = sorted({1, min(2, len(groups) - 1)}, key=lambda size: (abs(size - target_count), size))
    group_targets = {
        group: {int(row.target) for row in rows if row.evaluation_group_key == group}
        for group in groups
    }
    shuffled = list(groups)
    Random(random_seed).shuffle(shuffled)
    all_targets = {0, 1}
    for size in sizes:
        for candidate in combinations(shuffled, size):
            test_groups = frozenset(candidate)
            test_targets = set().union(*(group_targets[group] for group in test_groups))
            train_targets = set().union(*(group_targets[group] for group in groups if group not in test_groups))
            if test_targets == all_targets and train_targets == all_targets:
                return _partition_by_evaluation_groups(rows, test_groups)
    return None


def _partition_by_evaluation_groups(
    rows: tuple[SupervisedExample, ...],
    test_groups: frozenset[str],
) -> tuple[tuple[SupervisedExample, ...], tuple[SupervisedExample, ...]]:
    return (
        tuple(row for row in rows if row.evaluation_group_key not in test_groups),
        tuple(row for row in rows if row.evaluation_group_key in test_groups),
    )


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
