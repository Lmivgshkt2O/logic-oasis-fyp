from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

REPOSITORY = Path(__file__).resolve().parents[2]
if str(REPOSITORY / "ai_pipeline") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "ai_pipeline"))
if str(REPOSITORY / "ai_pipeline" / "tests") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "ai_pipeline" / "tests"))

from tools.verify_policy_evaluation_live import (
    PolicyEvaluationVerificationError,
    verify_live_study_boundary,
    verify_release_artifacts,
)
from training.export_policy_evaluation_release import (
    POLICY_EVALUATION_EXPORT_KEY_PREFIX,
    POLICY_EVALUATION_RELEASE_PREFIX,
    PolicyEvaluationRelease,
    export_policy_evaluation_release,
)
from training.export_real_attempts import _file_sha256

from policy_fixtures import build_dataset, standard_history
from test_policy_evaluation_release_governance import build_audits, build_probes


UTC = timezone.utc
NOW = datetime(2026, 8, 6, tzinfo=UTC)


class Snapshot:
    def __init__(self, document_id, data):
        self.id = document_id
        self._data = data
        self.exists = True

    def to_dict(self):
        return dict(self._data)


class Query:
    def __init__(self, documents, conditions=()):
        self.documents = documents
        self.conditions = conditions

    def where(self, field, _operator, value):
        return Query(self.documents, (*self.conditions, (field, value)))

    def stream(self):
        return [
            Snapshot(document_id, record)
            for document_id, record in self.documents.items()
            if all(record.get(field) == value for field, value in self.conditions)
        ]


class Collection(Query):
    def __init__(self, documents):
        super().__init__(documents)


class Database:
    def __init__(self, collections):
        self.collections = collections

    def collection(self, name):
        return Collection(self.collections.get(name, {}))


def approved_release(release_id: str = "pe-live-v1"):
    return PolicyEvaluationRelease(
        release_id=release_id,
        dataset_version="real_v1_live",
        study_version="study-v1",
        study_status="closed",
        release_decision_ref="PES-GATE-2026-001",
        consent_ethics_reference="ethics-approved-live",
        data_steward="steward@example.edu",
        steward_approved_at=NOW,
        collection_started_at=NOW,
        collection_ended_at=NOW,
        retention_review_at=datetime(2027, 8, 6, tzinfo=UTC),
        storage_path=f"{POLICY_EVALUATION_RELEASE_PREFIX}{release_id}/",
        export_key_version=f"{POLICY_EVALUATION_EXPORT_KEY_PREFIX}1",
    )


class VerifyPolicyEvaluationLiveContractTests(unittest.TestCase):
    def build_release(self, directory):
        dataset = build_dataset(standard_history())
        audits = build_audits(dataset)
        return export_policy_evaluation_release(
            dataset,
            audits,
            build_probes(audits),
            {},
            directory,
            release=approved_release(),
            pseudonymization_key="live-verify-key",
        )

    def test_release_artifacts_verify_hashes_counts_and_protected_content(self) -> None:
        with TemporaryDirectory() as directory:
            files = self.build_release(directory)
            report = verify_release_artifacts(directory)
            self.assertEqual("verified", report["status"])
            self.assertEqual(4, report["filesVerified"])
            tampered = files["decisionAudits"]
            original = tampered.read_bytes()
            tampered.write_bytes(original + b"\n")
            with self.assertRaisesRegex(PolicyEvaluationVerificationError, "hash mismatch"):
                verify_release_artifacts(directory)
            tampered.write_bytes(original)
            tampered.write_text("studentId,raw\n1,2\n", encoding="utf-8")
            manifest_path = Path(directory) / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["fileSha256"]["decision_audits.csv"] = _file_sha256(tampered)
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(PolicyEvaluationVerificationError, "protected content"):
                verify_release_artifacts(directory)

    def test_live_boundary_rejects_audits_after_revocation_and_orphan_audits(self) -> None:
        revoked_at = datetime(2026, 8, 2, tzinfo=UTC)
        database = Database(
            {
                "policyEvaluationEnrollments": {
                    "enr-active": {
                        "enrollmentId": "enr-active",
                        "studyVersion": "study-v1",
                        "status": "active",
                        "assignedArm": "P1",
                    },
                    "enr-revoked": {
                        "enrollmentId": "enr-revoked",
                        "studyVersion": "study-v1",
                        "status": "revoked",
                        "revokedAt": revoked_at,
                    },
                },
                "policyEvaluationDecisionAudits": {
                    "decision-1": {
                        "decisionId": "decision-1",
                        "studyVersion": "study-v1",
                        "enrollmentId": "enr-active",
                        "createdAt": datetime(2026, 8, 1, tzinfo=UTC),
                    },
                    "decision-2": {
                        "decisionId": "decision-2",
                        "studyVersion": "study-v1",
                        "enrollmentId": "enr-revoked",
                        "createdAt": datetime(2026, 8, 3, tzinfo=UTC),
                    },
                    "decision-3": {
                        "decisionId": "decision-3",
                        "studyVersion": "study-v1",
                        "enrollmentId": "missing-enr",
                        "createdAt": datetime(2026, 8, 1, tzinfo=UTC),
                    },
                },
            }
        )
        report = verify_live_study_boundary(database, study_version="study-v1", now=NOW)
        self.assertEqual("violation", report["status"])
        types = {violation["type"] for violation in report["violations"]}
        self.assertEqual({"audit_after_revocation", "orphan_audit"}, types)

    def test_live_boundary_accepts_historical_audits_before_revocation(self) -> None:
        database = Database(
            {
                "policyEvaluationEnrollments": {
                    "enr-revoked": {
                        "enrollmentId": "enr-revoked",
                        "studyVersion": "study-v1",
                        "status": "revoked",
                        "revokedAt": datetime(2026, 8, 5, tzinfo=UTC),
                    }
                },
                "policyEvaluationDecisionAudits": {
                    "decision-1": {
                        "decisionId": "decision-1",
                        "studyVersion": "study-v1",
                        "enrollmentId": "enr-revoked",
                        "createdAt": datetime(2026, 8, 1, tzinfo=UTC),
                    }
                },
            }
        )
        report = verify_live_study_boundary(database, study_version="study-v1", now=NOW)
        self.assertEqual("verified", report["status"])
        self.assertEqual([], report["violations"])


if __name__ == "__main__":
    unittest.main()
