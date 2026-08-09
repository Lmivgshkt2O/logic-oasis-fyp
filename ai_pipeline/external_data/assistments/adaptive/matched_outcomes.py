"""AQC-E6 matched historical outcome stage (structural matching + frozen gates).

E6 attaches later observed outcomes to E5 policy decisions ONLY when the
proposed target proxy tier equals the direct next observed eligible proxy tier.
Mismatched rows are censored as ``counterfactual_proxy_tier_mismatch`` and
their outcome values are never read.  The frozen U7 outcome definition is
reused: ``next_attempt_support_needed`` with mastery criterion 0.60 (NOT the
adaptive 0.80 promotion threshold).

E6 is observational and one-step.  It does not estimate causal effects, does
not use off-policy weighting or synthetic outcomes, and never declares a
policy winner.  Per the frozen E6 gate, aggregate outcome RATES (including
student-clustered descriptive CIs) may only be computed after an approved,
frozen student-clustered bootstrap configuration exists; otherwise E6 stops
before computing/viewing any aggregate outcome rate.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from random import Random
from typing import Iterable, Mapping, Sequence

from logic_oasis_ai.prediction_contract import (
    DEFAULT_MASTERY_CRITERION,
    PREDICTION_LABEL_VERSION,
    PREDICTION_TARGET,
)


E6_MANIFEST_VERSION = "assistments-e6-matched-outcomes-manifest-v1"
E5_MANIFEST_HASH = "209750da34bc7fed5660ea6aa1ae3b0bbdd7cb9c75292ffe46204a9e06316c77"
E5_DECISION_AUDIT_HASH = "75d9b9bdece8f410b787d68d7f7e99c3fb8405785bf142380683d704ff2907ab"
E5_DECISION_AUDIT_FILE_HASH = (
    "067da4bc0dacf0510db52d5688bdecd5112a54ed19e1f2abf3dd485a0379b412"
)
E4_MANIFEST_HASH = "bf8a0b20c94aea98e5b0d66df9ce0efcac1985f039f7b86e8218d3ed2a6c1b9c"
CLAIM_LEVEL = "external_descriptive_replay"
TIERS = ("proxy_easy", "proxy_moderate", "proxy_hard")
MIN_INDEPENDENT_LEARNERS_FOR_CI = 10
SPARSE_CI_FLAG = "sparse_independent_learner_evidence"
BKT_BANDS = (
    {"lower": 0.00, "upper": 0.20, "upperInclusive": False},
    {"lower": 0.20, "upper": 0.40, "upperInclusive": False},
    {"lower": 0.40, "upper": 0.60, "upperInclusive": False},
    {"lower": 0.60, "upper": 0.80, "upperInclusive": False},
    {"lower": 0.80, "upper": 1.00, "upperInclusive": True},
)


class OutcomeGateError(ValueError):
    """Raised when a frozen statistical configuration is required but absent."""


class MatchedOutcomeError(ValueError):
    """Raised when E6 matching cannot proceed safely."""


@dataclass(frozen=True)
class FrozenBootstrapConfig:
    """An APPROVED, frozen student-clustered bootstrap configuration."""

    version: str
    seed: int
    iterations: int
    confidence_level: float

    def __post_init__(self) -> None:
        if self.seed < 0:
            raise MatchedOutcomeError("bootstrap seed cannot be negative")
        if self.iterations < 100:
            raise MatchedOutcomeError("bootstrap iterations must be at least 100")
        if not 0.0 < self.confidence_level < 1.0:
            raise MatchedOutcomeError("confidence level must be between zero and one")


@dataclass(frozen=True)
class MatchedOutcomeRow:
    external_state_key: str
    external_student_key: str
    source_skill_code: str
    policy: str
    proposed_direction: str
    proposed_target_proxy_difficulty: str
    current_proxy_difficulty: str
    next_external_attempt_key: str | None
    next_observed_proxy_difficulty: str | None
    outcome_status: str
    primary_censor_reason: str | None
    secondary_censor_flags: tuple[str, ...]


def verify_e6_inputs(
    *,
    e3_attempts_path: str | Path,
    e3_manifest_path: str | Path,
    e4_manifest_path: str | Path,
    e5_decision_audit_path: str | Path,
    e5_manifest_path: str | Path,
    e2_catalog_path: str | Path,
    e2_manifest_path: str | Path,
    contract_path_v1_2: str | Path,
    contract_path_v1_3: str | Path,
    contract_path_v1_1: str | Path,
    contract_path_v1: str | Path,
    configs_dir: str | Path,
) -> dict[str, object]:
    """Fail-closed verification of every frozen E1-E5 artifact and the U7
    outcome contract, including the explicit E5 hash-naming resolution."""
    from .readiness_audit import verify_frozen_lineage
    from .external_policy_contract import (
        EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION,
        load_external_adaptive_contract,
    )

    v13 = load_external_adaptive_contract(
        contract_path_v1_3,
        version=EXTERNAL_ADAPTIVE_CONTRACT_V1_3_VERSION,
    )
    if v13.predecessor_contract_sha256 != "d82b50432157f9321808dfced5ad7cb55960ce2dbc3501987ab17a23de725955":
        raise MatchedOutcomeError("v1.3 predecessor is not the frozen v1.2 hash")
    if v13.statistical_reporting is None:
        raise MatchedOutcomeError("v1.3 statistical reporting is not frozen")
    require_frozen_bootstrap_config(v13)

    verification = verify_frozen_lineage(
        contract_path_v1_2=contract_path_v1_2,
        contract_path_v1_1=contract_path_v1_1,
        contract_path_v1=contract_path_v1,
        e2_catalog_path=e2_catalog_path,
        e2_manifest_path=e2_manifest_path,
        e3_attempts_path=e3_attempts_path,
        e3_manifest_path=e3_manifest_path,
        configs_dir=configs_dir,
    )
    e4_hash = _file_sha256(e4_manifest_path)
    if e4_hash != E4_MANIFEST_HASH:
        raise MatchedOutcomeError("E4 readiness manifest hash changed since the E4 freeze")
    e5_manifest_hash = _file_sha256(e5_manifest_path)
    if e5_manifest_hash != E5_MANIFEST_HASH:
        raise MatchedOutcomeError("E5 manifest hash changed since the E5 freeze")
    e5_audit_file_hash = _file_sha256(e5_decision_audit_path)
    if e5_audit_file_hash != E5_DECISION_AUDIT_FILE_HASH:
        raise MatchedOutcomeError("E5 decision audit file hash changed since the E5 freeze")
    e5_manifest = json.loads(Path(e5_manifest_path).read_text(encoding="utf-8"))
    if e5_manifest.get("decisionAuditHash") != E5_DECISION_AUDIT_HASH:
        raise MatchedOutcomeError("E5 manifest does not bind the frozen semantic decision audit hash")
    if e5_manifest.get("claimLevel") != CLAIM_LEVEL:
        raise MatchedOutcomeError("E5 claim level is not external_descriptive_replay")
    if e5_manifest.get("p3bExecuted") is not False:
        raise MatchedOutcomeError("E5 p3bExecuted must be false")
    if e5_manifest.get("futureOutcomeValuesUsed") is not False:
        raise MatchedOutcomeError("E5 must not have used future outcome values")
    if (
        e5_manifest.get("decisionRowCounts") != {"P1": 2090, "P2": 2090, "P3a": 2090}
        or e5_manifest.get("sourceStateCount") != 2090
    ):
        raise MatchedOutcomeError("E5 decision row parity/count changed")
    if e5_manifest.get("productionPromotionAllowed") is not False:
        raise MatchedOutcomeError("E5 productionPromotionAllowed must be false")
    if e5_manifest.get("provenance") != "external_real":
        raise MatchedOutcomeError("E5 provenance is not external_real")
    return {
        "verified": True,
        "contractHashV1_2": verification["contractHashV1_2"],
        "contractHashV1_3": v13.contract_sha256,
        "statisticalReporting": dict(v13.statistical_reporting),
        "e2CatalogHash": verification["e2CatalogHash"],
        "e3AttemptsHash": verification["e3AttemptsHash"],
        "e4ReadinessManifestHash": E4_MANIFEST_HASH,
        "e5ManifestHash": E5_MANIFEST_HASH,
        "e5DecisionAuditHash": E5_DECISION_AUDIT_HASH,
        "e5DecisionAuditFileSha256": E5_DECISION_AUDIT_FILE_HASH,
        "hashNamingResolution": {
            "decisionAuditHash": E5_DECISION_AUDIT_HASH,
            "decisionAuditHashMeaning": (
                "canonical/semantic hash of the E5 decision-row documents "
                "(JSON-serialized, sorted); used for decision identity"
            ),
            "decisionAuditFileSha256": E5_DECISION_AUDIT_FILE_HASH,
            "decisionAuditFileSha256Meaning": (
                "physical SHA-256 of the protected decision-audit CSV bytes"
            ),
            "distinctIntentionally": True,
            "consistent": True,
        },
        "u7OutcomeContract": {
            "target": PREDICTION_TARGET,
            "labelVersion": PREDICTION_LABEL_VERSION,
            "masteryCriterion": DEFAULT_MASTERY_CRITERION,
        },
        "provenance": "external_real",
        "containsRawIdentifiers": False,
        "productionPromotionAllowed": False,
        "p3bExecuted": False,
    }


def target_tier_for_direction(
    current_tier: str,
    direction: str,
) -> str:
    """Frozen target semantics: HOLD=current, UP=one higher, DOWN=one lower."""
    index = TIERS.index(current_tier)
    if direction == "hold":
        return current_tier
    if direction == "up":
        target = index + 1
    elif direction == "down":
        target = index - 1
    else:
        raise MatchedOutcomeError(f"unknown proposed direction: {direction}")
    if target < 0 or target >= len(TIERS):
        return current_tier
    return TIERS[target]


def build_next_tier_lookup(
    attempts: Sequence[object],
) -> dict[str, tuple[str | None, str | None, bool, bool]]:
    """state key -> (next key, next observed tier, is_chronology_ambiguous, next_valid).

    Direct next = immediate chronological later attempt for the same learner +
    exact skill (never skips an intervening episode).
    """
    grouped: dict[tuple[str, str], list[object]] = {}
    for attempt in attempts:
        grouped.setdefault(
            (attempt.external_student_key, attempt.source_skill_code), []
        ).append(attempt)
    for key in grouped:
        grouped[key].sort(
            key=lambda a: (
                a.source_timestamp,
                a.external_assignment_key,
                a.external_attempt_sequence,
            )
        )
    lookup: dict[str, tuple[str | None, str | None, bool, bool]] = {}
    for ordered in grouped.values():
        for index, attempt in enumerate(ordered):
            next_attempt = ordered[index + 1] if index + 1 < len(ordered) else None
            if next_attempt is None:
                lookup[attempt.external_attempt_key] = (None, None, False, False)
            else:
                ambiguous = next_attempt.source_timestamp == attempt.source_timestamp
                next_valid = next_attempt.correct_rate is not None
                lookup[attempt.external_attempt_key] = (
                    next_attempt.external_attempt_key,
                    next_attempt.current_proxy_difficulty,
                    ambiguous,
                    next_valid,
                )
    return lookup


def classify_matched_row(
    *,
    state_key: str,
    learner: str,
    skill: str,
    policy: str,
    direction: str,
    current_tier: str,
    next_key: str | None,
    next_tier: str | None,
    next_ambiguous: bool,
    next_valid: bool,
    current_problem_keys: frozenset[str],
    next_problem_keys: frozenset[str],
) -> MatchedOutcomeRow:
    """Classify one policy decision: matched or primary-censor reason.

    The frozen outcome ORDER is enforced: the next observed proxy tier is
    compared to the candidate target BEFORE any outcome value may be used.
    """
    target = target_tier_for_direction(current_tier, direction)
    flags: list[str] = []
    reason: str | None = None
    status = "matched"
    if next_key is None:
        reason = "no_next_eligible_attempt"
        status = "censored"
    elif next_ambiguous:
        reason = "chronology_ambiguous"
        status = "censored"
    elif not next_valid:
        reason = "invalid_next_outcome"
        status = "censored"
    elif current_problem_keys and current_problem_keys == next_problem_keys:
        reason = "identical_problem_set_repeat"
        status = "censored"
    elif next_tier is None or next_tier not in TIERS:
        reason = "next_proxy_tier_missing"
        status = "censored"
    elif abs(TIERS.index(next_tier) - TIERS.index(current_tier)) > 1:
        reason = "non_adjacent_observed_transition"
        status = "censored"
    elif next_tier != target:
        reason = "counterfactual_proxy_tier_mismatch"
        status = "censored"
    else:
        reason = None
        status = "matched"
    if next_key is None or next_ambiguous or not next_valid:
        flags.append("future_structural_unavailable")
    return MatchedOutcomeRow(
        external_state_key=state_key,
        external_student_key=learner,
        source_skill_code=skill,
        policy=policy,
        proposed_direction=direction,
        proposed_target_proxy_difficulty=target,
        current_proxy_difficulty=current_tier,
        next_external_attempt_key=next_key,
        next_observed_proxy_difficulty=next_tier,
        outcome_status=status,
        primary_censor_reason=reason,
        secondary_censor_flags=tuple(flags),
    )


def structural_matching(
    decision_rows: Sequence[Mapping[str, object]],
    attempts: Sequence[object],
) -> list[MatchedOutcomeRow]:
    """Structural per-policy matching; NEVER reads any outcome value."""
    by_attempt: dict[str, object] = {a.external_attempt_key: a for a in attempts}
    lookup = build_next_tier_lookup(attempts)
    rows: list[MatchedOutcomeRow] = []
    for decision in decision_rows:
        state_key = str(decision["externalStateKey"])
        attempt = by_attempt[state_key]
        next_key, next_tier, next_ambiguous, next_valid = lookup[state_key]
        next_attempt = by_attempt.get(next_key) if next_key else None
        rows.append(
            classify_matched_row(
                state_key=state_key,
                learner=str(decision["externalStudentKey"]),
                skill=str(decision["sourceSkillCode"]),
                policy=str(decision["policy"]),
                direction=str(decision["proposedDirection"]),
                current_tier=str(decision["currentProxyDifficulty"]),
                next_key=next_key,
                next_tier=next_tier,
                next_ambiguous=next_ambiguous,
                next_valid=next_valid,
                current_problem_keys=frozenset(attempt.problem_keys),
                next_problem_keys=frozenset(next_attempt.problem_keys) if next_attempt else frozenset(),
            )
        )
    return rows


def matched_outcome_summary(
    rows: Sequence[MatchedOutcomeRow],
) -> dict[str, object]:
    """Structural matched/censor summary per policy (no outcome values)."""
    summary: dict[str, object] = {}
    for policy in ("P1", "P2", "P3a"):
        policy_rows = [row for row in rows if row.policy == policy]
        total = len(policy_rows)
        matched = [row for row in policy_rows if row.outcome_status == "matched"]
        censors = Counter(row.primary_censor_reason for row in policy_rows if row.primary_censor_reason)
        by_direction = Counter(row.proposed_direction for row in matched)
        summary[policy] = {
            "totalDecisions": total,
            "matchedOutcomes": len(matched),
            "matchedLearners": len({row.external_student_key for row in matched}),
            "matchedSkills": len({row.source_skill_code for row in matched}),
            "matchedByDirection": {
                "up": by_direction["up"],
                "hold": by_direction["hold"],
                "down": by_direction["down"],
            },
            "censorCounts": dict(sorted(censors.items())),
            "matchedOutcomeCoverage": _rate(len(matched), total),
        }
    return summary


def require_frozen_bootstrap_config(contract=None) -> FrozenBootstrapConfig:
    """Return the frozen CI config from the v1.3 contract, or fail closed."""
    if contract is None or getattr(contract, "statistical_reporting", None) is None:
        raise OutcomeGateError(
            "student-clustered descriptive CI configuration not frozen"
        )
    bootstrap = contract.statistical_reporting["studentClusteredBootstrap"]
    return FrozenBootstrapConfig(
        version="assistments-adaptive-contract-v1.3",
        seed=int(bootstrap["bootstrapSeed"]),
        iterations=int(bootstrap["bootstrapResamples"]),
        confidence_level=float(bootstrap["confidenceLevel"]),
    )


def student_clustered_bootstrap(
    rows: Sequence[Mapping[str, object]],
    *,
    config: FrozenBootstrapConfig,
    value_key: str,
) -> tuple[float, float]:
    """Student-clustered 95% interval for a matched-outcome rate.

    Only callable with an APPROVED frozen config; clusters by
    externalStudentKey and never retries seeds.
    """
    groups: dict[str, list[Mapping[str, object]]] = {}
    for row in rows:
        groups.setdefault(str(row["externalStudentKey"]), []).append(row)
    keys = sorted(groups)
    if len(keys) < 2:
        raise MatchedOutcomeError("student-clustered CI requires at least two learners")
    observed = _rate(sum(int(row[value_key]) for row in rows), len(rows))
    rng = Random(config.seed)
    estimates: list[float] = []
    for _ in range(config.iterations):
        sample_total = 0
        sample_hits = 0
        for _ in range(len(keys)):
            learner = rng.choice(keys)
            for row in groups[learner]:
                sample_total += 1
                sample_hits += int(row[value_key])
        estimates.append(_rate(sample_hits, sample_total))
    estimates.sort()
    lower_index = max(0, int(round((1 - config.confidence_level) / 2 * len(estimates))) - 1)
    upper_index = min(len(estimates) - 1, int(round((1 + config.confidence_level) / 2 * len(estimates))) - 1)
    return estimates[lower_index], estimates[upper_index]


def attach_matched_outcome(
    row: MatchedOutcomeRow,
    next_correct_rate: float,
    *,
    mastery_criterion: float = DEFAULT_MASTERY_CRITERION,
) -> bool:
    """Attach the frozen U7 outcome ONLY for a matched row.

    Mismatched/censored rows fail closed: their outcome value is never read.
    """
    if row.outcome_status != "matched":
        raise MatchedOutcomeError(
            "outcome value may only be attached after a tier match"
        )
    if next_correct_rate is None or not 0.0 <= next_correct_rate <= 1.0:
        raise MatchedOutcomeError("invalid next correctness outcome")
    return next_correct_rate < mastery_criterion


@dataclass(frozen=True)
class MatchedOutcomeResult:
    external_state_key: str
    external_student_key: str
    source_skill_code: str
    policy: str
    proposed_direction: str
    proposed_target_proxy_difficulty: str
    current_proxy_difficulty: str
    next_external_attempt_key: str | None
    next_observed_proxy_difficulty: str | None
    outcome_status: str
    support_needed: bool | None
    later_success: bool | None


def attach_outcomes(
    rows: Sequence[MatchedOutcomeRow],
    attempts: Sequence[object],
    *,
    mastery_criterion: float = DEFAULT_MASTERY_CRITERION,
) -> list[MatchedOutcomeResult]:
    """Attach the frozen U7 outcome ONLY for tier-matched rows.

    Mismatched/censored rows keep support_needed/later_success None; their
    outcome values are never read.
    """
    by_attempt = {a.external_attempt_key: a for a in attempts}
    results: list[MatchedOutcomeResult] = []
    for row in rows:
        if row.outcome_status != "matched":
            results.append(
                MatchedOutcomeResult(
                    external_state_key=row.external_state_key,
                    external_student_key=row.external_student_key,
                    source_skill_code=row.source_skill_code,
                    policy=row.policy,
                    proposed_direction=row.proposed_direction,
                    proposed_target_proxy_difficulty=row.proposed_target_proxy_difficulty,
                    current_proxy_difficulty=row.current_proxy_difficulty,
                    next_external_attempt_key=row.next_external_attempt_key,
                    next_observed_proxy_difficulty=row.next_observed_proxy_difficulty,
                    outcome_status=row.outcome_status,
                    support_needed=None,
                    later_success=None,
                )
            )
            continue
        next_attempt = by_attempt[row.next_external_attempt_key]
        support = attach_matched_outcome(
            row,
            next_attempt.correct_rate,
            mastery_criterion=mastery_criterion,
        )
        results.append(
            MatchedOutcomeResult(
                external_state_key=row.external_state_key,
                external_student_key=row.external_student_key,
                source_skill_code=row.source_skill_code,
                policy=row.policy,
                proposed_direction=row.proposed_direction,
                proposed_target_proxy_difficulty=row.proposed_target_proxy_difficulty,
                current_proxy_difficulty=row.current_proxy_difficulty,
                next_external_attempt_key=row.next_external_attempt_key,
                next_observed_proxy_difficulty=row.next_observed_proxy_difficulty,
                outcome_status=row.outcome_status,
                support_needed=support,
                later_success=not support,
            )
        )
    return results


def _ci_or_sparse(
    subset: Sequence[MatchedOutcomeResult],
    learner_count: int,
    bootstrap_config: FrozenBootstrapConfig,
) -> tuple[list[float] | None, str | None]:
    if learner_count == 0:
        return None, "not_estimable"
    if learner_count < MIN_INDEPENDENT_LEARNERS_FOR_CI:
        return None, SPARSE_CI_FLAG
    rows = [
        {
            "externalStudentKey": result.external_student_key,
            "support": int(bool(result.support_needed)),
        }
        for result in subset
    ]
    lower, upper = student_clustered_bootstrap(
        rows,
        config=bootstrap_config,
        value_key="support",
    )
    return [lower, upper], None


def policy_direction_outcome_summary(
    results: Sequence[MatchedOutcomeResult],
    bootstrap_config: FrozenBootstrapConfig,
) -> dict[str, object]:
    """Policy/direction matched outcome summary with frozen CI guard."""
    summary: dict[str, object] = {}
    for policy in ("P1", "P2", "P3a"):
        policy_outcomes: dict[str, object] = {}
        for direction in ("up", "hold", "down"):
            subset = [
                result
                for result in results
                if result.policy == policy
                and result.proposed_direction == direction
                and result.outcome_status == "matched"
            ]
            learner_count = len({r.external_student_key for r in subset})
            support_count = sum(1 for r in subset if r.support_needed)
            success_count = sum(1 for r in subset if r.later_success)
            total = len(subset)
            ci, ci_flag = _ci_or_sparse(subset, learner_count, bootstrap_config)
            policy_outcomes[direction] = {
                "matchedDecisions": total,
                "independentLearners": learner_count,
                "skills": len({r.source_skill_code for r in subset}),
                "supportNeededCount": support_count,
                "laterSuccessCount": success_count,
                "observedSupportNeededRate": _rate(support_count, total),
                "observedLaterSuccessRate": _rate(success_count, total),
                "confidenceInterval": ci,
                "ciStatus": "computed" if ci is not None else ci_flag,
            }
        summary[policy] = policy_outcomes
    return summary


def eb4_metrics(
    summary: Mapping[str, object],
) -> dict[str, object]:
    """EB4: matched-UP support-needed vs later-success by policy."""
    result: dict[str, object] = {}
    for policy in ("P1", "P2", "P3a"):
        up = summary[policy]["up"]
        result[policy] = {
            "matchedUpDecisions": up["matchedDecisions"],
            "independentLearners": up["independentLearners"],
            "skills": up["skills"],
            "supportNeededCount": up["supportNeededCount"],
            "laterSuccessCount": up["laterSuccessCount"],
            "observedSupportNeededRate": up["observedSupportNeededRate"],
            "observedLaterSuccessRate": up["observedLaterSuccessRate"],
            "confidenceInterval": up["confidenceInterval"],
            "ciStatus": up["ciStatus"],
        }
    return result


def bkt_calibration(
    attempts: Sequence[object],
    shared_state_keys: Sequence[str],
    bootstrap_config: FrozenBootstrapConfig,
    *,
    mastery_criterion: float = DEFAULT_MASTERY_CRITERION,
) -> dict[str, object]:
    """Policy-independent BKT calibration (current mastery vs later success)."""
    lookup = build_next_tier_lookup(attempts)
    by_attempt = {a.external_attempt_key: a for a in attempts}
    calibration_rows: list[tuple[str, float, bool]] = []
    for key in shared_state_keys:
        next_key, _tier, ambiguous, valid = lookup.get(key, (None, None, False, False))
        if next_key is None or ambiguous or not valid:
            continue
        current = by_attempt[key]
        next_attempt = by_attempt[next_key]
        if current.problem_keys and set(current.problem_keys) == set(next_attempt.problem_keys):
            continue
        support = next_attempt.correct_rate < mastery_criterion
        calibration_rows.append(
            (current.external_student_key, current.bkt_mastery_probability, support)
        )
    band_rows: list[dict[str, object]] = []
    for band in BKT_BANDS:
        lower = float(band["lower"])
        upper = float(band["upper"])
        inclusive = bool(band["upperInclusive"])
        subset = [
            row
            for row in calibration_rows
            if lower <= row[1] < upper or (inclusive and row[1] == upper)
        ]
        learner_count = len({row[0] for row in subset})
        success = sum(1 for row in subset if not row[2])
        mean_mastery = sum(row[1] for row in subset) / len(subset) if subset else None
        ci, ci_flag = _calibration_band_ci(subset, learner_count, bootstrap_config)
        band_rows.append(
            {
                "bandLower": lower,
                "bandUpper": upper,
                "bandUpperInclusive": inclusive,
                "rowCount": len(subset),
                "independentLearners": learner_count,
                "meanPredictedMastery": mean_mastery,
                "observedLaterSuccessRate": _rate(success, len(subset)),
                "confidenceInterval": ci,
                "ciStatus": "computed" if ci is not None else ci_flag,
            }
        )
    brier = (
        sum(
            (mastery - (0.0 if support else 1.0)) ** 2
            for _learner, mastery, support in calibration_rows
        )
        / len(calibration_rows)
        if calibration_rows
        else None
    )
    return {
        "populationRowCount": len(calibration_rows),
        "populationLearnerCount": len({row[0] for row in calibration_rows}),
        "brierScore": brier,
        "bands": band_rows,
        "masteryCriterion": mastery_criterion,
    }


def _calibration_band_ci(
    subset: Sequence[tuple[str, float, bool]],
    learner_count: int,
    bootstrap_config: FrozenBootstrapConfig,
) -> tuple[list[float] | None, str | None]:
    if learner_count == 0:
        return None, "not_estimable"
    if learner_count < MIN_INDEPENDENT_LEARNERS_FOR_CI:
        return None, SPARSE_CI_FLAG
    rows = [
        {
            "externalStudentKey": learner,
            "support": 0 if support else 1,
        }
        for learner, _mastery, support in subset
    ]
    lower, upper = student_clustered_bootstrap(
        rows,
        config=bootstrap_config,
        value_key="support",
    )
    return [lower, upper], None


def matched_outcome_results_hash(results: Sequence[MatchedOutcomeResult]) -> str:
    payload = json.dumps(
        [
            {
                "state": r.external_state_key,
                "policy": r.policy,
                "direction": r.proposed_direction,
                "status": r.outcome_status,
                "supportNeeded": r.support_needed,
            }
            for r in sorted(results, key=lambda r: (r.external_state_key, r.policy))
        ],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest()


MATCHED_OUTCOME_CSV_FIELDS = (
    "externalStateKey",
    "externalStudentKey",
    "sourceSkillCode",
    "policy",
    "proposedDirection",
    "proposedTargetProxyDifficulty",
    "currentProxyDifficulty",
    "nextExternalAttemptKey",
    "nextObservedProxyDifficulty",
    "outcomeStatus",
    "supportNeeded",
    "laterSuccess",
)


def write_matched_outcomes_csv(
    results: Sequence[MatchedOutcomeResult],
    path: str | Path,
) -> Path:
    destination = Path(path)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MATCHED_OUTCOME_CSV_FIELDS)
        writer.writeheader()
        for result in sorted(
            results, key=lambda r: (r.external_state_key, r.policy)
        ):
            writer.writerow(
                {
                    "externalStateKey": result.external_state_key,
                    "externalStudentKey": result.external_student_key,
                    "sourceSkillCode": result.source_skill_code,
                    "policy": result.policy,
                    "proposedDirection": result.proposed_direction,
                    "proposedTargetProxyDifficulty": result.proposed_target_proxy_difficulty,
                    "currentProxyDifficulty": result.current_proxy_difficulty,
                    "nextExternalAttemptKey": result.next_external_attempt_key or "",
                    "nextObservedProxyDifficulty": result.next_observed_proxy_difficulty or "",
                    "outcomeStatus": result.outcome_status,
                    "supportNeeded": (
                        "true" if result.support_needed is True else "false" if result.support_needed is False else ""
                    ),
                    "laterSuccess": (
                        "true" if result.later_success is True else "false" if result.later_success is False else ""
                    ),
                }
            )
    return destination


def build_e6_manifest(
    *,
    verification: Mapping[str, object],
    structural_summary: Mapping[str, object],
    outcome_summary: Mapping[str, object],
    eb4: Mapping[str, object],
    bkt_cal: Mapping[str, object],
    coverage: Mapping[str, object],
    bootstrap_config: FrozenBootstrapConfig,
    matched_outcomes_hash: str,
) -> dict[str, object]:
    """Deterministic E6 outcome manifest (no timestamps/local paths)."""
    return {
        "manifestSchemaVersion": E6_MANIFEST_VERSION,
        "contractVersion": "assistments-adaptive-contract-v1.3",
        "contractHash": verification["contractHashV1_3"],
        "u7OutcomeContractVersion": PREDICTION_LABEL_VERSION,
        "u7OutcomeTarget": PREDICTION_TARGET,
        "masteryCriterion": DEFAULT_MASTERY_CRITERION,
        "e2DifficultyCatalogHash": verification["e2CatalogHash"],
        "e3AttemptHash": verification["e3AttemptsHash"],
        "e4ReadinessManifestHash": verification["e4ReadinessManifestHash"],
        "e5DecisionAuditHash": verification["e5DecisionAuditHash"],
        "e5ManifestHash": verification["e5ManifestHash"],
        "sharedStateCount": 2090,
        "policyDecisionCounts": {"P1": 2090, "P2": 2090, "P3a": 2090},
        "policyMatchedOutcomeCounts": {
            policy: structural_summary[policy]["matchedOutcomes"]
            for policy in ("P1", "P2", "P3a")
        },
        "policyMatchedUpCounts": {
            policy: structural_summary[policy]["matchedByDirection"]["up"]
            for policy in ("P1", "P2", "P3a")
        },
        "policyMatchedHoldCounts": {
            policy: structural_summary[policy]["matchedByDirection"]["hold"]
            for policy in ("P1", "P2", "P3a")
        },
        "policyMatchedDownCounts": {
            policy: structural_summary[policy]["matchedByDirection"]["down"]
            for policy in ("P1", "P2", "P3a")
        },
        "policyCensorCounts": {
            policy: structural_summary[policy]["censorCounts"]
            for policy in ("P1", "P2", "P3a")
        },
        "policyMatchedLearnerCounts": {
            policy: structural_summary[policy]["matchedLearners"]
            for policy in ("P1", "P2", "P3a")
        },
        "policyMatchedSkillCounts": {
            policy: structural_summary[policy]["matchedSkills"]
            for policy in ("P1", "P2", "P3a")
        },
        "observedSupportAfterMatchedUpCounts": {
            policy: outcome_summary[policy]["up"]["supportNeededCount"]
            for policy in ("P1", "P2", "P3a")
        },
        "observedSuccessAfterMatchedUpCounts": {
            policy: outcome_summary[policy]["up"]["laterSuccessCount"]
            for policy in ("P1", "P2", "P3a")
        },
        "policyDirectionOutcomeSummary": outcome_summary,
        "eb4": eb4,
        "matchedCoverageMetrics": coverage,
        "bktCalibrationPopulationCount": bkt_cal["populationRowCount"],
        "bktCalibrationLearnerCount": bkt_cal["populationLearnerCount"],
        "bktCalibrationMetrics": bkt_cal,
        "bootstrapConfigVersion": bootstrap_config.version,
        "bootstrapSeed": bootstrap_config.seed,
        "bootstrapResamples": bootstrap_config.iterations,
        "confidenceLevel": bootstrap_config.confidence_level,
        "matchedOutcomesSha256": matched_outcomes_hash,
        "claimLevel": CLAIM_LEVEL,
        "provenance": "external_real",
        "containsRawIdentifiers": False,
        "productionPromotionAllowed": False,
        "p3bExecuted": False,
        "causalClaimAllowed": False,
    }


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 8)


def _file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
