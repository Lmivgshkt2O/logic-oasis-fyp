from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "functions"))

from deploy_u8_runtime_iam import (
    ALLOWED_PROJECT_ROLES,
    FUNCTIONS_ROOT,
    MODEL_BUCKET_ROLE,
    RUN_INVOKER_ROLE,
    SERVICE_ACCOUNT,
    _gcloud_executable,
    commands,
    deployment_commands,
    runtime_deploy_command,
    run_invoker_command,
)


class RuntimeIdentityContractTests(unittest.TestCase):
    def test_narrow_identity_commands_do_not_grant_default_or_broad_roles(self) -> None:
        text = "\n".join(" ".join(command) for command in commands(model_bucket="gs://logic-oasis-models"))
        self.assertIn(SERVICE_ACCOUNT, text)
        self.assertEqual(
            ("roles/datastore.user", "roles/logging.logWriter", "roles/eventarc.eventReceiver"),
            ALLOWED_PROJECT_ROLES,
        )
        self.assertEqual("roles/storage.objectViewer", MODEL_BUCKET_ROLE)
        self.assertNotIn("roles/owner", text.lower())
        self.assertNotIn("roles/editor", text.lower())

    def test_eventarc_delivery_can_invoke_only_the_u8_service(self) -> None:
        command = " ".join(run_invoker_command())
        self.assertIn("processfinalizedquizattempt", command)
        self.assertIn(SERVICE_ACCOUNT, command)
        self.assertEqual("roles/run.invoker", RUN_INVOKER_ROLE)
        self.assertNotIn("roles/owner", command.lower())
        self.assertNotIn("roles/editor", command.lower())

    def test_trigger_declares_named_service_account(self) -> None:
        import main
        endpoint = getattr(main.processFinalizedQuizAttempt, "__firebase_endpoint__")
        self.assertEqual(SERVICE_ACCOUNT, endpoint.serviceAccountEmail)
        self.assertEqual("asia-southeast1", endpoint.region[0])

    def test_apply_resolves_explicit_cloud_cli_path(self) -> None:
        with patch.dict("os.environ", {"GCLOUD_BIN": r"C:\Cloud SDK\bin\gcloud.cmd"}, clear=False):
            self.assertEqual(r"C:\Cloud SDK\bin\gcloud.cmd", _gcloud_executable())

    def test_runtime_deploy_declares_evidence_mode_and_approved_bucket(self) -> None:
        import main

        deploy_args = runtime_deploy_command(
            model_bucket="gs://logic-oasis-models",
            evidence_mode="controlled_demo",
        )
        command = " ".join(deploy_args)
        endpoint = getattr(main.processFinalizedQuizAttempt, "__firebase_endpoint__")
        self.assertIn("AI_MODEL_EVIDENCE_MODE=controlled_demo", command)
        self.assertIn("AI_MODEL_BUCKET=logic-oasis-models", command)
        self.assertIn(f"--source {FUNCTIONS_ROOT}", command)
        self.assertIn("--runtime python311", command)
        self.assertIn("--entry-point processFinalizedQuizAttempt", command)
        self.assertIn(f"type={endpoint.eventTrigger['eventType']}", command)
        self.assertIn("document=quizAttempts/{attemptId}", command)
        self.assertTrue(endpoint.eventTrigger["retry"])
        self.assertIn("--retry", deploy_args)
        with self.assertRaises(ValueError):
            runtime_deploy_command(
                model_bucket="gs://logic-oasis-models/subdirectory",
                evidence_mode="controlled_demo",
            )

    def test_combined_bootstrap_deploys_before_granting_run_invoker(self) -> None:
        requested = deployment_commands(
            model_bucket="gs://logic-oasis-models",
            evidence_mode="controlled_demo",
            deploy_runtime=True,
            grant_run_invoker=True,
        )
        deploy_index = next(
            index for index, command in enumerate(requested)
            if command[:3] == ["gcloud", "functions", "deploy"]
        )
        invoker_index = next(
            index for index, command in enumerate(requested)
            if command[:4] == ["gcloud", "run", "services", "add-iam-policy-binding"]
        )
        self.assertLess(deploy_index, invoker_index)

    def test_runtime_only_mode_skips_non_idempotent_identity_bootstrap(self) -> None:
        requested = deployment_commands(
            model_bucket="gs://logic-oasis-models",
            evidence_mode="real_evaluated_only",
            runtime_only=True,
        )
        self.assertEqual(1, len(requested))
        command = " ".join(requested[0])
        self.assertIn("gcloud functions deploy", command)
        self.assertIn("AI_MODEL_EVIDENCE_MODE=real_evaluated_only", command)
        self.assertNotIn("service-accounts create", command)

    def test_function_parameters_default_fail_closed(self) -> None:
        import main

        self.assertEqual(main.AI_MODEL_EVIDENCE_MODE.name, "AI_MODEL_EVIDENCE_MODE")
        self.assertEqual(main.AI_MODEL_EVIDENCE_MODE.default, "real_evaluated_only")
        self.assertEqual(main.AI_MODEL_BUCKET.name, "AI_MODEL_BUCKET")
        self.assertEqual(main.AI_MODEL_BUCKET.default, "")


if __name__ == "__main__":
    unittest.main()
