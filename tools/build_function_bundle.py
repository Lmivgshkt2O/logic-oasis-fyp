"""Build the deployable U8 Functions vendor bundle from authoritative sources."""

from __future__ import annotations

import json
import shutil
from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ai_pipeline"
VENDOR = ROOT / "functions" / "vendor"
PACKAGE = SOURCE / "logic_oasis_ai"
BUNDLE_VERSION = "u8-ai-runtime-v1"
CONFIG_HASH_FILES = {
    "featureSchemaSha256": "feature_schema.yaml",
    "adaptivePolicySha256": "adaptive_policy_v1.yaml",
    "weakTopicRankingPolicySha256": "weak_topic_ranking_v1.yaml",
}
CONFIGS = tuple(CONFIG_HASH_FILES.values())


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def tree_sha256(path: Path) -> str:
    digest = sha256()
    for file in sorted(item for item in path.rglob("*") if item.is_file() and "__pycache__" not in item.parts):
        digest.update(file.relative_to(path).as_posix().encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()


def expected_bundle_manifest(*, include_forum_runtime: bool) -> dict[str, object]:
    """Build the authoritative source-bound Functions bundle manifest."""
    manifest: dict[str, object] = {
        "bundleVersion": BUNDLE_VERSION,
        "packageSha256": tree_sha256(PACKAGE),
        **{
            manifest_key: file_sha256(SOURCE / "configs" / filename)
            for manifest_key, filename in CONFIG_HASH_FILES.items()
        },
    }
    if include_forum_runtime:
        manifest["forumRuntimeBundle"] = {
            "bundleSchemaVersion": "forum-runtime-bundle-v1",
            "files": {
                name: file_sha256(PACKAGE / "forum_ai" / name)
                for name in ("__init__.py", "classifier.py")
            },
        }
    return manifest


def build_bundle() -> dict[str, object]:
    manifest_path = VENDOR / "bundle_manifest.json"
    existing = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.is_file()
        else {}
    )
    target_package = VENDOR / "logic_oasis_ai"
    target_configs = VENDOR / "configs"
    if target_package.exists():
        shutil.rmtree(target_package)
    if target_configs.exists():
        shutil.rmtree(target_configs)
    shutil.copytree(PACKAGE, target_package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    target_configs.mkdir(parents=True, exist_ok=True)
    for filename in CONFIGS:
        shutil.copy2(SOURCE / "configs" / filename, target_configs / filename)
    manifest = expected_bundle_manifest(
        include_forum_runtime="forumRuntimeBundle" in existing,
    )
    manifest_path.write_bytes(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    return manifest


if __name__ == "__main__":
    print(json.dumps(build_bundle(), sort_keys=True))
