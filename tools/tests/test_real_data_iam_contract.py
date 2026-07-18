import unittest

from tools.deploy_real_data_iam import (
    EXPORT_SERVICE_ACCOUNT,
    PROTECTED_BUCKET,
    RETENTION_SERVICE_ACCOUNT,
    IamBinding,
    build_bindings,
    deployment_commands,
    validate_bindings,
)


class RealDataIamContractTests(unittest.TestCase):
    def test_exact_export_and_retention_bindings_are_declared(self):
        bindings = build_bindings(hmac_secret_version="v7")
        self.assertEqual(5, len(bindings))
        self.assertIn(
            IamBinding(EXPORT_SERVICE_ACCOUNT, "roles/datastore.viewer", "projects/logic-oasis-fyp"),
            bindings,
        )
        self.assertIn(
            IamBinding(EXPORT_SERVICE_ACCOUNT, "roles/storage.objectCreator", f"gs://{PROTECTED_BUCKET}"),
            bindings,
        )
        self.assertIn(
            IamBinding(RETENTION_SERVICE_ACCOUNT, "roles/storage.objectAdmin", f"gs://{PROTECTED_BUCKET}"),
            bindings,
        )
        validate_bindings(bindings, hmac_secret_version="v7")

    def test_cross_secret_model_bucket_and_broad_role_bindings_are_denied(self):
        bindings = list(build_bindings())
        bindings[-1] = IamBinding(
            RETENTION_SERVICE_ACCOUNT,
            "roles/secretmanager.secretVersionManager",
            "projects/logic-oasis-fyp/secrets/another-secret",
        )
        with self.assertRaisesRegex(ValueError, "exactly match"):
            validate_bindings(bindings)
        bindings = list(build_bindings())
        bindings.append(IamBinding(EXPORT_SERVICE_ACCOUNT, "roles/editor", "projects/logic-oasis-fyp"))
        with self.assertRaisesRegex(ValueError, "exactly match"):
            validate_bindings(bindings)

    def test_rendered_commands_never_include_secret_material_or_model_access(self):
        commands = "\n".join(" ".join(command) for command in deployment_commands(hmac_secret_version="v2"))
        self.assertIn("logic-oasis-export-pseudonymization-key-v2", commands)
        self.assertNotIn("models", commands)
        self.assertNotIn("Owner", commands)
        self.assertNotIn("Editor", commands)


if __name__ == "__main__":
    unittest.main()
