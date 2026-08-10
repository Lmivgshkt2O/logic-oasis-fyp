"""Strict schema for the fictional forum scenario catalogue."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Mapping

import yaml


CATALOGUE_VERSION = "forum-controlled-demo-catalog-v1"
RUBRIC_VERSION = "forum-explanation-rubric-v1"
PROVENANCE = "expert_authored_controlled_demo"
EVIDENCE_LEVEL = "controlled_demonstration"
CLAIM_LEVEL = "controlled_demonstration_only"
RELEASE_SCOPE = "fyp1_forum_controlled_demo"
DEPLOYMENT_SCOPE = "controlled_demo"
FICTIONAL_AUTHOR_DECLARATION = "developer-authored-fictional-forum-scenarios-v1"
LABELS = frozenset({"explanation_sufficient", "answer_only_or_insufficient"})
LANGUAGES = frozenset({"en", "ms", "mixed"})
RUBRIC_DOCUMENT = {
    "rubricVersion": RUBRIC_VERSION,
    "labels": {
        "explanation_sufficient": "The fictional answer explains mathematical steps or reasoning a peer can follow.",
        "answer_only_or_insufficient": "The fictional answer gives only a result or too little reasoning for a peer to follow.",
    },
    "correctnessGrading": False,
    "advisoryOnly": True,
}
FORBIDDEN_FIELDS = frozenset({
    "studentId", "student_id", "studentEmail", "email", "name", "username",
    "answerKey", "answer_key", "correctAnswer", "copiedFromForum",
    "learnerText", "realLearnerText", "learnerDistributionClaim",
    "realDataClaim", "authorId", "userId",
})
FORBIDDEN_TEXT_PATTERNS = (
    ("email address", re.compile(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", re.IGNORECASE)),
    (
        "phone number",
        re.compile(r"(?<!\w)(?:\+?60[\s-]?|0)1\d[\s-]?\d{3,4}[\s-]?\d{4}(?!\w)"),
    ),
    (
        "student identifier",
        re.compile(
            r"\b(?:student|learner|pupil)\s*(?:id|identifier)\s*[:#=-]?\s*[a-z0-9-]{3,}\b",
            re.IGNORECASE,
        ),
    ),
    (
        "credential",
        re.compile(
            r"\b(?:password|passwd|api[ _-]?key|access[ _-]?token|secret)\s*[:=]\s*\S+",
            re.IGNORECASE,
        ),
    ),
    ("credential", re.compile(r"\bbearer\s+[a-z0-9._~-]{8,}", re.IGNORECASE)),
    (
        "answer-key marker",
        re.compile(r"\b(?:answer\s*key|marking\s*scheme|correct\s*answer)\s*[:=]", re.IGNORECASE),
    ),
)


@dataclass(frozen=True)
class ForumScenarioExample:
    example_id: str
    text: str
    label: str
    language: str


@dataclass(frozen=True)
class ForumScenarioFamily:
    scenario_family_id: str
    question_family_id: str | None
    mathematics_scenario_family: str
    examples: tuple[ForumScenarioExample, ...]


@dataclass(frozen=True)
class ForumScenarioCatalogue:
    catalog_version: str
    rubric_version: str
    training_data_provenance: str
    evidence_level: str
    claim_level: str
    release_scope: str
    deployment_scope: str
    author_declaration: str
    limitations: tuple[str, ...]
    scenario_families: tuple[ForumScenarioFamily, ...]


def load_catalogue(path: str | Path) -> ForumScenarioCatalogue:
    try:
        source = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError("forum controlled-demo catalogue is unavailable") from error
    return parse_catalogue(source)


def parse_catalogue(source: str | bytes) -> ForumScenarioCatalogue:
    try:
        document = yaml.safe_load(source)
    except yaml.YAMLError as error:
        raise ValueError("forum controlled-demo catalogue is malformed") from error
    if not isinstance(document, Mapping):
        raise ValueError("forum controlled-demo catalogue must be a mapping")
    _reject_forbidden_fields(document)
    _exact_keys(document, {
        "catalogVersion", "rubricVersion", "trainingDataProvenance", "evidenceLevel",
        "claimLevel", "releaseScope", "deploymentScope", "authorDeclaration",
        "limitations", "scenarioFamilies",
    }, "catalogue")
    families_raw = document["scenarioFamilies"]
    limitations_raw = document["limitations"]
    if not isinstance(families_raw, list) or not families_raw:
        raise ValueError("scenarioFamilies must be a non-empty list")
    if not _string_list(limitations_raw):
        raise ValueError("limitations must be a non-empty string list")
    catalogue = ForumScenarioCatalogue(
        catalog_version=_string(document, "catalogVersion"),
        rubric_version=_string(document, "rubricVersion"),
        training_data_provenance=_string(document, "trainingDataProvenance"),
        evidence_level=_string(document, "evidenceLevel"),
        claim_level=_string(document, "claimLevel"),
        release_scope=_string(document, "releaseScope"),
        deployment_scope=_string(document, "deploymentScope"),
        author_declaration=_string(document, "authorDeclaration"),
        limitations=tuple(limitations_raw),
        scenario_families=tuple(_parse_family(item) for item in families_raw),
    )
    _validate(catalogue)
    return catalogue


def catalogue_document(catalogue: ForumScenarioCatalogue) -> dict[str, object]:
    """Return the canonical logical catalogue, independent of YAML formatting."""
    return {
        "catalogVersion": catalogue.catalog_version,
        "rubricVersion": catalogue.rubric_version,
        "trainingDataProvenance": catalogue.training_data_provenance,
        "evidenceLevel": catalogue.evidence_level,
        "claimLevel": catalogue.claim_level,
        "releaseScope": catalogue.release_scope,
        "deploymentScope": catalogue.deployment_scope,
        "authorDeclaration": catalogue.author_declaration,
        "limitations": list(catalogue.limitations),
        "scenarioFamilies": [
            {
                "scenarioFamilyId": family.scenario_family_id,
                **({"questionFamilyId": family.question_family_id} if family.question_family_id else {}),
                "mathematicsScenarioFamily": family.mathematics_scenario_family,
                "examples": [
                    {
                        "exampleId": example.example_id,
                        "text": example.text,
                        "label": example.label,
                        "language": example.language,
                    }
                    for example in family.examples
                ],
            }
            for family in catalogue.scenario_families
        ],
    }


def _parse_family(value: object) -> ForumScenarioFamily:
    if not isinstance(value, Mapping):
        raise ValueError("each scenario family must be a mapping")
    required = {"scenarioFamilyId", "mathematicsScenarioFamily", "examples"}
    optional = {"questionFamilyId"}
    if not required <= set(value) or set(value) - required - optional:
        raise ValueError("scenario family fields must contain exactly the declared schema")
    examples = value["examples"]
    if not isinstance(examples, list) or len(examples) < 2:
        raise ValueError("each scenario family needs at least two examples")
    return ForumScenarioFamily(
        scenario_family_id=_string(value, "scenarioFamilyId"),
        question_family_id=_optional_string(value, "questionFamilyId"),
        mathematics_scenario_family=_string(value, "mathematicsScenarioFamily"),
        examples=tuple(_parse_example(item) for item in examples),
    )


def _parse_example(value: object) -> ForumScenarioExample:
    if not isinstance(value, Mapping):
        raise ValueError("each forum example must be a mapping")
    _exact_keys(value, {"exampleId", "text", "label", "language"}, "forum example")
    text = _string(value, "text")
    if len(text) < 8 or len(text) > 1000:
        raise ValueError("fictional forum text must be between 8 and 1000 characters")
    _reject_sensitive_text(text)
    label = _string(value, "label")
    language = _string(value, "language")
    if label not in LABELS:
        raise ValueError("forum example label does not match the controlled-demo rubric")
    if language not in LANGUAGES:
        raise ValueError("forum example language is unsupported")
    return ForumScenarioExample(_string(value, "exampleId"), " ".join(text.split()), label, language)


def _validate(catalogue: ForumScenarioCatalogue) -> None:
    expected = {
        "catalogVersion": (catalogue.catalog_version, CATALOGUE_VERSION),
        "rubricVersion": (catalogue.rubric_version, RUBRIC_VERSION),
        "trainingDataProvenance": (catalogue.training_data_provenance, PROVENANCE),
        "evidenceLevel": (catalogue.evidence_level, EVIDENCE_LEVEL),
        "claimLevel": (catalogue.claim_level, CLAIM_LEVEL),
        "releaseScope": (catalogue.release_scope, RELEASE_SCOPE),
        "deploymentScope": (catalogue.deployment_scope, DEPLOYMENT_SCOPE),
        "authorDeclaration": (catalogue.author_declaration, FICTIONAL_AUTHOR_DECLARATION),
    }
    for field, (actual, required) in expected.items():
        if actual != required:
            raise ValueError(f"{field} does not match the controlled-demo contract")
    family_ids = [item.scenario_family_id for item in catalogue.scenario_families]
    example_ids = [example.example_id for family in catalogue.scenario_families for example in family.examples]
    if len(family_ids) != len(set(family_ids)):
        raise ValueError("scenarioFamilyId values must be unique")
    if len(example_ids) != len(set(example_ids)):
        raise ValueError("exampleId values must be globally unique")
    for family in catalogue.scenario_families:
        if {example.label for example in family.examples} != LABELS:
            raise ValueError("each scenario family must contain both rubric labels")


def _reject_forbidden_fields(value: object) -> None:
    if isinstance(value, Mapping):
        forbidden = FORBIDDEN_FIELDS & set(value)
        if forbidden:
            raise ValueError(f"catalogue contains forbidden field(s): {sorted(forbidden)}")
        for child in value.values():
            _reject_forbidden_fields(child)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_fields(child)


def _reject_sensitive_text(text: str) -> None:
    for category, pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"fictional forum text contains a forbidden {category}")


def _exact_keys(value: Mapping[object, object], expected: set[str], context: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{context} fields must be exactly {sorted(expected)}")


def _string(value: Mapping[object, object], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return result.strip()


def _optional_string(value: Mapping[object, object], key: str) -> str | None:
    return _string(value, key) if key in value else None


def _string_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)
