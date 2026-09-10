"""In-process tests for the CLI entrypoint main()."""

import io
import sys
from email import message_from_bytes
from email.policy import default as default_policy
from typing import Any
from unittest.mock import MagicMock

import pytest
from conftest import AUTH_PASSWORD, AUTH_USER, ServerStarter, free_port

from sendsmtp.__main__ import main
from sendsmtp.sender import Security, Sender


def run_main(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
    """Run main() with a patched argv and empty stdin."""
    monkeypatch.setattr(sys, "argv", ["sendsmtp", *argv])
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    return main()


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
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        smtp_server_factory: ServerStarter,
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
                "-v",
            ],
        )
        assert len(server.handler.messages) == 1
        assert "Authenticated, reply:" in capsys.readouterr().err

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


class TestMainOutput:
    def test_success_message_is_short(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        smtp_server_factory: ServerStarter,
    ) -> None:
        server = smtp_server_factory()
        code = run_main(
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
            ],
        )
        assert code == 0
        assert capsys.readouterr().out.strip() == "Message successfully sent."

    def test_refused_recipient_reported_and_nonzero(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        smtp_server_factory: ServerStarter,
    ) -> None:
        server = smtp_server_factory()
        monkeypatch.setattr(
            Sender, "send", lambda *_, **__: {"w@v.u": (550, b"No such user")}
        )
        code = run_main(
            monkeypatch,
            ["127.0.0.1", "-p", str(server.port), "a@b.c", "x@y.z,w@v.u", "-m", "b"],
        )
        out = capsys.readouterr()
        assert code == 1
        assert "w@v.u: 550 No such user" in out.err
        assert out.out.strip() == "Message successfully sent."

    def test_verbose_prints_connection_and_dialog(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        smtp_server_factory: ServerStarter,
    ) -> None:
        server = smtp_server_factory()
        code = run_main(
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
                "-v",
            ],
        )
        out = capsys.readouterr()
        assert code == 0
        assert f"Connected to 127.0.0.1:{server.port} (plain)." in out.err
        assert out.out.strip() == "Message successfully sent to x@y.z, c@d.e"


class TestMainErrors:
    def test_error_is_short_by_default(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Nothing listening: one-line error, no stacktrace, exit code 1."""
        code = run_main(
            monkeypatch,
            ["127.0.0.1", "-p", str(free_port()), "a@b.c", "x@y.z", "-m", "b"],
        )
        err = capsys.readouterr().err
        assert code == 1
        assert err.startswith("Error: ConnectionRefusedError:")
        assert "Traceback" not in err

    def test_verbose_propagates_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with pytest.raises(ConnectionRefusedError):
            run_main(
                monkeypatch,
                [
                    "127.0.0.1",
                    "-p",
                    str(free_port()),
                    "a@b.c",
                    "x@y.z",
                    "-m",
                    "b",
                    "-v",
                ],
            )

    def test_keyboard_interrupt(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def boom(_: Any) -> int:
            raise KeyboardInterrupt

        monkeypatch.setattr("sendsmtp.__main__.run", boom)
        code = run_main(monkeypatch, ["127.0.0.1", "a@b.c", "x@y.z", "-m", "b"])
        assert code == 130
        assert capsys.readouterr().err.strip() == "Aborted."


class TestMainAttachments:
    def test_attach_flag_sends_file(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
        smtp_server_factory: ServerStarter,
    ) -> None:
        server = smtp_server_factory()
        path = tmp_path / "report.txt"
        path.write_text("attached text")
        code = run_main(
            monkeypatch,
            [
                "127.0.0.1",
                "-p",
                str(server.port),
                "a@b.c",
                "x@y.z",
                "-m",
                "b",
                "-a",
                str(path),
            ],
        )
        assert code == 0
        parsed = message_from_bytes(
            server.handler.messages[0].content, policy=default_policy
        )
        names = [part.get_filename() for part in parsed.iter_attachments()]
        assert names == ["report.txt"]

    def test_several_attachments(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
        smtp_server_factory: ServerStarter,
    ) -> None:
        server = smtp_server_factory()
        first, second = tmp_path / "one.txt", tmp_path / "two.bin"
        first.write_text("1")
        second.write_bytes(b"2")
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
                "-a",
                str(first),
                "-a",
                str(second),
            ],
        )
        parsed = message_from_bytes(
            server.handler.messages[0].content, policy=default_policy
        )
        names = [part.get_filename() for part in parsed.iter_attachments()]
        assert names == ["one.txt", "two.bin"]

    def test_missing_attachment_fails_before_connecting(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Bad path is reported without opening an SMTP connection."""
        code = run_main(
            monkeypatch,
            [
                "127.0.0.1",
                "-p",
                str(free_port()),
                "a@b.c",
                "x@y.z",
                "-m",
                "b",
                "-a",
                "/no/such/file.txt",
            ],
        )
        assert code == 1
        assert "Attachment not found: /no/such/file.txt" in capsys.readouterr().err


class TestMainHtml:
    def test_html_flag_sends_html_body(
        self,
        monkeypatch: pytest.MonkeyPatch,
        smtp_server_factory: ServerStarter,
    ) -> None:
        server = smtp_server_factory()
        code = run_main(
            monkeypatch,
            [
                "127.0.0.1",
                "-p",
                str(server.port),
                "a@b.c",
                "x@y.z",
                "-m",
                "<p>hi</p>",
                "--html",
            ],
        )
        assert code == 0
        parsed = message_from_bytes(
            server.handler.messages[0].content, policy=default_policy
        )
        assert parsed.get_content_type() == "text/html"
        assert parsed.get_content().strip() == "<p>hi</p>"
