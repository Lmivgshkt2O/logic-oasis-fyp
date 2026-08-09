"""AQC-E4 Stage-B readiness / sufficiency / coverage audit (no policy selectors).

E4 audits whether the frozen 2022-2023 ASSISTments external dataset contains
enough real, independent, policy-ready learner-skill states and structurally
valid future history to justify P1/P2/P3a replay.  It defines a shared
structural current-state population WITHOUT calling any policy selector, then
reports the filtering funnel, tier distribution, adjacent-tier availability,
BKT readiness, reversal-history readiness, fresh-problem exposure, direct-next
episode availability, potential (structural) tier-match opportunities, and the
censoring burden.  Outcome VALUES are never used to decide readiness.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from statistics import median, quantiles
from typing import Iterable, Mapping, Sequence

from logic_oasis_ai.adaptive_policy import load_adaptive_policy_config

from .adaptive_attempts import (
    E2_CATALOG_HASH,
    E2_MANIFEST_HASH,
    verify_stage_b_frozen,
)


E4_MANIFEST_VERSION = "assistments-e4-readiness-manifest-v1"
E3_ATTEMPTS_HASH = "b065d1d3cc70fc9086f92f24f998aed62a0d597ac74c1d2b9f385a1c4cd3b6a6"
E3_MANIFEST_HASH = "f5a966e98329c0936c12bce8728cf1601a57e8a649befd95c612b5cec468c2f1"

TIERS = ("proxy_easy", "proxy_moderate", "proxy_hard")


class ReadinessError(ValueError):
    """Raised when the E4 audit cannot proceed safely."""


@dataclass(frozen=True)
class ReadinessAttempt:
    """One parsed E3 reconstructed attempt (structural audit fields only)."""

    external_attempt_key: str
    external_student_key: str
    external_assignment_key: str
    source_skill_code: str
    source_timestamp: datetime
    external_attempt_sequence: int
    problem_keys: tuple[str, ...]
    total_questions: int
    correct_count: int
    correct_rate: float
    bkt_mastery_probability: float
    bkt_evidence_count: int
    bkt_version: str
    current_proxy_difficulty: str | None
    proxy_difficulty_purity: float | None
    external_problem_set_fingerprint: str
    previous_observed_proxy_difficulty: str | None
    fresh_problem_fraction: float | None
    skill_proxy_status: str
    current_tier_censor_reason: str | None
    cold_history: bool
    chronology_ambiguous: bool
    provenance: str


def load_attempts(path: str | Path) -> list[ReadinessAttempt]:
    """Parse the frozen E3 attempts CSV."""
    attempts: list[ReadinessAttempt] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            attempts.append(
                ReadinessAttempt(
                    external_attempt_key=row["externalAttemptKey"],
                    external_student_key=row["externalStudentKey"],
                    external_assignment_key=row["externalAssignmentKey"],
                    source_skill_code=row["sourceSkillCode"],
                    source_timestamp=datetime.fromisoformat(
                        row["sourceTimestamp"].replace("Z", "+00:00")
                    ),
                    external_attempt_sequence=int(row["externalAttemptSequence"]),
                    problem_keys=tuple(
                        key for key in row["problemKeys"].split("|") if key
                    ),
                    total_questions=int(row["totalQuestions"]),
                    correct_count=int(row["correctCount"]),
                    correct_rate=float(row["correctRate"]),
                    bkt_mastery_probability=float(row["bktMasteryProbability"]),
                    bkt_evidence_count=int(row["bktEvidenceCount"]),
                    bkt_version=row["bktVersion"],
                    current_proxy_difficulty=(
                        row["currentProxyDifficulty"] or None
                    ),
                    proxy_difficulty_purity=(
                        float(row["proxyDifficultyPurity"])
                        if row["proxyDifficultyPurity"]
                        else None
                    ),
                    external_problem_set_fingerprint=row["externalProblemSetFingerprint"],
                    previous_observed_proxy_difficulty=(
                        row["previousObservedProxyDifficulty"] or None
                    ),
                    fresh_problem_fraction=(
                        float(row["freshProblemFraction"])
                        if row["freshProblemFraction"]
                        else None
                    ),
                    skill_proxy_status=row["skillProxyStatus"],
                    current_tier_censor_reason=(
                        row["currentTierCensorReason"] or None
                    ),
                    cold_history=row["coldHistory"] == "true",
                    chronology_ambiguous=row["chronologyAmbiguous"] == "true",
                    provenance=row["provenance"],
                )
            )
    return attempts


def verify_frozen_lineage(
    *,
    contract_path_v1_2: str | Path,
    contract_path_v1_1: str | Path,
    contract_path_v1: str | Path,
    e2_catalog_path: str | Path,
    e2_manifest_path: str | Path,
    e3_attempts_path: str | Path,
    e3_manifest_path: str | Path,
    configs_dir: str | Path,
) -> dict[str, object]:
    """Fail-closed verification of every frozen E1-E3 artifact E4 depends on."""
    attempts_hash = _file_sha256(e3_attempts_path)
    manifest_hash = _file_sha256(e3_manifest_path)
    if attempts_hash != E3_ATTEMPTS_HASH:
        raise ReadinessError("E3 attempts CSV hash changed since the E3 freeze")
    if manifest_hash != E3_MANIFEST_HASH:
        raise ReadinessError("E3 manifest hash changed since the E3 freeze")
    e3_manifest = json.loads(Path(e3_manifest_path).read_text(encoding="utf-8"))
    if e3_manifest.get("attemptsSha256") != E3_ATTEMPTS_HASH:
        raise ReadinessError("E3 manifest does not bind the frozen attempts hash")
    for key in ("containsRawIdentifiers", "productionPromotionAllowed"):
        if e3_manifest.get(key) is not False:
            raise ReadinessError(f"E3 manifest {key} must be false")
    if e3_manifest.get("provenance") != "external_real":
        raise ReadinessError("E3 provenance is not external_real")
    if e3_manifest.get("chronologyAmbiguousAttempts", 0) != 0:
        raise ReadinessError("E3 chronology ambiguity is not zero")
    base = verify_stage_b_frozen(
        contract_path_v1_2=contract_path_v1_2,
        contract_path_v1_1=contract_path_v1_1,
        contract_path_v1=contract_path_v1,
        e2_catalog_path=e2_catalog_path,
        e2_manifest_path=e2_manifest_path,
        configs_dir=configs_dir,
    )
    if base.get("contractHashV1_2") != e3_manifest.get("contractHash"):
        raise ReadinessError("E3 manifest contract hash does not match v1.2")
    return {
        "verified": True,
        "contractHashV1_2": base["contractHashV1_2"],
        "predecessorContractHashV1_1": base["predecessorContractHashV1_1"],
        "predecessorContractHashV1": base["predecessorContractHashV1"],
        "e2CatalogHash": base["e2CatalogHash"],
        "e2ManifestHash": base["e2ManifestHash"],
        "e3AttemptsHash": attempts_hash,
        "e3ManifestHash": manifest_hash,
        "eligibleSkills": base["eligibleSkills"],
        "eligibleSkillCount": base["eligibleSkillCount"],
        "eligibleSkillCodesHash": base["eligibleSkillCodesHash"],
        "purityDenominatorRule": base["purityDenominatorRule"],
        "sourceReleaseHashes": base["sourceReleaseHashes"],
        "provenance": "external_real",
        "containsRawIdentifiers": False,
        "productionPromotionAllowed": False,
    }


def policy_ready_funnel(
    attempts: Sequence[ReadinessAttempt],
    eligible_skills: frozenset[str],
) -> tuple[list[ReadinessAttempt], dict[str, dict[str, int]]]:
    """Structural funnel A..H; returns (ready states, funnel counts)."""
    funnel: dict[str, dict[str, int]] = {
        "allReconstructed": {"attempts": len(attempts), "learners": _learners(attempts)},
        "inEligibleSkills": {"attempts": 0, "learners": 0},
        "scoreValidInEligible": {"attempts": 0, "learners": 0},
        "bktValidInEligible": {"attempts": 0, "learners": 0},
        "tierValidInEligible": {"attempts": 0, "learners": 0},
        "sharedPolicyReady": {"attempts": 0, "learners": 0},
        "readyUniqueSkills": 0,
    }
    ready: list[ReadinessAttempt] = []
    for attempt in attempts:
        if attempt.source_skill_code not in eligible_skills:
            continue
        funnel["inEligibleSkills"]["attempts"] += 1
        if not _valid_score(attempt):
            continue
        funnel["scoreValidInEligible"]["attempts"] += 1
        if not _valid_bkt(attempt):
            continue
        funnel["bktValidInEligible"]["attempts"] += 1
        if attempt.current_proxy_difficulty not in TIERS:
            continue
        funnel["tierValidInEligible"]["attempts"] += 1
        if attempt.chronology_ambiguous:
            continue
        if attempt.provenance != "external_real":
            continue
        ready.append(attempt)
    funnel["sharedPolicyReady"]["attempts"] = len(ready)
    funnel["sharedPolicyReady"]["learners"] = _learners(ready)
    funnel["readyUniqueSkills"] = len({a.source_skill_code for a in ready})
    for key in (
        "inEligibleSkills",
        "scoreValidInEligible",
        "bktValidInEligible",
        "tierValidInEligible",
    ):
        bucket = [a for a in attempts if a.source_skill_code in eligible_skills]
        if key == "scoreValidInEligible":
            bucket = [a for a in bucket if _valid_score(a)]
        elif key == "bktValidInEligible":
            bucket = [a for a in bucket if _valid_score(a) and _valid_bkt(a)]
        elif key == "tierValidInEligible":
            bucket = [
                a
                for a in bucket
                if _valid_score(a) and _valid_bkt(a) and a.current_proxy_difficulty in TIERS
            ]
        funnel[key]["learners"] = _learners(bucket)
    return ready, funnel


def tier_stats(ready: Sequence[ReadinessAttempt]) -> dict[str, dict[str, int]]:
    """Per-tier attempts / unique learners / unique exact skills."""
    stats: dict[str, dict[str, int]] = {}
    for tier in TIERS:
        rows = [a for a in ready if a.current_proxy_difficulty == tier]
        stats[tier] = {
            "attempts": len(rows),
            "learners": _learners(rows),
            "skills": len({a.source_skill_code for a in rows}),
        }
    return stats


def adjacent_tier_availability(
    ready: Sequence[ReadinessAttempt],
    eligible_skills: frozenset[str],
) -> dict[str, object]:
    """Analytical adjacent-tier availability from the frozen catalog (all 35
    gate-passing skills have full 3-tier catalogs, so availability is expected;
    any mismatch is a data-integrity blocker)."""
    full = 0
    missing: list[str] = []
    missing_learners: set[str] = set()
    for attempt in ready:
        if attempt.source_skill_code not in eligible_skills:
            missing.append(attempt.external_attempt_key)
            missing_learners.add(attempt.external_student_key)
            continue
        full += 1
    if missing:
        raise ReadinessError(
            "frozen catalog/E3 disagreement: policy-ready state without full "
            "adjacent-tier catalog availability"
        )
    return {
        "fullAdjacentTierAvailabilityAttempts": full,
        "missingAdjacentTierAttempts": len(missing),
        "missingAdjacentTierLearners": len(missing_learners),
        "missingAdjacentTierReasons": [],
    }


def boundary_opportunity_counts(
    ready: Sequence[ReadinessAttempt],
) -> dict[str, int]:
    """Structural movement opportunity counts (no policy direction)."""
    counts = {
        "statesAtLowerBoundary": 0,
        "statesAtUpperBoundary": 0,
        "statesWithUpTarget": 0,
        "statesWithDownTarget": 0,
        "statesWithHoldStructurallyPossible": len(ready),
    }
    for attempt in ready:
        if attempt.current_proxy_difficulty == "proxy_easy":
            counts["statesAtLowerBoundary"] += 1
            counts["statesWithUpTarget"] += 1
        elif attempt.current_proxy_difficulty == "proxy_moderate":
            counts["statesWithUpTarget"] += 1
            counts["statesWithDownTarget"] += 1
        elif attempt.current_proxy_difficulty == "proxy_hard":
            counts["statesAtUpperBoundary"] += 1
            counts["statesWithDownTarget"] += 1
    return counts


def bkt_readiness(
    ready: Sequence[ReadinessAttempt],
    *,
    move_up_minimum_evidence: int,
    hard_minimum_evidence: int,
) -> dict[str, object]:
    """BKT structural readiness (evidence/mastery distributions, guards)."""
    evidence = [a.bkt_evidence_count for a in ready]
    mastery = [a.bkt_mastery_probability for a in ready]
    bands = _bands(evidence)
    return {
        "bktValidAttempts": len(ready),
        "bktValidLearners": _learners(ready),
        "evidenceCountDistribution": _distribution([float(v) for v in evidence]),
        "masteryProbabilityDistribution": _distribution(mastery),
        "evidenceBands": bands,
        "evidenceGuardSatisfiableMoveUp": sum(
            1 for a in ready if a.bkt_evidence_count >= move_up_minimum_evidence
        ),
        "evidenceGuardSatisfiableHard": sum(
            1 for a in ready if a.bkt_evidence_count >= hard_minimum_evidence
        ),
        "moveUpMinimumEvidence": move_up_minimum_evidence,
        "hardMinimumEvidence": hard_minimum_evidence,
    }


def reversal_history_summary(
    ready: Sequence[ReadinessAttempt],
) -> dict[str, int]:
    """Observed reversal-history availability (never policy decisions)."""
    summary = {
        "previousTierAvailable": 0,
        "noPreviousTier": 0,
        "sameAsPrevious": 0,
        "oneLevelChange": 0,
        "nonAdjacentHistory": 0,
        "unresolvedOrInvalidHistory": 0,
    }
    for attempt in ready:
        previous = attempt.previous_observed_proxy_difficulty
        if previous is None:
            summary["noPreviousTier"] += 1
            continue
        summary["previousTierAvailable"] += 1
        current = attempt.current_proxy_difficulty
        if previous == current:
            summary["sameAsPrevious"] += 1
        elif abs(TIERS.index(previous) - TIERS.index(current)) == 1:
            summary["oneLevelChange"] += 1
        else:
            summary["nonAdjacentHistory"] += 1
    return summary


def fresh_problem_summary(ready: Sequence[ReadinessAttempt]) -> dict[str, object]:
    values = [a.fresh_problem_fraction for a in ready if a.fresh_problem_fraction is not None]
    null_count = sum(1 for a in ready if a.fresh_problem_fraction is None)
    learners = {
        a.external_student_key
        for a in ready
        if a.fresh_problem_fraction is not None
    }
    return {
        "freshProblemFractionAvailable": len(values),
        "freshProblemFractionNull": null_count,
        "freshProblemFractionDistribution": _distribution(values),
        "freshProblemLearnersRepresented": len(learners),
    }


def direct_next_audit(
    ready: Sequence[ReadinessAttempt],
    all_attempts: Sequence[ReadinessAttempt],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Direct next eligible chronological episode per learner + exact skill.

    Uses all reconstructed attempts as observed history (never skips an
    intervening episode).  Classifies: valid (with observed tier), no-next,
    chronology ambiguous, invalid outcome, identical complete problem-set
    repeat, next tier missing.  Outcome VALUES are never read.
    """
    grouped: dict[tuple[str, str], list[ReadinessAttempt]] = {}
    for attempt in all_attempts:
        grouped.setdefault(
            (attempt.external_student_key, attempt.source_skill_code), []
        ).append(attempt)
    for key in grouped:
        grouped[key].sort(
            key=lambda a: (a.source_timestamp, a.external_assignment_key, a.external_attempt_sequence)
        )

    counts = {
        "valid": 0,
        "none": 0,
        "invalidOutcome": 0,
        "repeat": 0,
        "nextTierMissing": 0,
        "chronologyAmbiguous": 0,
        "nonEligibleNextSkill": 0,
    }
    pairs: list[dict[str, object]] = []
    by_index: dict[str, int] = {}
    for key, ordered in grouped.items():
        for index, attempt in enumerate(ordered):
            by_index[attempt.external_attempt_key] = index

    for attempt in ready:
        ordered = grouped[(attempt.external_student_key, attempt.source_skill_code)]
        index = by_index[attempt.external_attempt_key]
        next_attempt = ordered[index + 1] if index + 1 < len(ordered) else None
        classification: str
        if next_attempt is None:
            classification = "none"
            counts["none"] += 1
        elif next_attempt.source_timestamp == attempt.source_timestamp:
            classification = "chronologyAmbiguous"
            counts["chronologyAmbiguous"] += 1
        elif not _valid_score(next_attempt) or not _valid_bkt(next_attempt):
            classification = "invalidOutcome"
            counts["invalidOutcome"] += 1
        elif next_attempt.source_skill_code != attempt.source_skill_code:
            classification = "nonEligibleNextSkill"
            counts["nonEligibleNextSkill"] += 1
        elif set(next_attempt.problem_keys) == set(attempt.problem_keys) and next_attempt.problem_keys:
            classification = "repeat"
            counts["repeat"] += 1
        elif next_attempt.current_proxy_difficulty not in TIERS:
            classification = "nextTierMissing"
            counts["nextTierMissing"] += 1
        else:
            classification = "valid"
            counts["valid"] += 1
        pairs.append(
            {
                "currentAttemptKey": attempt.external_attempt_key,
                "nextAttemptKey": next_attempt.external_attempt_key if next_attempt else None,
                "classification": classification,
                "currentTier": attempt.current_proxy_difficulty,
                "nextTier": (
                    next_attempt.current_proxy_difficulty if next_attempt else None
                ),
            }
        )
    return pairs, counts


