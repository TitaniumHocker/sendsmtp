"""SMTP sender client for plain-text and HTML email messages."""

from collections.abc import Sequence
from email.message import EmailMessage
from enum import StrEnum
from mimetypes import guess_type
from pathlib import Path
from smtplib import SMTP, SMTP_SSL
from socket import gethostname
from ssl import CERT_NONE, SSLContext, create_default_context
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
    :param allow_untrusted: Skip TLS certificate verification.
    """

    port: int
    smtp: SMTP

    def __init__(
        self,
        host: str,
        port: int | None = None,
        security: Security = Security.PLAIN,
        allow_untrusted: bool = False,
    ) -> None:
        self.host: str = host
        self.security: Security = security
        self.allow_untrusted: bool = allow_untrusted
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
        context: SSLContext | None = None
        if self.security is not Security.PLAIN:
            # smtplib defaults to an unverified context, so build our own.
            context = create_default_context()
            if self.allow_untrusted:
                context.check_hostname = False
                context.verify_mode = CERT_NONE
        if self.security is Security.TLS:
            self.smtp = SMTP_SSL(self.host, self.port, gethostname(), context=context)
        else:
            self.smtp = SMTP(self.host, self.port, gethostname())
            if self.security is Security.STARTTLS:
                self.smtp.starttls(context=context)
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
        attachments: Sequence[str | Path] | None = None,
        html: bool = False,
    ) -> dict[str, tuple[int, bytes]]:
        """Send an email message via opened SMTP connection.

        :param from_: Sender email address.
        :param to: Recipient address or sequence of addresses.
        :param message: Message body.
        :param subject: Optional subject; empty if omitted.
        :param cc: Optional carbon-copy address(es).
        :param bcc: Optional blind carbon-copy address(es).
        :param attachments: Optional paths of files to attach.
        :param html: Send the body as ``text/html`` instead of ``text/plain``.
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

        msg = EmailMessage()
        msg["X-Mailer"] = "sendsmtp"
        msg["From"] = from_
        msg["To"] = to if isinstance(to, str) else ",".join(to)
        if cc:
            msg["CC"] = cc if isinstance(cc, str) else ",".join(cc)
        msg["Subject"] = subject if subject else ""
        msg.set_content(message, subtype="html" if html else "plain")

        for attachment in attachments or []:
            path = Path(attachment)
            ctype, encoding = guess_type(path.name)
            # A content encoding (.gz, .bz2) makes the guessed type the type
            # of the *decoded* payload, which is not what we are attaching.
            maintype, _, subtype = (
                ctype if ctype and not encoding else "application/octet-stream"
            ).partition("/")
            msg.add_attachment(
                path.read_bytes(),
                maintype=maintype,
                subtype=subtype,
                filename=path.name,
            )

        return self.smtp.sendmail(from_, recipients, msg.as_string())
