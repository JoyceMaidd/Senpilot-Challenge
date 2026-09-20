"""pipeline: run one request end to end and return the email to send.

request_parser -> browser_open -> matter_search -> metadata_extractor + document_counter
-> document_finder -> document_downloader -> zip_tool -> email_composer
Any component failure becomes an error_code that email_composer turns into the reply.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from .browser import BrowserSession, browser_open
from .document_counter import count_documents
from .document_downloader import download_documents
from .document_finder import find_documents
from .email_composer import compose
from .matter_search import search_matter
from .metadata_extractor import extract_metadata
from .models import ComposerInput, EmailContent, PipelineError
from .request_parser import parse_request
from .zip_tool import make_zip

log = logging.getLogger(__name__)


def handle_request(
    subject: str,
    body: str,
    requester_email: str,
    work_dir: str,
    *,
    headless: Optional[bool] = None,
    parser_mode: Optional[str] = None,
) -> EmailContent:
    """Never raises: every failure ends up as an error email. Files are written under work_dir."""
    parsed = parse_request(subject, body, requester_email, mode=parser_mode)
    if isinstance(parsed, dict):
        return compose(ComposerInput(**parsed))

    inp = ComposerInput(
        requester_email=parsed.requester_email,
        matter_number=parsed.matter_number,
        document_type=parsed.document_type,
    )
    session: Optional[BrowserSession] = None
    try:
        session = browser_open(headless=headless)
        page = session.page
        search_matter(page, inp.matter_number)
        # search_matter returns as soon as the tabs show; make sure the header has rendered too.
        try:
            page.get_by_text(inp.matter_number, exact=True).first.wait_for(timeout=10_000)
        except Exception:
            raise PipelineError("MATTER_PAGE_UNAVAILABLE", "matter header did not render")

        inp.metadata = extract_metadata(page, inp.matter_number)
        inp.document_counts = count_documents(page)

        docs = find_documents(page, inp.document_type)
        dl = download_documents(
            page, inp.matter_number, inp.document_type, docs, os.path.join(work_dir, "files")
        )
        inp.downloaded_files = dl.downloaded_files
        inp.failed_downloads = dl.failed_downloads
        security = {d.doc_no: d.security for d in docs}
        inp.confidential_docs = [
            f.doc_no for f in dl.downloaded_files if security.get(f.doc_no, "Public").lower() != "public"
        ]

        z = make_zip(dl, os.path.join(work_dir, "zips"))
        inp.zip_file, inp.zip_parts, inp.too_large = z.zip_file, z.zip_parts, z.too_large
        inp.error_code = z.error_code
    except PipelineError as e:
        log.warning("request for %s failed: %s", parsed.matter_number, e)
        inp.error_code = e.error_code
    except Exception:
        log.exception("unexpected error handling %s", parsed.matter_number)
        inp.error_code = "UNEXPECTED_ERROR"
    finally:
        if session:
            session.close()
    return compose(inp)
