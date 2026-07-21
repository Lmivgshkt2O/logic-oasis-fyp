"""Minimal server-only delivery adapter for parent invitation email links.

The provider credentials are read only from deployment environment/secret
bindings. This module deliberately has no Firebase client fallback: allowing a
student device to send the action link would bypass the callable's limits and
audit boundary.
"""

from __future__ import annotations

from email.message import EmailMessage
import logging
import os
import smtplib
from urllib.parse import urlencode

from firebase_admin import auth


_LOGGER = logging.getLogger(__name__)


class ParentInvitationDeliveryError(RuntimeError):
    pass


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ParentInvitationDeliveryError("Parent invitation email delivery is not configured.")
    return value


def deliver_parent_invitation(recipient_email: str, invitation_id: str, verifier: str) -> None:
    """Generate an Auth link and send it with the opaque invitation values.

    Deployment must bind the SMTP password and HMAC key from Secret Manager.
    The client never receives either the generated sign-in link or verifier.
    """
    continue_url = _required("PARENT_INVITATION_CONTINUE_URL")
    separator = "&" if "?" in continue_url else "?"
    continue_url = f"{continue_url}{separator}{urlencode({'invitationId': invitation_id, 'verifier': verifier})}"
    try:
        # ``link_domain`` is only valid for a Firebase-Authentication approved
        # custom link domain.  The project uses Firebase's verified default
        # action-link host, while ``continue_url`` stays on Hosting where the
        # Android App Link is verified.  Supplying a normal ``web.app`` site as
        # ``link_domain`` makes Admin SDK reject the invitation before SMTP.
        settings = auth.ActionCodeSettings(
            url=continue_url,
            handle_code_in_app=True,
            android_package_name=_required("PARENT_INVITATION_ANDROID_PACKAGE"),
            android_install_app=True,
        )
        link = auth.generate_sign_in_with_email_link(recipient_email, settings)
    except ParentInvitationDeliveryError:
        raise
    except Exception as error:
        # Provider text can contain recipient or action-link data, so record
        # only a stable diagnostic category in protected server logs.
        _LOGGER.error(
            "parent_invitation_link_generation_failed error_type=%s",
            type(error).__name__,
        )
        raise ParentInvitationDeliveryError("Unable to prepare parent invitation email.") from None

    try:
        message = EmailMessage()
        message["Subject"] = "Logic Oasis parent invitation"
        message["From"] = _required("PARENT_INVITATION_SMTP_FROM")
        message["To"] = recipient_email
        message.set_content(
            "A student invited you to their Logic Oasis learning updates. "
            f"Open this secure link to review and accept the invitation: {link}"
        )
        with smtplib.SMTP_SSL(_required("PARENT_INVITATION_SMTP_HOST"), int(os.environ.get("PARENT_INVITATION_SMTP_PORT", "465"))) as smtp:
            smtp.login(_required("PARENT_INVITATION_SMTP_USERNAME"), _required("PARENT_INVITATION_SMTP_PASSWORD"))
            smtp.send_message(message)
    except ParentInvitationDeliveryError:
        raise
    except Exception as error:
        # As above, never log SMTP/provider text because it may include
        # protected message or recipient metadata.
        _LOGGER.error(
            "parent_invitation_smtp_delivery_failed error_type=%s",
            type(error).__name__,
        )
        raise ParentInvitationDeliveryError("Unable to deliver parent invitation email.") from None
