"""Controlled retention workflow for a governed real-data release.

This module does not delete Cloud Storage objects or Secret Manager versions
itself.  The retention service performs those privileged operations only after
this deterministic certificate has been written and steward verification is
recorded by the invoking admin workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from shutil import rmtree

from .export_real_attempts import PROTECTED_RELEASE_PREFIX


DELETION_CERTIFICATE_VERSION = "real-data-deletion-certificate-v1"
RETENTION_IDENTITY = "logic-oasis-data-retention@logic-oasis-fyp.iam.gserviceaccount.com"


@dataclass(frozen=True)
class ReleaseDeletionRequest:
    release_id: str
    storage_path: str
    export_key_version: str
    data_steward: str
    retention_actor: str
    retention_review_at: datetime

    def __post_init__(self) -> None:
        if not all((self.release_id, self.storage_path, self.export_key_version, self.data_steward, self.retention_actor)):
            raise ValueError("release deletion request fields are required")
        if self.storage_path != f"{PROTECTED_RELEASE_PREFIX}{self.release_id}/":
            raise ValueError("deletion may target only its protected release path")
        if not self.export_key_version.startswith("logic-oasis-export-pseudonymization-key-v"):
            raise ValueError("deletion must name the versioned export HMAC key")
        if self.retention_actor != RETENTION_IDENTITY:
            raise ValueError("only the declared retention identity may perform release cleanup")
        if self.retention_review_at.tzinfo is None:
            raise ValueError("retention_review_at must include a timezone")


@dataclass(frozen=True)
class StorageDeletionEvidence:
    """Verified result of deleting the protected release objects."""

    storage_path: str
    operation_id: str
    object_count: int
    completed_at: datetime
    verified_by: str

    def __post_init__(self) -> None:
        if not self.storage_path.startswith(PROTECTED_RELEASE_PREFIX):
            raise ValueError("deletion evidence must name a protected release path")
        if not self.operation_id or not self.verified_by:
            raise ValueError("deletion evidence operation and verifier are required")
        if isinstance(self.object_count, bool) or not isinstance(self.object_count, int) or self.object_count < 0:
            raise ValueError("deletion evidence object_count must be a non-negative integer")
        if self.completed_at.tzinfo is None:
            raise ValueError("deletion evidence completed_at must include a timezone")

    def to_document(self) -> dict[str, object]:
        return {
            "storagePath": self.storage_path,
            "operationId": self.operation_id,
            "objectCount": self.object_count,
            "completedAt": self.completed_at.isoformat(),
            "verifiedBy": self.verified_by,
        }


def create_deletion_certificate(
    request: ReleaseDeletionRequest,
    *,
    manifest: dict[str, object],
    storage_deletion_evidence: StorageDeletionEvidence | None = None,
) -> dict[str, object]:
    """Return safe evidence that must exist before key-version destruction."""
    _validate_manifest_for_deletion(request, manifest)
    if storage_deletion_evidence is None:
        raise ValueError("verified storage deletion evidence is required")
    if storage_deletion_evidence.storage_path != request.storage_path:
        raise ValueError("deletion evidence does not match request storage path")
    payload = {
        "certificateVersion": DELETION_CERTIFICATE_VERSION,
        "releaseId": request.release_id,
        "storagePath": request.storage_path,
        "exportKeyVersion": request.export_key_version,
        "dataSteward": request.data_steward,
        "retentionActor": request.retention_actor,
        "retentionReviewAt": request.retention_review_at.isoformat(),
        "deletedAt": storage_deletion_evidence.completed_at.isoformat(),
        "storageDeletion": storage_deletion_evidence.to_document(),
        "manifestSha256": sha256(json.dumps(manifest, sort_keys=True).encode("utf-8")).hexdigest(),
        "keyDestructionAuthorized": True,
    }
    return payload


def write_deletion_certificate(certificate: dict[str, object], path: str | Path) -> Path:
    """Write a safe certificate; callers must store it in protected custody."""
    _validate_certificate(certificate)
    destination = Path(path)
    destination.write_text(json.dumps(certificate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def may_destroy_key_version(certificate: dict[str, object], *, release_id: str, export_key_version: str) -> bool:
    """Fail closed unless deletion evidence matches this release and key."""
    _validate_certificate(certificate)
    return (
        certificate["releaseId"] == release_id
        and certificate["exportKeyVersion"] == export_key_version
        and certificate["keyDestructionAuthorized"] is True
    )


def cleanup_unpublished_release(
    request: ReleaseDeletionRequest,
    output_directory: str | Path,
) -> tuple[str, ...]:
    """Remove a manifest-less partial export before retrying its release path.

    This is deliberately separate from deletion certification: a directory
    without its manifest was never published as a governed release. Deployment
    must invoke it only under the retention service identity declared in the
    IAM contract.
    """
    output = Path(output_directory)
    manifest = output / "manifest.json"
    if manifest.exists():
        raise ValueError("a published release requires its deletion certificate workflow")
    removed: list[str] = []
    for path in (output / "attempts.csv", output / "responses.csv"):
        if path.exists():
            path.unlink()
            removed.append(path.name)
    for staging in output.glob(".release-staging-*"):
        if staging.is_dir():
            rmtree(staging)
            removed.append(staging.name)
    return tuple(removed)


def _validate_manifest_for_deletion(request: ReleaseDeletionRequest, manifest: dict[str, object]) -> None:
    if manifest.get("releaseId") != request.release_id:
        raise ValueError("deletion request does not match manifest release")
    if manifest.get("storagePath") != request.storage_path:
        raise ValueError("deletion request does not match manifest storage path")
    if manifest.get("exportKeyVersion") != request.export_key_version:
        raise ValueError("deletion request does not match manifest export key version")
    if manifest.get("dataSteward") != request.data_steward:
        raise ValueError("deletion request does not match manifest steward")


def _validate_certificate(certificate: dict[str, object]) -> None:
    required = ("certificateVersion", "releaseId", "storagePath", "exportKeyVersion", "dataSteward", "retentionActor", "deletedAt", "manifestSha256", "keyDestructionAuthorized")
    if any(not certificate.get(field) for field in required[:-1]):
        raise ValueError("deletion certificate is incomplete")
    if certificate.get("certificateVersion") != DELETION_CERTIFICATE_VERSION:
        raise ValueError("unsupported deletion certificate version")
    if certificate.get("keyDestructionAuthorized") is not True:
        raise ValueError("deletion certificate does not authorize key destruction")
    deletion = certificate.get("storageDeletion")
    if not isinstance(deletion, dict):
        raise ValueError("deletion certificate lacks storage deletion evidence")
    required_deletion_fields = ("storagePath", "operationId", "objectCount", "completedAt", "verifiedBy")
    if any(not deletion.get(field) for field in required_deletion_fields if field != "objectCount"):
        raise ValueError("deletion certificate has incomplete storage deletion evidence")
    if deletion.get("storagePath") != certificate.get("storagePath"):
        raise ValueError("deletion certificate storage evidence path does not match")
    if isinstance(deletion.get("objectCount"), bool) or not isinstance(deletion.get("objectCount"), int):
        raise ValueError("deletion certificate storage evidence object count is invalid")
