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

from .export_real_attempts import PROTECTED_RELEASE_PREFIX


DELETION_CERTIFICATE_VERSION = "real-data-deletion-certificate-v1"


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
        if self.retention_review_at.tzinfo is None:
            raise ValueError("retention_review_at must include a timezone")


def create_deletion_certificate(
    request: ReleaseDeletionRequest,
    *,
    manifest: dict[str, object],
    deleted_at: datetime | None = None,
) -> dict[str, object]:
    """Return safe evidence that must exist before key-version destruction."""
    _validate_manifest_for_deletion(request, manifest)
    timestamp = deleted_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("deleted_at must include a timezone")
    payload = {
        "certificateVersion": DELETION_CERTIFICATE_VERSION,
        "releaseId": request.release_id,
        "storagePath": request.storage_path,
        "exportKeyVersion": request.export_key_version,
        "dataSteward": request.data_steward,
        "retentionActor": request.retention_actor,
        "retentionReviewAt": request.retention_review_at.isoformat(),
        "deletedAt": timestamp.isoformat(),
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
