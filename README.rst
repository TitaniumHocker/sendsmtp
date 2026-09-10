########
sendsmtp
########

CLI SMTP client in pure Python. No dependencies, one command, plain-text
mail: it builds a UTF-8 ``text/plain`` message and hands it to an SMTP
server.

Installation
============

.. code:: console

   python3 -m pip install --user --upgrade sendsmtp

Requires Python 3.11 or newer.

Quick start
===========

.. code:: console

   $ sendsmtp smtp.example.com me@example.com you@example.com -s "Hi" -m "Hello!"
   Message successfully sent.

Synopsis
========

.. code:: console

   sendsmtp [-h] [-m MESSAGE] [-i INPUT] [-p PORT] [-u USERNAME]
            [--password PASSWORD] [-t | --starttls] [-c CC] [-b BCC]
            [-s SUBJECT] [-v]
            HOST FROM TO

Arguments
=========

``HOST``
--------

Hostname or IP address of the SMTP server to connect to.

.. code:: console

   $ sendsmtp smtp.example.com me@example.com you@example.com -m "hi"

``FROM``
--------

Sender address, used both as the SMTP envelope sender (``MAIL FROM``) and
as the ``From:`` header.

``TO``
------

Recipient address, or several addresses separated by commas — no spaces
around the commas.

.. code:: console

   $ sendsmtp smtp.example.com me@example.com "a@example.com,b@example.com" -m "hi"

Options
=======

``-m MESSAGE``, ``--message MESSAGE``
-------------------------------------

Message body, given inline.

.. code:: console

   $ sendsmtp smtp.example.com me@example.com you@example.com -m "Deploy finished."

``-i INPUT``, ``--input INPUT``
-------------------------------

Path to a file to read the message body from. Takes precedence over
``--message``. If the path is not an existing file the option is ignored
and the body is taken from ``--message`` or from stdin instead.

.. code:: console

   $ sendsmtp smtp.example.com me@example.com you@example.com -i report.txt

If neither ``--message`` nor ``--input`` is given, the body is read from
stdin. Piped input is read to EOF:

.. code:: console

   $ dmesg | tail -n 20 | sendsmtp smtp.example.com me@example.com you@example.com -s "dmesg"

When stdin is a terminal, sendsmtp prompts and reads lines until a line
containing only ``EOF``:

.. code:: console

   $ sendsmtp smtp.example.com me@example.com you@example.com
   Please, provide message contents. Type 'EOF' for end.
   First line.
   Second line.
   EOF
   Message successfully sent.

``-s SUBJECT``, ``--subject SUBJECT``
-------------------------------------

Message subject.

.. code:: console

   $ sendsmtp smtp.example.com me@example.com you@example.com -s "Nightly build" -m "green"

If ``--subject`` is not given and the body starts with a ``Subject:``
line, that line is stripped from the body and used as the subject:

.. code:: console

   $ printf 'Subject: From the body\n\nBody text.\n' \
       | sendsmtp smtp.example.com me@example.com you@example.com

``-p PORT``, ``--port PORT``
----------------------------

SMTP port. Defaults depend on the security mode: ``25`` for plain,
``587`` with ``--starttls``, ``465`` with ``--tls``.

.. code:: console

   $ sendsmtp smtp.example.com me@example.com you@example.com -p 2525 -m "hi"

``-t``, ``--tls``
-----------------

Use implicit TLS — the connection is encrypted from the first byte
(``SMTPS``, port 465 by default). Mutually exclusive with ``--starttls``.

.. code:: console

   $ sendsmtp smtp.example.com me@example.com you@example.com -t -u me@example.com -m "hi"

``--starttls``
--------------

Connect in plain text and upgrade the connection with the ``STARTTLS``
extension (port 587 by default). Mutually exclusive with ``--tls``.

.. code:: console

   $ sendsmtp smtp.example.com me@example.com you@example.com --starttls -u me@example.com -m "hi"

``-u USERNAME``, ``--username USERNAME``
----------------------------------------

Username for SMTP authentication. Without it no ``AUTH`` is attempted.

``--password PASSWORD``
-----------------------

Password for SMTP authentication. If ``--username`` is given but
``--password`` is not, the password is asked for interactively and is not
echoed — preferable, since command lines are visible to other processes
and land in the shell history.

.. code:: console

   $ sendsmtp smtp.example.com me@example.com you@example.com --starttls -u me@example.com -m "hi"
   me@example.com's passwd:

Authentication failures abort the run; the message is not sent.

``-c CC``, ``--cc CC``
----------------------

Carbon-copy recipient(s), comma separated. The addresses appear in the
``CC:`` header and receive the message.

.. code:: console

   $ sendsmtp smtp.example.com me@example.com you@example.com -c "boss@example.com" -m "hi"

``-b BCC``, ``--bcc BCC``
-------------------------

Blind carbon-copy recipient(s), comma separated. They receive the message
but are not listed in any header.

.. code:: console

   $ sendsmtp smtp.example.com me@example.com you@example.com -b "archive@example.com" -m "hi"

``-v``, ``--verbose``
---------------------

Print the SMTP dialog to stderr, report the connection and authentication
steps, list the addresses the message was delivered to, and, on failure,
let the full stacktrace through instead of a one-line error.

.. code:: console

   $ sendsmtp smtp.example.com me@example.com you@example.com -m "hi" -v
   Connected to smtp.example.com:25 (plain).
   send: 'ehlo host.example.com\r\n'
   reply: b'250 smtp.example.com\r\n'
   ...
   Message successfully sent to you@example.com

``-h``, ``--help``
------------------

Print the usage summary and exit.

Headers
=======

The generated message carries ``From:``, ``To:``, ``Subject:``,
``CC:`` (only with ``--cc``) and ``X-Mailer: sendsmtp``.

Exit codes
==========

======= =========================================================
Code    Meaning
======= =========================================================
``0``   Message accepted by the server for every recipient.
``1``   Error, or at least one recipient was refused.
``130`` Interrupted with ``Ctrl-C``.
======= =========================================================

On failure only a single-line error is printed; pass ``--verbose`` to get
the SMTP dialog and the full stacktrace.

License
=======

MIT. See `LICENSE <LICENSE>`_.
