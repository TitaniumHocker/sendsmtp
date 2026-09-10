"""Unit tests for Sender: default ports, MIME assembly, login."""

from collections.abc import Sequence
from smtplib import SMTPNotSupportedError
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from sendsmtp.sender import Security, Sender


class TestDefaultPorts:
    def test_plain_defaults_to_25(self) -> None:
        assert Sender("h").port == 25

    def test_starttls_defaults_to_587(self) -> None:
        assert Sender("h", security=Security.STARTTLS).port == 587

    def test_tls_defaults_to_465(self) -> None:
        assert Sender("h", security=Security.TLS).port == 465

    def test_explicit_port_wins(self) -> None:
        assert Sender("h", 2525).port == 2525


class TestMessageAssembly:
    def _sent(self, **kwargs: Any) -> tuple[MagicMock, str]:
        smtp = MagicMock()
        sender = Sender("h")
        sender.smtp = smtp
        defaults: dict[str, Any] = {
            "from_": "a@b.c",
            "to": ["x@y.z"],
            "message": "body",
        }
        sender.send(**{**defaults, **kwargs})
        raw = smtp.sendmail.call_args[0][2]
        return smtp, str(raw)

    def test_headers_present(self) -> None:
        _, raw = self._sent(subject="subj")
        assert "From: a@b.c" in raw
        assert "To: x@y.z" in raw
        assert "Subject: subj" in raw

    def test_x_mailer_header(self) -> None:
        _, raw = self._sent()
        assert "X-Mailer: sendsmtp" in raw

    def test_to_string_joined(self) -> None:
        _, raw = self._sent(to=["x@y.z", "w@v.u"])
        assert "To: x@y.z,w@v.u" in raw

    def test_bcc_not_in_headers_but_in_recipients(self) -> None:
        smtp, raw = self._sent(bcc=["secret@x.y"])
        assert "secret@x.y" not in raw
        recipients: Sequence[str] = smtp.sendmail.call_args[0][1]
        assert "secret@x.y" in recipients

    def test_cc_in_headers_and_recipients(self) -> None:
        smtp, raw = self._sent(cc=["copy@x.y"])
        assert "CC: copy@x.y" in raw
        recipients: Sequence[str] = smtp.sendmail.call_args[0][1]
        assert "copy@x.y" in recipients

    def test_subject_default_empty(self) -> None:
        _, raw = self._sent()
        assert "Subject: " in raw


class TestLogin:
    def _sender_with_login_raising(self, exc: Exception) -> Sender:
        sender = Sender("h")
        sender.smtp = MagicMock()
        sender.smtp.login.side_effect = exc
        return sender

    def test_raises_when_server_lacks_auth(self) -> None:
        sender = self._sender_with_login_raising(SMTPNotSupportedError())
        with pytest.raises(SMTPNotSupportedError):
            sender.login("u", "p")

    def test_passes_credentials_through(self) -> None:
        sender = Sender("h")
        sender.smtp = MagicMock()
        sender.login("user", "pass")
        sender.smtp.login.assert_called_once_with("user", "pass")


class TestEnterModes:
    def test_tls_uses_smtp_ssl(self) -> None:
        with (
            patch("sendsmtp.sender.SMTP_SSL") as ssl_cls,
            patch("sendsmtp.sender.SMTP") as plain_cls,
        ):
            ssl_cls.return_value.ehlo = MagicMock()
            with Sender("h", security=Security.TLS):
                pass
            ssl_cls.assert_called_once()
            plain_cls.assert_not_called()

    def test_plain_never_calls_starttls(self) -> None:
        with (
            patch("sendsmtp.sender.SMTP_SSL"),
            patch("sendsmtp.sender.SMTP") as plain_cls,
        ):
            plain_cls.return_value.starttls = MagicMock()
            with Sender("h"):
                pass
            plain_cls.return_value.starttls.assert_not_called()

    def test_starttls_upgrades(self) -> None:
        with (
            patch("sendsmtp.sender.SMTP_SSL"),
            patch("sendsmtp.sender.SMTP") as plain_cls,
        ):
            plain_cls.return_value.starttls = MagicMock()
            plain_cls.return_value.ehlo = MagicMock()
            with Sender("h", security=Security.STARTTLS):
                pass
            plain_cls.return_value.starttls.assert_called_once()
