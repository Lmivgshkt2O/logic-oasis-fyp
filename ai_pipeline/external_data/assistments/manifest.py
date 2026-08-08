"""J1 manifest: auditable record of the normalized external release.

The manifest records source hashes, the strict 2022-2023 window, usage terms,
release metadata, output file hashes, and aggregate counts.  It never contains
raw learner identifiers, pseudonym key material, or local working paths.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from .assistments_contract import PROVENANCE, SOURCE_DATASET, WINDOW_END, WINDOW_START
from .schemas import EXTERNAL_ACTION_ROWS_SCHEMA_VERSION, SOURCE_WINDOW


MANIFEST_SCHEMA_VERSION = "assistments-external-manifest-v1"
USAGE_TERMS = "ASSISTments Data Terms of Use effective 2020-10-30"


def build_manifest(
    *,
    release_id: str,
    source_hashes: Mapping[str, str],
    counts: Mapping[str, Any],
    action_rows_path: str | Path,
) -> dict[str, Any]:
    """Construct the manifest without writing it (safe for tests)."""
    if not release_id:
        raise ValueError("release_id is required")
    if not source_hashes:
        raise ValueError("source file hashes are required")
    return {
        "manifestSchemaVersion": MANIFEST_SCHEMA_VERSION,
        "releaseId": release_id,
        "dataset": SOURCE_DATASET,
        "provenance": PROVENANCE,
        "actionRowsSchemaVersion": EXTERNAL_ACTION_ROWS_SCHEMA_VERSION,
        "sourceWindow": SOURCE_WINDOW,
        "sourceWindowStart": WINDOW_START.isoformat(),
        "sourceWindowEnd": WINDOW_END.isoformat(),
        "usageTerms": USAGE_TERMS,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceFilesSha256": dict(sorted(source_hashes.items())),
        "counts": dict(counts),
        "fileSha256": {
            Path(action_rows_path).name: _file_sha256(Path(action_rows_path)),
        },
        "containsRawIdentifiers": False,
        "containsSecretMaterial": False,
        "redistributionProhibited": True,
        "deAnonymizationProhibited": True,
    }


def write_manifest(manifest: Mapping[str, Any], path: str | Path) -> Path:
    """Validate and write the manifest; returns the path."""
    validate_manifest(manifest)
    destination = Path(path)
    destination.write_text(json.dumps(dict(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    """Fail-closed structural validation of a manifest."""
    if manifest.get("manifestSchemaVersion") != MANIFEST_SCHEMA_VERSION:
        raise ValueError("manifest schema version is not assistments-external-manifest-v1")
    if manifest.get("provenance") != PROVENANCE:
        raise ValueError("manifest provenance must be external_real")
    if manifest.get("dataset") != SOURCE_DATASET:
        raise ValueError("manifest dataset must be assistments_edm_cup_2023")
    if manifest.get("sourceWindow") != SOURCE_WINDOW:
        raise ValueError("manifest source window must be 2022-01-01/2023-12-31")
    if not manifest.get("releaseId"):
        raise ValueError("manifest releaseId is required")
    if not isinstance(manifest.get("sourceFilesSha256"), dict) or not manifest["sourceFilesSha256"]:
        raise ValueError("manifest sourceFilesSha256 is required")
    if manifest.get("containsRawIdentifiers") is not False:
        raise ValueError("manifest must declare containsRawIdentifiers false")
    if manifest.get("containsSecretMaterial") is not False:
        raise ValueError("manifest must declare containsSecretMaterial false")
    if not isinstance(manifest.get("fileSha256"), dict) or not manifest["fileSha256"]:
        raise ValueError("manifest output file hashes are required")


def _file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

