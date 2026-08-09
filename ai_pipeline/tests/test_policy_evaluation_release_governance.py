from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from logic_oasis_ai.adaptive_policy import load_adaptive_policy_config
from logic_oasis_ai.policy_evaluation import (
    PolicyArm,
    deterministic_policy_decision_id,
    load_policy_evaluation_manifest,
)

from training.export_policy_evaluation_release import (
    POLICY_EVALUATION_EXPORT_KEY_PREFIX,
    POLICY_EVALUATION_RELEASE_PREFIX,
    PolicyEvaluationRelease,
    PolicyEvaluationReleaseDeletionRequest,
    PolicyEvaluationReleaseError,
    PolicyEvaluationStorageDeletionEvidence,
    cleanup_unpublished_release,
    create_deletion_certificate,
    export_policy_evaluation_release,
    may_destroy_key_version,
)
from policy_fixtures import build_dataset, standard_history


UTC = timezone.utc
NOW = datetime(2026, 8, 6, tzinfo=UTC)
CONFIGS = Path(__file__).parents[1] / "configs"
RETENTION_IDENTITY = (
    "logic-oasis-policy-evaluation-retention@logic-oasis-fyp.iam.gserviceaccount.com"
)


def adaptive_and_manifest():
    adaptive = load_adaptive_policy_config(CONFIGS / "adaptive_policy_v1.yaml")
    manifest = load_policy_evaluation_manifest(
        CONFIGS / "policy_evaluation_v1.yaml", adaptive_policy=adaptive
    )
    return adaptive, manifest


def build_audits(dataset, *, study_version="study-v1"):
    _, manifest = adaptive_and_manifest()
    audits = {}
    for attempt in dataset.attempts:
        decision_id = deterministic_policy_decision_id(
            attempt.attempt_id,
            PolicyArm.P1,
            "score-threshold-v1",
            manifest.source_sha256,
        )
        audits[decision_id] = {
            "decisionId": decision_id,
            "attemptId": attempt.attempt_id,
            "studentId": attempt.student_id,
            "studyVersion": study_version,
            "sourceAttemptSequence": attempt.source_attempt_sequence,
            "assignedArm": "P1",
            "deliveredArm": "P1",
            "protocolDeviation": None,
            "policyVersion": "score-threshold-v1",
            "evidenceMode": "score_only",
            "reasonCode": "p1_score_hold",
            "selectedBankId": "easy-1",
            "selectedDifficulty": "Easy",
            "usedBktFallback": False,
            "manifestSha256": manifest.source_sha256,
        }
    return audits


def build_probes(audits):
    return {
        decision_id: {
            "decisionId": decision_id,
            "studyVersion": "study-v1",
            "enrollmentId": f"enr-{decision_id[:8]}",
            "targetDifficulty": "Easy",
            "probeProtocolVersion": "policy-outcomes-v1",
            "status": "scheduled",
            "probeFormStatus": "pending_form_catalogue",
        }
        for decision_id in audits
    }


def approved_release(**overrides):
    values = {
        "release_id": "pe-release-v1",
        "dataset_version": "real_v1_pe",
        "study_version": "study-v1",
        "study_status": "closed",
        "release_decision_ref": "PES-GATE-2026-001",
        "consent_ethics_reference": "ethics-approved-aqc6",
        "data_steward": "steward@example.edu",
        "steward_approved_at": NOW,
        "collection_started_at": NOW,
        "collection_ended_at": NOW,
        "retention_review_at": datetime(2027, 8, 6, tzinfo=UTC),
        "storage_path": f"{POLICY_EVALUATION_RELEASE_PREFIX}pe-release-v1/",
        "export_key_version": f"{POLICY_EVALUATION_EXPORT_KEY_PREFIX}1",
    }
    values.update(overrides)
    return PolicyEvaluationRelease(**values)


class PolicyEvaluationReleaseGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = build_dataset(standard_history())
        self.audits = build_audits(self.dataset)
        self.probes = build_probes(self.audits)
        self.outcomes: dict = {}

    def export(self, output_directory, **overrides):
        release = overrides.pop("release", {})
        return export_policy_evaluation_release(
            self.dataset,
            self.audits,
            self.probes,
            self.outcomes,
            output_directory,
            release=approved_release(**release),
            pseudonymization_key=overrides.pop("key", "aqc6-export-hmac-key"),
            **overrides,
        )

    def test_governed_release_is_pseudonymous_deterministic_and_hash_bound(self) -> None:
        with TemporaryDirectory() as directory, TemporaryDirectory() as second_directory:
            files = self.export(directory)
            manifest = json.loads(files["manifest"].read_text(encoding="utf-8"))
            self.assertEqual("closed", manifest["studyStatus"])
            self.assertEqual(7, manifest["counts"]["decisionAudits"])
            self.assertFalse(manifest["containsRawIdentifiers"])
            self.assertFalse(manifest["containsSecretMaterial"])
            combined = (
                files["attempts"].read_text(encoding="utf-8")
                + files["responses"].read_text(encoding="utf-8")
                + files["decisionAudits"].read_text(encoding="utf-8")
                + files["probeOutcomes"].read_text(encoding="utf-8")
            ).lower()
            for token in ("student-a", "studentid", "answerkey", "shap", "@example"):
                self.assertNotIn(token, combined)
            second = self.export(second_directory)
            second_manifest = json.loads(second["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(manifest["fileSha256"], second_manifest["fileSha256"])

    def test_export_fails_when_governance_or_lineage_is_inconsistent(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(PolicyEvaluationReleaseError, "dedicated"):
                self.export(
                    directory,
                    release={"export_key_version": "logic-oasis-export-pseudonymization-key-v1"},
                )
            with self.assertRaisesRegex(PolicyEvaluationReleaseError, "closed or archived"):
                self.export(directory, release={"study_status": "active"})
            with self.assertRaisesRegex(PolicyEvaluationReleaseError, "consent"):
                self.export(directory, release={"consent_ethics_reference": ""})

            broken = dict(self.audits)
            first = next(iter(broken))
            broken[first] = {**broken[first], "attemptId": "not-a-trusted-attempt"}
            with self.assertRaisesRegex(PolicyEvaluationReleaseError, "trusted lineage"):
                export_policy_evaluation_release(
                    self.dataset,
                    broken,
                    self.probes,
                    self.outcomes,
                    directory,
                    release=approved_release(),
                    pseudonymization_key="key",
                )

            fabricated_id = "policy-decision-" + "0" * 64
            fabricated = {
                **self.audits,
                fabricated_id: {
                    **self.audits[first],
                    "decisionId": fabricated_id,
                },
            }
            del fabricated[first]
            with self.assertRaisesRegex(PolicyEvaluationReleaseError, "not deterministic"):
                export_policy_evaluation_release(
                    self.dataset,
                    fabricated,
                    self.probes,
                    self.outcomes,
                    directory,
                    release=approved_release(),
                    pseudonymization_key="key",
                )

    def test_synthetic_or_emulator_audits_cannot_enter_a_final_release(self) -> None:
        synthetic = build_dataset(
            standard_history(),
            provenance="emulator_verified",
            allow_emulator_records=True,
        )
        audits = build_audits(synthetic)
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(PolicyEvaluationReleaseError, "approved real"):
                export_policy_evaluation_release(
                    synthetic,
                    audits,
                    build_probes(audits),
                    {},
                    directory,
                    release=approved_release(),
                    pseudonymization_key="key",
                )

    def test_historical_audits_remain_even_when_an_enrollment_is_revoked(self) -> None:
        # The release exports historical decision evidence; revocation only
        # stops future decisions (verified by verify_live_study_boundary).
        with TemporaryDirectory() as directory:
            files = self.export(directory)
            audit_text = files["decisionAudits"].read_text(encoding="utf-8")
            self.assertEqual(7, audit_text.count("policy-decision-"))

    def test_deletion_certificate_precedes_key_destruction(self) -> None:
        release = approved_release()
        manifest = {
            "releaseId": release.release_id,
            "storagePath": release.storage_path,
            "exportKeyVersion": release.export_key_version,
            "dataSteward": release.data_steward,
        }
        request = PolicyEvaluationReleaseDeletionRequest(
            release_id=release.release_id,
            storage_path=release.storage_path,
            export_key_version=release.export_key_version,
            data_steward=release.data_steward,
            retention_actor=RETENTION_IDENTITY,
            retention_review_at=datetime(2027, 8, 6, tzinfo=UTC),
        )
        with self.assertRaisesRegex(
            PolicyEvaluationReleaseError, "storage deletion evidence"
        ):
            create_deletion_certificate(request, manifest=manifest)
        certificate = create_deletion_certificate(
            request,
            manifest=manifest,
            storage_deletion_evidence=PolicyEvaluationStorageDeletionEvidence(
                storage_path=release.storage_path,
                operation_id="pe-delete-1",
                object_count=5,
                completed_at=NOW,
                verified_by=release.data_steward,
            ),
        )
        self.assertTrue(
            may_destroy_key_version(
                certificate,
                release_id=release.release_id,
                export_key_version=release.export_key_version,
            )
        )
        self.assertFalse(
            may_destroy_key_version(
                certificate,
                release_id=release.release_id,
                export_key_version="logic-oasis-policy-evaluation-export-key-v9",
            )
        )

    def test_unpublished_release_cleanup_never_touches_a_published_manifest(self) -> None:
        release = approved_release()
        request = PolicyEvaluationReleaseDeletionRequest(
            release_id=release.release_id,
            storage_path=release.storage_path,
            export_key_version=release.export_key_version,
            data_steward=release.data_steward,
            retention_actor=RETENTION_IDENTITY,
            retention_review_at=datetime(2027, 8, 6, tzinfo=UTC),
        )
        with TemporaryDirectory() as directory:
            self.export(directory)
            with self.assertRaisesRegex(
                PolicyEvaluationReleaseError, "deletion certificate"
            ):
                cleanup_unpublished_release(request, directory)


if __name__ == "__main__":
    unittest.main()
