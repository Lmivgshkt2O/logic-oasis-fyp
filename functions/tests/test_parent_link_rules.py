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


class ParentLinkRulesContractTests(unittest.TestCase):
    def test_parent_link_callables_declare_the_narrow_runtime_identity(self) -> None:
        self.assertEqual(
            main.manageParentLink.__firebase_endpoint__.serviceAccountEmail,
            PARENT_LINK_ADMIN_SERVICE_ACCOUNT,
        )
        self.assertEqual(
            main.revokeParentLink.__firebase_endpoint__.serviceAccountEmail,
            PARENT_LINK_ADMIN_SERVICE_ACCOUNT,
        )

    def test_rules_protect_links_and_allow_only_safe_parent_projections(self) -> None:
        rules = (REPOSITORY / "firestore.rules").read_text(encoding="utf-8")
        self.assertIn("function isActiveLinkedParent(studentId)", rules)
        self.assertIn("match /forumParticipationSummaries/{studentId}", rules)
        self.assertIn("match /parentLinks/{linkId}", rules)
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
            {"roles/datastore.user", "roles/logging.logWriter"},
        )


if __name__ == "__main__":
    unittest.main()
