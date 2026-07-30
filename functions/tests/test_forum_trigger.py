from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "functions"))

import main
from forum_runtime import FORUM_RUNTIME_SERVICE_ACCOUNT, malaysia_week_start


class ForumTriggerContractTests(unittest.TestCase):
    def test_forum_triggers_bind_the_dedicated_least_privilege_runtime(self):
        for endpoint, pattern in (
            (main.processForumQuestion, "forumQuestions/{questionId}"),
            (main.processForumAnswer, "forumAnswers/{answerId}"),
        ):
            manifest = endpoint.__firebase_endpoint__
            self.assertEqual(FORUM_RUNTIME_SERVICE_ACCOUNT, manifest.serviceAccountEmail)
            self.assertEqual(pattern, manifest.eventTrigger["eventFilterPathPatterns"]["document"])
            self.assertTrue(manifest.eventTrigger["retry"])

    def test_week_start_uses_malaysia_local_monday_not_processing_time(self):
        # Sunday 17:00 UTC is Monday midnight in Kuala Lumpur.
        event_time = datetime(2026, 8, 2, 17, tzinfo=timezone.utc)
        self.assertEqual("2026-08-03", malaysia_week_start(event_time).date().isoformat())


if __name__ == "__main__":
    unittest.main()
