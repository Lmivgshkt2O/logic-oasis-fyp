"""Immutable AQC-2 run manifest for one offline policy comparison.

The manifest freezes the dataset binding, policy/BKT/feature versions, outcome
window, censoring rules, random seed, and claim level before any decision is
produced.  It contains no timestamps or random values so identical inputs
produce identical manifests and report hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from logic_oasis_ai.adaptive_policy import ADAPTIVE_POLICY_VERSION
from logic_oasis_ai.bkt import BKT_MODEL_VERSION
from logic_oasis_ai.features import FEATURE_SCHEMA_VERSION
from logic_oasis_ai.policy_evaluation import POLICY_EVALUATION_MANIFEST_VERSION
from logic_oasis_ai.prediction_contract import (
    PREDICTION_LABEL_VERSION,
    PREDICTION_TARGET,
)
from logic_oasis_ai.sources.firestore_source import SOURCE_SCHEMA_VERSION, SourceDataset


RUN_MANIFEST_VERSION = "policy-evaluation-run-v1"
ALLOWED_CLAIM_LABELS = frozenset({"pipeline_demo_only", "descriptive_replay_only"})
ALLOWED_PROVENANCES = frozenset({"real", "emulator_verified", "synthetic_test"})

REQUIRED_CENSOR_REASONS = frozenset(
    {
        "no_later_attempt",
        "no_later_attempt_in_window",
        "incompatible_curriculum",
        "incompatible_content_version",
        "incompatible_policy_version",
        "immediate_question_repeat",
        "counterfactual_difficulty_mismatch",
    }
)
OPTIONAL_CENSOR_REASONS = frozenset({"revoked_lineage", "missing_telemetry"})
ALLOWED_CENSOR_REASONS = REQUIRED_CENSOR_REASONS | OPTIONAL_CENSOR_REASONS

DEFAULT_RECONSTRUCTION_NOTES = (
    "last_transition is derived from the same arm's own previous reconstructed "
    "decision; bank exposure counts only prior attempts in the same "
    "learner/subtopic history; banks observed in the dataset are treated as "
    "active unless a bank catalogue overrides them."
)


class RunManifestError(ValueError):
    """Raised when a run manifest is missing, altered, or incompatible."""


@dataclass(frozen=True)
class OutcomeWindow:
    max_later_attempts: int
    max_calendar_duration_days: int

    def __post_init__(self) -> None:
        if self.max_later_attempts < 1:
            raise RunManifestError("outcome window requires at least one later attempt")
        if self.max_calendar_duration_days < 1:
            raise RunManifestError("outcome window requires a positive calendar duration")

    def to_document(self) -> dict[str, int]:
        return {
            "maxLaterAttempts": self.max_later_attempts,
            "maxCalendarDurationDays": self.max_calendar_duration_days,
        }

    @classmethod
    def from_document(cls, data: Mapping[str, object]) -> "OutcomeWindow":
        return cls(
            max_later_attempts=_positive_int(data, "maxLaterAttempts"),
            max_calendar_duration_days=_positive_int(data, "maxCalendarDurationDays"),
        )


@dataclass(frozen=True)
class EvaluationRunManifest:
    """One frozen, deterministic evaluation run contract."""

    manifest_version: str
    dataset_version: str
    dataset_sha256: str
    provenance: str
    hmac_namespace: str
    source_schema_version: str
    feature_schema_version: str
    bkt_version: str
    adaptive_policy_version: str
    adaptive_policy_sha256: str
    policy_evaluation_version: str
    policy_evaluation_sha256: str
    frozen_prediction_target: str
    label_version: str
    outcome_window: OutcomeWindow
    censoring_rules: frozenset[str]
    random_seed: int
    claim_label: str
    reconstruction_notes: str

    def __post_init__(self) -> None:
        if self.manifest_version != RUN_MANIFEST_VERSION:
            raise RunManifestError("unsupported policy evaluation run manifest version")
        if not self.dataset_version or not self.hmac_namespace:
            raise RunManifestError("dataset version and HMAC namespace are required")
        if len(self.dataset_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.dataset_sha256
        ):
            raise RunManifestError("datasetSha256 must be lowercase SHA-256 hex")
        if self.provenance not in ALLOWED_PROVENANCES:
            raise RunManifestError(f"provenance is not allowed for replay: {self.provenance}")
        if self.claim_label not in ALLOWED_CLAIM_LABELS:
            raise RunManifestError(f"claim label is not allowed: {self.claim_label}")
        if self.claim_label == "descriptive_replay_only" and self.provenance != "real":
            raise RunManifestError(
                "descriptive_replay_only requires approved real records"
            )
        if self.frozen_prediction_target != PREDICTION_TARGET:
            raise RunManifestError("frozen prediction target does not match the U7 contract")
        if self.label_version != PREDICTION_LABEL_VERSION:
            raise RunManifestError("label version does not match the U7 contract")
        if not self.censoring_rules or not self.censoring_rules <= ALLOWED_CENSOR_REASONS:
            raise RunManifestError("censoring rules are incomplete or undeclared")
        if not REQUIRED_CENSOR_REASONS <= self.censoring_rules:
            missing = sorted(REQUIRED_CENSOR_REASONS - self.censoring_rules)
            raise RunManifestError(f"censoring rules are missing required reasons: {missing}")
        if self.random_seed < 0:
            raise RunManifestError("random seed cannot be negative")
        if not self.reconstruction_notes:
            raise RunManifestError("reconstruction notes are required")
        for name, value in (
            ("source_schema_version", self.source_schema_version),
            ("feature_schema_version", self.feature_schema_version),
            ("bkt_version", self.bkt_version),
            ("adaptive_policy_version", self.adaptive_policy_version),
            ("policy_evaluation_version", self.policy_evaluation_version),
        ):
            if not value:
                raise RunManifestError(f"{name} is required")

    def manifest_sha256(self) -> str:
        return _canonical_sha256(self.to_document())

    def to_document(self) -> dict[str, object]:
        return {
            "manifestVersion": self.manifest_version,
            "datasetVersion": self.dataset_version,
            "datasetSha256": self.dataset_sha256,
            "provenance": self.provenance,
            "hmacNamespace": self.hmac_namespace,
            "sourceSchemaVersion": self.source_schema_version,
            "featureSchemaVersion": self.feature_schema_version,
            "bktVersion": self.bkt_version,
            "adaptivePolicyVersion": self.adaptive_policy_version,
            "adaptivePolicySha256": self.adaptive_policy_sha256,
            "policyEvaluationVersion": self.policy_evaluation_version,
            "policyEvaluationSha256": self.policy_evaluation_sha256,
            "frozenPredictionTarget": self.frozen_prediction_target,
            "labelVersion": self.label_version,
            "outcomeWindow": self.outcome_window.to_document(),
            "censoringRules": sorted(self.censoring_rules),
            "randomSeed": self.random_seed,
            "claimLabel": self.claim_label,
            "reconstructionNotes": self.reconstruction_notes,
        }

    @classmethod
    def from_document(cls, data: Mapping[str, object]) -> "EvaluationRunManifest":
        _require_exact_keys(
            data,
            {
                "manifestVersion", "datasetVersion", "datasetSha256", "provenance",
                "hmacNamespace", "sourceSchemaVersion", "featureSchemaVersion",
                "bktVersion", "adaptivePolicyVersion", "adaptivePolicySha256",
                "policyEvaluationVersion", "policyEvaluationSha256",
                "frozenPredictionTarget", "labelVersion", "outcomeWindow",
                "censoringRules", "randomSeed", "claimLabel", "reconstructionNotes",
            },
            "run manifest",
        )
        return cls(
            manifest_version=_string(data, "manifestVersion"),
            dataset_version=_string(data, "datasetVersion"),
            dataset_sha256=_string(data, "datasetSha256"),
            provenance=_string(data, "provenance"),
            hmac_namespace=_string(data, "hmacNamespace"),
            source_schema_version=_string(data, "sourceSchemaVersion"),
            feature_schema_version=_string(data, "featureSchemaVersion"),
            bkt_version=_string(data, "bktVersion"),
            adaptive_policy_version=_string(data, "adaptivePolicyVersion"),
            adaptive_policy_sha256=_string(data, "adaptivePolicySha256"),
            policy_evaluation_version=_string(data, "policyEvaluationVersion"),
            policy_evaluation_sha256=_string(data, "policyEvaluationSha256"),
            frozen_prediction_target=_string(data, "frozenPredictionTarget"),
            label_version=_string(data, "labelVersion"),
            outcome_window=OutcomeWindow.from_document(_mapping(data, "outcomeWindow")),
            censoring_rules=frozenset(_string_list(data, "censoringRules")),
            random_seed=_non_negative_int(data, "randomSeed"),
            claim_label=_string(data, "claimLabel"),
            reconstruction_notes=_string(data, "reconstructionNotes"),
        )


def build_run_manifest(
    *,
    dataset: SourceDataset,
    dataset_version: str,
    adaptive_policy_sha256: str,
    policy_evaluation_sha256: str,
    outcome_window: OutcomeWindow,
    random_seed: int,
    claim_label: str,
    hmac_namespace: str = "policy-evaluation-replay-v1",
    censoring_rules: frozenset[str] = REQUIRED_CENSOR_REASONS,
    reconstruction_notes: str = DEFAULT_RECONSTRUCTION_NOTES,
) -> EvaluationRunManifest:
    """Create the deterministic manifest for a replay of ``dataset``."""
    return EvaluationRunManifest(
        manifest_version=RUN_MANIFEST_VERSION,
        dataset_version=dataset_version,
        dataset_sha256=dataset_sha256(dataset),
        provenance=dataset.provenance,
        hmac_namespace=hmac_namespace,
        source_schema_version=dataset.schema_version,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        bkt_version=BKT_MODEL_VERSION,
        adaptive_policy_version=ADAPTIVE_POLICY_VERSION,
        adaptive_policy_sha256=adaptive_policy_sha256,
        policy_evaluation_version=POLICY_EVALUATION_MANIFEST_VERSION,
        policy_evaluation_sha256=policy_evaluation_sha256,
        frozen_prediction_target=PREDICTION_TARGET,
        label_version=PREDICTION_LABEL_VERSION,
        outcome_window=outcome_window,
        censoring_rules=censoring_rules,
        random_seed=random_seed,
        claim_label=claim_label,
        reconstruction_notes=reconstruction_notes,
    )


def load_run_manifest(path: str | Path) -> EvaluationRunManifest:
    """Load and validate a frozen run manifest; any failure fails closed."""
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunManifestError(f"run manifest is unavailable: {source}") from error
    if not isinstance(data, dict):
        raise RunManifestError("run manifest must be a JSON object")
    return EvaluationRunManifest.from_document(data)


def write_run_manifest(manifest: EvaluationRunManifest, path: str | Path) -> None:
    """Write the manifest deterministically (used by the runner and tests)."""
    destination = Path(path)
    destination.write_text(
        json.dumps(manifest.to_document(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def dataset_sha256(dataset: SourceDataset) -> str:
    """Stable content hash of the validated dataset (no raw answer text)."""
    attempts = [
        {
            "attemptId": attempt.attempt_id,
            "sessionId": attempt.session_id,
            "studentId": attempt.student_id,
            "subtopicId": attempt.subtopic_id,
            "totalQuestions": attempt.total_questions,
            "correctCount": attempt.correct_count,
            "score": attempt.score,
            "finalizationStatus": attempt.finalization_status,
            "validationStatus": attempt.validation_status,
            "dataSource": attempt.data_source,
            "finalizedAt": attempt.finalized_at.isoformat(),
            "sourceAttemptSequence": attempt.source_attempt_sequence,
            "yearLevel": attempt.year_level,
            "responseIds": list(attempt.response_ids),
        }
        for attempt in sorted(
            dataset.attempts, key=lambda item: (item.source_attempt_sequence or 0, item.attempt_id)
        )
    ]
    responses = [
        {
            "attemptId": response.attempt_id,
            "responseId": response.response_id,
            "sequenceIndex": response.sequence_index,
            "serverIsCorrect": response.is_correct,
            "skillId": response.skill_id,
            "questionId": response.question_id,
        }
        for attempt in sorted(
            dataset.attempts, key=lambda item: (item.source_attempt_sequence or 0, item.attempt_id)
        )
        for response in sorted(
            dataset.responses_by_attempt[attempt.attempt_id],
            key=lambda item: item.sequence_index,
        )
    ]
    contexts = [
        {
            "attemptId": attempt_id,
            "topicId": context.topic_id,
            "subtopicId": context.subtopic_id,
            "bankId": context.bank_id,
            "difficultyLevel": context.difficulty_level,
            "contentVersion": context.content_version,
            "assignmentId": context.assignment_id,
            "assignmentSource": context.assignment_source,
            "adaptivePolicyVersion": context.adaptive_policy_version,
        }
        for attempt_id, context in sorted(dataset.attempt_context_by_id.items())
    ]
    payload = {
        "schemaVersion": dataset.schema_version,
        "provenance": dataset.provenance,
        "attempts": attempts,
        "responses": responses,
        "contexts": contexts,
    }
    return _canonical_sha256(payload)


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return sha256(serialized.encode("utf-8")).hexdigest()


def _require_exact_keys(
    data: Mapping[str, object], expected: set[str], section: str
) -> None:
    if set(data) != expected:
        missing = sorted(expected - set(data))
        extra = sorted(set(data) - expected)
        raise RunManifestError(
            f"{section} keys are invalid; missing={missing}, extra={extra}"
        )


def _mapping(data: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise RunManifestError(f"run manifest requires mapping: {key}")
    return value


def _string(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise RunManifestError(f"run manifest requires string: {key}")
    return value


def _string_list(data: Mapping[str, object], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise RunManifestError(f"run manifest requires string list: {key}")
    if len(set(value)) != len(value):
        raise RunManifestError(f"run manifest list contains duplicates: {key}")
    return value


def _positive_int(data: Mapping[str, object], key: str) -> int:
    value = _non_negative_int(data, key)
    if value < 1:
        raise RunManifestError(f"run manifest requires positive integer: {key}")
    return value


def _non_negative_int(data: Mapping[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise RunManifestError(f"run manifest requires non-negative integer: {key}")
    return value

