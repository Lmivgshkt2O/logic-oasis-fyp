"""AQC-E3 protected 2022-2023 exact-skill adaptive attempt reconstruction.

This module reconstructs policy-ready historical states from the frozen
ASSISTments evaluation-period lineage under assistments-adaptive-contract-v1.2,
reusing the validated U7-v2 exact-skill episode reconstruction and the frozen
U7 BKT replay.  The semantic unit is one externalStudentKey + one completed
externalAssignmentKey + one exact non-null sourceSkillCode; skills never mix.

No policy selector is imported or called.  Attempt proxy difficulty uses ONLY
the frozen E2 problem-difficulty catalog; E3 never recalibrates or re-tiers
problems.  The v1.2 purity rule is: proxyDifficultyPurity =
dominantTierCount / validProblemCount over ALL valid graded problems, with
untiered problems remaining in the denominator and contributing to no tier
numerator; dominant-tier ties fail closed (no arbitrary selection).
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from logic_oasis_ai.bkt import BKT_MODEL_VERSION

from ..reconstruct_attempts import read_action_rows
from ..bkt_external import (
    BktStateAt,
    build_graded_observations,
    build_mastery_at_episodes,
)
from .external_policy_contract import (
    EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION,
    load_external_adaptive_contract,
    verify_frozen_policy_hashes,
    verify_shared_aqc_constants,
)
from .schemas import (
    ATTEMPT_PURITY_THRESHOLD,
    EXTERNAL_PROVENANCE,
    ExternalAdaptiveAttemptV1,
    ProxyDifficulty,
    problem_set_fingerprint,
)


ATTEMPT_RECONSTRUCTION_VERSION = "assistments-adaptive-attempts-v1"
E2_MANIFEST_HASH = "18502d7354c30a24849e659d7b8d656587eb3b48cefd495315f90b66436f3d17"
E2_CATALOG_HASH = "fe4cb2585bae9a8f15ee2802c23dea8270252384ab7e9c5a410d1ff934bd58e9"

ATTEMPT_FIELDS = (
    "datasetReleaseId",
    "externalAttemptKey",
    "externalStudentKey",
    "externalAssignmentKey",
    "sourceSkillCode",
    "sourceTimestamp",
    "externalAttemptSequence",
    "problemKeys",
    "totalQuestions",
    "correctCount",
    "correctRate",
    "bktMasteryProbability",
    "bktEvidenceCount",
    "bktVersion",
    "currentProxyDifficulty",
    "proxyDifficultyPurity",
    "externalProblemSetFingerprint",
    "previousObservedProxyDifficulty",
    "freshProblemFraction",
    "skillProxyStatus",
    "currentTierCensorReason",
    "coldHistory",
    "chronologyAmbiguous",
    "provenance",
)


class ReconstructionError(ValueError):
    """Raised when E3 reconstruction cannot proceed safely."""


@dataclass(frozen=True)
class AdaptiveAttemptRecord:
    """One reconstructed external adaptive attempt (E1-compatible core + audit)."""

    attempt: ExternalAdaptiveAttemptV1
    skill_proxy_status: str
    current_tier_censor_reason: str | None
    cold_history: bool
    chronology_ambiguous: bool

    def to_csv_row(self) -> dict[str, str]:
        a = self.attempt
        return {
            "datasetReleaseId": a.dataset_release_id,
            "externalAttemptKey": a.external_attempt_key,
            "externalStudentKey": a.external_student_key,
            "externalAssignmentKey": a.external_assignment_key,
            "sourceSkillCode": a.source_skill_code,
            "sourceTimestamp": a.source_timestamp.isoformat(),
            "externalAttemptSequence": str(a.external_attempt_sequence),
            "problemKeys": "|".join(a.problem_keys),
            "totalQuestions": str(a.total_questions),
            "correctCount": str(a.correct_count),
            "correctRate": f"{a.correct_rate:.8f}",
            "bktMasteryProbability": f"{a.bkt_mastery_probability:.8f}",
            "bktEvidenceCount": str(a.bkt_evidence_count),
            "bktVersion": a.bkt_version,
            "currentProxyDifficulty": a.current_proxy_difficulty.value if a.current_proxy_difficulty else "",
            "proxyDifficultyPurity": (
                f"{a.proxy_difficulty_purity:.8f}" if a.proxy_difficulty_purity is not None else ""
            ),
            "externalProblemSetFingerprint": a.external_problem_set_fingerprint,
            "previousObservedProxyDifficulty": (
                a.previous_observed_proxy_difficulty.value
                if a.previous_observed_proxy_difficulty
                else ""
            ),
            "freshProblemFraction": (
                f"{a.fresh_problem_fraction:.8f}" if a.fresh_problem_fraction is not None else ""
            ),
            "skillProxyStatus": self.skill_proxy_status,
            "currentTierCensorReason": self.current_tier_censor_reason or "",
            "coldHistory": str(self.cold_history).lower(),
            "chronologyAmbiguous": str(self.chronology_ambiguous).lower(),
            "provenance": a.provenance,
        }


def verify_stage_b_frozen(
    *,
    contract_path_v1_2: str | Path,
    contract_path_v1_1: str | Path,
    contract_path_v1: str | Path,
    e2_catalog_path: str | Path,
    e2_manifest_path: str | Path,
    configs_dir: str | Path,
    expected_e2_manifest_hash: str = E2_MANIFEST_HASH,
    expected_e2_catalog_hash: str = E2_CATALOG_HASH,
) -> dict[str, object]:
    """Fail-closed verification of every frozen E1/E2 artifact E3 depends on."""
    v12 = load_external_adaptive_contract(
        contract_path_v1_2, version=EXTERNAL_ADAPTIVE_CONTRACT_V1_2_VERSION
    )
    from .external_policy_contract import EXTERNAL_ADAPTIVE_CONTRACT_V1_1_VERSION

    v11 = load_external_adaptive_contract(
        contract_path_v1_1, version=EXTERNAL_ADAPTIVE_CONTRACT_V1_1_VERSION
    )
    v1 = load_external_adaptive_contract(contract_path_v1)
    verify_frozen_policy_hashes(v12, configs_dir)
    verify_shared_aqc_constants(v12)

    catalog = Path(e2_catalog_path)
    manifest = Path(e2_manifest_path)
    catalog_hash = file_sha256(catalog)
    manifest_hash = file_sha256(manifest)
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(manifest_data, dict):
        raise ReconstructionError("E2 manifest must be a JSON object")

    if v12.predecessor_contract_version != v11.contract_version:
        raise ReconstructionError("v1.2 predecessor is not v1.1")
    if v12.predecessor_contract_sha256 != v11.contract_sha256:
        raise ReconstructionError("v1.1 predecessor hash is not preserved by v1.2")
    if v11.predecessor_contract_sha256 != v1.contract_sha256:
        raise ReconstructionError("v1 predecessor hash is not preserved by v1.1")
    if manifest_data.get("contractHash") != v11.contract_sha256:
        raise ReconstructionError("E2 manifest contract hash is not the frozen v1.1 hash")
    if v12.amendment_reason != "attempt_proxy_difficulty_purity_denominator_clarification":
        raise ReconstructionError("v1.2 amendment reason is not frozen")
    if v12.purity_denominator_rule is None:
        raise ReconstructionError("v1.2 purity denominator rule is missing")
    if catalog_hash != expected_e2_catalog_hash:
        raise ReconstructionError("E2 catalog hash changed since the E2 freeze")
    if manifest_hash != expected_e2_manifest_hash:
        raise ReconstructionError("E2 manifest hash changed since the E2 freeze")
    if v12.provenance != EXTERNAL_PROVENANCE:
        raise ReconstructionError("provenance is not external_real")
    import yaml

    raw_v12 = yaml.safe_load(Path(contract_path_v1_2).read_text(encoding="utf-8"))
    cohort = raw_v12["dataset"]["primaryCohort"]
    if cohort.get("sourceGrade") != "6" or cohort.get("sourceSubject") != "Mathematics":
        raise ReconstructionError("primary cohort is not exact Grade 6 Mathematics")
    if cohort.get("gradeSixAcceleratedMerged") is not False:
        raise ReconstructionError("Grade 6 Accelerated must stay separate")
    if not v12.windows_are_disjoint:
        raise ReconstructionError("calibration/evaluation windows are not disjoint")
    if not manifest_data.get("evaluationLearnersExcludedFromCalibration"):
        raise ReconstructionError("evaluation learners were not excluded from calibration")
    possible = manifest_data.get("possiblePre2022GradeSixLearners")
    final_learners = manifest_data.get("finalCalibrationLearnerCount")
    excluded = manifest_data.get("calibrationEvaluationLearnerOverlapCount")
    if not isinstance(possible, int) or not isinstance(final_learners, int) or not isinstance(excluded, int):
        raise ReconstructionError("E2 learner-disjointness record is incomplete")
    if possible - excluded != final_learners:
        raise ReconstructionError(
            "E2 learner-disjointness record is inconsistent (final != possible - excluded)"
        )
    if (
        manifest_data.get("minimumProblemsPerSkill") != 9
        or manifest_data.get("minimumProblemsPerTier") != 3
    ):
        raise ReconstructionError("skill catalog gate changed since the E2 freeze")
    eligible_skills, tier_records = derive_gate_eligible_skills(catalog)
    if len(eligible_skills) != manifest_data.get("skillCounts", {}).get("skillsFullThreeTierEligible"):
        raise ReconstructionError("derived eligible skill count does not match the E2 manifest")
    for guard in ("Logic Oasis bankId", "finalizationStatus", "validationStatus"):
        if guard not in v12.never_fabricate_native_fields:
            raise ReconstructionError(f"native-field fabrication guard is missing: {guard}")
    for native in ("bankId", "finalizationStatus", "validationStatus"):
        if native in str(manifest_data) or native in ATTEMPT_FIELDS:
            raise ReconstructionError("native fields must never be fabricated")
    source_release_hashes = manifest_data.get("sourceReleaseHashes")
    if not isinstance(source_release_hashes, dict):
        raise ReconstructionError("E2 manifest source release hashes are missing")

    return {
        "verified": True,
        "contractVersionV1_2": v12.contract_version,
        "contractHashV1_2": v12.contract_sha256,
        "predecessorContractVersionV1_1": v11.contract_version,
        "predecessorContractHashV1_1": v11.contract_sha256,
        "predecessorContractVersionV1": v1.contract_version,
        "predecessorContractHashV1": v1.contract_sha256,
        "e2CatalogHash": catalog_hash,
        "e2ManifestHash": manifest_hash,
        "provenance": EXTERNAL_PROVENANCE,
        "calibrationWindow": [v12.calibration_window[0].isoformat(), v12.calibration_window[1].isoformat()],
        "evaluationWindow": [v12.evaluation_window[0].isoformat(), v12.evaluation_window[1].isoformat()],
        "eligibleSkillCount": len(eligible_skills),
        "eligibleSkillCodesHash": _canonical_sha256(sorted(eligible_skills)),
        "eligibleSkills": sorted(eligible_skills),
        "derivedTierRecords": tier_records,
        "purityDenominatorRule": dict(v12.purity_denominator_rule),
        "sourceReleaseHashes": dict(source_release_hashes),
    }


def load_frozen_problem_tiers(catalog_path: str | Path) -> dict[str, str]:
    """problem key -> frozen proxy tier from the E2 catalog (tiered rows only)."""
    tiers: dict[str, str] = {}
    with Path(catalog_path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            tier = (row.get("proxyDifficulty") or "").strip()
            if tier:
                tiers[row["externalProblemKey"]] = tier
    return tiers


def derive_gate_eligible_skills(
    catalog_path: str | Path,
    *,
    minimum_problems: int = 9,
    minimum_per_tier: int = 3,
) -> tuple[frozenset[str], dict[str, dict[str, int]]]:
    """Derive the full-gate eligible exact skills from the frozen catalog."""
    per_skill: dict[str, Counter[str]] = {}
    with Path(catalog_path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("calibrationStatus") != "calibrated":
                continue
            tier = (row.get("proxyDifficulty") or "").strip()
            if not tier:
                continue
            per_skill.setdefault(row["sourceSkillCode"], Counter())[tier] += 1
    eligible: set[str] = set()
    for skill, counts in per_skill.items():
        if (
            sum(counts.values()) >= minimum_problems
            and all(counts[tier] >= minimum_per_tier for tier in ("proxy_easy", "proxy_moderate", "proxy_hard"))
        ):
            eligible.add(skill)
    return frozenset(eligible), {skill: dict(counts) for skill, counts in sorted(per_skill.items())}


def attempt_purity(tiers: Sequence[str | None]) -> tuple[str | None, float]:
    """v1.2 attempt purity: dominant_tier_count / valid_problem_count.

    Untiered problems remain in the valid-problem denominator and never enter
    any tier count.  A non-unique dominant tier fails closed (no arbitrary
    selection).  The frozen 2/3 threshold is inclusive.
    """
    valid_count = len(tiers)
    if valid_count < 1:
        raise ReconstructionError("an attempt requires at least one valid problem")
    counts = Counter(tier for tier in tiers if tier is not None)
    if not counts:
        return None, 0.0
    dominant_count = max(counts.values())
    dominant_tiers = [tier for tier, count in counts.items() if count == dominant_count]
    fraction = dominant_count / valid_count
    if len(dominant_tiers) != 1:
        return None, fraction
    if fraction >= float(ATTEMPT_PURITY_THRESHOLD):
        return dominant_tiers[0], fraction
    return None, fraction


def build_attempt_records(
    episodes: Sequence[Mapping[str, object]],
    *,
    tiers: Mapping[str, str],
    eligible_skills: frozenset[str],
    bkt_states: Mapping[str, BktStateAt],
    release_id: str,
) -> tuple[list[AdaptiveAttemptRecord], Counter[str]]:
    """Reconstruct attempts from U7-v2 outcome-valid exact-skill episodes."""
    records: list[AdaptiveAttemptRecord] = []
    summary: Counter[str] = Counter()
    grouped: dict[tuple[str, str], list[Mapping[str, object]]] = {}
    for episode in episodes:
        learner = str(episode["externalStudentKey"])
        skill = str(episode["externalSkillCode"])
        grouped.setdefault((learner, skill), []).append(episode)

    prior_exposure: dict[tuple[str, str], set[str]] = {}
    previous_tier_by_key: dict[tuple[str, str], str] = {}
    for (learner, skill) in sorted(grouped):
        ordered = sorted(
            grouped[(learner, skill)],
            key=lambda episode: (
                _parse_timestamp(episode.get("episodeStartedAt")),
                str(episode.get("externalAssignmentKey")),
            ),
        )
        seen_starts: dict[tuple[str, str], str | None] = {}
        for index, episode in enumerate(ordered, start=1):
            started_at = _parse_timestamp(episode.get("episodeStartedAt"))
            assignment = str(episode.get("externalAssignmentKey"))
            key = (learner, skill)
            if started_at in seen_starts:
                chronology_ambiguous = True
                summary["chronology_ambiguous_attempts"] += 1
            else:
                chronology_ambiguous = False
                seen_starts[started_at] = assignment
            problem_keys = _parse_problem_keys(episode.get("gradedProblemKeys"))
            episode_tiers = [tiers.get(key, None) for key in problem_keys]
            current_tier, purity = attempt_purity(episode_tiers)
            previous_observed = previous_tier_by_key.get(key)
            cold_history = previous_observed is None
            if current_tier is not None:
                previous_tier_by_key[key] = current_tier
            prior = prior_exposure.get(key, set())
            fresh = (
                sum(1 for problem in problem_keys if problem not in prior) / len(problem_keys)
                if problem_keys
                else None
            )
            prior_exposure[key] = prior | set(problem_keys)

            bkt = bkt_states.get(str(episode.get("externalEpisodeId")))
            if bkt is None:
                raise ReconstructionError(
                    f"missing BKT state for episode {episode.get('externalEpisodeId')}"
                )
            graded_count = int(episode.get("gradedProblemCount") or 0)
            correct_count = int(episode.get("correctFirstResponseCount") or 0)
            if graded_count < 1:
                raise ReconstructionError("attempt scoring requires valid graded problems")
            correct_rate = correct_count / graded_count
            skill_status = "eligible" if skill in eligible_skills else "not_eligible"
            summary[f"attempts_skill_{skill_status}"] += 1
            summary[f"attempts_tiered_problems_{len([t for t in episode_tiers if t])}"] += 1
            summary["attempts_total"] += 1

            record = AdaptiveAttemptRecord(
                attempt=ExternalAdaptiveAttemptV1(
                    dataset_release_id=release_id,
                    external_attempt_key=str(episode.get("externalEpisodeId")),
                    external_student_key=learner,
                    external_assignment_key=assignment,
                    source_skill_code=skill,
                    source_timestamp=started_at,
                    external_attempt_sequence=index,
                    problem_keys=tuple(problem_keys),
                    total_questions=graded_count,
                    correct_count=correct_count,
                    correct_rate=correct_rate,
                    bkt_mastery_probability=bkt.mastery_probability,
                    bkt_evidence_count=bkt.evidence_count,
                    bkt_version=BKT_MODEL_VERSION,
                    current_proxy_difficulty=(
                        ProxyDifficulty(current_tier) if current_tier is not None else None
                    ),
                    proxy_difficulty_purity=purity,
                    external_problem_set_fingerprint=problem_set_fingerprint(skill, tuple(problem_keys)),
                    previous_observed_proxy_difficulty=(
                        ProxyDifficulty(previous_observed) if previous_observed is not None else None
                    ),
                    fresh_problem_fraction=fresh,
                    provenance=EXTERNAL_PROVENANCE,
                ),
                skill_proxy_status=skill_status,
                current_tier_censor_reason=(
                    None if current_tier is not None else "mixed_proxy_difficulty"
                ),
                cold_history=cold_history,
                chronology_ambiguous=chronology_ambiguous,
            )
            summary[f"attempts_current_tier_{current_tier or 'null'}"] += 1
            summary["attempts_with_previous_observed_tier" if previous_observed else "attempts_cold_history"] += 1
            records.append(record)
    return records, summary


def run_bkt_states(
    action_rows_path: str | Path,
    episodes: Sequence[Mapping[str, object]],
) -> dict[str, BktStateAt]:
    """Replay frozen U7 BKT per (learner, skill) at each episode boundary."""
    frame = read_action_rows(action_rows_path)
    observations, _summary = build_graded_observations(frame.to_dict("records"))
    labelled = [
        {
            "currentEpisodeId": episode["externalEpisodeId"],
            "externalStudentKey": episode["externalStudentKey"],
            "externalAssignmentKey": episode["externalAssignmentKey"],
            "externalSkillCode": episode["externalSkillCode"],
            "currentEpisodeStartedAt": _parse_timestamp(episode.get("episodeStartedAt")),
        }
        for episode in episodes
    ]
    return build_mastery_at_episodes(observations, labelled)


def write_attempts_csv(
    records: Iterable[AdaptiveAttemptRecord],
    path: str | Path,
) -> Path:
    destination = Path(path)
    rows = sorted(
        records,
        key=lambda record: (
            record.attempt.external_student_key,
            record.attempt.source_skill_code,
            record.attempt.external_attempt_sequence,
        ),
    )
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ATTEMPT_FIELDS)
        writer.writeheader()
        for record in rows:
            writer.writerow(record.to_csv_row())
    return destination


def build_e3_manifest(
    *,
    contract_version: str,
    contract_hash: str,
    predecessor_contract_version: str,
    predecessor_contract_hash: str,
    amendment_reason: str,
    purity_denominator_rule: Mapping[str, object],
    difficulty_catalog_version: str,
    difficulty_catalog_hash: str,
    dataset_release_id: str,
    source_release_hashes: Mapping[str, str],
    evaluation_start,
    evaluation_end,
    eligible_skill_count: int,
    eligible_skill_codes_hash: str,
    bkt_version: str,
    attempt_purity_threshold: Fraction,
    problem_set_fingerprint_version: str,
    fresh_problem_rule: str,
    chronology_rule: str,
    counts: Mapping[str, int],
    tier_counts: Mapping[str, int],
    attempts_sha256: str,
) -> dict[str, object]:
    """Deterministic E3 manifest (no timestamps; rerun reproduces the hash)."""
    return {
        "manifestSchemaVersion": "assistments-e3-attempt-manifest-v1",
        "contractVersion": contract_version,
        "contractHash": contract_hash,
        "predecessorContractVersion": predecessor_contract_version,
        "predecessorContractHash": predecessor_contract_hash,
        "amendmentReason": amendment_reason,
        "purityDenominatorRule": dict(purity_denominator_rule),
        "difficultyCatalogVersion": difficulty_catalog_version,
        "difficultyCatalogHash": difficulty_catalog_hash,
        "datasetReleaseId": dataset_release_id,
        "sourceReleaseHashes": dict(sorted(source_release_hashes.items())),
        "provenance": EXTERNAL_PROVENANCE,
        "evaluationStart": evaluation_start.isoformat(),
        "evaluationEnd": evaluation_end.isoformat(),
        "primaryCohort": "exact Grade 6 Mathematics",
        "eligibleSkillCount": eligible_skill_count,
        "eligibleSkillCodesHash": eligible_skill_codes_hash,
        "bktVersion": bkt_version,
        "attemptReconstructionVersion": ATTEMPT_RECONSTRUCTION_VERSION,
        "attemptPurityThreshold": (
            f"{attempt_purity_threshold.numerator}/{attempt_purity_threshold.denominator}"
        ),
        "problemSetFingerprintVersion": problem_set_fingerprint_version,
        "freshProblemRule": fresh_problem_rule,
        "chronologyRule": chronology_rule,
        "counts": dict(sorted(counts.items())),
        "tierCounts": dict(sorted(tier_counts.items())),
        "attemptsSha256": attempts_sha256,
        "containsRawIdentifiers": False,
        "productionPromotionAllowed": False,
    }


def write_manifest(manifest: Mapping[str, object], path: str | Path) -> Path:
    destination = Path(path)
    destination.write_text(
        json.dumps(dict(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return destination


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_problem_keys(value: object) -> list[str]:
    if value is None:
        return []
    return [item for item in str(value).split("|") if item]


def _parse_timestamp(value: object):
    if value is None or value == "":
        raise ReconstructionError("attempt reconstruction requires episodeStartedAt")
    from datetime import datetime

    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise ReconstructionError("unparseable episodeStartedAt") from error


def _canonical_sha256(items: Iterable[str]) -> str:
    payload = json.dumps(sorted(items), separators=(",", ":")).encode("utf-8")
    return sha256(payload).hexdigest()
