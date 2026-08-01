from pathlib import Path
import sys
import tempfile
import unittest
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from logic_oasis_ai.forum_ai.classifier import (
    REVISION, SUFFICIENT, ForumTextClassifier, train_classifier,
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
