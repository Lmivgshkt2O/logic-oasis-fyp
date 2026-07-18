"""Modest MLP baseline; it is a comparison model, not an assumed deployment choice."""

from __future__ import annotations

from logic_oasis_ai.prediction_contract import SupervisedExample

from .common import validated_training_data


def train_mlp(examples: tuple[SupervisedExample, ...], *, random_seed: int):
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    matrix, targets, names = validated_training_data(examples)
    # FYP1 has no viable inner student-grouped validation protocol yet.  The
    # outer held-out students must never be used for stopping.
    model = make_pipeline(
        StandardScaler(),
        MLPClassifier(
            hidden_layer_sizes=(8,),
            alpha=0.01,
            early_stopping=False,
            max_iter=500,
            tol=0.01,
            n_iter_no_change=12,
            random_state=random_seed,
        ),
    )
    return model.fit(matrix, targets), names
