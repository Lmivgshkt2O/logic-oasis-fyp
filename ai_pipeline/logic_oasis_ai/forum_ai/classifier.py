"""One reproducible TF-IDF + ComplementNB forum explanation-quality pipeline.

The classifier identifies text patterns associated with the reviewed rubric; it
does not determine whether a mathematical answer is correct or reward-worthy.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import Pipeline

MODEL_VERSION = "forum-explanation-nb-v1"
SUFFICIENT = "sufficient_reasoning"
REVISION = "needs_reasoning"
UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class ForumPrediction:
    label: str
    probability: float
    model_version: str
    calibration_state: str = "not_calibrated"


class ForumTextClassifier:
    def __init__(self, pipeline: Pipeline, *, model_version: str = MODEL_VERSION) -> None:
        self.pipeline = pipeline
        self.model_version = model_version

    def predict(self, text: str) -> ForumPrediction:
        normalized = " ".join(text.split())
        probabilities = self.pipeline.predict_proba([normalized])[0]
        labels = list(self.pipeline.classes_)
        index = max(range(len(probabilities)), key=probabilities.__getitem__)
        label = str(labels[index])
        probability = float(probabilities[index])
        # Preserve uncertainty rather than presenting an uncalibrated score as
        # confidence.  Authors can always edit and resubmit their explanation.
        if probability < 0.60:
            label = UNCERTAIN
        return ForumPrediction(label, probability, self.model_version)

    def save(self, path: str | Path) -> None:
        joblib.dump({"modelVersion": self.model_version, "pipeline": self.pipeline}, path)

    @classmethod
    def load(cls, path: str | Path) -> "ForumTextClassifier":
        saved = joblib.load(path)
        if not isinstance(saved, dict) or not isinstance(saved.get("pipeline"), Pipeline):
            raise ValueError("forum model artifact is invalid")
        version = saved.get("modelVersion")
        if not isinstance(version, str) or not version:
            raise ValueError("forum model version is missing")
        return cls(saved["pipeline"], model_version=version)


def train_classifier(rows: Iterable[tuple[str, str]], *, model_version: str = MODEL_VERSION) -> ForumTextClassifier:
    values = [(" ".join(text.split()), label) for text, label in rows if text.strip()]
    if len(values) < 4 or {label for _, label in values} != {SUFFICIENT, REVISION}:
        raise ValueError("training needs reviewed examples for both rubric labels")
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
        ("classifier", ComplementNB(alpha=0.5)),
    ])
    pipeline.fit([text for text, _ in values], [label for _, label in values])
    return ForumTextClassifier(pipeline, model_version=model_version)
