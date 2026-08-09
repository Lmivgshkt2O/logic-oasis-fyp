from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai_pipeline"))

from training.publish_forum_controlled_demo import (
    main as publish_forum_main,
    publish_forum_controlled_demo,
)


NOW = datetime(2026, 8, 9, 8, 0, tzinfo=timezone.utc)


class ForumModelPromotionTests(unittest.TestCase):
    def test_publisher_cli_carries_the_superseded_release_id(self):
        arguments = [
            "publish_forum_controlled_demo",
            "--repository-root", str(ROOT),
            "--functions-root", str(ROOT / "functions"),
            "--release-id", "forum-release-2",
            "--released-by", "developer",
            "--released-at", "2026-08-09T00:00:00Z",
            "--supersedes-release-id", "forum-release-1",
        ]
        with patch.object(sys, "argv", arguments), patch(
            "training.publish_forum_controlled_demo.publish_forum_controlled_demo",
        ) as publisher:
            publish_forum_main()
        self.assertEqual(
            "forum-release-1",
            publisher.call_args.kwargs["supersedes_release_id"],
        )

    def test_publisher_releases_only_eligible_naive_bayes_with_complete_bindings(self):
        with TemporaryDirectory() as directory:
            result = publish_forum_controlled_demo(
                repository_root=ROOT,
                functions_root=Path(directory) / "functions",
                released_by="developer",
                released_at=NOW,
                release_id="forum-controlled-demo-nb-v1-release-1",
            )
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual("MultinomialNB", manifest["modelType"])
            self.assertEqual("released", manifest["lifecycleStatus"])
            self.assertTrue(manifest["isActive"])
            self.assertEqual("controlled_demonstration_only", manifest["claimLevel"])
            self.assertEqual("pending_cloud_deployment", manifest["deploymentState"])
            for key in (
                "catalogueSha256", "datasetSha256", "datasetManifestSha256",
                "splitManifestSha256", "rubricSha256", "evaluationReportSha256",
                "candidateManifestSha256", "artifactSha256", "bundleManifestSha256",
                "codeRevision", "dependencies", "sourceRuntimeHashes", "vendorRuntimeHashes",
            ):
                self.assertIn(key, manifest)
            self.assertEqual(manifest["sourceRuntimeHashes"], manifest["vendorRuntimeHashes"])

    def test_rejected_candidate_and_baseline_have_no_publish_path(self):
        with TemporaryDirectory() as directory:
            manifest = ROOT / "ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_candidate_manifest.json"
            altered = json.loads(manifest.read_text(encoding="utf-8"))
            altered["controlledCandidateStatus"] = "rejected"
            bad = Path(directory) / "candidate.json"
            bad.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "eligible"):
                publish_forum_controlled_demo(
                    repository_root=ROOT, functions_root=Path(directory) / "functions",
                    candidate_manifest_path=bad, released_by="developer", released_at=NOW,
                    release_id="bad-release",
                )
            altered["controlledCandidateStatus"] = "eligible"
            altered["modelType"] = "deterministic_answer_only_baseline"
            bad.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Naive Bayes"):
                publish_forum_controlled_demo(
                    repository_root=ROOT, functions_root=Path(directory) / "functions",
                    candidate_manifest_path=bad, released_by="developer", released_at=NOW,
                    release_id="bad-release",
                )

    def test_publisher_rejects_candidate_whose_u4_bindings_do_not_match(self):
        source = ROOT / "ai_pipeline/forum_controlled_demo/generated/forum_controlled_demo_candidate_manifest.json"
        with TemporaryDirectory() as directory:
            altered = json.loads(source.read_text(encoding="utf-8"))
            altered["datasetSha256"] = "0" * 64
            candidate = Path(directory) / "candidate.json"
            candidate.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "dataset, catalogue, or rubric binding"):
                publish_forum_controlled_demo(
                    repository_root=ROOT,
                    functions_root=Path(directory) / "functions",
                    candidate_manifest_path=candidate,
                    released_by="developer",
                    released_at=NOW,
                    release_id="mismatched-release",
                )
if __name__ == "__main__":
    unittest.main()
