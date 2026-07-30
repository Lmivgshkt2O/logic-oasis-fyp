from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "functions"))

from forum_runtime import feedback_for, malaysia_week_start
from logic_oasis_ai.forum_ai.classifier import REVISION, SUFFICIENT, UNCERTAIN


class ForumRuntimeTests(unittest.TestCase):
    def test_supportive_feedback_is_advisory_and_has_an_uncertain_path(self):
        self.assertIn("method", feedback_for(SUFFICIENT))
        self.assertIn("steps", feedback_for(REVISION))
        self.assertIn("saved", feedback_for(UNCERTAIN))

    def test_event_week_is_stable_when_processing_happens_later(self):
        event_time = datetime(2026, 7, 26, 17, tzinfo=timezone.utc)
        self.assertEqual("2026-07-27", malaysia_week_start(event_time).date().isoformat())


if __name__ == "__main__":
    unittest.main()
