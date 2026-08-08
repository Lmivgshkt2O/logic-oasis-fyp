"""AQC-E2 within-skill proxy tier assignment and skill catalog gate.

The frozen E1 contract defines ordering (p_correct descending, then
externalProblemKey ascending) and the three-tertile semantics, but it does NOT
completely define how tertile boundaries are formed when a skill's calibrated
problem count is not divisible by three.  Per the E2 governance rule, real-data
tier assignment must therefore NOT run until a separately versioned pre-policy
amendment freezes the boundary rule.

This module implements a documented deterministic boundary convention
(``floor``: group sizes ``n // 3``, ``n // 3``, remainder to the lowest tier)
so the algorithm is ready for the amended contract.  The E2 run does not apply
it to real data; tests cover counts divisible by three (where every stable-rank
convention agrees) and the catalog gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


TIER_EASY = "proxy_easy"
TIER_MODERATE = "proxy_moderate"
TIER_HARD = "proxy_hard"
PROXY_TIER_ORDER = (TIER_EASY, TIER_MODERATE, TIER_HARD)

SKILL_CATALOG_MINIMUM_PROBLEMS = 9
SKILL_CATALOG_MINIMUM_PER_TIER = 3


class ProxyTierError(ValueError):
    """Raised when tier assignment or the catalog gate is misused."""


@dataclass(frozen=True)
class CalibratedProblem:
    """A calibrated problem eligible for within-skill tier assignment."""

    external_problem_key: str
    source_skill_code: str
    p_correct: float


@dataclass(frozen=True)
class SkillCatalogResult:
    source_skill_code: str
    calibrated_problem_count: int
    tier_counts: Mapping[str, int]
    skill_proxy_status: str


def _tertile_boundaries(problem_count: int) -> tuple[int, int]:
    """Rank boundaries for the documented ``floor`` convention.

    Returns (easy_end_rank, moderate_end_rank) as 1-based inclusive ranks.
    For counts divisible by three every stable-rank convention agrees, which is
    what the frozen E1 tests exercise.  The non-divisible split is a proposal
    pending the versioned amendment described in the module docstring.
    """
    if problem_count < 3:
        raise ProxyTierError("at least three calibrated problems are required for tiers")
    easy_end = problem_count // 3
    moderate_end = (2 * problem_count) // 3
    if easy_end < 1 or moderate_end <= easy_end or moderate_end >= problem_count:
        raise ProxyTierError("tertile boundaries are invalid for the problem count")
    return easy_end, moderate_end


def assign_within_skill_tiers(
    problems: Iterable[CalibratedProblem],
    *,
    boundary_rule: str = "floor",
) -> dict[str, str]:
    """Assign proxy tiers within each exact sourceSkillCode (never pooled).

    Ordering is frozen: p_correct descending, then externalProblemKey
    ascending.  Only the documented ``floor`` boundary convention is supported;
    it must not be applied to real data until the amendment freezes the rule.
    """
    if boundary_rule != "floor":
        raise ProxyTierError(f"unsupported boundary rule: {boundary_rule}")
    by_skill: dict[str, list[CalibratedProblem]] = {}
    for problem in problems:
        by_skill.setdefault(problem.source_skill_code, []).append(problem)
    assigned: dict[str, str] = {}
    for skill, skill_problems in sorted(by_skill.items()):
        ordered = sorted(
            skill_problems,
            key=lambda problem: (-problem.p_correct, problem.external_problem_key),
        )
        easy_end, moderate_end = _tertile_boundaries(len(ordered))
        for rank, problem in enumerate(ordered, start=1):
            tier = (
                TIER_EASY
                if rank <= easy_end
                else TIER_MODERATE
                if rank <= moderate_end
                else TIER_HARD
            )
            assigned[problem.external_problem_key] = tier
    return assigned


def evaluate_skill_catalog(
    source_skill_code: str,
    tier_counts: Mapping[str, int],
    *,
    minimum_problems: int = SKILL_CATALOG_MINIMUM_PROBLEMS,
    minimum_per_tier: int = SKILL_CATALOG_MINIMUM_PER_TIER,
) -> SkillCatalogResult:
    """Apply the frozen skill catalog gate (9 calibrated / 3+3+3 tiers)."""
    total = sum(tier_counts.get(tier, 0) for tier in PROXY_TIER_ORDER)
    eligible = (
        total >= minimum_problems
        and all(tier_counts.get(tier, 0) >= minimum_per_tier for tier in PROXY_TIER_ORDER)
    )
    return SkillCatalogResult(
        source_skill_code=source_skill_code,
        calibrated_problem_count=total,
        tier_counts=dict(tier_counts),
        skill_proxy_status=(
            "sufficient_skill_catalog" if eligible else "insufficient_skill_catalog"
        ),
    )


def summarize_skill_catalogs(
    results: Iterable[SkillCatalogResult],
) -> dict[str, int]:
    """Aggregate skill-catalog counts for the E2 manifest/report."""
    summary = {
        "skillsWithCalibratedProblems": 0,
        "skillsFullThreeTierEligible": 0,
        "skillsInsufficientCatalog": 0,
    }
    for result in results:
        summary["skillsWithCalibratedProblems"] += 1
        if result.skill_proxy_status == "sufficient_skill_catalog":
            summary["skillsFullThreeTierEligible"] += 1
        else:
            summary["skillsInsufficientCatalog"] += 1
    return summary


def tier_counts_by_tier(
    assigned: Mapping[str, str],
) -> dict[str, int]:
    """Count assigned tiers (proxy_easy/proxy_moderate/proxy_hard)."""
    counts = {tier: 0 for tier in PROXY_TIER_ORDER}
    for tier in assigned.values():
        if tier not in counts:
            raise ProxyTierError(f"undeclared proxy tier: {tier}")
        counts[tier] += 1
    return counts
