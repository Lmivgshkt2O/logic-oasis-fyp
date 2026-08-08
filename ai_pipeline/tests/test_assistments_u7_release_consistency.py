"""J6 release-consistency tests for the final U7 external-real-data evidence.

Pure checks run everywhere; manifest cross-checks run only when the protected
external-data directory is present.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
import unittest

from external_data.assistments.j2_contract import (
    J2_CONTRACT_VERSION_V2,
    MASTERY_CRITERION,
    load_j2_contract,
    validate_j2_contract_v2,
)
from external_data.assistments.schemas import SOURCE_WINDOW


REPO = Path(__file__).resolve().parents[2]
PROTECTED_ROOT = Path(r"C:\Users\zyonn\Documents\FYP\logic_oasis_private_data\assitments_edm_cup_2023")
V2_DIR = PROTECTED_ROOT / "processed" / "v2"
REPORTS = REPO / "ai_pipeline" / "reports"
EVIDENCE = REPO / "docs" / "evidence"
RAW_IDENTIFIER_PATTERN = re.compile(r"assistments_student_[0-9a-f]{64}")


class ContractConsistencyTests(unittest.TestCase):
    def test_final_authoritative_contract(self):
        contract = validate_j2_contract_v2(
            load_j2_contract(REPO / "ai_pipeline" / "external_data" / "assistments" / "assistments_j2_contract_v2.yaml")
        )
        self.assertEqual(contract["contractVersion"], J2_CONTRACT_VERSION_V2)
        self.assertEqual(contract["masteryCriterionAndTarget"]["masteryCriterion"], 0.60)
        self.assertEqual(contract["featureConstruction"]["baseFeatures"], ["correct_rate", "mean_response_time_ms"])
        self.assertEqual(contract["provenancePrivacy"]["provenance"], "external_real")
        self.assertEqual(contract["primaryCohort"]["sourceGrade"], "6")

    def test_frozen_constants(self):
        self.assertEqual(MASTERY_CRITERION, 0.60)
        self.assertEqual(SOURCE_WINDOW, "2022-01-01/2023-12-31")


class ReportConsistencyTests(unittest.TestCase):
    def test_final_reports_exist_and_preserve_conclusions(self):
        j4 = (REPORTS / "u7_assistments_j4_model_comparison.md").read_text(encoding="utf-8")
        j5 = (REPORTS / "u7_assistments_j5_architecture_evidence.md").read_text(encoding="utf-8")
        self.assertIn("MODEL COMPARISON COMPLETED", j4)
        self.assertIn("NO STABLE ADVANTAGE", j4.upper())
        self.assertIn("evidence_only_external", j4)
        self.assertIn("BKT ablation status: completed", j5)
        self.assertIn("evidence_only_external", j5)
        release = (EVIDENCE / "u7-assistments-external-real-data-release.md").read_text(encoding="utf-8")
        self.assertIn("NO STABLE IMPROVEMENT", release.upper())

    def test_final_model_comparison_report_has_recorded_result(self):
        report = (REPORTS / "model_comparison.md").read_text(encoding="utf-8")
        self.assertNotIn("no final model-performance result", report.lower())
        self.assertIn("external", report.lower())
        self.assertIn("MODEL COMPARISON COMPLETED", report.upper())

    def test_no_raw_identifiers_in_repository_artifacts(self):
        for path in REPORTS.glob("u7_assistments_j4_model_comparison.md"):
            self.assertIsNone(RAW_IDENTIFIER_PATTERN.search(path.read_text(encoding="utf-8")), path)
        for path in REPORTS.glob("u7_assistments_j5_architecture_evidence.md"):
            self.assertIsNone(RAW_IDENTIFIER_PATTERN.search(path.read_text(encoding="utf-8")), path)

    def test_no_learner_level_datasets_are_tracked_in_git(self):
        tracked = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        for forbidden in (
            "external_action_rows",
            "external_skill_attempts",
            "external_labels",
            "u7_model_table",
            "u7_audit_table",
        ):
            self.assertNotIn(forbidden, tracked)

    def test_external_runners_never_promote(self):
        for name in ("run_j4.py", "run_j5.py"):
            text = (REPO / "ai_pipeline" / "external_data" / "assistments" / name).read_text(encoding="utf-8")
            self.assertNotIn("ModelRegistry", text)
            self.assertNotIn("registry.", text)


@unittest.skipUnless((V2_DIR / "u7_v2_readiness_manifest.json").exists(), "protected manifests not present")
class ManifestCrossCheckTests(unittest.TestCase):
    def test_manifests_are_mutually_consistent(self):
        j3 = json.loads((V2_DIR / "u7_v2_readiness_manifest.json").read_text(encoding="utf-8"))
        j4 = json.loads((V2_DIR / "j4_external_manifest.json").read_text(encoding="utf-8"))
        j5 = json.loads((V2_DIR / "j5_architecture_manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(j4["contractVersion"], J2_CONTRACT_VERSION_V2)
        self.assertEqual(j4["train"]["rows"], 4376)
        self.assertEqual(j4["train"]["learners"], 653)
        self.assertEqual(j4["heldOut"]["rows"], 25)
        self.assertEqual(j4["heldOut"]["learners"], 2)
        self.assertEqual(j4["heldOut"]["classCounts"], {"true": 2, "false": 23})
        self.assertEqual(j3["classDistribution"]["labelledRows"], 4401)
        self.assertEqual(j4["train"]["rows"] + j4["heldOut"]["rows"], 4401)
        self.assertEqual(j4["conclusion"]["level"], "MODEL COMPARISON COMPLETED")
        self.assertEqual(j5["shapGlobal"]["featureNames"], ["correct_rate", "mean_response_time_ms"])
        self.assertTrue(j5["bkt"]["gate"]["passed"])
        self.assertEqual(j5["bkt"]["ablation"]["eligibleRows"], 4401)
        self.assertTrue(j5["bkt"]["ablation"]["sameRowsIdenticalExceptBkt"])

    def test_reports_match_manifests(self):
        j4 = json.loads((V2_DIR / "j4_external_manifest.json").read_text(encoding="utf-8"))
        j5 = json.loads((V2_DIR / "j5_architecture_manifest.json").read_text(encoding="utf-8"))
        j4_report = (REPORTS / "u7_assistments_j4_model_comparison.md").read_text(encoding="utf-8")
        j5_report = (REPORTS / "u7_assistments_j5_architecture_evidence.md").read_text(encoding="utf-8")
        self.assertIn(f"{j4['train']['rows']} rows", j4_report)
        self.assertIn(f"{j4['heldOut']['rows']} rows", j4_report)
        self.assertIn(j4["conclusion"]["level"], j4_report.upper())
        self.assertIn(str(j5["shapGlobal"]["rankingByMeanAbsShap"][0]), j5_report)


if __name__ == "__main__":
    unittest.main()
