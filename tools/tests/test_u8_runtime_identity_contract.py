from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "functions"))

from deploy_u8_runtime_iam import ALLOWED_PROJECT_ROLES, MODEL_BUCKET_ROLE, SERVICE_ACCOUNT, commands


class RuntimeIdentityContractTests(unittest.TestCase):
    def test_narrow_identity_commands_do_not_grant_default_or_broad_roles(self) -> None:
        text = "\n".join(" ".join(command) for command in commands(model_bucket="gs://logic-oasis-models"))
        self.assertIn(SERVICE_ACCOUNT, text)
        self.assertEqual(("roles/datastore.user", "roles/logging.logWriter"), ALLOWED_PROJECT_ROLES)
        self.assertEqual("roles/storage.objectViewer", MODEL_BUCKET_ROLE)
        self.assertNotIn("roles/owner", text.lower())
        self.assertNotIn("roles/editor", text.lower())

    def test_trigger_declares_named_service_account(self) -> None:
        import main
        endpoint = getattr(main.processFinalizedQuizAttempt, "__firebase_endpoint__")
        self.assertEqual(SERVICE_ACCOUNT, endpoint.serviceAccountEmail)
        self.assertEqual("asia-southeast1", endpoint.region[0])


if __name__ == "__main__":
    unittest.main()
