"""J2-v2 CLI: current -> next skill-episode labels and the v2 manifest."""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .assistments_contract import PROVENANCE, SOURCE_DATASET
from .j2_contract import (
    J2_CONTRACT_VERSION,
    J2_CONTRACT_VERSION_V2,
    MASTERY_CRITERION,
    MAX_RESPONSE_TIME_MS,
    load_j2_contract,
    validate_j2_contract_v2,
)
from .skill_episodes import LABEL_FIELDS, EpisodePair, build_episode_pairs


CATEGORY_COLUMNS = (
    "datasetReleaseId",
    "externalEpisodeId",
    "externalStudentKey",
    "externalAssignmentKey",
    "externalSequenceKey",
    "externalSkillCode",
    "externalContentKey",
    "sourceGrade",
    "sourceSubject",
    "provenance",
    "sourceDataset",
)


def read_episodes(path: str | Path) -> list[dict[str, Any]]:
    frame = pd.read_csv(
        path,
        dtype={column: "category" for column in CATEGORY_COLUMNS},
        keep_default_na=False,
    )
    return frame.to_dict("records")


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_labels_csv(pairs: list[EpisodePair], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        for pair in pairs:
            writer.writerow(pair.to_csv_row())


def build_v2_manifest(
    *,
    release_id: str,
    v1_contract_path: Path,
    v2_contract_path: Path,
    action_rows_path: Path,
    episodes_path: Path,
    outcomes_path: Path,
    labels_path: Path,
    reconstruction_summary: Mapping[str, Any],
    label_summary: Mapping[str, Any],
) -> dict[str, Any]:
    from datetime import datetime, timezone

    return {
        "manifestSchemaVersion": "assistments-j2-manifest-v2",
        "contractVersion": J2_CONTRACT_VERSION_V2,
        "contractSha256": file_sha256(v2_contract_path),
        "predecessorContract": J2_CONTRACT_VERSION,
        "predecessorContractSha256": file_sha256(v1_contract_path),
        "amendmentRationale": [
            "sequence-level in-unit assignments contain multiple skills, so the v1 same-sequence attempt conflates several student-subtopic units",
            "repeated same-sequence fluency rounds frequently reuse identical problem sets, which v1 correctly censored and produced zero labelled rows",
            "the exact source-native sourceSkillCode maps more directly to the canonical Logic Oasis student-subtopic prediction unit",
        ],
        "amendmentNotMotivatedByModelPerformance": True,
        "j3aDiagnosticCountsAreNotFinalModelData": True,
        "releaseId": release_id,
        "dataset": SOURCE_DATASET,
        "provenance": PROVENANCE,
        "sourceWindow": "2022-01-01/2023-12-31",
        "masteryCriterion": MASTERY_CRITERION,
        "timingContract": f"0 < response_time_ms <= {MAX_RESPONSE_TIME_MS}",
        "featureSchema": "quiz-attempt-features-v2",
        "baseFeatures": ["correct_rate", "mean_response_time_ms"],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceReleaseLineage": {"external_action_rows_v1.csv": file_sha256(action_rows_path)},
        "reconstruction": dict(reconstruction_summary),
        "labels": dict(label_summary),
        "fileSha256": {
            "external_skill_attempts_v2.csv": file_sha256(episodes_path),
            "external_skill_problem_outcomes_v2.csv": file_sha256(outcomes_path),
            "external_labels_v2.csv": file_sha256(labels_path),
        },
        "containsRawIdentifiers": False,
        "containsSecretMaterial": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="J2-v2 labels and manifest")
    parser.add_argument("--episodes", required=True, help="Protected v2 external_skill_attempts CSV")
    parser.add_argument("--action-rows", required=True, help="Protected J1 external_action_rows CSV")
    parser.add_argument("--problem-outcomes", required=True, help="Protected v2 problem outcomes CSV")
    parser.add_argument("--processed-dir", required=True)
    parser.add_argument("--contract", default=None)
    parser.add_argument("--release-id", default="assistments-edm-cup-2023-release-v1")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parents[2]
    v2_contract_path = Path(args.contract) if args.contract else repo_dir / "external_data" / "assistments" / "assistments_j2_contract_v2.yaml"
    v1_contract_path = repo_dir / "external_data" / "assistments" / "assistments_j2_contract_v1.yaml"
    contract = validate_j2_contract_v2(load_j2_contract(v2_contract_path))

    processed = Path(args.processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    labels_path = processed / "external_labels_v2.csv"
    manifest_path = processed / "j2_v2_manifest.json"
    if (labels_path.exists() or manifest_path.exists()) and not args.force:
        raise FileExistsError("protected v2 label outputs are immutable; use --force")

    episodes = read_episodes(args.episodes)
    # Rebuild EpisodeRecord-like dicts; build_episode_pairs needs the record API,
    # so convert CSV rows into lightweight mapping-compatible values.
    pairs, label_summary = _pair_from_rows(episodes, release_id=args.release_id, contract=contract)
    write_labels_csv(pairs, labels_path)

    reconstruction_summary: dict[str, Any] = {}
    summary_path = processed / "j2_v2_reconstruction_summary.json"
    if summary_path.exists():
        reconstruction_summary = json.loads(summary_path.read_text(encoding="utf-8"))

    manifest = build_v2_manifest(
        release_id=args.release_id,
        v1_contract_path=v1_contract_path,
        v2_contract_path=v2_contract_path,
        action_rows_path=Path(args.action_rows),
        episodes_path=Path(args.episodes),
        outcomes_path=Path(args.problem_outcomes),
        labels_path=labels_path,
        reconstruction_summary=reconstruction_summary,
        label_summary=dict(sorted(label_summary.items())),
    )
    serialized = json.dumps(manifest)
    if str(processed.resolve()) in serialized or str(Path.cwd().resolve()) in serialized:
        raise ValueError("v2 manifest must not contain a local working path")
    manifest_path.write_text(serialized + "\n", encoding="utf-8")
    print(json.dumps(dict(sorted(label_summary.items())), indent=2, sort_keys=True))
    print(f"labels: {labels_path}")
    print(f"manifest: {manifest_path}")


def _pair_from_rows(episodes: list[dict[str, Any]], *, release_id: str, contract: Mapping[str, Any]):
    """Pair episodes directly from CSV rows (mirrors skill_episodes semantics)."""
    from .skill_episodes import EpisodeRecord

    records = [
        EpisodeRecord(
            datasetReleaseId=str(row.get("datasetReleaseId") or release_id),
            externalEpisodeId=str(row["externalEpisodeId"]),
            externalStudentKey=str(row["externalStudentKey"]),
            externalAssignmentKey=str(row["externalAssignmentKey"]),
            externalSequenceKey=str(row["externalSequenceKey"]),
            externalSkillCode=str(row["externalSkillCode"]),
            externalContentKey=str(row.get("externalContentKey") or ""),
            sourceGrade=str(row.get("sourceGrade") or "") or None,
            sourceSubject=str(row.get("sourceSubject") or "") or None,
            episodeStartedAt=_parse_ts(row.get("episodeStartedAt")),
            episodeEndedAt=_parse_ts(row.get("episodeEndedAt")),
            completed=_bool(row.get("completed")),
            cohortEligible=_bool(row.get("cohortEligible")),
            problemCount=_int(row.get("problemCount")),
            gradedProblemCount=_int(row.get("gradedProblemCount")),
            correctFirstResponseCount=_int(row.get("correctFirstResponseCount")),
            correct_rate=_float(row.get("correct_rate")),
            validResponseTimePairs=_int(row.get("validResponseTimePairs")),
            mean_response_time_ms=_float(row.get("mean_response_time_ms")),
            gradedProblemKeys=tuple(item for item in str(row.get("gradedProblemKeys") or "").split("|") if item),
            outcomeValid=_bool(row.get("outcomeValid")),
            featureValid=_bool(row.get("featureValid")),
            episodeCensorReason=str(row.get("episodeCensorReason") or "") or None,
        )
        for row in episodes
    ]
    return build_episode_pairs(records, release_id=release_id)


def _parse_ts(value: object):
    if value is None or value == "":
        return None
    return pd.to_datetime(value, format="ISO8601", utc=True, errors="coerce").to_pydatetime()


def _bool(value: object) -> bool:
    return str(value).strip().lower() == "true"


def _int(value: object) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    main()

