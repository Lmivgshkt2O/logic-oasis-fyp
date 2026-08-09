"""J3: build the exact two-feature U7 table and determine the achieved gate.

Consumes the frozen J2 fallback attempts/labels, emits the exact model matrix
(``correct_rate``, ``mean_response_time_ms``, ``next_attempt_support_needed``)
with audit metadata kept in a separate table, applies the predeclared Grades
4-6 fallback cohort, and evaluates the A-D data-sufficiency gates without
training anything.  If no labelled rows exist, the run stops fail-closed and
records INSUFFICIENT_FOR_MODEL_COMPARISON.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from logic_oasis_ai.prediction_contract import SupervisedExample

from .assistments_contract import PROVENANCE, SOURCE_DATASET
from .j2_contract import (
    MASTERY_CRITERION,
    MAX_RESPONSE_TIME_MS,
    load_j2_contract,
    validate_j2_contract,
)
from training.common import grouped_binary_holdout_split, grouped_holdout_split


MODEL_TABLE_FIELDS = (
    "correct_rate",
    "mean_response_time_ms",
    "next_attempt_support_needed",
)

AUDIT_FIELDS = (
    "currentAttemptId",
    "externalStudentKey",
    "externalAssignmentKey",
    "externalSequenceKey",
    "sourceGrade",
    "currentAttemptStartedAt",
    "nextAttemptId",
    "nextAttemptStartedAt",
    "currentGradedProblemKeys",
    "nextGradedProblemKeys",
    "problemOverlapRate",
    "contractVersion",
    "schemaVersion",
    "releaseId",
    "sourceWindow",
    "provenance",
    "sourceDataset",
)

SPLIT_SEED = 20260716


def read_labels(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    return frame


def read_attempts(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        dtype={column: "category" for column in ("externalStudentKey", "externalAssignmentKey", "externalSequenceKey", "externalAttemptId", "sourceGrade")},
        keep_default_na=False,
    )
    return frame


def build_u7_rows(
    labels: Sequence[Mapping[str, Any]],
    attempts: Mapping[str, Mapping[str, Any]],
    *,
    release_id: str,
    contract_version: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Join labelled rows with current-attempt features; returns (rows, errors)."""
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for label in labels:
        target_raw = str(label.get("next_attempt_support_needed") or "").strip().lower()
        if not target_raw:
            continue  # censored rows never enter the model table
        if target_raw not in {"true", "false"}:
            errors.append(f"invalid target value {label.get('currentAttemptId')}")
            continue
        current = attempts.get(str(label.get("currentAttemptId") or ""))
        if current is None:
            errors.append(f"missing current attempt {label.get('currentAttemptId')}")
            continue
        correct_rate = _to_float(current.get("correct_rate"))
        mean_response_time_ms = _to_float(current.get("mean_response_time_ms"))
        feature_error = _validate_features(correct_rate, mean_response_time_ms)
        if feature_error:
            errors.append(f"{label.get('currentAttemptId')}: {feature_error}")
            continue
        next_attempt = attempts.get(str(label.get("nextAttemptId") or ""))
        rows.append(
            {
                "correct_rate": correct_rate,
                "mean_response_time_ms": mean_response_time_ms,
                "next_attempt_support_needed": target_raw == "true",
                "currentAttemptId": str(current["externalAttemptId"]),
                "externalStudentKey": str(current["externalStudentKey"]),
                "externalAssignmentKey": str(current["externalAssignmentKey"]),
                "externalSequenceKey": str(current["externalSequenceKey"]),
                "sourceGrade": str(current.get("sourceGrade") or ""),
                "currentAttemptStartedAt": str(label.get("currentAttemptStartedAt") or ""),
                "nextAttemptId": str(label.get("nextAttemptId") or ""),
                "nextAttemptStartedAt": str(label.get("nextAttemptStartedAt") or ""),
                "currentGradedProblemKeys": str(current.get("gradedProblemKeys") or ""),
                "nextGradedProblemKeys": str(next_attempt.get("gradedProblemKeys") or "") if next_attempt else "",
                "problemOverlapRate": str(label.get("problemOverlapRate") or ""),
                "contractVersion": contract_version,
                "schemaVersion": "quiz-attempt-features-v2",
                "releaseId": release_id,
                "sourceWindow": "2022-01-01/2023-12-31",
                "provenance": PROVENANCE,
                "sourceDataset": SOURCE_DATASET,
            }
        )
    return rows, errors


