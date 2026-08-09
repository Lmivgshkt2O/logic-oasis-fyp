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
    runtime_deploy_command,
    runtime_deploy_commands,
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


if __name__ == "__main__":
    unittest.main()
