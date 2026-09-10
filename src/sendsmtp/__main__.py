#!/usr/bin/env python3
"""CLI entrypoint for sendsmtp package."""

import os
import sys
from getpass import getpass
from select import select

from .cli import parser
from .sender import Security, Sender
from .utils import extract_subject, split_addresses


def main() -> int:
    """Parse CLI arguments, read the message and send it via SMTP.

    :returns: Process exit code.
    """
    args = parser.parse_args()

    # Parsing addresses.
    args.to = split_addresses(args.to) or []
    args.cc = split_addresses(args.cc)
    args.bcc = split_addresses(args.bcc)

    # Getting message contents.
    if args.input is not None and os.path.isfile(args.input):
        with open(args.input) as fh:
            message = fh.read()
    elif args.message is not None:
        message = args.message
    else:
        if select([sys.stdin], [], [], 0.0)[0]:
            message = sys.stdin.read()
        else:
            print("Please, provide message contents. Type 'EOF' for end.")
            buff = []
            for line in sys.stdin:
                if line.strip().upper() == "EOF":
                    break
                buff.append(line)
            message = str("".join(buff))

    # Getting subject: -s wins over a leading "Subject:" line.
    if args.subject is not None:
        subject = args.subject
    else:
        subject, message = extract_subject(message)

    if args.tls:
        security = Security.TLS
    elif args.starttls:
        security = Security.STARTTLS
    else:
        security = Security.PLAIN

    with Sender(args.host, args.port, security) as sender:
        if args.username and args.password:
            print("Authenticated, reply:", sender.login(args.username, args.password))
        elif args.username and not args.password:
            print(
                "Authenticated, reply:",
                sender.login(args.username, getpass(f"{args.username}'s passwd:")),
            )
        reply = sender.send(
            args.from_,
            args.to,
            message,
            subject,
            args.cc,
            args.bcc,
        )
        print("Message successfully sent, reply:", reply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
