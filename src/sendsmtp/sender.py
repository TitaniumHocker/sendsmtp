"""SMTP sender client for plain-text email messages."""

from collections.abc import Sequence
from email.mime.text import MIMEText
from enum import StrEnum
from smtplib import SMTP, SMTP_SSL
from socket import gethostname
from types import TracebackType


class Security(StrEnum):
    """Connection security mode.

    :ivar PLAIN: No transport security, plain SMTP (port 25).
    :ivar STARTTLS: Plain connection upgraded via STARTTLS extension (port 587).
    :ivar TLS: Implicit TLS from the first byte (port 465).
    """

    PLAIN = "plain"
    STARTTLS = "starttls"
    TLS = "tls"


class Sender:
    """Context manager wrapping an :class:`smtplib.SMTP` connection.

    :param host: SMTP server hostname.
    :param port: SMTP port; defaults to 465 for ``tls``, 587 for
    ``starttls`` and 25 for ``plain``.
    :param security: Connection security mode.
    """

    port: int
    smtp: SMTP

    def __init__(
        self,
        host: str,
        port: int | None = None,
        security: Security = Security.PLAIN,
    ) -> None:
        self.host: str = host
        self.security: Security = security
        if port is None:
            self.port = {
                Security.PLAIN: 25,
                Security.STARTTLS: 587,
                Security.TLS: 465,
            }[security]
        else:
            self.port = port

    def __enter__(self) -> "Sender":
        """Open the SMTP connection and greet the server.

        :returns: Itself, with the connection opened.
        """
        if self.security is Security.TLS:
            self.smtp = SMTP_SSL(self.host, self.port, gethostname())
        else:
            self.smtp = SMTP(self.host, self.port, gethostname())
            if self.security is Security.STARTTLS:
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
    ) -> tuple[int, bytes]:
        """Log in on the SMTP server.

        :param username: Login username.
        :param password: Login password.
        :returns: Server reply.
        """
        return self.smtp.login(username, password)

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
        msg["X-Mailer"] = "sendsmtp"
        msg["From"] = from_
        msg["To"] = to if isinstance(to, str) else ",".join(to)
        if cc:
            msg["CC"] = cc if isinstance(cc, str) else ",".join(cc)
        msg["Subject"] = subject if subject else ""

        return self.smtp.sendmail(from_, recipients, msg.as_string())
