"""Strict schema for the fictional forum verification catalogue.

Every example carries authoritative truth labels for correctness, relevance,
reasoning, and the composite public decision, across linked and free-form
contexts and the supported English, Bahasa Melayu, and mixed languages.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Mapping

import yaml


CATALOGUE_VERSION = "forum-verification-catalog-v1"
RUBRIC_VERSION = "forum-verification-rubric-v1"
PROVENANCE = "expert_authored_controlled_demo"
EVIDENCE_LEVEL = "controlled_demonstration"
CLAIM_LEVEL = "controlled_demonstration_only"
RELEASE_SCOPE = "fyp1_forum_controlled_demo"
DEPLOYMENT_SCOPE = "controlled_demo"
FICTIONAL_AUTHOR_DECLARATION = "developer-authored-fictional-forum-scenarios-v1"
LABELS = frozenset({"explanation_sufficient", "answer_only_or_insufficient"})
RELEVANCE_LABELS = frozenset({"relevant", "irrelevant"})
COMPOSITE_LABELS = frozenset({"verified", "should_not_verify", "advisory_only"})
LANGUAGES = frozenset({"en", "ms", "mixed"})
MODES = frozenset({"linked", "free_form"})
LINKED = "linked"
FREE_FORM = "free_form"
VERIFIED = "verified"
SHOULD_NOT_VERIFY = "should_not_verify"
ADVISORY_ONLY = "advisory_only"
RELEVANT = "relevant"
IRRELEVANT = "irrelevant"
EXPLANATION_SUFFICIENT = "explanation_sufficient"
ANSWER_ONLY_OR_INSUFFICIENT = "answer_only_or_insufficient"
RUBRIC_DOCUMENT = {
    "rubricVersion": RUBRIC_VERSION,
    "labels": {
        EXPLANATION_SUFFICIENT: "The fictional answer explains mathematical steps or reasoning a peer can follow.",
        ANSWER_ONLY_OR_INSUFFICIENT: "The fictional answer gives only a result or too little reasoning for a peer to follow.",
    },
    "relevance": {
        "relevant": "The fictional response directly addresses the question prompt.",
        "irrelevant": "The fictional response does not address the question prompt.",
    },
    "correctness": {
        "linked_only": "For linked contexts, the selected final answer is compared with the protected server answer key.",
        "free_form": "Free-form responses are never graded for correctness.",
    },
    "composite": {
        "verified": "Correct selected answer AND relevant response AND sufficient reasoning, all non-abstaining.",
        "should_not_verify": "At least one of correctness, relevance, or reasoning fails.",
        "advisory_only": "Free-form responses receive advisory feedback but never a verification badge.",
    },
    "correctnessGrading": True,
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
    expected_correct: bool | None
    expected_relevance: str
    expected_composite: str


@dataclass(frozen=True)
class ForumScenarioFamily:
    scenario_family_id: str
    question_family_id: str | None
    mathematics_scenario_family: str
    prompt: str
    prompt_bm: str
    mode: str
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
                "prompt": family.prompt,
                "promptBm": family.prompt_bm,
                "mode": family.mode,
                "examples": [
                    {
                        "exampleId": example.example_id,
                        "text": example.text,
                        "label": example.label,
                        "language": example.language,
                        "expectedCorrect": example.expected_correct,
                        "expectedRelevance": example.expected_relevance,
                        "expectedComposite": example.expected_composite,
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
    required = {
        "scenarioFamilyId", "mathematicsScenarioFamily", "prompt", "promptBm",
        "mode", "examples",
    }
    optional = {"questionFamilyId"}
    if not required <= set(value) or set(value) - required - optional:
        raise ValueError("scenario family fields must contain exactly the declared schema")
    examples = value["examples"]
    if not isinstance(examples, list) or len(examples) < 2:
        raise ValueError("each scenario family needs at least two examples")
    prompt = _string(value, "prompt")
    prompt_bm = _string(value, "promptBm")
    mode = _string(value, "mode")
    if mode not in MODES:
        raise ValueError("scenario family mode must be linked or free_form")
    _reject_sensitive_text(prompt)
    _reject_sensitive_text(prompt_bm)
    return ForumScenarioFamily(
        scenario_family_id=_string(value, "scenarioFamilyId"),
        question_family_id=_optional_string(value, "questionFamilyId"),
        mathematics_scenario_family=_string(value, "mathematicsScenarioFamily"),
        prompt=" ".join(prompt.split()),
        prompt_bm=" ".join(prompt_bm.split()),
        mode=mode,
        examples=tuple(_parse_example(item, mode) for item in examples),
    )


def _parse_example(value: object, mode: str) -> ForumScenarioExample:
    if not isinstance(value, Mapping):
        raise ValueError("each forum example must be a mapping")
    _exact_keys(value, {
        "exampleId", "text", "label", "language",
        "expectedCorrect", "expectedRelevance", "expectedComposite",
    }, "forum example")
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
    expected_relevance = _string(value, "expectedRelevance")
    if expected_relevance not in RELEVANCE_LABELS:
        raise ValueError("forum example relevance label is unsupported")
    expected_composite = _string(value, "expectedComposite")
    if expected_composite not in COMPOSITE_LABELS:
        raise ValueError("forum example composite label is unsupported")
    expected_correct_value = value.get("expectedCorrect")
    if mode == FREE_FORM:
        if expected_correct_value is not None:
            raise ValueError("free-form examples cannot declare expected correctness")
        expected_correct = None
        if expected_composite != ADVISORY_ONLY:
            raise ValueError("free-form examples must be advisory_only")
    else:
        if not isinstance(expected_correct_value, bool):
            raise ValueError("linked examples must declare expected correctness as a boolean")
        expected_correct = expected_correct_value
    if mode == LINKED:
        all_pass = (
            expected_correct is True
            and expected_relevance == RELEVANT
            and label == EXPLANATION_SUFFICIENT
        )
        if all_pass and expected_composite != VERIFIED:
            raise ValueError("passing linked examples must be verified")
        if not all_pass and expected_composite != SHOULD_NOT_VERIFY:
            raise ValueError("failing linked examples must be should_not_verify")
    return ForumScenarioExample(
        _string(value, "exampleId"),
        " ".join(text.split()),
        label,
        language,
        expected_correct,
        expected_relevance,
        expected_composite,
    )


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
    example_ids = [
        example.example_id
        for family in catalogue.scenario_families
        for example in family.examples
    ]
    if len(family_ids) != len(set(family_ids)):
        raise ValueError("scenarioFamilyId values must be unique")
    if len(example_ids) != len(set(example_ids)):
        raise ValueError("exampleId values must be globally unique")
    for family in catalogue.scenario_families:
        if {example.label for example in family.examples} != LABELS:
            raise ValueError("each scenario family must contain both reasoning labels")
        if {example.expected_relevance for example in family.examples} != RELEVANCE_LABELS:
            raise ValueError("each scenario family must contain both relevance labels")
        if family.mode == LINKED:
            if {example.expected_correct for example in family.examples} != {True, False}:
                raise ValueError("each linked family must contain both correctness outcomes")
            if {example.expected_composite for example in family.examples} != {
                VERIFIED, SHOULD_NOT_VERIFY,
            }:
                raise ValueError("each linked family must contain verified and should_not_verify examples")
        else:
            if any(example.expected_correct is not None for example in family.examples):
                raise ValueError("free-form examples cannot declare correctness")
            if {example.expected_composite for example in family.examples} != {ADVISORY_ONLY}:
                raise ValueError("free-form examples must be advisory_only")
    _validate_coverage(catalogue)


def _validate_coverage(catalogue: ForumScenarioCatalogue) -> None:
    examples = [
        example
        for family in catalogue.scenario_families
        for example in family.examples
    ]
    verified = [
        example for example in examples if example.expected_composite == VERIFIED
    ]
    should_not_verify = [
        example for example in examples if example.expected_composite == SHOULD_NOT_VERIFY
    ]
    irrelevant = [
        example for example in examples if example.expected_relevance == IRRELEVANT
    ]
    relevant = [
        example for example in examples if example.expected_relevance == RELEVANT
    ]
    correctness_gate = [
        example for example in should_not_verify if example.expected_correct is False
    ]
    relevance_gate = [
        example for example in should_not_verify
        if example.expected_relevance == IRRELEVANT
    ]
    reasoning_gate = [
        example for example in should_not_verify
        if example.label == ANSWER_ONLY_OR_INSUFFICIENT
    ]
    for group_name, group in (
        ("verified-eligible", verified),
        ("should-not-verify", should_not_verify),
        ("irrelevant", irrelevant),
        ("relevant controls", relevant),
    ):
        if len(group) < 8:
            raise ValueError(
                f"verification catalogue needs at least eight {group_name} cases",
            )
        if {example.language for example in group} != LANGUAGES:
            raise ValueError(
                f"{group_name} cases must cover en, ms, and mixed languages",
            )
    for gate_name, gate in (
        ("correctness", correctness_gate),
        ("relevance", relevance_gate),
        ("reasoning", reasoning_gate),
    ):
        if len(gate) < 2:
            raise ValueError(
                f"should-not-verify cases must span the {gate_name} failure gate",
            )


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
