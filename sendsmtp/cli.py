from argparse import ArgumentParser

parser = ArgumentParser("sendsmtp", description="CLI SMTP client in pure Python")
parser.add_argument(
    "host",
    metavar="HOST",
    help="Host to connect via SMTP.",
)
parser.add_argument(
    help="Sender email.",
    dest="from_",
    metavar="FROM",
)
parser.add_argument(
    "to",
    metavar="TO",
    help="Recipient email(s), comma separated.",
)
parser.add_argument(
    "-m",
    "--message",
    help="Message to send.",
    default=None,
    required=False,
)
parser.add_argument(
    "-i",
    "--input",
    help="Path to file to read message contents.",
    required=False,
    default=None,
)
parser.add_argument(
    "-p",
    "--port",
    default=None,
    type=int,
    help="Port to connect via SMTP.",
    required=False,
)
parser.add_argument(
    "-u",
    "--username",
    default=None,
    help="Username for login.",
    required=False,
)
parser.add_argument(
    "--password",
    default=None,
    help="Password for login.",
    required=False,
)
parser.add_argument(
    "-t",
    "--tls",
    help="Flag to use TLS.",
    action="store_true",
    required=False,
)
parser.add_argument(
    "-c",
    "--cc",
    default=None,
    help="Recipient address(es) to send copy to, comma separated.",
    required=False,
)
parser.add_argument(
    "-b",
    "--bcc",
    default=None,
    help="Recipient address(es) to send blind copy to, comma separated.",
    required=False,
)
parser.add_argument(
    "-s",
    "--subject",
    default=None,
    help="Message subject.",
    required=False,
)
