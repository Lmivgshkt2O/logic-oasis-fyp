"""AQC-6 live and release verification for the policy-evaluation study.

``verify_release_artifacts`` proves a published release is deterministic,
hash-bound, free of protected content, and derived from a closed study.
``verify_live_study_boundary`` proves revoked enrollments receive no new
decisions and every audit traces to a real enrollment.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Mapping

from training.export_real_attempts import _file_sha256
from training.export_policy_evaluation_release import (
    FORBIDDEN_OUTPUT_TOKENS,
    RELEASABLE_STUDY_STATUSES,
)


class PolicyEvaluationVerificationError(ValueError):
    """Raised when a release or live boundary cannot be verified."""


def verify_release_artifacts(release_directory: str | Path) -> dict[str, object]:
    """Verify a published policy-evaluation release artifact set."""
    output = Path(release_directory)
    manifest_path = output / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PolicyEvaluationVerificationError(
            "release manifest is unavailable or malformed"
        ) from error
    if not isinstance(manifest, dict):
        raise PolicyEvaluationVerificationError("release manifest must be an object")
    required = (
        "releaseSchemaVersion",
        "releaseId",
        "studyVersion",
        "studyStatus",
        "releaseDecisionRef",
        "exportKeyVersion",
        "fileSha256",
        "counts",
        "containsRawIdentifiers",
        "containsSecretMaterial",
    )
    for field in required:
        if field not in manifest:
            raise PolicyEvaluationVerificationError(
                f"release manifest is missing {field}"
            )
    if manifest["containsRawIdentifiers"] or manifest["containsSecretMaterial"]:
        raise PolicyEvaluationVerificationError(
            "release manifest claims protected content"
        )
    if manifest["studyStatus"] not in RELEASABLE_STUDY_STATUSES:
        raise PolicyEvaluationVerificationError(
            "release study is not closed or archived"
        )
    for name, expected_hash in manifest["fileSha256"].items():
        path = output / name
        if not path.exists():
            raise PolicyEvaluationVerificationError(
                f"release is missing expected file {name}"
            )
        if _file_sha256(path) != expected_hash:
            raise PolicyEvaluationVerificationError(
                f"release file hash mismatch: {name}"
            )
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for token in FORBIDDEN_OUTPUT_TOKENS:
            if token.lower() in text:
                raise PolicyEvaluationVerificationError(
                    f"release file contains protected content: {name} ({token})"
                )
    counts = manifest["counts"]
    expected_rows = {
        "attempts.csv": int(counts["attempts"]),
        "responses.csv": int(counts["responses"]),
        "decision_audits.csv": int(counts["decisionAudits"]),
        "probe_outcomes.csv": int(counts["probes"]),
    }
    for name, expected in expected_rows.items():
        with (output / name).open(newline="", encoding="utf-8") as file:
            actual = sum(1 for _ in csv.DictReader(file))
        if actual != expected:
            raise PolicyEvaluationVerificationError(
                f"release row count mismatch: {name}"
            )
    return {
        "status": "verified",
        "releaseId": manifest["releaseId"],
        "studyVersion": manifest["studyVersion"],
        "filesVerified": len(manifest["fileSha256"]),
    }


def verify_live_study_boundary(
    database: Any,
    *,
    study_version: str,
    now: datetime | None = None,
) -> dict[str, object]:
    """Prove revoked enrollments get no new decisions and audits have lineage."""
    enrollments = list(
        database.collection("policyEvaluationEnrollments")
        .where("studyVersion", "==", study_version)
        .stream()
    )
    audits = list(
        database.collection("policyEvaluationDecisionAudits")
        .where("studyVersion", "==", study_version)
        .stream()
    )
    enrollment_by_id: dict[str, Mapping[str, Any]] = {}
    for snapshot in enrollments:
        document = dict(snapshot.to_dict() or {})
        document.setdefault("enrollmentId", snapshot.id)
        enrollment_by_id[str(document["enrollmentId"])] = document
    violations: list[Mapping[str, object]] = []
    for snapshot in audits:
        document = dict(snapshot.to_dict() or {})
        enrollment_id = document.get("enrollmentId")
        enrollment = enrollment_by_id.get(str(enrollment_id))
        if enrollment is None:
            violations.append(
                {
                    "type": "orphan_audit",
                    "decisionId": document.get("decisionId"),
                    "enrollmentId": enrollment_id,
                }
            )
            continue
        if enrollment.get("status") == "revoked":
            revoked_at = enrollment.get("revokedAt")
            created_at = document.get("createdAt")
            if revoked_at is not None and created_at is not None and created_at > revoked_at:
                violations.append(
                    {
                        "type": "audit_after_revocation",
                        "decisionId": document.get("decisionId"),
                        "enrollmentId": enrollment_id,
                    }
                )
    return {
        "studyVersion": study_version,
        "enrollmentsChecked": len(enrollments),
        "auditsChecked": len(audits),
        "violations": violations,
        "status": "verified" if not violations else "violation",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify an AQC-6 policy-evaluation release and live boundary"
    )
    parser.add_argument("--release-dir", default=None)
    parser.add_argument("--study-version", default=None)
    args = parser.parse_args()
    if args.release_dir:
        print(json.dumps(verify_release_artifacts(args.release_dir), indent=2))
    if args.study_version:
        import firebase_admin
        from firebase_admin import firestore

        firebase_admin.initialize_app()
        print(
            json.dumps(
                verify_live_study_boundary(
                    firestore.client(), study_version=args.study_version
                ),
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
