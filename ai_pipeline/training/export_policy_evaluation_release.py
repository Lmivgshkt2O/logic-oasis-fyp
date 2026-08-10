"""AQC-6 governed, pseudonymized policy-evaluation release export.

The release joins trusted finalized attempts, create-only decision audits, and
separate probe/outcome documents under a declared closed or bounded study
manifest.  It uses a dedicated export HMAC key and never reuses the real-data
export key.  Outputs contain only pseudonymous assigned/delivered arm, policy
version, decision/probe/outcome/censoring fields, protocol-deviation flags,
and aggregate-compatible bank metadata.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Any, Iterable, Mapping

from logic_oasis_ai.policy_evaluation import (
    PolicyArm,
    deterministic_policy_decision_id,
)
from logic_oasis_ai.sources.firestore_source import SourceDataset

from .export_real_attempts import (
    ATTEMPT_FIELDS,
    RESPONSE_FIELDS,
    _attempt_rows,
    _file_sha256,
    _response_rows,
    _write_csv,
    hmac_pseudonym,
)


POLICY_EVALUATION_RELEASE_PREFIX = (
    "gs://logic-oasis-fyp-protected-data/policy-evaluation-releases/"
)
POLICY_EVALUATION_EXPORT_KEY_PREFIX = "logic-oasis-policy-evaluation-export-key-v"
POLICY_EVALUATION_RELEASE_SCHEMA_VERSION = "policy-evaluation-release-v1"
POLICY_EVALUATION_DELETION_CERTIFICATE_VERSION = (
    "policy-evaluation-deletion-certificate-v1"
)
POLICY_EVALUATION_RETENTION_IDENTITY = (
    "logic-oasis-policy-evaluation-retention@logic-oasis-fyp.iam.gserviceaccount.com"
)
RELEASABLE_STUDY_STATUSES = frozenset({"closed", "archived"})
ALLOWED_ARMS = frozenset({"P1", "P2", "P3a", "P3b"})
ALLOWED_EVIDENCE_MODES = frozenset(
    {"score_only", "bkt_score_agreement", "bkt_only_study", "model_assisted"}
)

AUDIT_FIELDS = (
    "decisionId",
    "attemptKey",
    "studentKey",
    "studyVersion",
    "assignedArm",
    "deliveredArm",
    "protocolDeviation",
    "policyVersion",
    "evidenceMode",
    "reasonCode",
    "selectedBankId",
    "selectedDifficulty",
    "usedBktFallback",
    "sourceAttemptSequence",
)
PROBE_OUTCOME_FIELDS = (
    "decisionId",
    "studentKey",
    "targetDifficulty",
    "probeStatus",
    "probeFormStatus",
    "outcomeStatus",
    "censoredReason",
    "supportNeeded",
    "stratum",
    "laterAttemptKey",
)
FORBIDDEN_OUTPUT_TOKENS = (
    "studentId",
    "email",
    "answerKey",
    "answerText",
    "shap",
    "artifactPath",
    "errorTrace",
)


class PolicyEvaluationReleaseError(ValueError):
    """Raised when a governed release cannot be produced safely."""


@dataclass(frozen=True)
class PolicyEvaluationRelease:
    """Approval/custody record for one policy-evaluation data release."""

    release_id: str
    dataset_version: str
    study_version: str
    study_status: str
    release_decision_ref: str
    consent_ethics_reference: str
    data_steward: str
    steward_approved_at: datetime
    collection_started_at: datetime
    collection_ended_at: datetime
    retention_review_at: datetime
    storage_path: str
    export_key_version: str

    def __post_init__(self) -> None:
        for field in (
            "release_id",
            "dataset_version",
            "study_version",
            "study_status",
            "release_decision_ref",
            "consent_ethics_reference",
            "data_steward",
            "storage_path",
            "export_key_version",
        ):
            if not getattr(self, field):
                raise PolicyEvaluationReleaseError(f"{field} is required")
        expected_path = f"{POLICY_EVALUATION_RELEASE_PREFIX}{self.release_id}/"
        if self.storage_path != expected_path:
            raise PolicyEvaluationReleaseError(
                "release storage_path must be its protected versioned release path"
            )
        if not self.export_key_version.startswith(POLICY_EVALUATION_EXPORT_KEY_PREFIX):
            raise PolicyEvaluationReleaseError(
                "policy-evaluation releases require the dedicated export HMAC key"
            )
        if self.study_status not in RELEASABLE_STUDY_STATUSES:
            raise PolicyEvaluationReleaseError(
                "only a closed or archived study manifest may be released"
            )
        timestamps = (
            self.steward_approved_at,
            self.collection_started_at,
            self.collection_ended_at,
            self.retention_review_at,
        )
        if any(value.tzinfo is None for value in timestamps):
            raise PolicyEvaluationReleaseError(
                "release timestamps must include a timezone"
            )
        if self.collection_ended_at < self.collection_started_at:
            raise PolicyEvaluationReleaseError(
                "collection end must not precede collection start"
            )


def export_policy_evaluation_release(
    dataset: SourceDataset,
    audits: Mapping[str, Mapping[str, Any]],
    probes: Mapping[str, Mapping[str, Any]],
    outcomes: Mapping[str, Mapping[str, Any]],
    output_directory: str | Path,
    *,
    release: PolicyEvaluationRelease,
    pseudonymization_key: bytes | str,
) -> dict[str, Path]:
    """Write a deterministic, governed, pseudonymized release."""
    _validate_release_inputs(
        dataset,
        audits,
        probes,
        outcomes,
        release=release,
        pseudonymization_key=pseudonymization_key,
    )
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    file_names = (
        "attempts.csv",
        "responses.csv",
        "decision_audits.csv",
        "probe_outcomes.csv",
        "manifest.json",
    )
    if any((output / name).exists() for name in file_names):
        raise FileExistsError("a governed release path is immutable once publication starts")

    attempt_keys = {
        attempt.attempt_id: hmac_pseudonym(
            "policy-evaluation-attempt", attempt.attempt_id, pseudonymization_key
        )
        for attempt in dataset.attempts
    }
    session_keys = {
        attempt.session_id: hmac_pseudonym(
            "policy-evaluation-session", attempt.session_id, pseudonymization_key
        )
        for attempt in dataset.attempts
    }
    response_keys = {
        response.response_id: hmac_pseudonym(
            "policy-evaluation-response", response.response_id, pseudonymization_key
        )
        for responses in dataset.responses_by_attempt.values()
        for response in responses
    }
    student_key = {
        attempt.student_id: hmac_pseudonym(
            "student", attempt.student_id, pseudonymization_key
        )
        for attempt in dataset.attempts
    }
    audit_rows = _audit_rows(audits, attempt_keys, student_key)
    probe_rows = _probe_outcome_rows(
        probes, outcomes, audits, student_key, attempt_keys
    )

    staging = Path(mkdtemp(prefix=".policy-release-staging-", dir=output))
    try:
        staged_attempts = staging / "attempts.csv"
        staged_responses = staging / "responses.csv"
        staged_audits = staging / "decision_audits.csv"
        staged_probes = staging / "probe_outcomes.csv"
        _write_csv(
            staged_attempts,
            ATTEMPT_FIELDS,
            _attempt_rows(
                dataset,
                attempt_keys,
                session_keys,
                response_keys,
                pseudonymization_key,
                {},
            ),
        )
        _write_csv(
            staged_responses,
            RESPONSE_FIELDS,
            _response_rows(
                dataset, attempt_keys, session_keys, response_keys, pseudonymization_key
            ),
        )
        _write_csv(staged_audits, AUDIT_FIELDS, audit_rows)
        _write_csv(staged_probes, PROBE_OUTCOME_FIELDS, probe_rows)
        manifest = _manifest(
            release,
            dataset,
            audits,
            probes,
            outcomes,
            staged_attempts,
            staged_responses,
            staged_audits,
            staged_probes,
        )
        _assert_safe_manifest(manifest, pseudonymization_key)
        staged_manifest = staging / "manifest.json"
        staged_manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        for staged, final_name in (
            (staged_attempts, "attempts.csv"),
            (staged_responses, "responses.csv"),
            (staged_audits, "decision_audits.csv"),
            (staged_probes, "probe_outcomes.csv"),
            (staged_manifest, "manifest.json"),
        ):
            staged.replace(output / final_name)
        return {
            "attempts": output / "attempts.csv",
            "responses": output / "responses.csv",
            "decisionAudits": output / "decision_audits.csv",
            "probeOutcomes": output / "probe_outcomes.csv",
            "manifest": output / "manifest.json",
        }
    finally:
        rmtree(staging, ignore_errors=True)


def _validate_release_inputs(
    dataset: SourceDataset,
    audits: Mapping[str, Mapping[str, Any]],
    probes: Mapping[str, Mapping[str, Any]],
    outcomes: Mapping[str, Mapping[str, Any]],
    *,
    release: PolicyEvaluationRelease,
    pseudonymization_key: bytes | str,
) -> None:
    if dataset.provenance != "real":
        raise PolicyEvaluationReleaseError(
            "only approved real records may enter a policy-evaluation release"
        )
    if not pseudonymization_key:
        raise PolicyEvaluationReleaseError("a non-empty HMAC key is required")
    if not audits:
        raise PolicyEvaluationReleaseError(
            "at least one create-only decision audit is required"
        )
    attempts_by_id = {attempt.attempt_id: attempt for attempt in dataset.attempts}
    for decision_id, audit in audits.items():
        _validate_audit(decision_id, audit, attempts_by_id, release=release)
    for decision_id in probes:
        if decision_id not in audits:
            raise PolicyEvaluationReleaseError(
                f"probe references unknown decision audit: {decision_id}"
            )
    for decision_id in outcomes:
        if decision_id not in audits:
            raise PolicyEvaluationReleaseError(
                f"outcome references unknown decision audit: {decision_id}"
            )


def _validate_audit(
    decision_id: str,
    audit: Mapping[str, Any],
    attempts_by_id: Mapping[str, Any],
    *,
    release: PolicyEvaluationRelease,
) -> None:
    if str(audit.get("decisionId")) != decision_id:
        raise PolicyEvaluationReleaseError("audit decisionId does not match its key")
    attempt_id = audit.get("attemptId")
    attempt = attempts_by_id.get(attempt_id)
    if attempt is None:
        raise PolicyEvaluationReleaseError(
            "audit references an attempt outside the trusted lineage"
        )
    if audit.get("studentId") != attempt.student_id:
        raise PolicyEvaluationReleaseError("audit student does not match its attempt")
    if audit.get("studyVersion") != release.study_version:
        raise PolicyEvaluationReleaseError(
            "audit study version does not match the release study manifest"
        )
    if int(audit.get("sourceAttemptSequence", -1)) != attempt.source_attempt_sequence:
        raise PolicyEvaluationReleaseError(
            "audit sourceAttemptSequence does not match its attempt"
        )
    assigned_arm = audit.get("assignedArm")
    delivered_arm = audit.get("deliveredArm")
    if assigned_arm not in ALLOWED_ARMS or delivered_arm not in ALLOWED_ARMS:
        raise PolicyEvaluationReleaseError("audit arm is not allowed")
    if audit.get("evidenceMode") not in ALLOWED_EVIDENCE_MODES:
        raise PolicyEvaluationReleaseError("audit evidence mode is not allowed")
    manifest_sha = audit.get("manifestSha256")
    if not isinstance(manifest_sha, str) or len(manifest_sha) != 64:
        raise PolicyEvaluationReleaseError("audit manifestSha256 is invalid")
    policy_version = audit.get("policyVersion")
    if not isinstance(policy_version, str) or not policy_version:
        raise PolicyEvaluationReleaseError("audit policyVersion is required")
    deviation = audit.get("protocolDeviation")
    if deviation == "selector_failed":
        if not str(decision_id).startswith("policy-decision-"):
            raise PolicyEvaluationReleaseError("failure audit decisionId is invalid")
        return
    expected_id = deterministic_policy_decision_id(
        str(attempt_id),
        PolicyArm(str(delivered_arm)),
        str(policy_version),
        str(manifest_sha),
    )
    if expected_id != str(decision_id):
        raise PolicyEvaluationReleaseError(
            "audit decisionId is not deterministic for its delivered arm"
        )


def _audit_rows(
    audits: Mapping[str, Mapping[str, Any]],
    attempt_keys: Mapping[str, str],
    student_keys: Mapping[str, str],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for decision_id in sorted(audits):
        audit = audits[decision_id]
        rows.append(
            {
                "decisionId": decision_id,
                "attemptKey": attempt_keys.get(str(audit["attemptId"]), ""),
                "studentKey": student_keys.get(str(audit["studentId"]), ""),
                "studyVersion": str(audit["studyVersion"]),
                "assignedArm": str(audit["assignedArm"]),
                "deliveredArm": str(audit["deliveredArm"]),
                "protocolDeviation": audit.get("protocolDeviation") or "",
                "policyVersion": str(audit["policyVersion"]),
                "evidenceMode": str(audit["evidenceMode"]),
                "reasonCode": str(audit["reasonCode"]),
                "selectedBankId": audit.get("selectedBankId") or "",
                "selectedDifficulty": audit.get("selectedDifficulty") or "",
                "usedBktFallback": bool(audit.get("usedBktFallback")),
                "sourceAttemptSequence": int(audit["sourceAttemptSequence"]),
            }
        )
    return rows


def _probe_outcome_rows(
    probes: Mapping[str, Mapping[str, Any]],
    outcomes: Mapping[str, Mapping[str, Any]],
    audits: Mapping[str, Mapping[str, Any]],
    student_keys: Mapping[str, str],
    attempt_keys: Mapping[str, str],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for decision_id in sorted(probes):
        probe = probes[decision_id]
        outcome = outcomes.get(decision_id, {})
        audit = audits[decision_id]
        rows.append(
            {
                "decisionId": decision_id,
                "studentKey": student_keys.get(str(audit.get("studentId", "")), ""),
                "targetDifficulty": str(probe.get("targetDifficulty", "")),
                "probeStatus": str(probe.get("status", "")),
                "probeFormStatus": str(probe.get("probeFormStatus", "")),
                "outcomeStatus": outcome.get("outcomeStatus") or "",
                "censoredReason": outcome.get("censoredReason") or "",
                "supportNeeded": outcome.get("supportNeeded") if outcome else "",
                "stratum": outcome.get("stratum") or "",
                "laterAttemptKey": attempt_keys.get(str(outcome.get("laterAttemptId", "")), "")
                if outcome
                else "",
            }
        )
    return rows


def _manifest(
    release: PolicyEvaluationRelease,
    dataset: SourceDataset,
    audits: Mapping[str, Mapping[str, Any]],
    probes: Mapping[str, Mapping[str, Any]],
    outcomes: Mapping[str, Mapping[str, Any]],
    attempts_path: Path,
    responses_path: Path,
    audits_path: Path,
    probes_path: Path,
) -> dict[str, object]:
    return {
        "releaseSchemaVersion": POLICY_EVALUATION_RELEASE_SCHEMA_VERSION,
        "releaseId": release.release_id,
        "datasetVersion": release.dataset_version,
        "studyVersion": release.study_version,
        "studyStatus": release.study_status,
        "releaseDecisionRef": release.release_decision_ref,
        "consentEthicsReference": release.consent_ethics_reference,
        "provenance": "real",
        "exportKeyVersion": release.export_key_version,
        "dataSteward": release.data_steward,
        "stewardApprovedAt": release.steward_approved_at.isoformat(),
        "collectionWindow": {
            "startedAt": release.collection_started_at.isoformat(),
            "endedAt": release.collection_ended_at.isoformat(),
        },
        "storagePath": release.storage_path,
        "retentionReviewAt": release.retention_review_at.isoformat(),
        "counts": {
            "attempts": len(dataset.attempts),
            "responses": sum(len(rows) for rows in dataset.responses_by_attempt.values()),
            "decisionAudits": len(audits),
            "probes": len(probes),
            "outcomes": len(outcomes),
        },
        "fileSha256": {
            "attempts.csv": _file_sha256(attempts_path),
            "responses.csv": _file_sha256(responses_path),
            "decision_audits.csv": _file_sha256(audits_path),
            "probe_outcomes.csv": _file_sha256(probes_path),
        },
        "pseudonymizationNamespaces": [
            "student",
            "policy-evaluation-attempt",
            "policy-evaluation-session",
            "policy-evaluation-response",
        ],
        "sourceAttemptOrdering": "(sourceAttemptSequence, sequenceIndex)",
        "containsRawIdentifiers": False,
        "containsSecretMaterial": False,
    }


def _assert_safe_manifest(manifest: dict[str, object], key: bytes | str) -> None:
    serialized = json.dumps(manifest, sort_keys=True)
    key_text = key.decode("utf-8", errors="ignore") if isinstance(key, bytes) else key
    if key_text and key_text in serialized:
        raise PolicyEvaluationReleaseError("manifest must not contain HMAC key material")
    if "\\\\" in serialized or ":\\\\" in serialized:
        raise PolicyEvaluationReleaseError("manifest must not contain a local path")


@dataclass(frozen=True)
class PolicyEvaluationReleaseDeletionRequest:
    release_id: str
    storage_path: str
    export_key_version: str
    data_steward: str
    retention_actor: str
    retention_review_at: datetime

    def __post_init__(self) -> None:
        if not all(
            (
                self.release_id,
                self.storage_path,
                self.export_key_version,
                self.data_steward,
                self.retention_actor,
            )
        ):
            raise PolicyEvaluationReleaseError(
                "release deletion request fields are required"
            )
        if self.storage_path != f"{POLICY_EVALUATION_RELEASE_PREFIX}{self.release_id}/":
            raise PolicyEvaluationReleaseError(
                "deletion may target only its protected release path"
            )
        if not self.export_key_version.startswith(POLICY_EVALUATION_EXPORT_KEY_PREFIX):
            raise PolicyEvaluationReleaseError(
                "deletion must name the dedicated policy-evaluation export HMAC key"
            )
        if self.retention_actor != POLICY_EVALUATION_RETENTION_IDENTITY:
            raise PolicyEvaluationReleaseError(
                "only the declared retention identity may perform release cleanup"
            )
        if self.retention_review_at.tzinfo is None:
            raise PolicyEvaluationReleaseError(
                "retention_review_at must include a timezone"
            )


@dataclass(frozen=True)
class PolicyEvaluationStorageDeletionEvidence:
    storage_path: str
    operation_id: str
    object_count: int
    completed_at: datetime
    verified_by: str

    def __post_init__(self) -> None:
        if not self.storage_path.startswith(POLICY_EVALUATION_RELEASE_PREFIX):
            raise PolicyEvaluationReleaseError(
                "deletion evidence must name a protected release path"
            )
        if not self.operation_id or not self.verified_by:
            raise PolicyEvaluationReleaseError(
                "deletion evidence operation and verifier are required"
            )
        if (
            isinstance(self.object_count, bool)
            or not isinstance(self.object_count, int)
            or self.object_count < 0
        ):
            raise PolicyEvaluationReleaseError(
                "deletion evidence object_count must be a non-negative integer"
            )
        if self.completed_at.tzinfo is None:
            raise PolicyEvaluationReleaseError(
                "deletion evidence completed_at must include a timezone"
            )


def create_deletion_certificate(
    request: PolicyEvaluationReleaseDeletionRequest,
    *,
    manifest: dict[str, object],
    storage_deletion_evidence: PolicyEvaluationStorageDeletionEvidence | None = None,
) -> dict[str, object]:
    _validate_manifest_for_deletion(request, manifest)
    if storage_deletion_evidence is None:
        raise PolicyEvaluationReleaseError(
            "verified storage deletion evidence is required"
        )
    if storage_deletion_evidence.storage_path != request.storage_path:
        raise PolicyEvaluationReleaseError(
            "deletion evidence does not match request storage path"
        )
    return {
        "certificateVersion": POLICY_EVALUATION_DELETION_CERTIFICATE_VERSION,
        "releaseId": request.release_id,
        "storagePath": request.storage_path,
        "exportKeyVersion": request.export_key_version,
        "dataSteward": request.data_steward,
        "retentionActor": request.retention_actor,
        "retentionReviewAt": request.retention_review_at.isoformat(),
        "deletedAt": storage_deletion_evidence.completed_at.isoformat(),
        "storageDeletion": {
            "storagePath": storage_deletion_evidence.storage_path,
            "operationId": storage_deletion_evidence.operation_id,
            "objectCount": storage_deletion_evidence.object_count,
            "completedAt": storage_deletion_evidence.completed_at.isoformat(),
            "verifiedBy": storage_deletion_evidence.verified_by,
        },
        "manifestSha256": sha256(
            json.dumps(manifest, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "keyDestructionAuthorized": True,
    }


def may_destroy_key_version(
    certificate: dict[str, object],
    *,
    release_id: str,
    export_key_version: str,
) -> bool:
    _validate_certificate(certificate)
    return (
        certificate["releaseId"] == release_id
        and certificate["exportKeyVersion"] == export_key_version
        and certificate["keyDestructionAuthorized"] is True
    )


def cleanup_unpublished_release(
    request: PolicyEvaluationReleaseDeletionRequest,
    output_directory: str | Path,
) -> tuple[str, ...]:
    output = Path(output_directory)
    manifest = output / "manifest.json"
    if manifest.exists():
        raise PolicyEvaluationReleaseError(
            "a published release requires its deletion certificate workflow"
        )
    removed: list[str] = []
    for name in ("attempts.csv", "responses.csv", "decision_audits.csv", "probe_outcomes.csv"):
        path = output / name
        if path.exists():
            path.unlink()
            removed.append(name)
    for staging in output.glob(".policy-release-staging-*"):
        if staging.is_dir():
            rmtree(staging)
            removed.append(staging.name)
    return tuple(removed)


def _validate_manifest_for_deletion(
    request: PolicyEvaluationReleaseDeletionRequest,
    manifest: dict[str, object],
) -> None:
    if manifest.get("releaseId") != request.release_id:
        raise PolicyEvaluationReleaseError("deletion request does not match manifest release")
    if manifest.get("storagePath") != request.storage_path:
        raise PolicyEvaluationReleaseError(
            "deletion request does not match manifest storage path"
        )
    if manifest.get("exportKeyVersion") != request.export_key_version:
        raise PolicyEvaluationReleaseError(
            "deletion request does not match manifest export key version"
        )
    if manifest.get("dataSteward") != request.data_steward:
        raise PolicyEvaluationReleaseError("deletion request does not match manifest steward")


def _validate_certificate(certificate: dict[str, object]) -> None:
    required = (
        "certificateVersion",
        "releaseId",
        "storagePath",
        "exportKeyVersion",
        "dataSteward",
        "retentionActor",
        "deletedAt",
        "manifestSha256",
        "keyDestructionAuthorized",
    )
    if any(not certificate.get(field) for field in required[:-1]):
        raise PolicyEvaluationReleaseError("deletion certificate is incomplete")
    if certificate.get("certificateVersion") != POLICY_EVALUATION_DELETION_CERTIFICATE_VERSION:
        raise PolicyEvaluationReleaseError("unsupported deletion certificate version")
    if certificate.get("keyDestructionAuthorized") is not True:
        raise PolicyEvaluationReleaseError(
            "deletion certificate does not authorize key destruction"
        )
    deletion = certificate.get("storageDeletion")
    if not isinstance(deletion, dict):
        raise PolicyEvaluationReleaseError(
            "deletion certificate lacks storage deletion evidence"
        )
    required_deletion_fields = (
        "storagePath",
        "operationId",
        "objectCount",
        "completedAt",
        "verifiedBy",
    )
    if any(
        not deletion.get(field)
        for field in required_deletion_fields
        if field != "objectCount"
    ):
        raise PolicyEvaluationReleaseError(
            "deletion certificate has incomplete storage deletion evidence"
        )
    if deletion.get("storagePath") != certificate.get("storagePath"):
        raise PolicyEvaluationReleaseError(
            "deletion certificate storage evidence path does not match"
        )
    if isinstance(deletion.get("objectCount"), bool) or not isinstance(
        deletion.get("objectCount"), int
    ):
        raise PolicyEvaluationReleaseError(
            "deletion certificate storage evidence object count is invalid"
        )
