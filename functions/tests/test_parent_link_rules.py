from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main
from parent_link_admin import PARENT_LINK_ADMIN_SERVICE_ACCOUNT
from parent_link_invitation import PARENT_INVITATION_SERVICE_ACCOUNT


class ParentLinkRulesContractTests(unittest.TestCase):
    def test_parent_link_callables_declare_the_narrow_runtime_identity(self) -> None:
        self.assertEqual(
            main.getLinkedChildren.__firebase_endpoint__.serviceAccountEmail,
            PARENT_LINK_ADMIN_SERVICE_ACCOUNT,
        )
        self.assertEqual(
            main.manageParentLink.__firebase_endpoint__.serviceAccountEmail,
            PARENT_LINK_ADMIN_SERVICE_ACCOUNT,
        )
        self.assertEqual(
            main.revokeParentLink.__firebase_endpoint__.serviceAccountEmail,
            PARENT_LINK_ADMIN_SERVICE_ACCOUNT,
        )
        self.assertEqual(
            main.createParentLinkInvitation.__firebase_endpoint__.serviceAccountEmail,
            PARENT_INVITATION_SERVICE_ACCOUNT,
        )
        self.assertEqual(
            main.acceptParentLinkInvitation.__firebase_endpoint__.serviceAccountEmail,
            PARENT_INVITATION_SERVICE_ACCOUNT,
        )
        self.assertEqual(
            {secret["key"] for secret in main.createParentLinkInvitation.__firebase_endpoint__.secretEnvironmentVariables},
            {"PARENT_INVITATION_EMAIL_HMAC_KEY", "PARENT_INVITATION_SMTP_PASSWORD"},
        )

    def test_rules_protect_links_and_allow_only_safe_parent_projections(self) -> None:
        rules = (REPOSITORY / "firestore.rules").read_text(encoding="utf-8")
        self.assertIn("function isActiveLinkedParent(studentId)", rules)
        self.assertIn("match /forumParticipationSummaries/{studentId}", rules)
        self.assertIn("match /parentLinks/{linkId}", rules)
        self.assertIn("match /parentLinkInvitations/{invitationId}", rules)
        self.assertIn("match /parentLinkAudits/{auditId}", rules)
        self.assertIn("keepsStudentAuthorityImmutable", rules)
        self.assertIn(".data.parentId == request.auth.uid", rules)
        self.assertIn(".data.studentId == studentId", rules)
        self.assertIn("allow write: if false;", rules)
        self.assertIn("match /aiModelRuns/{runId}", rules)

    def test_u9_iam_manifest_grants_only_declared_runtime_roles(self) -> None:
        tools_root = REPOSITORY / "tools"
        sys.path.insert(0, str(tools_root))
        import deploy_parent_link_admin_iam as iam

        rendered = iam.commands(deployer_member="user:deployer@example.com")
        parent_runtime_roles = {
            command[-1]
            for command in rendered
            if f"serviceAccount:{iam.PARENT_LINK_ADMIN_SERVICE_ACCOUNT}" in command
        }
        self.assertEqual(
            parent_runtime_roles,
            {
                "roles/firebaseauth.viewer",
                "roles/datastore.user",
                "roles/logging.logWriter",
            },
        )

    def test_u9_iam_manifest_exposes_only_the_declared_callable_entrypoints(self) -> None:
        tools_root = REPOSITORY / "tools"
        sys.path.insert(0, str(tools_root))
        import deploy_parent_link_admin_iam as iam

        rendered = iam.commands(deployer_member="user:deployer@example.com")
        invoker_commands = [
            command
            for command in rendered
            if command[:5] == ["gcloud", "run", "services", "add-iam-policy-binding", command[4]]
        ]
        self.assertEqual(
            invoker_commands,
            [
                [
                    "gcloud", "run", "services", "add-iam-policy-binding", "getlinkedchildren",
                    "--region", "asia-southeast1", "--project", iam.PROJECT_ID,
                    "--member", "allUsers", "--role", "roles/run.invoker",
                ],
                [
                    "gcloud", "run", "services", "add-iam-policy-binding", "manageparentlink",
                    "--region", "asia-southeast1", "--project", iam.PROJECT_ID,
                    "--member", "allUsers", "--role", "roles/run.invoker",
                ],
                [
                    "gcloud", "run", "services", "add-iam-policy-binding", "revokeparentlink",
                    "--region", "asia-southeast1", "--project", iam.PROJECT_ID,
                    "--member", "allUsers", "--role", "roles/run.invoker",
                ],
            ],
        )

    def test_u12_invitation_iam_manifest_matches_its_declared_runtime(self) -> None:
        tools_root = REPOSITORY / "tools"
        sys.path.insert(0, str(tools_root))
        import deploy_parent_invitation_iam as iam

        rendered = iam.commands(deployer_member="user:deployer@example.com")
        runtime_roles = {
            command[-1]
            for command in rendered
            if command[:3] == ["gcloud", "projects", "add-iam-policy-binding"]
            and f"serviceAccount:{iam.SERVICE_ACCOUNT}" in command
        }
        self.assertEqual(runtime_roles, set(iam.RUNTIME_ROLES))
        secret_bindings = [
            command[3]
            for command in rendered
            if command[:4] == ["gcloud", "secrets", "add-iam-policy-binding", command[3]]
        ]
        self.assertEqual(secret_bindings, list(iam.REQUIRED_SECRETS))
        services = [command[4] for command in rendered if command[:4] == ["gcloud", "run", "services", "add-iam-policy-binding"]]
        self.assertEqual(services, list(iam.CALLABLES))


if __name__ == "__main__":
    unittest.main()
