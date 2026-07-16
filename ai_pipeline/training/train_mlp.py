"""Modest MLP baseline; it is a comparison model, not an assumed deployment choice."""

from __future__ import annotations

from logic_oasis_ai.prediction_contract import SupervisedExample

from .common import validated_training_data


def train_mlp(examples: tuple[SupervisedExample, ...], *, random_seed: int):
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    matrix, targets, names = validated_training_data(examples)
    # Early stopping needs enough rows for a validation fold; tiny studies still
    # receive an explicitly preliminary report rather than a misleading claim.
    use_early_stopping = len(matrix) >= 30
    model = make_pipeline(
        StandardScaler(),
        MLPClassifier(
            hidden_layer_sizes=(8,),
            alpha=0.01,
            early_stopping=use_early_stopping,
            max_iter=500,
            tol=0.01,
            n_iter_no_change=12,
            random_state=random_seed,
        ),
    )
    return model.fit(matrix, targets), names
