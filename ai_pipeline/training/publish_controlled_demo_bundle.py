"""Publish a reproducible controlled-demo XGBoost artifact and manifest."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
import shutil
import tempfile
from typing import Mapping

from logic_oasis_ai.features import BASE_FEATURE_NAMES
from logic_oasis_ai.model_registry import ModelArtifact
from logic_oasis_ai.native_xgboost import (
    NativeXGBoostContractError,
    SHAP_RECONSTRUCTION_TOLERANCE,
    predict_and_explain_native_xgboost,
)

from .evaluate_models import EVALUATION_STATUS_EVALUATED, RANDOM_SEED
from .train_controlled_demo_xgboost import ControlledDemoEvaluation
from .train_xgboost import XGBOOST_PARAMETERS


BUNDLE_SCHEMA_VERSION = "controlled-demo-xgboost-bundle-v1"
DEFAULT_MODEL_VERSION = "controlled-demo-xgboost-v1"
MODEL_VERSION_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?")
HASH_FIELDS = frozenset({
    "artifactSha256", "trainingDatasetSha256", "scenarioCatalogueSha256",
    "featureSchemaSha256", "controlledDemoConfigSha256", "evaluationReportSha256",
})
MANIFEST_FIELDS = frozenset({
    "bundleSchemaVersion", "modelType", "modelVersion", "artifactFile", "artifactSha256",
    "targetName", "labelVersion", "masteryCriterion", "featureSchemaVersion", "featureNames",
    "trainingDatasetVersion", "trainingDatasetSha256", "trainingDataProvenance",
    "scenarioCatalogueSha256", "featureSchemaSha256", "controlledDemoConfigSha256",
    "evaluationReportSha256", "evaluationStatus", "evidenceLevel", "claimLevel",
    "deploymentScope", "randomSeed", "xgboostParameters", "trainEvaluationGroupKeys",
    "testEvaluationGroupKeys", "scenarioLimitations", "shapIntegrity",
})


@dataclass(frozen=True)
class PublishedControlledDemoBundle:
    artifact: ModelArtifact
    artifact_path: Path
    manifest_path: Path
    manifest: Mapping[str, object]
    manifest_sha256: str
    shap_integrity: tuple[Mapping[str, object], ...]


def publish_controlled_demo_bundle(
    evaluation: ControlledDemoEvaluation,
    output_directory: str | Path,
    *,
    model_version: str = DEFAULT_MODEL_VERSION,
    report_path: str | Path | None = None,
) -> PublishedControlledDemoBundle:
    _validate_model_version(model_version)
    report = evaluation.report
    if report.evaluation_status != EVALUATION_STATUS_EVALUATED or report.data_sufficiency.claim_level != "controlled_demonstration_only":
        raise ValueError("a complete controlled-demo evaluation is required before bundle publication")
    xgboost_result = next((result for result in report.results if result.algorithm == "xgboost"), None)
    if xgboost_result is None:
        raise ValueError("controlled-demo evaluation does not contain an XGBoost result")
    if tuple(xgboost_result.feature_names) != tuple(BASE_FEATURE_NAMES):
        raise ValueError("controlled-demo XGBoost artifact must use exactly the v2 feature order")

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    bundle_directory = output / model_version
    if bundle_directory.exists():
        raise ValueError("controlled-demo bundle output already exists")
    staging_directory = Path(tempfile.mkdtemp(prefix=f".{model_version}.", dir=output))
    try:
        staged_artifact = staging_directory / "model.ubj"
        staged_manifest = staging_directory / "manifest.json"
        xgboost_result.model.save_model(staged_artifact)
        artifact_bytes = staged_artifact.read_bytes()
        artifact_sha256 = sha256(artifact_bytes).hexdigest()
        shap_integrity = _representative_shap_integrity(evaluation, artifact_bytes)
        report_sha256 = report.sha256()
        dataset_manifest = evaluation.dataset.manifest
        manifest: dict[str, object] = {
            "bundleSchemaVersion": BUNDLE_SCHEMA_VERSION,
            "modelType": "xgboost",
            "modelVersion": model_version,
            "artifactFile": "model.ubj",
            "artifactSha256": artifact_sha256,
            "targetName": report.contract.target_name,
            "labelVersion": report.contract.label_version,
            "masteryCriterion": report.contract.mastery_criterion,
            "featureSchemaVersion": report.contract.feature_schema_version,
            "featureNames": list(xgboost_result.feature_names),
            "trainingDatasetVersion": dataset_manifest["datasetVersion"],
            "trainingDatasetSha256": dataset_manifest["datasetSha256"],
            "trainingDataProvenance": dataset_manifest["trainingDataProvenance"],
            "scenarioCatalogueSha256": dataset_manifest["catalogueSha256"],
            "featureSchemaSha256": dataset_manifest["featureSchemaSha256"],
            "controlledDemoConfigSha256": evaluation.config_sha256,
            "evaluationReportSha256": report_sha256,
            "evaluationStatus": EVALUATION_STATUS_EVALUATED,
            "evidenceLevel": "controlled_demonstration",
            "claimLevel": "controlled_demonstration_only",
            "deploymentScope": "controlled_demo",
            "randomSeed": report.random_seed,
            "xgboostParameters": dict(evaluation.xgboost_parameters),
            "trainEvaluationGroupKeys": list(report.train_evaluation_group_keys),
            "testEvaluationGroupKeys": list(report.test_evaluation_group_keys),
            "scenarioLimitations": [
                "Expert-authored fictional trajectories encode scenario-author assumptions.",
                "Metrics demonstrate deterministic mechanics and scenario fit only.",
                "No real-student accuracy, learning-effect, calibration, or model-superiority claim is supported.",
            ],
            "shapIntegrity": list(shap_integrity),
        }
        _validate_manifest(manifest, artifact_name="model.ubj")
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        staged_manifest.write_bytes(manifest_bytes)
        try:
            staging_directory.rename(bundle_directory)
        except FileExistsError as error:
            raise ValueError("controlled-demo bundle output already exists") from error
    except Exception:
        if staging_directory.exists():
            shutil.rmtree(staging_directory)
        raise

    manifest_sha256 = sha256(manifest_bytes).hexdigest()
    artifact_path = bundle_directory / "model.ubj"
    manifest_path = bundle_directory / "manifest.json"
    artifact = ModelArtifact(
        artifact_id=f"xgboost-{model_version}",
        model_type="xgboost",
        model_version=model_version,
        feature_schema_version=report.contract.feature_schema_version,
        training_dataset_version=str(dataset_manifest["datasetVersion"]),
        artifact_sha256=artifact_sha256,
        prediction_target=report.contract.target_name,
        label_version=report.contract.label_version,
        mastery_criterion=report.contract.mastery_criterion,
        evaluation_status=EVALUATION_STATUS_EVALUATED,
        evaluation_report_sha256=report_sha256,
        artifact_manifest_sha256=manifest_sha256,
        promotion_gate_status="not_passed",
    )
    published = PublishedControlledDemoBundle(
        artifact=artifact,
        artifact_path=artifact_path,
        manifest_path=manifest_path,
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        shap_integrity=shap_integrity,
    )
    if report_path is not None:
        write_controlled_demo_report(evaluation, published, report_path)
    return published


def load_controlled_demo_bundle(
    artifact_path: str | Path,
    manifest_path: str | Path,
) -> tuple[object, Mapping[str, object]]:
    artifact_source = Path(artifact_path)
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("controlled-demo artifact manifest is unavailable or malformed") from error
    _validate_manifest(manifest, artifact_name=artifact_source.name)
    try:
        artifact_bytes = artifact_source.read_bytes()
    except OSError as error:
        raise ValueError("controlled-demo artifact is unavailable") from error
    if sha256(artifact_bytes).hexdigest() != manifest["artifactSha256"]:
        raise ValueError("controlled-demo artifact hash does not match its manifest")
    return _load_native_xgboost(artifact_bytes), manifest


def write_controlled_demo_report(
    evaluation: ControlledDemoEvaluation,
    published: PublishedControlledDemoBundle,
    output_path: str | Path,
) -> Path:
    report = evaluation.report
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Controlled-demonstration XGBoost mechanics report",
        "",
        "- Claim level: `controlled_demonstration_only`",
        f"- Evaluation status: `{report.evaluation_status}`",
        f"- Dataset: `{evaluation.dataset.manifest['datasetVersion']}` (`{evaluation.dataset.manifest['datasetSha256']}`)",
        f"- Catalogue SHA-256: `{evaluation.dataset.manifest['catalogueSha256']}`",
        f"- Configuration SHA-256: `{evaluation.config_sha256}`",
        f"- Evaluation report SHA-256: `{published.manifest['evaluationReportSha256']}`",
        f"- Model artifact SHA-256: `{published.artifact.artifact_sha256}`",
        f"- Artifact manifest SHA-256: `{published.manifest_sha256}`",
        f"- Random seed: `{report.random_seed}`",
        f"- Training groups: `{', '.join(report.train_evaluation_group_keys)}`",
        f"- Held-out groups: `{', '.join(report.test_evaluation_group_keys)}`",
        "",
        "## Mechanics comparison",
        "",
        "All models used the same grouped rows and exactly `correct_rate` plus `mean_response_time_ms`.",
        "These metrics describe fit to fictional supervisor-reviewed scenarios only; they are not real-world performance or superiority evidence.",
        "",
        "| Model | Accuracy | F1 | ROC-AUC | PR-AUC | Log loss | Brier |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in report.results:
        metrics = result.metrics
        lines.append(
            f"| {result.algorithm} | {metrics['accuracy']} | {metrics['f1']} | {metrics['roc_auc']} | "
            f"{metrics['pr_auc']} | {metrics['log_loss']} | {metrics['brier_score']} |"
        )
    lines.extend([
        "", "## Tree SHAP integrity", "",
        f"The same serialized XGBoost artifact reconstructed low-, medium-, and high-risk outputs within `{SHAP_RECONSTRUCTION_TOLERANCE}`.",
    ])
    for case in published.shap_integrity:
        lines.append(
            f"- `{case['riskTier']}`: risk `{case['supportRisk']}`, reconstructed `{case['reconstructedRisk']}`, "
            f"absolute error `{case['absoluteError']}`, features `{', '.join(case['shapValues'])}`."
        )
    lines.extend([
        "", "## Limitations", "",
        "This is an implemented controlled demonstration based on fictional trajectories. It does not establish accuracy for real students, learning improvement, calibration, or superiority over Decision Tree or MLP baselines.",
    ])
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _representative_shap_integrity(
    evaluation: ControlledDemoEvaluation,
    artifact_bytes: bytes,
) -> tuple[Mapping[str, object], ...]:
    import numpy as np
    model = _load_native_xgboost(artifact_bytes)
    rows = evaluation.dataset.prediction_dataset.examples
    matrix = np.asarray([[float(row.features[name]) for name in BASE_FEATURE_NAMES] for row in rows])
    try:
        scored_explanations = predict_and_explain_native_xgboost(
            model, matrix, feature_names=BASE_FEATURE_NAMES,
        )
    except NativeXGBoostContractError as error:
        _raise_publication_shap_error(error)
    scored = [
        (round(support_risk, 8), row)
        for support_risk, row in zip(scored_explanations.support_risks, rows)
    ]
    scored.sort(key=lambda item: (item[0], item[1].attempt_id))
    selected = (("low", scored[0]), ("medium", scored[len(scored) // 2]), ("high", scored[-1]))
    selected_matrix = np.asarray([[float(row.features[name]) for name in BASE_FEATURE_NAMES] for _, (_, row) in selected])
    try:
        selected_explanations = predict_and_explain_native_xgboost(
            model, selected_matrix, feature_names=BASE_FEATURE_NAMES,
        )
    except NativeXGBoostContractError as error:
        _raise_publication_shap_error(error)
    evidence: list[Mapping[str, object]] = []
    for index, (tier, (_, row)) in enumerate(selected):
        support_risk = selected_explanations.support_risks[index]
        raw_values = selected_explanations.shap_values[index]
        shap_values = {name: round(float(value), 8) for name, value in zip(BASE_FEATURE_NAMES, raw_values)}
        if not any(abs(value) > 0 for value in shap_values.values()):
            raise ValueError("Tree SHAP output does not match the controlled-demo feature contract")
        expected_value = selected_explanations.expected_values[index]
        reconstructed = selected_explanations.reconstructed_risks[index]
        absolute_error = abs(reconstructed - support_risk)
        if absolute_error > SHAP_RECONSTRUCTION_TOLERANCE:
            raise ValueError("Tree SHAP values do not reconstruct the matching XGBoost output")
        evidence.append({
            "riskTier": tier,
            "attemptId": row.attempt_id,
            "supportRisk": round(support_risk, 8),
            "expectedValue": round(expected_value, 8),
            "reconstructedRisk": round(reconstructed, 8),
            "absoluteError": round(absolute_error, 10),
            "shapValues": shap_values,
        })
    return tuple(evidence)


def _raise_publication_shap_error(error: NativeXGBoostContractError) -> None:
    if error.code == "model_target_incompatible":
        raise ValueError("controlled-demo XGBoost artifact does not contain the support-needed target") from error
    if error.code == "shap_reconstruction_mismatch":
        raise ValueError("Tree SHAP values do not reconstruct the matching XGBoost output") from error
    if error.code == "shap_output_invalid":
        raise ValueError("Tree SHAP output does not match the controlled-demo feature contract") from error
    raise ValueError(f"controlled-demo native XGBoost validation failed: {error.code}") from error


def _load_native_xgboost(artifact_bytes: bytes):
    from xgboost import XGBClassifier

    model = XGBClassifier()
    model.load_model(bytearray(artifact_bytes))
    return model


def _validate_model_version(model_version: object) -> None:
    if not isinstance(model_version, str) or not MODEL_VERSION_PATTERN.fullmatch(model_version) or ".." in model_version:
        raise ValueError("model_version must be a safe lowercase version token")


def _validate_manifest(manifest: object, *, artifact_name: str) -> None:
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS:
        raise ValueError("artifact manifest does not match the complete controlled-demo schema")
    expected = {
        "bundleSchemaVersion": BUNDLE_SCHEMA_VERSION,
        "modelType": "xgboost",
        "artifactFile": artifact_name,
        "targetName": "next_attempt_support_needed",
        "labelVersion": "next-attempt-support-needed-v1",
        "masteryCriterion": 0.60,
        "featureSchemaVersion": "quiz-attempt-features-v2",
        "featureNames": list(BASE_FEATURE_NAMES),
        "trainingDatasetVersion": "controlled-demo-dataset-v1",
        "trainingDataProvenance": "expert_authored_controlled_demo",
        "evidenceLevel": "controlled_demonstration",
        "claimLevel": "controlled_demonstration_only",
        "deploymentScope": "controlled_demo",
        "evaluationStatus": EVALUATION_STATUS_EVALUATED,
        "randomSeed": RANDOM_SEED,
        "xgboostParameters": {**XGBOOST_PARAMETERS, "random_state": RANDOM_SEED},
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("artifact manifest does not match the controlled-demo prediction contract")
    _validate_model_version(manifest.get("modelVersion"))
    if any(not isinstance(manifest.get(field), str) or not re.fullmatch(r"[0-9a-f]{64}", manifest[field]) for field in HASH_FIELDS):
        raise ValueError("artifact manifest contains an invalid SHA-256 binding")
    train_groups = manifest.get("trainEvaluationGroupKeys")
    test_groups = manifest.get("testEvaluationGroupKeys")
    if (
        not isinstance(train_groups, list) or not train_groups
        or not isinstance(test_groups, list) or not test_groups
        or not all(isinstance(group, str) and group for group in (*train_groups, *test_groups))
        or set(train_groups) & set(test_groups)
    ):
        raise ValueError("artifact manifest evaluation groups are invalid")
    limitations = manifest.get("scenarioLimitations")
    if not isinstance(limitations, list) or not limitations or not all(isinstance(item, str) and item for item in limitations):
        raise ValueError("artifact manifest scenario limitations are required")
    shap_integrity = manifest.get("shapIntegrity")
    if not isinstance(shap_integrity, list) or len(shap_integrity) != 3:
        raise ValueError("artifact manifest requires three Tree SHAP integrity cases")
    expected_case_fields = {"riskTier", "attemptId", "supportRisk", "expectedValue", "reconstructedRisk", "absoluteError", "shapValues"}
    for case in shap_integrity:
        if not isinstance(case, dict) or set(case) != expected_case_fields or set(case.get("shapValues", {})) != set(BASE_FEATURE_NAMES):
            raise ValueError("artifact manifest Tree SHAP evidence is malformed")
        numeric = (case.get("supportRisk"), case.get("expectedValue"), case.get("reconstructedRisk"), case.get("absoluteError"))
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)) for value in numeric):
            raise ValueError("artifact manifest Tree SHAP evidence is invalid")
