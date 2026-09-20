"""metadata_extractor: read the matter header (read-only; never clicks or navigates).

The header has no per-field DOM labels, so values are matched to label columns by
position: a value belongs to the right-most label whose x is at or left of it.
Type/Category and Matter No/Status are stacked pairs (first is the top one).
"""
from __future__ import annotations

import re
from typing import Optional

from playwright.sync_api import Page

from .models import Metadata, PipelineError

# Collects the visible leaf-ish text elements above the document tabs.
_JS = """
() => {
  const tab = [...document.querySelectorAll('button')]
    .find(b => /^(Exhibits|Key Documents|Other Documents|Transcripts|Recordings) - \\d+$/.test(b.innerText.trim()));
  if (!tab) return null;
  const limit = tab.getBoundingClientRect().top;
  const out = [];
  for (const e of document.querySelectorAll('div, span, button, a')) {
    const t = (e.innerText || '').trim();
    if (!t) continue;
    // skip wrappers: keep the element only if no child element carries the same text
    if ([...e.children].some(c => (c.innerText || '').trim() === t)) continue;
    if (e.children.length > 3) continue;
    const r = e.getBoundingClientRect();
    if (r.height === 0 || r.width === 0 || r.bottom > limit || r.top < 60) continue;
    out.push({text: t, x: r.x, y: r.y, w: r.width, h: r.height});
  }
  return out;
}
"""

# label text -> field. 'Decision Date' becomes 'Date Final Submission(s)' once a tab is open.
_LABELS = [
    (re.compile(r"^Matter No\b"), "matter"),
    (re.compile(r"^Title - Description$"), "title"),
    (re.compile(r"^Type\b"), "type"),
    (re.compile(r"^Date Received$"), "date_received"),
    (re.compile(r"^(Decision Date|Date Final\s*Submissions?)$", re.S), "decision_date"),
    (re.compile(r"^Outcome$"), "outcome"),
]
_X_TOL = 25


def _clean(s: Optional[str]) -> Optional[str]:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s or None


def extract_metadata(page: Page, matter_number: str) -> Metadata:
    try:
        items = page.evaluate(_JS)
    except Exception as e:
        raise PipelineError("MATTER_PAGE_UNAVAILABLE", str(e))
    if items is None:
        raise PipelineError("MATTER_PAGE_UNAVAILABLE", "matter header not found")

    columns: list[tuple[float, str]] = []   # (x of label, field key)
    label_tops: list[float] = []
    values = []
    for it in items:
        key = next((k for rx, k in _LABELS if rx.match(re.sub(r"\s+", " ", it["text"]))), None)
        if key and it["h"] < 40:
            columns.append((it["x"], key))
            label_tops.append(it["y"])
        else:
            values.append(it)
    if not columns:
        raise PipelineError("MATTER_PAGE_UNAVAILABLE", "no header labels found")
    # Values sit below the label row; this drops the page heading, which shares the left edge.
    label_bottom = min(label_tops) + 5
    values = [v for v in values if v["y"] > label_bottom]

    # If Type/Category or Matter/Status labels are listed as one block ("Type\nCategory") the
    # regexes above catch it via '^Type\b'; a 'Status'/'Category' line on its own is ignored.
    columns.sort()
    by_col: dict[str, list[dict]] = {}
    for v in values:
        owner = None
        for x, key in columns:
            if x <= v["x"] + _X_TOL:
                owner = key
        if owner:
            by_col.setdefault(owner, []).append(v)
    for key, lst in by_col.items():
        lst.sort(key=lambda v: v["y"])
        deduped: list[dict] = []
        for v in lst:  # overlapping elements can carry the same text
            if not deduped or v["text"] != deduped[-1]["text"] or abs(v["y"] - deduped[-1]["y"]) > 10:
                deduped.append(v)
        by_col[key] = deduped

    def nth(key: str, i: int) -> Optional[str]:
        lst = by_col.get(key, [])
        return _clean(lst[i]["text"]) if len(lst) > i else None

    full_title = nth("title", 0)
    title, description = full_title, None
    if full_title:
        m = re.match(r"^(.*\S)\s+-\s+(\$[\d,.]+)$", full_title)  # "... Project - $69,275,000"
        if m:
            title, description = m.group(1), m.group(2)

    return Metadata(
        matter_number=matter_number,
        status=nth("matter", 1),
        title=title,
        description=description,
        type=nth("type", 0),
        category=nth("type", 1),
        date_received=nth("date_received", 0),
        decision_date=nth("decision_date", 0),
        outcome=nth("outcome", 0),
    )
