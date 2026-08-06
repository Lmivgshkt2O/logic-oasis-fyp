"""U8 automatic, idempotent server-side runtime for trusted quiz attempts.

This module has no Flutter-facing surface.  It accepts only U3-R finalized
attempts, computes BKT first, and treats the supervised/XGBoost route as an
optional, registry-bound enhancement.  Safe projections never contain model
paths, hashes, feature vectors, raw SHAP values, or exception text.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from threading import RLock
from typing import Any, Mapping, Protocol

import yaml

from logic_oasis_ai.adaptive_policy import (
    AssignmentContext, Difficulty, EligibleBank, load_adaptive_policy_config, select_next_bank,
)
from logic_oasis_ai.bkt import build_bkt_materialization
from logic_oasis_ai.explain import explain_prediction
from logic_oasis_ai.features import BASE_FEATURE_NAMES, FEATURE_SCHEMA_VERSION, build_attempt_features
from logic_oasis_ai.inference import InferenceContractError, predict_support_risk
from logic_oasis_ai.model_registry import (
    CONTROLLED_DEMO_RELEASE_SCOPE,
    CONTROLLED_DEMO_DEPLOYMENT_SCOPE,
    CONTROLLED_DEMO_EVIDENCE_LEVEL,
    CONTROLLED_DEMO_PROVENANCE,
    CONTROLLED_DEMO_RELEASE_RATIONALE_MARKER,
    REAL_EVALUATED_DEPLOYMENT_SCOPE,
    SHA256_PATTERN,
    controlled_demo_object_paths,
)
from logic_oasis_ai.native_xgboost import (
    NativeXGBoostContractError,
    predict_and_explain_native_xgboost,
)
from logic_oasis_ai.policy_evaluation import (
    PolicyArm,
    PolicyDecisionContext,
    deterministic_policy_decision_id,
    load_policy_evaluation_manifest,
    select_policy_decision,
)
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
    "model_registry_missing", "model_registry_inactive", "release_missing",
    "bundle_mismatch", "artifact_hash_mismatch", "model_load_failed",
    "shap_load_failed", "feature_schema_incompatible", "model_target_incompatible",
    "policy_unavailable", "artifact_unavailable", "artifact_hash_invalid", "model_prediction_invalid", "shap_output_invalid",
    "model_evidence_incompatible",
})
SAFE_ERROR_CODES = FALLBACK_CODES | frozenset({"trusted_source_invalid", "runtime_exhausted"})
CONTROLLED_DEMO_MODE = "controlled_demo"
REAL_EVALUATED_ONLY_MODE = "real_evaluated_only"
ALLOWED_EVIDENCE_MODES = frozenset({CONTROLLED_DEMO_MODE, REAL_EVALUATED_ONLY_MODE})
CONTROLLED_DEMO_NATIVE_CACHE_SIZE = 2
POLICY_ASSIGNMENT_DELIVERY_VERSION = "assignment-delivery-v1"
POLICY_PROBE_PROTOCOL_VERSION = "policy-outcomes-v1"

NEUTRAL_REASON_CODES = {
    "p1_score_promote": "advance_ready",
    "p2_agreement_promote": "advance_ready",
    "p3_move_up_mastery": "advance_ready",
    "p3_move_up_bkt_fallback": "advance_ready",
    "p3_cold_start_easy": "build_evidence",
    "p2_agreement_demote": "practice_support",
    "p3_move_down_support": "practice_support",
    "p3_stay_easy_support": "practice_support",
    "p1_score_hold": "build_evidence",
    "p2_disagreement_hold": "build_evidence",
    "p2_neutral_hold": "build_evidence",
    "p3_stay_hard_mastery": "build_evidence",
    "p3_stay_build_evidence": "build_evidence",
    "p3_stay_target_zone": "build_evidence",
    "anti_oscillation_hold": "build_evidence",
    "hard_requires_more_evidence": "build_evidence",
    "difficulty_upper_bound_hold": "build_evidence",
    "difficulty_lower_bound_hold": "build_evidence",
    "no_eligible_bank": "no_eligible_bank",
}
ENROLLED_ARMS = frozenset({"P1", "P2", "P3a", "P3b"})


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
    policy_evaluation_sha256: str
    adaptive_policy_path: Path
    policy_evaluation_path: Path
    artifact_root: Path
    evidence_mode: str
    model_bucket: str

    @classmethod
    def from_runtime_root(
        cls,
        root: str | Path,
        *,
        evidence_mode: str = REAL_EVALUATED_ONLY_MODE,
        model_bucket: str = "",
    ) -> "RuntimeBundle":
        root_path = Path(root).resolve()
        package = root_path / "logic_oasis_ai"
        feature_schema = root_path / "configs" / "feature_schema.yaml"
        adaptive = root_path / "configs" / "adaptive_policy_v1.yaml"
        ranking = root_path / "configs" / "weak_topic_ranking_v1.yaml"
        policy_evaluation = root_path / "configs" / "policy_evaluation_v1.yaml"
        if not all(
            path.exists()
            for path in (package, feature_schema, adaptive, ranking, policy_evaluation)
        ):
            raise RuntimeFailure("bundle_mismatch", fallback_available=True)
        return cls(
            package_sha256=_tree_sha256(package),
            feature_schema_sha256=_file_sha256(feature_schema),
            adaptive_policy_sha256=_file_sha256(adaptive),
            ranking_policy_sha256=_file_sha256(ranking),
            policy_evaluation_sha256=_file_sha256(policy_evaluation),
            adaptive_policy_path=adaptive,
            policy_evaluation_path=policy_evaluation,
            artifact_root=(root_path / "models").resolve(),
            evidence_mode=evidence_mode,
            model_bucket=model_bucket.removeprefix("gs://").rstrip("/"),
        )


class _ControlledDemoNativeRuntime:
    """One immutable native model/explainer pair safe for warm-instance reuse."""

    def __init__(self, model: Any, explainer: Any) -> None:
        self.model = model
        self.explainer = explainer
        self.lock = RLock()


_CONTROLLED_DEMO_NATIVE_CACHE: OrderedDict[
    tuple[str, str], _ControlledDemoNativeRuntime
] = OrderedDict()
_CONTROLLED_DEMO_NATIVE_CACHE_LOCK = RLock()


class RuntimeGateway(Protocol):
    def claim(self, attempt: Mapping[str, Any]) -> RuntimeClaim: ...
    def attempt(self, attempt_id: str) -> Mapping[str, Any] | None: ...
    def history(self, attempt: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]: ...
    def banks(self, attempt: Mapping[str, Any]) -> list[Mapping[str, Any]]: ...
    def enrollment(self, attempt: Mapping[str, Any]) -> Mapping[str, Any] | None: ...
    def previous_assignment(self, attempt: Mapping[str, Any]) -> Mapping[str, Any] | None: ...
    def active_registry(self) -> Mapping[str, Any] | None: ...
    def record_retry(self, attempt: Mapping[str, Any], code: str) -> None: ...
    def finalize(self, attempt: Mapping[str, Any], *, state: str, code: str, raw_run: Mapping[str, Any],
                 snapshots: list[Mapping[str, Any]], assignment: Mapping[str, Any] | None,
                 mastery: Mapping[str, Any] | None,
                 policy_audit: Mapping[str, Any] | None = None,
                 policy_probe: Mapping[str, Any] | None = None) -> str: ...


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
        model_evidence_state = model_run.get("modelEvidenceState")
        banks = gateway.banks(attempt)
        enrollment = gateway.enrollment(attempt)
        policy_audit = None
        policy_probe = None
        if enrollment is not None:
            assignment, policy_audit, policy_probe = _policy_assignment(
                attempt,
                enrollment,
                primary.mastery_probability,
                primary.evidence_count,
                support_risk,
                banks,
                gateway.previous_assignment(attempt),
                bundle,
                model_evidence_state=(
                    model_evidence_state
                    if model_evidence_state == CONTROLLED_DEMO_EVIDENCE_LEVEL
                    else None
                ),
            )
        else:
            assignment = _assignment(
                attempt,
                primary.mastery_probability,
                primary.evidence_count,
                support_risk,
                banks,
                bundle,
                model_evidence_state=(
                    model_evidence_state
                    if model_evidence_state == CONTROLLED_DEMO_EVIDENCE_LEVEL
                    else None
                ),
            )
        mastery = _subtopic_mastery(attempt, primary, support_risk, bundle)
        return gateway.finalize(attempt, state=state, code=model_run["statusCode"], raw_run=model_run,
                                snapshots=snapshots, assignment=assignment, mastery=mastery,
                                policy_audit=policy_audit, policy_probe=policy_probe)
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
    row_feature_values = row.to_model_features()
    try:
        with _released_artifact_path(bundle, registry) as artifact_path:
            if registry.get("deploymentScope") == CONTROLLED_DEMO_DEPLOYMENT_SCOPE:
                support_risk, shap_values, shap_expected_value = _controlled_demo_prediction_and_explanation(
                    artifact_path,
                    feature_values=row_feature_values,
                    artifact_sha256=str(registry["artifactSha256"]),
                    manifest_sha256=str(registry["artifactManifestSha256"]),
                )
                feature_values = {
                    name: float(row_feature_values[name])
                    for name in BASE_FEATURE_NAMES
                }
            else:
                prediction = predict_support_risk(artifact_path, expected_sha256=registry["artifactSha256"],
                                                   feature_names=BASE_FEATURE_NAMES, feature_values=row_feature_values)
                explanation = explain_prediction(str(artifact_path), expected_sha256=registry["artifactSha256"],
                                                 feature_names=BASE_FEATURE_NAMES, feature_values=prediction.feature_values)
                support_risk = prediction.support_risk
                shap_values = dict(explanation.values)
                shap_expected_value = explanation.expected_value
                feature_values = dict(prediction.feature_values)
    except (InferenceContractError, RuntimeFailure) as error:
        return None, _fallback_run(attempt, str(error))
    model_evidence_state = (
        CONTROLLED_DEMO_EVIDENCE_LEVEL
        if registry.get("deploymentScope") == CONTROLLED_DEMO_DEPLOYMENT_SCOPE
        else None
    )
    return support_risk, {
        "attemptId": attempt["attemptId"], "studentId": attempt["studentId"], "status": "completed",
        "statusCode": "model_completed", "modelVersion": registry["modelVersion"],
        "featureSchemaVersion": FEATURE_SCHEMA_VERSION, "predictionTarget": registry["predictionTarget"],
        "labelVersion": registry["labelVersion"], "supportRisk": support_risk,
        "featureValues": feature_values, "shapValues": shap_values,
        "shapExpectedValue": shap_expected_value, "sourceAttemptSequence": attempt["sourceAttemptSequence"],
        "releaseId": registry["releaseId"], "dataSource": "runtime_callable",
        **({"modelEvidenceState": model_evidence_state} if model_evidence_state else {}),
    }


def _controlled_demo_prediction_and_explanation(
    artifact_path: Path,
    *,
    feature_values: Mapping[str, float],
    artifact_sha256: str,
    manifest_sha256: str,
) -> tuple[float, Mapping[str, float], float]:
    """Load one verified native UBJ model and derive its prediction and Tree SHAP."""
    try:
        import numpy as np

        matrix = np.asarray([[float(feature_values[name]) for name in BASE_FEATURE_NAMES]])
    except Exception as error:
        raise InferenceContractError("model_load_failed") from error
    runtime = _controlled_demo_native_runtime(
        artifact_path,
        artifact_sha256=artifact_sha256,
        manifest_sha256=manifest_sha256,
    )
    try:
        # XGBoost/TreeExplainer do not declare concurrent-call safety. Serialize
        # use of one cached pair while allowing different immutable pairs to run.
        with runtime.lock:
            explanation = predict_and_explain_native_xgboost(
                runtime.model,
                matrix,
                feature_names=BASE_FEATURE_NAMES,
                explainer_factory=lambda _model: runtime.explainer,
            )
    except NativeXGBoostContractError as error:
        if error.code in {"model_target_incompatible", "model_prediction_invalid"}:
            raise InferenceContractError(error.code) from error
        if error.code == "shap_load_failed":
            raise InferenceContractError("shap_load_failed") from error
        raise InferenceContractError("shap_output_invalid") from error
    except Exception as error:
        raise InferenceContractError("shap_load_failed") from error
    return (
        round(explanation.support_risks[0], 8),
        {name: round(value, 8) for name, value in zip(BASE_FEATURE_NAMES, explanation.shap_values[0])},
        explanation.expected_values[0],
    )


def _controlled_demo_native_runtime(
    artifact_path: Path,
    *,
    artifact_sha256: str,
    manifest_sha256: str,
) -> _ControlledDemoNativeRuntime:
    """Reuse only a pair whose artifact and manifest were verified this call."""
    key = (artifact_sha256, manifest_sha256)
    with _CONTROLLED_DEMO_NATIVE_CACHE_LOCK:
        cached = _CONTROLLED_DEMO_NATIVE_CACHE.get(key)
        if cached is not None:
            _CONTROLLED_DEMO_NATIVE_CACHE.move_to_end(key)
            return cached
        loaded = _load_controlled_demo_native_runtime(artifact_path)
        _CONTROLLED_DEMO_NATIVE_CACHE[key] = loaded
        _CONTROLLED_DEMO_NATIVE_CACHE.move_to_end(key)
        while len(_CONTROLLED_DEMO_NATIVE_CACHE) > CONTROLLED_DEMO_NATIVE_CACHE_SIZE:
            _CONTROLLED_DEMO_NATIVE_CACHE.popitem(last=False)
        return loaded


def _load_controlled_demo_native_runtime(
    artifact_path: Path,
) -> _ControlledDemoNativeRuntime:
    try:
        from xgboost import XGBClassifier

        model = XGBClassifier()
        model.load_model(str(artifact_path))
    except Exception as error:
        raise InferenceContractError("model_load_failed") from error
    try:
        import shap

        explainer = shap.TreeExplainer(model)
    except Exception as error:
        raise InferenceContractError("shap_load_failed") from error
    return _ControlledDemoNativeRuntime(model, explainer)


def _clear_controlled_demo_native_cache() -> None:
    """Reset warm-instance state for deterministic isolated tests."""
    with _CONTROLLED_DEMO_NATIVE_CACHE_LOCK:
        _CONTROLLED_DEMO_NATIVE_CACHE.clear()


def _registry_mismatch(registry: Mapping[str, Any], bundle: RuntimeBundle) -> str | None:
    if registry.get("isActive") is not True or registry.get("lifecycleStatus") != "promoted":
        return "model_registry_inactive"
    if not all(registry.get(key) for key in (
        "releaseId", "releasedBy", "releasedAt", "releaseRationale", "evaluationReportSha256",
        "artifactManifestSha256", "promotedAt",
    )):
        return "release_missing"
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
    return _evidence_mismatch(registry, bundle)


def _evidence_mismatch(registry: Mapping[str, Any], bundle: RuntimeBundle) -> str | None:
    if bundle.evidence_mode not in ALLOWED_EVIDENCE_MODES:
        return "model_evidence_incompatible"
    if bundle.evidence_mode == CONTROLLED_DEMO_MODE:
        return _controlled_demo_evidence_mismatch(registry, bundle)
    return _real_evidence_mismatch(registry, bundle)


def _controlled_demo_evidence_mismatch(
    registry: Mapping[str, Any], bundle: RuntimeBundle
) -> str | None:
    expected = {
        "trainingDataProvenance": CONTROLLED_DEMO_PROVENANCE,
        "evidenceLevel": CONTROLLED_DEMO_EVIDENCE_LEVEL,
        "releaseScope": CONTROLLED_DEMO_RELEASE_SCOPE,
        "deploymentScope": CONTROLLED_DEMO_DEPLOYMENT_SCOPE,
    }
    if any(registry.get(field) != value for field, value in expected.items()):
        return "model_evidence_incompatible"
    if any(
        not isinstance(registry.get(field), str)
        or not SHA256_PATTERN.fullmatch(str(registry[field]))
        for field in (
            "trainingDatasetSha256", "scenarioCatalogueSha256", "controlledDemoConfigSha256",
        )
    ):
        return "model_evidence_incompatible"
    if not isinstance(registry.get("trainingDatasetVersion"), str) or not registry["trainingDatasetVersion"]:
        return "model_evidence_incompatible"
    rationale = registry.get("releaseRationale")
    if not isinstance(rationale, str) or CONTROLLED_DEMO_RELEASE_RATIONALE_MARKER not in rationale.lower():
        return "model_evidence_incompatible"
    try:
        paths = controlled_demo_object_paths(
            f"gs://{bundle.model_bucket}", registry.get("modelVersion")
        )
    except ValueError:
        return "artifact_unavailable"
    if (registry.get("artifactPath"), registry.get("artifactManifestPath")) != paths:
        return "artifact_unavailable"
    return None


def _real_evidence_mismatch(registry: Mapping[str, Any], bundle: RuntimeBundle) -> str | None:
    if registry.get("deploymentScope") == CONTROLLED_DEMO_DEPLOYMENT_SCOPE:
        return "model_evidence_incompatible"
    expected_real = {
        "trainingDataProvenance": "approved_pseudonymized_real",
        "evidenceLevel": "real_evaluated",
        "releaseScope": "real_evaluated",
        "deploymentScope": REAL_EVALUATED_DEPLOYMENT_SCOPE,
    }
    evidence_values = tuple(registry.get(field) for field in expected_real)
    if any(value is not None for value in evidence_values) and any(
        registry.get(field) != value for field, value in expected_real.items()
    ):
        return "model_evidence_incompatible"
    artifact_path = str(registry.get("artifactPath", ""))
    if not bundle.model_bucket or not artifact_path.startswith(f"gs://{bundle.model_bucket}/"):
        return "artifact_unavailable"
    return None


@contextmanager
def _released_artifact_path(bundle: RuntimeBundle, registry: Mapping[str, Any]):
    """Download approved GCS bytes to a short-lived verified local path.

    The registry may use ``gs://bucket/object`` only; relative paths remain an
    emulator-only bundle fixture.  Both model and manifest bytes are checked
    before native UBJ loading or the legacy real-evaluated joblib path.
    """
    artifact_path = str(registry["artifactPath"])
    with TemporaryDirectory(prefix="logic-oasis-model-") as temporary:
        root = Path(temporary)
        artifact_name = "model.ubj" if registry.get("deploymentScope") == CONTROLLED_DEMO_DEPLOYMENT_SCOPE else "model.joblib"
        candidate, manifest = root / artifact_name, root / "model.manifest.json"
        if artifact_path.startswith("gs://"):
            try:
                from firebase_admin import storage
                bucket_name, object_name = artifact_path[5:].split("/", 1)
                manifest_path = registry.get("artifactManifestPath")
                if manifest_path:
                    manifest_prefix = f"gs://{bucket_name}/"
                    if not isinstance(manifest_path, str) or not manifest_path.startswith(manifest_prefix):
                        raise ValueError("manifest must use the approved artifact bucket")
                    manifest_object = manifest_path.removeprefix(manifest_prefix)
                    if not manifest_object:
                        raise ValueError("manifest object path is missing")
                else:
                    manifest_object = object_name + ".manifest.json"
                bucket = storage.bucket(bucket_name)
                candidate.write_bytes(bucket.blob(object_name).download_as_bytes())
                manifest.write_bytes(bucket.blob(manifest_object).download_as_bytes())
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
        if not isinstance(declared, Mapping):
            raise RuntimeFailure("artifact_hash_mismatch", fallback_available=True)
        if registry.get("deploymentScope") == CONTROLLED_DEMO_DEPLOYMENT_SCOPE:
            bindings = {
                "bundleSchemaVersion": "controlled-demo-xgboost-bundle-v1",
                "modelType": "xgboost",
                "modelVersion": registry["modelVersion"],
                "artifactFile": "model.ubj",
                "artifactSha256": registry["artifactSha256"],
                "targetName": registry["predictionTarget"],
                "labelVersion": registry["labelVersion"],
                "featureSchemaVersion": FEATURE_SCHEMA_VERSION,
                "featureNames": list(BASE_FEATURE_NAMES),
                "trainingDatasetVersion": registry["trainingDatasetVersion"],
                "trainingDatasetSha256": registry["trainingDatasetSha256"],
                "trainingDataProvenance": CONTROLLED_DEMO_PROVENANCE,
                "scenarioCatalogueSha256": registry["scenarioCatalogueSha256"],
                "featureSchemaSha256": bundle.feature_schema_sha256,
                "controlledDemoConfigSha256": registry["controlledDemoConfigSha256"],
                "evaluationReportSha256": registry["evaluationReportSha256"],
                "evaluationStatus": "evaluated",
                "evidenceLevel": CONTROLLED_DEMO_EVIDENCE_LEVEL,
                "claimLevel": "controlled_demonstration_only",
                "deploymentScope": CONTROLLED_DEMO_DEPLOYMENT_SCOPE,
                "packageSha256": bundle.package_sha256,
                "weakTopicRankingPolicySha256": bundle.ranking_policy_sha256,
                "adaptivePolicySha256": bundle.adaptive_policy_sha256,
                "predictionTarget": registry["predictionTarget"],
            }
        else:
            bindings = {"artifactSha256": registry["artifactSha256"], "modelVersion": registry["modelVersion"],
                        "featureSchemaVersion": FEATURE_SCHEMA_VERSION, "featureSchemaSha256": bundle.feature_schema_sha256,
                        "packageSha256": bundle.package_sha256, "weakTopicRankingPolicySha256": bundle.ranking_policy_sha256,
                        "adaptivePolicySha256": bundle.adaptive_policy_sha256, "predictionTarget": registry["predictionTarget"],
                        "labelVersion": registry["labelVersion"]}
        if any(declared.get(key) != value for key, value in bindings.items()):
            raise RuntimeFailure("artifact_hash_mismatch", fallback_available=True)
        yield candidate


def _assignment(attempt: Mapping[str, Any], mastery: float, evidence: int, support_risk: float | None,
                banks: list[Mapping[str, Any]], bundle: RuntimeBundle, *,
                model_evidence_state: str | None = None) -> Mapping[str, Any] | None:
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
            "sourceAttemptId": attempt["attemptId"], "sourceAttemptSequence": attempt["sourceAttemptSequence"],
            # `startQuizSession` consumes only assignments whose lineage can
            # be traced to this trusted callable-finalized attempt. Seed/demo
            # rows and manually shaped records are never a normal runtime path.
            "dataSource": "runtime_callable",
            **({"modelEvidenceState": model_evidence_state} if model_evidence_state else {})}


def neutral_reason_code(reason_code: str) -> str:
    """Map a selector reason to the arm-neutral public delivery vocabulary."""
    try:
        return NEUTRAL_REASON_CODES[reason_code]
    except KeyError as error:
        raise RuntimeFailure("policy_unavailable", fallback_available=True) from error


def _policy_assignment(
    attempt: Mapping[str, Any],
    enrollment: Mapping[str, Any],
    mastery: float,
    evidence: int,
    support_risk: float | None,
    banks: list[Mapping[str, Any]],
    previous_assignment: Mapping[str, Any] | None,
    bundle: RuntimeBundle,
    *,
    model_evidence_state: str | None = None,
) -> tuple[Mapping[str, Any] | None, Mapping[str, Any], Mapping[str, Any] | None]:
    """Run the allocated arm's selector and build blinded outputs.

    A selector failure never reaches a client: the learner receives the
    declared existing safe P3 assignment and a protected failure audit.
    """
    now = datetime.now(timezone.utc)
    try:
        policy = load_adaptive_policy_config(bundle.adaptive_policy_path)
        manifest = load_policy_evaluation_manifest(
            bundle.policy_evaluation_path, adaptive_policy=policy
        )
        enrolled_arm = _enrolled_arm(enrollment)
        arm = enrolled_arm
        deviation = None
        if arm == "P3b" and support_risk is None:
            arm = "P3a"
            deviation = "p3b_incompatible_model"
        context = PolicyDecisionContext(
            source_attempt_id=str(attempt["attemptId"]),
            student_id=str(attempt["studentId"]),
            subtopic_id=str(attempt["subtopicId"]),
            current_difficulty=Difficulty(str(attempt["difficultyLevel"])),
            correct_count=int(attempt["correctCount"]),
            total_questions=int(attempt["totalQuestions"]),
            mastery_probability=mastery,
            evidence_count=evidence,
            support_risk=support_risk if arm == "P3b" else None,
            compatible_model_available=(arm == "P3b" and support_risk is not None),
            last_transition=_last_transition(previous_assignment),
        )
        eligible = [
            EligibleBank(
                bank_id=str(bank["bankId"]),
                difficulty=Difficulty(str(bank["difficultyLevel"])),
                exposure_count=int(bank.get("exposureCount", 0)),
                is_active=bank.get("isActive") is True,
            )
            for bank in banks
        ]
        decision = select_policy_decision(
            PolicyArm(arm),
            context,
            eligible,
            manifest=manifest,
            adaptive_policy=policy,
        )
        audit = _decision_audit_document(
            attempt, enrollment, decision, context, manifest, policy,
            enrolled_arm=enrolled_arm, deviation=deviation, now=now,
        )
        probe = _probe_document(attempt, enrollment, decision, context, now=now)
        if not decision.is_assignable:
            return None, audit, probe
        projection = {
            "bankId": decision.selected_bank_id,
            "difficultyLevel": decision.selected_difficulty.value,
            "policyVersion": POLICY_ASSIGNMENT_DELIVERY_VERSION,
            "reasonCode": neutral_reason_code(decision.reason_code),
            "status": decision.outcome_status,
            "studentId": str(attempt["studentId"]),
            "subtopicId": str(attempt["subtopicId"]),
            "sourceAttemptId": str(attempt["attemptId"]),
            "sourceAttemptSequence": int(attempt["sourceAttemptSequence"]),
            "dataSource": "runtime_callable",
        }
        return projection, audit, probe
    except Exception as error:
        assignment = _assignment(
            attempt,
            mastery,
            evidence,
            support_risk,
            banks,
            bundle,
            model_evidence_state=model_evidence_state,
        )
        return (
            assignment,
            _selector_failure_audit(
                attempt, enrollment, mastery=mastery, evidence=evidence, now=now
            ),
            None,
        )


def _enrolled_arm(enrollment: Mapping[str, Any]) -> str:
    arm = str(enrollment.get("assignedArm", ""))
    if arm not in ENROLLED_ARMS:
        raise RuntimeFailure("policy_unavailable", fallback_available=True)
    return arm


def _last_transition(previous_assignment: Mapping[str, Any] | None) -> str | None:
    if previous_assignment is None:
        return None
    reason = previous_assignment.get("reasonCode")
    if isinstance(reason, str) and reason.lower().startswith(("move_up", "move_down")):
        return reason
    return None


def _decision_audit_document(
    attempt: Mapping[str, Any],
    enrollment: Mapping[str, Any],
    decision: Any,
    context: PolicyDecisionContext,
    manifest: Any,
    policy: Any,
    *,
    enrolled_arm: str,
    deviation: str | None,
    now: datetime,
) -> Mapping[str, Any]:
    return {
        "decisionId": decision.decision_id,
        "studyVersion": str(enrollment.get("studyVersion", "")),
        "enrollmentId": str(enrollment.get("enrollmentId", "")),
        "attemptId": str(attempt["attemptId"]),
        "studentId": str(attempt["studentId"]),
        "sourceAttemptSequence": int(attempt["sourceAttemptSequence"]),
        "assignedArm": enrolled_arm,
        "deliveredArm": decision.arm.value,
        "protocolDeviation": deviation,
        "selectorVersion": decision.policy_version,
        "manifestVersion": manifest.manifest_version,
        "manifestSha256": manifest.source_sha256,
        "adaptivePolicySha256": policy.source_sha256,
        "evidenceMode": decision.evidence_mode.value,
        "reasonCode": decision.reason_code,
        "selectedBankId": decision.selected_bank_id,
        "selectedDifficulty": (
            decision.selected_difficulty.value if decision.selected_difficulty else None
        ),
        "usedBktFallback": decision.used_bkt_fallback,
        "redactedInputs": {
            "currentDifficulty": context.current_difficulty.value,
            "scoreRate": round(context.score_rate, 8),
            "evidenceCount": context.evidence_count,
            "lastTransition": context.last_transition,
        },
    }


def _probe_document(
    attempt: Mapping[str, Any],
    enrollment: Mapping[str, Any],
    decision: Any,
    context: PolicyDecisionContext,
    *,
    now: datetime,
) -> Mapping[str, Any]:
    target = (
        decision.selected_difficulty.value
        if decision.selected_difficulty is not None
        else context.current_difficulty.value
    )
    return {
        "decisionId": decision.decision_id,
        "studyVersion": str(enrollment.get("studyVersion", "")),
        "enrollmentId": str(enrollment.get("enrollmentId", "")),
        "targetDifficulty": target,
        "probeProtocolVersion": POLICY_PROBE_PROTOCOL_VERSION,
        "status": "scheduled",
        "probeFormStatus": "pending_form_catalogue",
    }


def _selector_failure_audit(
    attempt: Mapping[str, Any],
    enrollment: Mapping[str, Any],
    *,
    mastery: float,
    evidence: int,
    now: datetime,
) -> Mapping[str, Any]:
    digest = sha256(
        f"selector-failed:{attempt['attemptId']}:{enrollment.get('studyVersion', '')}".encode(
            "utf-8"
        )
    ).hexdigest()
    total = int(attempt["totalQuestions"])
    correct = int(attempt["correctCount"])
    return {
        "decisionId": f"policy-decision-{digest}",
        "studyVersion": str(enrollment.get("studyVersion", "")),
        "enrollmentId": str(enrollment.get("enrollmentId", "")),
        "attemptId": str(attempt["attemptId"]),
        "studentId": str(attempt["studentId"]),
        "sourceAttemptSequence": int(attempt["sourceAttemptSequence"]),
        "assignedArm": str(enrollment.get("assignedArm", "")),
        "deliveredArm": None,
        "protocolDeviation": "selector_failed",
        "selectorVersion": None,
        "manifestVersion": None,
        "manifestSha256": None,
        "adaptivePolicySha256": None,
        "evidenceMode": None,
        "reasonCode": "selector_failed",
        "selectedBankId": None,
        "selectedDifficulty": None,
        "usedBktFallback": True,
        "redactedInputs": {
            "currentDifficulty": str(attempt["difficultyLevel"]),
            "scoreRate": round(correct / total, 8) if total > 0 else 0.0,
            "evidenceCount": evidence,
            "masteryBand": _mastery_band(mastery),
        },
    }


def _mastery_band(mastery: float) -> str:
    if mastery < 0.4:
        return "low"
    if mastery < 0.7:
        return "medium"
    return "high"


def _subtopic_mastery(attempt: Mapping[str, Any], snapshot: Any, risk: float | None, bundle: RuntimeBundle) -> dict[str, Any]:
    ranking_version, minimum_evidence = _ranking_policy(bundle)
    reliability = min(snapshot.evidence_count / minimum_evidence, 1.0)
    correct_rate = _attempt_correct_rate(attempt)
    return {"studentId": attempt["studentId"], "yearLevel": attempt["yearLevel"], "topicId": attempt["topicId"],
            "subtopicId": attempt["subtopicId"], "masteryProbability": snapshot.mastery_probability,
            "observationCount": snapshot.evidence_count, "evidenceLevel": "preliminary" if reliability < 1 else "established",
            "weakTopicPriorityScore": round((1.0 - snapshot.mastery_probability) * reliability, 8),
            "rankingVersion": ranking_version, "lastSourceAttemptId": attempt["attemptId"],
            "sourceAttemptSequence": attempt["sourceAttemptSequence"],
            # These bounded progression fields are deliberately separate from
            # the BKT posterior. They let the student UI reflect only a
            # server-confirmed quiz completion without exposing raw responses
            # or AI/model evidence.
            "lastCorrectRate": correct_rate}


def _attempt_correct_rate(attempt: Mapping[str, Any]) -> float:
    total = attempt.get("totalQuestions")
    correct = attempt.get("correctCount")
    if isinstance(total, bool) or isinstance(correct, bool) or not isinstance(total, int) or not isinstance(correct, int) or total <= 0:
        raise RuntimeFailure("trusted_source_invalid")
    return max(0.0, min(correct, total) / total)


def _mastery_level_for_rate(rate: float) -> str:
    if rate >= 0.8:
        return "Strong"
    if rate > 0.5:
        return "Moderate"
    if rate > 0:
        return "Weak"
    return "New"


def _merged_subtopic_mastery(existing: Mapping[str, Any] | None, mastery: Mapping[str, Any]) -> dict[str, Any]:
    current_rate = mastery.get("lastCorrectRate")
    if not isinstance(current_rate, (int, float)) or isinstance(current_rate, bool):
        raise RuntimeFailure("trusted_source_invalid")
    previous_rate = (existing or {}).get("bestCorrectRate", 0.0)
    if not isinstance(previous_rate, (int, float)) or isinstance(previous_rate, bool):
        previous_rate = 0.0
    best_rate = max(float(previous_rate), float(current_rate))
    return {**mastery, "bestCorrectRate": best_rate, "completed": best_rate > 0.5,
            "masteryLevel": _mastery_level_for_rate(best_rate)}


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
        # Exposure belongs to this learner's trusted history, never to a shared
        # bank document. Including the just-finalized source attempt means the
        # next policy decision prefers another eligible bank at the same level.
        exposure_by_bank: dict[str, int] = {}
        for snapshot in self.db.collection("quizAttempts").where(
            "studentId", "==", attempt["studentId"]
        ).where("subtopicId", "==", attempt["subtopicId"]).stream():
            record = _snapshot_dict(snapshot) or {}
            sequence = record.get("sourceAttemptSequence")
            bank_id = record.get("bankId")
            if (
                record.get("validationStatus") == "finalized"
                and record.get("finalizationStatus") == "finalized"
                and record.get("dataSource") == "runtime_callable"
                and isinstance(sequence, int)
                and not isinstance(sequence, bool)
                and 0 < sequence <= attempt["sourceAttemptSequence"]
                and isinstance(bank_id, str)
                and bank_id
            ):
                exposure_by_bank[bank_id] = exposure_by_bank.get(bank_id, 0) + 1

        banks = []
        for snapshot in self.db.collection("questionBanks").where(
            "topicId", "==", attempt["topicId"]).where("subtopicId", "==", attempt["subtopicId"]).where(
            "yearLevel", "==", attempt["yearLevel"]).stream():
            bank = _snapshot_dict(snapshot) or {}
            bank_id = bank.get("bankId", snapshot.id)
            if isinstance(bank_id, str) and bank_id:
                bank["bankId"] = bank_id
                bank["exposureCount"] = exposure_by_bank.get(bank_id, 0)
            banks.append(bank)
        return banks

    def enrollment(self, attempt: Mapping[str, Any]) -> Mapping[str, Any] | None:
        rows = list(
            self.db.collection("policyEvaluationEnrollments")
            .where("studentId", "==", attempt["studentId"])
            .where("yearLevel", "==", attempt["yearLevel"])
            .where("topicId", "==", attempt["topicId"])
            .where("subtopicId", "==", attempt["subtopicId"])
            .where("status", "==", "active")
            .limit(2)
            .stream()
        )
        if len(rows) != 1:
            return None
        document = _snapshot_dict(rows[0])
        if document is None:
            return None
        document.setdefault("enrollmentId", rows[0].id)
        return document

    def previous_assignment(self, attempt: Mapping[str, Any]) -> Mapping[str, Any] | None:
        snapshot = self.db.collection("adaptiveAssignments").document(
            adaptive_assignment_id(
                str(attempt["studentId"]), str(attempt["subtopicId"])
            )
        ).get()
        return _snapshot_dict(snapshot)

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
                 mastery: Mapping[str, Any] | None,
                 policy_audit: Mapping[str, Any] | None = None,
                 policy_probe: Mapping[str, Any] | None = None) -> str:
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
                existing_data = _snapshot_dict(existing)
                is_pending_same_attempt = (
                    existing_data is not None and
                    existing_data.get("sourceAttemptSequence") == sequence and
                    existing_data.get("projectionStatus") == "finalized_pending_ai"
                )
                if is_newer_projection(sequence, existing_data) or is_pending_same_attempt:
                    projection_writes.append((ref, {
                        **_merged_subtopic_mastery(existing_data, mastery),
                        # U8 keeps policy hashes and model scores in server-only
                        # records. Remove legacy copies from this client-readable
                        # summary as the next finalized attempt updates it.
                        "rankingPolicySha256": firestore.DELETE_FIELD,
                        "supportRisk": firestore.DELETE_FIELD,
                        "projectionStatus": "ai_enriched",
                        "updatedAt": now,
                    }))
            if assignment is not None:
                ref = self.db.collection("adaptiveAssignments").document(adaptive_assignment_id(
                    str(attempt["studentId"]), str(attempt["subtopicId"])))
                existing = ref.get(transaction=transaction)
                if is_newer_projection(sequence, _snapshot_dict(existing)):
                    assignment_projection = {**assignment, "updatedAt": now}
                    if "modelEvidenceState" not in assignment_projection:
                        assignment_projection["modelEvidenceState"] = firestore.DELETE_FIELD
                    projection_writes.append((ref, assignment_projection))
            policy_audit_ref = None
            policy_probe_ref = None
            if policy_audit is not None:
                policy_audit_ref = self.db.collection("policyEvaluationDecisionAudits").document(
                    str(policy_audit["decisionId"])
                )
                if not policy_audit_ref.get(transaction=transaction).exists:
                    transaction.create(policy_audit_ref, {**policy_audit, "createdAt": now})
            if policy_probe is not None:
                policy_probe_ref = self.db.collection("policyEvaluationProbes").document(
                    str(policy_probe["decisionId"])
                )
                if not policy_probe_ref.get(transaction=transaction).exists:
                    transaction.create(policy_probe_ref, {**policy_probe, "createdAt": now})
            # Firestore transactions require every read to occur before the first write.
            transaction.set(run_ref, {**raw_run, "createdAt": now}, merge=True)
            for ref, document in projection_writes:
                transaction.set(ref, document, merge=True)
            display = {"completed": "analysis_completed", "fallback": "analysis_fallback", "failed": "analysis_failed"}[state]
            status = safe_status_document(attempt=attempt, analysis_state=state, display_code=display)
            if raw_run.get("modelEvidenceState") == CONTROLLED_DEMO_EVIDENCE_LEVEL:
                status["modelEvidenceState"] = CONTROLLED_DEMO_EVIDENCE_LEVEL
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
