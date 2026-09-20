"""document_downloader: GO GET IT -> click the file in the popup -> save -> close popup."""
from __future__ import annotations

import logging
import os
import re
import time

from playwright.sync_api import Page

from .models import Document, DownloadedFile, DownloadResult, FailedDownload, PipelineError

log = logging.getLogger(__name__)

ATTEMPTS = 3
DOWNLOAD_TIMEOUT_MS = 60_000


def _safe_name(name: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "_", name).strip() or "download"


def _close_popup(page: Page) -> None:
    """Close the 'Download Files' popup if it is showing."""
    try:
        if page.get_by_text("Download Files", exact=True).count():
            close = page.get_by_role("button", name="Close", exact=True)
            if close.count() and close.first.is_visible():
                close.first.click()
            page.get_by_text("Download Files", exact=True).first.wait_for(state="hidden", timeout=10_000)
    except Exception as e:
        log.debug("close popup: %s", e)


def _row(page: Page, doc_no: str):
    return page.locator("tr.v-grid-row").filter(has=page.get_by_text(doc_no, exact=True)).first


def _download_one(page: Page, doc: Document, dest_dir: str) -> str:
    _close_popup(page)  # a leftover popup would block the row
    row = _row(page, doc.doc_no)
    row.get_by_role("button", name="GO GET IT").click(timeout=15_000)

    page.get_by_text("Download Files", exact=True).first.wait_for(timeout=20_000)
    label = f"{doc.doc_no}{doc.extension}"
    exact = page.get_by_role("button", name=label, exact=True)
    by_ext = page.get_by_role("button", name=re.compile(re.escape(doc.extension) + r"$", re.I))
    # The popup title can appear before its file button does, so wait for the button itself.
    deadline = time.time() + 30
    btn, expect_exact = None, False
    while time.time() < deadline and btn is None:
        if exact.count():
            btn, expect_exact = exact, True
        elif doc.extension and by_ext.count():  # popup names the file itself; fall back to any file button
            btn = by_ext
        else:
            page.wait_for_timeout(300)
    if btn is None:
        raise RuntimeError("file button not found in popup")

    with page.expect_download(timeout=DOWNLOAD_TIMEOUT_MS) as dl:
        btn.first.click()
    d = dl.value
    name = d.suggested_filename or label
    # Guard against the site handing back a different document than the row we clicked.
    if expect_exact and name.lower() != label.lower():
        raise RuntimeError(f"expected {label!r} but the site sent {name!r}")
    path = os.path.join(dest_dir, _safe_name(name))
    if os.path.exists(path):
        raise RuntimeError(f"{os.path.basename(path)} was already downloaded in this batch")
    d.save_as(path)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        if os.path.isfile(path):
            os.remove(path)  # so the retry is not mistaken for a duplicate
        raise RuntimeError("downloaded file is missing or empty")
    return path


def _download_with_retries(page: Page, doc: Document, dest_dir: str):
    """Return the saved path, or None after ATTEMPTS failed attempts."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            return _download_one(page, doc, dest_dir)
        except Exception as e:
            log.warning("download %s attempt %d/%d failed: %s", doc.doc_no, attempt, ATTEMPTS, e)
            _close_popup(page)
            page.wait_for_timeout(1000)
    return None


def download_documents(
    page: Page, matter_number: str, document_type: str, documents: list[Document], dest_dir: str
) -> DownloadResult:
    """Download each document (3 attempts each). One failure never stops the rest."""
    result = DownloadResult(matter_number=matter_number, document_type=document_type)
    if not documents:
        return result
    if page.is_closed():
        raise PipelineError("DOCUMENT_DOWNLOAD_FAILED", "browser page is closed")
    os.makedirs(dest_dir, exist_ok=True)

    for doc in documents:
        path = _download_with_retries(page, doc, dest_dir)
        _close_popup(page)  # the popup stays open after a download; clear it for the next row
        if path:
            result.downloaded_files.append(DownloadedFile(doc_no=doc.doc_no, title=doc.title, local_path=path))
        else:
            result.failed_downloads.append(FailedDownload(doc_no=doc.doc_no, title=doc.title))
    return result
