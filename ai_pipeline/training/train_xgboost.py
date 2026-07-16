"""Small, deterministic XGBoost candidate for the frozen U7 contract."""

from __future__ import annotations

from logic_oasis_ai.prediction_contract import SupervisedExample

from .common import validated_training_data


def train_xgboost(examples: tuple[SupervisedExample, ...], *, random_seed: int):
    from xgboost import XGBClassifier

    matrix, targets, names = validated_training_data(examples)
    model = XGBClassifier(
        n_estimators=40,
        max_depth=3,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=random_seed,
        n_jobs=1,
    )
    return model.fit(matrix, targets), names