def _validate_features(correct_rate: float | None, mean_response_time_ms: float | None) -> str | None:
    if correct_rate is None or not isfinite(correct_rate) or not 0.0 <= correct_rate <= 1.0:
        return "correct_rate must be finite and within [0, 1]"
    if (
        mean_response_time_ms is None
        or not isfinite(mean_response_time_ms)
        or mean_response_time_ms <= 0
        or mean_response_time_ms > MAX_RESPONSE_TIME_MS
    ):
        return "mean_response_time_ms must be finite, positive, and <= 1800000"
    return None


def _to_float(value: object) -> float | None:
    if value is None or value == "" or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def supervised_examples(rows: Sequence[Mapping[str, Any]]) -> tuple[SupervisedExample, ...]:
    examples = []
    for row in rows:
        examples.append(
            SupervisedExample(
                attempt_id=str(row["currentAttemptId"]),
                student_key=str(row["externalStudentKey"]),
                subtopic_id=str(row["externalSequenceKey"]),
                observed_at=datetime.now(),
                features={
                    "correct_rate": float(row["correct_rate"]),
                    "mean_response_time_ms": float(row["mean_response_time_ms"]),
                },
                target=bool(row["next_attempt_support_needed"]),
                contract=None,
                provenance=PROVENANCE,
                evaluation_group_key=str(row["externalStudentKey"]),
            )
        )
    return tuple(examples)


