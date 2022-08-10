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
    usage: sendsmtp [-h] [-m MESSAGE] [-i INPUT] [-p PORT] [-u USERNAME] [--password PASSWORD] [-t] [-c CC] [-b BCC] [-s SUBJECT] HOST FROM TO

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
      -t, --tls             Flag to use TLS.
      -c CC, --cc CC        Recipient address(es) to send copy to, comma separated.
      -b BCC, --bcc BCC     Recipient address(es) to send blind copy to, comma separated.
      -s SUBJECT, --subject SUBJECT
                            Message subject.
