"""J4 runner: frozen external DT/XGBoost/MLP comparison on the v2 Grade 6 set.

Loads the protected v2 model/audit tables and the frozen split manifest,
verifies the exact feature matrix, fits the three frozen classifiers once,
evaluates them once on the frozen held-out partition, and adds training-only
repeated student-grouped stability evidence.  No artifact is promoted.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd

from logic_oasis_ai.prediction_contract import SupervisedExample

from .assistments_contract import PROVENANCE
from .j2_contract import J2_CONTRACT_VERSION_V2
from training.evaluate_models import (
    EXTERNAL_FEATURE_COLUMNS,
    EXTERNAL_PROVENANCE,
    RANDOM_SEED,
    evaluate_external_fair_comparison,
    repeated_grouped_validation,
)


MODEL_TABLE_FIELDS = ("correct_rate", "mean_response_time_ms", "next_attempt_support_needed")


def load_dataset(processed_dir: Path) -> tuple[list[SupervisedExample], dict[str, Any]]:
    model_path = processed_dir / "u7_model_table_v2.csv"
    audit_path = processed_dir / "u7_audit_table_v2.csv"
    readiness_path = processed_dir / "u7_v2_readiness_manifest.json"
    for path in (model_path, audit_path, readiness_path):
        if not path.exists():
            raise FileNotFoundError(f"missing protected input: {path}")

    with model_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(MODEL_TABLE_FIELDS):
            raise ValueError("model matrix must contain exactly the three frozen columns")
        model_rows = list(reader)
    audit_frame = pd.read_csv(audit_path, dtype=str, keep_default_na=False)
    if len(audit_frame) != len(model_rows):
        raise ValueError("model table and audit table row counts must match")

    examples: list[SupervisedExample] = []
    for model_row, audit in zip(model_rows, audit_frame.to_dict("records")):
        examples.append(
            SupervisedExample(
                attempt_id=str(audit["currentEpisodeId"]),
                student_key=str(audit["externalStudentKey"]),
                subtopic_id=str(audit["externalSkillCode"]),
                observed_at=pd.to_datetime(audit["currentEpisodeStartedAt"], format="ISO8601", utc=True, errors="coerce").to_pydatetime(),
                features={
                    "correct_rate": float(model_row["correct_rate"]),
                    "mean_response_time_ms": float(model_row["mean_response_time_ms"]),
                },
                target=str(model_row["next_attempt_support_needed"]).strip().lower() == "true",
                contract=None,
                provenance=EXTERNAL_PROVENANCE,
                evaluation_group_key=str(audit["externalStudentKey"]),
            )
        )
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    return examples, readiness


def frozen_split_from(readiness: dict[str, Any]) -> tuple[list[str], list[str]]:
    split = readiness.get("studentGroupedSplit")
    if not split or readiness.get("splitSeed") != RANDOM_SEED:
        raise ValueError("frozen split manifest missing or seed mismatch")
    train_keys = list(split[0]["learnerKeys"])
    test_keys = list(split[1]["learnerKeys"])
    if set(train_keys) & set(test_keys):
        raise ValueError("frozen split learners overlap")
    return train_keys, test_keys


def conclusion_level(
    external: Any,
    stability: Any,
) -> tuple[str, str]:
    """Interpret results: A/B/C per the frozen J4 interpretation rule."""
    by_algorithm = {result.algorithm: result for result in external.results}
    stability_means = {
        algorithm: metrics.get("roc_auc", {}).get("mean")
        for algorithm, metrics in stability.per_model_metrics.items()
    }
    stability_means = {k: v for k, v in stability_means.items() if v is not None}
    if not stability_means:
        return "MODEL COMPARISON COMPLETED", "no stable grouped ROC-AUC estimates available"
    stability_best = max(stability_means, key=stability_means.get)
    ordered = sorted(stability_means.items(), key=lambda item: item[1], reverse=True)
    gap = ordered[0][1] - ordered[1][1] if len(ordered) > 1 else 0.0

    held_out_roc = by_algorithm[stability_best].metrics.get("roc_auc")
    held_out_best = max(by_algorithm, key=lambda name: by_algorithm[name].metrics.get("roc_auc") or 0.0)

    if held_out_best != stability_best:
        return "INCONCLUSIVE", f"held-out best model ({held_out_best}) differs from grouped best ({stability_best})"
    if gap >= 0.01 and held_out_roc is not None and held_out_roc >= 0.5:
        return "CAUTIOUS DATASET-BOUNDED ADVANTAGE", f"{stability_best} shows a stable grouped advantage (ROC-AUC gap {gap:.3f}) and directionally compatible held-out evidence (ROC-AUC {held_out_roc:.3f})"
    return "MODEL COMPARISON COMPLETED", "metrics exist but no stable advantage is established"


def write_report(
    external: Any,
    stability: Any,
    readiness: dict[str, Any],
    *,
    report_path: Path,
    configs: dict[str, str],
) -> tuple[str, str]:
    level, reason = conclusion_level(external, stability)
    lines = [
        "# U7 ASSISTments External-Real Model Comparison (J4, v2 Grade 6)",
        "",
        f"- Contract: `{J2_CONTRACT_VERSION_V2}`",
        f"- Dataset version: `{readiness.get('releaseId', 'assistments-edm-cup-2023-release-v1')}`",
        f"- Provenance: `{PROVENANCE}`; artifact status: **{external.artifact_status}**",
        f"- Mastery criterion: `0.60`; split seed: `{RANDOM_SEED}`",
        f"- Feature columns: `{', '.join(external.feature_names)}`",
        "",
        "## Model configurations (frozen)",
        "",
    ]
    for name, config in configs.items():
        lines.append(f"- **{name}**: `{config}`")
    lines.extend(
        [
            "",
            "## Frozen split",
            "",
            f"- Training: {external.train_row_count} rows / {external.train_learner_count} learners "
            f"(true {external.train_class_counts['true']}, false {external.train_class_counts['false']})",
            f"- Held-out: {external.test_row_count} rows / {external.test_learner_count} learners "
            f"(true {external.test_class_counts['true']}, false {external.test_class_counts['false']})",
            f"- Row identity SHA-256 (all): `{external.row_identity_sha256}`",
            f"- Train identity SHA-256: `{external.train_identity_sha256}`; held-out identity SHA-256: `{external.test_identity_sha256}`",
            "",
            "## Baseline context",
            "",
            f"- Positive-class prevalence: {external.baseline['positive_prevalence']:.3f}",
            f"- Majority-class accuracy: {external.baseline['majority_class_accuracy']:.3f}",
            "",
            "## Frozen held-out results (evaluated once)",
            "",
            "| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Log loss | Brier |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for result in external.results:
        metrics = result.metrics
        lines.append(
            "| {name} | {accuracy} | {precision} | {recall} | {f1} | {roc_auc} | {pr_auc} | {log_loss} | {brier_score} |".format(
                name=result.algorithm,
                accuracy=metrics["accuracy"],
                precision=metrics["precision"],
                recall=metrics["recall"],
                f1=metrics["f1"],
                roc_auc=metrics["roc_auc"],
                pr_auc=metrics["pr_auc"],
                log_loss=metrics["log_loss"],
                brier_score=metrics["brier_score"],
            )
        )
    lines.extend(["", "Confusion matrices (held-out, rows=predicted, cols=true/false):"])
    for result in external.results:
        lines.append(f"- **{result.algorithm}**: {result.metrics['confusion_matrix']}")
    lines.extend(
        [
            "",
            "## Training-only repeated student-grouped stability (5 folds, held-out learners excluded)",
            "",
            f"- Folds: {stability.n_folds}; seed: {stability.random_seed}",
            f"- Learners per validation fold: {[fold.validation_learner_count for fold in stability.folds]}",
        ]
    )
    for algorithm, metrics in stability.per_model_metrics.items():
        lines.append("")
        lines.append(f"### {algorithm} (mean +/- std across folds)")
        lines.append("")
        lines.append("| Metric | Mean | Std | n |")
        lines.append("| --- | ---: | ---: | ---: |")
        for metric, values in metrics.items():
            lines.append(f"| {metric} | {values['mean']} | {values['std']} | {values['n']} |")
    lines.extend(
        [
            "",
            "## Training/preprocessing confirmation",
            "",
            "- MLP `StandardScaler` is fit inside `train_mlp` on training learners only (pipeline fitted per fold and once on the frozen training partition); held-out data is never used for fitting.",
            "- DT/XGBoost use only their existing declared preprocessing.",
            f"- Training time (seconds): {json.dumps(external.training_time_seconds)}",
            "",
            "## Limitations",
            "",
            "- Held-out contains only **2 independent learners and 25 rows (2 positives)**; metrics are reported with this limitation and cannot alone support a cautious-superiority claim.",
            "- Evidence is ASSISTments external U.S.-curriculum data; it is **not direct KSSR validation** and no generalization to Logic Oasis target users is claimed.",
            "- Class imbalance (~19% positive) means accuracy near 81% equals the majority baseline; precision/recall/F1/PR-AUC and probability quality must be read alongside accuracy.",
            "",
            "## Conclusion",
            "",
            f"- Level: **{level}**",
            f"- Rationale: {reason}",
            "",
            "No model artifact was promoted; all artifacts remain `evidence_only_external`.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return level, reason


def main() -> None:
    parser = argparse.ArgumentParser(description="J4 external model comparison")
    parser.add_argument("--processed-dir", required=True, help="Protected v2 directory with model/audit/split files")
    parser.add_argument("--report", default=None, help="Repository report path (default ai_pipeline/reports/u7_assistments_j4_model_comparison.md)")
    parser.add_argument("--j4-manifest-out", default=None, help="Protected J4 manifest output path")
    args = parser.parse_args()

    processed = Path(args.processed_dir)
    examples, readiness = load_dataset(processed)
    train_keys, test_keys = frozen_split_from(readiness)

    external = evaluate_external_fair_comparison(
        examples,
        random_seed=RANDOM_SEED,
        train_learner_keys=train_keys,
        test_learner_keys=test_keys,
        contract_version=readiness.get("contractVersion", J2_CONTRACT_VERSION_V2),
        dataset_version=readiness.get("releaseId", "assistments-edm-cup-2023-release-v1"),
    )
    training_examples = tuple(row for row in examples if row.student_key in set(train_keys))
    stability = repeated_grouped_validation(training_examples, random_seed=RANDOM_SEED, n_folds=5)

    repo_dir = Path(__file__).resolve().parents[2]
    report_path = Path(args.report) if args.report else repo_dir / "reports" / "u7_assistments_j4_model_comparison.md"
    configs = {
        "Decision Tree": "max_depth=4, min_samples_leaf=2, class_weight=balanced, random_state=20260716",
        "XGBoost": "n_estimators=40, max_depth=3, learning_rate=0.08, subsample=0.9, colsample_bytree=0.9, n_jobs=1, random_state=20260716 (existing XGBOOST_PARAMETERS)",
        "MLP": "StandardScaler + MLP(hidden_layer_sizes=(8,), alpha=0.01, early_stopping=False, max_iter=500, tol=0.01, random_state=20260716)",
    }
    level, reason = write_report(external, stability, readiness, report_path=report_path, configs=configs)

    j4_manifest = {
        "manifestSchemaVersion": "assistments-j4-external-comparison-v1",
        "contractVersion": external.contract_version,
        "datasetVersion": external.dataset_version,
        "provenance": PROVENANCE,
        "artifactStatus": external.artifact_status,
        "randomSeed": external.random_seed,
        "featureNames": list(external.feature_names),
        "train": {"learners": external.train_learner_count, "rows": external.train_row_count, "classCounts": dict(external.train_class_counts)},
        "heldOut": {"learners": external.test_learner_count, "rows": external.test_row_count, "classCounts": dict(external.test_class_counts)},
        "rowIdentitySha256": external.row_identity_sha256,
        "trainIdentitySha256": external.train_identity_sha256,
        "testIdentitySha256": external.test_identity_sha256,
        "heldOutResults": {
            result.algorithm: {
                "metrics": {key: value for key, value in result.metrics.items() if key != "model"},
                "featureNames": list(result.feature_names),
            }
            for result in external.results
        },
        "trainingTimeSeconds": dict(external.training_time_seconds),
        "baseline": dict(external.baseline),
        "groupedStability": {
            "nFolds": stability.n_folds,
            "seed": stability.random_seed,
            "perModelMetrics": {
                algorithm: {metric: dict(values) for metric, values in metrics.items()}
                for algorithm, metrics in stability.per_model_metrics.items()
            },
        },
        "conclusion": {"level": level, "reason": reason},
        "containsRawIdentifiers": False,
        "containsSecretMaterial": False,
    }
    if args.j4_manifest_out:
        manifest_path = Path(args.j4_manifest_out)
        manifest_path.write_text(json.dumps(j4_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"J4 manifest: {manifest_path}")
    print(f"report: {report_path}")
    print(json.dumps({"conclusion": level, "reason": reason, "heldOutRoc": {r.algorithm: r.metrics.get("roc_auc") for r in external.results}}, indent=2))


if __name__ == "__main__":
    main()
