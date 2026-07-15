"""DELIVER (send) stage — send the HTML brief via Gmail SMTP over SSL.

Credentials come from the environment (GMAIL_USER, GMAIL_APP_PASSWORD) — never
hardcoded (AC-7). Uses a 16-char Gmail App Password, not the account password.
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 465


def send(html_body: str, subject: str, to: str) -> None:
    """Send one HTML email. Raises RuntimeError if credentials are absent."""
    user = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError(
            "GMAIL_USER and GMAIL_APP_PASSWORD must be set "
            "(use a Gmail App Password, not your account password)."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    msg.set_content("This brief is best viewed in an HTML-capable email client.")
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT) as server:
        server.login(user, password)
        server.send_message(msg)
    print(f"[mailer] sent to {to}")
