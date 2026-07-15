"""T5 tests — Gmail SMTP sender: creds required (AC-7), sends multipart HTML (AC-4)."""
from unittest.mock import MagicMock, patch

import pytest

from etbrief import mailer


def test_send_raises_when_creds_missing(monkeypatch):
    monkeypatch.delenv("GMAIL_USER", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="GMAIL"):
        mailer.send("<html></html>", "Subject", "to@example.com")


def test_send_connects_logs_in_and_sends(monkeypatch):
    monkeypatch.setenv("GMAIL_USER", "sender@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "app-pass-1234")

    server = MagicMock()
    ctx = MagicMock()
    ctx.__enter__.return_value = server

    with patch.object(mailer.smtplib, "SMTP_SSL", return_value=ctx) as smtp:
        mailer.send("<html>hi</html>", "Daily Brief", "to@example.com")

    smtp.assert_called_once()                       # connected to Gmail SSL
    server.login.assert_called_once_with("sender@gmail.com", "app-pass-1234")
    server.send_message.assert_called_once()
    msg = server.send_message.call_args[0][0]
    assert msg["Subject"] == "Daily Brief"
    assert msg["To"] == "to@example.com"
    assert msg["From"] == "sender@gmail.com"
