"""Helpers for WebDirect's modal popups."""
from __future__ import annotations

from playwright.sync_api import Page


def dismiss_ok_popup(page: Page, attempts: int = 3) -> bool:
    """Click the popup's OK button until it is gone. Returns True once dismissed.

    A plain first click often leaves the dialog open (WebDirect seems to use it to focus the
    button), so later attempts click with force=True.
    """
    ok = page.get_by_role("button", name="OK", exact=True)
    for attempt in range(attempts):
        if ok.count() == 0:
            return True
        try:
            ok.first.click(force=attempt > 0, timeout=5_000)
        except Exception:
            pass
        page.wait_for_timeout(1500)
    return ok.count() == 0
