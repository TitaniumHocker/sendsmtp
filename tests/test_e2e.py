"""End-to-end tests: Sender against a live aiosmtpd server."""

from email import message_from_bytes
from smtplib import SMTPAuthenticationError, SMTPNotSupportedError
from ssl import SSLCertVerificationError
from typing import Any, cast

import pytest
from aiosmtpd.smtp import Envelope
from conftest import AUTH_PASSWORD, AUTH_USER, CaptureHandler, ServerStarter

from sendsmtp.sender import Security, Sender


def received(handler: CaptureHandler) -> Envelope:
    """Return the single captured envelope, asserting exactly one message."""
    assert len(handler.messages) == 1
    return cast(Envelope, handler.messages[0])


def body_of(envelope: Envelope) -> str:
    """Decode the MIME body captured by the server."""
    assert isinstance(envelope.content, bytes)
    payload = message_from_bytes(envelope.content).get_payload(decode=True)
    assert isinstance(payload, bytes)
    # MIME text parts end with a newline; compare the body without it.
    return payload.decode().rstrip("\r\n")


class TestPlainE2E:
    def test_send_receive(self, smtp_server_factory: ServerStarter) -> None:
        server = smtp_server_factory(Security.PLAIN)
        with Sender("127.0.0.1", server.port, Security.PLAIN) as sender:
            sender.send("a@b.c", "x@y.z", "body", "subj")
        envelope = received(server.handler)
        assert envelope.mail_from == "a@b.c"
        assert envelope.rcpt_tos == ["x@y.z"]
        assert "subj" in str(envelope.content)
        assert body_of(envelope) == "body"


class TestStarttlsE2E:
    def test_send_receive(self, smtp_server_factory: ServerStarter) -> None:
        server = smtp_server_factory(Security.STARTTLS)
        with Sender("127.0.0.1", server.port, Security.STARTTLS) as sender:
            sender.send("a@b.c", "x@y.z", "tls body")
        assert body_of(received(server.handler)) == "tls body"


class TestImplicitTlsE2E:
    test_body = "implicit body"

    def test_send_receive(self, smtp_server_factory: ServerStarter) -> None:
        server = smtp_server_factory(Security.TLS)
        with Sender("127.0.0.1", server.port, Security.TLS) as sender:
            sender.send("a@b.c", "x@y.z", self.test_body)
        assert body_of(received(server.handler)) == self.test_body


class TestAuthE2E:
    def test_login_ok(self, smtp_server_factory: ServerStarter) -> None:
        server = smtp_server_factory(Security.PLAIN, auth=True)
        with Sender("127.0.0.1", server.port, Security.PLAIN) as sender:
            reply = sender.login(AUTH_USER, AUTH_PASSWORD)
        assert reply is not None
        assert reply[0] == 235

    def test_login_bad_credentials_rejected(
        self, smtp_server_factory: ServerStarter
    ) -> None:
        server = smtp_server_factory(Security.PLAIN, auth=True)
        with Sender("127.0.0.1", server.port, Security.PLAIN) as sender:
            with pytest.raises(SMTPAuthenticationError):
                sender.login(AUTH_USER, "wrong")

    def test_raises_on_server_without_auth(
        self, smtp_server_factory: ServerStarter
    ) -> None:
        server = smtp_server_factory(Security.PLAIN, auth=False)
        with Sender("127.0.0.1", server.port, Security.PLAIN) as sender:
            with pytest.raises(SMTPNotSupportedError):
                sender.login(AUTH_USER, AUTH_PASSWORD)


class TestStarttlsAuthE2E:
    def test_login_over_starttls(self, smtp_server_factory: ServerStarter) -> None:
        server = smtp_server_factory(Security.STARTTLS, auth=True)
        with Sender("127.0.0.1", server.port, Security.STARTTLS) as sender:
            sender.login(AUTH_USER, AUTH_PASSWORD)
            sender.send("a@b.c", "x@y.z", "authed tls body")
        assert body_of(received(server.handler)) == "authed tls body"


class TestCertVerificationE2E:
    @pytest.fixture
    def untrusted(self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        """Make the test CA unknown to the client for this test."""
        empty = tmp_path / "no-ca.pem"
        empty.write_text("")
        monkeypatch.setenv("SSL_CERT_FILE", str(empty))

    def test_tls_rejects_unknown_ca(
        self, smtp_server_factory: ServerStarter, untrusted: None
    ) -> None:
        server = smtp_server_factory(Security.TLS)
        with pytest.raises(SSLCertVerificationError):
            with Sender("127.0.0.1", server.port, Security.TLS):
                pass

    def test_starttls_rejects_unknown_ca(
        self, smtp_server_factory: ServerStarter, untrusted: None
    ) -> None:
        server = smtp_server_factory(Security.STARTTLS)
        with pytest.raises(SSLCertVerificationError):
            with Sender("127.0.0.1", server.port, Security.STARTTLS):
                pass

    def test_tls_allow_untrusted_sends(
        self, smtp_server_factory: ServerStarter, untrusted: None
    ) -> None:
        server = smtp_server_factory(Security.TLS)
        with Sender(
            "127.0.0.1", server.port, Security.TLS, allow_untrusted=True
        ) as sender:
            sender.send("a@b.c", "x@y.z", "untrusted body")
        assert body_of(received(server.handler)) == "untrusted body"

    def test_starttls_allow_untrusted_sends(
        self, smtp_server_factory: ServerStarter, untrusted: None
    ) -> None:
        server = smtp_server_factory(Security.STARTTLS)
        with Sender(
            "127.0.0.1", server.port, Security.STARTTLS, allow_untrusted=True
        ) as sender:
            sender.send("a@b.c", "x@y.z", "untrusted body")
        assert body_of(received(server.handler)) == "untrusted body"
