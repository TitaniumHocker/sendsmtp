########
sendsmtp
########

CLI SMTP client in pure Python.

Installation:

.. code:: console

   python3 -m pip install --user --upgrade sendsmtp

Usage:

.. code:: console

   $ sendsmtp --help
    usage: sendsmtp [-h] [-m MESSAGE] [-i INPUT] [-p PORT] [-u USERNAME]
                    [--password PASSWORD] [-t | --starttls] [-c CC] [-b BCC]
                    [-s SUBJECT] [-v]
                    HOST FROM TO

    CLI SMTP client in pure Python

    positional arguments:
      HOST                  Host to connect via SMTP.
      FROM                  Sender email.
      TO                    Recipient email(s), comma separated.

    options:
      -h, --help            show this help message and exit
      -m MESSAGE, --message MESSAGE
                            Message to send.
      -i INPUT, --input INPUT
                            Path to file to read message contents.
      -p PORT, --port PORT  Port to connect via SMTP.
      -u USERNAME, --username USERNAME
                            Username for login.
      --password PASSWORD   Password for login.
      -t, --tls             Flag to use implicit TLS (port 465).
      --starttls            Flag to use STARTTLS extension (port 587).
      -c CC, --cc CC        Recipient address(es) to send copy to, comma separated.
      -b BCC, --bcc BCC     Recipient address(es) to send blind copy to, comma separated.
      -s SUBJECT, --subject SUBJECT
                            Message subject.
      -v, --verbose         Print the SMTP dialog and full stacktrace on error.

On failure only a single-line error is printed; pass ``--verbose`` to get the
SMTP dialog and the full stacktrace. Exit code is ``0`` on success, ``1`` on
error or when a recipient was refused, ``130`` on ``Ctrl-C``.
