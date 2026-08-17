"""Reproducible TF-IDF + Naive Bayes question-response relevance component.

The relevance component is separately governed from the reasoning classifier:
it decides whether a response addresses the question, and can abstain. It
never determines mathematical correctness and never emits a verification
badge; the composite policy in the runtime combines it with deterministic
correctness and the reasoning component.
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

from .classifier import normalize_forum_text


MODEL_VERSION = "forum-relevance-nb-v1"
RELEVANT = "relevant"
IRRELEVANT = "irrelevant"
RELEVANCE_UNCERTAIN = "uncertain"
RELEVANCE_LABELS = frozenset({RELEVANT, IRRELEVANT})
RELEVANCE_VARIANTS = frozenset({"ComplementNB", "MultinomialNB"})
RELEVANCE_CONTRACT = {
    "family": "TfidfVectorizer",
    "tokenization": "sklearn_word_unicode_v1",
    "ngramRange": [1, 2],
    "minimumDocumentFrequency": 1,
    "sublinearTf": True,
    "languageNormalization": "unicode_whitespace_casefold_v1",
    "preprocessingVersion": "forum-relevance-preprocessing-v1",
    "abstentionPolicyVersion": "forum-relevance-policy-v1",
    "positiveThreshold": 0.65,
    "negativeThreshold": 0.80,
}


@dataclass(frozen=True)
class ForumRelevancePrediction:
    label: str
    probability: float
    model_version: str
    calibration_state: str = "not_calibrated"


def relevance_input(prompt: str, text: str) -> str:
    return normalize_forum_text(f"{prompt} {text}")


class ForumRelevanceClassifier:
    def __init__(
        self, pipeline: Pipeline, *, model_version: str = MODEL_VERSION,
    ) -> None:
        self.pipeline = pipeline
        self.model_version = model_version

    def predict(self, prompt: str, text: str) -> ForumRelevancePrediction:
        normalized = relevance_input(prompt, text)
        probabilities = self.pipeline.predict_proba([normalized])[0]
        labels = list(self.pipeline.classes_)
        index = max(range(len(probabilities)), key=probabilities.__getitem__)
        label = str(labels[index])
        probability = float(probabilities[index])
        positive_threshold = float(RELEVANCE_CONTRACT["positiveThreshold"])
        negative_threshold = float(RELEVANCE_CONTRACT["negativeThreshold"])
        if label == RELEVANT and probability >= positive_threshold:
            return ForumRelevancePrediction(
                RELEVANT, probability, self.model_version,
            )
        if label == IRRELEVANT and probability >= negative_threshold:
            return ForumRelevancePrediction(
                IRRELEVANT, probability, self.model_version,
            )
        return ForumRelevancePrediction(
            RELEVANCE_UNCERTAIN, probability, self.model_version,
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_bytes(self.to_bytes())

    def to_bytes(self) -> bytes:
        buffer = io.BytesIO()
        joblib.dump(
            {"modelVersion": self.model_version, "pipeline": self.pipeline},
            buffer,
        )
        return buffer.getvalue()

    @classmethod
    def load(cls, path: str | Path) -> "ForumRelevanceClassifier":
        saved = joblib.load(path)
        if not isinstance(saved, dict) or not isinstance(
            saved.get("pipeline"), Pipeline,
        ):
            raise ValueError("forum relevance artifact is invalid")
        version = saved.get("modelVersion")
        if not isinstance(version, str) or not version:
            raise ValueError("forum relevance model version is missing")
        return cls(saved["pipeline"], model_version=version)


def build_relevance_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        ngram_range=tuple(RELEVANCE_CONTRACT["ngramRange"]),
        min_df=int(RELEVANCE_CONTRACT["minimumDocumentFrequency"]),
        sublinear_tf=bool(RELEVANCE_CONTRACT["sublinearTf"]),
    )


def train_relevance_classifier(
    rows: Iterable[tuple[str, str, str]],
    *,
    model_version: str = MODEL_VERSION,
    variant: str = "ComplementNB",
) -> ForumRelevanceClassifier:
    """Train from (prompt, response, relevance-label) controlled rows."""
    values = [
        (relevance_input(prompt, text), label)
        for prompt, text, label in rows
        if prompt.strip() and text.strip()
    ]
    labels = {label for _, label in values}
    if len(values) < 4 or labels != RELEVANCE_LABELS:
        raise ValueError(
            "relevance training needs reviewed examples for both relevance labels",
        )
    if variant not in RELEVANCE_VARIANTS:
        raise ValueError(
            "relevance classifier variant must be MultinomialNB or ComplementNB",
        )
    estimator = (
        ComplementNB(alpha=0.5)
        if variant == "ComplementNB"
        else MultinomialNB(alpha=0.5)
    )
    pipeline = Pipeline([
        ("tfidf", build_relevance_vectorizer()),
        ("classifier", estimator),
    ])
    pipeline.fit([text for text, _ in values], [label for _, label in values])
    return ForumRelevanceClassifier(pipeline, model_version=model_version)
