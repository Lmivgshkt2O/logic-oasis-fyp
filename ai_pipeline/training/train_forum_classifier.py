"""Train a versioned forum artifact and write an evidence-limited manifest."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path
import tempfile
from typing import Iterable

from logic_oasis_ai.forum_ai.classifier import (
    CONTROLLED_REVISION,
    CONTROLLED_SUFFICIENT,
    MODEL_VERSION,
    ForumTextClassifier,
    train_classifier,
)
from logic_oasis_ai.forum_ai.dataset import grouped_rows, load_labelled_examples
from forum_controlled_demo.schema import EVIDENCE_LEVEL, PROVENANCE
from forum_controlled_demo.build_forum_dataset import ForumDatasetRow


def train_controlled_demo_candidate(
    rows: Iterable[ForumDatasetRow],
    *,
    variant: str,
    model_version: str,
) -> ForumTextClassifier:
    """Train only from schema-validated fictional controlled-demo rows."""
    values = tuple(rows)
    if not values or any(
        row.provenance != PROVENANCE or row.evidence_level != EVIDENCE_LEVEL
        for row in values
    ):
        raise ValueError("controlled-demo candidate requires fictional controlled provenance")
    labels = {row.label for row in values}
    if labels != {CONTROLLED_SUFFICIENT, CONTROLLED_REVISION}:
        raise ValueError("controlled-demo candidate requires both declared rubric labels")
    return train_classifier(
        [(row.text, row.label) for row in values],
        model_version=model_version,
        variant=variant,
    )


def train(*, dataset_path: Path, artifact_path: Path, report_path: Path) -> dict[str, object]:
    examples = load_labelled_examples(dataset_path)
    provenance = sorted({example.provenance for example in examples})
    if provenance != ["synthetic_test"]:
        raise ValueError(
            "real/approved forum data needs the separate reviewed evaluation workflow before an artifact can be produced"
        )
    if len({dataset_path.resolve(), artifact_path.resolve(), report_path.resolve()}) != 3:
        raise ValueError("dataset, artifact, and manifest paths must be distinct")
    classifier = train_classifier(grouped_rows(examples))
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=artifact_path.parent, delete=False) as artifact_file:
        temporary_artifact = Path(artifact_file.name)
    with tempfile.NamedTemporaryFile(dir=report_path.parent, delete=False) as report_file:
        temporary_report = Path(report_file.name)
    classifier.save(temporary_artifact)
    report = {
        "modelVersion": MODEL_VERSION,
        "rubricVersion": "forum-explanation-rubric-v1",
        "datasetSha256": sha256(dataset_path.read_bytes()).hexdigest(),
        "artifactSha256": sha256(temporary_artifact.read_bytes()).hexdigest(),
        "rowCount": len(examples),
        "classBalance": dict(sorted(Counter(example.label for example in examples).items())),
        "authorGroupedSplit": "not_evaluable_small_fixture_dataset",
        "precisionRecallF1": "not_claimed_small_fixture_dataset",
        "calibrationState": "not_calibrated",
        "provenance": provenance,
        "evidenceState": "emulator_fixture_only" if provenance == ["synthetic_test"] else "requires_review",
        "claimBoundary": "This artifact validates integration only; it is not evidence of performance with learners.",
    }
    temporary_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # The runtime checks the manifest hash before loading. If an interrupted
    # replace leaves an old/new pair, it fails safely to advisory fallback.
    temporary_artifact.replace(artifact_path)
    temporary_report.replace(report_path)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(train(dataset_path=args.dataset, artifact_path=args.artifact, report_path=args.report), sort_keys=True))
