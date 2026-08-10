"""Publish the evaluated U4 Naive Bayes candidate as a bounded U5 release."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import shutil
from typing import Any

from forum_controlled_demo.build_forum_dataset import (
    build_forum_dataset,
    canonical_json_bytes,
)
from forum_controlled_demo.schema import (
    CLAIM_LEVEL,
    DEPLOYMENT_SCOPE,
    EVIDENCE_LEVEL,
    PROVENANCE,
    RELEASE_SCOPE,
)
from logic_oasis_ai.forum_ai.classifier import NAIVE_BAYES_VARIANTS


RATIONALE = (
    "Developer-released FYP1 controlled-demonstration model. "
    "Not evaluated on real learner forum responses."
)
DEPENDENCIES = ("joblib", "numpy", "scikit-learn")
RUNTIME_FILES = ("__init__.py", "classifier.py")


@dataclass(frozen=True)
class PublishedForumRelease:
    artifact_path: Path
    manifest_path: Path
    bundle_manifest_path: Path


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical_text_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _canonical_text_hash(path: Path) -> str:
    return sha256(_canonical_text_bytes(path)).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def _content_revision(root: Path, paths: tuple[Path, ...]) -> str:
    digest = sha256()
    for path in sorted(paths, key=lambda value: value.as_posix()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def publish_forum_controlled_demo(
    *, repository_root: Path, functions_root: Path,
    released_by: str, released_at: datetime, release_id: str,
    candidate_manifest_path: Path | None = None,
    release_rationale: str = RATIONALE,
    supersedes_release_id: str | None = None,
) -> PublishedForumRelease:
    if released_at.tzinfo is None:
        raise ValueError("released_at must be a trusted timezone-aware timestamp")
    generated = repository_root / "ai_pipeline/forum_controlled_demo/generated"
    reports = repository_root / "ai_pipeline/reports"
    candidate_manifest_path = candidate_manifest_path or generated / "forum_controlled_demo_candidate_manifest.json"
    candidate = _read_json(candidate_manifest_path)
    if candidate.get("controlledCandidateStatus") != "eligible" or candidate.get("activationStatus") != "pending_u5_activation":
        raise ValueError("only an eligible controlled candidate may be released")
    if candidate.get("modelType") not in NAIVE_BAYES_VARIANTS:
        raise ValueError("only the selected genuine Naive Bayes candidate may be released")
    if candidate.get("evidenceLevel") != "controlled_demonstration":
        raise ValueError("candidate evidence level is incompatible")
    report_path = reports / str(candidate["evaluationReportFile"])
    report = _read_json(report_path)
    if report.get("failedGates") or report.get("controlledCandidateStatus") != "eligible":
        failures = ",".join(str(value) for value in report.get("failedGates", [])) or "candidate_not_eligible"
        raise ValueError(f"candidate non-degeneracy gates are not eligible: {failures}")
    artifact_source = generated / str(candidate["artifactFile"])
    if _hash(artifact_source) != candidate.get("artifactSha256"):
        raise ValueError("candidate artifact hash mismatch")

    dataset_path = generated / str(candidate["datasetFile"])
    dataset_manifest_path = generated / str(candidate["datasetManifestFile"])
    split_manifest_path = generated / str(candidate["splitManifestFile"])
    catalogue_path = repository_root / str(candidate["catalogueFile"])
    authoritative = build_forum_dataset(catalogue_path)
    dataset_manifest = _read_json(dataset_manifest_path)
    if (
        _canonical_text_bytes(dataset_path) != authoritative.canonical_jsonl
        or dataset_manifest != dict(authoritative.manifest)
    ):
        raise ValueError("dataset does not rebuild from the authoritative catalogue")
    candidate_bindings = {
        "catalogueSha256": authoritative.manifest["catalogueSha256"],
        "datasetSha256": authoritative.manifest["datasetSha256"],
        "rubricSha256": authoritative.manifest["rubricSha256"],
    }
    if any(candidate.get(key) != value for key, value in candidate_bindings.items()):
        raise ValueError("candidate dataset, catalogue, or rubric binding mismatch")
    split_manifest = _read_json(split_manifest_path)
    if (
        sha256(canonical_json_bytes(split_manifest)).hexdigest()
        != candidate.get("splitManifestSha256")
        or _canonical_text_hash(report_path) != candidate.get("evaluationReportSha256")
    ):
        raise ValueError("candidate split or evaluation report binding mismatch")
    report_bindings = {
        "artifactByteHash": candidate["artifactSha256"],
        "catalogueSha256": candidate["catalogueSha256"],
        "datasetSha256": candidate["datasetSha256"],
        "rubricSha256": candidate["rubricSha256"],
        "splitManifestSha256": candidate["splitManifestSha256"],
        "selectedNaiveBayesVariant": candidate["modelType"],
    }
    if any(report.get(key) != value for key, value in report_bindings.items()):
        raise ValueError("evaluation report does not match the selected candidate")

    source_runtime = repository_root / "ai_pipeline/logic_oasis_ai/forum_ai"
    vendor_runtime = functions_root / "vendor/logic_oasis_ai/forum_ai"
    vendor_runtime.mkdir(parents=True, exist_ok=True)
    source_hashes: dict[str, str] = {}
    vendor_hashes: dict[str, str] = {}
    for name in RUNTIME_FILES:
        source = source_runtime / name
        destination = vendor_runtime / name
        shutil.copyfile(source, destination)
        source_hashes[name] = _hash(source)
        vendor_hashes[name] = _hash(destination)
    if source_hashes != vendor_hashes:
        raise ValueError("forum source/vendor runtime parity failed")

    bundle_path = functions_root / "vendor/bundle_manifest.json"
    bundle = _read_json(bundle_path) if bundle_path.exists() else {}
    bundle["forumRuntimeBundle"] = {
        "bundleSchemaVersion": "forum-runtime-bundle-v1",
        "files": vendor_hashes,
    }
    _write_json(bundle_path, bundle)

    artifact_path = functions_root / "forum_model.joblib"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact_source, artifact_path)
    dependencies = {name: importlib.metadata.version(name) for name in DEPENDENCIES}
    deployment_runtime_hashes = {
        name: _hash(repository_root / "functions" / name)
        for name in ("forum_runtime.py", "main.py")
    }
    revision_paths = (
        repository_root / "ai_pipeline/training/publish_forum_controlled_demo.py",
        repository_root / "functions/forum_runtime.py",
        repository_root / "functions/main.py",
        repository_root / "tools/deploy_forum_runtime_iam.py",
        repository_root / "tools/promote_controlled_demo_model.py",
        *(source_runtime / name for name in RUNTIME_FILES),
    )
    code_revision = _content_revision(repository_root, tuple(revision_paths))
    manifest = {
        "manifestSchemaVersion": "forum-model-release-manifest-v1",
        "releaseId": release_id,
        "releasedBy": released_by,
        "releasedAt": released_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "lifecycleStatus": "released", "isActive": True,
        "releaseRationale": release_rationale,
        "supersedesReleaseId": supersedes_release_id,
        "trainingDataProvenance": PROVENANCE,
        "evidenceLevel": EVIDENCE_LEVEL,
        "releaseScope": RELEASE_SCOPE,
        "deploymentScope": DEPLOYMENT_SCOPE,
        "claimLevel": CLAIM_LEVEL,
        "deploymentState": "pending_cloud_deployment",
        "candidateGateStatus": "passed", "failedGates": [],
        "modelType": candidate["modelType"], "modelVersion": candidate["modelVersion"],
        "artifactSha256": _hash(artifact_path), "artifactSizeBytes": artifact_path.stat().st_size,
        "catalogueSha256": candidate["catalogueSha256"],
        "datasetSha256": candidate["datasetSha256"],
        "datasetManifestSha256": _canonical_text_hash(dataset_manifest_path),
        "splitManifestSha256": candidate["splitManifestSha256"],
        "rubricSha256": candidate["rubricSha256"],
        "evaluationReportSha256": candidate["evaluationReportSha256"],
        "candidateManifestSha256": _canonical_text_hash(candidate_manifest_path),
        "preprocessingVersion": candidate["vectorizerContract"]["preprocessingVersion"],
        "vectorizerContract": candidate["vectorizerContract"],
        "abstentionPolicyVersion": candidate["abstentionPolicyVersion"],
        "outputContract": candidate["outputContract"],
        "semanticReproducibilityStatus": candidate["semanticReproducibilityStatus"],
        "runtimeEnvironmentFingerprint": candidate["runtimeEnvironmentFingerprint"],
        "baselineComparisonResult": report["baselineComparisonResult"],
        "dependencies": dependencies, "codeRevision": code_revision,
        "codeRevisionKind": "sha256_bounded_release_sources_v1",
        "deploymentRuntimeHashes": deployment_runtime_hashes,
        "sourceRuntimeHashes": source_hashes, "vendorRuntimeHashes": vendor_hashes,
        "bundleManifestSha256": _hash(bundle_path),
    }
    manifest_path = functions_root / "forum_model_manifest.json"
    _write_json(manifest_path, manifest)
    return PublishedForumRelease(artifact_path, manifest_path, bundle_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--functions-root", type=Path)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--released-by", required=True)
    parser.add_argument("--released-at", required=True)
    parser.add_argument("--supersedes-release-id")
    args = parser.parse_args()
    released_at = datetime.fromisoformat(args.released_at.replace("Z", "+00:00"))
    publish_forum_controlled_demo(
        repository_root=args.repository_root,
        functions_root=args.functions_root or args.repository_root / "functions",
        release_id=args.release_id, released_by=args.released_by, released_at=released_at,
        supersedes_release_id=args.supersedes_release_id,
    )


if __name__ == "__main__":
    main()
