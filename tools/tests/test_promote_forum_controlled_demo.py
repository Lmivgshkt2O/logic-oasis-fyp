from datetime import datetime, timezone
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
from tools.tests.test_controlled_demo_registry_contract import Database


NOW = datetime(2026, 8, 9, 9, 0, tzinfo=timezone.utc)


def release_manifest() -> dict[str, object]:
    return json.loads(
        (ROOT / "functions/forum_model_manifest.json").read_text(encoding="utf-8")
    )


class ForumControlledDemoPromotionTests(unittest.TestCase):
    def test_transaction_creates_one_immutable_active_forum_release(self):
        document = release_manifest()
        database = Database()
        with patch(
            "firebase_admin.firestore.transactional",
            lambda function: lambda transaction: function(transaction),
        ):
            promoted = promote_forum_controlled_demo_model(database, document, now=NOW)
        self.assertEqual(document["releaseId"], promoted["releaseId"])
        self.assertTrue(database.registry[str(document["releaseId"])]["isActive"])
        with patch(
            "firebase_admin.firestore.transactional",
            lambda function: lambda transaction: function(transaction),
        ), self.assertRaisesRegex(ValueError, "immutable"):
            promote_forum_controlled_demo_model(database, document, now=NOW)

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
            promote_forum_controlled_demo_model(database, replacement, now=NOW)
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
            promote_forum_controlled_demo_model(database, replacement, now=NOW)
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
            promote_forum_controlled_demo_model(database, replacement, now=NOW)
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


if __name__ == "__main__":
    unittest.main()
