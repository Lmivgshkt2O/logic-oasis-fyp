"""Train a versioned forum artifact and write an evidence-limited manifest."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path
import tempfile

from logic_oasis_ai.forum_ai.classifier import MODEL_VERSION, train_classifier
from logic_oasis_ai.forum_ai.dataset import grouped_rows, load_labelled_examples


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
