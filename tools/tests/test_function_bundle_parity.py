from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "ai_pipeline"))
import build_function_bundle
from logic_oasis_ai.model_registry import SHA256_PATTERN
from build_function_bundle import (
    BUNDLE_VERSION,
    CONFIGS,
    expected_bundle_manifest,
    PACKAGE,
    VENDOR,
)


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
        expected = expected_bundle_manifest(
            include_forum_runtime="forumRuntimeBundle" in stored,
        )
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
        self.assertEqual(metadata["artifact_contract"], "logic-oasis-controlled-demo-release-evidence/v1")
        self.assertEqual(metadata["release_status"], "developer_released")
        self.assertEqual(metadata["live_activation_status"], "verified")
        self.assertEqual(metadata["live_quiz_verification_status"], "passed_and_cleaned_up")
        self.assertTrue(metadata["deployment_observation"]["disposableQuiz"]["cleanupVerified"])
        self.assertEqual(
            metadata["catalogue_declaration_reference"],
            "developer-declaration-cdm-catalog-v1",
        )
        release = metadata["release_declaration"]
        self.assertEqual(release["releaseId"], "CDM-2026-001")
        self.assertEqual(release["releasedBy"], "zyonn")
        self.assertEqual(release["releasedAt"].isoformat(), "2026-07-27T00:00:00+08:00")
        self.assertEqual(release["releaseScope"], "fyp1_controlled_demo")
        self.assertEqual(release["trainingDataProvenance"], "expert_authored_controlled_demo")
        self.assertEqual(release["evidenceLevel"], "controlled_demonstration")
        self.assertEqual(release["deploymentScope"], "controlled_demo")
        self.assertIn("not real-world validated", release["releaseRationale"])
        self.assertFalse(metadata["contains_scenario_content"])
        self.assertIsInstance(metadata["bindings"], dict)
        self.assertEqual(BUNDLE_VERSION, metadata["bindings"]["bundleVersion"])
        self.assertTrue(all(
            isinstance(value, str) and SHA256_PATTERN.fullmatch(value)
            for key, value in metadata["bindings"].items()
            if key.endswith("Sha256")
        ))
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

    def test_historical_release_evidence_keeps_complete_immutable_bindings(self) -> None:
        evidence = RELEASE_EVIDENCE.read_text(encoding="utf-8")
        metadata = yaml.safe_load(evidence.split("---", 2)[1])
        bindings = metadata["bindings"]
        self.assertEqual({
            "bundleVersion", "modelVersion", "packageSha256", "artifactSha256",
            "publicationManifestSha256", "deploymentManifestSha256",
            "trainingDatasetVersion", "trainingDatasetSha256", "scenarioCatalogueSha256",
            "controlledDemoConfigSha256", "evaluationReportSha256", "featureSchemaVersion",
            "featureSchemaSha256", "weakTopicRankingPolicySha256", "adaptivePolicySha256",
            "predictionTarget", "labelVersion", "evidenceLevel", "deploymentScope",
        }, set(bindings))
        self.assertEqual(
            "gs://logic-oasis-models/controlled-demo/controlled-demo-xgboost-v1/model.ubj",
            metadata["runtime"]["artifact_uri"],
        )
        self.assertEqual(
            "gs://logic-oasis-models/controlled-demo/controlled-demo-xgboost-v1/manifest.json",
            metadata["runtime"]["manifest_uri"],
        )
        lock = (ROOT / "ai_pipeline" / "requirements-controlled-demo.lock").read_text(encoding="utf-8")
        for package, version in metadata["toolchain"].items():
            if package not in {"python", "platform"}:
                self.assertIn(f"{package}=={version}", lock)
        self.assertEqual("3.11.9", str(metadata["toolchain"]["python"]))
        self.assertTrue(str(metadata["toolchain"]["platform"]).startswith("Windows-"))
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