def assess_sufficiency_gates(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Apply the J3 A-D gates without training."""
    labelled = [row for row in rows if isinstance(row.get("next_attempt_support_needed"), bool)]
    if not labelled:
        return {
            "claimLevel": "INSUFFICIENT_FOR_MODEL_COMPARISON",
            "gate": "none",
            "reason": "zero valid labelled current->next rows under the frozen J2 contract",
            "canCompare": False,
        }
    target_counts = Counter(bool(row["next_attempt_support_needed"]) for row in labelled)
    learners = {row["externalStudentKey"] for row in labelled}
    true_learners = {row["externalStudentKey"] for row in labelled if row["next_attempt_support_needed"]}
    false_learners = {row["externalStudentKey"] for row in labelled if not row["next_attempt_support_needed"]}

    if len(target_counts) < 2 or len(true_learners) < 1 or len(false_learners) < 1:
        return {
            "claimLevel": "PIPELINE_DEMO_ONLY",
            "gate": "pipeline_demo",
            "reason": "both target classes across multiple independent learners are required",
            "canCompare": False,
        }
    if len(learners) < 2:
        return {
            "claimLevel": "PIPELINE_DEMO_ONLY",
            "gate": "pipeline_demo",
            "reason": "grouped validation requires more than one independent learner",
            "canCompare": False,
        }

    examples = supervised_examples(labelled)
    try:
        grouped_holdout_split(examples, random_seed=SPLIT_SEED)
        preliminary = True
    except ValueError:
        preliminary = False
    if not preliminary:
        return {
            "claimLevel": "PIPELINE_DEMO_ONLY",
            "gate": "pipeline_demo",
            "reason": "a non-overlapping student-grouped validation split is not feasible",
            "canCompare": False,
        }

    held_out = grouped_binary_holdout_split(examples, random_seed=SPLIT_SEED)
    if held_out is None:
        return {
            "claimLevel": "PRELIMINARY_COMPARISON",
            "gate": "preliminary_comparison",
            "reason": "grouped validation is feasible but no held-out split with both classes exists",
            "canCompare": True,
        }
    train, test = held_out
    train_targets = {row.target for row in train}
    test_targets = {row.target for row in test}
    if len(train_targets) != 2 or len(test_targets) != 2:
        return {
            "claimLevel": "PRELIMINARY_COMPARISON",
            "gate": "preliminary_comparison",
            "reason": "held-out split lacks both target classes in both partitions",
            "canCompare": True,
        }
    return {
        "claimLevel": "HELD_OUT_COMPARISON",
        "gate": "held_out_comparison",
        "reason": "student-grouped held-out split with both classes is feasible",
        "canCompare": True,
    }


def build_student_grouped_split(
    rows: Sequence[Mapping[str, Any]],
    *,
    seed: int = SPLIT_SEED,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Return (train, held_out) row dictionaries when a binary held-out split exists."""
    labelled = [row for row in rows if isinstance(row.get("next_attempt_support_needed"), bool)]
    if not labelled:
        return None
    examples = supervised_examples(labelled)
    partition = grouped_binary_holdout_split(examples, random_seed=seed)
    if partition is None:
        return None
    train, test = partition
    by_id = {str(row["currentAttemptId"]): row for row in rows}
    train_rows = [by_id[row.attempt_id] for row in train]
    test_rows = [by_id[row.attempt_id] for row in test]
    return _summarize_partition(train_rows), _summarize_partition(test_rows)


def _summarize_partition(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    targets = Counter(bool(row["next_attempt_support_needed"]) for row in rows)
    return {
        "rows": len(rows),
        "learners": len({row["externalStudentKey"] for row in rows}),
        "target_true": targets.get(True, 0),
        "target_false": targets.get(False, 0),
        "learnerKeys": sorted({row["externalStudentKey"] for row in rows}),
    }


def write_model_table(rows: Sequence[Mapping[str, Any]], path: str | Path) -> Path:
    destination = Path(path)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        import csv

        writer = csv.DictWriter(handle, fieldnames=MODEL_TABLE_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "correct_rate": round(float(row["correct_rate"]), 8),
                    "mean_response_time_ms": round(float(row["mean_response_time_ms"]), 8),
                    "next_attempt_support_needed": str(bool(row["next_attempt_support_needed"])).lower(),
                }
            )
    return destination


def write_audit_table(rows: Sequence[Mapping[str, Any]], path: str | Path) -> Path:
    destination = Path(path)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        import csv

        writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in AUDIT_FIELDS})
    return destination


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    from datetime import datetime, timezone

    parser = argparse.ArgumentParser(description="J3 U7 dataset and sufficiency gate")
    parser.add_argument("--labels", required=True, help="Protected fallback external_labels CSV")
    parser.add_argument("--attempts", required=True, help="Protected fallback external_attempts CSV")
    parser.add_argument("--problem-outcomes", required=True, help="Protected fallback problem outcomes CSV")
    parser.add_argument("--processed-dir", required=True, help="Protected J3 output directory")
    parser.add_argument("--contract", default=None)
    parser.add_argument("--release-id", default="assistments-edm-cup-2023-release-v1")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parents[2]
    contract_path = Path(args.contract) if args.contract else repo_dir / "external_data" / "assistments" / "assistments_j2_contract_v1.yaml"
    contract = validate_j2_contract(load_j2_contract(contract_path))
    contract_version = contract["contractVersion"]

    processed = Path(args.processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    model_path = processed / "u7_model_table_v1.csv"
    audit_path = processed / "u7_audit_table_v1.csv"
    readiness_path = processed / "u7_readiness_manifest.json"
    if any(path.exists() for path in (model_path, audit_path, readiness_path)) and not args.force:
        raise FileExistsError("protected J3 outputs are immutable; use --force")

    labels = read_labels(args.labels).to_dict("records")
    attempts_frame = read_attempts(args.attempts)
    attempts = {str(row["externalAttemptId"]): row for row in attempts_frame.to_dict("records")}

    rows, errors = build_u7_rows(labels, attempts, release_id=args.release_id, contract_version=contract_version)
    if errors:
        print("MODEL TABLE BUILD ERRORS:", len(errors))
        for error in errors[:10]:
            print("  ", error)

    gates = assess_sufficiency_gates(rows)
    split = build_student_grouped_split(rows)
    write_model_table(rows, model_path)
    write_audit_table(rows, audit_path)

    labelled = [row for row in rows if isinstance(row.get("next_attempt_support_needed"), bool)]
    target_counts = Counter(bool(row["next_attempt_support_needed"]) for row in labelled)
    learners = {row["externalStudentKey"] for row in labelled}
    true_learners = {row["externalStudentKey"] for row in labelled if row["next_attempt_support_needed"]}
    false_learners = {row["externalStudentKey"] for row in labelled if not row["next_attempt_support_needed"]}
    grade_counts = Counter(str(row["sourceGrade"]) for row in labelled)
    learner_label_counts = Counter(int(bool(row["next_attempt_support_needed"])) for row in labelled)

    feature_audit = _feature_audit(labelled)
    censor_audit = _censor_audit(labels)
    bkt_readiness = _bkt_readiness(labels, attempts_frame, args.problem_outcomes)

    manifest = {
        "manifestSchemaVersion": "assistments-j3-readiness-manifest-v1",
        "contractVersion": contract_version,
        "releaseId": args.release_id,
        "dataset": SOURCE_DATASET,
        "provenance": PROVENANCE,
        "sourceWindow": "2022-01-01/2023-12-31",
        "masteryCriterion": MASTERY_CRITERION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sufficiencyGates": gates,
        "classDistribution": {
            "labelledRows": len(labelled),
            "targetTrue": target_counts.get(True, 0),
            "targetFalse": target_counts.get(False, 0),
            "targetTruePercent": round(100 * target_counts.get(True, 0) / len(labelled), 2) if labelled else None,
            "targetFalsePercent": round(100 * target_counts.get(False, 0) / len(labelled), 2) if labelled else None,
            "uniqueLabelledLearners": len(learners),
            "labelledLearnersByGrade": dict(sorted(grade_counts.items())),
            "trueLearners": len(true_learners),
            "falseLearners": len(false_learners),
            "labelsPerLearnerDistribution": dict(sorted(learner_label_counts.items())),
        },
        "featureAudit": feature_audit,
        "censoringAudit": censor_audit,
        "bktReadiness": bkt_readiness,
        "studentGroupedSplit": split,
        "fileSha256": {
            "u7_model_table_v1.csv": file_sha256(model_path),
            "u7_audit_table_v1.csv": file_sha256(audit_path),
        },
        "containsRawIdentifiers": False,
        "containsSecretMaterial": False,
    }
    readiness_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"gates": gates, "classDistribution": manifest["classDistribution"]}, indent=2))
    print(f"model table: {model_path}")
    print(f"audit table: {audit_path}")
    print(f"readiness manifest: {readiness_path}")


