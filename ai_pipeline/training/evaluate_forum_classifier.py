"""Leakage-safe controlled-demonstration evaluation for the U10 forum model."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import platform
import time
from typing import Iterable, Mapping, Sequence

import joblib
import numpy
import sklearn
import yaml
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
    f1_score,
)
from sklearn.model_selection import StratifiedGroupKFold

from forum_controlled_demo.build_forum_dataset import (
    DEFAULT_CATALOGUE_PATH,
    ForumDatasetBuild,
    ForumDatasetRow,
    build_forum_dataset,
    canonical_json_bytes,
    forum_dataset_jsonl_bytes,
    portable_path_identity,
    publish_files_atomically,
    validate_forum_dataset_build,
)
from forum_controlled_demo.schema import (
    CLAIM_LEVEL,
    DEPLOYMENT_SCOPE,
    EVIDENCE_LEVEL,
    PROVENANCE,
    RELEASE_SCOPE,
    RUBRIC_DOCUMENT,
)
from logic_oasis_ai.forum_ai.classifier import (
    CONTROLLED_REVISION,
    CONTROLLED_SUFFICIENT,
    VECTORIZER_CONTRACT,
    ForumTextClassifier,
    build_forum_vectorizer,
    normalize_forum_text,
)
from training.train_forum_classifier import train_controlled_demo_candidate


RANDOM_SEED = 20260803
MODEL_VERSION = "forum-controlled-demo-nb-v1"
LIMITATION_STATEMENT = (
    "The metrics demonstrate reproducible classifier behaviour, scenario-fit, artifact integrity, "
    "and prototype integration readiness. They do not establish predictive accuracy, "
    "generalisability, educational effectiveness, or performance for real primary-school learners."
)
LABEL_ORDER = (CONTROLLED_REVISION, CONTROLLED_SUFFICIENT)
VARIANTS = ("MultinomialNB", "ComplementNB")
BASELINE = "deterministic_answer_only_baseline"
ALLOWED_OPERATOR_ROLES = frozenset({"developer", "reviewer", "release-operator"})
CONTROLLED_EVIDENCE_CONTRACT = {
    "claimLevel": CLAIM_LEVEL,
    "trainingDataProvenance": PROVENANCE,
    "evidenceLevel": EVIDENCE_LEVEL,
    "releaseScope": RELEASE_SCOPE,
    "deploymentScope": DEPLOYMENT_SCOPE,
}


@dataclass(frozen=True)
class ForumEvaluation:
    report: Mapping[str, object]
    split_manifest: Mapping[str, object]
    candidate: ForumTextClassifier | None
    artifact_bytes: bytes | None


def evaluate_forum_controlled_demo(
    rows: Iterable[ForumDatasetRow],
    dataset_manifest: Mapping[str, object],
    *,
    random_seed: int = RANDOM_SEED,
) -> ForumEvaluation:
    values = tuple(sorted(rows, key=lambda row: (row.scenario_family_id, row.example_id)))
    contract_failure = _evidence_contract_failure(values, dataset_manifest)
    split = _grouped_split(values, random_seed=random_seed)
    if contract_failure or split["evaluationMode"] == "insufficient":
        reasons = [item for item in (contract_failure, split.get("reason")) if item]
        return ForumEvaluation(
            report=_insufficient_report(values, dataset_manifest, split, reasons, random_seed),
            split_manifest=split,
            candidate=None,
            artifact_bytes=None,
        )

    if split["evaluationMode"] == "grouped_three_way":
        train = _rows_for(values, split["trainScenarioFamilyIds"])
        validation = _rows_for(values, split["validationScenarioFamilyIds"])
        test = _rows_for(values, split["testScenarioFamilyIds"])
        selection_results = {
            variant: _fit_and_score(variant, train, validation)
            for variant in VARIANTS
        }
        baseline_selection = _baseline_score(train, validation)
        selected = _select_variant(selection_results)
        candidate = train_controlled_demo_candidate(
            (*train, *validation),
            model_version=MODEL_VERSION,
            variant=selected,
        )
        final_rows = test
        final_predictions = list(candidate.pipeline.predict(_normalized_texts(test)))
        final_probabilities = candidate.pipeline.predict_proba(_normalized_texts(test))
        comparator_results = {
            variant: (
                {
                    "metrics": _metrics([row.label for row in test], final_predictions),
                    "fitRows": len(train) + len(validation),
                    "heldOutRows": len(test),
                }
                if variant == selected
                else _fit_and_score(variant, (*train, *validation), test)
            )
            for variant in VARIANTS
        }
        comparator_results[BASELINE] = _baseline_score((*train, *validation), test)
        validation_labels = [row.label for row in validation]
        held_out_labels = [row.label for row in test]
        no_test_fit = True
        untouched_count = 1
        final_status = "final_test"
    else:
        selected, selection_results, candidate, cv_labels, cv_predictions, cv_probabilities = _grouped_cv_select(
            values, random_seed=random_seed,
        )
        baseline_selection = _grouped_cv_baseline(values, random_seed=random_seed)
        final_rows = values
        final_predictions = cv_predictions[selected]
        final_probabilities = cv_probabilities[selected]
        comparator_results = {variant: selection_results[variant] for variant in VARIANTS}
        comparator_results[BASELINE] = baseline_selection
        validation_labels = cv_labels
        held_out_labels = cv_labels
        no_test_fit = True
        untouched_count = 0
        final_status = "no_untouched_final_test"

    selection_evidence = _selection_evidence(values, split)
    selection_sha = sha256(canonical_json_bytes(selection_evidence)).hexdigest()
    labels = [row.label for row in final_rows] if split["evaluationMode"] == "grouped_three_way" else held_out_labels
    metrics = _metrics(labels, final_predictions)
    max_probabilities = [float(max(probabilities)) for probabilities in final_probabilities]
    published_count = sum(probability >= VECTORIZER_CONTRACT["abstentionThreshold"] for probability in max_probabilities)
    matrix = metrics["confusionMatrix"]["values"]
    artifact_bytes = _artifact_bytes(candidate)
    artifact_reproduces = _artifact_round_trip(candidate, artifact_bytes, values)
    failed_gates = candidate_gate_failures(
        training_labels=[row.label for row in _training_rows(values, split)],
        validation_labels=validation_labels,
        held_out_labels=held_out_labels,
        predictions=final_predictions,
        confusion_matrix=matrix,
        vocabulary_size=len(candidate.pipeline.named_steps["tfidf"].vocabulary_),
        preprocessing_valid=_pipeline_contract_valid(candidate),
        leakage_free=_split_is_leakage_free(values, split),
        no_test_fit=no_test_fit,
        published_count=published_count,
        held_out_count=len(labels),
        artifact_reproduces=artifact_reproduces,
        bindings_valid=_bindings_valid(values, dataset_manifest),
    )
    if split["evaluationMode"] == "grouped_cross_validation":
        failed_gates.extend(selection_results[selected].get("foldFailedGates", []))
        failed_gates = sorted(set(failed_gates))
    eligible = not failed_gates
    baseline_macro = float(baseline_selection["metrics"]["macroF1"])
    best_nb_macro = max(float(selection_results[name]["metrics"]["macroF1"]) for name in VARIANTS)
    baseline_comparison = (
        "naive_bayes_advantage_demonstrated"
        if best_nb_macro > baseline_macro
        else "no_controlled_scenario_advantage_demonstrated"
    )
    evidence_contract = _evidence_contract(dataset_manifest)
    comparators = {
        name: {**result, "evidenceContract": evidence_contract}
        for name, result in comparator_results.items()
    }
    runtime_fingerprint = _runtime_environment_fingerprint()
    report: dict[str, object] = {
        "reportSchemaVersion": "forum-controlled-demo-report-v1",
        "evaluationStatus": "evaluated",
        "evaluationMode": split["evaluationMode"],
        "applicableFinalTestStatus": final_status,
        "untouchedTestEvaluationCount": untouched_count,
        **metrics,
        "abstentionCoverage": _round(1 - published_count / len(labels)),
        "publicationCoverage": _round(published_count / len(labels)),
        "fallbackCoverage": _round((len(labels) - published_count) / len(labels)),
        "latencyMs": {
            "canonicalStatus": "execution_observation_excluded_from_canonical_report",
            "protocol": "single-row predict after warm load",
        },
        "serializedSizeBytes": len(artifact_bytes),
        "artifactByteHash": sha256(artifact_bytes).hexdigest(),
        "semanticReproducibilityStatus": (
            "verified_same_runtime_contract"
            if artifact_reproduces
            else "failed_artifact_round_trip"
        ),
        "runtimeEnvironmentFingerprint": runtime_fingerprint,
        "datasetCounts": {
            "rows": len(values),
            "scenarioFamilies": len({row.scenario_family_id for row in values}),
            "questionFamilies": len({row.question_family_id for row in values if row.question_family_id}),
            "classes": dict(sorted(Counter(row.label for row in values).items())),
            "languages": dict(sorted(Counter(row.language for row in values).items())),
        },
        "splitSeed": random_seed,
        "splitManifestSha256": sha256(canonical_json_bytes(split)).hexdigest(),
        "preprocessingVersion": VECTORIZER_CONTRACT["preprocessingVersion"],
        "preprocessingSha256": sha256(canonical_json_bytes(VECTORIZER_CONTRACT)).hexdigest(),
        "vectorizerContract": dict(VECTORIZER_CONTRACT),
        "outputContract": {
            "explanation_sufficient": "sufficient_reasoning",
            "answer_only_or_insufficient": "needs_reasoning",
            "abstained": "uncertain",
        },
        "rubricVersion": dataset_manifest["rubricVersion"],
        "rubricSha256": dataset_manifest["rubricSha256"],
        "catalogueVersion": dataset_manifest["catalogVersion"],
        "catalogueSha256": dataset_manifest["catalogueSha256"],
        "datasetSha256": dataset_manifest["datasetSha256"],
        "selectionMetric": "macroF1",
        "selectionEvidenceSha256": selection_sha,
        "candidateSelectionDecision": f"selected_{selected}_using_training_and_validation_only",
        "selectedNaiveBayesVariant": selected,
        "baselineComparisonResult": baseline_comparison,
        "controlledDemoActivationDecision": (
            "eligible_for_u5_release_review" if eligible else "blocked_by_non_degeneracy_gate"
        ),
        "controlledCandidateStatus": "eligible" if eligible else "rejected",
        "activationStatus": "pending_u5_activation" if eligible else "blocked",
        "failedGates": failed_gates,
        "comparators": comparators,
        **CONTROLLED_EVIDENCE_CONTRACT,
        "calibrationStatus": "not_established_on_real_learners",
        "limitations": [
            LIMITATION_STATEMENT,
            "The deterministic baseline is comparison-only and cannot be released or activated.",
            "A baseline win permits no Naive Bayes superiority claim.",
        ],
    }
    return ForumEvaluation(
        report=report,
        split_manifest=split,
        candidate=candidate if eligible else None,
        artifact_bytes=artifact_bytes if eligible else None,
    )


def candidate_gate_failures(
    *, training_labels: Sequence[object], validation_labels: Sequence[object],
    held_out_labels: Sequence[object], predictions: Sequence[object],
    confusion_matrix: Sequence[Sequence[int]], vocabulary_size: int,
    preprocessing_valid: bool, leakage_free: bool, no_test_fit: bool,
    published_count: int, held_out_count: int, artifact_reproduces: bool,
    bindings_valid: bool,
) -> list[str]:
    failures: list[str] = []
    if len(set(training_labels)) != 2:
        failures.append("training_missing_class")
    if len(set(validation_labels)) != 2:
        failures.append("validation_missing_class")
    if len(set(held_out_labels)) != 2:
        failures.append("held_out_missing_class")
    if len(set(predictions)) != 2:
        failures.append("single_class_predictions")
    valid_matrix = (
        len(confusion_matrix) == 2
        and all(len(row) == 2 for row in confusion_matrix)
        and all(isinstance(value, int) and value >= 0 for row in confusion_matrix for value in row)
    )
    if not valid_matrix:
        failures.append("invalid_confusion_matrix")
    elif any(confusion_matrix[index][index] == 0 for index in range(2)):
        failures.append("zero_recall")
    if vocabulary_size < 1:
        failures.append("empty_vocabulary")
    if not preprocessing_valid:
        failures.append("preprocessing_failed")
    if not leakage_free:
        failures.append("group_leakage")
    if not no_test_fit:
        failures.append("test_rows_fitted")
    if held_out_count < 1 or published_count < 1:
        failures.append("all_abstained")
    if not artifact_reproduces:
        failures.append("artifact_output_mismatch")
    if not bindings_valid:
        failures.append("binding_mismatch")
    return failures


def reject_controlled_provenance_for_real_evaluation(rows: Iterable[ForumDatasetRow]) -> None:
    if any(row.provenance == PROVENANCE for row in rows):
        raise ValueError("real-data evaluator rejects controlled-demonstration provenance")


def write_forum_evaluation(
    build: ForumDatasetBuild,
    output_directory: str | Path,
    *,
    report_directory: str | Path | None = None,
    operator_role: str = "developer",
) -> dict[str, Path]:
    if operator_role not in ALLOWED_OPERATOR_ROLES:
        raise ValueError(
            "operator role must be developer, reviewer, or release-operator"
        )
    build = validate_forum_dataset_build(build)
    output = Path(output_directory)
    reports = Path(report_directory) if report_directory is not None else output
    dataset_path = output / "forum_controlled_demo_v1.jsonl"
    dataset_manifest_path = output / "forum_controlled_demo_v1_manifest.json"
    candidate_path = output / "forum_controlled_demo_candidate.joblib"
    candidate_manifest_path = output / "forum_controlled_demo_candidate_manifest.json"
    dataset_paths = {"dataset": dataset_path, "manifest": dataset_manifest_path}
    evaluation = evaluate_forum_controlled_demo(build.rows, build.manifest)
    split_path = output / "forum_controlled_demo_split_manifest.json"
    execution_path = output / "forum_controlled_demo_execution_record.json"
    report_json_path = reports / "forum_controlled_demo_report.json"
    report_md_path = reports / "forum_controlled_demo_report.md"
    report = dict(evaluation.report)
    artifact_bytes: bytes | None = None
    if evaluation.candidate is not None:
        artifact_bytes = evaluation.artifact_bytes
        if artifact_bytes is None:
            raise ValueError("eligible candidate bytes are unavailable")
        if sha256(artifact_bytes).hexdigest() != report["artifactByteHash"]:
            raise ValueError("candidate byte hash changed within the compatible runtime")
    report_bytes = _pretty_json(report).encode("utf-8")
    candidate_manifest_bytes: bytes | None = None
    if evaluation.candidate is not None:
        candidate_manifest = {
            "manifestSchemaVersion": "forum-controlled-demo-candidate-manifest-v1",
            "datasetVersion": build.manifest["datasetVersion"],
            "catalogVersion": build.manifest["catalogVersion"],
            "splitSchemaVersion": evaluation.split_manifest["splitSchemaVersion"],
            "reportSchemaVersion": report["reportSchemaVersion"],
            "modelVersion": MODEL_VERSION,
            "modelType": report["selectedNaiveBayesVariant"],
            "catalogueFile": build.catalogue_source,
            "datasetFile": dataset_path.name,
            "datasetManifestFile": dataset_manifest_path.name,
            "splitManifestFile": split_path.name,
            "evaluationReportFile": report_json_path.name,
            "artifactFile": candidate_path.name,
            "artifactSha256": report["artifactByteHash"],
            "artifactSizeBytes": report["serializedSizeBytes"],
            "datasetSha256": build.manifest["datasetSha256"],
            "catalogueSha256": build.manifest["catalogueSha256"],
            "splitManifestSha256": report["splitManifestSha256"],
            "evaluationReportSha256": sha256(report_bytes).hexdigest(),
            "rubricVersion": build.manifest["rubricVersion"],
            "rubricSha256": build.manifest["rubricSha256"],
            "vectorizerContract": report["vectorizerContract"],
            "outputContract": report["outputContract"],
            "abstentionPolicyVersion": VECTORIZER_CONTRACT["abstentionPolicyVersion"],
            "controlledCandidateStatus": report["controlledCandidateStatus"],
            "activationStatus": report["activationStatus"],
            "claimLevel": report["claimLevel"],
            "trainingDataProvenance": report["trainingDataProvenance"],
            "evidenceLevel": report["evidenceLevel"],
            "releaseScope": report["releaseScope"],
            "deploymentScope": report["deploymentScope"],
            "semanticReproducibilityStatus": report["semanticReproducibilityStatus"],
            "runtimeEnvironmentFingerprint": report["runtimeEnvironmentFingerprint"],
        }
        candidate_manifest_bytes = _pretty_json(candidate_manifest).encode("utf-8")

    started = time.perf_counter()
    if evaluation.candidate is not None:
        evaluation.candidate.predict("First I regrouped the ones, then checked the total.")
    observed_latency = round((time.perf_counter() - started) * 1000, 6)
    execution = {
        "executionTimestampUtc": datetime.now(timezone.utc).isoformat(),
        "operatingSystem": platform.system(),
        "pythonVersion": platform.python_version(),
        "command": "python -m training.evaluate_forum_classifier",
        "commandArguments": [
            "--catalogue", build.catalogue_source,
            "--generated", portable_path_identity(output),
            "--reports", portable_path_identity(reports),
            "--operator-role", operator_role,
        ],
        "logicalWorkingPath": "ai_pipeline",
        "environmentMode": "controlled_demo_generation",
        "operatorRole": operator_role,
        "observedWarmPredictionLatencyMs": observed_latency,
    }
    publication = [
        (dataset_path, build.jsonl_bytes()),
        (dataset_manifest_path, _pretty_json(build.manifest).encode("utf-8")),
        (split_path, _pretty_json(evaluation.split_manifest).encode("utf-8")),
        (report_md_path, _markdown_report(report).encode("utf-8")),
        (execution_path, _pretty_json(execution).encode("utf-8")),
        (report_json_path, report_bytes),
        (candidate_path, artifact_bytes),
        (candidate_manifest_path, candidate_manifest_bytes),
    ]
    publish_files_atomically(
        publication,
        commit_marker=(candidate_manifest_path if candidate_manifest_bytes is not None else report_json_path),
    )
    paths = {
        **dataset_paths,
        "split_manifest": split_path,
        "execution_record": execution_path,
        "report_json": report_json_path,
        "report_markdown": report_md_path,
    }
    if evaluation.candidate is not None:
        paths.update({"candidate": candidate_path, "candidate_manifest": candidate_manifest_path})
    return paths


def _grouped_split(rows: Sequence[ForumDatasetRow], *, random_seed: int) -> dict[str, object]:
    groups = sorted({row.scenario_family_id for row in rows}, key=lambda value: _seeded_key(value, random_seed))
    # Connected question-family components must stay together even if a future
    # catalogue links more than one scenario family to the same question family.
    components = [set(values) for values in _linked_scenario_components(rows)]
    components.sort(key=lambda values: _seeded_key("|".join(sorted(values)), random_seed))
    if len(components) >= 8:
        test_components = components[-2:]
        validation_components = components[-4:-2]
        train_components = components[:-4]
        split = {
            "splitSchemaVersion": "forum-controlled-demo-grouped-split-v1",
            "evaluationMode": "grouped_three_way",
            "evaluationGroupKey": "scenarioFamilyId",
            "relatedQuestionGroupKey": "questionFamilyId",
            "randomSeed": random_seed,
            "trainScenarioFamilyIds": _flatten(train_components),
            "validationScenarioFamilyIds": _flatten(validation_components),
            "testScenarioFamilyIds": _flatten(test_components),
            "testUsePolicy": "untouched_until_naive_bayes_variant_and_pipeline_are_frozen",
        }
        if _partition_has_both_labels(rows, split):
            return split
    if len(components) >= 4 and _all_groups_have_both_labels(rows):
        return {
            "splitSchemaVersion": "forum-controlled-demo-grouped-split-v1",
            "evaluationMode": "grouped_cross_validation",
            "evaluationGroupKey": "scenarioFamilyId",
            "relatedQuestionGroupKey": "questionFamilyId",
            "randomSeed": random_seed,
            "foldCount": min(3, len(components)),
            "allScenarioFamilyIds": sorted(groups),
            "trainScenarioFamilyIds": [],
            "validationScenarioFamilyIds": [],
            "testScenarioFamilyIds": [],
            "testUsePolicy": "no_untouched_final_test_exists",
        }
    return {
        "splitSchemaVersion": "forum-controlled-demo-grouped-split-v1",
        "evaluationMode": "insufficient",
        "evaluationGroupKey": "scenarioFamilyId",
        "relatedQuestionGroupKey": "questionFamilyId",
        "randomSeed": random_seed,
        "trainScenarioFamilyIds": [],
        "validationScenarioFamilyIds": [],
        "testScenarioFamilyIds": [],
        "reason": "controlled catalogue cannot support grouped validation or grouped cross-validation with both labels",
    }


def _grouped_cv_select(rows: Sequence[ForumDatasetRow], *, random_seed: int):
    texts = [row.text for row in rows]
    labels = [row.label for row in rows]
    linked_groups = _linked_group_ids(rows)
    groups = [linked_groups[row.scenario_family_id] for row in rows]
    splitter = StratifiedGroupKFold(
        n_splits=min(3, len(set(groups))), shuffle=True, random_state=random_seed,
    )
    predictions: dict[str, list[str]] = {variant: [""] * len(rows) for variant in VARIANTS}
    probabilities: dict[str, list[list[float]]] = {variant: [[] for _ in rows] for variant in VARIANTS}
    fold_failures: dict[str, list[str]] = {variant: [] for variant in VARIANTS}
    for fold_index, (train_indices, held_indices) in enumerate(splitter.split(texts, labels, groups), 1):
        train_rows = [rows[index] for index in train_indices]
        held_rows = [rows[index] for index in held_indices]
        if len({row.label for row in train_rows}) != 2 or len({row.label for row in held_rows}) != 2:
            raise ValueError("grouped cross-validation fold lost class support")
        for variant in VARIANTS:
            model = train_controlled_demo_candidate(
                train_rows,
                model_version=MODEL_VERSION,
                variant=variant,
            )
            fold_predictions = model.pipeline.predict(_normalized_texts(held_rows))
            fold_probabilities = model.pipeline.predict_proba(_normalized_texts(held_rows))
            fold_matrix = confusion_matrix(
                [row.label for row in held_rows], fold_predictions, labels=LABEL_ORDER,
            ).astype(int).tolist()
            fold_published = sum(
                float(max(probability)) >= VECTORIZER_CONTRACT["abstentionThreshold"]
                for probability in fold_probabilities
            )
            for failure in _fold_prediction_gate_failures(
                predictions=fold_predictions,
                confusion=fold_matrix,
                published_count=fold_published,
            ):
                fold_failures[variant].append(f"fold_{fold_index}_{failure}")
            for index, prediction, probability in zip(held_indices, fold_predictions, fold_probabilities):
                predictions[variant][int(index)] = str(prediction)
                probabilities[variant][int(index)] = [float(value) for value in probability]
    results = {
        variant: {
            "metrics": _metrics(labels, predictions[variant]),
            "fitRows": len(rows),
            "heldOutRows": len(rows),
            "foldFailedGates": fold_failures[variant],
        }
        for variant in VARIANTS
    }
    selected = _select_variant(results)
    candidate = train_controlled_demo_candidate(
        rows, model_version=MODEL_VERSION, variant=selected,
    )
    return selected, results, candidate, labels, predictions, probabilities


def _fold_prediction_gate_failures(*, predictions, confusion, published_count):
    failures = []
    if len(set(predictions)) != 2:
        failures.append("single_class_predictions")
    if any(confusion[index][index] == 0 for index in range(2)):
        failures.append("zero_recall")
    if published_count < 1:
        failures.append("all_abstained")
    return failures


def _fit_and_score(variant: str, train: Sequence[ForumDatasetRow], held: Sequence[ForumDatasetRow]) -> dict[str, object]:
    model = train_controlled_demo_candidate(
        train, model_version=MODEL_VERSION, variant=variant,
    )
    predictions = model.pipeline.predict(_normalized_texts(held))
    return {
        "metrics": _metrics([row.label for row in held], predictions),
        "fitRows": len(train),
        "heldOutRows": len(held),
    }


def _baseline_score(
    train: Sequence[ForumDatasetRow], held: Sequence[ForumDatasetRow],
) -> dict[str, object]:
    predictions, vocabulary_size = _baseline_predictions(train, held)
    return {
        "metrics": _metrics([row.label for row in held], predictions),
        "fitRows": len(train),
        "heldOutRows": len(held),
        "vectorizerVocabularySize": vocabulary_size,
    }


def _baseline_predictions(
    train: Sequence[ForumDatasetRow], held: Sequence[ForumDatasetRow],
) -> tuple[list[str], int]:
    vectorizer = build_forum_vectorizer()
    vectorizer.fit(_normalized_texts(train))
    matrix = vectorizer.transform(_normalized_texts(held))
    predictions = [
        CONTROLLED_SUFFICIENT if feature_count >= 4 else CONTROLLED_REVISION
        for feature_count in matrix.getnnz(axis=1)
    ]
    return predictions, len(vectorizer.vocabulary_)


def _grouped_cv_baseline(
    rows: Sequence[ForumDatasetRow], *, random_seed: int,
) -> dict[str, object]:
    labels = [row.label for row in rows]
    linked_groups = _linked_group_ids(rows)
    groups = [linked_groups[row.scenario_family_id] for row in rows]
    splitter = StratifiedGroupKFold(
        n_splits=min(3, len(set(groups))), shuffle=True, random_state=random_seed,
    )
    predictions = [""] * len(rows)
    vocabulary_sizes = []
    for train_indices, held_indices in splitter.split(_normalized_texts(rows), labels, groups):
        train_rows = [rows[index] for index in train_indices]
        held_rows = [rows[index] for index in held_indices]
        fold_predictions, vocabulary_size = _baseline_predictions(train_rows, held_rows)
        vocabulary_sizes.append(vocabulary_size)
        for index, prediction in zip(held_indices, fold_predictions):
            predictions[int(index)] = prediction
    return {
        "metrics": _metrics(labels, predictions),
        "fitRows": len(rows),
        "heldOutRows": len(rows),
        "vectorizerVocabularySize": min(vocabulary_sizes),
    }


def _normalized_texts(rows: Sequence[ForumDatasetRow]) -> list[str]:
    return [normalize_forum_text(row.text) for row in rows]


def _metrics(labels: Sequence[object], predictions: Sequence[object]) -> dict[str, object]:
    precision, recall, f1, support = precision_recall_fscore_support(
        labels, predictions, labels=LABEL_ORDER, zero_division=0,
    )
    matrix = confusion_matrix(labels, predictions, labels=LABEL_ORDER).astype(int).tolist()
    return {
        "accuracy": _round(accuracy_score(labels, predictions)),
        "macroF1": _round(f1_score(labels, predictions, labels=LABEL_ORDER, average="macro", zero_division=0)),
        "balancedAccuracy": _round(balanced_accuracy_score(labels, predictions)),
        "perClass": {
            label: {
                "precision": _round(precision[index]),
                "recall": _round(recall[index]),
                "f1": _round(f1[index]),
                "support": int(support[index]),
            }
            for index, label in enumerate(LABEL_ORDER)
        },
        "confusionMatrix": {
            "labels": list(LABEL_ORDER),
            "values": matrix,
        },
    }


def _select_variant(results: Mapping[str, Mapping[str, object]]) -> str:
    return sorted(
        VARIANTS,
        key=lambda name: (-float(results[name]["metrics"]["macroF1"]), VARIANTS.index(name)),
    )[0]


def _insufficient_report(rows, manifest, split, reasons, random_seed):
    return {
        "reportSchemaVersion": "forum-controlled-demo-report-v1",
        "evaluationStatus": "controlled_catalogue_insufficient",
        "evaluationMode": split["evaluationMode"],
        "applicableFinalTestStatus": "no_untouched_final_test",
        "untouchedTestEvaluationCount": 0,
        "candidateSelectionDecision": "no_candidate",
        "selectedNaiveBayesVariant": None,
        "baselineComparisonResult": "not_evaluated_catalogue_insufficient",
        "controlledDemoActivationDecision": "blocked_catalogue_insufficient",
        "controlledCandidateStatus": "rejected",
        "activationStatus": "blocked",
        "failedGates": reasons,
        "datasetCounts": {
            "rows": len(rows),
            "scenarioFamilies": len({row.scenario_family_id for row in rows}),
            "classes": dict(sorted(Counter(row.label for row in rows).items())),
        },
        "splitSeed": random_seed,
        "rubricVersion": manifest.get("rubricVersion"),
        "catalogueVersion": manifest.get("catalogVersion"),
        "catalogueSha256": manifest.get("catalogueSha256"),
        "datasetSha256": manifest.get("datasetSha256"),
        **CONTROLLED_EVIDENCE_CONTRACT,
        "calibrationStatus": "not_established_on_real_learners",
        "limitations": [LIMITATION_STATEMENT],
    }


def _evidence_contract_failure(rows, manifest):
    if not rows:
        return "empty_catalogue"
    expected = {**CONTROLLED_EVIDENCE_CONTRACT, "evaluationGroupKey": "scenarioFamilyId"}
    if any(manifest.get(key) != value for key, value in expected.items()):
        return "evidence_binding_mismatch"
    if {row.label for row in rows} != set(LABEL_ORDER):
        return "catalogue_missing_class"
    if any(row.provenance != PROVENANCE for row in rows):
        return "provenance_mismatch"
    return None


def _evidence_contract(manifest):
    return {
        "datasetSha256": manifest["datasetSha256"],
        "evaluationGroupKey": "scenarioFamilyId",
        "relatedQuestionGroupKey": "questionFamilyId",
        "preprocessingVersion": VECTORIZER_CONTRACT["preprocessingVersion"],
        "vectorizerFamily": VECTORIZER_CONTRACT["family"],
        "ngramRange": VECTORIZER_CONTRACT["ngramRange"],
        "minimumDocumentFrequency": VECTORIZER_CONTRACT["minimumDocumentFrequency"],
        "abstentionPolicyVersion": VECTORIZER_CONTRACT["abstentionPolicyVersion"],
    }


def _selection_evidence(rows, split):
    excluded = set(split.get("testScenarioFamilyIds", []))
    return [row.document() for row in rows if row.scenario_family_id not in excluded]


def _artifact_bytes(candidate):
    return candidate.to_bytes()


def _artifact_round_trip(candidate, artifact_bytes, rows):
    try:
        saved = joblib.load(io.BytesIO(artifact_bytes))
        restored = ForumTextClassifier(saved["pipeline"], model_version=saved["modelVersion"])
        sample = rows[0].text
        return restored.predict(sample) == candidate.predict(sample)
    except Exception:
        return False


def _runtime_environment_fingerprint():
    document = {
        "pythonImplementation": platform.python_implementation(),
        "pythonVersion": platform.python_version(),
        "scikitLearnVersion": sklearn.__version__,
        "joblibVersion": joblib.__version__,
        "numpyVersion": numpy.__version__,
        "pyYamlVersion": yaml.__version__,
        "operatingSystem": platform.system(),
        "architecture": platform.machine(),
    }
    return {"sha256": sha256(canonical_json_bytes(document)).hexdigest(), **document}


def _pipeline_contract_valid(candidate):
    vectorizer = candidate.pipeline.named_steps.get("tfidf")
    return (
        vectorizer is not None
        and tuple(vectorizer.ngram_range) == tuple(VECTORIZER_CONTRACT["ngramRange"])
        and vectorizer.min_df == VECTORIZER_CONTRACT["minimumDocumentFrequency"]
        and vectorizer.sublinear_tf is True
    )


def _bindings_valid(rows, manifest):
    class_counts = dict(sorted(Counter(row.label for row in rows).items()))
    language_counts = dict(sorted(Counter(row.language for row in rows).items()))
    catalogue_hashes = {row.catalogue_sha256 for row in rows}
    rubric_hashes = {row.rubric_sha256 for row in rows}
    author_declarations = {row.author_declaration for row in rows}
    return (
        all(row.rubric_version == manifest.get("rubricVersion") for row in rows)
        and all(row.catalog_version == manifest.get("catalogVersion") for row in rows)
        and catalogue_hashes == {manifest.get("catalogueSha256")}
        and rubric_hashes == {manifest.get("rubricSha256")}
        and rubric_hashes == {sha256(canonical_json_bytes(RUBRIC_DOCUMENT)).hexdigest()}
        and author_declarations == {manifest.get("authorDeclaration")}
        and manifest.get("rowCount") == len(rows)
        and manifest.get("scenarioFamilyCount") == len({row.scenario_family_id for row in rows})
        and manifest.get("questionFamilyCount") == len({row.question_family_id for row in rows if row.question_family_id})
        and manifest.get("classCounts") == class_counts
        and manifest.get("languageCounts") == language_counts
        and manifest.get("containsLearnerIdentity") is False
        and manifest.get("containsCopiedForumText") is False
        and manifest.get("containsAnswerKeys") is False
        and manifest.get("containsLearnerDistributionClaims") is False
        and sha256(forum_dataset_jsonl_bytes(rows)).hexdigest() == manifest.get("datasetSha256")
    )


def _split_is_leakage_free(rows, split):
    if split["evaluationMode"] == "grouped_cross_validation":
        return True
    partitions = [set(split[key]) for key in (
        "trainScenarioFamilyIds", "validationScenarioFamilyIds", "testScenarioFamilyIds",
    )]
    if any(partitions[i] & partitions[j] for i in range(3) for j in range(i + 1, 3)):
        return False
    assignment = {group: index for index, groups in enumerate(partitions) for group in groups}
    question_assignments: dict[str, set[int]] = {}
    for row in rows:
        if row.question_family_id:
            question_assignments.setdefault(row.question_family_id, set()).add(assignment[row.scenario_family_id])
    return all(len(values) == 1 for values in question_assignments.values())


def _linked_scenario_components(rows):
    scenario_ids = {row.scenario_family_id for row in rows}
    links = {scenario: {scenario} for scenario in scenario_ids}
    question_to_scenarios: dict[str, set[str]] = {}
    for row in rows:
        if row.question_family_id:
            question_to_scenarios.setdefault(row.question_family_id, set()).add(row.scenario_family_id)
    for scenarios in question_to_scenarios.values():
        for scenario in scenarios:
            links[scenario] |= scenarios
    changed = True
    while changed:
        changed = False
        for scenario in scenario_ids:
            expanded = set().union(*(links[item] for item in links[scenario]))
            if expanded != links[scenario]:
                links[scenario] = expanded
                changed = True
    return {frozenset(links[scenario]) for scenario in scenario_ids}


def _linked_group_ids(rows):
    """Map scenario families to a stable connected question-family component."""
    return {
        scenario: "|".join(sorted(component))
        for component in _linked_scenario_components(rows)
        for scenario in component
    }


def _partition_has_both_labels(rows, split):
    return all(
        {row.label for row in _rows_for(rows, split[key])} == set(LABEL_ORDER)
        for key in ("trainScenarioFamilyIds", "validationScenarioFamilyIds", "testScenarioFamilyIds")
    )


def _all_groups_have_both_labels(rows):
    return all(
        {row.label for row in rows if row.scenario_family_id == group} == set(LABEL_ORDER)
        for group in {row.scenario_family_id for row in rows}
    )


def _training_rows(rows, split):
    if split["evaluationMode"] == "grouped_three_way":
        return _rows_for(rows, split["trainScenarioFamilyIds"])
    return list(rows)


def _rows_for(rows, groups):
    wanted = set(groups)
    return [row for row in rows if row.scenario_family_id in wanted]


def _flatten(components):
    return sorted(group for component in components for group in component)


def _seeded_key(value, seed):
    return sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()


def _round(value):
    return round(float(value), 8)


def _pretty_json(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _markdown_report(report):
    lines = [
        "# Forum controlled-demonstration evaluation report", "",
        f"- Evaluation mode: `{report['evaluationMode']}`",
        f"- Candidate: `{report['selectedNaiveBayesVariant']}`",
        f"- Candidate status: `{report['controlledCandidateStatus']}`",
        f"- Activation status: `{report['activationStatus']}`",
        f"- Claim level: `{report['claimLevel']}`", "",
        "## Metrics", "",
    ]
    if report.get("evaluationStatus") == "evaluated":
        lines.extend([
            f"- Accuracy: `{report['accuracy']}`",
            f"- Macro F1: `{report['macroF1']}`",
            f"- Balanced accuracy: `{report['balancedAccuracy']}`",
            f"- Publication coverage: `{report['publicationCoverage']}`",
            f"- Fallback coverage: `{report['fallbackCoverage']}`", "",
            "## Selection and baseline", "",
            f"- Selection decision: `{report['candidateSelectionDecision']}`",
            f"- Baseline comparison: `{report['baselineComparisonResult']}`",
            "- The baseline is comparison-only and is never a releasable candidate.", "",
        ])
    lines.extend(["## Limitations", "", *[f"- {item}" for item in report["limitations"]]])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalogue", type=Path, default=DEFAULT_CATALOGUE_PATH)
    parser.add_argument(
        "--generated", type=Path,
        default=Path(__file__).resolve().parents[1] / "forum_controlled_demo" / "generated",
    )
    parser.add_argument(
        "--reports", type=Path,
        default=Path(__file__).resolve().parents[1] / "reports",
    )
    parser.add_argument("--operator-role", default=os.environ.get("FORUM_DEMO_OPERATOR_ROLE", "developer"))
    args = parser.parse_args()
    build = build_forum_dataset(args.catalogue)
    paths = write_forum_evaluation(
        build, args.generated, report_directory=args.reports, operator_role=args.operator_role,
    )
    print(json.dumps({key: path.as_posix() for key, path in paths.items()}, sort_keys=True))


if __name__ == "__main__":
    main()
