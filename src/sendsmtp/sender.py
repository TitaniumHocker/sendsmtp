"""SMTP sender client for plain-text email messages."""

from collections.abc import Sequence
from email.mime.text import MIMEText
from smtplib import SMTP, SMTPNotSupportedError
from socket import gethostname
from types import TracebackType


class Sender:
    """Context manager wrapping an :class:`smtplib.SMTP` connection.

    :param host: SMTP server hostname.
    :param port: SMTP port; 587 when ``tls`` is used, 25 otherwise.
    :param tls: Whether to switch the connection to TLS.
    """

    port: int
    smtp: SMTP

    def __init__(self, host: str, port: int | None = None, tls: bool = False) -> None:
        self.host: str = host
        if port is None:
            if tls:
                self.port = 587
            else:
                self.port = 25
        else:
            self.port = port
        self.tls: bool = tls

    def __enter__(self) -> "Sender":
        """Open the SMTP connection and greet the server.

        :returns: Itself, with the connection opened.
        """
        self.smtp = SMTP(self.host, self.port, gethostname())
        if self.tls:
            self.smtp.starttls()
        self.smtp.ehlo(gethostname())
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        """Close the SMTP connection.

        :param exc_type: Exception type raised in the block, if any.
        :param exc_value: Exception instance raised in the block, if any.
        :param exc_traceback: Traceback of the exception, if any.
        """
        self.smtp.quit()

    def login(
        self,
        username: str,
        password: str,
        suppress: bool = True,
    ) -> tuple[int, bytes] | None:
        """Log in on the SMTP server.

        :param username: Login username.
        :param password: Login password.
        :param suppress: Whether to suppress the error raised by servers
            without AUTH support.
        :returns: Server reply, or ``None`` when the error was suppressed.
        :raises SMTPNotSupportedError: If the server does not support AUTH
            and ``suppress`` is ``False``.
        """
        try:
            return self.smtp.login(username, password)
        except SMTPNotSupportedError:
            if not suppress:
                raise
            return None

    def send(
        self,
        from_: str,
        to: Sequence[str] | str,
        message: str,
        subject: str | None = None,
        cc: Sequence[str] | str | None = None,
        bcc: Sequence[str] | str | None = None,
    ) -> dict[str, tuple[int, bytes]]:
        """Send an email message via opened SMTP connection.

        :param from_: Sender email address.
        :param to: Recipient address or sequence of addresses.
        :param message: Message body.
        :param subject: Optional subject; empty if omitted.
        :param cc: Optional carbon-copy address(es).
        :param bcc: Optional blind carbon-copy address(es).
        :returns: Refused recipients mapping from ``smtplib``.
        """
        recipients: list[str] = []
        if isinstance(to, str):
            recipients.append(to)
        else:
            recipients += to
        if cc is not None:
            if isinstance(cc, str):
                recipients.append(cc)
            else:
                recipients += cc
        if bcc is not None:
            if isinstance(bcc, str):
                recipients.append(bcc)
            else:
                recipients += bcc

        msg = MIMEText(message, "plain", "utf-8")
        msg["From"] = from_
        msg["To"] = to if isinstance(to, str) else ",".join(to)
        if cc:
            msg["CC"] = cc if isinstance(cc, str) else ",".join(cc)
        msg["Subject"] = subject if subject else ""

        return self.smtp.sendmail(from_, recipients, msg.as_string())