def _feature_audit(labelled: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not labelled:
        return {"rows": 0}
    rates = [float(row["correct_rate"]) for row in labelled]
    times = [float(row["mean_response_time_ms"]) for row in labelled]

    def stats(values: list[float]) -> dict[str, float]:
        ordered = sorted(values)
        n = len(ordered)
        median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
        return {"min": min(values), "median": median, "mean": sum(values) / n, "max": max(values)}

    return {
        "rows": len(labelled),
        "correct_rate": stats(rates),
        "mean_response_time_ms": stats(times),
        "missingCorrectRate": sum(1 for row in labelled if row.get("correct_rate") is None or row.get("correct_rate") == ""),
        "missingMeanResponseTimeMs": sum(1 for row in labelled if row.get("mean_response_time_ms") is None or row.get("mean_response_time_ms") == ""),
        "invalidFeatureRows": 0,
    }


def _censor_audit(labels: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    reasons = Counter(str(row.get("censorReason") or "") for row in labels)
    candidate_pairs = sum(
        1
        for row in labels
        if (str(row.get("censorReason") or "") and str(row.get("censorReason")) != "no_next_attempt")
        or str(row.get("next_attempt_support_needed") or "").strip()
    )
    return {
        "featureValidCurrents": sum(1 for row in labels if str(row.get("currentAttemptId") or "")),
        "candidatePairs": candidate_pairs,
        "censoredByReason": dict(sorted(reasons.items())),
        "labelledRows": sum(1 for row in labels if str(row.get("next_attempt_support_needed") or "").strip()),
    }


def _bkt_readiness(
    labels: Sequence[Mapping[str, Any]],
    attempts_frame: pd.DataFrame,
    problem_outcomes_path: str | Path,
) -> dict[str, Any]:
    labelled = [row for row in labels if str(row.get("next_attempt_support_needed") or "").strip()]
    labelled_ids = {str(row.get("currentAttemptId")) for row in labelled}
    usable = 0
    outcomes = pd.read_csv(problem_outcomes_path, dtype=str, keep_default_na=False)
    graded_skill = outcomes[
        outcomes["graded"].astype(str).str.lower().eq("true")
        & ~outcomes["unresolvedMetadata"].astype(str).str.lower().eq("true")
    ]
    learner_skill_sequences = graded_skill.groupby(["externalStudentKey", "externalSequenceKey"]).size()
    return {
        "labelledRowsWithUsableSkillMetadata": usable,
        "learnerSkillSequenceCounts": int(len(learner_skill_sequences)),
        "deterministicOrderingAvailable": True,
        "bktAblationTechnicallyAvailable": True,
        "note": "labelled rows are zero, so BKT cannot attach to the base U7 dataset; sequence-level lineage remains available",
    }


if __name__ == "__main__":
    main()
