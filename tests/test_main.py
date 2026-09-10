"""In-process tests for the CLI entrypoint main()."""

import io
import sys
from typing import Any

import pytest
from conftest import AUTH_PASSWORD, AUTH_USER, ServerStarter

from sendsmtp.__main__ import main
from sendsmtp.sender import Security


def run_main(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> None:
    """Run main() with a patched argv and empty stdin."""
    monkeypatch.setattr(sys, "argv", ["sendsmtp", *argv])
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    main()


class TestMainMessageSources:
    def test_message_flag(
        self, monkeypatch: pytest.MonkeyPatch, smtp_server_factory: ServerStarter
    ) -> None:
        server = smtp_server_factory()
        run_main(
            monkeypatch,
            ["127.0.0.1", "-p", str(server.port), "a@b.c", "x@y.z", "-m", "hello body"],
        )
        assert len(server.handler.messages) == 1

    def test_input_file(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
        smtp_server_factory: ServerStarter,
    ) -> None:
        server = smtp_server_factory()
        path = tmp_path / "msg.txt"
        path.write_text("file body")
        run_main(
            monkeypatch,
            ["127.0.0.1", "-p", str(server.port), "a@b.c", "x@y.z", "-i", str(path)],
        )
        assert len(server.handler.messages) == 1

    def test_stdin_pipe(
        self, monkeypatch: pytest.MonkeyPatch, smtp_server_factory: ServerStarter
    ) -> None:
        server = smtp_server_factory()
        monkeypatch.setattr(
            sys,
            "argv",
            ["sendsmtp", "127.0.0.1", "-p", str(server.port), "a@b.c", "x@y.z"],
        )
        monkeypatch.setattr(sys, "stdin", io.StringIO("piped body"))
        # main() does "from select import select"; patch the bound name.
        monkeypatch.setattr(
            "sendsmtp.__main__.select", lambda *_: ([sys.stdin], [], [])
        )
        main()
        assert len(server.handler.messages) == 1


class TestMainSubject:
    def test_subject_flag_wins(
        self, monkeypatch: pytest.MonkeyPatch, smtp_server_factory: ServerStarter
    ) -> None:
        server = smtp_server_factory()
        run_main(
            monkeypatch,
            [
                "127.0.0.1",
                "-p",
                str(server.port),
                "a@b.c",
                "x@y.z",
                "-m",
                "body",
                "-s",
                "flag subj",
            ],
        )
        assert b"flag subj" in server.handler.messages[0].content

    def test_subject_extracted_from_body(
        self, monkeypatch: pytest.MonkeyPatch, smtp_server_factory: ServerStarter
    ) -> None:
        server = smtp_server_factory()
        run_main(
            monkeypatch,
            [
                "127.0.0.1",
                "-p",
                str(server.port),
                "a@b.c",
                "x@y.z",
                "-m",
                "Subject: inline subj\nbody",
            ],
        )
        assert b"inline subj" in server.handler.messages[0].content


class TestMainSecurity:
    def test_starttls_flag(
        self, monkeypatch: pytest.MonkeyPatch, smtp_server_factory: ServerStarter
    ) -> None:
        server = smtp_server_factory(Security.STARTTLS)
        run_main(
            monkeypatch,
            [
                "127.0.0.1",
                "-p",
                str(server.port),
                "a@b.c",
                "x@y.z",
                "-m",
                "b",
                "--starttls",
            ],
        )
        assert len(server.handler.messages) == 1

    def test_tls_flag(
        self, monkeypatch: pytest.MonkeyPatch, smtp_server_factory: ServerStarter
    ) -> None:
        server = smtp_server_factory(Security.TLS)
        run_main(
            monkeypatch,
            ["127.0.0.1", "-p", str(server.port), "a@b.c", "x@y.z", "-m", "b", "-t"],
        )
        assert len(server.handler.messages) == 1


class TestMainAuth:
    def test_auth_with_password(
        self, monkeypatch: pytest.MonkeyPatch, smtp_server_factory: ServerStarter
    ) -> None:
        server = smtp_server_factory(auth=True)
        run_main(
            monkeypatch,
            [
                "127.0.0.1",
                "-p",
                str(server.port),
                "a@b.c",
                "x@y.z",
                "-m",
                "b",
                "-u",
                AUTH_USER,
                "--password",
                AUTH_PASSWORD,
            ],
        )
        assert len(server.handler.messages) == 1


class TestMainRecipients:
    def test_comma_separated_to(
        self, monkeypatch: pytest.MonkeyPatch, smtp_server_factory: ServerStarter
    ) -> None:
        server = smtp_server_factory()
        run_main(
            monkeypatch,
            ["127.0.0.1", "-p", str(server.port), "a@b.c", "x@y.z,w@v.u", "-m", "b"],
        )
        assert server.handler.messages[0].rcpt_tos == ["x@y.z", "w@v.u"]

    def test_cc_and_bcc(
        self, monkeypatch: pytest.MonkeyPatch, smtp_server_factory: ServerStarter
    ) -> None:
        server = smtp_server_factory()
        run_main(
            monkeypatch,
            [
                "127.0.0.1",
                "-p",
                str(server.port),
                "a@b.c",
                "x@y.z",
                "-m",
                "b",
                "-c",
                "c@d.e",
                "-b",
                "f@g.h",
            ],
        )
        assert server.handler.messages[0].rcpt_tos == ["x@y.z", "c@d.e", "f@g.h"]
