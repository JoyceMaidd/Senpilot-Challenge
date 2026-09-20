import pytest

from uarb_agent.email_composer import compose, format_counts, format_date
from uarb_agent.models import ComposerInput, DownloadedFile, FailedDownload, Metadata

COUNTS = {"Exhibits": 13, "Key Documents": 5, "Other Documents": 21, "Transcripts": 0, "Recordings": 0}
MD = Metadata(
    matter_number="M12205", status="Open",
    title="Halifax Regional Water Commission - Windsor Street Exchange Redevelopment Project",
    description="$69,270,000", type="Water", category="Capital Expenditure",
    date_received="04/07/2025", decision_date="10/23/2025",
)
FILES = [DownloadedFile(doc_no=str(i), title="t", local_path=f"/tmp/{i}.pdf") for i in range(10)]


def base(**kw):
    d = dict(requester_email="u@example.com", matter_number="M12205", document_type="Other Documents",
             metadata=MD, document_counts=COUNTS, downloaded_files=FILES, zip_file="/tmp/x.zip")
    d.update(kw)
    return ComposerInput(**d)


def test_success_matches_assignment_example():
    e = compose(base())
    assert e.subject == "UARB Documents - M12205"
    assert e.attachment == "/tmp/x.zip"
    assert e.body == (
        "Hi User,\n\n"
        "M12205 is about the Halifax Regional Water Commission - Windsor Street Exchange "
        "Redevelopment Project - $69,270,000. It relates to Capital Expenditure within the Water category. "
        "The matter had an initial filing on April 7, 2025 and a final filing on October 23, 2025. "
        "I found 13 Exhibits, 5 Key Documents, 21 Other Documents, and no Transcripts or Recordings. "
        "I downloaded 10 out of the 21 Other Documents and am attaching them as a ZIP here."
    )


def test_partial_lists_failures_and_attaches():
    e = compose(base(downloaded_files=FILES[:8], failed_downloads=[
        FailedDownload(doc_no="102675", title="Example Document"),
        FailedDownload(doc_no="102676", title="Other"),
    ]))
    assert e.attachment == "/tmp/x.zip"
    assert "I downloaded 8 out of the 21 Other Documents" in e.body
    assert "2 file(s) could not be downloaded after 3 attempts: 102675 – Example Document; 102676 – Other." in e.body


def test_no_documents_of_type_no_attachment():
    e = compose(base(document_type="Transcripts", downloaded_files=[], zip_file=None))
    assert e.attachment is None
    assert "There are no Transcripts for this matter, so there is no ZIP to attach." in e.body
    assert "I found 13 Exhibits" in e.body


def test_all_downloads_failed_uses_download_failed_template():
    e = compose(base(downloaded_files=[], zip_file=None, failed_downloads=[FailedDownload(doc_no="1", title="a")]))
    assert e.attachment is None
    assert "the download process failed" in e.body


@pytest.mark.parametrize("code,needle", [
    ("MISSING_MATTER_NUMBER", "couldn't find a matter number"),
    ("INVALID_MATTER_NUMBER", "isn't valid"),
    ("MISSING_DOCUMENT_TYPE", "couldn't find a document type"),
    ("INVALID_DOCUMENT_TYPE", "don't recognize the document type"),
    ("INVALID_INPUT", "more than one matter number"),
])
def test_parser_errors_with_only_email_and_code(code, needle):
    e = compose(ComposerInput(requester_email="u@example.com", error_code=code))
    assert needle in e.body and e.attachment is None
    assert e.subject == "UARB Documents Request"
    assert e.body.startswith("Hi User,\n\n")


@pytest.mark.parametrize("code,needle", [
    ("BROWSER_OPEN_FAILED", "couldn't reach the UARB website after several attempts, so I couldn't process M12205"),
    ("MATTER_NOT_FOUND", "couldn't find M12205 on the UARB website"),
    ("MATTER_PAGE_UNAVAILABLE", "I found M12205, but its page couldn't be loaded"),
])
def test_site_errors(code, needle):
    e = compose(ComposerInput(requester_email="u@e.com", matter_number="M12205", document_type="Exhibits", error_code=code))
    assert needle in e.body and e.attachment is None


def test_document_find_failed_with_and_without_summary():
    e = compose(base(error_code="DOCUMENT_FIND_FAILED", zip_file=None, downloaded_files=[]))
    assert "I found 13 Exhibits" in e.body and "However, I couldn't load the list of Other Documents" in e.body
    assert e.attachment is None
    e = compose(ComposerInput(requester_email="u@e.com", matter_number="M12205", document_type="Exhibits",
                              error_code="DOCUMENT_FIND_FAILED"))
    assert e.body == "Hi User,\n\nI couldn't load the list of Exhibits, so I couldn't download any files. Please try again later."


