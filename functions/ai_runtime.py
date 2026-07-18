"""U8 automatic, idempotent server-side runtime for trusted quiz attempts.

This module has no Flutter-facing surface.  It accepts only U3-R finalized
attempts, computes BKT first, and treats the supervised/XGBoost route as an
optional, registry-bound enhancement.  Safe projections never contain model
paths, hashes, feature vectors, raw SHAP values, or exception text.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from typing import Any, Mapping, Protocol

import yaml

from logic_oasis_ai.adaptive_policy import (
    AssignmentContext, Difficulty, EligibleBank, load_adaptive_policy_config, select_next_bank,
)
from logic_oasis_ai.bkt import build_bkt_materialization
from logic_oasis_ai.explain import explain_prediction
from logic_oasis_ai.features import BASE_FEATURE_NAMES, FEATURE_SCHEMA_VERSION, build_attempt_features
from logic_oasis_ai.inference import InferenceContractError, predict_support_risk
from logic_oasis_ai.sinks.firestore_sink import (
    adaptive_assignment_id, is_newer_projection, mastery_snapshot_id,
    safe_status_document, subtopic_mastery_id,
)
from logic_oasis_ai.sources.firestore_source import load_firestore_dataset


AI_RUNTIME_VERSION = "u8-ai-runtime-v1"
AI_RUNTIME_SERVICE_ACCOUNT = "logic-oasis-ai-runtime@logic-oasis-fyp.iam.gserviceaccount.com"
TERMINAL_STATES = frozenset({"completed", "fallback", "failed"})
MAX_RUNTIME_ATTEMPTS = 3
FALLBACK_CODES = frozenset({
    "model_registry_missing", "model_registry_inactive", "approval_missing",
    "bundle_mismatch", "artifact_hash_mismatch", "model_load_failed",
    "shap_load_failed", "feature_schema_incompatible", "model_target_incompatible",
    "policy_unavailable", "artifact_unavailable", "artifact_hash_invalid", "model_prediction_invalid", "shap_output_invalid",
})
SAFE_ERROR_CODES = FALLBACK_CODES | frozenset({"trusted_source_invalid", "runtime_exhausted"})


class RuntimeFailure(RuntimeError):
    def __init__(self, code: str, *, retryable: bool = False, fallback_available: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.fallback_available = fallback_available


@dataclass(frozen=True)
class RuntimeClaim:
    attempt_count: int
    terminal_state: str | None = None


@dataclass(frozen=True)
class RuntimeBundle:
    package_sha256: str
    feature_schema_sha256: str
    adaptive_policy_sha256: str
    ranking_policy_sha256: str
    adaptive_policy_path: Path
    artifact_root: Path

    @classmethod
    def from_runtime_root(cls, root: str | Path) -> "RuntimeBundle":
        root_path = Path(root).resolve()
        package = root_path / "logic_oasis_ai"
        feature_schema = root_path / "configs" / "feature_schema.yaml"
        adaptive = root_path / "configs" / "adaptive_policy_v1.yaml"
        ranking = root_path / "configs" / "weak_topic_ranking_v1.yaml"
        if not all(path.exists() for path in (package, feature_schema, adaptive, ranking)):
            raise RuntimeFailure("bundle_mismatch", fallback_available=True)
        return cls(
            package_sha256=_tree_sha256(package),
            feature_schema_sha256=_file_sha256(feature_schema),
            adaptive_policy_sha256=_file_sha256(adaptive),
            ranking_policy_sha256=_file_sha256(ranking),
            adaptive_policy_path=adaptive,
            artifact_root=(root_path / "models").resolve(),
        )


class RuntimeGateway(Protocol):
    def claim(self, attempt: Mapping[str, Any]) -> RuntimeClaim: ...
    def attempt(self, attempt_id: str) -> Mapping[str, Any] | None: ...
    def history(self, attempt: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]: ...
    def banks(self, attempt: Mapping[str, Any]) -> list[Mapping[str, Any]]: ...
    def active_registry(self) -> Mapping[str, Any] | None: ...
    def record_retry(self, attempt: Mapping[str, Any], code: str) -> None: ...
    def finalize(self, attempt: Mapping[str, Any], *, state: str, code: str, raw_run: Mapping[str, Any],
                 snapshots: list[Mapping[str, Any]], assignment: Mapping[str, Any] | None,
                 mastery: Mapping[str, Any] | None) -> str: ...


def process_finalized_attempt(attempt_id: str, *, gateway: RuntimeGateway, bundle: RuntimeBundle,
                              provenance: str = "real") -> str:
    """Process one event delivery; rethrow only controlled transient failures."""
    attempt = gateway.attempt(attempt_id)
    if not attempt:
        return "failed"
    claim = gateway.claim(attempt)
    if claim.terminal_state:
        return claim.terminal_state
    try:
        _validate_trusted_attempt(attempt)
        attempts, responses = gateway.history(attempt)
        dataset = load_firestore_dataset(attempts, responses, provenance=provenance,
                                         allow_emulator_records=provenance == "emulator_verified")
        materialization = build_bkt_materialization(dataset.attempts, dataset.responses_by_attempt)
        current = [snapshot for snapshot in materialization.snapshots
                   if snapshot.student_id == attempt["studentId"] and snapshot.subtopic_id == attempt["subtopicId"]
                   and snapshot.source_attempt_sequence == attempt["sourceAttemptSequence"]]
        if not current:
            raise RuntimeFailure("trusted_source_invalid")
        snapshots = [dict(snapshot.to_firestore_document()) for snapshot in current]
        support_risk, model_run = _supervised_or_fallback(attempt, dataset, gateway.active_registry(), bundle)
        state = "completed" if model_run["status"] == "completed" else "fallback"
        primary = current[0]
        assignment = _assignment(attempt, primary.mastery_probability, primary.evidence_count,
                                 support_risk, gateway.banks(attempt), bundle)
        mastery = _subtopic_mastery(attempt, primary, support_risk, bundle)
        return gateway.finalize(attempt, state=state, code=model_run["statusCode"], raw_run=model_run,
                                snapshots=snapshots, assignment=assignment, mastery=mastery)
    except RuntimeFailure as error:
        if error.retryable and claim.attempt_count < MAX_RUNTIME_ATTEMPTS:
            gateway.record_retry(attempt, error.code)
            raise
        state = "fallback" if error.fallback_available else "failed"
        return gateway.finalize(attempt, state=state, code=error.code,
                                raw_run=_fallback_run(attempt, error.code), snapshots=[], assignment=None, mastery=None)
    except Exception:
        if claim.attempt_count < MAX_RUNTIME_ATTEMPTS:
            raise RuntimeFailure("runtime_transient", retryable=True)
        return gateway.finalize(attempt, state="failed", code="runtime_exhausted",
                                raw_run=_fallback_run(attempt, "runtime_exhausted"), snapshots=[], assignment=None, mastery=None)


def _validate_trusted_attempt(attempt: Mapping[str, Any]) -> None:
    required = {
        "attemptId", "studentId", "topicId", "subtopicId", "yearLevel", "sourceAttemptSequence",
        "validationStatus", "finalizationStatus", "dataSource",
    }
    if any(not attempt.get(field) for field in required):
        raise RuntimeFailure("trusted_source_invalid")
    if (attempt.get("validationStatus"), attempt.get("finalizationStatus"), attempt.get("dataSource")) != (
        "finalized", "finalized", "runtime_callable",
    ):
        raise RuntimeFailure("trusted_source_invalid")
    sequence = attempt.get("sourceAttemptSequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise RuntimeFailure("trusted_source_invalid")


def _supervised_or_fallback(attempt: Mapping[str, Any], dataset: Any, registry: Mapping[str, Any] | None,
                            bundle: RuntimeBundle) -> tuple[float | None, dict[str, Any]]:
    fallback = _fallback_run(attempt, "model_registry_missing")
    if not registry:
        return None, fallback
    mismatch = _registry_mismatch(registry, bundle)
    if mismatch:
        return None, _fallback_run(attempt, mismatch)
    rows = build_attempt_features(dataset, anonymization_salt="runtime-not-exported")
    try:
        row = next(item for item in rows if item.source_attempt_sequence == attempt["sourceAttemptSequence"])
    except StopIteration:
        row = rows[-1]
    try:
        with _approved_artifact_path(bundle, registry) as artifact_path:
            prediction = predict_support_risk(artifact_path, expected_sha256=registry["artifactSha256"],
                                              feature_names=BASE_FEATURE_NAMES, feature_values=row.to_model_features())
            explanation = explain_prediction(str(artifact_path), expected_sha256=registry["artifactSha256"],
                                             feature_names=BASE_FEATURE_NAMES, feature_values=prediction.feature_values)
    except (InferenceContractError, RuntimeFailure) as error:
        return None, _fallback_run(attempt, str(error))
    return prediction.support_risk, {
        "attemptId": attempt["attemptId"], "studentId": attempt["studentId"], "status": "completed",
        "statusCode": "model_completed", "modelVersion": registry["modelVersion"],
        "featureSchemaVersion": FEATURE_SCHEMA_VERSION, "predictionTarget": registry["predictionTarget"],
        "labelVersion": registry["labelVersion"], "supportRisk": prediction.support_risk,
        "featureValues": dict(prediction.feature_values), "shapValues": dict(explanation.values),
        "shapExpectedValue": explanation.expected_value, "sourceAttemptSequence": attempt["sourceAttemptSequence"],
        "approvalId": registry["approvalId"], "dataSource": "runtime_callable",
    }


def _registry_mismatch(registry: Mapping[str, Any], bundle: RuntimeBundle) -> str | None:
    if registry.get("isActive") is not True or registry.get("lifecycleStatus") != "promoted":
        return "model_registry_inactive"
    if not all(registry.get(key) for key in (
        "approvalId", "approvedBy", "approvedAt", "approvalRationale", "evaluationReportSha256",
        "artifactManifestSha256",
    )):
        return "approval_missing"
    expected = {
        "packageSha256": bundle.package_sha256, "featureSchemaVersion": FEATURE_SCHEMA_VERSION,
        "featureSchemaSha256": bundle.feature_schema_sha256,
        "weakTopicRankingPolicySha256": bundle.ranking_policy_sha256,
        "adaptivePolicySha256": bundle.adaptive_policy_sha256,
    }
    if any(registry.get(key) != value for key, value in expected.items()):
        return "bundle_mismatch"
    if registry.get("modelType") != "xgboost" or registry.get("evaluationStatus") != "evaluated" or registry.get("promotionGateStatus") != "passed":
        return "model_registry_inactive"
    if registry.get("predictionTarget") != "next_attempt_support_needed" or registry.get("labelVersion") != "next-attempt-support-needed-v1":
        return "model_target_incompatible"
    if not registry.get("artifactSha256") or not registry.get("artifactPath"):
        return "artifact_unavailable"
    return None


@contextmanager
def _approved_artifact_path(bundle: RuntimeBundle, registry: Mapping[str, Any]):
    """Download approved GCS bytes to a short-lived verified local path.

    The registry may use ``gs://bucket/object`` only; relative paths remain an
    emulator-only bundle fixture.  Both model and manifest bytes are checked
    before the caller can pass the model to joblib.
    """
    artifact_path = str(registry["artifactPath"])
    with TemporaryDirectory(prefix="logic-oasis-model-") as temporary:
        root = Path(temporary)
        candidate, manifest = root / "model.joblib", root / "model.manifest.json"
        if artifact_path.startswith("gs://"):
            try:
                from firebase_admin import storage
                bucket_name, object_name = artifact_path[5:].split("/", 1)
                bucket = storage.bucket(bucket_name)
                candidate.write_bytes(bucket.blob(object_name).download_as_bytes())
                manifest.write_bytes(bucket.blob(object_name + ".manifest.json").download_as_bytes())
            except Exception as error:
                raise RuntimeFailure("artifact_unavailable", fallback_available=True) from error
        else:
            source = (bundle.artifact_root / artifact_path).resolve()
            if bundle.artifact_root not in source.parents or not source.is_file():
                raise RuntimeFailure("artifact_unavailable", fallback_available=True)
            candidate.write_bytes(source.read_bytes())
            source_manifest = source.with_suffix(source.suffix + ".manifest.json")
            if not source_manifest.is_file():
                raise RuntimeFailure("artifact_hash_mismatch", fallback_available=True)
            manifest.write_bytes(source_manifest.read_bytes())
        if _file_sha256_or_none(candidate) != registry.get("artifactSha256") or _file_sha256_or_none(manifest) != registry.get("artifactManifestSha256"):
            raise RuntimeFailure("artifact_hash_mismatch", fallback_available=True)
        try:
            declared = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise RuntimeFailure("artifact_hash_mismatch", fallback_available=True) from error
        bindings = {"artifactSha256": registry["artifactSha256"], "modelVersion": registry["modelVersion"],
                    "featureSchemaVersion": FEATURE_SCHEMA_VERSION, "featureSchemaSha256": bundle.feature_schema_sha256,
                    "packageSha256": bundle.package_sha256, "weakTopicRankingPolicySha256": bundle.ranking_policy_sha256,
                    "adaptivePolicySha256": bundle.adaptive_policy_sha256, "predictionTarget": registry["predictionTarget"],
                    "labelVersion": registry["labelVersion"]}
        if any(declared.get(key) != value for key, value in bindings.items()):
            raise RuntimeFailure("artifact_hash_mismatch", fallback_available=True)
        yield candidate


def _assignment(attempt: Mapping[str, Any], mastery: float, evidence: int, support_risk: float | None,
                banks: list[Mapping[str, Any]], bundle: RuntimeBundle) -> Mapping[str, Any] | None:
    try:
        policy = load_adaptive_policy_config(bundle.adaptive_policy_path)
        eligible = [EligibleBank(bank_id=str(bank["bankId"]), difficulty=Difficulty(str(bank["difficultyLevel"])),
                                 exposure_count=int(bank.get("exposureCount", 0)), is_active=bank.get("isActive") is True)
                    for bank in banks]
        decision = select_next_bank(AssignmentContext(student_id=str(attempt["studentId"]), subtopic_id=str(attempt["subtopicId"]),
            current_difficulty=Difficulty(str(attempt["difficultyLevel"])), mastery_probability=mastery,
            evidence_count=evidence, support_risk=support_risk), eligible, policy=policy)
    except Exception as error:
        raise RuntimeFailure("policy_unavailable", fallback_available=True) from error
    if not decision.is_assignable:
        return None
    return {**decision.to_firestore_document(), "studentId": attempt["studentId"], "subtopicId": attempt["subtopicId"],
            "sourceAttemptId": attempt["attemptId"], "sourceAttemptSequence": attempt["sourceAttemptSequence"]}


def _subtopic_mastery(attempt: Mapping[str, Any], snapshot: Any, risk: float | None, bundle: RuntimeBundle) -> dict[str, Any]:
    ranking_version, minimum_evidence = _ranking_policy(bundle)
    reliability = min(snapshot.evidence_count / minimum_evidence, 1.0)
    return {"studentId": attempt["studentId"], "yearLevel": attempt["yearLevel"], "topicId": attempt["topicId"],
            "subtopicId": attempt["subtopicId"], "masteryProbability": snapshot.mastery_probability,
            "observationCount": snapshot.evidence_count, "evidenceLevel": "preliminary" if reliability < 1 else "established",
            "weakTopicPriorityScore": round((1.0 - snapshot.mastery_probability) * reliability, 8),
            "rankingVersion": ranking_version, "rankingPolicySha256": bundle.ranking_policy_sha256,
            "supportRisk": risk, "lastSourceAttemptId": attempt["attemptId"],
            "sourceAttemptSequence": attempt["sourceAttemptSequence"]}


def _ranking_policy(bundle: RuntimeBundle) -> tuple[str, int]:
    path = bundle.adaptive_policy_path.parent / "weak_topic_ranking_v1.yaml"
    try:
        data = yaml.safe_load(path.read_bytes())
        version = data["policyVersion"]
        minimum = data["minimumEvidenceForHighConfidence"]
        if data.get("formula") != "severity_times_evidence_reliability":
            raise ValueError("unsupported formula")
        if not isinstance(version, str) or not version or isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
            raise ValueError("invalid policy")
        return version, minimum
    except (OSError, ValueError, TypeError, yaml.YAMLError, KeyError) as error:
        raise RuntimeFailure("policy_unavailable", fallback_available=True) from error


def _fallback_run(attempt: Mapping[str, Any], code: str) -> dict[str, Any]:
    return {"attemptId": attempt.get("attemptId"), "studentId": attempt.get("studentId"), "status": "fallback",
            "statusCode": code if code in SAFE_ERROR_CODES else "fallback_unavailable",
            "sourceAttemptSequence": attempt.get("sourceAttemptSequence"), "dataSource": "runtime_callable",
            "featureSchemaVersion": FEATURE_SCHEMA_VERSION, "modelVersion": "bkt-v1"}


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _file_sha256_or_none(path: Path) -> str | None:
    try:
        return _file_sha256(path)
    except OSError:
        return None


def _tree_sha256(path: Path) -> str:
    digest = sha256()
    for file in sorted(item for item in path.rglob("*") if item.is_file() and "__pycache__" not in item.parts):
        digest.update(file.relative_to(path).as_posix().encode("utf-8"))
        digest.update(file.read_bytes())
    return digest.hexdigest()


class FirestoreRuntimeGateway:
    """Production gateway.  Claim and terminal reconciliation are transactions."""

    def __init__(self, database: Any) -> None:
        self.db = database

    def attempt(self, attempt_id: str) -> Mapping[str, Any] | None:
        snapshot = self.db.collection("quizAttempts").document(attempt_id).get()
        return _snapshot_dict(snapshot, attempt_id=attempt_id)

    def claim(self, attempt: Mapping[str, Any]) -> RuntimeClaim:
        from firebase_admin import firestore

        job_ref = self.db.collection("aiJobs").document(str(attempt["attemptId"]))
        status_ref = self.db.collection("studentAiStatuses").document(str(attempt["attemptId"]))

        @firestore.transactional
        def claim_tx(transaction: Any) -> RuntimeClaim:
            snapshot = job_ref.get(transaction=transaction)
            existing = dict(snapshot.to_dict() or {}) if snapshot.exists else {}
            state = existing.get("status")
            if state in TERMINAL_STATES:
                return RuntimeClaim(int(existing.get("attemptCount", 0)), state)
            count = int(existing.get("attemptCount", 0)) + 1
            now = datetime.now(timezone.utc)
            transaction.set(job_ref, {"attemptId": attempt["attemptId"], "studentId": attempt["studentId"],
                "status": "processing", "attemptCount": count, "pipelineVersion": AI_RUNTIME_VERSION,
                "sourceAttemptSequence": attempt["sourceAttemptSequence"], "updatedAt": now,
                "createdAt": existing.get("createdAt", now)}, merge=True)
            if not existing:
                status = safe_status_document(attempt=attempt, analysis_state="processing", display_code="analysis_in_progress")
                status["updatedAt"] = now
                transaction.create(status_ref, status)
            return RuntimeClaim(count)

        return claim_tx(self.db.transaction())

    def history(self, attempt: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
        attempts = []
        for snapshot in self.db.collection("quizAttempts").where("studentId", "==", attempt["studentId"]).where(
            "subtopicId", "==", attempt["subtopicId"]).stream():
            record = _snapshot_dict(snapshot)
            if (record and record.get("validationStatus") == "finalized" and record.get("finalizationStatus") == "finalized"
                and record.get("dataSource") == "runtime_callable" and isinstance(record.get("sourceAttemptSequence"), int)
                and not isinstance(record.get("sourceAttemptSequence"), bool) and record["sourceAttemptSequence"] > 0
                and record["sourceAttemptSequence"] <= attempt["sourceAttemptSequence"]):
                record.setdefault("attemptId", snapshot.id)
                record.setdefault("documentId", snapshot.id)
                attempts.append(record)
        response_refs = []
        for item in attempts:
            response_refs.extend(self.db.collection("questionResponses").document(value) for value in item.get("responseIds", []))
        responses = []
        for snapshot in self.db.get_all(response_refs):
            record = _snapshot_dict(snapshot)
            if record:
                record.setdefault("responseId", snapshot.id)
                record.setdefault("documentId", snapshot.id)
                responses.append(record)
        return attempts, responses

    def banks(self, attempt: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return [_snapshot_dict(snapshot) or {} for snapshot in self.db.collection("questionBanks").where(
            "topicId", "==", attempt["topicId"]).where("subtopicId", "==", attempt["subtopicId"]).where(
            "yearLevel", "==", attempt["yearLevel"]).stream()]

    def active_registry(self) -> Mapping[str, Any] | None:
        rows = list(self.db.collection("modelRegistry").where("isActive", "==", True).limit(2).stream())
        if len(rows) != 1:
            return None
        return _snapshot_dict(rows[0])

    def record_retry(self, attempt: Mapping[str, Any], code: str) -> None:
        from firebase_admin import firestore
        job_ref = self.db.collection("aiJobs").document(str(attempt["attemptId"]))
        @firestore.transactional
        def retry_tx(transaction: Any) -> None:
            transaction.set(job_ref, {"status": "processing", "retryState": "retry_pending", "errorCode": code,
                "lastRetryAt": datetime.now(timezone.utc)}, merge=True)
        retry_tx(self.db.transaction())

    def finalize(self, attempt: Mapping[str, Any], *, state: str, code: str, raw_run: Mapping[str, Any],
                 snapshots: list[Mapping[str, Any]], assignment: Mapping[str, Any] | None,
                 mastery: Mapping[str, Any] | None) -> str:
        from firebase_admin import firestore

        if state not in TERMINAL_STATES:
            raise ValueError("U8 terminal state is invalid")
        attempt_id, sequence = str(attempt["attemptId"]), int(attempt["sourceAttemptSequence"])
        job_ref = self.db.collection("aiJobs").document(attempt_id)
        status_ref = self.db.collection("studentAiStatuses").document(attempt_id)
        run_ref = self.db.collection("aiModelRuns").document(attempt_id)

        @firestore.transactional
        def final_tx(transaction: Any) -> str:
            job_snapshot = job_ref.get(transaction=transaction)
            job = dict(job_snapshot.to_dict() or {}) if job_snapshot.exists else {}
            if job.get("status") in TERMINAL_STATES:
                return str(job["status"])
            now = datetime.now(timezone.utc)
            projection_writes: list[tuple[Any, Mapping[str, Any]]] = []
            for snapshot in snapshots:
                ref = self.db.collection("masterySnapshots").document(mastery_snapshot_id(
                    str(snapshot["studentId"]), str(snapshot["subtopicId"]), str(snapshot["skillId"])))
                existing = ref.get(transaction=transaction)
                if is_newer_projection(sequence, _snapshot_dict(existing)):
                    projection_writes.append((ref, {**snapshot, "updatedAt": now}))
            if mastery is not None:
                ref = self.db.collection("subtopicMastery").document(subtopic_mastery_id(
                    str(attempt["studentId"]), int(attempt["yearLevel"]), str(attempt["topicId"]), str(attempt["subtopicId"])))
                existing = ref.get(transaction=transaction)
                if is_newer_projection(sequence, _snapshot_dict(existing)):
                    projection_writes.append((ref, {**mastery, "updatedAt": now}))
            if assignment is not None:
                ref = self.db.collection("adaptiveAssignments").document(adaptive_assignment_id(
                    str(attempt["studentId"]), str(attempt["subtopicId"])))
                existing = ref.get(transaction=transaction)
                if is_newer_projection(sequence, _snapshot_dict(existing)):
                    projection_writes.append((ref, {**assignment, "updatedAt": now}))
            # Firestore transactions require every read to occur before the first write.
            transaction.set(run_ref, {**raw_run, "createdAt": now}, merge=True)
            for ref, document in projection_writes:
                transaction.set(ref, document, merge=True)
            display = {"completed": "analysis_completed", "fallback": "analysis_fallback", "failed": "analysis_failed"}[state]
            status = safe_status_document(attempt=attempt, analysis_state=state, display_code=display)
            status["updatedAt"] = now
            transaction.set(status_ref, status, merge=True)
            transaction.set(job_ref, {"status": state, "errorCode": code if state != "completed" else None,
                "completedAt": now, "updatedAt": now}, merge=True)
            return state

        return final_tx(self.db.transaction())


def _snapshot_dict(snapshot: Any, *, attempt_id: str | None = None) -> dict[str, Any] | None:
    if snapshot is None or not getattr(snapshot, "exists", False):
        return None
    data = dict(snapshot.to_dict() or {})
    if attempt_id:
        data.setdefault("attemptId", attempt_id)
    else:
        document_id = getattr(snapshot, "id", None)
        if document_id and "attemptId" not in data and str(getattr(snapshot, "reference", "")).find("quizAttempts") >= 0:
            data["attemptId"] = document_id
        data.setdefault("documentId", document_id)
    return data
