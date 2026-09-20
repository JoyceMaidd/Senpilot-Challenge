"""browser_open: start a Playwright session and open the UARB Public Documents Database."""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from .models import PipelineError

log = logging.getLogger(__name__)

URL = "https://uarb.novascotia.ca/fmi/webd/UARB15"
# Tall on purpose: the results grid is virtualized, so a viewport that fits the first
# 10 rows keeps them all rendered and clickable without scrolling.
VIEWPORT = {"width": 1500, "height": 1600}
PAGE_LOAD_TIMEOUT_MS = 45_000


class BrowserSession:
    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        self._pw: Playwright = sync_playwright().start()
        try:
            kwargs = {"headless": headless}
            if proxy:
                kwargs["proxy"] = {"server": proxy}
            self.browser: Browser = self._pw.chromium.launch(**kwargs)
            self.context: BrowserContext = self.browser.new_context(
                viewport=VIEWPORT, accept_downloads=True
            )
            self.page: Page = self.context.new_page()
            self.page.set_default_timeout(30_000)
        except Exception:
            self._pw.stop()
            raise

    def close(self) -> None:
        for step in (self.context.close, self.browser.close, self._pw.stop):
            try:
                step()
            except Exception:
                pass

    def __enter__(self) -> "BrowserSession":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def open_search_page(page: Page) -> None:
    """Load the site and wait until the 'Go Directly to Matter' box is usable."""
    page.goto(URL, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
    page.locator("div.placeholder", has_text="eg M01234").wait_for(timeout=PAGE_LOAD_TIMEOUT_MS)


def browser_open(
    *, headless: Optional[bool] = None, retries: int = 3, backoff_s: float = 2.0
) -> BrowserSession:
    """Open the site, retrying up to `retries` times. Raises BROWSER_OPEN_FAILED."""
    if headless is None:
        headless = os.environ.get("HEADLESS", "1") != "0"
    proxy = os.environ.get("UARB_PROXY") or None
    last: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        session: Optional[BrowserSession] = None
        try:
            session = BrowserSession(headless=headless, proxy=proxy)
            open_search_page(session.page)
            return session
        except Exception as e:
            last = e
            log.warning("browser_open attempt %d/%d failed: %s", attempt, retries, e)
            if session:
                session.close()
            if attempt < retries:
                time.sleep(backoff_s * attempt)
    raise PipelineError("BROWSER_OPEN_FAILED", str(last))
