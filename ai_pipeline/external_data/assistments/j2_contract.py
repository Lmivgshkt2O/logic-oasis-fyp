"""Frozen J2 attempt/label contract constants and validation.

Implements the decisions recorded in ``assistments_j2_contract_v1.yaml``.
These values are frozen before the J2 data build and must not be tuned after
observing J3 held-out composition or J4 model performance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from .assistments_contract import PROVENANCE, SOURCE_DATASET


J2_CONTRACT_VERSION = "assistments-j2-attempt-label-contract-v1"
J2_CONTRACT_VERSION_V2 = "assistments-j2-attempt-label-contract-v2"

MASTERY_CRITERION = 0.60
MIN_VALID_GRADED_PROBLEMS = 3
MIN_VALID_RESPONSE_TIME_PAIRS = 3
MAX_RESPONSE_TIME_MS = 1_800_000  # 30 minutes, project-defined telemetry-quality rule

PRIMARY_GRADE = "6"
PRIMARY_SUBJECT = "Mathematics"
FALLBACK_GRADES = ("4", "5", "6")

OUTCOME_VALID = "outcome_valid"
FEATURE_VALID = "feature_valid"
INVALID = "invalid"

GRADED_ACTIONS = ("correct_response", "wrong_response")
PROBLEM_START_ACTION = "problem_started"
ASSIGNMENT_START_ACTION = "assignment_started"
ASSIGNMENT_FINISH_ACTION = "assignment_finished"

# Attempt-level exclusion reasons.
REASON_NO_START = "no_valid_assignment_start_in_window"
REASON_INCOMPLETE = "assignment_not_completed"
REASON_NOT_PRIMARY_COHORT = "not_primary_cohort"
REASON_INSUFFICIENT_GRADED = "insufficient_valid_graded_problems"
REASON_INSUFFICIENT_TIMING = "insufficient_valid_response_time_pairs"

# Pair-level censor reasons.
REASON_NO_NEXT = "no_next_attempt"
REASON_NEXT_NOT_OUTCOME_VALID = "next_not_outcome_valid"
REASON_CHRONOLOGY_AMBIGUOUS = "chronology_ambiguous"
REASON_IDENTICAL_PROBLEM_SET = "immediate_identical_problem_set_repeat"

# Problem-level response-time statuses (counted in the J2 manifest).
RT_VALID = "valid_le_30min"
RT_CENSORED_OVER_30_MIN = "censored_gt_30min"
RT_ZERO = "zero_duration"
RT_NEGATIVE = "negative_duration"
RT_AMBIGUOUS = "ambiguous_pairing"
RT_MISSING_GRADED = "no_graded_response"
RT_NO_START = "no_problem_start"


def load_j2_contract(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        contract = yaml.safe_load(handle)
    if not isinstance(contract, dict):
        raise ValueError("J2 contract must be a YAML mapping")
    return contract


def validate_j2_contract(contract: Mapping[str, Any]) -> Mapping[str, Any]:
    """Fail-closed validation of the frozen J2 contract structure."""
    if contract.get("contractVersion") != J2_CONTRACT_VERSION:
        raise ValueError("J2 contract version is not assistments-j2-attempt-label-contract-v1")
    compatibility = contract.get("compatibilityIdentity")
    if not isinstance(compatibility, dict) or compatibility.get("crossSequencePairingForSampleSize") is not False:
        raise ValueError("compatibility identity must forbid cross-sequence pairing")
    if not isinstance(contract.get("attemptChronology"), dict):
        raise ValueError("attemptChronology is required")
    _validate_frozen_rule_sections(contract, evidence_section="minimumAssignmentEvidence")
    return contract


def validate_j2_contract_v2(contract: Mapping[str, Any]) -> Mapping[str, Any]:
    """Fail-closed validation of the v2 amended (skill-episode) contract."""
    if contract.get("contractVersion") != J2_CONTRACT_VERSION_V2:
        raise ValueError("J2 contract version is not assistments-j2-attempt-label-contract-v2")
    if contract.get("predecessor") != J2_CONTRACT_VERSION:
        raise ValueError("v2 contract predecessor must be assistments-j2-attempt-label-contract-v1")

    amendment = contract.get("amendment")
    if not isinstance(amendment, dict) or amendment.get("motivatedBy") != "source-semantic-mismatch":
        raise ValueError("v2 amendment must be motivated by source-semantic-mismatch")
    if amendment.get("notMotivatedByModelPerformance") is not True:
        raise ValueError("v2 amendment must declare it is not motivated by model performance")

    attempt_unit = contract.get("attemptUnit")
    if not isinstance(attempt_unit, dict) or attempt_unit.get("v2Unit") != "one learner-specific exact-skill episode inside one completed external assignment":
        raise ValueError("v2 attempt unit must be a learner-specific exact-skill episode")
    if attempt_unit.get("usesOnlyResponsesOfThatSkill") is not True or attempt_unit.get("neverMixSkillsInOneEpisode") is not True:
        raise ValueError("v2 episodes must never mix sourceSkillCode values")

    compatibility = contract.get("compatibilityIdentity")
    if not isinstance(compatibility, dict) or compatibility.get("v2Rule") != "same externalStudentKey AND exact non-null sourceSkillCode":
        raise ValueError("v2 compatibility identity must be same learner + exact non-null sourceSkillCode")
    if compatibility.get("crossSkillPairing") is not False:
        raise ValueError("v2 must forbid cross-skill pairing")

    null_skill = contract.get("nullSkillExclusion")
    if not isinstance(null_skill, dict) or null_skill.get("nullSkillEpisodesCannotEnterV2BaseDataset") is not True:
        raise ValueError("v2 must exclude null-skill episodes from the base dataset")
    if null_skill.get("neverAssignOrInferSkillCode") is not True:
        raise ValueError("v2 must never assign or infer a skill code")
    if not isinstance(contract.get("episodeChronology"), dict):
        raise ValueError("episodeChronology is required")

    _validate_frozen_rule_sections(contract, evidence_section="minimumEpisodeEvidence")
    return contract


def _validate_frozen_rule_sections(contract: Mapping[str, Any], *, evidence_section: str) -> None:
    """Validate the rules that v1 and v2 share unchanged."""
    attempt_unit = contract.get("attemptUnit")
    if not isinstance(attempt_unit, dict) or not attempt_unit.get("requiresAssignmentStarted"):
        raise ValueError("attempt unit must require assignment_started")
    if not attempt_unit.get("requiresLaterAssignmentFinished"):
        raise ValueError("attempt unit must require a later assignment_finished")

    cohort = contract.get("primaryCohort")
    if not isinstance(cohort, dict) or cohort.get("sourceGrade") != PRIMARY_GRADE:
        raise ValueError("primary cohort sourceGrade must be 6")
    if cohort.get("sourceSubject") != PRIMARY_SUBJECT:
        raise ValueError("primary cohort sourceSubject must be Mathematics")

    correctness = contract.get("problemCorrectness")
    if not isinstance(correctness, dict) or correctness.get("openResponseUngraded") is not True:
        raise ValueError("problemCorrectness must treat open_response as ungraded")

    quality = contract.get("responseTimeQualityRule")
    if not isinstance(quality, dict):
        raise ValueError("responseTimeQualityRule is required")
    if quality.get("validRangeMilliseconds") != "0 < response_time_ms <= 1800000":
        raise ValueError("response-time valid range is not 0 < response_time_ms <= 1800000")
    if quality.get("thresholdMinutes") != 30 or quality.get("projectDefinedRule") is not True:
        raise ValueError("the 30-minute rule must be recorded as project-defined")

    evidence = contract.get(evidence_section)
    if not isinstance(evidence, dict):
        raise ValueError(f"{evidence_section} is required")
    if evidence.get("minimumValidGradedProblems") != MIN_VALID_GRADED_PROBLEMS:
        raise ValueError("minimumValidGradedProblems must be 3")
    if evidence.get("minimumValidResponseTimePairs") != MIN_VALID_RESPONSE_TIME_PAIRS:
        raise ValueError("minimumValidResponseTimePairs must be 3")

    features = contract.get("featureConstruction")
    if not isinstance(features, dict) or features.get("baseSchema") != "quiz-attempt-features-v2":
        raise ValueError("base schema must remain quiz-attempt-features-v2")
    if features.get("baseFeatures") != ["correct_rate", "mean_response_time_ms"]:
        raise ValueError("base features must be exactly correct_rate and mean_response_time_ms")

    mastery = contract.get("masteryCriterionAndTarget")
    if not isinstance(mastery, dict) or mastery.get("masteryCriterion") != MASTERY_CRITERION:
        raise ValueError("masteryCriterion must be frozen at 0.60")
    if mastery.get("tuneAfterObservingModelResults") is not False:
        raise ValueError("masteryCriterion tuning after model results is forbidden")

    leakage = contract.get("futureLeakageBoundary")
    if not isinstance(leakage, dict) or not (
        leakage.get("currentFeaturesFromCurrentAssignmentOnly") is True
        or leakage.get("currentFeaturesFromCurrentEpisodeOnly") is True
    ):
        raise ValueError("future-leakage boundary must restrict features to the current attempt/episode")

    provenance = contract.get("provenancePrivacy")
    if not isinstance(provenance, dict) or provenance.get("provenance") != PROVENANCE:
        raise ValueError("J2 provenance must be external_real")
    if provenance.get("sourceDataset") != SOURCE_DATASET:
        raise ValueError("J2 sourceDataset must be assistments_edm_cup_2023")

    next_rule = contract.get("nextCompatibleAttemptRule")
    if next_rule is None:
        next_rule = contract.get("nextCompatibleEpisodeRule")
    if not isinstance(next_rule, dict):
        raise ValueError("nextCompatibleAttemptRule/nextCompatibleEpisodeRule is required")
    for section in (
        "multipleOrAmbiguousStarts",
        "identicalQuestionRepeatRule",
        "unresolvedProblemMetadata",
        "bktBoundary",
    ):
        if not isinstance(contract.get(section), dict):
            raise ValueError(f"{section} is required")
