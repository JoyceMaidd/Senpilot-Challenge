"""Tests against the real UARB site. Run with:  RUN_LIVE=1 pytest -m live

Counts for M12205 change as filings arrive, so only M12383 (closed) is asserted exactly.
"""
import os
import re
import zipfile

import pytest

from uarb_agent.browser import browser_open, open_search_page
from uarb_agent.document_counter import count_documents
from uarb_agent.document_downloader import download_documents
from uarb_agent.document_finder import find_documents
from uarb_agent.matter_search import search_matter
from uarb_agent.metadata_extractor import extract_metadata
from uarb_agent.models import PipelineError
from uarb_agent.zip_tool import make_zip

pytestmark = pytest.mark.live


@pytest.fixture()
def session():
    with browser_open() as s:
        yield s


def open_matter(s, m):
    search_matter(s.page, m)
    s.page.get_by_text(m, exact=True).first.wait_for(timeout=10_000)
    return s.page


def test_search_existing_and_missing(session):
    open_matter(session, "M12383")
    open_search_page(session.page)  # back to the search page in the same session
    with pytest.raises(PipelineError) as e:
        search_matter(session.page, "M99999")
    assert e.value.error_code == "MATTER_NOT_FOUND"
    # the popup was dismissed, so the session is still usable
    open_matter(session, "M12383")


def test_counts_and_metadata_for_known_matter(session):
    page = open_matter(session, "M12383")
    assert count_documents(page) == {
        "Exhibits": 6, "Key Documents": 4, "Other Documents": 18, "Transcripts": 0, "Recordings": 0}
    md = extract_metadata(page, "M12383")
    assert md.title.startswith("Municipal Boundary - Town of Amherst")
    assert (md.type, md.category) == ("Municipal Boundaries", "Other")
    assert (md.date_received, md.decision_date, md.outcome) == ("07/10/2025", "11/28/2025", "Allowed/Approved")


def test_finder_caps_at_ten_in_displayed_order(session):
    docs = find_documents(open_matter(session, "M12383"), "Other Documents")
    assert len(docs) == 10 and len({d.doc_no for d in docs}) == 10
    assert all(d.download_reference == f"Other Documents:{d.doc_no}" for d in docs)


def test_finder_fewer_than_ten_and_exhibit_fields(session):
    docs = find_documents(open_matter(session, "M12383"), "Exhibits")
    assert len(docs) == 6
    assert all(re.match(r"^\d{2}/\d{2}/\d{4}$", d.date) and d.extension for d in docs)


def test_finder_zero_count_returns_empty_without_clicking(session):
    assert find_documents(open_matter(session, "M12383"), "Transcripts") == []


def test_finder_rejects_hearings(session):
    with pytest.raises(PipelineError) as e:
        find_documents(open_matter(session, "M12383"), "Hearings")
    assert e.value.error_code == "DOCUMENT_FIND_FAILED"


def test_download_and_zip_key_documents(session, tmp_path):
    page = open_matter(session, "M12383")
    docs = find_documents(page, "Key Documents")
    r = download_documents(page, "M12383", "Key Documents", docs, str(tmp_path / "files"))
    assert len(r.downloaded_files) == 4 and r.failed_downloads == []
    assert all(os.path.getsize(f.local_path) > 0 for f in r.downloaded_files)
    z = make_zip(r, str(tmp_path / "zips"))
    assert z.zip_file.endswith("M12383_Key_Documents.zip")
    assert len(zipfile.ZipFile(z.zip_file).namelist()) == 4
