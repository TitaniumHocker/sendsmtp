#!/usr/bin/env python3
"""CLI entrypoint for sendsmtp package."""

import os
import sys
from argparse import Namespace
from getpass import getpass
from select import select

from .cli import parser
from .sender import Security, Sender
from .utils import extract_subject, split_addresses


def run(args: Namespace) -> int:
    """Read the message and send it via SMTP.

    :param args: Parsed CLI arguments.
    :returns: Process exit code.
    """
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
        if args.verbose:
            sender.smtp.set_debuglevel(1)
            print(
                f"Connected to {sender.host}:{sender.port} ({sender.security}).",
                file=sys.stderr,
            )
        if args.username:
            password = args.password or getpass(f"{args.username}'s passwd:")
            reply = sender.login(args.username, password)
            if args.verbose:
                print("Authenticated, reply:", reply, file=sys.stderr)
        refused = sender.send(
            args.from_,
            args.to,
            message,
            subject,
            args.cc,
            args.bcc,
        )

    for address, (code, text) in refused.items():
        print(
            f"Recipient refused: {address}: {code} {text.decode(errors='replace')}",
            file=sys.stderr,
        )
    if args.verbose:
        delivered = [
            address
            for address in args.to + (args.cc or []) + (args.bcc or [])
            if address not in refused
        ]
        print("Message successfully sent to", ", ".join(delivered))
    else:
        print("Message successfully sent.")
    return 1 if refused else 0


def main() -> int:
    """Parse CLI arguments and send the message, reporting failures.

    Without ``--verbose`` a failure is reported as a single line; with it
    the exception propagates so Python prints the full stacktrace.

    :returns: Process exit code.
    :raises Exception: Any failure, re-raised as-is when ``--verbose``
        is given, so Python prints the full stacktrace.
    """
    args = parser.parse_args()
    try:
        return run(args)
    except KeyboardInterrupt:
        print("Aborted.", file=sys.stderr)
        return 130
    except Exception as exc:
        if args.verbose:
            raise
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("Re-run with --verbose for the full stacktrace.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
