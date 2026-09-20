"""matter_search: enter a matter number in 'Go Directly to Matter' and open its page."""
from __future__ import annotations

import logging
import re
import time

from playwright.sync_api import Page

from .models import PipelineError
from .popups import dismiss_ok_popup

log = logging.getLogger(__name__)

TAB_RE = re.compile(r"^(Exhibits|Key Documents|Other Documents|Transcripts|Recordings) - \d+$")
SEARCH_TIMEOUT_S = 30


def _go_directly_field(page: Page):
    # WebDirect draws a placeholder <div>; the real editable <div class="text"> is its sibling.
    ph = page.locator("div.placeholder", has_text="eg M01234")
    return ph.locator("xpath=..").locator("div.text[tabindex='0']")


def _go_directly_search_button(page: Page, field):
    """The page has several 'Search' buttons; pick the one right of the matter box."""
    fb = field.bounding_box()
    candidates = [b for b in page.get_by_role("button", name="Search", exact=True).all() if b.is_visible()]
    if not fb or not candidates:
        raise PipelineError("MATTER_SEARCH_FAILED", "search button not found")

    def dist(b):
        bb = b.bounding_box()
        return abs(bb["y"] - fb["y"]) + abs(bb["x"] - (fb["x"] + fb["width"]))

    return min(candidates, key=dist)


def _tab_visible(page: Page) -> bool:
    return any(b.is_visible() for b in page.get_by_role("button", name=TAB_RE).all())


def _no_records_ok_button(page: Page):
    """The 'No Records Found' popup's OK button, or None."""
    if page.get_by_text("No Records Found").count() == 0:
        return None
    ok = page.get_by_role("button", name="OK", exact=True)
    return ok.first if ok.count() and ok.first.is_visible() else None


def search_matter(page: Page, matter_number: str) -> str:
    """Search for the matter. Returns matter_number; the page is left on the matter page."""
    try:
        field = _go_directly_field(page)
        field.wait_for(timeout=30_000)
        field.click()
        page.wait_for_timeout(1000)  # the field only becomes editable a moment after focus
        page.keyboard.insert_text(matter_number)
        page.wait_for_timeout(300)
        _go_directly_search_button(page, field).click()
    except PipelineError:
        raise
    except Exception as e:
        raise PipelineError("MATTER_SEARCH_FAILED", str(e))

    deadline = time.time() + SEARCH_TIMEOUT_S
    while time.time() < deadline:
        if _tab_visible(page):
            return matter_number
        if _no_records_ok_button(page):
            if not dismiss_ok_popup(page):
                log.warning("'No Records Found' popup still showing after clicking OK")
            raise PipelineError("MATTER_NOT_FOUND", matter_number)
        page.wait_for_timeout(500)
    raise PipelineError("MATTER_SEARCH_FAILED", "timed out waiting for results")
