"""Deterministic mechanics evaluation for the controlled-demo catalogue."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Mapping

import yaml

from controlled_demo.build_dataset import ControlledDemoBuild, build_controlled_demo_dataset
from logic_oasis_ai.prediction_contract import CONTROLLED_DEMO_PROVENANCE

from .evaluate_models import ComparisonReport, RANDOM_SEED, evaluate_fair_comparison
from .train_xgboost import XGBOOST_PARAMETERS


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "controlled_demo_model_v1.yaml"


@dataclass(frozen=True)
class ControlledDemoEvaluation:
    dataset: ControlledDemoBuild
    report: ComparisonReport
    config: Mapping[str, object]
    config_sha256: str
    xgboost_parameters: Mapping[str, object]


def train_controlled_demo_xgboost(
    *,
    catalogue_path: str | Path | None = None,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    feature_schema_path: str | Path | None = None,
) -> ControlledDemoEvaluation:
    config_source = Path(config_path)
    config_bytes = config_source.read_bytes()
    config = yaml.safe_load(config_bytes)
    _validate_config(config)
    dataset_kwargs: dict[str, object] = {}
    if catalogue_path is not None:
        dataset_kwargs["catalogue_path"] = catalogue_path
    if feature_schema_path is not None:
        dataset_kwargs["feature_schema_path"] = feature_schema_path
    dataset = build_controlled_demo_dataset(**dataset_kwargs)
    report = evaluate_fair_comparison(
        dataset.prediction_dataset.examples,
        random_seed=RANDOM_SEED,
        pair_audit_summary=dataset.prediction_dataset.pair_audit_summary,
        allow_controlled_demo=True,
    )
    return ControlledDemoEvaluation(
        dataset=dataset,
        report=report,
        config=dict(config),
        config_sha256=sha256(config_bytes).hexdigest(),
        xgboost_parameters={**XGBOOST_PARAMETERS, "random_state": RANDOM_SEED},
    )


def _validate_config(config: object) -> None:
    if not isinstance(config, dict):
        raise ValueError("controlled-demo model config must be a mapping")
    expected = {
        "configVersion": "controlled-demo-model-config-v1",
        "deploymentScope": "controlled_demo",
        "trainingDataProvenance": CONTROLLED_DEMO_PROVENANCE,
        "evidenceLevel": "controlled_demonstration",
        "claimLevel": "controlled_demonstration_only",
        "catalogVersion": "controlled-demo-scenario-catalog-v1",
        "datasetVersion": "controlled-demo-dataset-v1",
        "featureSchemaVersion": "quiz-attempt-features-v2",
        "predictionTarget": "next_attempt_support_needed",
        "labelVersion": "next-attempt-support-needed-v1",
        "masteryCriterion": 0.60,
        "randomSeed": RANDOM_SEED,
        "groupingKey": "scenarioFamilyId",
        "automaticPromotion": False,
    }
    if config != expected:
        raise ValueError("controlled-demo model config does not match the frozen CDM-2 contract")
