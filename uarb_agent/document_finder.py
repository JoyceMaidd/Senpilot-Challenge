"""document_finder: open the requested document-type tab and list up to 10 documents."""
from __future__ import annotations

import logging
import re
import time

from playwright.sync_api import Page

from .document_counter import read_tab_labels
from .models import DOCUMENT_TYPES, MAX_DOCUMENTS, Document, PipelineError
from .popups import dismiss_ok_popup

log = logging.getLogger(__name__)

CLICK_ATTEMPTS = 3

_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_EXT = re.compile(r"^\.[A-Za-z0-9]{1,6}$")
_BUTTON_TEXT = {"Preview", "GO GET IT"}

# Leaf text with position for every rendered grid row that has a GO GET IT button.
_ROWS_JS = """
() => [...document.querySelectorAll('tr.v-grid-row')]
  .filter(tr => /GO GET IT/.test(tr.innerText))
  .map(tr => {
    const y = tr.getBoundingClientRect().y;
    const leaves = [];
    for (const e of tr.querySelectorAll('div, span, button, a')) {
      const t = (e.innerText || '').trim();
      if (!t || [...e.children].some(c => (c.innerText || '').trim() === t) || e.children.length > 3) continue;
      const r = e.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      leaves.push({text: t, x: r.x, y: r.y});
    }
    return {y, leaves};
  })
"""


def parse_row(leaves: list[dict], document_type: str):
    """Turn one row's positioned texts into a Document (None if it doesn't look like one).

    The cell order in the DOM differs between tabs, so identify cells by shape/position:
    extension and date by pattern, then of what remains the right-most is the title and the
    two left-column cells are Doc No (upper) and Security (lower).
    """
    texts = [l for l in leaves if l["text"] not in _BUTTON_TEXT]
    # de-duplicate overlapping elements carrying the same text
    seen, uniq = set(), []
    for l in texts:
        k = (l["text"], round(l["x"]), round(l["y"]))
        if k not in seen:
            seen.add(k)
            uniq.append(l)
    ext = next((l["text"] for l in uniq if _EXT.match(l["text"])), "")
    date = next((l["text"] for l in uniq if _DATE.match(l["text"])), "")
    rest = [l for l in uniq if not _EXT.match(l["text"]) and not _DATE.match(l["text"])]
    if len(rest) < 2:
        return None
    if len(rest) >= 3:
        title_leaf = max(rest, key=lambda l: l["x"])
        left = sorted((l for l in rest if l is not title_leaf), key=lambda l: l["y"])
        title = title_leaf["text"]
    else:
        left, title = sorted(rest, key=lambda l: l["y"]), ""
    doc_no, security = left[0]["text"], left[1]["text"]
    return Document(
        doc_no=doc_no, title=re.sub(r"\s+", " ", title).strip(), extension=ext, date=date,
        security=security, download_reference=f"{document_type}:{doc_no}",
    )


def _wait_for_list(page: Page, want_rows: int, timeout_s: float) -> str:
    """'loaded', 'empty' (No Matching Records popup, dismissed) or 'timeout'."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if page.get_by_text("No Matching Records").count():
            dismiss_ok_popup(page)
            return "empty"
        # Not every tab shows a "Found Count" line, so wait for the rows themselves.
        if page.get_by_role("button", name="GO GET IT").count() >= want_rows:
            return "loaded"
        page.wait_for_timeout(400)
    return "timeout"


def _tab_button(page: Page, document_type: str):
    return page.get_by_role("button", name=re.compile(rf"^{re.escape(document_type)} - \d+$"))


def find_documents(page: Page, document_type: str) -> list[Document]:
    """List up to 10 documents, in displayed order, and leave the tab open for downloading."""
    if document_type not in DOCUMENT_TYPES:
        raise PipelineError("DOCUMENT_FIND_FAILED", f"unsupported document type {document_type!r}")
    try:
        counts = read_tab_labels(page)
        if document_type not in counts:
            raise PipelineError("DOCUMENT_FIND_FAILED", "tab not found")
        total = counts[document_type]
        if total == 0:
            return []  # don't click a tab we know is empty

        # WebDirect occasionally ignores a click made while the page is still settling, so
        # re-click the tab if the list has not appeared.
        for _ in range(CLICK_ATTEMPTS):
            _tab_button(page, document_type).first.click()
            outcome = _wait_for_list(page, min(total, MAX_DOCUMENTS), timeout_s=12)
            if outcome == "empty":
                return []
            if outcome == "loaded":
                break
        else:
            raise PipelineError("DOCUMENT_FIND_FAILED", "list did not load")
        page.wait_for_timeout(1000)  # let the grid finish rendering

        rows = page.evaluate(_ROWS_JS)
    except PipelineError:
        raise
    except Exception as e:
        raise PipelineError("DOCUMENT_FIND_FAILED", str(e))

    rows.sort(key=lambda r: r["y"])  # displayed order; the grid only renders a window of rows
    docs: list[Document] = []
    for r in rows:
        d = parse_row(r["leaves"], document_type)
        if d and d.doc_no not in {x.doc_no for x in docs}:
            docs.append(d)
        if len(docs) == MAX_DOCUMENTS:
            break
    if not docs:
        raise PipelineError("DOCUMENT_FIND_FAILED", "no rows could be read")
    return docs
