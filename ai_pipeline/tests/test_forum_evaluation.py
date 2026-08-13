from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
import joblib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from forum_controlled_demo.build_forum_dataset import (
    DEFAULT_CATALOGUE_PATH,
    build_forum_dataset,
    forum_dataset_jsonl_bytes,
)
from logic_oasis_ai.forum_ai.classifier import CONTROLLED_REVISION, ForumTextClassifier
from logic_oasis_ai.forum_ai.relevance import (
    RELEVANCE_CONTRACT,
    ForumRelevanceClassifier,
    relevance_input,
    train_relevance_classifier,
)
from training.evaluate_forum_classifier import (
    LIMITATION_STATEMENT,
    candidate_gate_failures,
    evaluate_forum_controlled_demo,
    reject_controlled_provenance_for_real_evaluation,
    write_forum_evaluation,
)


class ForumRelevanceComponentTests(unittest.TestCase):
    def _training_rows(self):
        return [
            (
                "What is 46 + 27?",
                "First I add the ones, regroup ten ones as one ten, then add the tens and check by subtracting.",
                "relevant",
            ),
            (
                "What is 46 + 27?",
                "I counted on from forty-six and added twenty-seven in place-value steps.",
                "relevant",
            ),
            (
                "What is 46 + 27?",
                "I added the tens, regrouped the ones, and checked with subtraction.",
                "relevant",
            ),
            (
                "What is 46 + 27?",
                "My favourite football team scored three goals at lunch.",
                "irrelevant",
            ),
            (
                "What is 46 + 27?",
                "After lunch I told my friend about the football match.",
                "irrelevant",
            ),
            (
                "What is 46 + 27?",
                "I drew a picture of my favourite colour for the school fair.",
                "irrelevant",
            ),
        ]

    def test_relevance_classifier_emits_positive_and_negative_with_frozen_thresholds(self):
        classifier = train_relevance_classifier(
            self._training_rows(), variant="ComplementNB",
        )
        positive = classifier.predict(
            "What is 46 + 27?",
            "I regrouped the ones into one ten and added the tens by place value.",
        )
        self.assertEqual("relevant", positive.label)
        self.assertGreaterEqual(
            positive.probability,
            float(RELEVANCE_CONTRACT["positiveThreshold"]),
        )

        negative = classifier.predict(
            "What is 46 + 27?",
            "At lunch my favourite football team won the match.",
        )
        self.assertEqual("irrelevant", negative.label)
        self.assertGreaterEqual(
            negative.probability,
            float(RELEVANCE_CONTRACT["negativeThreshold"]),
        )

    def test_relevance_classifier_can_abstain_and_round_trips(self):
        import tempfile
        from pathlib import Path

        classifier = train_relevance_classifier(
            self._training_rows(), variant="MultinomialNB",
        )
        uncertain = classifier.predict(
            "What is 46 + 27?",
            "Maybe I should ask a friend about this.",
        )
        self.assertIn(uncertain.label, {"relevant", "irrelevant", "uncertain"})

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "relevance.joblib"
            classifier.save(path)
            restored = ForumRelevanceClassifier.load(path)
            self.assertEqual(
                classifier.predict("What is 46 + 27?", "First I add the ones."),
                restored.predict("What is 46 + 27?", "First I add the ones."),
            )

    def test_relevance_contract_and_variant_validation(self):
        self.assertLess(
            float(RELEVANCE_CONTRACT["positiveThreshold"]),
            float(RELEVANCE_CONTRACT["negativeThreshold"]),
        )
        with self.assertRaisesRegex(ValueError, "variant"):
            train_relevance_classifier(
                self._training_rows(), variant="GaussianNB",
            )
        with self.assertRaisesRegex(ValueError, "both relevance labels"):
            train_relevance_classifier(self._training_rows()[:2])

    def test_relevance_input_combines_prompt_and_response_deterministically(self):
        self.assertEqual(
            "what is 46 + 27? first i add the ones.",
            relevance_input("What is 46 + 27?", "First I add the ones."),
        )


class ForumControlledDemoEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = build_forum_dataset()
        cls.evaluation = evaluate_forum_controlled_demo(cls.build.rows, cls.build.manifest)

    def test_three_way_groups_are_disjoint_and_final_test_is_evaluated_once(self):
        split = self.evaluation.split_manifest
        self.assertEqual("grouped_three_way", split["evaluationMode"])
        train = set(split["trainScenarioFamilyIds"])
        validation = set(split["validationScenarioFamilyIds"])
        test = set(split["testScenarioFamilyIds"])
        self.assertFalse(train & validation or train & test or validation & test)
        self.assertEqual(13, len(train | validation | test))
        self.assertEqual("final_test", self.evaluation.report["applicableFinalTestStatus"])
        self.assertEqual(1, self.evaluation.report["untouchedTestEvaluationCount"])
        self.assertGreaterEqual(len(test), 3)

    def test_training_never_receives_an_untouched_test_group(self):
        import training.evaluate_forum_classifier as evaluator

        test_groups = set(self.evaluation.split_manifest["testScenarioFamilyIds"])
        fitted_groups = []
        original = evaluator.train_controlled_demo_candidate

        def recording_train(rows, **kwargs):
            values = tuple(rows)
            fitted_groups.append({row.scenario_family_id for row in values})
            return original(values, **kwargs)

        with patch.object(evaluator, "train_controlled_demo_candidate", recording_train):
            evaluated = evaluator.evaluate_forum_controlled_demo(
                self.build.rows, self.build.manifest,
            )

        self.assertEqual("final_test", evaluated.report["applicableFinalTestStatus"])
        self.assertTrue(fitted_groups)
        self.assertTrue(all(not (groups & test_groups) for groups in fitted_groups))

    def test_selection_is_frozen_before_test_and_only_naive_bayes_can_win(self):
        original = self.evaluation
        test_groups = set(original.split_manifest["testScenarioFamilyIds"])
        changed_rows = tuple(
            replace(
                row,
                label=(
                    "answer_only_or_insufficient"
                    if row.label == "explanation_sufficient"
                    else "explanation_sufficient"
                ),
            ) if row.scenario_family_id in test_groups else row
            for row in self.build.rows
        )
        changed = evaluate_forum_controlled_demo(changed_rows, self.build.manifest)

        self.assertEqual(original.report["selectedNaiveBayesVariant"], changed.report["selectedNaiveBayesVariant"])
        self.assertEqual(original.report["candidateSelectionDecision"], changed.report["candidateSelectionDecision"])
        self.assertEqual(original.report["selectionEvidenceSha256"], changed.report["selectionEvidenceSha256"])
        self.assertIn(original.report["selectedNaiveBayesVariant"], {"MultinomialNB", "ComplementNB"})
        self.assertNotEqual("deterministic_answer_only_baseline", original.report["selectedNaiveBayesVariant"])

    def test_grouped_cv_fallback_and_catalogue_insufficiency_do_not_invent_final_test(self):
        group_order = sorted({row.scenario_family_id for row in self.build.rows})
        cv_rows = tuple(row for row in self.build.rows if row.scenario_family_id in set(group_order[:5]))
        cv = evaluate_forum_controlled_demo(cv_rows, self.build.manifest)
        self.assertEqual("grouped_cross_validation", cv.split_manifest["evaluationMode"])
        self.assertEqual("no_untouched_final_test", cv.report["applicableFinalTestStatus"])
        self.assertEqual(0, cv.report["untouchedTestEvaluationCount"])
        self.assertEqual("rejected", cv.report["controlledCandidateStatus"])
        self.assertEqual("blocked", cv.report["activationStatus"])
        self.assertIn("no_untouched_final_test", cv.report["failedGates"])
        self.assertIsNone(cv.candidate)

        insufficient_rows = tuple(row for row in self.build.rows if row.scenario_family_id in set(group_order[:3]))
        insufficient = evaluate_forum_controlled_demo(insufficient_rows, self.build.manifest)
        self.assertEqual("controlled_catalogue_insufficient", insufficient.report["evaluationStatus"])
        self.assertEqual("blocked", insufficient.report["activationStatus"])
        self.assertIsNone(insufficient.candidate)

    def test_grouped_cv_fold_failures_are_prefixed_and_reject_the_candidate(self):
        class DegenerateVectorizer:
            vocabulary_ = {"fictional": 0}
            ngram_range = (1, 2)
            min_df = 1
            sublinear_tf = True

        class DegeneratePipeline:
            named_steps = {"tfidf": DegenerateVectorizer()}

            def predict(self, texts):
                return [CONTROLLED_REVISION] * len(texts)

            def predict_proba(self, texts):
                return [[0.5, 0.5] for _ in texts]

        class DegenerateClassifier:
            model_version = "forum-controlled-demo-nb-v1"
            pipeline = DegeneratePipeline()

            def to_bytes(self):
                return b"degenerate-test-artifact"

        group_order = sorted({row.scenario_family_id for row in self.build.rows})
        cv_rows = tuple(
            row for row in self.build.rows
            if row.scenario_family_id in set(group_order[:5])
        )
        with patch(
            "training.evaluate_forum_classifier.train_controlled_demo_candidate",
            return_value=DegenerateClassifier(),
        ):
            evaluation = evaluate_forum_controlled_demo(cv_rows, self.build.manifest)

        self.assertEqual("grouped_cross_validation", evaluation.report["evaluationMode"])
        self.assertEqual("rejected", evaluation.report["controlledCandidateStatus"])
        self.assertEqual("blocked", evaluation.report["activationStatus"])
        failed = evaluation.report["failedGates"]
        for suffix in ("single_class_predictions", "zero_recall", "all_abstained"):
            with self.subTest(suffix=suffix):
                self.assertTrue(
                    any(code.startswith("fold_") and code.endswith(suffix) for code in failed),
                    failed,
                )
        self.assertIsNone(evaluation.candidate)

    def test_comparators_share_contract_and_baseline_never_becomes_candidate(self):
        comparators = self.evaluation.report["comparators"]
        relevance_comparators = self.evaluation.report["relevanceComparators"]
        self.assertEqual(
            {"MultinomialNB", "ComplementNB", "deterministic_answer_only_baseline"},
            set(comparators),
        )
        self.assertEqual(
            {"MultinomialNB", "ComplementNB", "deterministic_majority_baseline"},
            set(relevance_comparators),
        )
        contracts = {json.dumps(value["evidenceContract"], sort_keys=True) for value in comparators.values()}
        self.assertEqual(1, len(contracts))
        relevance_contracts = {
            json.dumps(value["evidenceContract"], sort_keys=True)
            for value in relevance_comparators.values()
        }
        self.assertEqual(1, len(relevance_contracts))
        self.assertGreater(comparators["deterministic_answer_only_baseline"]["fitRows"], 0)
        self.assertGreater(
            comparators["deterministic_answer_only_baseline"]["vectorizerVocabularySize"], 0,
        )
        self.assertGreater(
            relevance_comparators["deterministic_majority_baseline"]["fitRows"], 0,
        )
        self.assertIn(
            self.evaluation.report["baselineComparisonResult"],
            {"naive_bayes_advantage_demonstrated", "no_controlled_scenario_advantage_demonstrated"},
        )
        self.assertNotIn(
            "naive bayes superiority demonstrated",
            " ".join(self.evaluation.report["limitations"]).casefold(),
        )

    def test_baseline_win_records_no_advantage_without_promoting_the_baseline(self):
        baseline = {
            "metrics": {"macroF1": 1.0},
            "fitRows": 1,
            "heldOutRows": 1,
            "vectorizerVocabularySize": 1,
        }
        with patch(
            "training.evaluate_forum_classifier._baseline_score", return_value=baseline,
        ):
            evaluation = evaluate_forum_controlled_demo(self.build.rows, self.build.manifest)

        self.assertEqual(
            "no_controlled_scenario_advantage_demonstrated",
            evaluation.report["baselineComparisonResult"],
        )
        self.assertIn(evaluation.report["selectedNaiveBayesVariant"], {"MultinomialNB", "ComplementNB"})
        self.assertNotEqual("deterministic_answer_only_baseline", evaluation.report["selectedNaiveBayesVariant"])

    def test_evaluation_uses_the_runtime_normalization_contract(self):
        import training.evaluate_forum_classifier as evaluator
        from logic_oasis_ai.forum_ai.classifier import normalize_forum_text

        with patch.object(
            evaluator, "normalize_forum_text", wraps=normalize_forum_text,
        ) as normalize:
            evaluator.evaluate_forum_controlled_demo(self.build.rows, self.build.manifest)

        self.assertGreaterEqual(normalize.call_count, len(self.build.rows))

    def test_linked_question_families_stay_together_and_unsplittable_links_fail_closed(self):
        families = sorted({row.scenario_family_id for row in self.build.rows})
        first, bridge, third = families[:3]
        linked_rows = []
        for row in self.build.rows:
            question_family = row.question_family_id
            if row.scenario_family_id == first:
                question_family = "linked-a"
            elif row.scenario_family_id == bridge:
                question_family = "linked-a" if row.label == "explanation_sufficient" else "linked-b"
            elif row.scenario_family_id == third:
                question_family = "linked-b"
            linked_rows.append(replace(row, question_family_id=question_family))
        linked = evaluate_forum_controlled_demo(tuple(linked_rows), self.build.manifest)
        partitions = {
            family: name
            for name, key in (
                ("train", "trainScenarioFamilyIds"),
                ("validation", "validationScenarioFamilyIds"),
                ("test", "testScenarioFamilyIds"),
            )
            for family in linked.split_manifest[key]
        }
        self.assertEqual(1, len({partitions[family] for family in (first, bridge, third)}))

        collapsed = tuple(replace(row, question_family_id="one-component") for row in self.build.rows)
        insufficient = evaluate_forum_controlled_demo(collapsed, self.build.manifest)
        self.assertEqual("controlled_catalogue_insufficient", insufficient.report["evaluationStatus"])
        self.assertIsNone(insufficient.candidate)

    def test_manifest_hashes_and_counts_are_verified_before_candidate_eligibility(self):
        mutations = {
            "catalogueSha256": "0" * 64,
            "rubricSha256": "1" * 64,
            "rowCount": 999,
            "scenarioFamilyCount": 999,
            "classCounts": {},
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                manifest = dict(self.build.manifest)
                manifest[field] = value
                evaluation = evaluate_forum_controlled_demo(self.build.rows, manifest)
                self.assertEqual("rejected", evaluation.report["controlledCandidateStatus"])
                self.assertIn("binding_mismatch", evaluation.report["failedGates"])
                self.assertIsNone(evaluation.candidate)
                self.assertIsNone(evaluation.artifact_bytes)

    def test_every_non_degeneracy_gate_has_an_exact_failure_code(self):
        base = dict(
            training_labels=[0, 1], validation_labels=[0, 1], held_out_labels=[0, 1],
            predictions=[0, 1], confusion_matrix=[[1, 0], [0, 1]], vocabulary_size=2,
            preprocessing_valid=True, leakage_free=True, no_test_fit=True,
            published_count=1, held_out_count=2, artifact_reproduces=True, bindings_valid=True,
        )
        cases = {
            "training_missing_class": {"training_labels": [0, 0]},
            "validation_missing_class": {"validation_labels": [1, 1]},
            "held_out_missing_class": {"held_out_labels": [0, 0]},
            "single_class_predictions": {"predictions": [0, 0]},
            "zero_recall": {"confusion_matrix": [[1, 0], [1, 0]]},
            "invalid_confusion_matrix": {"confusion_matrix": [[1]]},
            "empty_vocabulary": {"vocabulary_size": 0},
            "preprocessing_failed": {"preprocessing_valid": False},
            "group_leakage": {"leakage_free": False},
            "test_rows_fitted": {"no_test_fit": False},
            "all_abstained": {"published_count": 0},
            "artifact_output_mismatch": {"artifact_reproduces": False},
            "binding_mismatch": {"bindings_valid": False},
        }
        for expected, override in cases.items():
            with self.subTest(gate=expected):
                self.assertIn(expected, candidate_gate_failures(**(base | override)))

        for expected in cases:
            with self.subTest(orchestration=expected), patch(
                "training.evaluate_forum_classifier.candidate_gate_failures",
                return_value=[expected],
            ):
                rejected = evaluate_forum_controlled_demo(self.build.rows, self.build.manifest)
                self.assertEqual("rejected", rejected.report["controlledCandidateStatus"])
                self.assertEqual("blocked", rejected.report["activationStatus"])
                self.assertEqual([expected], rejected.report["failedGates"])
                self.assertIsNone(rejected.candidate)
                self.assertIsNone(rejected.artifact_bytes)

    def test_artifact_round_trip_failure_has_truthful_semantic_status(self):
        with patch(
            "training.evaluate_forum_classifier._artifact_round_trip",
            return_value=False,
        ):
            rejected = evaluate_forum_controlled_demo(
                self.build.rows, self.build.manifest,
            )

        self.assertEqual("rejected", rejected.report["controlledCandidateStatus"])
        self.assertIn("artifact_output_mismatch", rejected.report["failedGates"])
        self.assertEqual(
            "failed_artifact_round_trip",
            rejected.report["semanticReproducibilityStatus"],
        )
        self.assertIsNone(rejected.candidate)
        self.assertIsNone(rejected.artifact_bytes)

    def test_report_claims_metrics_reproducibility_and_candidate_round_trip_are_complete(self):
        report = self.evaluation.report
        for key in (
            "accuracy", "macroF1", "perClass", "balancedAccuracy", "confusionMatrix",
            "abstentionCoverage", "publicationCoverage", "fallbackCoverage", "latencyMs",
            "serializedSizeBytes", "datasetCounts", "splitSeed", "preprocessingVersion",
            "rubricVersion", "rubricSha256", "catalogueVersion", "catalogueSha256", "datasetSha256",
            "candidateSelectionDecision", "selectedNaiveBayesVariant", "baselineComparisonResult",
            "relevanceCandidateSelectionDecision", "selectedRelevanceNaiveBayesVariant",
            "relevanceBaselineComparisonResult", "relevanceComponent", "composite",
            "compositePolicy", "relevanceArtifactByteHash", "relevanceSerializedSizeBytes",
            "controlledDemoActivationDecision", "controlledCandidateStatus", "activationStatus",
            "claimLevel", "calibrationStatus", "semanticReproducibilityStatus",
            "runtimeEnvironmentFingerprint", "failedGates", "limitations",
        ):
            self.assertIn(key, report)
        self.assertEqual("controlled_demonstration_only", report["claimLevel"])
        self.assertEqual("expert_authored_controlled_demo", report["trainingDataProvenance"])
        self.assertEqual("controlled_demonstration", report["evidenceLevel"])
        self.assertEqual("fyp1_forum_controlled_demo", report["releaseScope"])
        self.assertEqual("controlled_demo", report["deploymentScope"])
        self.assertEqual("not_established_on_real_learners", report["calibrationStatus"])
        self.assertIn(LIMITATION_STATEMENT, report["limitations"])

        with TemporaryDirectory() as directory:
            paths = write_forum_evaluation(self.build, directory, operator_role="developer")
            restored = ForumTextClassifier.load(paths["candidate"])
            self.assertTrue(paths["relevance_candidate"].exists())
            from logic_oasis_ai.forum_ai.relevance import ForumRelevanceClassifier
            restored_relevance = ForumRelevanceClassifier.load(
                paths["relevance_candidate"],
            )
            sample_row = self.build.rows[0]
            self.assertEqual(
                self.evaluation.relevance_candidate.predict(
                    sample_row.prompt, sample_row.text,
                ),
                restored_relevance.predict(sample_row.prompt, sample_row.text),
            )
            sample = "First I regrouped the tens, then I checked the total."
            self.assertEqual(
                self.evaluation.candidate.predict(sample),
                restored.predict(sample),
            )
            execution = json.loads(paths["execution_record"].read_text(encoding="utf-8"))
            self.assertNotIn("hostname", execution)
            self.assertNotIn("environmentVariables", execution)
            self.assertEqual("developer", execution["operatorRole"])

            candidate_manifest = json.loads(
                paths["candidate_manifest"].read_text(encoding="utf-8")
            )
            self.assertEqual(
                {
                    "datasetVersion": "forum-controlled-demo-dataset-v1",
                    "catalogVersion": "forum-verification-catalog-v1",
                    "splitSchemaVersion": "forum-controlled-demo-grouped-split-v1",
                    "reportSchemaVersion": "forum-controlled-demo-report-v2",
                    "catalogueFile": "ai_pipeline/forum_controlled_demo/forum_verification_catalog_v1.yaml",
                    "datasetFile": "forum_controlled_demo_v1.jsonl",
                    "datasetManifestFile": "forum_controlled_demo_v1_manifest.json",
                    "splitManifestFile": "forum_controlled_demo_split_manifest.json",
                    "evaluationReportFile": "forum_controlled_demo_report.json",
                    "artifactFile": "forum_controlled_demo_candidate.joblib",
                    "relevanceArtifactFile": "forum_controlled_demo_relevance_candidate.joblib",
                },
                {
                    key: candidate_manifest[key]
                    for key in (
                        "datasetVersion", "catalogVersion", "splitSchemaVersion",
                        "reportSchemaVersion", "catalogueFile", "datasetFile",
                        "datasetManifestFile", "splitManifestFile",
                        "evaluationReportFile", "artifactFile", "relevanceArtifactFile",
                    )
                },
            )

    def test_writer_rejects_rows_that_do_not_rebuild_from_the_catalogue(self):
        forged_rows = list(self.build.rows)
        forged_rows[0] = replace(
            forged_rows[0],
            text="I replaced this fictional row after catalogue approval.",
        )
        forged_jsonl = forum_dataset_jsonl_bytes(forged_rows)
        forged_manifest = dict(
            self.build.manifest,
            datasetSha256=sha256(forged_jsonl).hexdigest(),
        )
        forged = replace(
            self.build,
            rows=tuple(forged_rows),
            manifest=forged_manifest,
            canonical_jsonl=forged_jsonl,
        )

        with TemporaryDirectory() as directory, self.assertRaisesRegex(
            ValueError, "authoritative catalogue",
        ):
            write_forum_evaluation(forged, directory, operator_role="developer")

    def test_custom_catalogue_records_portable_source_and_effective_arguments(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            custom_catalogue = root / "custom-catalogue.yaml"
            custom_catalogue.write_bytes(DEFAULT_CATALOGUE_PATH.read_bytes())
            build = build_forum_dataset(custom_catalogue)
            generated, reports = root / "generated", root / "reports"
            paths = write_forum_evaluation(
                build,
                generated,
                report_directory=reports,
                operator_role="reviewer",
            )
            candidate_manifest = json.loads(
                paths["candidate_manifest"].read_text(encoding="utf-8")
            )
            execution = json.loads(paths["execution_record"].read_text(encoding="utf-8"))

            self.assertEqual("custom-catalogue.yaml", build.catalogue_source)
            self.assertEqual("custom-catalogue.yaml", candidate_manifest["catalogueFile"])
            self.assertEqual(
                [
                    "--catalogue", "custom-catalogue.yaml",
                    "--generated", "generated",
                    "--reports", "reports",
                    "--operator-role", "reviewer",
                ],
                execution["commandArguments"],
            )
            self.assertNotIn(str(root), json.dumps(execution))

    def test_committed_canonical_outputs_match_a_fresh_generation(self):
        repository = Path(__file__).resolve().parents[2]
        committed_generated = repository / "ai_pipeline" / "forum_controlled_demo" / "generated"
        committed_reports = repository / "ai_pipeline" / "reports"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = write_forum_evaluation(
                self.build,
                root / "generated",
                report_directory=root / "reports",
                operator_role="developer",
            )
            deterministic = {
                "dataset": committed_generated / "forum_controlled_demo_v1.jsonl",
                "manifest": committed_generated / "forum_controlled_demo_v1_manifest.json",
                "split_manifest": committed_generated / "forum_controlled_demo_split_manifest.json",
                "report_markdown": committed_reports / "forum_controlled_demo_report.md",
            }
            for key, committed_path in deterministic.items():
                with self.subTest(key=key):
                    self.assertEqual(committed_path.read_bytes(), paths[key].read_bytes())

            committed_candidate_path = committed_generated / "forum_controlled_demo_candidate.joblib"
            committed_candidate = joblib.load(committed_candidate_path)
            fresh_candidate = joblib.load(paths["candidate"])
            committed_relevance_candidate = joblib.load(
                committed_generated / "forum_controlled_demo_relevance_candidate.joblib"
            )
            fresh_relevance_candidate = joblib.load(
                paths["relevance_candidate"]
            )
            self.assertEqual(committed_candidate["modelVersion"], fresh_candidate["modelVersion"])
            self.assertEqual(
                committed_relevance_candidate["modelVersion"],
                fresh_relevance_candidate["modelVersion"],
            )
            committed_classifier = ForumTextClassifier(
                committed_candidate["pipeline"], model_version=committed_candidate["modelVersion"],
            )
            fresh_classifier = ForumTextClassifier(
                fresh_candidate["pipeline"], model_version=fresh_candidate["modelVersion"],
            )
            from logic_oasis_ai.forum_ai.relevance import ForumRelevanceClassifier
            committed_relevance = ForumRelevanceClassifier(
                committed_relevance_candidate["pipeline"],
                model_version=committed_relevance_candidate["modelVersion"],
            )
            fresh_relevance = ForumRelevanceClassifier(
                fresh_relevance_candidate["pipeline"],
                model_version=fresh_relevance_candidate["modelVersion"],
            )
            for row in self.build.rows:
                self.assertEqual(
                    committed_classifier.predict(row.text),
                    fresh_classifier.predict(row.text),
                )
                self.assertEqual(
                    committed_relevance.predict(row.prompt, row.text),
                    fresh_relevance.predict(row.prompt, row.text),
                )

            committed_report = json.loads(
                (committed_reports / "forum_controlled_demo_report.json").read_text(encoding="utf-8")
            )
            fresh_report = json.loads(paths["report_json"].read_text(encoding="utf-8"))
            self.assertEqual(
                sha256(committed_candidate_path.read_bytes()).hexdigest(),
                committed_report["artifactByteHash"],
            )
            self.assertEqual(
                sha256(paths["candidate"].read_bytes()).hexdigest(),
                fresh_report["artifactByteHash"],
            )
            committed_report.pop("artifactByteHash")
            fresh_report.pop("artifactByteHash")
            committed_report.pop("relevanceArtifactByteHash")
            fresh_report.pop("relevanceArtifactByteHash")
            self.assertEqual(committed_report, fresh_report)

            committed_manifest = json.loads(
                (committed_generated / "forum_controlled_demo_candidate_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            fresh_manifest = json.loads(paths["candidate_manifest"].read_text(encoding="utf-8"))
            for manifest, report_path in (
                (committed_manifest, committed_reports / "forum_controlled_demo_report.json"),
                (fresh_manifest, paths["report_json"]),
            ):
                self.assertEqual(
                    manifest["evaluationReportSha256"],
                    sha256(report_path.read_bytes()).hexdigest(),
                )
                manifest.pop("artifactSha256")
                manifest.pop("relevanceArtifactSha256")
                manifest.pop("evaluationReportSha256")
            self.assertEqual(committed_manifest, fresh_manifest)

    def test_rejected_rerun_removes_stale_candidate_files_and_unsafe_operator_roles_fail(self):
        with TemporaryDirectory() as directory:
            paths = write_forum_evaluation(self.build, directory, operator_role="developer")
            self.assertTrue(paths["candidate"].exists())
            groups = sorted({row.scenario_family_id for row in self.build.rows})
            insufficient_rows = tuple(
                row for row in self.build.rows if row.scenario_family_id in set(groups[:3])
            )
            rejected = evaluate_forum_controlled_demo(insufficient_rows, self.build.manifest)
            with patch(
                "training.evaluate_forum_classifier.evaluate_forum_controlled_demo",
                return_value=rejected,
            ):
                write_forum_evaluation(self.build, directory, operator_role="developer")
            self.assertFalse(paths["candidate"].exists())
            self.assertFalse(paths["candidate_manifest"].exists())

            for role in (
                "", "name@example.test", "../operator", "role:developer",
                "Alice Example", "developer-admin", "prod",
            ):
                with self.subTest(role=role), self.assertRaisesRegex(ValueError, "operator role"):
                    write_forum_evaluation(self.build, directory, operator_role=role)

            for role in ("developer", "reviewer", "release-operator"):
                with self.subTest(allowed_role=role):
                    allowed = write_forum_evaluation(
                        self.build, directory, operator_role=role,
                    )
                    execution = json.loads(
                        allowed["execution_record"].read_text(encoding="utf-8")
                    )
                    self.assertEqual(role, execution["operatorRole"])

    def test_canonical_artifacts_repeat_while_execution_metadata_stays_out_of_hashes(self):
        with TemporaryDirectory() as first, TemporaryDirectory() as second:
            first_paths = write_forum_evaluation(self.build, first, operator_role="developer")
            second_paths = write_forum_evaluation(self.build, second, operator_role="reviewer")
            for key in (
                "dataset", "manifest", "split_manifest", "candidate", "relevance_candidate",
                "candidate_manifest", "report_json", "report_markdown",
            ):
                with self.subTest(key=key):
                    self.assertEqual(first_paths[key].read_bytes(), second_paths[key].read_bytes())
            self.assertNotEqual(
                first_paths["execution_record"].read_bytes(),
                second_paths["execution_record"].read_bytes(),
            )

    def test_publication_failure_rolls_back_every_previous_output(self):
        with TemporaryDirectory() as directory:
            paths = write_forum_evaluation(self.build, directory, operator_role="developer")
            before = {key: path.read_bytes() for key, path in paths.items()}
            original_replace = os.replace
            replace_calls = 0

            def fail_during_publish(source, destination):
                nonlocal replace_calls
                replace_calls += 1
                if replace_calls == 6:
                    raise OSError("injected publication failure")
                return original_replace(source, destination)

            with patch(
                "forum_controlled_demo.build_forum_dataset.os.replace",
                side_effect=fail_during_publish,
            ):
                with self.assertRaisesRegex(OSError, "injected publication failure"):
                    write_forum_evaluation(self.build, directory, operator_role="developer")

            self.assertEqual(before, {key: path.read_bytes() for key, path in paths.items()})
            self.assertEqual([], list(Path(directory).glob(".forum-publication-*")))

    def test_candidate_manifest_is_the_last_publication_replace(self):
        with TemporaryDirectory() as directory:
            original_replace = os.replace
            destinations = []

            def record_replace(source, destination):
                destinations.append(Path(destination).name)
                return original_replace(source, destination)

            with patch(
                "forum_controlled_demo.build_forum_dataset.os.replace",
                side_effect=record_replace,
            ):
                write_forum_evaluation(self.build, directory, operator_role="developer")

            self.assertEqual("forum_controlled_demo_candidate_manifest.json", destinations[-1])

    def test_future_real_data_evaluator_rejects_controlled_provenance(self):
        with self.assertRaisesRegex(ValueError, "real-data evaluator"):
            reject_controlled_provenance_for_real_evaluation(self.build.rows)


if __name__ == "__main__":
    unittest.main()
