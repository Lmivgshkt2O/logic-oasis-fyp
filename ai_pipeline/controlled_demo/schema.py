"""Strict schema for supervisor-reviewed fictional learning trajectories."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Mapping

import yaml

from logic_oasis_ai.features import BASE_FEATURE_NAMES, FEATURE_SCHEMA_VERSION
from logic_oasis_ai.prediction_contract import (
    CONTROLLED_DEMO_PROVENANCE,
    DEFAULT_MASTERY_CRITERION,
    PREDICTION_LABEL_VERSION,
    PREDICTION_TARGET,
)


CATALOG_VERSION = "controlled-demo-scenario-catalog-v1"
FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "studentId", "student_id", "studentEmail", "email", "name",
        "answer", "answerKey", "answer_key", "rawAnswerText",
        "rawQuestionText", "questionText", "freeText",
    }
)


@dataclass(frozen=True)
class ScenarioAttempt:
    attempt_id: str
    source_attempt_sequence: int
    bank_id: str
    difficulty_level: str
    correct_rate: float
    mean_response_time_ms: float
    question_ids: tuple[str, ...]
    content_version: str | None
    adaptive_policy_version: str | None


@dataclass(frozen=True)
class ScenarioFamily:
    scenario_family_id: str
    fictional_profile_id: str
    year_level: int
    topic_id: str
    subtopic_id: str
    skill_ids: tuple[str, ...]
    content_version: str
    adaptive_policy_version: str
    attempts: tuple[ScenarioAttempt, ...]


@dataclass(frozen=True)
class ScenarioCatalogue:
    catalog_version: str
    feature_schema_version: str
    prediction_target: str
    label_version: str
    mastery_criterion: float
    training_data_provenance: str
    scenario_author_approval_reference: str
    scenario_families: tuple[ScenarioFamily, ...]


def load_catalogue(path: str | Path) -> ScenarioCatalogue:
    return parse_catalogue(Path(path).read_bytes())


def parse_catalogue(source: str | bytes) -> ScenarioCatalogue:
    document = yaml.safe_load(source)
    if not isinstance(document, Mapping):
        raise ValueError("controlled-demo catalogue must be a mapping")
    _reject_forbidden_fields(document)
    _require_exact_keys(
        document,
        {
            "catalogVersion", "featureSchemaVersion", "predictionTarget",
            "labelVersion", "masteryCriterion", "trainingDataProvenance",
            "scenarioAuthorApprovalReference", "scenarioFamilies",
        },
        "catalogue",
    )
    families_raw = document["scenarioFamilies"]
    if not isinstance(families_raw, list) or not families_raw:
        raise ValueError("scenarioFamilies must be a non-empty list")
    catalogue = ScenarioCatalogue(
        catalog_version=_required_string(document, "catalogVersion"),
        feature_schema_version=_required_string(document, "featureSchemaVersion"),
        prediction_target=_required_string(document, "predictionTarget"),
        label_version=_required_string(document, "labelVersion"),
        mastery_criterion=_finite_number(document, "masteryCriterion"),
        training_data_provenance=_required_string(document, "trainingDataProvenance"),
        scenario_author_approval_reference=_required_string(document, "scenarioAuthorApprovalReference"),
        scenario_families=tuple(_parse_family(value) for value in families_raw),
    )
    _validate_catalogue(catalogue)
    return catalogue


def _parse_family(value: object) -> ScenarioFamily:
    if not isinstance(value, Mapping):
        raise ValueError("each scenario family must be a mapping")
    _require_exact_keys(
        value,
        {
            "scenarioFamilyId", "fictionalProfileId", "yearLevel", "topicId",
            "subtopicId", "skillIds", "contentVersion",
            "adaptivePolicyVersion", "attempts",
        },
        "scenario family",
    )
    attempts_raw = value["attempts"]
    skill_ids = value["skillIds"]
    if not isinstance(attempts_raw, list) or not attempts_raw:
        raise ValueError("scenario family attempts must be a non-empty list")
    if not isinstance(skill_ids, list) or not skill_ids or not all(isinstance(item, str) and item for item in skill_ids):
        raise ValueError("skillIds must be a non-empty string list")
    return ScenarioFamily(
        scenario_family_id=_required_string(value, "scenarioFamilyId"),
        fictional_profile_id=_required_string(value, "fictionalProfileId"),
        year_level=_positive_int(value, "yearLevel"),
        topic_id=_required_string(value, "topicId"),
        subtopic_id=_required_string(value, "subtopicId"),
        skill_ids=tuple(skill_ids),
        content_version=_required_string(value, "contentVersion"),
        adaptive_policy_version=_required_string(value, "adaptivePolicyVersion"),
        attempts=tuple(_parse_attempt(item) for item in attempts_raw),
    )


def _parse_attempt(value: object) -> ScenarioAttempt:
    if not isinstance(value, Mapping):
        raise ValueError("each scenario attempt must be a mapping")
    required = {
        "attemptId", "sourceAttemptSequence", "bankId", "difficultyLevel",
        *BASE_FEATURE_NAMES, "questionIds",
    }
    optional = {"contentVersion", "adaptivePolicyVersion"}
    if not required <= set(value) or set(value) - required - optional:
        raise ValueError(f"scenario attempt fields must contain {sorted(required)} and only declared context overrides")
    questions = value["questionIds"]
    if (
        not isinstance(questions, list)
        or len(questions) != 5
        or len(set(questions)) != 5
        or not all(isinstance(item, str) and item for item in questions)
    ):
        raise ValueError("questionIds must contain five unique non-empty strings")
    return ScenarioAttempt(
        attempt_id=_required_string(value, "attemptId"),
        source_attempt_sequence=_positive_int(value, "sourceAttemptSequence"),
        bank_id=_required_string(value, "bankId"),
        difficulty_level=_required_string(value, "difficultyLevel"),
        correct_rate=_finite_number(value, "correct_rate"),
        mean_response_time_ms=_finite_number(value, "mean_response_time_ms"),
        question_ids=tuple(questions),
        content_version=_optional_string(value, "contentVersion"),
        adaptive_policy_version=_optional_string(value, "adaptivePolicyVersion"),
    )


def _validate_catalogue(catalogue: ScenarioCatalogue) -> None:
    expected = (
        (catalogue.catalog_version, CATALOG_VERSION, "catalogVersion"),
        (catalogue.feature_schema_version, FEATURE_SCHEMA_VERSION, "featureSchemaVersion"),
        (catalogue.prediction_target, PREDICTION_TARGET, "predictionTarget"),
        (catalogue.label_version, PREDICTION_LABEL_VERSION, "labelVersion"),
        (catalogue.mastery_criterion, DEFAULT_MASTERY_CRITERION, "masteryCriterion"),
        (catalogue.training_data_provenance, CONTROLLED_DEMO_PROVENANCE, "trainingDataProvenance"),
    )
    for actual, required, field in expected:
        if actual != required:
            raise ValueError(f"{field} does not match the controlled-demo contract")
    family_ids = [family.scenario_family_id for family in catalogue.scenario_families]
    profile_ids = [family.fictional_profile_id for family in catalogue.scenario_families]
    if len(set(family_ids)) != len(family_ids) or len(set(profile_ids)) != len(profile_ids):
        raise ValueError("scenario family and fictional profile IDs must be unique")
    attempt_ids: set[str] = set()
    for family in catalogue.scenario_families:
        sequences = [attempt.source_attempt_sequence for attempt in family.attempts]
        if sequences != list(range(1, len(sequences) + 1)):
            raise ValueError("scenario attempts must use contiguous ordered sourceAttemptSequence values")
        for attempt in family.attempts:
            if attempt.attempt_id in attempt_ids:
                raise ValueError("scenario attempt IDs must be globally unique")
            attempt_ids.add(attempt.attempt_id)
            if not 0.0 <= attempt.correct_rate <= 1.0:
                raise ValueError("correct_rate must be between zero and one")
            if attempt.mean_response_time_ms <= 0:
                raise ValueError("mean_response_time_ms must be positive")


def _reject_forbidden_fields(value: object) -> None:
    if isinstance(value, Mapping):
        forbidden = FORBIDDEN_FIELD_NAMES & set(value)
        if forbidden:
            raise ValueError(f"controlled-demo catalogue contains forbidden raw learner fields: {sorted(forbidden)}")
        for child in value.values():
            _reject_forbidden_fields(child)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_fields(child)


def _require_exact_keys(value: Mapping[object, object], expected: set[str], context: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{context} fields must be exactly {sorted(expected)}")


def _required_string(value: Mapping[object, object], key: str) -> str:
    result = value[key]
    if not isinstance(result, str) or not result.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return result


def _positive_int(value: Mapping[object, object], key: str) -> int:
    result = value[key]
    if not isinstance(result, int) or isinstance(result, bool) or result < 1:
        raise ValueError(f"{key} must be a positive integer")
    return result


def _finite_number(value: Mapping[object, object], key: str) -> float:
    result = value[key]
    if isinstance(result, bool) or not isinstance(result, (int, float)) or not isfinite(float(result)):
        raise ValueError(f"{key} must be a finite number")
    return float(result)


def _optional_string(value: Mapping[object, object], key: str) -> str | None:
    if key not in value:
        return None
    return _required_string(value, key)
