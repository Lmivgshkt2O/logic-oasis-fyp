from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "functions"))

import main
from forum_runtime import FORUM_RUNTIME_SERVICE_ACCOUNT, malaysia_week_start


class ForumTriggerContractTests(unittest.TestCase):
    def test_production_registry_reader_filters_the_existing_shared_registry(self):
        database = Mock()
        query = database.collection.return_value.where.return_value
        quiz = Mock()
        quiz.to_dict.return_value = {"releaseScope": "fyp1_controlled_demo", "isActive": True}
        forum = Mock()
        forum.to_dict.return_value = {
            "releaseScope": "fyp1_forum_controlled_demo",
            "releaseId": "forum-release-1",
            "isActive": True,
        }
        query.stream.return_value = [quiz, forum]
        with patch.object(main, "firestore_db", return_value=database):
            self.assertEqual(
                [{"releaseScope": "fyp1_forum_controlled_demo", "releaseId": "forum-release-1", "isActive": True}],
                main._active_forum_registry_documents(),
            )
        database.collection.assert_called_once_with("modelRegistry")
        database.collection.return_value.where.assert_called_once_with("isActive", "==", True)

    def test_forum_triggers_bind_the_dedicated_least_privilege_runtime(self):
        for endpoint, pattern in (
            (main.processForumQuestion, "forumQuestions/{questionId}"),
            (main.processForumAnswer, "forumAnswers/{answerId}"),
            (main.reprocessForumAnswer, "forumAnswers/{answerId}"),
        ):
            manifest = endpoint.__firebase_endpoint__
            self.assertEqual(FORUM_RUNTIME_SERVICE_ACCOUNT, manifest.serviceAccountEmail)
            self.assertEqual(pattern, manifest.eventTrigger["eventFilterPathPatterns"]["document"])
            self.assertTrue(manifest.eventTrigger["retry"])

    def test_warm_instance_caches_only_the_verified_bundle_result(self):
        sentinel = object()
        releases = [{"releaseId": "release-1"}]
        main._cached_verified_forum_bundle.cache_clear()
        with patch("main._active_forum_registry_documents", return_value=releases), patch(
            "main.load_forum_bundle", return_value=sentinel,
        ) as loader:
            self.assertIs(sentinel, main._forum_bundle())
            self.assertIs(sentinel, main._forum_bundle())
        loader.assert_called_once_with(
            evidence_mode="real_evaluated_only", code_revision="",
            registry_documents=releases,
        )
        main._cached_verified_forum_bundle.cache_clear()

    def test_failed_verification_is_not_retained_in_the_warm_cache(self):
        sentinel = object()
        releases = [{"releaseId": "release-1"}]
        main._cached_verified_forum_bundle.cache_clear()
        with patch("main._active_forum_registry_documents", return_value=releases), patch(
            "main.load_forum_bundle", side_effect=[None, sentinel],
        ) as loader:
            self.assertIsNone(main._forum_bundle())
            self.assertIs(sentinel, main._forum_bundle())
        self.assertEqual(2, loader.call_count)
        main._cached_verified_forum_bundle.cache_clear()

    def test_warm_instance_rechecks_registry_revocation_before_using_cache(self):
        sentinel = object()
        active = [{"releaseId": "release-1", "isActive": True}]
        main._cached_verified_forum_bundle.cache_clear()
        with patch(
            "main._active_forum_registry_documents", side_effect=[active, []],
        ), patch("main.load_forum_bundle", side_effect=[sentinel, None]) as loader:
            self.assertIs(sentinel, main._forum_bundle())
            self.assertIsNone(main._forum_bundle())
        self.assertEqual(2, loader.call_count)
        main._cached_verified_forum_bundle.cache_clear()

    def test_answer_update_reprocesses_only_a_new_content_revision(self):
        before = {"text": "Old explanation", "revision": 1}
        after = {"text": "New explanation", "revision": 2}
        unchanged = dict(after, aiFeedback={"state": "pending"})

        self.assertTrue(main._forum_answer_needs_reprocessing(before, after))
        self.assertFalse(main._forum_answer_needs_reprocessing(after, unchanged))

    def test_week_start_uses_malaysia_local_monday_not_processing_time(self):
        # Sunday 17:00 UTC is Monday midnight in Kuala Lumpur.
        event_time = datetime(2026, 8, 2, 17, tzinfo=timezone.utc)
        self.assertEqual("2026-08-03", malaysia_week_start(event_time).date().isoformat())


if __name__ == "__main__":
    unittest.main()
