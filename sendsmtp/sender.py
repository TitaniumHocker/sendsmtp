import typing as t
from email.mime.text import MIMEText
from smtplib import SMTP, SMTPNotSupportedError
from socket import gethostname


class Sender:
    port: int

    def __init__(self, host: str, port: t.Optional[int] = None, tls: bool = False):
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
        self.smtp = SMTP(self.host, self.port, gethostname())
        if self.tls:
            self.smtp.starttls()
        self.smtp.ehlo(gethostname())
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):  # type: ignore
        self.smtp.quit()

    def login(self, username: str, password: str, suppress: bool = True):
        try:
            return self.smtp.login(username, password)
        except SMTPNotSupportedError:
            if not suppress:
                raise

    def send(
        self,
        from_: str,
        to: t.Union[t.Sequence[str], str],
        message: str,
        subject: t.Optional[str] = None,
        cc: t.Optional[t.Union[t.Sequence[str], str]] = None,
        bcc: t.Optional[t.Union[t.Sequence[str], str]] = None,
    ):
        recipients = []
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
