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
CONFIGS = ("feature_schema.yaml", "adaptive_policy_v1.yaml", "weak_topic_ranking_v1.yaml")


def _file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _tree_sha(path: Path) -> str:
    digest = sha256()
    for file in sorted(item for item in path.rglob("*") if item.is_file() and "__pycache__" not in item.parts):
        digest.update(file.relative_to(path).as_posix().encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()


def build_bundle() -> dict[str, object]:
    target_package = VENDOR / "logic_oasis_ai"
    target_configs = VENDOR / "configs"
    if target_package.exists():
        shutil.rmtree(target_package)
    shutil.copytree(PACKAGE, target_package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    target_configs.mkdir(parents=True, exist_ok=True)
    for filename in CONFIGS:
        shutil.copy2(SOURCE / "configs" / filename, target_configs / filename)
    manifest = {
        "bundleVersion": "u8-ai-runtime-v1",
        "packageSha256": _tree_sha(PACKAGE),
        "featureSchemaSha256": _file_sha(SOURCE / "configs" / "feature_schema.yaml"),
        "adaptivePolicySha256": _file_sha(SOURCE / "configs" / "adaptive_policy_v1.yaml"),
        "weakTopicRankingPolicySha256": _file_sha(SOURCE / "configs" / "weak_topic_ranking_v1.yaml"),
    }
    (VENDOR / "bundle_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(build_bundle(), sort_keys=True))
