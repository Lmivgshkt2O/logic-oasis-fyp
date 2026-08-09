from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main
from policy_evaluation import POLICY_EVALUATION_ADMIN_SERVICE_ACCOUNT


ALLOCATION_SECRET = "POLICY_EVALUATION_ALLOCATION_KEY"


def _secrets(callable_name: str) -> set[str]:
    endpoint = getattr(main, callable_name).__firebase_endpoint__
    values = getattr(endpoint, "secretEnvironmentVariables", None) or []
    return {secret["key"] for secret in values}


class PolicyEvaluationRulesContractTests(unittest.TestCase):
    def test_evaluation_callables_declare_the_narrow_runtime_identity(self) -> None:
        for name in (
            "managePolicyEvaluationStudy",
            "recordPolicyEvaluationConsent",
            "managePolicyEvaluationEnrollment",
        ):
            endpoint = getattr(main, name).__firebase_endpoint__
            self.assertEqual(
                endpoint.serviceAccountEmail,
                POLICY_EVALUATION_ADMIN_SERVICE_ACCOUNT,
                name,
            )

    def test_allocation_secret_is_bound_only_to_enrollment(self) -> None:
        self.assertEqual(_secrets("managePolicyEvaluationStudy"), set())
        self.assertEqual(_secrets("recordPolicyEvaluationConsent"), set())
        self.assertEqual(_secrets("managePolicyEvaluationEnrollment"), {ALLOCATION_SECRET})

    def test_quiz_callables_receive_no_allocation_secret(self) -> None:
        for name in ("startQuizSession", "submitQuizResponse", "finalizeQuizSession"):
            self.assertNotIn(ALLOCATION_SECRET, _secrets(name), name)

    def test_rules_terminally_deny_every_evaluation_collection(self) -> None:
        rules = (REPOSITORY / "firestore.rules").read_text(encoding="utf-8")
        for collection in (
            "policyEvaluationStudies",
            "policyEvaluationConsents",
            "policyEvaluationEnrollments",
            "policyEvaluationAllocationBlocks",
            "policyEvaluationDecisionAudits",
            "policyEvaluationProbes",
            "policyEvaluationOutcomes",
            "policyEvaluationAdminAudits",
        ):
            self.assertIn(f"match /{collection}/{{", rules, collection)
        self.assertIn("allow read, write: if false;", rules)


if __name__ == "__main__":
    unittest.main()