def potential_tier_matches(
    pairs: Sequence[Mapping[str, object]],
    ready_by_key: Mapping[str, ReadinessAttempt],
) -> dict[str, dict[str, int]]:
    """Structural (not policy) tier-match classification for valid pairs."""
    match_counts = {
        "potential_up_tier_match": {"pairs": 0, "learners": 0, "skills": 0},
        "potential_hold_tier_match": {"pairs": 0, "learners": 0, "skills": 0},
        "potential_down_tier_match": {"pairs": 0, "learners": 0, "skills": 0},
        "non_adjacent_observed_transition": {"pairs": 0, "learners": 0, "skills": 0},
    }
    learners: dict[str, set[str]] = {key: set() for key in match_counts}
    skills: dict[str, set[str]] = {key: set() for key in match_counts}
    for pair in pairs:
        if pair["classification"] != "valid":
            continue
        current = pair["currentTier"]
        next_tier = pair["nextTier"]
        label = _tier_match_label(current, next_tier)
        match_counts[label]["pairs"] += 1
        attempt = ready_by_key[str(pair["currentAttemptKey"])]
        learners[label].add(attempt.external_student_key)
        skills[label].add(attempt.source_skill_code)
    for label in match_counts:
        match_counts[label]["learners"] = len(learners[label])
        match_counts[label]["skills"] = len(skills[label])
    return match_counts


