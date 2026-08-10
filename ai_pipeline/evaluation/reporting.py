"""Machine-readable and markdown aggregate reports for Stage B replay."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Mapping

from .manifest import EvaluationRunManifest
from .metrics import PolicyComparisonMetrics


REPORT_KIND = "policy_evaluation_replay_report_v1"
FORBIDDEN_REPORT_SUBSTRINGS = (
    "answerText",
    "answerKey",
    "shap",
    "artifactSha256",
    "studentId",
    "sessionId",
    "questionText",
)


class ReportingError(ValueError):
    """Raised when an aggregate report cannot be built safely."""


def build_machine_report(
    run_manifest: EvaluationRunManifest,
    metrics: PolicyComparisonMetrics,
    *,
    attempt_count: int,
) -> dict[str, object]:
    """Build the deterministic machine-readable report (aggregates only)."""
    manifest_document = dict(run_manifest.to_document())
    manifest_document["manifestSha256"] = run_manifest.manifest_sha256()
    figure_data = [
        {
            "arm": arm.arm,
            "promotionRate": arm.promotion_rate,
            "falsePromotionBurden": arm.false_promotion_burden,
            "descriptiveFalseDemotionOrUnnecessaryHoldRate": (
                arm.descriptive_false_demotion_or_unnecessary_hold_rate
            ),
        }
        for arm in metrics.arms
    ]
    report = {
        "reportKind": REPORT_KIND,
        "claimLevel": metrics.claim_label,
        "manifest": manifest_document,
        "dataset": {
            "attemptCount": attempt_count,
            "studentCount": metrics.student_count,
            "decisionCount": metrics.decision_count,
            "provenance": run_manifest.provenance,
        },
        "metrics": metrics.to_document(),
        "figureData": {
            "promotionSafety": figure_data,
        },
        "limitations": _limitations(run_manifest),
    }
    report["reportSha256"] = _canonical_sha256(report)
    _assert_safe_report(report)
    return report


def render_machine_json(report: Mapping[str, object]) -> str:
    """Render the machine report deterministically."""
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def build_markdown_report(
    run_manifest: EvaluationRunManifest,
    metrics: PolicyComparisonMetrics,
    *,
    attempt_count: int,
) -> str:
    """Build the supervisor-readable descriptive markdown report."""
    lines: list[str] = []
    lines.append("# Logic Oasis Policy Comparison - Stage B Descriptive Replay")
    lines.append("")
    lines.append(f"**Claim level:** `{metrics.claim_label}`")
    lines.append("")
    lines.append(
        "This report reconstructs what each declared policy would have decided "
        "at historical decision points. It is **observational and descriptive**, "
        "not causal evidence. It never claims that one policy outperformed another."
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
        ("HMAC namespace", run_manifest.hmac_namespace),
        ("Source schema", run_manifest.source_schema_version),
        ("Feature schema", run_manifest.feature_schema_version),
        ("BKT version", run_manifest.bkt_version),
        ("Adaptive policy", f"{run_manifest.adaptive_policy_version} ({run_manifest.adaptive_policy_sha256[:12]}...)"),
        ("Policy-evaluation contract", f"{run_manifest.policy_evaluation_version} ({run_manifest.policy_evaluation_sha256[:12]}...)"),
        ("Frozen target", run_manifest.frozen_prediction_target),
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
    lines.append("## Dataset")
    lines.append("")
    lines.append(
        f"- Trusted attempts: {attempt_count}; students: {metrics.student_count}; "
        f"reconstructed decisions: {metrics.decision_count}."
    )
    lines.append("")
    lines.append("## Policy decision metrics")
    lines.append("")
    lines.append("| Arm | Decisions | Assignable | Coverage | Up | Down | Hold |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for arm in metrics.arms:
        lines.append(
            f"| {arm.arm} | {arm.decision_count} | {arm.assignable_count} | "
            f"{arm.coverage_rate:.4f} | {arm.promotion_rate:.4f} | "
            f"{arm.demotion_rate:.4f} | {arm.hold_rate:.4f} |"
        )
    lines.append("")
    lines.append("## Observed-assignment-matched outcomes (descriptive)")
    lines.append("")
    lines.append(
        "Later outcomes are reported only when the candidate-selected difficulty "
        "matches the difficulty actually delivered and compatibility checks pass. "
        "All other rows are censored and never scored."
    )
    lines.append("")
    lines.append(
        "| Arm | Observed | Support needed | False promotion burden | "
        "False demotion / unnecessary hold (descriptive) |"
    )
    lines.append("| --- | --- | --- | --- | --- |")
    for arm in metrics.arms:
        lines.append(
            f"| {arm.arm} | {arm.observed_outcome_count} | "
            f"{arm.observed_support_needed_rate:.4f} | "
            f"{arm.false_promotion_burden:.4f} | "
            f"{arm.descriptive_false_demotion_or_unnecessary_hold_rate:.4f} |"
        )
    lines.append("")
    lines.append("## Censoring audit")
    lines.append("")
    lines.append("| Reason | Count |")
    lines.append("| --- | --- |")
    for reason, count in metrics.censoring_summary:
        lines.append(f"| `{reason}` | {count} |")
    lines.append("")
    lines.append("## Decision agreement")
    lines.append("")
    lines.append("| Arm A | Arm B | Agreement rate | Compared decisions |")
    lines.append("| --- | --- | --- | --- |")
    for arm_a, arm_b, rate, count in metrics.agreement:
        lines.append(f"| {arm_a} | {arm_b} | {rate:.4f} | {count} |")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    for limitation in _limitations(run_manifest):
        lines.append(f"- {limitation}")
    lines.append("")
    lines.append("## Reproducibility")
    lines.append("")
    lines.append(
        f"Identical trusted exports and this frozen manifest reproduce identical "
        f"ordered decisions and report hashes. Report SHA-256: "
        f"`{_canonical_sha256(build_machine_report(run_manifest, metrics, attempt_count=attempt_count))}`"
    )
    lines.append("")
    return "\n".join(lines)


def report_sha256(report: Mapping[str, object]) -> str:
    """Return the deterministic report content hash."""
    return _canonical_sha256(report)


def _limitations(run_manifest: EvaluationRunManifest) -> list[str]:
    limitations = [
        "Offline observational replay only; it cannot prove that a policy causes better learning.",
        "Observed-assignment-matched outcomes exclude counterfactual difficulty mismatches.",
        "Censored rows are reported by reason and never converted into success or failure.",
        "Banks observed in the dataset are treated as active unless a server-owned bank catalogue was supplied.",
        "P3b (model-assisted) results are reported separately and only when compatible support-risk evidence is provided.",
    ]
    if run_manifest.provenance != "real":
        limitations.append(
            "Records are not approved real runtime data; results are a pipeline demonstration only."
        )
    return limitations


def _assert_safe_report(report: Mapping[str, object]) -> None:
    serialized = json.dumps(report, sort_keys=True, ensure_ascii=True).lower()
    for forbidden in FORBIDDEN_REPORT_SUBSTRINGS:
        if forbidden.lower() in serialized:
            raise ReportingError(f"report must not contain protected field: {forbidden}")


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    serialized = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return sha256(serialized.encode("utf-8")).hexdigest()

