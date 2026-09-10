"""In-process tests for the CLI entrypoint main()."""

import io
import sys
from email import message_from_bytes
from typing import Any
from unittest.mock import MagicMock

import pytest
from conftest import AUTH_PASSWORD, AUTH_USER, ServerStarter

from sendsmtp.__main__ import main
from sendsmtp.sender import Security, Sender


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

    def test_stdin_interactive_eof(
        self, monkeypatch: pytest.MonkeyPatch, smtp_server_factory: ServerStarter
    ) -> None:
        """No piped stdin: message typed interactively until an EOF line."""
        server = smtp_server_factory()
        monkeypatch.setattr(
            sys,
            "argv",
            ["sendsmtp", "127.0.0.1", "-p", str(server.port), "a@b.c", "x@y.z"],
        )
        monkeypatch.setattr(sys, "stdin", io.StringIO("typed line\neof\nnever sent"))
        monkeypatch.setattr("sendsmtp.__main__.select", lambda *_: ([], [], []))
        main()
        assert len(server.handler.messages) == 1
        raw = server.handler.messages[0].content
        assert isinstance(raw, bytes)
        payload = message_from_bytes(raw).get_payload(decode=True)
        assert isinstance(payload, bytes)
        assert b"typed line" in payload
        assert b"never sent" not in payload


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

    def test_auth_prompts_for_password(
        self, monkeypatch: pytest.MonkeyPatch, smtp_server_factory: ServerStarter
    ) -> None:
        """-u without --password: getpass() supplies the password."""
        server = smtp_server_factory(auth=True)
        monkeypatch.setattr("sendsmtp.__main__.getpass", lambda _: AUTH_PASSWORD)
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


class TestMainGuard:
    def test_python_dash_m_invocation(
        self, monkeypatch: pytest.MonkeyPatch, smtp_server_factory: ServerStarter
    ) -> None:
        """python -m sendsmtp: the __main__ guard runs main() end-to-end."""
        import runpy

        server = smtp_server_factory()
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "sendsmtp",
                "127.0.0.1",
                "-p",
                str(server.port),
                "a@b.c",
                "x@y.z",
                "-m",
                "via runpy",
            ],
        )
        with pytest.raises(SystemExit) as exc:
            runpy.run_module("sendsmtp.__main__", run_name="__main__")
        assert exc.value.code == 0
        assert len(server.handler.messages) == 1


class TestSenderStringRecipients:
    def test_cc_and_bcc_as_single_strings(self) -> None:
        """cc/bcc accept a lone address string, not only sequences."""
        sender = Sender("h")
        smtp = MagicMock()
        sender.smtp = smtp
        sender.send("a@b.c", "x@y.z", "body", cc="c@d.e", bcc="f@g.h")
        recipients = smtp.sendmail.call_args[0][1]
        assert recipients == ["x@y.z", "c@d.e", "f@g.h"]