def censoring_table(
    attempts: Sequence[ReadinessAttempt],
    ready: Sequence[ReadinessAttempt],
    ready_skill_set: frozenset[str],
    pairs: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Structural censoring burden; mutually exclusive vs overlapping split."""
    all_learners = _learners(attempts)
    ready_keys = {a.external_attempt_key for a in ready}
    mutually_exclusive = {
        "outside_full_skill_catalog": {
            "attempts": sum(1 for a in attempts if a.source_skill_code not in ready_skill_set),
            "learners": _learners(
                [a for a in attempts if a.source_skill_code not in ready_skill_set]
            ),
            "denominator": "all reconstructed attempts",
        },
        "no_current_proxy_tier": {
            "attempts": sum(
                1
                for a in attempts
                if a.source_skill_code in ready_skill_set
                and a.current_proxy_difficulty not in TIERS
            ),
            "learners": _learners(
                [
                    a
                    for a in attempts
                    if a.source_skill_code in ready_skill_set
                    and a.current_proxy_difficulty not in TIERS
                ]
            ),
            "denominator": "attempts in full eligible skills",
        },
        "mixed_proxy_difficulty": {
            "attempts": sum(
                1
                for a in attempts
                if a.source_skill_code in ready_skill_set
                and a.current_tier_censor_reason == "mixed_proxy_difficulty"
                and a.proxy_difficulty_purity != 0.0
            ),
            "learners": 0,
            "denominator": "subset of no_current_proxy_tier (overlap category)",
        },
        "zero_tier_coverage": {
            "attempts": sum(
                1
                for a in attempts
                if a.source_skill_code in ready_skill_set
                and a.proxy_difficulty_purity == 0.0
            ),
            "learners": 0,
            "denominator": "subset of no_current_proxy_tier (overlap category)",
        },
    }
    mutually_exclusive["mixed_proxy_difficulty"]["learners"] = _learners(
        [
            a
            for a in attempts
            if a.source_skill_code in ready_skill_set
            and a.current_tier_censor_reason == "mixed_proxy_difficulty"
            and a.proxy_difficulty_purity != 0.0
        ]
    )
    mutually_exclusive["zero_tier_coverage"]["learners"] = _learners(
        [
            a
            for a in attempts
            if a.source_skill_code in ready_skill_set and a.proxy_difficulty_purity == 0.0
        ]
    )

    pair_counts = Counter(pair["classification"] for pair in pairs)
    next_censors = {
        "chronology_ambiguous": {
            "attempts": pair_counts["chronologyAmbiguous"],
            "denominator": "shared policy-ready states",
        },
        "no_next_eligible_attempt": {
            "attempts": pair_counts["none"],
            "denominator": "shared policy-ready states",
        },
        "invalid_next_outcome": {
            "attempts": pair_counts["invalidOutcome"],
            "denominator": "shared policy-ready states",
        },
        "identical_problem_set_repeat": {
            "attempts": pair_counts["repeat"],
            "denominator": "shared policy-ready states",
        },
        "next_proxy_tier_missing": {
            "attempts": pair_counts["nextTierMissing"],
            "denominator": "shared policy-ready states",
        },
        "non_adjacent_observed_transition": {
            "attempts": sum(
                1
                for pair in pairs
                if pair["classification"] == "valid"
                and _tier_match_label(pair["currentTier"], pair["nextTier"])
                == "non_adjacent_observed_transition"
            ),
            "denominator": "valid direct-next pairs (overlap category)",
        },
    }
    return {
        "mutuallyExclusiveStateCensors": mutually_exclusive,
        "nextEpisodeCensors": next_censors,
        "allReconstructedLearners": all_learners,
    }


def build_e4_manifest(
    *,
    verification: Mapping[str, object],
    funnel: Mapping[str, object],
    tier_stats_: Mapping[str, object],
    adjacent: Mapping[str, object],
    boundary: Mapping[str, object],
    bkt: Mapping[str, object],
    reversal: Mapping[str, object],
    fresh: Mapping[str, object],
    next_counts: Mapping[str, object],
    match_counts: Mapping[str, object],
    censoring: Mapping[str, object],
    policy_replay_readiness: str,
    matched_outcome_readiness: str,
    overall_decision: str,
    decision_components: Sequence[str],
) -> dict[str, object]:
    """Deterministic E4 readiness manifest (no timestamps/local paths)."""
    return {
        "manifestSchemaVersion": E4_MANIFEST_VERSION,
        "contractVersion": "assistments-adaptive-contract-v1.2",
        "contractHash": verification["contractHashV1_2"],
        "predecessorContractHashV1_1": verification["predecessorContractHashV1_1"],
        "predecessorContractHashV1": verification["predecessorContractHashV1"],
        "difficultyCatalogVersion": "assistments_problem_difficulty_proxy_v1",
        "difficultyCatalogHash": verification["e2CatalogHash"],
        "e3AttemptVersion": "assistments-adaptive-attempts-v1",
        "e3AttemptHash": verification["e3AttemptsHash"],
        "datasetReleaseId": "assistments-edm-cup-2023-release-v1",
        "sourceReleaseHashes": verification["sourceReleaseHashes"],
        "provenance": "external_real",
        "primaryCohort": "exact Grade 6 Mathematics",
        "funnel": dict(funnel),
        "tierStats": dict(tier_stats_),
        "adjacentTierAvailability": dict(adjacent),
        "boundaryOpportunityCounts": dict(boundary),
        "bktReadiness": dict(bkt),
        "reversalHistory": dict(reversal),
        "freshProblem": dict(fresh),
        "directNextEpisodeCounts": dict(next_counts),
        "potentialTierMatchCounts": dict(match_counts),
        "censoringCounts": dict(censoring),
        "policyReplayReadiness": policy_replay_readiness,
        "matchedOutcomeReadiness": matched_outcome_readiness,
        "overallDecision": overall_decision,
        "decisionComponents": list(decision_components),
        "containsRawIdentifiers": False,
        "productionPromotionAllowed": False,
    }


def write_manifest(manifest: Mapping[str, object], path: str | Path) -> Path:
    destination = Path(path)
    destination.write_text(
        json.dumps(dict(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return destination


def _valid_score(attempt: ReadinessAttempt) -> bool:
    return (
        attempt.total_questions > 0
        and 0 <= attempt.correct_count <= attempt.total_questions
        and attempt.correct_rate is not None
        and 0.0 <= attempt.correct_rate <= 1.0
    )


def _valid_bkt(attempt: ReadinessAttempt) -> bool:
    return (
        attempt.bkt_version == "bkt-v1"
        and attempt.bkt_evidence_count >= 1
        and 0.0 <= attempt.bkt_mastery_probability <= 1.0
    )


def _tier_match_label(current: object, next_tier: object) -> str:
    """Structural match label for a valid current -> next observed tier pair."""
    if current == "proxy_easy":
        return (
            "potential_hold_tier_match"
            if next_tier == "proxy_easy"
            else "potential_up_tier_match"
            if next_tier == "proxy_moderate"
            else "non_adjacent_observed_transition"
        )
    if current == "proxy_moderate":
        return (
            "potential_down_tier_match"
            if next_tier == "proxy_easy"
            else "potential_hold_tier_match"
            if next_tier == "proxy_moderate"
            else "potential_up_tier_match"
        )
    if current == "proxy_hard":
        return (
            "potential_down_tier_match"
            if next_tier == "proxy_moderate"
            else "potential_hold_tier_match"
            if next_tier == "proxy_hard"
            else "non_adjacent_observed_transition"
        )
    raise ReadinessError("tier-match classification requires a valid current tier")


def _learners(attempts: Sequence[ReadinessAttempt]) -> int:
    return len({a.external_student_key for a in attempts})


def _distribution(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "q25": None, "median": None, "q75": None, "max": None}
    ordered = sorted(values)
    if len(ordered) == 1:
        value = ordered[0]
        return {"min": value, "q25": value, "median": value, "q75": value, "max": value}
    quartiles = quantiles(ordered, n=4)
    return {
        "min": ordered[0],
        "q25": quartiles[0],
        "median": median(ordered),
        "q75": quartiles[2],
        "max": ordered[-1],
    }


def _bands(values: list[int]) -> dict[str, int]:
    bands = {"1-4": 0, "5-9": 0, "10-19": 0, "20+": 0}
    for value in values:
        if value <= 4:
            bands["1-4"] += 1
        elif value <= 9:
            bands["5-9"] += 1
        elif value <= 19:
            bands["10-19"] += 1
        else:
            bands["20+"] += 1
    return bands


def _file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
