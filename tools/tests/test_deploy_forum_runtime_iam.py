from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from deploy_forum_runtime_iam import (
    FUNCTION_REGION,
    FUNCTIONS_ROOT,
    SERVICE_ACCOUNT,
    RUNTIME_ROLES,
    commands,
    deploy_commands,
    deployment_attestation,
    inspection_commands,
    preflight_checks,
    runtime_deploy_command,
    runtime_deploy_commands,
)
from forum_function_inventory import (
    FORUM_FUNCTION_INVENTORY,
    forum_inventory_digest,
)


class ForumRuntimeIamTests(unittest.TestCase):
    def test_identity_is_dedicated_and_narrow(self):
        rendered = "\n".join(" ".join(command) for command in commands())
        self.assertIn(SERVICE_ACCOUNT, rendered)
        self.assertNotIn("roles/owner", rendered)
        self.assertNotIn("roles/editor", rendered)
        self.assertNotIn("appspot.gserviceaccount.com", rendered)
        runtime_role_flags = {
            argument.removeprefix("--role=")
            for command in commands()
            for argument in command
            if argument.startswith("--role=") and argument != "--role=roles/iam.serviceAccountUser"
        }
        self.assertEqual(set(RUNTIME_ROLES), runtime_role_flags)

    def test_deploy_sets_controlled_mode_revision_and_named_identity(self):
        revision = "a" * 64
        commands_to_deploy = runtime_deploy_commands(
            evidence_mode="controlled_demo", code_revision=revision,
        )
        self.assertEqual(2, len(commands_to_deploy))
        rendered = "\n".join(" ".join(command) for command in commands_to_deploy)
        self.assertIn("FORUM_MODEL_EVIDENCE_MODE=controlled_demo", rendered)
        self.assertIn(f"FORUM_RUNTIME_CODE_REVISION={revision}", rendered)
        self.assertIn(SERVICE_ACCOUNT, rendered)
        self.assertIn(f"--source {FUNCTIONS_ROOT}", rendered)
        self.assertIn(f"--trigger-location {FUNCTION_REGION}", rendered)
        self.assertIn("google.cloud.firestore.document.v1.created", rendered)
        self.assertIn("google.cloud.firestore.document.v1.updated", rendered)
        self.assertEqual(2, rendered.count("document=forumAnswers/{answerId}"))
        with self.assertRaises(ValueError):
            runtime_deploy_command(evidence_mode="unknown", code_revision=revision)
        for invalid in ("abc123", "A" * 64, "a" * 63, "a," + "b" * 62):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                runtime_deploy_command(evidence_mode="controlled_demo", code_revision=invalid)

    def test_all_forum_triggers_declare_the_dedicated_identity(self):
        sys.path.insert(0, str(ROOT / "functions"))
        import main
        for endpoint in (main.processForumQuestion, main.processForumAnswer, main.reprocessForumAnswer):
            self.assertEqual(SERVICE_ACCOUNT, endpoint.__firebase_endpoint__.serviceAccountEmail)

    def test_authoritative_inventory_is_eleven_entries_with_one_identity(self):
        self.assertEqual(11, len(FORUM_FUNCTION_INVENTORY))
        names = [entry["name"] for entry in FORUM_FUNCTION_INVENTORY]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(
            {entry["serviceAccount"] for entry in FORUM_FUNCTION_INVENTORY},
            {SERVICE_ACCOUNT},
        )
        self.assertEqual(
            {entry["region"] for entry in FORUM_FUNCTION_INVENTORY},
            {FUNCTION_REGION},
        )
        retrying = {
            entry["name"] for entry in FORUM_FUNCTION_INVENTORY
            if entry["retry"] is True
        }
        self.assertEqual(retrying, {"processForumAnswer", "reprocessForumAnswer"})
        self.assertRegex(forum_inventory_digest(), r"^[0-9a-f]{64}$")

    def test_preflight_is_read_only_and_rejects_unsafe_inputs(self):
        revision = "a" * 64
        operator = (
            "serviceAccount:logic-oasis-deployer@logic-oasis-fyp.iam.gserviceaccount.com"
        )
        checks = preflight_checks(
            project_id="logic-oasis-fyp", operator_account=operator,
            region=FUNCTION_REGION, runtime="python311",
            evidence_mode="controlled_demo", code_revision=revision,
        )
        self.assertTrue(all(check["ok"] for check in checks))
        self.assertEqual(11, checks[-1]["entryCount"])

        for project in ("other-project", ""):
            with self.subTest(project=project), self.assertRaises(ValueError):
                preflight_checks(
                    project_id=project, operator_account=operator,
                    region=FUNCTION_REGION, runtime="python311",
                    evidence_mode="controlled_demo", code_revision=revision,
                )
        for operator_account in (
            "serviceAccount:default", "default-compute", "compute",
            f"serviceAccount:{SERVICE_ACCOUNT}",
        ):
            with self.subTest(operator=operator_account), self.assertRaises(ValueError):
                preflight_checks(
                    project_id="logic-oasis-fyp", operator_account=operator_account,
                    region=FUNCTION_REGION, runtime="python311",
                    evidence_mode="controlled_demo", code_revision=revision,
                )
        for runtime in ("python312", "python3110", ""):
            with self.subTest(runtime=runtime), self.assertRaises(ValueError):
                preflight_checks(
                    project_id="logic-oasis-fyp", operator_account=operator,
                    region=FUNCTION_REGION, runtime=runtime,
                    evidence_mode="controlled_demo", code_revision=revision,
                )
        for invalid in ("abc", "A" * 64, "", "a" * 63):
            with self.subTest(revision=invalid), self.assertRaises(ValueError):
                preflight_checks(
                    project_id="logic-oasis-fyp", operator_account=operator,
                    region=FUNCTION_REGION, runtime="python311",
                    evidence_mode="controlled_demo", code_revision=invalid,
                )

    def test_deploy_commands_cover_all_eleven_and_retry_only_two(self):
        revision = "a" * 64
        deploy = deploy_commands(
            evidence_mode="controlled_demo", code_revision=revision,
        )
        self.assertEqual(11, len(deploy))
        rendered = "\n".join(" ".join(command) for command in deploy)
        for entry in FORUM_FUNCTION_INVENTORY:
            self.assertIn(entry["name"], rendered)
        self.assertEqual(2, rendered.count("--retry"))
        self.assertEqual(11, rendered.count("--service-account"))
        self.assertEqual(3, rendered.count("--trigger-location"))
        self.assertEqual(8, rendered.count("--trigger-http"))
        self.assertEqual(3, rendered.count("--trigger-service-account"))
        self.assertEqual(3, rendered.count("FUNCTION_SIGNATURE_TYPE=cloudevent"))
        self.assertEqual(3, rendered.count("--memory=512MiB"))

    def test_inspection_and_attestation_require_the_full_matching_inventory(self):
        inspection = inspection_commands()
        self.assertEqual(11, len(inspection))
        revision = "a" * 64
        manifest = {"releaseId": "forum-controlled-demo-nb-v1-release-5", "codeRevision": revision}
        observed = {
            entry["name"]: {
                "region": FUNCTION_REGION,
                "serviceAccount": SERVICE_ACCOUNT,
                "runtime": "python311",
                "codeRevision": revision,
            }
            for entry in FORUM_FUNCTION_INVENTORY
        }
        attestation = deployment_attestation(
            release_manifest=manifest,
            observed_functions=observed,
            attested_at="2026-08-13T00:00:00Z",
        )
        self.assertEqual("deployed", attestation["deploymentState"])
        self.assertEqual(11, attestation["observedFunctionCount"])
        self.assertRegex(attestation["attestationSha256"], r"^[0-9a-f]{64}$")

        with self.assertRaises(ValueError):
            deployment_attestation(
                release_manifest=manifest,
                observed_functions=dict(list(observed.items())[:-1]),
                attested_at="2026-08-13T00:00:00Z",
            )
        drifted = dict(observed)
        drifted["processForumAnswer"] = {
            **drifted["processForumAnswer"], "runtime": "python312",
        }
        with self.assertRaises(ValueError):
            deployment_attestation(
                release_manifest=manifest,
                observed_functions=drifted,
                attested_at="2026-08-13T00:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
