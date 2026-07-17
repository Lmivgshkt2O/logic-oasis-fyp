from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class WeakTopicRankingPolicyTests(unittest.TestCase):
    def test_ranking_policy_is_versioned_and_separates_severity_from_evidence(self) -> None:
        policy = yaml.safe_load((ROOT / "configs" / "weak_topic_ranking_v1.yaml").read_text(encoding="utf-8"))
        self.assertEqual("weak-topic-ranking-v1", policy["policyVersion"])
        self.assertEqual("severity_times_evidence_reliability", policy["formula"])
        self.assertEqual(6, policy["minimumEvidenceForHighConfidence"])


if __name__ == "__main__":
    unittest.main()
