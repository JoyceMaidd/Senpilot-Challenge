"""document_counter: read the per-type counts from the tab labels ('Other Documents - 43')."""
from __future__ import annotations

import re

from playwright.sync_api import Page

from .models import DOCUMENT_TYPES, PipelineError

_LABEL = re.compile(r"^(Exhibits|Key Documents|Other Documents|Transcripts|Recordings) - (\d+)$")


def read_tab_labels(page: Page) -> dict[str, int]:
    """{'Exhibits': 13, ...} for every type tab currently on the page."""
    found: dict[str, int] = {}
    for b in page.get_by_role("button", name=_LABEL).all():
        m = _LABEL.match(b.inner_text().strip())
        if m and b.is_visible():
            found[m.group(1)] = int(m.group(2))
    return found


def count_documents(page: Page) -> dict[str, int]:
    """Count for all five types. Types whose tab can't be read count as 0."""
    found = read_tab_labels(page)
    if not found:
        raise PipelineError("MATTER_PAGE_UNAVAILABLE", "no document tabs on page")
    return {t: found.get(t, 0) for t in DOCUMENT_TYPES}
