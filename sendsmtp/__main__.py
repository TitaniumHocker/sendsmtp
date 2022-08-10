#!/usr/bin/env python3
"""CLI entrypoint for sendsmtp package."""
import os
import sys
from getpass import getpass
from select import select

from .cli import parser
from .sender import Sender


def main() -> int:
    args = parser.parse_args()

    # Parsing addresses.
    if args.to is not None and "," in args.to:
        args.to = args.to.split(",")
    if args.cc is not None and "," in args.cc:
        args.cc = args.cc.split(",")
    if args.bcc is not None and "," in args.bcc:
        args.bcc = args.bcc.split(",")

    # Getting message contents.
    if args.input is not None and os.path.isfile(args.input):
        with open(args.input, "rt") as fh:
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

    # Getting subject.
    if args.subject is not None:
        subject = args.subject
    elif len(message) > 8 and message[:8].lower().startswith("subject:"):
        subject, message = message.split("\n", 1)
        subject = subject.split(":", 1)[2].strip()
    else:
        subject = None

    with Sender(args.host, args.port, args.tls) as sender:
        if args.username and args.password:
            sender.login(args.username, args.password)
        elif args.username and not args.password:
            sender.login(args.username, getpass(f"{args.username}'s passwd:"))
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
