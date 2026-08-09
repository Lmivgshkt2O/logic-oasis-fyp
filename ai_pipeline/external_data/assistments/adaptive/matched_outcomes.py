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
    contract_path_v1_1: str | Path,
    contract_path_v1: str | Path,
    configs_dir: str | Path,
) -> dict[str, object]:
    """Fail-closed verification of every frozen E1-E5 artifact and the U7
    outcome contract, including the explicit E5 hash-naming resolution."""
    from .readiness_audit import verify_frozen_lineage

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


def require_frozen_bootstrap_config() -> FrozenBootstrapConfig:
    """Return the frozen CI config, or fail closed with the E6 gate blocker."""
    raise OutcomeGateError(
        "student-clustered descriptive CI configuration not frozen"
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
