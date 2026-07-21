from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import parent_link_email_delivery as delivery


class ParentLinkEmailDeliveryTests(unittest.TestCase):
    environment = {
        "PARENT_INVITATION_CONTINUE_URL": "https://logic-oasis-fyp.web.app/parent-invitation",
        "PARENT_INVITATION_ANDROID_PACKAGE": "com.example.logic_oasis",
        "PARENT_INVITATION_SMTP_HOST": "smtp.example.test",
        "PARENT_INVITATION_SMTP_PORT": "465",
        "PARENT_INVITATION_SMTP_USERNAME": "sender@example.test",
        "PARENT_INVITATION_SMTP_PASSWORD": "smtp-secret",
        "PARENT_INVITATION_SMTP_FROM": "sender@example.test",
    }

    def test_link_generation_failure_logs_only_the_error_category(self) -> None:
        with patch.dict(os.environ, self.environment, clear=False), patch.object(
            delivery.auth,
            "generate_sign_in_with_email_link",
            side_effect=RuntimeError("recipient@example.test must not appear in logs"),
        ), patch.object(delivery._LOGGER, "error") as log_error:
            with self.assertRaisesRegex(delivery.ParentInvitationDeliveryError, "Unable to prepare"):
                delivery.deliver_parent_invitation("recipient@example.test", "invite-id", "verifier")

        log_error.assert_called_once_with(
            "parent_invitation_link_generation_failed error_type=%s", "RuntimeError"
        )


if __name__ == "__main__":
    unittest.main()
