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
    CONTROLLED_DEMO_PROVENANCE,
    DataSufficiency,
    PredictionContract,
    PairAuditSummary,
    SupervisedExample,
    assess_data_sufficiency,
    feature_names,
    BKT_FEATURE_NAME,
)

from .common import grouped_binary_holdout_split, grouped_holdout_split, matrix_and_target
from .train_decision_tree import train_decision_tree
from .train_mlp import train_mlp
from .train_xgboost import train_xgboost


RANDOM_SEED = 20260716
EVALUATION_STATUS_EVALUATED = "evaluated"
EVALUATION_STATUS_CATALOGUE_INSUFFICIENT = "catalogue_insufficient"


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
    pair_audit_summary: PairAuditSummary | None = None
    telemetry_readiness_status: str = "not_audited"
    evaluation_status: str = EVALUATION_STATUS_EVALUATED
    train_evaluation_group_keys: tuple[str, ...] = ()
    test_evaluation_group_keys: tuple[str, ...] = ()

    def to_document(self) -> dict[str, object]:
        return {
            "targetName": self.contract.target_name,
            "labelVersion": self.contract.label_version,
            "masteryCriterion": self.contract.mastery_criterion,
            "featureSchemaVersion": self.contract.feature_schema_version,
            "claimLevel": self.data_sufficiency.claim_level,
            "evaluationStatus": self.evaluation_status,
            "limitation": self.data_sufficiency.reason,
            "exampleCount": self.data_sufficiency.example_count,
            "studentCount": self.data_sufficiency.student_count,
            "supportNeededCount": self.data_sufficiency.support_needed_count,
            "supportNotNeededCount": self.data_sufficiency.support_not_needed_count,
            "trainAttemptIds": list(self.train_attempt_ids),
            "testAttemptIds": list(self.test_attempt_ids),
            "trainEvaluationGroupKeys": list(self.train_evaluation_group_keys),
            "testEvaluationGroupKeys": list(self.test_evaluation_group_keys),
            "randomSeed": self.random_seed,
            "telemetryReadinessStatus": self.telemetry_readiness_status,
            "pairAudit": self.pair_audit_summary.to_document() if self.pair_audit_summary else None,
            "models": [
                {"algorithm": result.algorithm, "features": list(result.feature_names), "metrics": dict(result.metrics)}
                for result in self.results
            ],
        }

    def sha256(self) -> str:
        document = self.to_document()
        for model in document["models"]:
            model["metrics"].pop("inference_latency_ms", None)
        return sha256(json.dumps(document, sort_keys=True).encode("utf-8")).hexdigest()


def evaluate_fair_comparison(
    examples: Iterable[SupervisedExample],
    *,
    random_seed: int = RANDOM_SEED,
    pair_audit_summary: PairAuditSummary | None = None,
    telemetry_readiness_status: str = "not_audited",
    allow_synthetic_test: bool = False,
    allow_controlled_demo: bool = False,
) -> ComparisonReport:
    """Evaluate all comparison models on exactly one grouped holdout split."""
    rows = tuple(examples)
    contract = rows[0].contract if rows else PredictionContract()
    if any(row.contract != contract for row in rows):
        raise ValueError("all examples must share one frozen prediction contract")
    if random_seed != RANDOM_SEED:
        raise ValueError(f"U7 requires deterministic random seed {RANDOM_SEED}")
    if telemetry_readiness_status not in {"not_audited", "ready", "not_ready"}:
        raise ValueError("telemetry_readiness_status is not recognized")
    readiness = assess_data_sufficiency(rows)
    synthetic_execution = allow_synthetic_test and rows and all(row.provenance == "synthetic_test" for row in rows)
    controlled_execution = allow_controlled_demo and rows and all(
        row.provenance == CONTROLLED_DEMO_PROVENANCE for row in rows
    )
    if not readiness.can_compare and not synthetic_execution and not controlled_execution:
        return ComparisonReport(contract, readiness, (), (), (), random_seed, pair_audit_summary, telemetry_readiness_status)
    if controlled_execution:
        partition = grouped_binary_holdout_split(rows, random_seed=random_seed)
        if partition is None:
            insufficient = replace(
                readiness,
                reason="catalogue insufficient: both target classes are required in grouped training and held-out evaluation partitions",
            )
            return ComparisonReport(
                contract=contract,
                data_sufficiency=insufficient,
                train_attempt_ids=(),
                test_attempt_ids=(),
                results=(),
                random_seed=random_seed,
                pair_audit_summary=pair_audit_summary,
                telemetry_readiness_status=telemetry_readiness_status,
                evaluation_status=EVALUATION_STATUS_CATALOGUE_INSUFFICIENT,
            )
        train, test = partition
    else:
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
        pair_audit_summary=pair_audit_summary,
        telemetry_readiness_status=telemetry_readiness_status,
        evaluation_status=EVALUATION_STATUS_EVALUATED,
        train_evaluation_group_keys=tuple(sorted({row.evaluation_group_key for row in train})),
        test_evaluation_group_keys=tuple(sorted({row.evaluation_group_key for row in test})),
    )


