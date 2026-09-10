"""Pure helpers extracted from the CLI entrypoint."""

from collections.abc import Sequence


def split_addresses(value: str | Sequence[str] | None) -> list[str] | None:
    """Normalize recipient addresses from CLI input.

    :param value: Comma-separated addresses, a single address, an already
        split sequence, or ``None`` when the option was not given.
    :returns: List of addresses, or ``None`` if ``value`` is ``None``.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value.split(",") if "," in value else [value]
    return list(value)


def extract_subject(message: str) -> tuple[str | None, str]:
    """Extract the subject from the first line of the message, if any.

    :param message: Raw message contents.
    :returns: Tuple of the subject (``None`` if the message does not start
        with a ``Subject:`` line) and the remaining message body.
    """
    if len(message) > 8 and message[:8].lower().startswith("subject:"):
        subject, rest = message.split("\n", 1)
        return subject.split(":", 1)[1].strip(), rest
    return None, message
