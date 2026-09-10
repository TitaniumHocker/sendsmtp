"""Shared fixtures: aiosmtpd server factory, TLS contexts, free ports."""

import os
import socket
import ssl
from collections.abc import Callable, Iterator
from typing import Any, NamedTuple

import pytest
import trustme
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP as SMTPServer
from aiosmtpd.smtp import AuthResult, LoginPassword

from sendsmtp.sender import Security

AUTH_USER = "user"
AUTH_PASSWORD = "secret"


class CaptureHandler:
    """aiosmtpd handler that stores every received message envelope."""

    def __init__(self) -> None:
        self.messages: list[Any] = []

    async def handle_DATA(
        self,
        server: SMTPServer,
        session: Any,
        envelope: Any,
    ) -> str:
        self.messages.append(envelope)
        return "250 Message accepted for delivery"


class ServerHandle(NamedTuple):
    """A started test server: its handler and listening port."""

    handler: CaptureHandler
    port: int


ServerStarter = Callable[..., ServerHandle]


def make_authenticator(
    valid: tuple[str, str] = (AUTH_USER, AUTH_PASSWORD),
) -> Callable[..., AuthResult]:
    """Build an authenticator accepting exactly one login/password pair."""

    def authenticator(
        server: SMTPServer,
        session: Any,
        envelope: Any,
        mechanism: str,
        auth_data: Any,
    ) -> AuthResult:
        if not isinstance(auth_data, LoginPassword):
            return AuthResult(success=False, handled=False)
        ok = (
            auth_data.login == valid[0].encode()
            and auth_data.password == valid[1].encode()
        )
        # handled=False lets the server send the 535 reply itself;
        # handled=True on failure makes the server send nothing at all.
        return AuthResult(success=ok, handled=False)

    return authenticator


def free_port() -> int:
    """Reserve and release an ephemeral port.

    ponytail: aiosmtpd Controller does not support port=0, so we pick a
    free port ourselves; small TOCTOU race is acceptable for tests.
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session", autouse=True)
def trusted_ca(tmp_path_factory: pytest.TempPathFactory) -> Iterator[trustme.CA]:
    """Session-scoped CA, trusted process-wide via ``SSL_CERT_FILE``.

    ``ssl.create_default_context()`` reads that variable, so the client
    side of every test trusts the server certificates issued below.
    """
    ca = trustme.CA()
    pem = tmp_path_factory.mktemp("ca") / "ca.pem"
    ca.cert_pem.write_to_path(pem)
    old = os.environ.get("SSL_CERT_FILE")
    os.environ["SSL_CERT_FILE"] = str(pem)
    yield ca
    if old is None:
        del os.environ["SSL_CERT_FILE"]
    else:
        os.environ["SSL_CERT_FILE"] = old


@pytest.fixture(scope="session")
def server_ssl_context(trusted_ca: trustme.CA) -> Any:
    """Session-scoped server SSL context from the test CA."""
    cert = trusted_ca.issue_cert("127.0.0.1", "localhost")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    cert.configure_cert(ctx)
    return ctx


@pytest.fixture
def smtp_server_factory(server_ssl_context: Any) -> Iterator[ServerStarter]:
    """Factory fixture starting an aiosmtpd server per test.

    Yields a function taking security mode and auth flag; every started
    server is stopped on teardown.
    """
    started: list[Controller] = []

    def start(
        security: Security = Security.PLAIN,
        *,
        auth: bool = False,
    ) -> ServerHandle:
        handler = CaptureHandler()
        kwargs: dict[str, Any] = {}
        ctl_kwargs: dict[str, Any] = {
            "hostname": "127.0.0.1",
            "port": free_port(),
        }
        if auth:
            kwargs["authenticator"] = make_authenticator()
            if security is Security.PLAIN:
                kwargs["auth_require_tls"] = False
        if security is Security.STARTTLS:
            ctl_kwargs["tls_context"] = server_ssl_context
        elif security is Security.TLS:
            ctl_kwargs["ssl_context"] = server_ssl_context
        controller = Controller(
            handler,
            **{**kwargs, **ctl_kwargs},
        )
        controller.start()
        started.append(controller)
        return ServerHandle(handler, int(controller.port))

    yield start
    for controller in started:
        controller.stop()
