"""J5: SHAP, operational evidence, and the conditional BKT ablation.

J4 is frozen evidence and is not rewritten.  XGBoost SHAP explains the frozen
two-feature model; operational evidence is measured with one shared input
contract; BKT is a named temporal-mastery ablation using the frozen bkt-v1
parameters after rechecking the v2 lineage gate.  No artifact is promoted.
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from logic_oasis_ai.prediction_contract import SupervisedExample

from .assistments_contract import PROVENANCE
from .bkt_external import (
    bkt_lineage_gate,
    build_graded_observations,
    build_mastery_at_episodes,
    bkt_mastery_feature,
)
from .j2_contract import J2_CONTRACT_VERSION_V2
from .run_j4 import load_dataset, frozen_split_from
from .reconstruct_attempts import read_action_rows
from training import evaluate_models
from training.evaluate_models import (
    EXTERNAL_FEATURE_COLUMNS,
    EXTERNAL_PROVENANCE,
    RANDOM_SEED,
    evaluate_external_fair_comparison,
    repeated_grouped_validation,
    row_identity_sha256,
)
from training.train_decision_tree import train_decision_tree
from training.train_mlp import train_mlp
from training.train_xgboost import train_xgboost


BKT_FEATURE_NAME = "bkt_mastery_probability"
SHAP_MODEL_VERSION = "xgboost-risk-bundle-v1"


def feature_matrix(examples: Sequence[SupervisedExample], columns: tuple[str, ...]) -> np.ndarray:
    return np.asarray([[row.features[name] for name in columns] for row in examples], dtype=float)


def shap_global_summary(model: Any, examples: Sequence[SupervisedExample], columns: tuple[str, ...]) -> dict[str, Any]:
    import shap

    matrix = feature_matrix(examples, columns)
    explainer = shap.TreeExplainer(model)
    explanation = explainer(matrix)
    values = _positive_class_values(explanation.values)
    base_value = float(np.mean(np.asarray(explanation.base_values, dtype=float)))

    per_feature = {}
    for index, name in enumerate(columns):
        contributions = np.asarray(values[:, index], dtype=float)
        per_feature[name] = {
            "meanAbsShap": round(float(np.mean(np.abs(contributions))), 6),
            "meanShap": round(float(np.mean(contributions)), 6),
            "percentiles": {
                str(percentile): round(float(np.percentile(contributions, percentile)), 6)
                for percentile in (5, 25, 50, 75, 95)
            },
        }
    ranking = sorted(per_feature, key=lambda name: per_feature[name]["meanAbsShap"], reverse=True)
    return {
        "modelVersion": SHAP_MODEL_VERSION,
        "contractVersion": J2_CONTRACT_VERSION_V2,
        "featureNames": list(columns),
        "baseValue": round(base_value, 6),
        "explainedRows": len(examples),
        "perFeature": per_feature,
        "rankingByMeanAbsShap": ranking,
        "interpretationBoundary": "SHAP describes how the frozen XGBoost model's two input features contributed to its predicted support-risk probabilities; it is not causal evidence.",
    }


def _positive_class_values(values: Any) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 3:
        return arr[..., 1]
    return arr


def shap_local_examples(
    model: Any,
    examples: Sequence[SupervisedExample],
    columns: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Predeclared descriptive selection: low / median / high predicted risk."""
    import shap

    matrix = feature_matrix(examples, columns)
    probabilities = np.asarray([float(row[1]) for row in model.predict_proba(matrix)])
    explainer = shap.TreeExplainer(model)
    explanation = explainer(matrix)
    values = _positive_class_values(explanation.values)
    base_value = float(np.mean(np.asarray(explanation.base_values, dtype=float)))

    order = np.argsort(probabilities)
    picks = [order[0], order[len(order) // 2], order[-1]]
    labels = ["lowest_predicted_risk", "median_predicted_risk", "highest_predicted_risk"]
    exported = []
    for label, index in zip(labels, picks):
        exported.append(
            {
                "rule": label,
                "correct_rate": float(examples[index].features["correct_rate"]),
                "mean_response_time_ms": float(examples[index].features["mean_response_time_ms"]),
                "predicted_probability": round(float(probabilities[index]), 6),
                "base_value": round(base_value, 6),
                "shap_contributions": {
                    name: round(float(values[index, feature_index]), 6)
                    for feature_index, name in enumerate(columns)
                },
                "disclaimer": "example demonstrates model explanation only, not prediction accuracy or pedagogical causality",
            }
        )
    return exported


def operational_evidence(
    fitted: Mapping[str, Any],
    examples: Sequence[SupervisedExample],
    columns: tuple[str, ...],
) -> dict[str, Any]:
    matrix = feature_matrix(examples, columns)
    evidence = {}
    for name, model in fitted.items():
        serialized_size = len(pickle.dumps(model))
        # warm-up + repeated inference, identical input for every model
        for _ in range(3):
            model.predict_proba(matrix)
        latencies = []
        for _ in range(10):
            started = perf_counter()
            probabilities = model.predict_proba(matrix)
            latencies.append((perf_counter() - started) * 1000)
        finite = bool(np.isfinite(probabilities).all())
        evidence[name] = {
            "serializedSizeBytes": serialized_size,
            "inferenceLatencyMs": {
                "median": round(float(np.median(latencies)), 6),
                "mean": round(float(np.mean(latencies)), 6),
                "runs": len(latencies),
            },
            "invalidPredictions": 0 if finite else None,
            "inputRows": len(examples),
            "featureNames": list(columns),
        }
    return evidence


def model_complexity(fitted: Mapping[str, Any]) -> dict[str, Any]:
    tree = fitted["decision_tree"].tree_
    xgb = fitted["xgboost"]
    mlp = fitted["mlp"].named_steps["mlpclassifier"]
    mlp_parameters = sum(
        int(np.prod(weights.shape)) + int(np.prod(biases.shape))
        for weights, biases in zip(mlp.coefs_, mlp.intercepts_)
    )
    return {
        "decision_tree": {
            "configuredMaxDepth": 4,
            "realizedMaxDepth": int(tree.max_depth),
            "nodeCount": int(tree.node_count),
            "leafCount": int(tree.n_leaves),
            "note": "Decision Tree interpretability does not automatically imply better predictive performance",
        },
        "xgboost": {
            "nEstimators": len(xgb.get_booster().get_dump()),
            "configuredMaxDepth": 3,
            "featureCount": len(EXTERNAL_FEATURE_COLUMNS),
        },
        "mlp": {
            "hiddenLayerSizes": list(mlp.hidden_layer_sizes),
            "nLayers": int(mlp.n_layers_),
            "parameterCount": mlp_parameters,
            "nIter": int(mlp.n_iter_),
            "earlyStopping": bool(mlp.early_stopping),
            "interpretabilityLimitation": "MLP has weaker native human interpretability than the Decision Tree and the SHAP-explained XGBoost architecture",
        },
    }


def bkt_ablation(
    examples: Sequence[SupervisedExample],
    bkt_rows: Mapping[str, Any],
    *,
    train_keys: Sequence[str],
    test_keys: Sequence[str],
) -> dict[str, Any]:
    """Fair base vs +BKT comparison on the same BKT-eligible rows."""
    base_examples = []
    bkt_examples = []
    eligible = 0
    for row in examples:
        bkt = bkt_rows.get(row.attempt_id)
        if bkt is None or not isinstance(bkt.get("bkt_mastery_probability"), float):
            continue
        if not 0.0 <= bkt["bkt_mastery_probability"] <= 1.0:
            continue
        eligible += 1
        base_examples.append(row)
        bkt_examples.append(
            SupervisedExample(
                attempt_id=row.attempt_id,
                student_key=row.student_key,
                subtopic_id=row.subtopic_id,
                observed_at=row.observed_at,
                features={**row.features, BKT_FEATURE_NAME: bkt["bkt_mastery_probability"]},
                target=row.target,
                contract=row.contract,
                provenance=row.provenance,
                evaluation_group_key=row.evaluation_group_key,
            )
        )
    if not base_examples:
        return {"eligible": 0, "status": "no_bkt_eligible_rows"}

    base_train = tuple(row for row in base_examples if row.student_key in set(train_keys))
    bkt_train = tuple(row for row in bkt_examples if row.student_key in set(train_keys))
    base_stability = repeated_grouped_validation(base_train, random_seed=RANDOM_SEED, n_folds=5)
    bkt_stability = repeated_grouped_validation(bkt_train, random_seed=RANDOM_SEED, n_folds=5, extra_feature=BKT_FEATURE_NAME)

    base_identity = row_identity_sha256(base_examples, partition="all")
    bkt_identity = row_identity_sha256(bkt_examples, partition="all")
    base_shared = _ablation_shared_identity(base_examples)
    bkt_shared = _ablation_shared_identity(bkt_examples)
    return {
        "status": "completed",
        "eligibleRows": eligible,
        "eligibleLearners": len({row.student_key for row in base_examples}),
        "sameRowsIdenticalExceptBkt": base_shared == bkt_shared,
        "identityBase": base_identity,
        "identityBkt": bkt_identity,
        "baseGrouped": base_stability.per_model_metrics,
        "bktGrouped": bkt_stability.per_model_metrics,
        "delta": _metric_delta(base_stability.per_model_metrics, bkt_stability.per_model_metrics),
    }


def _ablation_shared_identity(rows: Sequence[SupervisedExample]) -> str:
    """Hash attempt/learner/target and the two shared base features only."""
    from hashlib import sha256

    lines = sorted(
        (
            f"{row.attempt_id}|{row.student_key}|{row.features['correct_rate']}|"
            f"{row.features['mean_response_time_ms']}|{int(row.target)}"
        )
        for row in rows
    )
    return sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _metric_delta(
    base: Mapping[str, Mapping[str, Mapping[str, float]]],
    bkt: Mapping[str, Mapping[str, Mapping[str, float]]],
) -> dict[str, dict[str, float]]:
    deltas = {}
    for algorithm in base:
        deltas[algorithm] = {}
        for metric in base[algorithm]:
            base_mean = base[algorithm][metric]["mean"]
            bkt_mean = bkt.get(algorithm, {}).get(metric, {}).get("mean")
            if bkt_mean is None:
                continue
            deltas[algorithm][metric] = round(bkt_mean - base_mean, 6)
    return deltas


def main() -> None:
    parser = argparse.ArgumentParser(description="J5 SHAP/operational/BKT evidence")
    parser.add_argument("--processed-dir", required=True, help="Protected v2 directory")
    parser.add_argument("--action-rows", required=True, help="Protected J1 external_action_rows CSV")
    parser.add_argument("--report", default=None)
    parser.add_argument("--j5-manifest-out", default=None)
    args = parser.parse_args()

    processed = Path(args.processed_dir)
    examples, readiness = load_dataset(processed)
    train_keys, test_keys = frozen_split_from(readiness)
    train_examples = tuple(row for row in examples if row.student_key in set(train_keys))
    test_examples = tuple(row for row in examples if row.student_key in set(test_keys))

    # Refit the exact frozen models on the frozen training partition (J4 config).
    fitted = {
        "decision_tree": train_decision_tree(train_examples, random_seed=RANDOM_SEED)[0],
        "xgboost": train_xgboost(train_examples, random_seed=RANDOM_SEED)[0],
        "mlp": train_mlp(train_examples, random_seed=RANDOM_SEED)[0],
    }

    columns = EXTERNAL_FEATURE_COLUMNS
    shap_global = shap_global_summary(fitted["xgboost"], train_examples, columns)
    shap_local = shap_local_examples(fitted["xgboost"], train_examples, columns)
    operational = operational_evidence(fitted, examples, columns)
    complexity = model_complexity(fitted)

    # BKT: gate recheck, then named ablation on the same labelled rows.
    frame = read_action_rows(args.action_rows)
    observations, observation_summary = build_graded_observations(frame.to_dict("records"))
    gate = bkt_lineage_gate(observations)
    bkt_section: dict[str, Any] = {"gate": gate, "observationSummary": dict(observation_summary)}
    if gate["passed"]:
        audit_frame = pd.read_csv(processed / "u7_audit_table_v2.csv", dtype=str, keep_default_na=False)
        episode_meta = audit_frame[["currentEpisodeId", "externalStudentKey", "externalAssignmentKey", "externalSkillCode"]].to_dict("records")
        states = build_mastery_at_episodes(observations, episode_meta)
        bkt_rows = {row["currentEpisodeId"]: row for row in bkt_mastery_feature(states, episode_meta)}
        bkt_section["masteryRows"] = len(bkt_rows)
        bkt_section["ablation"] = bkt_ablation(examples, bkt_rows, train_keys=train_keys, test_keys=test_keys)
    else:
        bkt_section["ablation"] = {"status": "unavailable", "reason": gate["reason"]}

    report_path = Path(args.report) if args.report else Path(__file__).resolve().parents[2] / "reports" / "u7_assistments_j5_architecture_evidence.md"
    _write_report(report_path, shap_global, shap_local, operational, complexity, bkt_section)

    manifest = {
        "manifestSchemaVersion": "assistments-j5-architecture-evidence-v1",
        "contractVersion": J2_CONTRACT_VERSION_V2,
        "provenance": PROVENANCE,
        "j4Conclusion": "MODEL COMPARISON COMPLETED; NO STABLE ADVANTAGE ESTABLISHED",
        "shapGlobal": shap_global,
        "shapLocalExamples": shap_local,
        "operational": operational,
        "complexity": complexity,
        "bkt": bkt_section,
        "containsRawIdentifiers": False,
        "containsSecretMaterial": False,
    }
    if args.j5_manifest_out:
        manifest_path = Path(args.j5_manifest_out)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        print(f"J5 manifest: {manifest_path}")
    print(f"report: {report_path}")
    print(json.dumps({"shapRanking": shap_global["rankingByMeanAbsShap"], "bktGate": gate["passed"], "bktAblationStatus": bkt_section.get("ablation", {}).get("status", "n/a")}, indent=2))


def _write_report(path: Path, shap_global: dict, shap_local: list, operational: dict, complexity: dict, bkt: dict) -> None:
    lines = [
        "# U7 ASSISTments Architecture Evidence (J5, v2 Grade 6)",
        "",
        f"- Contract: `{J2_CONTRACT_VERSION_V2}`; provenance: `{PROVENANCE}`",
        "- J4 conclusion preserved: **MODEL COMPARISON COMPLETED; NO STABLE ADVANTAGE ESTABLISHED**",
        "",
        "## XGBoost global SHAP summary (frozen two-feature model)",
        "",
        f"- Model/artifact version: `{SHAP_MODEL_VERSION}`; explained rows (training): {shap_global['explainedRows']}",
        f"- Base value: {shap_global['baseValue']}",
        f"- Ranking by mean |SHAP|: {', '.join(shap_global['rankingByMeanAbsShap'])}",
        "",
        "| Feature | Mean |SHAP| | Mean SHAP | 5% | 50% | 95% |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in shap_global["rankingByMeanAbsShap"]:
        values = shap_global["perFeature"][name]
        lines.append(
            f"| {name} | {values['meanAbsShap']} | {values['meanShap']} | "
            f"{values['percentiles']['5']} | {values['percentiles']['50']} | {values['percentiles']['95']} |"
        )
    lines.extend(
        [
            "",
            f"Interpretation boundary: {shap_global['interpretationBoundary']}",
            "",
            "## Safe local SHAP examples (predeclared low / median / high risk)",
            "",
        ]
    )
    for example in shap_local:
        lines.append(f"- Rule: **{example['rule']}**; correct_rate={example['correct_rate']}; mean_response_time_ms={example['mean_response_time_ms']}; predicted_probability={example['predicted_probability']}; base_value={example['base_value']}; SHAP={example['shap_contributions']}")
    lines.append("")
    lines.append("The examples demonstrate model explanation only, not prediction accuracy or pedagogical causality.")
    lines.extend(
        [
            "",
            "## Operational evidence (same machine, same input contract, warm-up + 10 runs)",
            "",
            "| Model | Serialized size (bytes) | Latency median (ms) | Latency mean (ms) | Invalid predictions |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in ("decision_tree", "xgboost", "mlp"):
        item = operational[name]
        lines.append(
            f"| {name} | {item['serializedSizeBytes']} | {item['inferenceLatencyMs']['median']} | "
            f"{item['inferenceLatencyMs']['mean']} | {item['invalidPredictions']} |"
        )
    lines.extend(["", "## Model complexity", "", "```json", json.dumps(complexity, indent=2), "```", ""])
    lines.extend(["## BKT v2 lineage gate", "", "```json", json.dumps(bkt["gate"], indent=2), "```", ""])
    ablation = bkt.get("ablation", {})
    lines.append(f"BKT ablation status: {ablation.get('status', 'completed')}")
    if ablation.get("eligibleRows"):
        lines.extend(
            [
                "",
                f"- Eligible labelled rows: {ablation['eligibleRows']}; learners: {ablation['eligibleLearners']}",
                f"- Base/BKT row identity identical except BKT feature: {ablation['sameRowsIdenticalExceptBkt']}",
                "",
                "### Grouped metric delta (BKT variant - base variant, training-only 5 folds)",
                "",
                "| Algorithm | Metric | Delta |",
                "| --- | --- | ---: |",
            ]
        )
        for algorithm, metrics in ablation["delta"].items():
            for metric, delta in metrics.items():
                lines.append(f"| {algorithm} | {metric} | {delta} |")
        lines.append("")
        lines.append("A single numeric difference is not declared an improvement without considering grouped variability.")
    lines.extend(
        [
            "",
            "## Limitations and governance",
            "",
            "- External U.S.-curriculum ASSISTments evidence; **not direct Malaysian KSSR validation**.",
            "- Held-out contains only 2 independent learners / 2 positives; supplemental only.",
            "- All artifacts remain `evidence_only_external`; no registry promotion.",
            "",
            "## J5 conclusion",
            "",
            "- SHAP/operational evidence completed; BKT ablation completed (if gate passed) or documented unavailable.",
            "- The frozen J4 conclusion is not rewritten.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
