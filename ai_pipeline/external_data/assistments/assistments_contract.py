"""Frozen J0 contract helpers for the ASSISTments EDM Cup 2023 external path.

This module is intentionally pure: it never reads the protected raw CSVs and
never constructs learner-level extracts.  It encodes the physical -> semantic
decisions that J0 detected on 2026-08-07 so that tests, the bounded inspector,
and the later J1 adapter share one versioned contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import yaml


SOURCE_DATASET = "assistments_edm_cup_2023"
PROVENANCE = "external_real"
SCHEMA_MAPPING_VERSION = "assistments-schema-mapping-v1"

# Frozen U7 window: only source actions inside this inclusive window may enter
# the final FYP1 U7 evidence path.
WINDOW_START = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

# Detected physical action values (exact capitalization from action_logs.csv).
PROBLEM_START_ACTION = "problem_started"
PROBLEM_FINISH_ACTION = "problem_finished"
ASSIGNMENT_START_ACTION = "assignment_started"
ASSIGNMENT_FINISH_ACTION = "assignment_finished"
ASSIGNMENT_RESUME_ACTION = "assignment_resumed"
ANSWER_REQUESTED_ACTION = "answer_requested"
OPEN_RESPONSE_ACTION = "open_response"
CONTINUE_SELECTED_ACTION = "continue_selected"
HINT_REQUESTED_ACTION = "hint_requested"
EXPLANATION_REQUESTED_ACTION = "explanation_requested"

# Graded response actions: action value -> first-response correctness.
GRADED_ACTIONS: Mapping[str, bool] = {
    "correct_response": True,
    "wrong_response": False,
}

# Detected base-U7 source files and their semantic roles.
REQUIRED_BASE_U7_FILES = (
    "action_logs.csv",
    "assignment_details.csv",
    "problem_details.csv",
    "sequence_details.csv",
)
RELATIONSHIP_FILES = (
    "assignment_relationships.csv",
    "sequence_relationships.csv",
)
EXCLUDED_SOURCE_FILES = (
    "training_unit_test_scores.csv",
    "evaluation_unit_test_scores.csv",
    "hint_details.csv",
    "explanation_details.csv",
)

# Semantic concepts every valid mapping must resolve to a physical field.
REQUIRED_SEMANTIC_CONCEPTS = (
    "learner",
    "assignment",
    "problem",
    "sequence",
    "event_type",
    "event_timestamp",
    "grade",
    "subject",
    "curriculum_context",
    "assignment_chronology",
    "problem_skill_relationship",
    "sequence_problem_relationship",
    "assignment_sequence_relationship",
)

# Native Logic Oasis runtime fields must never be fabricated onto ASSISTments
# rows; ASSISTments evidence stays external_real only.
FORBIDDEN_NATIVE_FIELDS = (
    "finalizationStatus",
    "validationStatus",
    "sourceAttemptSequence",
    "contentVersionId",
    "bankId",
    "adaptivePolicyVersion",
    "runtimePolicyVersion",
)
FORBIDDEN_NATIVE_PROVENANCE_VALUES = (
    "runtime_callable",
    "logic_oasis_runtime_real",
    "native_logic_oasis_quizAttempts",
)
FORBIDDEN_NATIVE_TERMS = (
    "finalizationStatus",
    "validationStatus",
    "sourceAttemptSequence",
    "contentVersionId",
    "runtime policy version",
    "native bank assignment metadata",
)

GRADE_LEVEL_2_PATTERN = r"^Grade ([1-8])$"
GRADE_ACCELERATED_LEVEL_2 = "Grade 6 Accelerated"
SKILL_CODE_GRADE_PATTERN = r"^([1-8])\."


def parse_epoch_seconds(value: object) -> datetime | None:
    """Parse the detected epoch-seconds timestamp (UTC) or return None.

    action_logs.timestamp and assignment_details time fields are epoch seconds
    with millisecond fractional precision.  Missing, empty, and unparseable
    values return None so callers fail closed.
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    try:
        return datetime.fromtimestamp(numeric, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def in_selected_window(timestamp: datetime | None) -> bool:
    """Fail-closed window rule: inclusive 2022-01-01 .. 2023-12-31."""
    if timestamp is None or timestamp.tzinfo is None:
        return False
    return WINDOW_START <= timestamp <= WINDOW_END


def is_graded_action(action: object) -> bool:
    return isinstance(action, str) and action in GRADED_ACTIONS


def graded_correctness(action: object) -> bool | None:
    """Return the first-response correctness for a graded action."""
    if not isinstance(action, str):
        return None
    return GRADED_ACTIONS.get(action)


def response_time_ms(start: datetime, graded: datetime) -> float:
    """Millisecond duration between a problem start and its graded response."""
    if start is None or graded is None:
        raise ValueError("response-time pairing requires start and graded timestamps")
    if start.tzinfo is None or graded.tzinfo is None:
        raise ValueError("response-time pairing requires timezone-aware timestamps")
    duration_ms = (graded - start).total_seconds() * 1000.0
    if duration_ms < 0:
        raise ValueError("negative response time is not admissible")
    return duration_ms


def first_graded_response(events: Sequence[tuple[datetime, str]]) -> tuple[datetime, str] | None:
    """First graded response (correct_response/wrong_response) in event order."""
    for timestamp, action in events:
        if is_graded_action(action):
            return timestamp, action
    return None


def pair_problem_duration(
    start_events: Sequence[tuple[datetime, str]],
    all_events: Sequence[tuple[datetime, str]],
) -> tuple[bool, float | None, str | None]:
    """Validate a problem-start -> first-graded-response pairing.

    Returns (paired, duration_ms, reason).  Missing start, missing graded
    response, or a negative duration are reported as unpaired rather than
    silently substituted.
    """
    if not start_events:
        return False, None, "missing_problem_start"
    start_time = min(timestamp for timestamp, _ in start_events)
    after_start = [(t, a) for t, a in all_events if t >= start_time]
    graded = first_graded_response(after_start)
    if graded is None:
        return False, None, "missing_graded_response"
    graded_time, _ = graded
    try:
        duration = response_time_ms(start_time, graded_time)
    except ValueError:
        return False, None, "negative_duration"
    return True, duration, None


def grade_from_level_2(value: object) -> str | None:
    """Extract the exact 'Grade N' token from sequence_folder_path_level_2."""
    import re

    if not isinstance(value, str):
        return None
    match = re.fullmatch(GRADE_LEVEL_2_PATTERN, value.strip())
    return match.group(1) if match else None


def is_primary_grade_six_level_2(value: object) -> bool:
    return isinstance(value, str) and value.strip() == "Grade 6"


def grade_from_skill_code(skill_code: object) -> str | None:
    """Corroborating grade from a CCSS skill code such as '6.RP.A.3b'."""
    import re

    if not isinstance(skill_code, str):
        return None
    match = re.match(SKILL_CODE_GRADE_PATTERN, skill_code.strip())
    return match.group(1) if match else None


def validate_provenance_external_real(provenance: object) -> str:
    """Reject any attempt to relabel ASSISTments rows as native runtime data."""
    if provenance != PROVENANCE:
        raise ValueError(f"ASSISTments provenance must be {PROVENANCE!r}, got {provenance!r}")
    return PROVENANCE


def detect_forbidden_native_terms(mapping_text: str) -> tuple[str, ...]:
    """Return forbidden native terms present in a mapping/source description."""
    lowered = mapping_text.lower()
    return tuple(term for term in FORBIDDEN_NATIVE_TERMS if term.lower() in lowered)


def load_schema_mapping(path: str | Path) -> dict[str, object]:
    with Path(path).open(encoding="utf-8") as handle:
        mapping = yaml.safe_load(handle)
    if not isinstance(mapping, dict):
        raise ValueError("schema mapping must be a YAML mapping")
    return mapping


def validate_schema_mapping(mapping: Mapping[str, object]) -> Mapping[str, object]:
    """Fail-closed structural validation of the physical -> semantic mapping."""
    if mapping.get("schemaMappingVersion") != SCHEMA_MAPPING_VERSION:
        raise ValueError("schema mapping version is not assistments-schema-mapping-v1")
    if mapping.get("source", {}).get("provenance") != PROVENANCE:
        raise ValueError("mapping provenance must be external_real")

    concepts = mapping.get("semanticConcepts")
    if not isinstance(concepts, dict):
        raise ValueError("semanticConcepts is required")
    for concept in REQUIRED_SEMANTIC_CONCEPTS:
        entry = concepts.get(concept)
        if not isinstance(entry, dict):
            raise ValueError(f"semantic concept {concept!r} is missing")
        field = entry.get("physicalField")
        fields = entry.get("physicalFields")
        if isinstance(field, str) and field:
            continue
        if isinstance(fields, list) and fields and all(isinstance(item, str) and item for item in fields):
            continue
        if not isinstance(field, str) or not field:
            raise ValueError(f"semantic concept {concept!r} requires a physicalField")

    files = mapping.get("physicalFiles")
    if not isinstance(files, dict):
        raise ValueError("physicalFiles is required")
    for filename in REQUIRED_BASE_U7_FILES:
        entry = files.get(filename)
        if not isinstance(entry, dict) or entry.get("requiredForBaseU7") is not True:
            raise ValueError(f"{filename} must be marked required for base U7")

    actions = mapping.get("actionSemantics")
    if not isinstance(actions, dict):
        raise ValueError("actionSemantics is required")
    for action in ("problem_started", "correct_response", "wrong_response"):
        if not isinstance(actions.get(action), dict):
            raise ValueError(f"actionSemantics.{action} is required")

    for section in ("correctnessContract", "responseTimeContract", "gradeFilterContract", "dateWindowContract", "featureContract", "governance"):
        if not isinstance(mapping.get(section), dict):
            raise ValueError(f"{section} is required")
    return mapping


def ordered_events(
    rows: Iterable[tuple[object, object]],
) -> list[tuple[datetime, str]]:
    """Deterministic event ordering: (parsed UTC timestamp, action).

    Rows with an unparseable timestamp are dropped from chronological evidence
    (fail closed) rather than guessed.
    """
    events: list[tuple[datetime, str]] = []
    for timestamp_value, action in rows:
        parsed = parse_epoch_seconds(timestamp_value)
        if parsed is None or not isinstance(action, str) or not action:
            continue
        events.append((parsed, action))
    events.sort(key=lambda item: item[0])
    return events
