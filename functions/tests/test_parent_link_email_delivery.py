from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

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

    def test_emulator_action_uses_verified_mobile_link_envelope(self) -> None:
        action_link = (
            "http://127.0.0.1:9099/emulator/action?mode=signIn&"
            "oobCode=test-code&continueUrl=https%3A%2F%2Flogic-oasis-fyp.web.app%2Fparent-invitation"
        )
        environment = {**self.environment, "FUNCTIONS_EMULATOR": "true"}

        with patch.dict(os.environ, environment, clear=False), patch.object(
            delivery.auth,
            "generate_sign_in_with_email_link",
            return_value=action_link,
        ), patch.object(delivery.smtplib, "SMTP_SSL") as smtp_ssl:
            delivery.deliver_parent_invitation(
                "recipient@example.test", "invite-id", "verifier"
            )

        smtp = smtp_ssl.return_value.__enter__.return_value
        message = smtp.send_message.call_args.args[0]
        mobile_link = message.get_content().split(
            "Open this secure link to review and accept the invitation: ", 1
        )[1].strip()

        parsed = urlparse(mobile_link)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "logic-oasis-fyp.firebaseapp.com")
        self.assertEqual(parsed.path, "/__/auth/links")
        self.assertEqual(parse_qs(parsed.query)["link"], [action_link])

    def test_production_action_link_is_not_rewritten(self) -> None:
        action_link = "https://logic-oasis-fyp.firebaseapp.com/__/auth/links?link=production"

        with patch.dict(os.environ, {"FUNCTIONS_EMULATOR": "false"}, clear=False):
            self.assertEqual(delivery.mobile_email_link(action_link), action_link)


if __name__ == "__main__":
    unittest.main()
