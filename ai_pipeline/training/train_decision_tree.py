"""Decision Tree baseline for the frozen U7 prediction contract."""

from __future__ import annotations

from logic_oasis_ai.prediction_contract import SupervisedExample

from .common import validated_training_data


def train_decision_tree(examples: tuple[SupervisedExample, ...], *, random_seed: int):
    from sklearn.tree import DecisionTreeClassifier

    matrix, targets, names = validated_training_data(examples)
    model = DecisionTreeClassifier(max_depth=4, min_samples_leaf=2, class_weight="balanced", random_state=random_seed)
    return model.fit(matrix, targets), names
