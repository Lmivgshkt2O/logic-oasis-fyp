"""Deterministic markdown rendering of the AQC-3 evidence package.

The rendered report follows ``ai_pipeline/reports/policy_comparison_template.md``
and enforces the evidence claim boundary: it never states that one policy is
better than another and always distinguishes offline observational replay from
a randomized pilot.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Mapping

from .manifest import EvaluationRunManifest
from .metrics import PolicyComparisonMetrics


class ReportingError(ValueError):
    """Raised when the evidence report cannot be rendered safely."""


def render_evidence_markdown(
    evidence: Mapping[str, object],
    run_manifest: EvaluationRunManifest,
    metrics: PolicyComparisonMetrics,
) -> str:
    """Render the complete supervisor-readable evidence report."""
    lines: list[str] = []
    lines.append("# Logic Oasis Policy Comparison - Stage B Evidence Package")
    lines.append("")
    lines.append(
        f"**Claim level:** `{evidence['claimLevel']}`. "
        f"{evidence['claimRationale']}"
    )
    lines.append("")
    lines.append(
        "This evidence package is **observational and descriptive**. It does not "
        "claim that any bank-selection policy is better than another and it does "
        "not claim that offline replay proves a learning effect."
    )
    lines.append("")
    lines.append("## Frozen run manifest")
    lines.append("")
    lines.append("| Setting | Value |")
    lines.append("| --- | --- |")
    manifest_rows = (
        ("Dataset version", run_manifest.dataset_version),
        ("Dataset SHA-256", run_manifest.dataset_sha256),
        ("Provenance", run_manifest.provenance),
        ("Outcome window", (
            f"{run_manifest.outcome_window.max_later_attempts} later attempts / "
            f"{run_manifest.outcome_window.max_calendar_duration_days} days"
        )),
        ("Random seed", str(run_manifest.random_seed)),
        ("Manifest SHA-256", run_manifest.manifest_sha256()),
    )
    for label, value in manifest_rows:
        lines.append(f"| {label} | `{value}` |")
    lines.append("")
    totals = evidence["totals"]
    lines.append("## Decision and censoring totals")
    lines.append("")
    lines.append(
        f"- Decisions: {totals['decisionCount']}; observed assignment-matched "
        f"outcomes: {totals['observedCount']}; censored outcomes: "
        f"{totals['censoredCount']}."
    )
    lines.append("")
    lines.append("## Promotion-safety forest plot data")
    lines.append("")
    lines.append(
        "Descriptive false-promotion burden difference (P3a minus comparator) "
        "over observed assignment-matched outcomes with student-clustered "
        "bootstrap intervals. The sample denominator is the observed-outcome "
        "count for the primary arm."
    )
    lines.append("")
    lines.append(
        "| Comparator | Risk difference | 95% CI | P3a burden | Comparator burden | "
        "False-demotion delta (descriptive) | Denominator |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for row in evidence["forestPlot"]:
        lines.append(
            f"| {row['comparator']} | {row['riskDifference']:.8f} | "
            f"{row['riskDifferenceCi'][0]:.8f} .. {row['riskDifferenceCi'][1]:.8f} | "
            f"{row['falsePromotionBurdenPrimary']:.8f} | "
            f"{row['falsePromotionBurdenComparator']:.8f} | "
            f"{row['falseDemotionDelta']:.8f} | {row['sampleDenominator']} |"
        )
    lines.append("")
    lines.append("## Safety-benefit quadrant data")
    lines.append("")
    lines.append("| Arm | False-promotion burden | False demotion / unnecessary hold (descriptive) |")
    lines.append("| --- | --- | --- |")
    for row in evidence["safetyBenefitQuadrant"]:
        lines.append(
            f"| {row['arm']} | {row['falsePromotionBurden']:.8f} | "
            f"{row['descriptiveFalseDemotionOrUnnecessaryHoldRate']:.8f} |"
        )
    lines.append("")
    lines.append("## Next-level success and oscillation")
    lines.append("")
    lines.append(
        "Next-level success is the complement of the frozen "
        "`next_attempt_support_needed` label for observed assignment-matched "
        "outcomes. Oscillation is a move up followed by a move down, or the "
        "reverse, within a learner/subtopic decision sequence."
    )
    lines.append("")
    lines.append(
        "| Arm | Next-level success count | Next-level success rate | "
        "Oscillation count | Oscillation rate |"
    )
    lines.append("| --- | --- | --- | --- | --- |")
    for row in evidence["nextLevelSuccessAndOscillation"]:
        lines.append(
            f"| {row['arm']} | {row['nextLevelSuccessCount']} | "
            f"{row['nextLevelSuccessRate']:.8f} | {row['oscillationCount']} | "
            f"{row['oscillationRate']:.8f} |"
        )
    lines.append("")
    lines.append("## BKT reliability curve")
    lines.append("")
    lines.append(
        "Bands with fewer than five observations are labelled `insufficient` "
        "and must not be plotted as reliable."
    )
    lines.append("")
    lines.append(
        "| Band | Predicted mastery (mid) | Observed next-level success | "
        "Observations | Status |"
    )
    lines.append("| --- | --- | --- | --- | --- |")
    for row in evidence["bktReliabilityCurve"]:
        lines.append(
            f"| {row['lower']:.1f}-{row['upper']:.1f} | "
            f"{row['predictedMasteryMid']:.3f} | {row['observedSuccessRate']:.8f} | "
            f"{row['observationCount']} | `{row['status']}` |"
        )
    lines.append("")
    lines.append("## Transition matrices")
    lines.append("")
    for arm, transition in sorted(evidence["transitionMatrices"].items()):
        lines.append(f"### Arm {arm}")
        lines.append("")
        lines.append("| Current \\ Target | Easy | Moderate | Hard |")
        lines.append("| --- | --- | --- | --- |")
        for current in ("Easy", "Moderate", "Hard"):
            values = transition["matrix"][current]
            lines.append(
                f"| {current} | {values['Easy']} | {values['Moderate']} | "
                f"{values['Hard']} |"
            )
        lines.append("")
        lines.append(f"Unassigned decisions: `{transition['unassignedCount']}`.")
        lines.append("")
    lines.append("## Decision audit table")
    lines.append("")
    lines.append(
        "Pseudonymized decision rows with reason codes, selected and delivered "
        "difficulty, and later outcome status. Counterfactual mismatches are "
        "censored, never scored."
    )
    lines.append("")
    audit = evidence["decisionAuditTable"]
    if audit:
        header = list(audit[0])
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join("---" for _ in header) + " |")
        for row in audit:
            lines.append("| " + " | ".join(str(row[key]) for key in header) + " |")
    else:
        lines.append("_No decisions to audit._")
    lines.append("")
    lines.append("## Fairness and censoring")
    lines.append("")
    fairness = evidence["fairnessAndCensoring"]
    lines.append("| Arm | Observed | Same bank | Cross bank | Censored by reason |")
    lines.append("| --- | --- | --- | --- | --- |")
    for arm, values in sorted(fairness["byArm"].items()):
        censored_text = ", ".join(
            f"{reason}={count}" for reason, count in sorted(values["censoredByReason"].items())
        ) or "none"
        lines.append(
            f"| {arm} | {values['observedCount']} | "
            f"{values['sameBankObservedCount']} | {values['crossBankObservedCount']} | "
            f"{censored_text} |"
        )
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    for limitation in evidence["limitations"]:
        lines.append(f"- {limitation}")
    lines.append("")
    lines.append("## Reproducibility")
    lines.append("")
    lines.append(
        f"Every plotted aggregate traces to manifest `{run_manifest.manifest_sha256()}` "
        f"and dataset `{run_manifest.dataset_sha256}`. Report SHA-256: "
        f"`{report_sha256(evidence)}`."
    )
    lines.append("")
    text = "\n".join(lines)
    assert_claim_safe(text)
    return text


def render_decision_audit_csv(evidence: Mapping[str, object]) -> str:
    """Render the pseudonymized decision audit table as CSV."""
    import csv
    import io

    rows = evidence["decisionAuditTable"]
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def report_sha256(evidence: Mapping[str, object]) -> str:
    """Deterministic content hash of the evidence package."""
    serialized = json.dumps(evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(serialized.encode("utf-8")).hexdigest()


def assert_claim_safe(text: str) -> None:
    """Fail closed if the rendered report states a superiority claim."""
    lowered = text.lower()
    if "superior" in lowered:
        raise ReportingError("rendered report must not contain a superiority claim")

