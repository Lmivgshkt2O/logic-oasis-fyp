from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[2]
if str(REPOSITORY / "functions") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "functions"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))
if str(REPOSITORY / "ai_pipeline") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "ai_pipeline"))

import build_function_bundle
import main
from build_function_bundle import CONFIG_HASH_FILES, file_sha256


EVALUATION_COLLECTIONS = (
    "policyEvaluationStudies",
    "policyEvaluationConsents",
    "policyEvaluationEnrollments",
    "policyEvaluationAllocationBlocks",
    "policyEvaluationDecisionAudits",
    "policyEvaluationProbes",
    "policyEvaluationOutcomes",
    "policyEvaluationAdminAudits",
)


class PolicyEvaluationDeploymentContractTests(unittest.TestCase):
    def test_bundle_manifest_carries_the_evaluation_contract_hash(self) -> None:
        manifest = json.loads(
            (REPOSITORY / "functions" / "vendor" / "bundle_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("policyEvaluationSha256", manifest)
        self.assertEqual(64, len(manifest["policyEvaluationSha256"]))
        self.assertEqual(
            "policy_evaluation_v1.yaml",
            CONFIG_HASH_FILES["policyEvaluationSha256"],
        )
        self.assertTrue(
            (
                REPOSITORY
                / "functions"
                / "vendor"
                / "logic_oasis_ai"
                / "policy_evaluation.py"
            ).exists()
        )
        self.assertTrue(
            (
                REPOSITORY
                / "functions"
                / "vendor"
                / "configs"
                / "policy_evaluation_v1.yaml"
            ).exists()
        )
        self.assertEqual(
            manifest["policyEvaluationSha256"],
            file_sha256(
                REPOSITORY
                / "ai_pipeline"
                / "configs"
                / "policy_evaluation_v1.yaml"
            ),
        )

    def test_allocation_secret_is_bound_only_to_the_enrollment_callable(self) -> None:
        allocation = "POLICY_EVALUATION_ALLOCATION_KEY"
        for name in (
            "managePolicyEvaluationStudy",
            "recordPolicyEvaluationConsent",
            "managePolicyEvaluationEnrollment",
        ):
            endpoint = getattr(main, name).__firebase_endpoint__
            secrets = {
                secret["key"]
                for secret in (
                    getattr(endpoint, "secretEnvironmentVariables", None) or []
                )
            }
            self.assertEqual(
                {allocation} if name == "managePolicyEvaluationEnrollment" else set(),
                secrets,
                name,
            )
        runtime_endpoint = getattr(main, "processFinalizedQuizAttempt").__firebase_endpoint__
        runtime_secrets = {
            secret["key"]
            for secret in (
                getattr(runtime_endpoint, "secretEnvironmentVariables", None) or []
            )
        }
        self.assertNotIn(allocation, runtime_secrets)

    def test_firestore_rules_terminally_deny_every_evaluation_collection(self) -> None:
        rules = (REPOSITORY / "firestore.rules").read_text(encoding="utf-8")
        for collection in EVALUATION_COLLECTIONS:
            self.assertIn(f"match /{collection}/{{", rules, collection)
        self.assertIn("allow read, write: if false;", rules)
        self.assertIn("match /{document=**}", rules)

    def test_firebase_json_wires_the_rules_and_functions_source(self) -> None:
        config = json.loads((REPOSITORY / "firebase.json").read_text(encoding="utf-8"))
        self.assertEqual("firestore.rules", config["firestore"]["rules"])
        self.assertEqual("functions", config["functions"]["source"])


if __name__ == "__main__":
    unittest.main()