def test_zip_failed_template():
    e = compose(base(error_code="ZIP_CREATION_FAILED", zip_file=None))
    assert "I downloaded 10 out of the 21 Other Documents, but I couldn't create the ZIP file" in e.body
    assert e.attachment is None


def test_unknown_error_code_is_generic():
    e = compose(base(error_code="SOMETHING_NEW"))
    assert e.body == "Hi User,\n\nSomething went wrong while processing your request for M12205. Please try again later."
    assert e.attachment is None


def test_missing_metadata_omitted():
    md = Metadata(matter_number="M12205", title="Some Title", date_received="04/07/2025")
    e = compose(base(metadata=md))
    assert e.body.startswith("Hi User,\n\nM12205 is about the Some Title. The matter had an initial filing on April 7, 2025. I found")
    assert "relates to" not in e.body and "final filing" not in e.body
    e = compose(base(metadata=None, document_counts=None))
    assert e.body == "Hi User,\n\nI downloaded 10 out of the 0 Other Documents and am attaching them as a ZIP here."


def test_format_date():
    assert format_date("04/07/2025") == "April 7, 2025"
    assert format_date(None) is None and format_date("") is None
    assert format_date("garbage") == "garbage"


def test_format_counts_variants():
    z = dict.fromkeys(COUNTS, 0)
    assert format_counts(z) == "I found no Exhibits, Key Documents, Other Documents, Transcripts or Recordings."
    assert format_counts({**z, "Exhibits": 1}) == "I found 1 Exhibit and no Key Documents, Other Documents, Transcripts or Recordings."
    assert format_counts({k: 2 for k in z}) == "I found 2 Exhibits, 2 Key Documents, 2 Other Documents, 2 Transcripts, and 2 Recordings."
    assert format_counts({**z, "Exhibits": 3, "Recordings": 1}) == "I found 3 Exhibits, 1 Recording, and no Key Documents, Other Documents or Transcripts."


def test_split_zip_parts_produce_follow_up_emails(tmp_path):
    import zipfile
    parts = []
    for i in (1, 2, 3):
        p = tmp_path / f"M12205_Other_Documents_part{i}.zip"
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr(f"{i}.pdf", "x"); zf.writestr(f"{i}b.pdf", "y")
        parts.append(str(p))
    e = compose(base(zip_file=parts[0], zip_parts=parts))
    assert e.subject == "UARB Documents - M12205 (part 1 of 3)"
    assert e.attachment == parts[0]
    assert "split across 3 ZIPs sent as 3 separate emails; this is part 1 of 3." in e.body
    assert [x[0] for x in e.extra_parts] == ["UARB Documents - M12205 (part 2 of 3)", "UARB Documents - M12205 (part 3 of 3)"]
    assert [x[2] for x in e.extra_parts] == parts[1:]
    assert "part 2 of 3" in e.extra_parts[0][1] and "2 document(s)" in e.extra_parts[0][1]


def test_too_large_files_listed(tmp_path):
    big = tmp_path / "big.pdf"; big.write_bytes(b"x" * 5_000_000)
    tl = [DownloadedFile(doc_no="H-1", title="Application", local_path=str(big))]
    e = compose(base(too_large=tl, downloaded_files=FILES[:3] + tl))
    assert "am attaching 3 of them as a ZIP here." in e.body
    assert "1 file(s) were too large to attach to any email and are not included: H-1 – Application (5.0 MB)." in e.body
    assert e.attachment == "/tmp/x.zip"


def test_all_files_too_large_nothing_attached(tmp_path):
    big = tmp_path / "big.pdf"; big.write_bytes(b"x" * 5_000_000)
    tl = [DownloadedFile(doc_no="H-1", title="Application", local_path=str(big))]
    e = compose(base(zip_file=None, too_large=tl, downloaded_files=tl))
    assert e.attachment is None
    assert "every file is too large to send by email, so nothing is attached: H-1 – Application (5.0 MB)." in e.body


def test_confidential_note():
    e = compose(base(confidential_docs=["H-4(C)", "H-5(C)-i"]))
    assert "Note: 2 of the documents (H-4(C), H-5(C)-i) are marked Confidential" in e.body
    assert "one-page confidentiality notice" in e.body
    assert "Note:" not in compose(base()).body