def evaluate_bkt_ablation(
    base_examples: Iterable[SupervisedExample],
    bkt_examples: Iterable[SupervisedExample],
    *,
    random_seed: int = RANDOM_SEED,
    allow_synthetic_test: bool = False,
) -> Mapping[str, ComparisonReport]:
    """Compare the same rows with and without the separately named BKT feature."""
    base_rows = tuple(base_examples)
    bkt_rows = tuple(bkt_examples)
    if len(base_rows) != len(bkt_rows):
        raise ValueError("BKT ablation must use the identical labelled attempt rows")
    for base_row, bkt_row in zip(base_rows, bkt_rows):
        if (
            (base_row.attempt_id, base_row.student_key, base_row.evaluation_group_key, base_row.subtopic_id, base_row.observed_at, base_row.target, base_row.contract)
            != (bkt_row.attempt_id, bkt_row.student_key, bkt_row.evaluation_group_key, bkt_row.subtopic_id, bkt_row.observed_at, bkt_row.target, bkt_row.contract)
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
        "without_bkt": evaluate_fair_comparison(base_rows, random_seed=random_seed, allow_synthetic_test=allow_synthetic_test),
        "with_bkt": evaluate_fair_comparison(bkt_rows, random_seed=random_seed, allow_synthetic_test=allow_synthetic_test),
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
            "bundleSchemaVersion": "xgboost-risk-bundle-v1",
        },
        "model": result.model,
    }
    import joblib

    joblib.dump(document, output)
    artifact_hash = _file_sha256(output)
    manifest_hash = sha256(json.dumps(document["manifest"], sort_keys=True).encode("utf-8")).hexdigest()
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
        artifact_manifest_sha256=manifest_hash,
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
        "bundleSchemaVersion": "xgboost-risk-bundle-v1",
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
        f"- Telemetry readiness: `{document['telemetryReadinessStatus']}`",
        "",
        "| Model | Features | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Log loss | Brier |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in document["models"]:
        metrics = model["metrics"]
        lines.append(
            "| {algorithm} | {features} | {accuracy} | {precision} | {recall} | {f1} | {roc_auc} | {pr_auc} | {log_loss} | {brier_score} |".format(
                algorithm=model["algorithm"], features=", ".join(model["features"]), **metrics,
            )
        )
    pair_audit = document["pairAudit"]
    if pair_audit:
        lines.extend(["", "## Pair audit", "", *(f"- {key}: {value}" for key, value in pair_audit.items())])
    lines.extend(["", "Do not claim model superiority without approved repeated grouped/held-out real-data results."])
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
        accuracy_score, average_precision_score, brier_score_loss, confusion_matrix, f1_score, log_loss,
        precision_score, recall_score, roc_auc_score,
    )

    return {
        "accuracy": round(float(accuracy_score(targets, predictions)), 6),
        "precision": round(float(precision_score(targets, predictions, zero_division=0)), 6),
        "recall": round(float(recall_score(targets, predictions, zero_division=0)), 6),
        "f1": round(float(f1_score(targets, predictions, zero_division=0)), 6),
        "roc_auc": round(float(roc_auc_score(targets, probabilities)), 6) if len(set(targets)) == 2 else None,
        "pr_auc": round(float(average_precision_score(targets, probabilities)), 6) if len(set(targets)) == 2 else None,
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


# ---------------------------------------------------------------------------
# External (ASSISTments) real-data comparison path.
#
# These helpers implement the approved v2 external evaluation on top of the
# existing frozen trainers and metric definitions.  Native Logic Oasis
# validation is not weakened: the external path requires provenance
# external_real, the frozen split supplied by the protected manifest, and the
# exact quiz-attempt-features-v2 columns.  No artifact is promoted.
# ---------------------------------------------------------------------------

EXTERNAL_PROVENANCE = "external_real"
EXTERNAL_ARTIFACT_STATUS = "evidence_only_external"
EXTERNAL_FEATURE_COLUMNS = ("correct_rate", "mean_response_time_ms")


@dataclass(frozen=True)
class ExternalComparisonReport:
    contract_version: str
    dataset_version: str
    random_seed: int
    feature_names: tuple[str, ...]
    train_learner_count: int
    train_row_count: int
    train_class_counts: Mapping[str, int]
    test_learner_count: int
    test_row_count: int
    test_class_counts: Mapping[str, int]
    row_identity_sha256: str
    train_identity_sha256: str
    test_identity_sha256: str
    results: tuple[ModelResult, ...]
    training_time_seconds: Mapping[str, float]
    baseline: Mapping[str, float]
    artifact_status: str = EXTERNAL_ARTIFACT_STATUS


@dataclass(frozen=True)
class GroupedFoldResult:
    fold_index: int
    train_learner_count: int
    validation_learner_count: int
    validation_learner_keys: tuple[str, ...]
    train_class_counts: Mapping[str, int]
    validation_class_counts: Mapping[str, int]
    results: tuple[ModelResult, ...]


@dataclass(frozen=True)
class GroupedStabilityReport:
    n_folds: int
    random_seed: int
    feature_names: tuple[str, ...]
    folds: tuple[GroupedFoldResult, ...]
    per_model_metrics: Mapping[str, Mapping[str, Mapping[str, float]]]


def evaluate_external_fair_comparison(
    examples: Iterable[SupervisedExample],
    *,
    random_seed: int,
    train_learner_keys: Iterable[str],
    test_learner_keys: Iterable[str],
    contract_version: str,
    dataset_version: str,
    extra_feature: str | None = None,
) -> ExternalComparisonReport:
    """Fit and evaluate DT/XGBoost/MLP once on the frozen external split."""
    rows = tuple(examples)
    if not rows:
        raise ValueError("external examples are required")
    if any(row.provenance != EXTERNAL_PROVENANCE for row in rows):
        raise ValueError("external evaluation requires provenance external_real")
    if random_seed != RANDOM_SEED:
        raise ValueError(f"U7 requires deterministic random seed {RANDOM_SEED}")
    columns = feature_names(rows)
    expected_columns = EXTERNAL_FEATURE_COLUMNS
    if extra_feature is not None:
        expected_columns = EXTERNAL_FEATURE_COLUMNS + (extra_feature,)
    if columns != expected_columns:
        raise ValueError(f"external evaluation requires exactly {expected_columns}")

    train_keys = frozenset(train_learner_keys)
    test_keys = frozenset(test_learner_keys)
    if train_keys & test_keys:
        raise ValueError("frozen split learner groups must not overlap")
    train = tuple(row for row in rows if row.student_key in train_keys)
    test = tuple(row for row in rows if row.student_key in test_keys)
    if len(train) + len(test) != len(rows):
        raise ValueError("every external example must belong to exactly one frozen partition")
    for name, partition in (("training", train), ("held-out", test)):
        targets = {row.target for row in partition}
        if len(targets) != 2:
            raise ValueError(f"{name} partition must contain both target classes")

    trainers: tuple[tuple[str, Callable[..., tuple[object, tuple[str, ...]]]], ...] = (
        ("decision_tree", train_decision_tree),
        ("xgboost", train_xgboost),
        ("mlp", train_mlp),
    )
    results: list[ModelResult] = []
    training_time: dict[str, float] = {}
    for name, trainer in trainers:
        result, fit_seconds = _fit_and_evaluate(name, trainer, train, test, columns, random_seed)
        results.append(result)
        training_time[name] = fit_seconds

    true_count = sum(row.target for row in rows)
    prevalence = true_count / len(rows)
    baseline = {
        "positive_prevalence": round(prevalence, 6),
        "majority_class_accuracy": round(max(prevalence, 1 - prevalence), 6),
    }
    return ExternalComparisonReport(
        contract_version=contract_version,
        dataset_version=dataset_version,
        random_seed=random_seed,
        feature_names=columns,
        train_learner_count=len({row.student_key for row in train}),
        train_row_count=len(train),
        train_class_counts=_class_counts(train),
        test_learner_count=len({row.student_key for row in test}),
        test_row_count=len(test),
        test_class_counts=_class_counts(test),
        row_identity_sha256=row_identity_sha256(rows, partition="all"),
        train_identity_sha256=row_identity_sha256(train, partition="train"),
        test_identity_sha256=row_identity_sha256(test, partition="test"),
        results=tuple(results),
        training_time_seconds=training_time,
        baseline=baseline,
    )


def _fit_and_evaluate(
    name: str,
    trainer: Callable[..., tuple[object, tuple[str, ...]]],
    train: tuple[SupervisedExample, ...],
    test: tuple[SupervisedExample, ...],
    columns: tuple[str, ...],
    random_seed: int,
) -> tuple[ModelResult, float]:
    started = perf_counter()
    model, trained_columns = trainer(train, random_seed=random_seed)
    fit_seconds = perf_counter() - started
    if trained_columns != columns:
        raise ValueError("all models must train with the same feature columns")
    matrix, targets, _ = matrix_and_target(test, columns)
    prediction_started = perf_counter()
    probabilities = [float(row[1]) for row in model.predict_proba(matrix)]
    predictions = [int(value) for value in model.predict(matrix)]
    latency_ms = (perf_counter() - prediction_started) * 1000
    return ModelResult(name, columns, _metrics(targets, predictions, probabilities, latency_ms, model), model), fit_seconds


def row_identity_sha256(
    examples: Iterable[SupervisedExample],
    *,
    partition: str,
) -> str:
    """Deterministic identity hash over rows, features, labels, and partition."""
    lines = sorted(
        (
            f"{row.attempt_id}|{row.student_key}|{row.features['correct_rate']}|"
            f"{row.features['mean_response_time_ms']}|{int(row.target)}|{partition}"
        )
        for row in examples
    )
    return sha256("\n".join(lines).encode("utf-8")).hexdigest()


def repeated_grouped_validation(
    examples: Iterable[SupervisedExample],
    *,
    random_seed: int,
    n_folds: int = 5,
    extra_feature: str | None = None,
) -> GroupedStabilityReport:
    """Training-only deterministic student-grouped stability evaluation.

    Learners are grouped and never split across fold boundaries; preprocessing
    is refit inside each fold (the MLP pipeline scales on fold-training data
    only); the frozen held-out learners are not present in ``examples``.
    """
    from random import Random

    rows = tuple(examples)
    if not rows:
        raise ValueError("grouped validation examples are required")
    if any(row.provenance != EXTERNAL_PROVENANCE for row in rows):
        raise ValueError("grouped external validation requires provenance external_real")
    if random_seed != RANDOM_SEED:
        raise ValueError(f"U7 requires deterministic random seed {RANDOM_SEED}")
    columns = feature_names(rows)
    expected_columns = EXTERNAL_FEATURE_COLUMNS
    if extra_feature is not None:
        expected_columns = EXTERNAL_FEATURE_COLUMNS + (extra_feature,)
    if columns != expected_columns:
        raise ValueError(f"external grouped validation requires exactly {expected_columns}")
    groups = sorted({row.student_key for row in rows})
    if len(groups) < n_folds:
        raise ValueError("grouped validation requires at least n_folds learners")

    shuffled = list(groups)
    Random(random_seed).shuffle(shuffled)
    folds = [set(shuffled[index::n_folds]) for index in range(n_folds)]

    trainers: tuple[tuple[str, Callable[..., tuple[object, tuple[str, ...]]]], ...] = (
        ("decision_tree", train_decision_tree),
        ("xgboost", train_xgboost),
        ("mlp", train_mlp),
    )
    fold_results: list[GroupedFoldResult] = []
    for index, validation_groups in enumerate(folds):
        validation = tuple(row for row in rows if row.student_key in validation_groups)
        training = tuple(row for row in rows if row.student_key not in validation_groups)
        if len({row.target for row in training}) != 2:
            raise ValueError("grouped fold training partition must contain both target classes")
        per_model: list[ModelResult] = []
        for name, trainer in trainers:
            model, trained_columns = trainer(training, random_seed=random_seed)
            if trained_columns != columns:
                raise ValueError("all models must train with the same feature columns")
            matrix, targets, _ = matrix_and_target(validation, columns)
            probabilities = [float(row[1]) for row in model.predict_proba(matrix)]
            predictions = [int(value) for value in model.predict(matrix)]
            per_model.append(
                ModelResult(name, columns, _metrics(targets, predictions, probabilities, 0.0, model), model)
            )
        fold_results.append(
            GroupedFoldResult(
                fold_index=index,
                train_learner_count=len({row.student_key for row in training}),
                validation_learner_count=len(validation_groups),
                validation_learner_keys=tuple(sorted(validation_groups)),
                train_class_counts=_class_counts(training),
                validation_class_counts=_class_counts(validation),
                results=tuple(per_model),
            )
        )
    return GroupedStabilityReport(
        n_folds=n_folds,
        random_seed=random_seed,
        feature_names=columns,
        folds=tuple(fold_results),
        per_model_metrics=_stability_summary(fold_results, columns),
    )


def _class_counts(rows: tuple[SupervisedExample, ...]) -> Mapping[str, int]:
    return {"true": sum(row.target for row in rows), "false": sum(not row.target for row in rows)}


def _stability_summary(
    folds: list[GroupedFoldResult],
    columns: tuple[str, ...],
) -> Mapping[str, Mapping[str, Mapping[str, float]]]:
    metric_keys = ("accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "log_loss", "brier_score")
    algorithms = [result.algorithm for result in folds[0].results]
    summary: dict[str, dict[str, dict[str, float]]] = {}
    for algorithm in algorithms:
        summary[algorithm] = {}
        for metric in metric_keys:
            values = [
                float(fold_result.results[index].metrics[metric])
                for fold_result in folds
                for index, result in enumerate(fold_result.results)
                if result.algorithm == algorithm and fold_result.results[index].metrics.get(metric) is not None
            ]
            if not values:
                continue
            mean = sum(values) / len(values)
            variance = sum((value - mean) ** 2 for value in values) / len(values)
            summary[algorithm][metric] = {"mean": round(mean, 6), "std": round(variance**0.5, 6), "n": len(values)}
    return summary
