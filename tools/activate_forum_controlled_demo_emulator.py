"""Activate the bundled forum release in a local Firestore Emulator only."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import firebase_admin
from firebase_admin import firestore


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "functions" / "forum_model_manifest.json"
EMULATOR_HOSTS = {"127.0.0.1:8080", "localhost:8080"}


def main() -> None:
    emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST", "")
    if emulator_host not in EMULATOR_HOSTS:
        raise SystemExit(
            "Refusing activation: set FIRESTORE_EMULATOR_HOST to "
            "127.0.0.1:8080 or localhost:8080."
        )
    project_id = os.environ.get("GCLOUD_PROJECT", "logic-oasis-fyp")
    if str(ROOT / "tools") not in sys.path:
        sys.path.insert(0, str(ROOT / "tools"))
    from promote_controlled_demo_model import (
        promote_forum_controlled_demo_model,
        validate_forum_controlled_demo_registry_document,
    )

    release = json.loads(MANIFEST.read_text(encoding="utf-8"))
    validate_forum_controlled_demo_registry_document(release)
    firebase_admin.initialize_app(options={"projectId": project_id})
    database = firestore.client()
    reference = database.collection("modelRegistry").document(release["releaseId"])
    existing = reference.get()
    if existing.exists:
        current = dict(existing.to_dict() or {})
        if current.get("isActive") is True and current.get("releaseId") == release["releaseId"]:
            print(f"Forum controlled release already active: {release['releaseId']}")
            return
        raise SystemExit(
            "The emulator contains an inactive or incompatible record for this immutable "
            "release ID. Restart with a clean Firestore Emulator before activating it."
        )
    promote_forum_controlled_demo_model(database, release)
    print(f"Activated forum controlled release: {release['releaseId']}")


if __name__ == "__main__":
    main()
