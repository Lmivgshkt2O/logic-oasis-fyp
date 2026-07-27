from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "functions"))

import main
from ai_runtime import AI_RUNTIME_SERVICE_ACCOUNT


class QuizTriggerContractTests(unittest.TestCase):
    def test_finalized_attempt_trigger_uses_the_named_runtime_identity(self) -> None:
        endpoint = getattr(main.processFinalizedQuizAttempt, "__firebase_endpoint__")
        self.assertEqual("google.cloud.firestore.document.v1.created", endpoint.eventTrigger["eventType"])
        self.assertEqual("quizAttempts/{attemptId}", endpoint.eventTrigger["eventFilterPathPatterns"]["document"])
        self.assertTrue(endpoint.eventTrigger["retry"])
        self.assertEqual(AI_RUNTIME_SERVICE_ACCOUNT, endpoint.serviceAccountEmail)

    def test_runtime_string_parameters_resolve_with_installed_sdk(self) -> None:
        self.assertEqual(
            main.AI_MODEL_EVIDENCE_MODE.value,
            main._resolved_string_param(main.AI_MODEL_EVIDENCE_MODE),
        )
        self.assertEqual(
            main.AI_MODEL_BUCKET.value,
            main._resolved_string_param(main.AI_MODEL_BUCKET),
        )

    def test_runtime_string_parameters_accept_legacy_callable_value(self) -> None:
        legacy_parameter = type("LegacyParameter", (), {"value": lambda self: "controlled_demo"})()
        self.assertEqual("controlled_demo", main._resolved_string_param(legacy_parameter))


if __name__ == "__main__":
    unittest.main()
