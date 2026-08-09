"""J3-v2: build the exact two-feature U7 table from v2 skill episodes.

Grade 6 is evaluated as the primary cohort; Grades 4-6 remain the declared
secondary analysis.  Gates follow the existing U7 sufficiency rules; if the
held-out gate is viable, the deterministic student-grouped split (seed
20260716) is created and frozen.  No model is trained.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from .assistments_contract import PROVENANCE, SOURCE_DATASET
from .build_u7_dataset import assess_sufficiency_gates, build_student_grouped_split, write_model_table
from .j2_contract import (
    J2_CONTRACT_VERSION_V2,
    MASTERY_CRITERION,
    MAX_RESPONSE_TIME_MS,
    load_j2_contract,
    validate_j2_contract_v2,
)


MODEL_TABLE_FIELDS = ("correct_rate", "mean_response_time_ms", "next_attempt_support_needed")
AUDIT_FIELDS = (
    "currentEpisodeId",
    "externalStudentKey",
    "externalAssignmentKey",
    "externalSequenceKey",
    "externalSkillCode",
    "sourceGrade",
    "currentEpisodeStartedAt",
    "nextEpisodeId",
    "nextEpisodeStartedAt",
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


def read_labels(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def read_episodes(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def build_v2_rows(
    labels: Sequence[Mapping[str, Any]],
    episodes: Mapping[str, Mapping[str, Any]],
    *,
    release_id: str,
    contract_version: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for label in labels:
        target_raw = str(label.get("next_attempt_support_needed") or "").strip().lower()
        if not target_raw:
            continue
        if target_raw not in {"true", "false"}:
            errors.append(f"invalid target {label.get('currentEpisodeId')}")
            continue
        current = episodes.get(str(label.get("currentEpisodeId") or ""))
        if current is None:
            errors.append(f"missing current episode {label.get('currentEpisodeId')}")
            continue
        correct_rate = _float(current.get("correct_rate"))
        mean_rt = _float(current.get("mean_response_time_ms"))
        if correct_rate is None or not isfinite(correct_rate) or not 0.0 <= correct_rate <= 1.0:
            errors.append(f"{label.get('currentEpisodeId')}: correct_rate out of range")
            continue
        if mean_rt is None or not isfinite(mean_rt) or mean_rt <= 0 or mean_rt > MAX_RESPONSE_TIME_MS:
            errors.append(f"{label.get('currentEpisodeId')}: mean_response_time_ms out of range")
            continue
        next_episode = episodes.get(str(label.get("nextEpisodeId") or ""))
        rows.append(
            {
                "correct_rate": correct_rate,
                "mean_response_time_ms": mean_rt,
                "next_attempt_support_needed": target_raw == "true",
                "currentAttemptId": str(current["externalEpisodeId"]),
                "externalStudentKey": str(current["externalStudentKey"]),
                "externalAssignmentKey": str(current["externalAssignmentKey"]),
                "externalSequenceKey": str(current["externalSequenceKey"]),
                "externalSkillCode": str(current["externalSkillCode"]),
                "sourceGrade": str(current.get("sourceGrade") or ""),
                "currentEpisodeStartedAt": str(label.get("currentEpisodeStartedAt") or ""),
                "nextEpisodeId": str(label.get("nextEpisodeId") or ""),
                "nextEpisodeStartedAt": str(label.get("nextEpisodeStartedAt") or ""),
                "currentGradedProblemKeys": str(current.get("gradedProblemKeys") or ""),
                "nextGradedProblemKeys": str(next_episode.get("gradedProblemKeys") or "") if next_episode else "",
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


def _float(value: object) -> float | None:
    if value is None or value == "" or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def feature_audit(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"rows": 0}
    rates = [float(row["correct_rate"]) for row in rows]
    times = [float(row["mean_response_time_ms"]) for row in rows]

    def stats(values: list[float]) -> dict[str, float]:
        ordered = sorted(values)
        n = len(ordered)
        median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
        return {"min": min(values), "median": median, "mean": sum(values) / n, "max": max(values)}

    return {
        "rows": len(rows),
        "correct_rate": stats(rates),
        "mean_response_time_ms": stats(times),
        "missingCount": 0,
    }


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_v2_audit_table(rows: Sequence[Mapping[str, Any]], path: str | Path) -> Path:
    destination = Path(path)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in AUDIT_FIELDS})
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="J3-v2 U7 dataset, gates, and frozen split")
    parser.add_argument("--labels", required=True, help="Protected v2 external_labels CSV")
    parser.add_argument("--episodes", required=True, help="Protected v2 external_skill_attempts CSV")
    parser.add_argument("--processed-dir", required=True)
    parser.add_argument("--contract", default=None)
    parser.add_argument("--release-id", default="assistments-edm-cup-2023-release-v1")
    parser.add_argument("--cohort-label", default="Grade 6")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parents[2]
    contract_path = Path(args.contract) if args.contract else repo_dir / "external_data" / "assistments" / "assistments_j2_contract_v2.yaml"
    contract = validate_j2_contract_v2(load_j2_contract(contract_path))

    processed = Path(args.processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    model_path = processed / "u7_model_table_v2.csv"
    audit_path = processed / "u7_audit_table_v2.csv"
    readiness_path = processed / "u7_v2_readiness_manifest.json"
    if any(path.exists() for path in (model_path, audit_path, readiness_path)) and not args.force:
        raise FileExistsError("protected v2 J3 outputs are immutable; use --force")

    labels = read_labels(args.labels).to_dict("records")
    episodes = {str(row["externalEpisodeId"]): row for row in read_episodes(args.episodes).to_dict("records")}
    rows, errors = build_v2_rows(labels, episodes, release_id=args.release_id, contract_version=contract["contractVersion"])
    if errors:
        print("ROW BUILD ERRORS:", len(errors))
        for error in errors[:10]:
            print("  ", error)

    labelled = [row for row in rows if isinstance(row.get("next_attempt_support_needed"), bool)]
    gates = assess_sufficiency_gates(rows)
    split = build_student_grouped_split(rows)
    write_model_table(rows, model_path)
    write_v2_audit_table(rows, audit_path)

    targets = Counter(bool(row["next_attempt_support_needed"]) for row in labelled)
    learners = {row["externalStudentKey"] for row in labelled}
    true_learners = {row["externalStudentKey"] for row in labelled if row["next_attempt_support_needed"]}
    false_learners = {row["externalStudentKey"] for row in labelled if not row["next_attempt_support_needed"]}
    grade_counts = Counter(str(row["sourceGrade"]) for row in labelled)
    learners_by_grade: dict[str, set[str]] = {}
    for row in labelled:
        learners_by_grade.setdefault(str(row["sourceGrade"]), set()).add(str(row["externalStudentKey"]))
    learner_label_counts = Counter(int(bool(row["next_attempt_support_needed"])) for row in labelled)

    manifest = {
        "manifestSchemaVersion": "assistments-j3-v2-readiness-manifest",
        "contractVersion": J2_CONTRACT_VERSION_V2,
        "cohortLabel": args.cohort_label,
        "releaseId": args.release_id,
        "dataset": SOURCE_DATASET,
        "provenance": PROVENANCE,
        "sourceWindow": "2022-01-01/2023-12-31",
        "masteryCriterion": MASTERY_CRITERION,
        "splitSeed": 20260716,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sufficiencyGates": gates,
        "classDistribution": {
            "labelledRows": len(labelled),
            "targetTrue": targets.get(True, 0),
            "targetFalse": targets.get(False, 0),
            "targetTruePercent": round(100 * targets.get(True, 0) / len(labelled), 2) if labelled else None,
            "targetFalsePercent": round(100 * targets.get(False, 0) / len(labelled), 2) if labelled else None,
            "uniqueLabelledLearners": len(learners),
            "labelledRowsByGrade": dict(sorted(grade_counts.items())),
            "labelledLearnersByGrade": {grade: len(learners) for grade, learners in sorted(learners_by_grade.items())},
            "trueLearners": len(true_learners),
            "falseLearners": len(false_learners),
            "labelsPerLearnerDistribution": dict(sorted(learner_label_counts.items())),
        },
        "featureAudit": feature_audit(labelled),
        "studentGroupedSplit": split,
        "rowBuildErrors": len(errors),
        "fileSha256": {
            "u7_model_table_v2.csv": file_sha256(model_path),
            "u7_audit_table_v2.csv": file_sha256(audit_path),
        },
        "containsRawIdentifiers": False,
        "containsSecretMaterial": False,
    }
    readiness_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"gates": gates, "classDistribution": manifest["classDistribution"], "split": split}, indent=2, sort_keys=True, default=str))
    print(f"model table: {model_path}")
    print(f"readiness manifest: {readiness_path}")


if __name__ == "__main__":
    main()
