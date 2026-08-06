import unittest

from tools.deploy_policy_evaluation_iam import (
    AI_RUNTIME_SERVICE_ACCOUNT,
    ALLOCATION_SECRET,
    POLICY_EVALUATION_ADMIN_SERVICE_ACCOUNT,
    IamBinding,
    build_bindings,
    deployment_commands,
    validate_bindings,
)


class PolicyEvaluationIamContractTests(unittest.TestCase):
    def test_admin_identity_alone_holds_the_allocation_secret_accessor(self):
        bindings = build_bindings()
        self.assertEqual(3, len(bindings))
        secret_bindings = [
            binding
            for binding in bindings
            if binding.role == "roles/secretmanager.secretAccessor"
            and ALLOCATION_SECRET in binding.resource
        ]
        self.assertEqual(1, len(secret_bindings))
        self.assertEqual(POLICY_EVALUATION_ADMIN_SERVICE_ACCOUNT, secret_bindings[0].principal)
        self.assertNotIn(
            AI_RUNTIME_SERVICE_ACCOUNT,
            {binding.principal for binding in bindings},
        )
        validate_bindings(bindings)

    def test_runtime_identity_cannot_receive_the_allocation_secret(self):
        bindings = list(build_bindings())
        bindings.append(
            IamBinding(
                AI_RUNTIME_SERVICE_ACCOUNT,
                "roles/secretmanager.secretAccessor",
                f"projects/logic-oasis-fyp/secrets/{ALLOCATION_SECRET}",
            )
        )
        with self.assertRaisesRegex(ValueError, "bound only to the evaluation admin"):
            validate_bindings(bindings)
        with self.assertRaisesRegex(ValueError, "exactly match"):
            validate_bindings(bindings[:2])

    def test_broad_or_model_scoped_bindings_are_denied(self):
        bindings = list(build_bindings())
        bindings.append(
            IamBinding(
                POLICY_EVALUATION_ADMIN_SERVICE_ACCOUNT,
                "roles/editor",
                "projects/logic-oasis-fyp",
            )
        )
        with self.assertRaisesRegex(ValueError, "broad or signing roles"):
            validate_bindings(bindings)
        bindings = list(build_bindings())
        bindings[0] = IamBinding(
            POLICY_EVALUATION_ADMIN_SERVICE_ACCOUNT,
            "roles/datastore.user",
            "projects/logic-oasis-fyp/secrets/model-bucket",
        )
        with self.assertRaisesRegex(ValueError, "model"):
            validate_bindings(bindings)

    def test_rendered_commands_never_include_secret_material_or_broad_roles(self):
        commands = "\n".join(" ".join(command) for command in deployment_commands())
        self.assertIn(ALLOCATION_SECRET, commands)
        self.assertNotIn("models", commands)
        self.assertNotIn("Owner", commands)
        self.assertNotIn("Editor", commands)


if __name__ == "__main__":
    unittest.main()
