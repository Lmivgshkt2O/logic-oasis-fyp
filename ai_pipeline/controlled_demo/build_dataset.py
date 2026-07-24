"""Build deterministic, next-attempt-labelled controlled-demo evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Mapping

from logic_oasis_ai.features import AttemptFeatureRow, BASE_FEATURE_NAMES, FEATURE_SCHEMA_VERSION
from logic_oasis_ai.prediction_contract import PredictionDataset, build_prediction_dataset

from .schema import ScenarioCatalogue, parse_catalogue


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOGUE_PATH = Path(__file__).with_name("scenario_catalog_v1.yaml")
DEFAULT_FEATURE_SCHEMA_PATH = ROOT / "configs" / "feature_schema.yaml"
DATASET_VERSION = "controlled-demo-dataset-v1"


@dataclass(frozen=True)
class ControlledDemoBuild:
    prediction_dataset: PredictionDataset
    manifest: Mapping[str, object]
    document: Mapping[str, object]

    def dataset_document(self) -> dict[str, object]:
        return dict(self.document)


def build_controlled_demo_dataset(
    catalogue_path: str | Path = DEFAULT_CATALOGUE_PATH,
    *,
    feature_schema_path: str | Path = DEFAULT_FEATURE_SCHEMA_PATH,
) -> ControlledDemoBuild:
    catalogue_source = Path(catalogue_path)
    feature_schema_source = Path(feature_schema_path)
    catalogue_bytes = catalogue_source.read_bytes()
    schema_bytes = feature_schema_source.read_bytes()
    catalogue = parse_catalogue(catalogue_bytes)
    attempts = _feature_rows(catalogue)
    prediction_dataset = build_prediction_dataset(attempts, allow_controlled_demo=True)
    groups = sorted(family.scenario_family_id for family in catalogue.scenario_families)
    manifest: dict[str, object] = {
        "datasetVersion": DATASET_VERSION,
        "catalogVersion": catalogue.catalog_version,
        "catalogueSha256": sha256(catalogue_bytes).hexdigest(),
        "featureSchemaVersion": catalogue.feature_schema_version,
        "featureSchemaSha256": sha256(schema_bytes).hexdigest(),
        "featureNames": list(BASE_FEATURE_NAMES),
        "predictionTarget": catalogue.prediction_target,
        "labelVersion": catalogue.label_version,
        "masteryCriterion": catalogue.mastery_criterion,
        "trainingDataProvenance": catalogue.training_data_provenance,
        "scenarioAuthorApprovalReference": catalogue.scenario_author_approval_reference,
        "scenarioFamilyGroups": groups,
        "scenarioFamilyCount": len(catalogue.scenario_families),
        "sourceAttemptCount": len(attempts),
        "trainingRowCount": len(prediction_dataset.examples),
        "supportNeededCount": sum(row.target for row in prediction_dataset.examples),
        "supportNotNeededCount": sum(not row.target for row in prediction_dataset.examples),
        "pairAudit": prediction_dataset.pair_audit_summary.to_document(),
        "containsRawLearnerIdentity": False,
        "claimLevel": "controlled_demonstration_only",
    }
    dataset_document = _dataset_document(prediction_dataset)
    manifest["datasetSha256"] = sha256(
        json.dumps(
            {"dataset": dataset_document, "manifest": manifest},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return ControlledDemoBuild(prediction_dataset, manifest, dataset_document)


def write_controlled_demo_dataset(
    output_directory: str | Path,
    *,
    catalogue_path: str | Path = DEFAULT_CATALOGUE_PATH,
    feature_schema_path: str | Path = DEFAULT_FEATURE_SCHEMA_PATH,
) -> dict[str, Path]:
    build = build_controlled_demo_dataset(catalogue_path, feature_schema_path=feature_schema_path)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    dataset_path = output / "controlled_demo_dataset_v1.json"
    manifest_path = output / "controlled_demo_dataset_v1.manifest.json"
    dataset_path.write_text(json.dumps(build.document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(build.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"dataset": dataset_path, "manifest": manifest_path}


def _feature_rows(catalogue: ScenarioCatalogue) -> tuple[AttemptFeatureRow, ...]:
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows: list[AttemptFeatureRow] = []
    for family_index, family in enumerate(catalogue.scenario_families):
        for attempt in family.attempts:
            total_questions = 5
            correct_count = round(attempt.correct_rate * total_questions)
            if abs(correct_count / total_questions - attempt.correct_rate) > 1e-9:
                raise ValueError("controlled-demo correct_rate must be representable by the five-question FYP1 quiz")
            rows.append(
                AttemptFeatureRow(
                    attempt_id=attempt.attempt_id,
                    student_key=family.scenario_family_id,
                    topic_id=family.topic_id,
                    subtopic_id=family.subtopic_id,
                    bank_id=attempt.bank_id,
                    difficulty_level=attempt.difficulty_level,
                    content_version=attempt.content_version or family.content_version,
                    finalized_at=(base_time + timedelta(days=family_index * 10 + attempt.source_attempt_sequence)).isoformat(),
                    total_questions=total_questions,
                    correct_count=correct_count,
                    correct_rate=attempt.correct_rate,
                    mean_response_time_ms=attempt.mean_response_time_ms,
                    mean_hint_count=0.0,
                    provenance=catalogue.training_data_provenance,
                    source_attempt_sequence=attempt.source_attempt_sequence,
                    year_level=family.year_level,
                    assignment_source="controlled_demo_catalogue",
                    adaptive_policy_version=attempt.adaptive_policy_version or family.adaptive_policy_version,
                    skill_ids=family.skill_ids,
                    question_ids=attempt.question_ids,
                    response_ids=tuple(f"{attempt.attempt_id}-response-{index + 1}" for index in range(total_questions)),
                    question_versions=(attempt.content_version or family.content_version,),
                    response_time_quality="expert_authored_controlled_demo",
                )
            )
    return tuple(rows)


def _dataset_document(prediction_dataset: PredictionDataset) -> dict[str, object]:
    return {
        "datasetVersion": DATASET_VERSION,
        "featureSchemaVersion": FEATURE_SCHEMA_VERSION,
        "featureNames": list(BASE_FEATURE_NAMES),
        "rows": [
            {
                "attemptId": row.attempt_id,
                "evaluationGroupKey": row.evaluation_group_key,
                "scenarioFamilyId": row.student_key,
                "features": dict(row.features),
                "nextAttemptSupportNeeded": row.target,
                "trainingDataProvenance": row.provenance,
            }
            for row in prediction_dataset.examples
        ],
        "pairAudits": [
            {
                "currentAttemptId": audit.current_attempt_id,
                "nextAttemptId": audit.next_attempt_id,
                "eligible": audit.eligible,
                "censorReason": audit.censor_reason,
                "stratum": audit.stratum,
                "immediateQuestionRepeat": audit.immediate_question_repeat,
            }
            for audit in prediction_dataset.pair_audits
        ],
    }
