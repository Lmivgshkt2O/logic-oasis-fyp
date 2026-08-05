from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from logic_oasis_ai.sources.csv_source import load_csv_files
from logic_oasis_ai.sources.firestore_source import (
    POLICY_EVALUATION_AUDIT_FIELDS,
    PolicyEvaluationAuditJoin,
)
from training.export_real_attempts import (
    PROTECTED_RELEASE_PREFIX,
    RealDataRelease,
    export_real_attempts,
)
from policy_fixtures import build_dataset, standard_history


UTC = timezone.utc
NOW = datetime(2026, 8, 1, tzinfo=UTC)


def approved_release(release_id: str = "release-aqc2-export"):
    return RealDataRelease(
        release_id=release_id,
        dataset_version="real_v1_aqc2_export",
        consent_ethics_reference="ethics-approved-aqc2",
        data_steward="steward@example.edu",
        steward_approved_at=NOW,
        collection_started_at=NOW,
        collection_ended_at=NOW,
        retention_review_at=datetime(2027, 8, 1, tzinfo=UTC),
        storage_path=f"{PROTECTED_RELEASE_PREFIX}{release_id}/",
        export_key_version="logic-oasis-export-pseudonymization-key-v1",
    )


def audit_for(attempt_id: str, **overrides) -> PolicyEvaluationAuditJoin:
    values = {
        "decision_id": f"policy-decision-{attempt_id}-audit",
        "study_version": "policy-evaluation-study-v1",
        "assigned_arm": "P3a",
        "reason_code": "p3_stay_build_evidence",
        "selector_config_version": "score-threshold-v1",
        "delivered_bank_id": "moderate-1",
        "delivered_difficulty": "Moderate",
    }
    values.update(overrides)
    return PolicyEvaluationAuditJoin(**values)


class PolicyEvaluationExportContractTests(unittest.TestCase):
    def test_export_carries_server_only_audit_join_fields(self):
        dataset = build_dataset(standard_history())
        audits = {
            "a1": audit_for("a1"),
            "b3": audit_for("b3", assigned_arm="P2", reason_code="p2_agreement_promote"),
        }
        with TemporaryDirectory() as temporary_directory:
            files = export_real_attempts(
                dataset,
                temporary_directory,
                release=approved_release(),
                pseudonymization_key="aqc2-hmac-key",
                policy_evaluation_audits=audits,
            )
            manifest = json.loads(files["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(manifest["policyEvaluationAuditCount"], 2)
            self.assertEqual(
                list(manifest["policyEvaluationJoinFields"]),
                list(POLICY_EVALUATION_AUDIT_FIELDS),
            )
            with files["attempts"].open(encoding="utf-8") as attempts_file:
                rows = list(csv.DictReader(attempts_file))
            self.assertTrue(any(row["policyEvaluationDecisionId"] for row in rows))
            reloaded = load_csv_files(
                files["attempts"], files["responses"], provenance="real"
            )
            self.assertEqual(len(reloaded.policy_evaluation_audit_by_attempt), 2)
            joined = next(
                audit
                for audit in reloaded.policy_evaluation_audit_by_attempt.values()
                if audit.decision_id == audits["a1"].decision_id
            )
            self.assertEqual(joined.decision_id, audits["a1"].decision_id)
            self.assertEqual(joined.assigned_arm, "P3a")
            self.assertEqual(joined.delivered_difficulty, "Moderate")

    def test_invalid_arm_and_unknown_attempt_fail_closed(self):
        dataset = build_dataset(standard_history())
        with self.assertRaisesRegex(ValueError, "arm is not allowed"):
            audit_for("a1", assigned_arm="P9")
        with TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(ValueError, "unknown attempt"):
                export_real_attempts(
                    dataset,
                    temporary_directory,
                    release=approved_release(),
                    pseudonymization_key="key",
                    policy_evaluation_audits={"not-an-attempt": audit_for("a1")},
                )

    def test_deterministic_export_with_same_audits_and_key(self):
        dataset = build_dataset(standard_history())
        audits = {"a1": audit_for("a1")}
        with TemporaryDirectory() as first_directory, TemporaryDirectory() as second_directory:
            first = export_real_attempts(
                dataset,
                first_directory,
                release=approved_release(),
                pseudonymization_key="same-key",
                policy_evaluation_audits=audits,
            )
            second = export_real_attempts(
                dataset,
                second_directory,
                release=approved_release(),
                pseudonymization_key="same-key",
                policy_evaluation_audits=audits,
            )
            first_manifest = json.loads(first["manifest"].read_text(encoding="utf-8"))
            second_manifest = json.loads(second["manifest"].read_text(encoding="utf-8"))
        self.assertEqual(first_manifest["fileSha256"], second_manifest["fileSha256"])
        self.assertEqual(first_manifest["policyEvaluationAuditCount"], 1)

    def test_export_never_exposes_raw_ids_answer_text_or_key_material(self):
        dataset = build_dataset(standard_history())
        with TemporaryDirectory() as temporary_directory:
            files = export_real_attempts(
                dataset,
                temporary_directory,
                release=approved_release(),
                pseudonymization_key="do-not-write-aqc2-key",
                policy_evaluation_audits={"a1": audit_for("a1")},
            )
            attempts_text = files["attempts"].read_text(encoding="utf-8")
            manifest = json.loads(files["manifest"].read_text(encoding="utf-8"))
        self.assertNotIn("student-a", attempts_text)
        self.assertNotIn("do-not-write-aqc2-key", json.dumps(manifest))
        self.assertFalse(manifest["containsRawIdentifiers"])
        self.assertFalse(manifest["containsSecretMaterial"])
        self.assertNotIn(str(temporary_directory), json.dumps(manifest))


if __name__ == "__main__":
    unittest.main()
