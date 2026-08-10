from pathlib import Path
import sys
import tempfile
import unittest
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from logic_oasis_ai.forum_ai.classifier import (
    CONTROLLED_REVISION,
    CONTROLLED_SUFFICIENT,
    REVISION,
    SUFFICIENT,
    VECTORIZER_CONTRACT,
    ForumTextClassifier,
    build_forum_vectorizer,
    train_classifier,
)
from logic_oasis_ai.forum_ai.dataset import load_labelled_examples


class NaiveBayesForumTests(unittest.TestCase):
    def setUp(self):
        self.classifier = train_classifier([
            ("I added 24 and 16, then checked 40 with a number line.", SUFFICIENT),
            ("First split the fraction into halves and compare the shaded parts.", SUFFICIENT),
            ("The answer is 40.", REVISION),
            ("It is one half.", REVISION),
        ])

    def test_known_explanatory_and_answer_only_text_get_a_label_and_probability(self):
        for text in ("I added the tens first, then checked my total.", "The answer is 40."):
            prediction = self.classifier.predict(text)
            self.assertIsInstance(prediction.label, str)
            self.assertGreaterEqual(prediction.probability, 0.0)
            self.assertLessEqual(prediction.probability, 1.0)
            self.assertEqual("not_calibrated", prediction.calibration_state)

    def test_saved_vectorizer_and_classifier_keep_identical_preprocessing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "forum.joblib"
            self.classifier.save(path)
            restored = ForumTextClassifier.load(path)
            self.assertEqual(
                self.classifier.predict("I split it into equal groups and checked."),
                restored.predict("I split it into equal groups and checked."),
            )

    def test_vectorizer_is_constructed_from_the_declared_contract(self):
        vectorizer = build_forum_vectorizer()
        self.assertEqual(tuple(VECTORIZER_CONTRACT["ngramRange"]), vectorizer.ngram_range)
        self.assertEqual(VECTORIZER_CONTRACT["minimumDocumentFrequency"], vectorizer.min_df)
        self.assertEqual(VECTORIZER_CONTRACT["sublinearTf"], vectorizer.sublinear_tf)

    def test_both_controlled_demo_variants_preserve_runtime_output_labels(self):
        rows = [
            ("First I regroup, then I check the total.", CONTROLLED_SUFFICIENT),
            ("I divide into equal groups because each share is equal.", CONTROLLED_SUFFICIENT),
            ("The answer is 12.", CONTROLLED_REVISION),
            ("Jawapannya 24 sahaja.", CONTROLLED_REVISION),
        ]
        for variant in ("MultinomialNB", "ComplementNB"):
            with self.subTest(variant=variant):
                classifier = train_classifier(rows, variant=variant)
                self.assertIn(
                    classifier.predict("First I regroup, then I check the total.").label,
                    {SUFFICIENT, REVISION, "uncertain"},
                )

    def test_controlled_labels_map_exactly_to_runtime_advisory_labels(self):
        class DeterministicPipeline:
            classes_ = [CONTROLLED_REVISION, CONTROLLED_SUFFICIENT]

            def __init__(self, probabilities):
                self.probabilities = probabilities

            def predict_proba(self, _texts):
                return [self.probabilities]

        cases = (
            ([0.1, 0.9], SUFFICIENT),
            ([0.9, 0.1], REVISION),
            ([0.45, 0.55], "uncertain"),
        )
        for probabilities, expected in cases:
            with self.subTest(probabilities=probabilities):
                classifier = ForumTextClassifier(
                    DeterministicPipeline(probabilities),
                )
                self.assertEqual(expected, classifier.predict("Test explanation").label)

    def test_emulator_fixture_is_deidentified_and_explicitly_test_only(self):
        examples = load_labelled_examples(
            ROOT / "logic_oasis_ai" / "forum_ai" / "data" / "emulator_reviewed_examples.jsonl"
        )
        self.assertEqual({"synthetic_test"}, {example.provenance for example in examples})
        self.assertTrue(all(example.author_group.startswith("fixture-") for example in examples))

    def test_dataset_rejects_unknown_fields_that_could_carry_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "labels.jsonl"
            path.write_text(
                '{"text":"The answer is twelve.","label":"needs_reasoning","provenance":"synthetic_test","reviewer":"r","authorGroup":"a","phone":"123"}\n' * 4,
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unsupported field"):
                load_labelled_examples(path)


if __name__ == "__main__":
    unittest.main()
