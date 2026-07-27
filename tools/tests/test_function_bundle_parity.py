from __future__ import annotations

import json
from hashlib import sha256
from importlib.metadata import version as installed_version
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "ai_pipeline"))
import build_function_bundle
from build_function_bundle import (
    BUNDLE_VERSION,
    CONFIGS,
    CONFIG_HASH_FILES,
    PACKAGE,
    VENDOR,
    file_sha256,
    tree_sha256,
)
from deploy_controlled_demo_model import build_deployment_manifest_bytes
from logic_oasis_ai.model_registry import controlled_demo_object_paths
from training.publish_controlled_demo_bundle import publish_controlled_demo_bundle
from training.train_controlled_demo_xgboost import train_controlled_demo_xgboost


RELEASE_EVIDENCE = ROOT / "docs" / "evidence" / "2026-07-24-controlled-demo-xgboost-release.md"


def _files_below(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


class FunctionBundleParityTests(unittest.TestCase):
    def test_builder_removes_stale_package_and_config_files(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            package = source / "logic_oasis_ai"
            configs = source / "configs"
            vendor = root / "vendor"
            package.mkdir(parents=True)
            configs.mkdir()
            (package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
            for filename in CONFIGS:
                (configs / filename).write_text(f"name: {filename}\n", encoding="utf-8")
            (vendor / "logic_oasis_ai").mkdir(parents=True)
            (vendor / "logic_oasis_ai" / "stale.py").write_text("stale\n", encoding="utf-8")
            (vendor / "configs").mkdir()
            (vendor / "configs" / "stale.yaml").write_text("stale: true\n", encoding="utf-8")

            with (
                patch.object(build_function_bundle, "SOURCE", source),
                patch.object(build_function_bundle, "PACKAGE", package),
                patch.object(build_function_bundle, "VENDOR", vendor),
            ):
                manifest = build_function_bundle.build_bundle()

            self.assertFalse((vendor / "logic_oasis_ai" / "stale.py").exists())
            self.assertFalse((vendor / "configs" / "stale.yaml").exists())
            self.assertEqual({"module.py"}, set(_files_below(vendor / "logic_oasis_ai")))
            self.assertEqual(set(CONFIGS), set(_files_below(vendor / "configs")))
            self.assertEqual(BUNDLE_VERSION, manifest["bundleVersion"])

    def test_generated_manifest_matches_authoritative_sources(self) -> None:
        stored = json.loads((ROOT / "functions" / "vendor" / "bundle_manifest.json").read_text(encoding="utf-8"))
        expected = {
            "bundleVersion": BUNDLE_VERSION,
            "packageSha256": tree_sha256(PACKAGE),
            **{
                manifest_key: file_sha256(ROOT / "ai_pipeline" / "configs" / filename)
                for manifest_key, filename in CONFIG_HASH_FILES.items()
            },
        }
        self.assertEqual(expected, stored)

    def test_vendored_package_and_configs_are_byte_identical_without_stale_files(self) -> None:
        source_package = _files_below(PACKAGE)
        vendored_package = _files_below(VENDOR / "logic_oasis_ai")
        self.assertEqual(source_package, vendored_package)
        vendored_configs = _files_below(VENDOR / "configs")
        self.assertEqual(set(CONFIGS), set(vendored_configs))
        for filename in CONFIGS:
            self.assertEqual(
                (ROOT / "ai_pipeline" / "configs" / filename).read_bytes(),
                vendored_configs[filename],
            )
        self.assertIn("native_xgboost.py", vendored_package)
        forbidden_model_suffixes = {".pkl", ".joblib", ".ubj"}
        self.assertFalse(
            any(Path(name).suffix in forbidden_model_suffixes for name in _files_below(VENDOR))
        )

    def test_release_evidence_binds_the_selected_bundle_and_safe_claim_boundary(self) -> None:
        evidence = RELEASE_EVIDENCE.read_text(encoding="utf-8")
        metadata = yaml.safe_load(evidence.split("---", 2)[1])
        manifest = json.loads((VENDOR / "bundle_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["artifact_contract"], "logic-oasis-controlled-demo-release-evidence/v1")
        self.assertEqual(metadata["release_status"], "release_candidate")
        self.assertEqual(metadata["live_activation_status"], "pending")
        self.assertEqual(metadata["mechanism_approval_reference"], "supervisor-review-cdm-catalog-v1")
        self.assertEqual(metadata["model_activation_approval_status"], "pending")
        self.assertFalse(metadata["contains_scenario_content"])
        self.assertIsInstance(metadata["bindings"], dict)
        for key, value in manifest.items():
            self.assertEqual(metadata["bindings"][key], value)
        self.assertEqual(metadata["runtime"]["evidence_mode"], "controlled_demo")
        self.assertEqual(metadata["runtime"]["model_bucket"], "logic-oasis-models")
        self.assertEqual(metadata["claim_level"], "controlled_demonstration_only")
        self.assertIn("not real-world validated", evidence)
        catalogue = yaml.safe_load(
            (ROOT / "ai_pipeline" / "controlled_demo" / "scenario_catalog_v1.yaml").read_text(encoding="utf-8")
        )
        scenario_identifiers: set[str] = set()
        for family in catalogue["scenarioFamilies"]:
            scenario_identifiers.update((family["scenarioFamilyId"], family["fictionalProfileId"]))
            for attempt in family["attempts"]:
                scenario_identifiers.add(attempt["attemptId"])
                scenario_identifiers.update(attempt["questionIds"])
        self.assertFalse([value for value in scenario_identifiers if value in evidence])

    def test_release_evidence_reproduces_every_selected_candidate_binding(self) -> None:
        evidence = RELEASE_EVIDENCE.read_text(encoding="utf-8")
        metadata = yaml.safe_load(evidence.split("---", 2)[1])
        bindings = metadata["bindings"]
        with TemporaryDirectory() as temporary:
            published = publish_controlled_demo_bundle(
                train_controlled_demo_xgboost(),
                temporary,
            )
        deployment_bytes = build_deployment_manifest_bytes(published.manifest)
        artifact_uri, manifest_uri = controlled_demo_object_paths(
            f"gs://{metadata['runtime']['model_bucket']}",
            published.manifest["modelVersion"],
        )
        expected = {
            "bundleVersion": BUNDLE_VERSION,
            "modelVersion": published.manifest["modelVersion"],
            "packageSha256": tree_sha256(PACKAGE),
            "artifactSha256": published.manifest["artifactSha256"],
            "publicationManifestSha256": published.manifest_sha256,
            "deploymentManifestSha256": sha256(deployment_bytes).hexdigest(),
            "trainingDatasetVersion": published.manifest["trainingDatasetVersion"],
            "trainingDatasetSha256": published.manifest["trainingDatasetSha256"],
            "scenarioCatalogueSha256": published.manifest["scenarioCatalogueSha256"],
            "controlledDemoConfigSha256": published.manifest["controlledDemoConfigSha256"],
            "evaluationReportSha256": published.manifest["evaluationReportSha256"],
            "featureSchemaVersion": published.manifest["featureSchemaVersion"],
            "featureSchemaSha256": published.manifest["featureSchemaSha256"],
            "weakTopicRankingPolicySha256": file_sha256(
                ROOT / "ai_pipeline" / "configs" / "weak_topic_ranking_v1.yaml"
            ),
            "adaptivePolicySha256": file_sha256(
                ROOT / "ai_pipeline" / "configs" / "adaptive_policy_v1.yaml"
            ),
            "predictionTarget": published.manifest["targetName"],
            "labelVersion": published.manifest["labelVersion"],
            "evidenceLevel": published.manifest["evidenceLevel"],
            "deploymentScope": published.manifest["deploymentScope"],
        }
        self.assertEqual(set(expected), set(bindings))
        for key, value in expected.items():
            self.assertEqual(value, bindings[key], key)
        self.assertEqual(artifact_uri, metadata["runtime"]["artifact_uri"])
        self.assertEqual(manifest_uri, metadata["runtime"]["manifest_uri"])
        lock = (ROOT / "ai_pipeline" / "requirements-controlled-demo.lock").read_text(encoding="utf-8")
        for package, version in metadata["toolchain"].items():
            if package not in {"python", "platform"}:
                self.assertIn(f"{package}=={version}", lock)
                self.assertEqual(str(version), installed_version(package), package)
        self.assertEqual(str(metadata["toolchain"]["python"]), platform.python_version())
        self.assertEqual(metadata["toolchain"]["platform"], platform.platform())
        expected_shap = [
            {
                key: sample[key]
                for key in ("riskTier", "supportRisk", "reconstructedRisk", "absoluteError")
            }
            for sample in published.shap_integrity
        ]
        self.assertEqual(expected_shap, metadata["shap_samples"])
        table_shap = []
        for line in evidence.splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) == 4 and cells[0] in {"Low", "Medium", "High"}:
                table_shap.append({
                    "riskTier": cells[0].lower(),
                    "supportRisk": float(cells[1]),
                    "reconstructedRisk": float(cells[2]),
                    "absoluteError": float(cells[3]),
                })
        self.assertEqual(metadata["shap_samples"], table_shap)


if __name__ == "__main__":
    unittest.main()
