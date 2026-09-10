"""Unit tests for the pure helpers in sendsmtp.utils."""

from sendsmtp.utils import extract_subject, split_addresses


class TestSplitAddresses:
    def test_none_stays_none(self) -> None:
        assert split_addresses(None) is None

    def test_single_string_becomes_list(self) -> None:
        assert split_addresses("a@b.c") == ["a@b.c"]

    def test_comma_separated_splits(self) -> None:
        assert split_addresses("a@b.c,d@e.f") == ["a@b.c", "d@e.f"]

    def test_sequence_passes_through_as_list(self) -> None:
        assert split_addresses(["a@b.c", "d@e.f"]) == ["a@b.c", "d@e.f"]


class TestExtractSubject:
    def test_subject_line_extracted(self) -> None:
        subject, body = extract_subject("Subject: hello\n\nbody text")
        assert subject == "hello"
        assert body == "\nbody text"

    def test_case_insensitive_prefix(self) -> None:
        subject, _ = extract_subject("SUBJECT: hi\nbody")
        assert subject == "hi"

    def test_no_subject_returns_none(self) -> None:
        subject, body = extract_subject("just a body")
        assert subject is None
        assert body == "just a body"

    def test_too_short_message_has_no_subject(self) -> None:
        subject, body = extract_subject("Subject")
        assert subject is None
        assert body == "Subject"

    def test_subject_mid_message_ignored(self) -> None:
        subject, body = extract_subject("line\nSubject: hi\nrest")
        assert subject is None
        assert body == "line\nSubject: hi\nrest"
