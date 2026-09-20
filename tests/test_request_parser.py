import pytest

from uarb_agent.models import ParsedRequest
from uarb_agent.request_parser import (
    normalize_document_type,
    normalize_matter_number,
    parse_request,
)

EMAIL = "user@example.com"


def parse(body, subject=""):
    return parse_request(subject, body, EMAIL, mode="regex")


@pytest.mark.parametrize("raw,want", [
    ("m12205", "M12205"), ("12205", "M12205"), ("M12205", "M12205"), (" M 12205 ", "M12205"),
    ("M1234", None), ("M123456", None), ("1234", None), ("ABC123", None), ("", None),
])
def test_normalize_matter(raw, want):
    assert normalize_matter_number(raw) == want


@pytest.mark.parametrize("raw,want", [
    ("exhibits", "Exhibits"), ("EXHIBITS", "Exhibits"), ("key documents", "Key Documents"),
    ("other docs", "Other Documents"), ("other documents", "Other Documents"),
    ("transcript", "Transcripts"), ("recording", "Recordings"), ("  Key   Documents ", "Key Documents"),
    ("Hearings", None), ("Related Matters", None), ("", None), ("photos", None),
])
def test_normalize_type(raw, want):
    assert normalize_document_type(raw) == want


@pytest.mark.parametrize("t", ["Exhibits", "Key Documents", "Other Documents", "Transcripts", "Recordings"])
def test_all_five_types_accepted(t):
    r = parse(f"Hi Agent, can you give me {t} files from M12205? Thanks!")
    assert r == ParsedRequest(matter_number="M12205", document_type=t, requester_email=EMAIL)


def test_example_from_assignment():
    r = parse("Hi Agent, Can you give me Other Documents files from M12205? Thanks!")
    assert (r.matter_number, r.document_type) == ("M12205", "Other Documents")


def test_matter_in_subject_and_lowercase_and_bare_digits():
    assert parse("please send transcripts", subject="m12383").matter_number == "M12383"
    assert parse("need the exhibits for 12205").matter_number == "M12205"


def test_key_documents_not_double_counted_as_documents():
    assert parse("key documents for M12205").document_type == "Key Documents"


@pytest.mark.parametrize("body,code", [
    ("I want exhibits", "MISSING_MATTER_NUMBER"),
    ("I want exhibits for matter ABC123", "INVALID_MATTER_NUMBER"),
    ("exhibits for M1234", "INVALID_MATTER_NUMBER"),
    ("exhibits for M123456", "INVALID_MATTER_NUMBER"),
    ("Please send M12205", "MISSING_DOCUMENT_TYPE"),
    ("Please send the hearings for M12205", "INVALID_DOCUMENT_TYPE"),
    ("Please send the related matters for M12205", "INVALID_DOCUMENT_TYPE"),
    ("Hello, how are you today?", "INVALID_INPUT"),
    ("exhibits for M12205 and M12383", "INVALID_INPUT"),
    ("exhibits and transcripts for M12205", "INVALID_INPUT"),
])
def test_errors(body, code):
    r = parse(body)
    assert r == {"requester_email": EMAIL, "error_code": code}


def test_same_matter_repeated_is_fine():
    assert parse("M12205 exhibits please. Again: m12205").matter_number == "M12205"


def test_quoted_history_ignored():
    body = "transcripts for M12205\n\nOn Mon, Jan 1, 2026 someone wrote:\n> M99999 exhibits"
    r = parse(body)
    assert (r.matter_number, r.document_type) == ("M12205", "Transcripts")


def test_llm_failure_falls_back_to_regex(monkeypatch):
    import uarb_agent.request_parser as rp

    def boom(_):
        raise RuntimeError("no network")

    monkeypatch.setattr(rp, "extract_with_llm", boom)
    r = parse_request("", "exhibits for M12205", EMAIL, mode="llm")
    assert r.matter_number == "M12205"


def test_llm_output_still_goes_through_validation(monkeypatch):
    import uarb_agent.request_parser as rp

    monkeypatch.setattr(
        rp, "extract_with_llm",
        lambda _: rp.Extracted(matter_numbers=["m12205"], document_types=["other docs"]),
    )
    r = parse_request("", "whatever", EMAIL, mode="llm")
    assert (r.matter_number, r.document_type) == ("M12205", "Other Documents")
    monkeypatch.setattr(
        rp, "extract_with_llm",
        lambda _: rp.Extracted(matter_numbers=["M1"], document_types=["exhibits"]),
    )
    assert parse_request("", "x", EMAIL, mode="llm")["error_code"] == "INVALID_MATTER_NUMBER"
