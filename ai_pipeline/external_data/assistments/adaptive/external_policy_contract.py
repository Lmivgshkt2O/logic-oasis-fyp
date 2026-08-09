"""AQC-E1 frozen external policy contract loader and fail-closed validator.

This module reads ``assistments_adaptive_contract_v1.yaml`` and rejects any
missing, altered, or boundary-violating contract before later E2-E5 stages may
use it. It performs no calibration and no policy replay.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from typing import Mapping

import yaml

from logic_oasis_ai.bkt import BKT_MODEL_VERSION
from logic_oasis_ai.policy_evaluation import (
    P1_PROMOTION_THRESHOLD,
    P2_DEMOTION_THRESHOLD,
    SelectionEvidenceMode,
)

from .schemas import (
    ATTEMPT_PURITY_THRESHOLD,
    BKT_VERSION,
    EXTERNAL_CANDIDATE_KEY_NAMESPACE,
    EXTERNAL_PROVENANCE,
    FORBIDDEN_EXTERNAL_CLAIM_LEVELS,
    FORBIDDEN_NATIVE_FIELDS,
    MINIMUM_CALIBRATION_LEARNERS,
    PROXY_DIFFICULTY_VALUES,
    REPLAY_MODE,
    REQUIRED_CENSOR_REASONS,
    REVERSAL_HISTORY_SOURCE,
    SKILL_CATALOG_MINIMUM_CALIBRATED_PROBLEMS,
    SKILL_CATALOG_MINIMUM_PER_TIER,
    ExternalClaimLevel,
    ExternalContractError,
)


EXTERNAL_ADAPTIVE_CONTRACT_VERSION = "assistments-adaptive-contract-v1"
EXTERNAL_ADAPTIVE_CONTRACT_V1_1_VERSION = "assistments-adaptive-contract-v1.1"
EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION = "assistments-adaptive-contract-v1.2"
EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION = "assistments-adaptive-contract-v1.3"
AMENDED_CONTRACT_VERSIONS = frozenset(
    {
        EXTERNAL_ADAPTIVE_CONTRACT_V1_1_VERSION,
        EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION,
        EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION,
    }
)

REQUIRED_EXTERNAL_METRICS = frozenset(
    {
        "policy_up_rate",
        "policy_hold_rate",
        "policy_down_rate",
        "p1_p2_agreement_rate",
        "p1_p3a_agreement_rate",
        "p2_p3a_agreement_rate",
        "three_way_agreement_rate",
        "guardrail_activation_rate",
        "descriptive_challenge_opportunity",
        "proxy_tier_matched_outcome_rate",
        "observed_proxy_matched_support_after_up_rate",
        "observed_proxy_matched_success_after_up_rate",
        "matched_hold_support_rate",
        "matched_down_support_rate",
        "counterfactual_proxy_tier_mismatch_rate",
        "no_next_censor_rate",
        "repeat_censor_rate",
        "mixed_proxy_difficulty_rate",
        "bkt_calibration_by_band",
    }
)

REQUIRED_STAGE_B_QUESTIONS = frozenset({"EB1", "EB2", "EB3", "EB4", "EB5", "EB6"})


@dataclass(frozen=True)
class ExternalAdaptiveContract:
    """Typed, validated representation of the frozen E1 contract."""

    contract_version: str
    contract_sha256: str
    dataset_release_id: str
    dataset_name: str
    provenance: str
    evidence_mode: str
    source_mode: str
    calibration_window: tuple[datetime, datetime]
    evaluation_window: tuple[datetime, datetime]
    minimum_calibration_learners: int
    proxy_difficulty_values: tuple[str, ...]
    skill_catalog_minimum_calibrated_problems: int
    skill_catalog_minimum_per_tier: int
    attempt_purity_threshold: Fraction
    replay_mode: str
    reversal_history_source: str
    censor_reasons: frozenset[str]
    allowed_claim_levels: frozenset[str]
    forbidden_claim_levels: frozenset[str]
    production_promotion_allowed: bool
    contains_raw_identifiers: bool
    bkt_version: str
    adaptive_policy_sha256: str
    adaptive_policy_content_sha256: str
    policy_evaluation_sha256: str
    policy_evaluation_content_sha256: str
    fresh_bank_limitation: Mapping[str, object]
    never_fabricate_native_fields: frozenset[str]
    predecessor_contract_version: str | None = None
    predecessor_contract_sha256: str | None = None
    amendment_reason: str | None = None
    tertile_boundary_rule: Mapping[str, object] | None = None
    purity_denominator_rule: Mapping[str, object] | None = None
    statistical_reporting: Mapping[str, object] | None = None

    @property
    def windows_are_disjoint(self) -> bool:
        return self.calibration_window[1] < self.evaluation_window[0]


def load_external_adaptive_contract(
    path: str | Path,
    *,
    version: str = EXTERNAL_ADAPTIVE_CONTRACT_VERSION,
) -> ExternalAdaptiveContract:
    """Load and fail-closed validate the frozen external contract YAML."""
    if version not in AMENDED_CONTRACT_VERSIONS | {EXTERNAL_ADAPTIVE_CONTRACT_VERSION}:
        raise ExternalContractError(f"unsupported external adaptive contract version: {version}")
    source = Path(path)
    try:
        raw_bytes = source.read_bytes()
        data = yaml.safe_load(raw_bytes)
    except (OSError, yaml.YAMLError) as error:
        raise ExternalContractError(
            f"external adaptive contract is unavailable: {source}"
        ) from error
    if not isinstance(data, dict):
        raise ExternalContractError("external adaptive contract must be a mapping")

    base_keys = {
        "contractVersion", "contractRole", "frozenAt", "status",
        "predecessorContracts", "dataset", "evidenceMode", "sourceMode",
        "timeContract", "attemptUnit", "proxyDifficulty", "attemptTier",
        "tierAvailability", "problemSetFingerprint", "freshBankLimitation",
        "replayMode", "policyBindings", "outcomeMatching",
        "censoringVocabulary", "externalMetrics", "claimLevels",
        "stageBQuestions", "sourceAbstraction", "governance",
    }
    if version in AMENDED_CONTRACT_VERSIONS:
        expected_keys = base_keys | {
            "predecessorContractVersion",
            "predecessorContractSha256",
            "amendment",
        }
        if version == EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION:
            expected_keys = expected_keys | {"statisticalReporting"}
    else:
        expected_keys = base_keys
    _require_exact_keys(data, expected_keys, "external adaptive contract")
    if _string(data, "contractVersion") != version:
        raise ExternalContractError("unsupported external adaptive contract version")
    if _string(data, "contractRole") != "external_descriptive_stage_b_contract_freeze":
        raise ExternalContractError("contractRole is not the frozen Stage-B freeze")
    if _string(data, "status") != "frozen":
        raise ExternalContractError("external adaptive contract must be frozen")

    predecessor_contract_version: str | None = None
    predecessor_contract_sha256: str | None = None
    amendment_reason: str | None = None
    tertile_boundary_rule: Mapping[str, object] | None = None
    purity_denominator_rule: Mapping[str, object] | None = None
    statistical_reporting: Mapping[str, object] | None = None
    if version in AMENDED_CONTRACT_VERSIONS:
        predecessor_contract_version = _string(data, "predecessorContractVersion")
        expected_predecessor = (
            EXTERNAL_ADAPTIVE_CONTRACT_VERSION
            if version == EXTERNAL_ADAPTIVE_CONTRACT_V1_1_VERSION
            else EXTERNAL_ADAPTIVE_CONTRACT_V1_1_VERSION
            if version == EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION
            else EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION
        )
        if predecessor_contract_version != expected_predecessor:
            raise ExternalContractError(
                f"amended contract predecessor must be {expected_predecessor}"
            )
        predecessor_contract_sha256 = _sha256(data, "predecessorContractSha256")
        amendment = _mapping(data, "amendment")
        amendment_keys = {
            "reason", "scope", "fixesUnderspecifiedImplementationDetail",
            "motivatedByPolicyPerformance", "policyResultsExistedBeforeAmendment",
            "v1Preserved", "rationale",
        }
        if version == EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION:
            amendment_keys.add("v1_1Preserved")
        if version == EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION:
            amendment_keys.update(
                {
                    "v1_1Preserved",
                    "v1_2Preserved",
                    "outcomeValuesInspectedBeforeAmendment",
                    "policyOutcomeRatesExistedBeforeAmendment",
                }
            )
        _require_exact_keys(amendment, amendment_keys, "amendment")
        amendment_reason = _string(amendment, "reason")
        expected_reason = (
            "deterministic_discrete_tertile_boundary_clarification"
            if version == EXTERNAL_ADAPTIVE_CONTRACT_V1_1_VERSION
            else "attempt_proxy_difficulty_purity_denominator_clarification"
            if version == EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION
            else "external_stage_b_descriptive_cluster_bootstrap_and_calibration_reporting_freeze"
        )
        if amendment_reason != expected_reason:
            raise ExternalContractError("amendment reason is not the frozen clarification")
        expected_scope = (
            "within_skill_tertile_boundaries_only"
            if version == EXTERNAL_ADAPTIVE_CONTRACT_V1_1_VERSION
            else "attempt_purity_denominator_only"
            if version == EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION
            else "statistical_reporting_configuration_only"
        )
        if _string(amendment, "scope") != expected_scope:
            raise ExternalContractError("amendment scope is not within-skill tertile boundaries only")
        if not _bool(amendment, "fixesUnderspecifiedImplementationDetail"):
            raise ExternalContractError("amendment must fix an underspecified implementation detail")
        if _bool(amendment, "motivatedByPolicyPerformance"):
            raise ExternalContractError("amendment must not be motivated by policy performance")
        if _bool(amendment, "policyResultsExistedBeforeAmendment"):
            raise ExternalContractError("no policy result may have existed before the amendment")
        if not _bool(amendment, "v1Preserved"):
            raise ExternalContractError("v1 must remain preserved")
        if (
            version == EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION
            and not _bool(amendment, "v1_1Preserved")
        ):
            raise ExternalContractError("v1.1 must remain preserved")
        if (
            version == EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION
            and not _bool(amendment, "v1_2Preserved")
        ):
            raise ExternalContractError("v1.2 must remain preserved")
        if version == EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION and (
            _bool(amendment, "outcomeValuesInspectedBeforeAmendment")
            or _bool(amendment, "policyOutcomeRatesExistedBeforeAmendment")
        ):
            raise ExternalContractError(
                "no outcome value or policy outcome rate may have existed before the amendment"
            )

    predecessors = _mapping(data, "predecessorContracts")
    shared_aqc = _mapping(predecessors, "sharedAqcPolicyContract")
    if _string(shared_aqc, "policyEvaluationVersion") != "policy-evaluation-v1":
        raise ExternalContractError(
            "predecessor policy evaluation contract is not policy-evaluation-v1"
        )
    if _string(shared_aqc, "adaptivePolicyVersion") != "adaptive-policy-v1":
        raise ExternalContractError("predecessor adaptive policy version is not adaptive-policy-v1")
    if _string(shared_aqc, "bktVersion") != BKT_VERSION:
        raise ExternalContractError("predecessor BKT version is not the frozen bkt-v1")
    u7 = _mapping(predecessors, "u7ExternalRealData")
    if _string(u7, "attemptLabelContract") != "assistments-j2-attempt-label-contract-v2":
        raise ExternalContractError("U7 attempt-label contract is not the v2 contract")
    _sha256(u7, "attemptLabelContractSha256")
    if version in (EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION, EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION):
        history = _mapping(predecessors, "externalAdaptiveContracts")
        v1_history = _mapping(history, "v1")
        v1_1_history = _mapping(history, "v1_1")
        if (
            _string(v1_history, "contractVersion") != EXTERNAL_ADAPTIVE_CONTRACT_VERSION
            or _sha256(v1_history, "contractSha256")
            != "46997eaf92d6c9aba0dc7d8d196080bc03bd59093ef5b2f04a1fd6fc4e424170"
        ):
            raise ExternalContractError("v1 predecessor history is not preserved")
        if (
            _string(v1_1_history, "contractVersion") != EXTERNAL_ADAPTIVE_CONTRACT_V1_1_VERSION
            or _sha256(v1_1_history, "contractSha256")
            != "e54085ddfe1e00e1cd12d02639f02a70681c767a2ea51697548890e8211f63de"
        ):
            raise ExternalContractError("v1.1 predecessor history is not preserved")
        if version == EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION:
            v1_2_history = _mapping(history, "v1_2")
            if (
                _string(v1_2_history, "contractVersion") != EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION
                or _sha256(v1_2_history, "contractSha256")
                != "d82b50432157f9321808dfced5ad7cb55960ce2dbc3501987ab17a23de725955"
            ):
                raise ExternalContractError("v1.2 predecessor history is not preserved")

    dataset = _mapping(data, "dataset")
    provenance = _string(dataset, "provenance")
    if provenance != EXTERNAL_PROVENANCE:
        raise ExternalContractError(
            f"dataset provenance must be {EXTERNAL_PROVENANCE!r}, got {provenance!r}"
        )
    if "runtime_callable" in provenance or "runtime" in provenance:
        raise ExternalContractError(
            "external provenance can never be relabelled as native runtime data"
        )
    cohort = _mapping(dataset, "primaryCohort")
    if _string(cohort, "sourceGrade") != "6" or _string(cohort, "sourceSubject") != "Mathematics":
        raise ExternalContractError("primary cohort must be exact Grade 6 Mathematics")
    if _bool(cohort, "gradeSixAcceleratedMerged"):
        raise ExternalContractError("Grade 6 Accelerated must stay separate")

    evidence = _mapping(data, "evidenceMode")
    if _string(evidence, "mode") != "external_real_proxy_difficulty":
        raise ExternalContractError("evidence mode is not external_real_proxy_difficulty")
    distinct_from = _string_list(evidence, "distinctFrom")
    for native_mode in ("native_runtime", "pipeline_demo_only", "controlled_demo", "stage_c_live_pilot"):
        if native_mode not in distinct_from:
            raise ExternalContractError(f"evidence mode must remain distinct from {native_mode}")
    if not _bool(evidence, "neverPretendsToSatisfyNativeRuntimeContract"):
        raise ExternalContractError(
            "external evidence must not pretend to satisfy the native runtime contract"
        )

    source_mode = _mapping(data, "sourceMode")
    supported_modes = _string_list(source_mode, "supported")
    if supported_modes != ["native_runtime", "assistments_external"]:
        raise ExternalContractError("source-mode vocabulary is incomplete or reordered")
    if not _bool(source_mode, "nativeRuntimeContractUnchanged"):
        raise ExternalContractError("the native runtime contract must remain unchanged")

    time_contract = _mapping(data, "timeContract")
    calibration = _mapping(time_contract, "calibrationWindow")
    evaluation = _mapping(time_contract, "evaluationWindow")
    calibration_start = _parse_datetime(calibration, "start")
    calibration_end = _parse_datetime(calibration, "end")
    evaluation_start = _parse_datetime(evaluation, "start")
    evaluation_end = _parse_datetime(evaluation, "end")
    if calibration_end >= evaluation_start:
        raise ExternalContractError("calibration and evaluation windows must not overlap")
    if _bool(time_contract, "windowsOverlap"):
        raise ExternalContractError("windowsOverlap must be false")
    if not _string(time_contract, "guarantee"):
        raise ExternalContractError("the calibration-independence guarantee is required")

    proxy = _mapping(data, "proxyDifficulty")
    minimum_learners = _positive_int(proxy, "minimumIndependentCalibrationLearnersPerProblem")
    if minimum_learners != MINIMUM_CALIBRATION_LEARNERS:
        raise ExternalContractError(
            "minimum independent calibration learners is not frozen at 20"
        )
    proxy_values = tuple(_string_list(proxy, "proxyDifficultyValues"))
    if proxy_values != PROXY_DIFFICULTY_VALUES:
        raise ExternalContractError("proxy difficulty values are not the frozen tier vocabulary")
    if _string(proxy, "insufficientEvidenceStatus") != "insufficient_problem_evidence":
        raise ExternalContractError("insufficient-problem status is not frozen")
    tiering = _mapping(proxy, "withinSkillTiering")
    if _string(tiering, "tieringScope") != "exact_sourceSkillCode_only":
        raise ExternalContractError("proxy tiers must be constructed within exact sourceSkillCode")
    if version in AMENDED_CONTRACT_VERSIONS:
        boundary = _mapping(tiering, "tertileBoundaryRule")
        _require_exact_keys(
            boundary,
            {
                "appliesTo", "n", "b1", "b2", "assignmentBy1BasedRank",
                "examples", "forbiddenImplementations",
            },
            "tertileBoundaryRule",
        )
        if _string(boundary, "b1") != "floor(n / 3)" or _string(boundary, "b2") != "floor(2 * n / 3)":
            raise ExternalContractError(
                "v1.1 tertile boundaries must be floor(n/3) and floor(2n/3)"
            )
        assignment = _string_list(boundary, "assignmentBy1BasedRank")
        if assignment != [
            "ranks 1 through b1 -> proxy_easy",
            "ranks b1 + 1 through b2 -> proxy_moderate",
            "ranks b2 + 1 through n -> proxy_hard",
        ]:
            raise ExternalContractError("v1.1 rank assignment is not the frozen partition")
        examples = _mapping(boundary, "examples")
        expected_examples = {
            "n9": {"proxy_easy": 3, "proxy_moderate": 3, "proxy_hard": 3},
            "n10": {"proxy_easy": 3, "proxy_moderate": 3, "proxy_hard": 4},
            "n11": {"proxy_easy": 3, "proxy_moderate": 4, "proxy_hard": 4},
            "n12": {"proxy_easy": 4, "proxy_moderate": 4, "proxy_hard": 4},
        }
        if dict(examples) != expected_examples:
            raise ExternalContractError("v1.1 tertile examples are not the frozen examples")
        forbidden = _string_list(boundary, "forbiddenImplementations")
        for item in (
            "pandas qcut",
            "floating quantile interpolation",
            "global cross-skill ranking",
            "random tie breaking",
        ):
            if item not in forbidden:
                raise ExternalContractError(f"forbidden tertile implementation missing: {item}")
        tertile_boundary_rule = dict(boundary)
    catalog = _mapping(proxy, "skillCatalogGate")
    if _positive_int(catalog, "minimumCalibratedProblemsPerSkill") != (
        SKILL_CATALOG_MINIMUM_CALIBRATED_PROBLEMS
    ):
        raise ExternalContractError("skill catalog minimum calibrated problems is not frozen at 9")
    if (
        _positive_int(catalog, "minimumProxyEasy") != SKILL_CATALOG_MINIMUM_PER_TIER
        or _positive_int(catalog, "minimumProxyModerate") != SKILL_CATALOG_MINIMUM_PER_TIER
        or _positive_int(catalog, "minimumProxyHard") != SKILL_CATALOG_MINIMUM_PER_TIER
    ):
        raise ExternalContractError("skill catalog per-tier minimum is not frozen at 3")
    if _string(catalog, "insufficientStatus") != "insufficient_skill_catalog":
        raise ExternalContractError("skill catalog insufficient status is not frozen")
    if not _bool(catalog, "noSilentPoolingOfUnrelatedSkills"):
        raise ExternalContractError("silent pooling of unrelated skills is forbidden")

    attempt_tier = _mapping(data, "attemptTier")
    if _positive_int(attempt_tier, "purityThresholdNumerator") != ATTEMPT_PURITY_THRESHOLD.numerator:
        raise ExternalContractError("attempt purity numerator is not frozen at 2")
    if _positive_int(attempt_tier, "purityThresholdDenominator") != ATTEMPT_PURITY_THRESHOLD.denominator:
        raise ExternalContractError("attempt purity denominator is not frozen at 3")
    if _string(attempt_tier, "mixedCensorReason") != "mixed_proxy_difficulty":
        raise ExternalContractError("mixed-tier censor reason is not frozen")
    if version in (EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION, EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION):
        purity_rule = _mapping(attempt_tier, "purityDenominatorRule")
        _require_exact_keys(
            purity_rule,
            {
                "validProblemCount", "easyCount", "moderateCount", "hardCount",
                "dominantTierCount", "proxyDifficultyPurity", "untieredProblems",
                "assignment", "dominantTierTies", "examples",
            },
            "purityDenominatorRule",
        )
        if _string(purity_rule, "proxyDifficultyPurity") != "dominantTierCount / validProblemCount":
            raise ExternalContractError("v1.2 purity formula is not the frozen denominator rule")
        untiered = _mapping(purity_rule, "untieredProblems")
        _require_exact_keys(
            untiered,
            {
                "remainInValidProblemCount", "contributeToNoTierCount",
                "neverInventedTier", "neverDroppedToIncreasePurity",
                "purityIsNeverDominantOverTieredOnlyCount",
            },
            "untieredProblems",
        )
        if not _bool(untiered, "remainInValidProblemCount"):
            raise ExternalContractError("untiered problems must remain in the denominator")
        if not _bool(untiered, "contributeToNoTierCount"):
            raise ExternalContractError("untiered problems must never enter a tier numerator")
        if not _bool(untiered, "neverDroppedToIncreasePurity"):
            raise ExternalContractError("untiered problems must never be dropped")
        ties = _mapping(purity_rule, "dominantTierTies")
        if _string(ties, "rule") != "no unique dominant tier -> currentProxyDifficulty = null (fail closed, no arbitrary selection)":
            raise ExternalContractError("v1.2 dominant-tier tie rule is not frozen")
        purity_denominator_rule = dict(purity_rule)

    if version == EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION:
        statistical = _mapping(data, "statisticalReporting")
        _require_exact_keys(
            statistical,
            {
                "studentClusteredBootstrap",
                "ciSparsityGuard",
                "bktCalibration",
                "outcomeContractUnchanged",
            },
            "statisticalReporting",
        )
        bootstrap = _mapping(statistical, "studentClusteredBootstrap")
        confidence = bootstrap.get("confidenceLevel")
        confidence_ok = (
            isinstance(confidence, (float, int))
            and not isinstance(confidence, bool)
            and float(confidence) == 0.95
        )
        if (
            _string(bootstrap, "bootstrapUnit") != "externalStudentKey"
            or _positive_int(bootstrap, "bootstrapResamples") != 2000
            or _positive_int(bootstrap, "bootstrapSeed") != 20260716
            or not confidence_ok
            or _string(bootstrap, "intervalMethod") != "percentile"
            or _string(bootstrap, "resamplingMethod") != "learner_cluster_with_replacement"
        ):
            raise ExternalContractError("student-clustered bootstrap is not the frozen configuration")
        if not _bool(bootstrap, "sameConfigurationForAllPolicies"):
            raise ExternalContractError("bootstrap must use the same configuration for all policies")
        if not _bool(bootstrap, "noPolicyDifferenceSuperiorityInterval"):
            raise ExternalContractError("policy-difference superiority intervals are forbidden")
        guard = _mapping(statistical, "ciSparsityGuard")
        if _positive_int(guard, "minimumIndependentLearnersForCI") != 10:
            raise ExternalContractError("sparse-CI guard is not frozen at 10 independent learners")
        if _string(guard, "sparseFlag") != "sparse_independent_learner_evidence":
            raise ExternalContractError("sparse-CI flag is not frozen")
        calibration = _mapping(statistical, "bktCalibration")
        if _string(calibration, "bandSource") != "aqc3_reliability_curve":
            raise ExternalContractError("BKT calibration band source is not the frozen AQC-3 curve")
        expected_bands = [
            {"lower": 0.00, "upper": 0.20, "upperInclusive": False},
            {"lower": 0.20, "upper": 0.40, "upperInclusive": False},
            {"lower": 0.40, "upper": 0.60, "upperInclusive": False},
            {"lower": 0.60, "upper": 0.80, "upperInclusive": False},
            {"lower": 0.80, "upper": 1.00, "upperInclusive": True},
        ]
        if calibration.get("bands") != expected_bands:
            raise ExternalContractError("BKT calibration bands are not the frozen AQC-3 bands")
        if not _bool(calibration, "onePointZeroBelongsToHighestBand"):
            raise ExternalContractError("1.0 must belong to the highest BKT band")
        if not _bool(calibration, "brierScoreDeclared"):
            raise ExternalContractError("Brier score must be declared")
        statistical_reporting = dict(statistical)

    availability = _mapping(data, "tierAvailability")
    if _string(availability, "semantics") != "proxy_tier_catalog_availability":
        raise ExternalContractError(
            "external tier availability must be proxy-tier catalog availability"
        )
    if not _bool(availability, "notHistoricalBankAvailability"):
        raise ExternalContractError("tier availability must not be historical bank availability")
    if _string(availability, "unavailableHoldReason") != "external_proxy_tier_unavailable":
        raise ExternalContractError("unavailable-tier hold reason is not frozen")
    if not _bool(availability, "neverFabricateIsActiveOrBankVersion"):
        raise ExternalContractError("isActive/bank-version metadata must never be fabricated")

    fingerprint = _mapping(data, "problemSetFingerprint")
    if _string(fingerprint, "method") != "SHA256(sourceSkillCode + sorted(valid problem keys))":
        raise ExternalContractError("problem-set fingerprint method is not frozen")
    if not _bool(fingerprint, "neverExposedAsNativeBankId"):
        raise ExternalContractError("problem-set fingerprint must never be exposed as a native bankId")

    fresh_bank = _mapping(data, "freshBankLimitation")
    _require_exact_keys(
        fresh_bank,
        {
            "productionRule", "exactExternalObservability", "externalSubstitute",
            "includedInFullPolicyEquivalenceClaim", "mayAudit", "mayNotClaim",
        },
        "freshBankLimitation",
    )
    if (
        _string(fresh_bank, "productionRule") != "preserved"
        or _string(fresh_bank, "exactExternalObservability") != "unavailable"
        or _string(fresh_bank, "externalSubstitute") != "fresh_problem_exposure_audit_only"
        or _bool(fresh_bank, "includedInFullPolicyEquivalenceClaim")
    ):
        raise ExternalContractError("fresh-bank limitation is not frozen as declared")

    replay = _mapping(data, "replayMode")
    if _string(replay, "mode") != REPLAY_MODE:
        raise ExternalContractError("replay mode is not one_step_non_propagating")
    if _string(replay, "reversalHistorySource") != REVERSAL_HISTORY_SOURCE:
        raise ExternalContractError(
            "reversal-history source must be observed_proxy_difficulty_history"
        )
    if not _bool(replay, "neverFeedCounterfactualOutputsRecursively"):
        raise ExternalContractError("counterfactual outputs must never feed later states")
    if _string(replay, "nextDecisionStateSource") != "actual_historical_assistments_history":
        raise ExternalContractError("the next decision state must come from observed history")

    bindings = _mapping(data, "policyBindings")
    if _bool(bindings, "sourceMetadata"):
        raise ExternalContractError(
            "policy versions must be analysis metadata, never ASSISTments source metadata"
        )
    p3a = _mapping(bindings, "P3a")
    if not _bool(p3a, "bktOnly") or not _bool(p3a, "bypassSupportRiskXgboostInference"):
        raise ExternalContractError("P3a must remain BKT-only and bypass support-risk inference")
    if _string(p3a, "selectionEvidenceMode") != SelectionEvidenceMode.BKT_ONLY_STUDY.value:
        raise ExternalContractError("P3a selection evidence mode is not bkt_only_study")
    if not _bool(p3a, "usedBktFallback"):
        raise ExternalContractError("P3a usedBktFallback must be true")
    if _string(_mapping(bindings, "P1"), "policyVersion") != "score-threshold-v1":
        raise ExternalContractError("P1 policy version is not score-threshold-v1")
    if _string(_mapping(bindings, "P2"), "policyVersion") != "bkt-score-agreement-v1":
        raise ExternalContractError("P2 policy version is not bkt-score-agreement-v1")
    if _string(_mapping(bindings, "P3a"), "policyVersion") != "guarded-bkt-study-v1":
        raise ExternalContractError("P3a policy version is not guarded-bkt-study-v1")
    config_hashes = _mapping(bindings, "configHashes")
    adaptive_sha = _sha256(config_hashes, "adaptivePolicySha256")
    adaptive_content_sha = _sha256(config_hashes, "adaptivePolicyContentSha256")
    evaluation_sha = _sha256(config_hashes, "policyEvaluationSha256")
    evaluation_content_sha = _sha256(config_hashes, "policyEvaluationContentSha256")

    censoring = _mapping(data, "censoringVocabulary")
    censor_reasons = frozenset(_string_list(censoring, "reasons"))
    missing_censors = sorted(REQUIRED_CENSOR_REASONS - censor_reasons)
    if missing_censors:
        raise ExternalContractError(f"censoring vocabulary is missing required reasons: {missing_censors}")
    if not _bool(censoring, "neverTranslateIntoNativeBankErrors"):
        raise ExternalContractError("external censors must never be translated into native-bank errors")

    metrics = _mapping(data, "externalMetrics")
    metric_names = frozenset(_string_list(metrics, "names"))
    missing_metrics = sorted(REQUIRED_EXTERNAL_METRICS - metric_names)
    if missing_metrics:
        raise ExternalContractError(f"external metrics are missing required names: {missing_metrics}")
    reserved = _string_list(metrics, "reservedForStageCOnly")
    if "falsePromotionBurden" not in reserved:
        raise ExternalContractError(
            "falsePromotionBurden must remain reserved for Stage C"
        )

    claims = _mapping(data, "claimLevels")
    allowed_claims = frozenset(_string_list(claims, "allowed"))
    forbidden_claims = frozenset(_string_list(claims, "forbidden"))
    expected_allowed = frozenset(level.value for level in ExternalClaimLevel)
    if allowed_claims != expected_allowed:
        raise ExternalContractError("allowed claim levels are not the frozen vocabulary")
    if not FORBIDDEN_EXTERNAL_CLAIM_LEVELS <= forbidden_claims:
        raise ExternalContractError("forbidden claim levels are incomplete")
    if allowed_claims & forbidden_claims:
        raise ExternalContractError("claim levels overlap allowed/forbidden")
    if _string(claims, "source") != EXTERNAL_PROVENANCE:
        raise ExternalContractError("claim-level source must be external_real")
    if not _bool(claims, "sampleSizeNeverUpgradesToCausalOrSuperiority"):
        raise ExternalContractError("sample size must never upgrade the external claim level")

    questions = _mapping(data, "stageBQuestions")
    if not REQUIRED_STAGE_B_QUESTIONS <= set(questions):
        raise ExternalContractError("Stage-B questions EB1-EB6 are incomplete")

    abstraction = _mapping(data, "sourceAbstraction")
    if _string(abstraction, "reuseEngine") != "existing_aqc2_replay_engine":
        raise ExternalContractError("the existing AQC-2 replay engine must be reused")
    if not _bool(abstraction, "noSecondFullComparisonPipeline"):
        raise ExternalContractError("a second full comparison pipeline is forbidden")
    option = _mapping(abstraction, "evaluationDifficultyOption")
    if "external_proxy_tier" not in _string_list(option, "candidateKinds"):
        raise ExternalContractError("external_proxy_tier candidate kind is missing")
    if _string(option, "externalCandidateKeyNamespace") != EXTERNAL_CANDIDATE_KEY_NAMESPACE:
        raise ExternalContractError("external candidate key namespace is not frozen")

    governance = _mapping(data, "governance")
    if _bool(governance, "productionPromotionAllowed"):
        raise ExternalContractError("production promotion must remain forbidden")
    if _bool(governance, "containsRawIdentifiers"):
        raise ExternalContractError("the contract must declare containsRawIdentifiers false")
    if _bool(governance, "redistributionAllowed"):
        raise ExternalContractError("redistribution must remain forbidden")
    forbidden_fields = frozenset(_string_list(governance, "neverFabricateNativeFields"))
    missing_fields = sorted(FORBIDDEN_NATIVE_FIELDS - forbidden_fields)
    if missing_fields:
        raise ExternalContractError(
            f"native-field fabrication guard is missing entries: {missing_fields}"
        )

    # The frozen contract hash is defined over LF-canonical bytes so it is
    # reproducible on any checkout regardless of line-ending filters.
    return ExternalAdaptiveContract(
        contract_version=version,
        contract_sha256=sha256(raw_bytes.replace(b"\r\n", b"\n")).hexdigest(),
        dataset_release_id=_string(dataset, "releaseId"),
        dataset_name=_string(dataset, "datasetName"),
        provenance=provenance,
        evidence_mode=_string(evidence, "mode"),
        source_mode=",".join(supported_modes),
        calibration_window=(calibration_start, calibration_end),
        evaluation_window=(evaluation_start, evaluation_end),
        minimum_calibration_learners=minimum_learners,
        proxy_difficulty_values=proxy_values,
        skill_catalog_minimum_calibrated_problems=_positive_int(
            catalog, "minimumCalibratedProblemsPerSkill"
        ),
        skill_catalog_minimum_per_tier=_positive_int(catalog, "minimumProxyEasy"),
        attempt_purity_threshold=ATTEMPT_PURITY_THRESHOLD,
        replay_mode=_string(replay, "mode"),
        reversal_history_source=_string(replay, "reversalHistorySource"),
        censor_reasons=censor_reasons,
        allowed_claim_levels=allowed_claims,
        forbidden_claim_levels=forbidden_claims,
        production_promotion_allowed=_bool(governance, "productionPromotionAllowed"),
        contains_raw_identifiers=_bool(governance, "containsRawIdentifiers"),
        bkt_version=BKT_MODEL_VERSION,
        adaptive_policy_sha256=adaptive_sha,
        adaptive_policy_content_sha256=adaptive_content_sha,
        policy_evaluation_sha256=evaluation_sha,
        policy_evaluation_content_sha256=evaluation_content_sha,
        fresh_bank_limitation=dict(fresh_bank),
        never_fabricate_native_fields=forbidden_fields,
        predecessor_contract_version=predecessor_contract_version,
        predecessor_contract_sha256=predecessor_contract_sha256,
        amendment_reason=amendment_reason,
        tertile_boundary_rule=tertile_boundary_rule,
        purity_denominator_rule=purity_denominator_rule,
        statistical_reporting=statistical_reporting,
    )


def verify_frozen_policy_hashes(
    contract: ExternalAdaptiveContract,
    configs_dir: str | Path,
) -> None:
    """Verify the frozen P1/P2/P3a configuration hashes against the live files.

    Content hashes are computed over LF-normalized bytes so the check is
    reproducible on any checkout regardless of line-ending filters. The raw
    recorded hashes are additionally checked against the shared AQC contract's
    recorded values (the adaptive policy raw hash is stable across checkouts).
    """
    configs = Path(configs_dir)
    adaptive_bytes = (configs / "adaptive_policy_v1.yaml").read_bytes()
    evaluation_bytes = (configs / "policy_evaluation_v1.yaml").read_bytes()
    adaptive_lf = adaptive_bytes.replace(b"\r\n", b"\n")
    evaluation_lf = evaluation_bytes.replace(b"\r\n", b"\n")
    if sha256(adaptive_lf).hexdigest() != contract.adaptive_policy_content_sha256:
        raise ExternalContractError("adaptive policy hash changed since the E1 contract freeze")
    if sha256(evaluation_lf).hexdigest() != contract.policy_evaluation_content_sha256:
        raise ExternalContractError(
            "policy evaluation hash changed since the E1 contract freeze"
        )
    if sha256(adaptive_bytes).hexdigest() != contract.adaptive_policy_sha256:
        raise ExternalContractError(
            "adaptive policy raw hash no longer matches the shared AQC contract record"
        )


def verify_shared_aqc_constants(contract: ExternalAdaptiveContract) -> None:
    """Freeze-check the shared AQC policy constants used by the external contract."""
    if contract.bkt_version != BKT_VERSION:
        raise ExternalContractError("BKT version is not the frozen bkt-v1")
    if P1_PROMOTION_THRESHOLD != 0.80 or P2_DEMOTION_THRESHOLD != 0.40:
        raise ExternalContractError("P1/P2 score thresholds changed since the E1 freeze")


def _parse_datetime(data: Mapping[str, object], key: str) -> datetime:
    from datetime import timezone

    value = _string(data, key)
    try:
        normalized = value if "T" in value else f"{value}T00:00:00Z"
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as error:
        raise ExternalContractError(f"window timestamp is invalid: {key}") from error
    if parsed.tzinfo is None:
        raise ExternalContractError(f"window timestamp must be timezone-aware UTC: {key}")
    return parsed.astimezone(timezone.utc)


def _require_exact_keys(
    data: Mapping[str, object], expected: set[str], section: str
) -> None:
    if set(data) != expected:
        missing = sorted(expected - set(data))
        extra = sorted(set(data) - expected)
        raise ExternalContractError(
            f"{section} keys are invalid; missing={missing}, extra={extra}"
        )


def _mapping(data: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ExternalContractError(f"external adaptive contract requires mapping: {key}")
    return value


def _string(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ExternalContractError(f"external adaptive contract requires string: {key}")
    return value


def _string_list(data: Mapping[str, object], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise ExternalContractError(f"external adaptive contract requires string list: {key}")
    if len(set(value)) != len(value):
        raise ExternalContractError(f"external adaptive contract list contains duplicates: {key}")
    return value


def _bool(data: Mapping[str, object], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ExternalContractError(f"external adaptive contract requires boolean: {key}")
    return value


def _positive_int(data: Mapping[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ExternalContractError(f"external adaptive contract requires positive integer: {key}")
    return value


def _sha256(data: Mapping[str, object], key: str) -> str:
    value = _string(data, key)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ExternalContractError(
            f"external adaptive contract requires lowercase SHA-256: {key}"
        )
    return value
