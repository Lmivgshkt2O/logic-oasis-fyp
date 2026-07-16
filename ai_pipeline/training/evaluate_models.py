"""Fair, reproducible U7 comparison and XGBoost bundle lifecycle helpers."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import pickle
from time import perf_counter
from typing import Callable, Iterable, Mapping

from logic_oasis_ai.model_registry import ModelArtifact
from logic_oasis_ai.prediction_contract import (
    DataSufficiency,
    PredictionContract,
    SupervisedExample,
    assess_data_sufficiency,
    feature_names,
    BKT_FEATURE_NAME,
)

from .common import grouped_holdout_split, matrix_and_target
from .train_decision_tree import train_decision_tree
from .train_mlp import train_mlp
from .train_xgboost import train_xgboost


RANDOM_SEED = 20260716


@dataclass(frozen=True)
class ModelResult:
    algorithm: str
    feature_names: tuple[str, ...]
    metrics: Mapping[str, object]
    model: object


@dataclass(frozen=True)
class ComparisonReport:
    contract: PredictionContract
    data_sufficiency: DataSufficiency
    train_attempt_ids: tuple[str, ...]
    test_attempt_ids: tuple[str, ...]
    results: tuple[ModelResult, ...]
    random_seed: int

    def to_document(self) -> dict[str, object]:
        return {
            "targetName": self.contract.target_name,
            "labelVersion": self.contract.label_version,
            "masteryCriterion": self.contract.mastery_criterion,
            "featureSchemaVersion": self.contract.feature_schema_version,
            "claimLevel": self.data_sufficiency.claim_level,
            "limitation": self.data_sufficiency.reason,
            "exampleCount": self.data_sufficiency.example_count,
            "studentCount": self.data_sufficiency.student_count,
            "supportNeededCount": self.data_sufficiency.support_needed_count,
            "supportNotNeededCount": self.data_sufficiency.support_not_needed_count,
            "trainAttemptIds": list(self.train_attempt_ids),
            "testAttemptIds": list(self.test_attempt_ids),
            "randomSeed": self.random_seed,
            "models": [
                {"algorithm": result.algorithm, "features": list(result.feature_names), "metrics": dict(result.metrics)}
                for result in self.results
            ],
        }

    def sha256(self) -> str:
        return sha256(json.dumps(self.to_document(), sort_keys=True).encode("utf-8")).hexdigest()


def evaluate_fair_comparison(
    examples: Iterable[SupervisedExample],
    *,
    random_seed: int = RANDOM_SEED,
) -> ComparisonReport:
    """Evaluate all comparison models on exactly one grouped holdout split."""
    rows = tuple(examples)
    contract = rows[0].contract if rows else PredictionContract()
    if any(row.contract != contract for row in rows):
        raise ValueError("all examples must share one frozen prediction contract")
    readiness = assess_data_sufficiency(rows)
    if not readiness.can_compare:
        return ComparisonReport(contract, readiness, (), (), (), random_seed)
    train, test = grouped_holdout_split(rows, random_seed=random_seed)
    if readiness.claim_level == "held_out_comparison" and len({row.target for row in test}) != 2:
        readiness = replace(
            readiness,
            claim_level="preliminary_comparison",
            reason="held-out student group does not contain both target classes",
        )
    columns = feature_names(rows)
    trainers: tuple[tuple[str, Callable[..., tuple[object, tuple[str, ...]]]], ...] = (
        ("decision_tree", train_decision_tree),
        ("xgboost", train_xgboost),
        ("mlp", train_mlp),
    )
    results = tuple(
        _evaluate_one(name, trainer, train, test, columns, random_seed)
        for name, trainer in trainers
    )
    return ComparisonReport(
        contract=contract,
        data_sufficiency=readiness,
        train_attempt_ids=tuple(row.attempt_id for row in train),
        test_attempt_ids=tuple(row.attempt_id for row in test),
        results=results,
        random_seed=random_seed,
    )


def evaluate_bkt_ablation(
    base_examples: Iterable[SupervisedExample],
    bkt_examples: Iterable[SupervisedExample],
    *,
    random_seed: int = RANDOM_SEED,
) -> Mapping[str, ComparisonReport]:
    """Compare the same rows with and without the separately named BKT feature."""
    base_rows = tuple(base_examples)
    bkt_rows = tuple(bkt_examples)
    if len(base_rows) != len(bkt_rows):
        raise ValueError("BKT ablation must use the identical labelled attempt rows")
    for base_row, bkt_row in zip(base_rows, bkt_rows):
        if (
            (base_row.attempt_id, base_row.student_key, base_row.subtopic_id, base_row.observed_at, base_row.target, base_row.contract)
            != (bkt_row.attempt_id, bkt_row.student_key, bkt_row.subtopic_id, bkt_row.observed_at, bkt_row.target, bkt_row.contract)
        ):
            raise ValueError("BKT ablation must use the identical labelled attempt rows")
        bkt_value = bkt_row.features.get(BKT_FEATURE_NAME)
        if (
            not isinstance(bkt_value, float)
            or not isfinite(bkt_value)
            or not 0.0 <= bkt_value <= 1.0
            or {key: value for key, value in bkt_row.features.items() if key != BKT_FEATURE_NAME} != dict(base_row.features)
            or set(bkt_row.features) != set(base_row.features) | {BKT_FEATURE_NAME}
        ):
            raise ValueError("BKT ablation may differ only by a valid BKT feature")
    return {
        "without_bkt": evaluate_fair_comparison(base_rows, random_seed=random_seed),
        "with_bkt": evaluate_fair_comparison(bkt_rows, random_seed=random_seed),
    }


def save_xgboost_bundle(
    report: ComparisonReport,
    output_path: str | Path,
    *,
    model_version: str,
    training_dataset_version: str,
) -> ModelArtifact:
    """Persist only an evaluated XGBoost candidate; promotion remains explicit."""
    result = next((item for item in report.results if item.algorithm == "xgboost"), None)
    if result is None:
        raise ValueError("an evaluated XGBoost result is required before saving a bundle")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    evaluation_report_sha256 = report.sha256()
    document = {
        "manifest": {
            "modelType": "xgboost",
            "modelVersion": model_version,
            "targetName": report.contract.target_name,
            "labelVersion": report.contract.label_version,
            "masteryCriterion": report.contract.mastery_criterion,
            "featureSchemaVersion": report.contract.feature_schema_version,
            "featureNames": list(result.feature_names),
            "trainingDatasetVersion": training_dataset_version,
            "evaluationReportSha256": evaluation_report_sha256,
        },
        "model": result.model,
    }
    import joblib

    joblib.dump(document, output)
    artifact_hash = _file_sha256(output)
    return ModelArtifact(
        artifact_id=f"xgboost-{model_version}",
        model_type="xgboost",
        model_version=model_version,
        feature_schema_version=report.contract.feature_schema_version,
        training_dataset_version=training_dataset_version,
        artifact_sha256=artifact_hash,
        prediction_target=report.contract.target_name,
        label_version=report.contract.label_version,
        mastery_criterion=report.contract.mastery_criterion,
        evaluation_status="evaluated",
        evaluation_report_sha256=evaluation_report_sha256,
        promotion_gate_status="not_passed",
    )


def load_xgboost_bundle(path: str | Path, *, contract: PredictionContract) -> Mapping[str, object]:
    import joblib

    document = joblib.load(path)
    manifest = document.get("manifest") if isinstance(document, dict) else None
    if not isinstance(manifest, dict) or "model" not in document:
        raise ValueError("model bundle is malformed")
    expected = {
        "modelType": "xgboost",
        "targetName": contract.target_name,
        "labelVersion": contract.label_version,
        "masteryCriterion": contract.mastery_criterion,
        "featureSchemaVersion": contract.feature_schema_version,
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("model bundle does not match the frozen prediction contract")
    return document


def write_comparison_report(report: ComparisonReport, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    document = report.to_document()
    lines = [
        "# U7 Model Comparison",
        "",
        f"- Target: `{document['targetName']}` ({document['labelVersion']})",
        f"- Mastery criterion: `{document['masteryCriterion']}`",
        f"- Claim level: **{document['claimLevel']}**",
        f"- Limitation: {document['limitation']}",
        f"- Examples/students: {document['exampleCount']} / {document['studentCount']}",
        "",
        "| Model | Features | Accuracy | Precision | Recall | F1 | ROC-AUC | Log loss | Brier |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in document["models"]:
        metrics = model["metrics"]
        lines.append(
            "| {algorithm} | {features} | {accuracy} | {precision} | {recall} | {f1} | {roc_auc} | {log_loss} | {brier_score} |".format(
                algorithm=model["algorithm"], features=", ".join(model["features"]), **metrics,
            )
        )
    lines.extend(["", "Do not claim model superiority without repeated grouped/held-out results."])
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _evaluate_one(name, trainer, train, test, columns, random_seed) -> ModelResult:
    model, trained_columns = trainer(train, random_seed=random_seed)
    if trained_columns != columns:
        raise ValueError("all models must train with the same feature columns")
    matrix, targets, _ = matrix_and_target(test, columns)
    started = perf_counter()
    probabilities = [float(row[1]) for row in model.predict_proba(matrix)]
    predictions = [int(value) for value in model.predict(matrix)]
    latency_ms = (perf_counter() - started) * 1000
    return ModelResult(name, columns, _metrics(targets, predictions, probabilities, latency_ms, model), model)


def _metrics(targets, predictions, probabilities, latency_ms, model) -> Mapping[str, object]:
    from sklearn.metrics import (
        accuracy_score, brier_score_loss, confusion_matrix, f1_score, log_loss,
        precision_score, recall_score, roc_auc_score,
    )

    return {
        "accuracy": round(float(accuracy_score(targets, predictions)), 6),
        "precision": round(float(precision_score(targets, predictions, zero_division=0)), 6),
        "recall": round(float(recall_score(targets, predictions, zero_division=0)), 6),
        "f1": round(float(f1_score(targets, predictions, zero_division=0)), 6),
        "roc_auc": round(float(roc_auc_score(targets, probabilities)), 6) if len(set(targets)) == 2 else None,
        "log_loss": round(float(log_loss(targets, probabilities, labels=[0, 1])), 6),
        "brier_score": round(float(brier_score_loss(targets, probabilities)), 6),
        "confusion_matrix": confusion_matrix(targets, predictions, labels=[0, 1]).tolist(),
        "inference_latency_ms": round(latency_ms, 6),
        "serialized_size_bytes": _serialized_size(model),
    }


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class _CountingWriter:
    def __init__(self) -> None:
        self.size = 0

    def write(self, chunk: bytes) -> int:
        self.size += len(chunk)
        return len(chunk)


def _serialized_size(model: object) -> int:
    writer = _CountingWriter()
    pickle.dump(model, writer)
    return writer.size
