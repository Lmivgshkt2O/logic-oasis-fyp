from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from promote_controlled_demo_model import (
    promote_forum_controlled_demo_model,
    revoke_forum_controlled_demo_model,
)
from forum_function_inventory import (
    forum_inventory_digest,
    validate_forum_function_inventory,
)
from tools.tests.test_controlled_demo_registry_contract import Database


NOW = datetime(2026, 8, 9, 9, 0, tzinfo=timezone.utc)


def release_manifest() -> dict[str, object]:
    return json.loads(
        (ROOT / "functions/forum_model_manifest.json").read_text(encoding="utf-8")
    )


def deployment_attestation(document: dict[str, object]) -> dict[str, object]:
    payload = {
        "attestationKind": "live_deployment_attestation_v1",
        "deploymentState": "deployed",
        "releaseId": document["releaseId"],
        "codeRevision": document["codeRevision"],
        "functionInventorySha256": forum_inventory_digest(),
        "observedFunctionCount": len(validate_forum_function_inventory()),
        "attestedAt": "2026-08-13T00:00:00Z",
    }
    payload["attestationSha256"] = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


class ForumControlledDemoPromotionTests(unittest.TestCase):
    def test_transaction_creates_one_immutable_active_forum_release(self):
        document = release_manifest()
        # The bundled manifest now names its immutable predecessor; the
        # first-rollout contract requires an empty registry and no supersede.
        document["supersedesReleaseId"] = None
        database = Database()
        with patch(
            "firebase_admin.firestore.transactional",
            lambda function: lambda transaction: function(transaction),
        ):
            promoted = promote_forum_controlled_demo_model(
                database, document, now=NOW,
                deployment_attestation=deployment_attestation(document),
            )
        self.assertEqual(document["releaseId"], promoted["releaseId"])
        self.assertTrue(database.registry[str(document["releaseId"])]["isActive"])
        self.assertEqual(
            database.registry[str(document["releaseId"])]["deploymentAttestationSha256"],
            deployment_attestation(document)["attestationSha256"],
        )
        with patch(
            "firebase_admin.firestore.transactional",
            lambda function: lambda transaction: function(transaction),
        ), self.assertRaisesRegex(ValueError, "immutable"):
            promote_forum_controlled_demo_model(
                database, document, now=NOW,
                deployment_attestation=deployment_attestation(document),
            )

    def test_replacement_supersedes_prior_release_in_same_transaction(self):
        prior = release_manifest()
        prior["releaseId"] = "forum-release-1"
        database = Database({"forum-release-1": prior})
        replacement = release_manifest()
        replacement["releaseId"] = "forum-release-2"
        replacement["supersedesReleaseId"] = "forum-release-1"
        with patch(
            "firebase_admin.firestore.transactional",
            lambda function: lambda transaction: function(transaction),
        ):
            promote_forum_controlled_demo_model(
                database, replacement, now=NOW,
                deployment_attestation=deployment_attestation(replacement),
            )
        self.assertFalse(database.registry["forum-release-1"]["isActive"])
        self.assertEqual("superseded", database.registry["forum-release-1"]["lifecycleStatus"])
        self.assertTrue(database.registry["forum-release-2"]["isActive"])

    def test_replacement_must_name_the_current_active_release(self):
        prior = release_manifest()
        prior["releaseId"] = "forum-release-1"
        database = Database({"forum-release-1": prior})
        replacement = release_manifest()
        replacement["releaseId"] = "forum-release-2"
        replacement["supersedesReleaseId"] = "wrong-release"
        with patch(
            "firebase_admin.firestore.transactional",
            lambda function: lambda transaction: function(transaction),
        ), self.assertRaisesRegex(ValueError, "identify the active"):
            promote_forum_controlled_demo_model(
                database, replacement, now=NOW,
                deployment_attestation=deployment_attestation(replacement),
            )
        self.assertTrue(database.registry["forum-release-1"]["isActive"])

    def test_revocation_preserves_bindings_and_deactivates_the_record(self):
        document = release_manifest()
        release_id = str(document["releaseId"])
        database = Database({release_id: document})
        before = dict(database.registry[release_id])
        with patch(
            "firebase_admin.firestore.transactional",
            lambda function: lambda transaction: function(transaction),
        ):
            revoked = revoke_forum_controlled_demo_model(database, release_id)
        self.assertFalse(revoked["isActive"])
        self.assertEqual("revoked", revoked["lifecycleStatus"])
        for key, value in before.items():
            if key not in {"isActive", "lifecycleStatus"}:
                self.assertEqual(value, database.registry[release_id][key])
        with patch(
            "firebase_admin.firestore.transactional",
            lambda function: lambda transaction: function(transaction),
        ), self.assertRaisesRegex(ValueError, "requested active"):
            revoke_forum_controlled_demo_model(database, release_id)

    def test_replacement_can_restore_a_revoked_compatible_release(self):
        prior = release_manifest()
        prior["releaseId"] = "forum-release-1"
        prior["isActive"] = False
        prior["lifecycleStatus"] = "revoked"
        database = Database({"forum-release-1": prior})
        replacement = release_manifest()
        replacement["releaseId"] = "forum-release-2"
        replacement["supersedesReleaseId"] = "forum-release-1"
        with patch(
            "firebase_admin.firestore.transactional",
            lambda function: lambda transaction: function(transaction),
        ):
            promote_forum_controlled_demo_model(
                database, replacement, now=NOW,
                deployment_attestation=deployment_attestation(replacement),
            )
        self.assertEqual("revoked", database.registry["forum-release-1"]["lifecycleStatus"])
        self.assertTrue(database.registry["forum-release-2"]["isActive"])

    def test_revocation_rejects_corrupt_multiple_active_state(self):
        first = release_manifest()
        first["releaseId"] = "forum-release-1"
        second = release_manifest()
        second["releaseId"] = "forum-release-2"
        database = Database({"forum-release-1": first, "forum-release-2": second})
        with patch(
            "firebase_admin.firestore.transactional",
            lambda function: lambda transaction: function(transaction),
        ), self.assertRaisesRegex(ValueError, "only the requested active"):
            revoke_forum_controlled_demo_model(database, "forum-release-1")
        self.assertTrue(database.registry["forum-release-1"]["isActive"])
        self.assertTrue(database.registry["forum-release-2"]["isActive"])

    def test_promotion_requires_a_matching_live_deployment_attestation(self):
        document = release_manifest()
        database = Database()
        with patch(
            "firebase_admin.firestore.transactional",
            lambda function: lambda transaction: function(transaction),
        ), self.assertRaisesRegex(ValueError, "attestation"):
            promote_forum_controlled_demo_model(database, document, now=NOW)

        mismatched = deployment_attestation(document)
        mismatched["releaseId"] = "different-release"
        with patch(
            "firebase_admin.firestore.transactional",
            lambda function: lambda transaction: function(transaction),
        ), self.assertRaisesRegex(ValueError, "does not match"):
            promote_forum_controlled_demo_model(
                database, document, now=NOW,
                deployment_attestation=mismatched,
            )

        incomplete = deployment_attestation(document)
        incomplete["observedFunctionCount"] = 8
        with patch(
            "firebase_admin.firestore.transactional",
            lambda function: lambda transaction: function(transaction),
        ), self.assertRaisesRegex(ValueError, "authoritative forum inventory"):
            promote_forum_controlled_demo_model(
                database, document, now=NOW,
                deployment_attestation=incomplete,
            )

    def test_first_rollout_cannot_supersede_an_earlier_release(self):
        document = release_manifest()
        document["supersedesReleaseId"] = "forum-release-1"
        database = Database()
        with patch(
            "firebase_admin.firestore.transactional",
            lambda function: lambda transaction: function(transaction),
        ), self.assertRaisesRegex(ValueError, "first forum rollout"):
            promote_forum_controlled_demo_model(
                database, document, now=NOW,
                deployment_attestation=deployment_attestation(document),
            )
        self.assertEqual({}, database.registry)


if __name__ == "__main__":
    unittest.main()
