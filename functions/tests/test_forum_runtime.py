from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "functions"))

from forum_runtime import _transaction_snapshot, feedback_for, load_forum_classifier, malaysia_week_start
from logic_oasis_ai.forum_ai.classifier import REVISION, SUFFICIENT, UNCERTAIN


class ForumRuntimeTests(unittest.TestCase):
    def test_supportive_feedback_is_advisory_and_has_an_uncertain_path(self):
        self.assertIn("method", feedback_for(SUFFICIENT))
        self.assertIn("steps", feedback_for(REVISION))
        self.assertIn("saved", feedback_for(UNCERTAIN))

    def test_event_week_is_stable_when_processing_happens_later(self):
        event_time = datetime(2026, 7, 26, 17, tzinfo=timezone.utc)
        self.assertEqual("2026-07-27", malaysia_week_start(event_time).date().isoformat())

    def test_transaction_read_accepts_the_current_sdk_iterator_shape(self):
        snapshot = type("Snapshot", (), {"exists": True})()
        transaction = type("Transaction", (), {"get": lambda self, _: iter([snapshot])})()
        self.assertIs(snapshot, _transaction_snapshot(transaction, object()))

    def test_model_loader_rejects_an_artifact_that_does_not_match_its_manifest(self):
        from logic_oasis_ai.forum_ai.classifier import REVISION, SUFFICIENT, train_classifier
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "model.joblib"
            manifest = Path(directory) / "manifest.json"
            train_classifier([
                ("I used a number line to check.", SUFFICIENT),
                ("I added groups and checked.", SUFFICIENT),
                ("The answer is twelve.", REVISION),
                ("It is twelve.", REVISION),
            ]).save(artifact)
            manifest.write_text(json.dumps({"artifactSha256": "wrong", "modelVersion": "forum-explanation-nb-v1"}))
            self.assertIsNone(load_forum_classifier(artifact, manifest))

    def test_fixture_artifact_is_emulator_only(self):
        from logic_oasis_ai.forum_ai.classifier import REVISION, SUFFICIENT, train_classifier
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "model.joblib"
            manifest = Path(directory) / "manifest.json"
            classifier = train_classifier([
                ("I used a number line to check.", SUFFICIENT),
                ("I added groups and checked.", SUFFICIENT),
                ("The answer is twelve.", REVISION),
                ("It is twelve.", REVISION),
            ])
            classifier.save(artifact)
            manifest.write_text(json.dumps({"artifactSha256": sha256(artifact.read_bytes()).hexdigest(), "modelVersion": classifier.model_version, "evidenceState": "emulator_fixture_only"}))
            previous = os.environ.pop("FUNCTIONS_EMULATOR", None)
            try:
                self.assertIsNone(load_forum_classifier(artifact, manifest))
                os.environ["FUNCTIONS_EMULATOR"] = "true"
                self.assertIsNotNone(load_forum_classifier(artifact, manifest))
            finally:
                if previous is not None:
                    os.environ["FUNCTIONS_EMULATOR"] = previous
                else:
                    os.environ.pop("FUNCTIONS_EMULATOR", None)


if __name__ == "__main__":
    unittest.main()
