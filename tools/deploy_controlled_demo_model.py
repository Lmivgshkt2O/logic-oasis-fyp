"""Upload and activate a supervisor-approved CDM-2 bundle in one model bucket."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import firebase_admin
from firebase_admin import firestore, storage

ROOT = Path(__file__).resolve().parents[1]
AI_ROOT = ROOT / "ai_pipeline"
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from build_function_bundle import file_sha256, tree_sha256
from logic_oasis_ai.model_registry import (
    controlled_demo_object_paths,
    validate_model_bucket_uri as validate_model_bucket,
)
from logic_oasis_ai.time_utils import parse_timestamp
from promote_controlled_demo_model import promote_controlled_demo_model
from training.publish_controlled_demo_bundle import load_controlled_demo_bundle


@dataclass(frozen=True)
class SupervisorApproval:
    approval_id: str
    approved_by: str
    approved_at: datetime
    rationale: str


def build_controlled_demo_registry_document(
    manifest: Mapping[str, object],
    *,
    model_bucket: str,
    approval: SupervisorApproval,
    manifest_sha256: str,
) -> dict[str, object]:
    artifact_path, manifest_path = controlled_demo_object_paths(model_bucket, str(manifest.get("modelVersion", "")))
    runtime_bindings = _runtime_manifest_bindings(manifest)
    document = {
        "artifactId": f"xgboost-{manifest['modelVersion']}",
        "modelType": manifest["modelType"],
        "modelVersion": manifest["modelVersion"],
        "artifactPath": artifact_path,
        "artifactManifestPath": manifest_path,
        "artifactSha256": manifest["artifactSha256"],
        "artifactManifestSha256": manifest_sha256,
        "featureSchemaVersion": manifest["featureSchemaVersion"],
        "featureSchemaSha256": manifest["featureSchemaSha256"],
        "packageSha256": runtime_bindings["packageSha256"],
        "weakTopicRankingPolicySha256": runtime_bindings["weakTopicRankingPolicySha256"],
        "adaptivePolicySha256": runtime_bindings["adaptivePolicySha256"],
        "trainingDatasetVersion": manifest["trainingDatasetVersion"],
        "trainingDatasetSha256": manifest["trainingDatasetSha256"],
        "predictionTarget": runtime_bindings["predictionTarget"],
        "labelVersion": manifest["labelVersion"],
        "masteryCriterion": manifest["masteryCriterion"],
        "evaluationStatus": manifest["evaluationStatus"],
        "evaluationReportSha256": manifest["evaluationReportSha256"],
        "promotionGateStatus": "passed",
        "lifecycleStatus": "promoted",
        "isActive": True,
        "approvalId": approval.approval_id,
        "approvedBy": approval.approved_by,
        "approvedAt": approval.approved_at,
        "approvalRationale": approval.rationale,
        "trainingDataProvenance": manifest["trainingDataProvenance"],
        "evidenceLevel": manifest["evidenceLevel"],
        "approvalScope": "fyp1_controlled_demo",
        "deploymentScope": manifest["deploymentScope"],
        "scenarioCatalogueSha256": manifest["scenarioCatalogueSha256"],
        "controlledDemoConfigSha256": manifest["controlledDemoConfigSha256"],
    }
    return document


def _runtime_manifest_bindings(manifest: Mapping[str, object]) -> dict[str, object]:
    return {
        "packageSha256": tree_sha256(AI_ROOT / "logic_oasis_ai"),
        "weakTopicRankingPolicySha256": file_sha256(AI_ROOT / "configs" / "weak_topic_ranking_v1.yaml"),
        "adaptivePolicySha256": file_sha256(AI_ROOT / "configs" / "adaptive_policy_v1.yaml"),
        "predictionTarget": manifest["targetName"],
    }


def build_deployment_manifest_bytes(manifest: Mapping[str, object]) -> bytes:
    """Return the canonical runtime-bound manifest bytes used for upload and hashing."""
    deployment_manifest = {**manifest, **_runtime_manifest_bindings(manifest)}
    return (json.dumps(deployment_manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")


def deploy_controlled_demo_model(
    *,
    database: Any,
    bucket: Any,
    model_bucket: str,
    artifact_path: str | Path,
    manifest_path: str | Path,
    approval: SupervisorApproval,
    promoted_at: datetime | None = None,
) -> Mapping[str, object]:
    """Verify, upload, re-verify, then atomically switch the registry record."""
    bucket_name = validate_model_bucket(model_bucket)
    if getattr(bucket, "name", bucket_name) != bucket_name:
        raise ValueError("storage bucket does not match the approved model bucket")
    artifact_source = Path(artifact_path)
    manifest_source = Path(manifest_path)
    _, manifest = load_controlled_demo_bundle(artifact_source, manifest_source)
    artifact_uri, manifest_uri = controlled_demo_object_paths(model_bucket, str(manifest["modelVersion"]))
    artifact_object = artifact_uri.removeprefix(f"gs://{bucket_name}/")
    manifest_object = manifest_uri.removeprefix(f"gs://{bucket_name}/")
    artifact_bytes = artifact_source.read_bytes()
    manifest_bytes = build_deployment_manifest_bytes(manifest)
    for object_name, expected in (
        (artifact_object, artifact_bytes),
        (manifest_object, manifest_bytes),
    ):
        blob = bucket.blob(object_name)
        try:
            blob.upload_from_string(expected, if_generation_match=0)
        except Exception:
            uploaded = blob.download_as_bytes()
            if uploaded != expected:
                raise
        else:
            uploaded = blob.download_as_bytes()
        if uploaded != expected:
            raise ValueError("uploaded controlled-demo bundle failed byte verification")
    timestamp = promoted_at or datetime.now(timezone.utc)
    document = build_controlled_demo_registry_document(
        manifest,
        model_bucket=model_bucket,
        approval=approval,
        manifest_sha256=sha256(manifest_bytes).hexdigest(),
    )
    return promote_controlled_demo_model(database, document, now=timestamp)


def _timestamp(value: str) -> datetime:
    try:
        return parse_timestamp(value, "approved-at")
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy one approved controlled-demo XGBoost bundle")
    parser.add_argument("--project", required=True)
    parser.add_argument("--model-bucket", required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--approval-id", required=True)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--approved-at", type=_timestamp, required=True)
    parser.add_argument("--approval-rationale", required=True)
    args = parser.parse_args()
    bucket_name = validate_model_bucket(args.model_bucket)
    app = firebase_admin.initialize_app(options={"projectId": args.project, "storageBucket": bucket_name})
    result = deploy_controlled_demo_model(
        database=firestore.client(app),
        bucket=storage.bucket(bucket_name, app=app),
        model_bucket=args.model_bucket,
        artifact_path=args.artifact,
        manifest_path=args.manifest,
        approval=SupervisorApproval(args.approval_id, args.approved_by, args.approved_at, args.approval_rationale),
    )
    print(f"Activated controlled-demo artifact: {result['artifactId']}")


if __name__ == "__main__":
    main()
