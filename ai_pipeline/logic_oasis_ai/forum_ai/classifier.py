"""Reproducible TF-IDF + Naive Bayes forum explanation-quality pipelines.

The classifier identifies text patterns associated with the reviewed rubric; it
does not determine whether a mathematical answer is correct or reward-worthy.
"""
from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path
from typing import Iterable

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import ComplementNB, MultinomialNB
from sklearn.pipeline import Pipeline

MODEL_VERSION = "forum-explanation-nb-v1"
SUFFICIENT = "sufficient_reasoning"
REVISION = "needs_reasoning"
UNCERTAIN = "uncertain"
CONTROLLED_SUFFICIENT = "explanation_sufficient"
CONTROLLED_REVISION = "answer_only_or_insufficient"
NAIVE_BAYES_VARIANTS = frozenset({"ComplementNB", "MultinomialNB"})
VECTORIZER_CONTRACT = {
    "family": "TfidfVectorizer",
    "tokenization": "sklearn_word_unicode_v1",
    "ngramRange": [1, 2],
    "minimumDocumentFrequency": 1,
    "sublinearTf": True,
    "languageNormalization": "unicode_whitespace_casefold_v1",
    "preprocessingVersion": "forum-text-preprocessing-v1",
    "abstentionPolicyVersion": "forum-advisory-policy-v1",
    "abstentionThreshold": 0.60,
}


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
        normalized = normalize_forum_text(text)
        probabilities = self.pipeline.predict_proba([normalized])[0]
        labels = list(self.pipeline.classes_)
        index = max(range(len(probabilities)), key=probabilities.__getitem__)
        label = str(labels[index])
        probability = float(probabilities[index])
        # Preserve uncertainty rather than presenting an uncalibrated score as
        # confidence.  Authors can always edit and resubmit their explanation.
        if probability < float(VECTORIZER_CONTRACT["abstentionThreshold"]):
            label = UNCERTAIN
        elif label == CONTROLLED_SUFFICIENT:
            label = SUFFICIENT
        elif label == CONTROLLED_REVISION:
            label = REVISION
        return ForumPrediction(label, probability, self.model_version)

    def save(self, path: str | Path) -> None:
        Path(path).write_bytes(self.to_bytes())

    def to_bytes(self) -> bytes:
        buffer = io.BytesIO()
        joblib.dump({"modelVersion": self.model_version, "pipeline": self.pipeline}, buffer)
        return buffer.getvalue()

    @classmethod
    def load(cls, path: str | Path) -> "ForumTextClassifier":
        saved = joblib.load(path)
        if not isinstance(saved, dict) or not isinstance(saved.get("pipeline"), Pipeline):
            raise ValueError("forum model artifact is invalid")
        version = saved.get("modelVersion")
        if not isinstance(version, str) or not version:
            raise ValueError("forum model version is missing")
        return cls(saved["pipeline"], model_version=version)


def normalize_forum_text(text: str) -> str:
    return " ".join(text.casefold().split())


def build_forum_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        ngram_range=tuple(VECTORIZER_CONTRACT["ngramRange"]),
        min_df=int(VECTORIZER_CONTRACT["minimumDocumentFrequency"]),
        sublinear_tf=bool(VECTORIZER_CONTRACT["sublinearTf"]),
    )


def train_classifier(
    rows: Iterable[tuple[str, str]],
    *,
    model_version: str = MODEL_VERSION,
    variant: str = "ComplementNB",
) -> ForumTextClassifier:
    values = [(normalize_forum_text(text), label) for text, label in rows if text.strip()]
    labels = {label for _, label in values}
    allowed_pairs = ({SUFFICIENT, REVISION}, {CONTROLLED_SUFFICIENT, CONTROLLED_REVISION})
    if len(values) < 4 or labels not in allowed_pairs:
        raise ValueError("training needs reviewed examples for both rubric labels")
    if variant not in NAIVE_BAYES_VARIANTS:
        raise ValueError("forum classifier variant must be MultinomialNB or ComplementNB")
    estimator = ComplementNB(alpha=0.5) if variant == "ComplementNB" else MultinomialNB(alpha=0.5)
    pipeline = Pipeline([
        ("tfidf", build_forum_vectorizer()),
        ("classifier", estimator),
    ])
    pipeline.fit([text for text, _ in values], [label for _, label in values])
    return ForumTextClassifier(pipeline, model_version=model_version)
