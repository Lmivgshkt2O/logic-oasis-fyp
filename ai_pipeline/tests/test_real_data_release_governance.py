from datetime import datetime, timezone
import json
from tempfile import TemporaryDirectory
import unittest

from logic_oasis_ai.sources.firestore_source import load_firestore_dataset
from training.delete_real_data_release import (
    ReleaseDeletionRequest,
    create_deletion_certificate,
    may_destroy_key_version,
)
from training.export_real_attempts import (
    PROTECTED_RELEASE_PREFIX,
    RealDataRelease,
    export_real_attempts,
    hmac_pseudonym,
)
from test_source_parity import firestore_attempts, firestore_responses


NOW = datetime(2026, 7, 17, tzinfo=timezone.utc)


def approved_release(**overrides):
    values = {
        "release_id": "release-governance-v1",
        "dataset_version": "real_attempts_v1_2026-07",
        "consent_ethics_reference": "ethics-approved-001",
        "data_steward": "steward@example.edu",
        "steward_approved_at": NOW,
        "collection_started_at": NOW,
        "collection_ended_at": NOW,
        "retention_review_at": datetime(2027, 7, 17, tzinfo=timezone.utc),
        "storage_path": f"{PROTECTED_RELEASE_PREFIX}release-governance-v1/",
        "export_key_version": "logic-oasis-export-pseudonymization-key-v1",
    }
    values.update(overrides)
    return RealDataRelease(**values)


class RealDataReleaseGovernanceTests(unittest.TestCase):
    def test_hmac_pseudonyms_are_stable_but_do_not_expose_raw_identifier(self):
        first = hmac_pseudonym("student", "student-raw-id", "release-key")
        self.assertEqual(first, hmac_pseudonym("student", "student-raw-id", "release-key"))
        self.assertNotIn("student-raw-id", first)
        self.assertNotEqual(first, hmac_pseudonym("student", "student-raw-id", "rotated-key"))

    def test_release_requires_approval_metadata_and_protected_path(self):
        with self.assertRaisesRegex(ValueError, "consent_ethics_reference"):
            approved_release(consent_ethics_reference="")
        with self.assertRaisesRegex(ValueError, "protected versioned GCS"):
            approved_release(storage_path="C:/Users/developer/Desktop/export")
        with self.assertRaisesRegex(ValueError, "HMAC Secret Manager"):
            approved_release(export_key_version="local-secret")

    def test_manifest_has_hashes_custody_and_no_local_path_or_secret(self):
        dataset = load_firestore_dataset(firestore_attempts(), firestore_responses(), provenance="real")
        with TemporaryDirectory() as temporary_directory:
            files = export_real_attempts(
                dataset, temporary_directory, release=approved_release(), pseudonymization_key="do-not-write-this-key"
            )
            manifest = json.loads(files["manifest"].read_text(encoding="utf-8"))
        self.assertEqual("real", manifest["provenance"])
        self.assertEqual("steward@example.edu", manifest["dataSteward"])
        self.assertIn("attempts.csv", manifest["fileSha256"])
        self.assertIn("sourceAttemptSequence", manifest["sourceAttemptOrdering"])
        self.assertNotIn("do-not-write-this-key", json.dumps(manifest))
        self.assertNotIn(temporary_directory, json.dumps(manifest))
        self.assertFalse(manifest["containsRawIdentifiers"])

    def test_deletion_evidence_must_precede_matching_key_destruction(self):
        release = approved_release()
        manifest = {
            "releaseId": release.release_id,
            "storagePath": release.storage_path,
            "exportKeyVersion": release.export_key_version,
            "dataSteward": release.data_steward,
        }
        request = ReleaseDeletionRequest(
            release_id=release.release_id, storage_path=release.storage_path,
            export_key_version=release.export_key_version, data_steward=release.data_steward,
            retention_actor="logic-oasis-data-retention@logic-oasis-fyp.iam.gserviceaccount.com",
            retention_review_at=release.retention_review_at,
        )
        certificate = create_deletion_certificate(request, manifest=manifest, deleted_at=NOW)
        self.assertTrue(may_destroy_key_version(certificate, release_id=release.release_id, export_key_version=release.export_key_version))
        self.assertFalse(may_destroy_key_version(certificate, release_id=release.release_id, export_key_version="logic-oasis-export-pseudonymization-key-v2"))


if __name__ == "__main__":
    unittest.main()
