"""email_composer: build the reply email from a run's result or from an error_code."""
from __future__ import annotations

import os
import zipfile
from datetime import datetime
from typing import Optional

from .models import DOCUMENT_TYPES, ComposerInput, EmailContent

_SINGULAR = {
    "Exhibits": "Exhibit",
    "Key Documents": "Key Document",
    "Other Documents": "Other Document",
    "Transcripts": "Transcript",
    "Recordings": "Recording",
}

_TYPE_LIST = "Exhibits, Key Documents, Other Documents, Transcripts, or Recordings"

# error_code -> body (after "Hi User,"). {summary} lines are handled separately.
_ERRORS = {
    "MISSING_MATTER_NUMBER": "I couldn't find a matter number in your request. Please reply with one in the form M12205.",
    "INVALID_MATTER_NUMBER": "The matter number in your request isn't valid. Matter numbers are the letter M followed by 5 digits, such as M12205. Please check it and try again.",
    "MISSING_DOCUMENT_TYPE": f"I couldn't find a document type in your request. Please choose one of: {_TYPE_LIST}.",
    "INVALID_DOCUMENT_TYPE": f"I don't recognize the document type in your request. Please choose one of: {_TYPE_LIST}.",
    "INVALID_INPUT": "I couldn't understand your request, or it contained more than one matter number. Please send one matter number and one document type, for example: \"Can you give me Other Documents files from M12205?\"",
    "BROWSER_OPEN_FAILED": "I couldn't reach the UARB website after several attempts, so I couldn't process {matter}. Please try again later.",
    "MATTER_NOT_FOUND": "I couldn't find {matter} on the UARB website. Please check the matter number and try again.",
    "MATTER_PAGE_UNAVAILABLE": "I found {matter}, but its page couldn't be loaded, so I couldn't retrieve its details or documents. Please try again later.",
}
# These start with the matter summary when we have one.
_ERRORS_WITH_SUMMARY = {
    "DOCUMENT_FIND_FAILED": "However, I couldn't load the list of {type}, so I couldn't download any files. Please try again later.",
    "DOCUMENT_DOWNLOAD_FAILED": "I found the {type}, but the download process failed, so I have no files to send. Please try again later.",
    "ZIP_CREATION_FAILED": "I downloaded {n} out of the {total} {type}, but I couldn't create the ZIP file, so nothing is attached. Please try again later.",
}
_GENERIC = "Something went wrong while processing your request for {matter}. Please try again later."


def format_date(s: Optional[str]) -> Optional[str]:
    """'04/07/2025' -> 'April 7, 2025'. Unparseable values are returned unchanged."""
    if not s:
        return None
    try:
        d = datetime.strptime(s.strip(), "%m/%d/%Y")
    except ValueError:
        return s
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def format_counts(counts: dict[str, int]) -> str:
    """'I found 13 Exhibits, 5 Key Documents, and no Transcripts or Recordings.'"""
    present, absent = [], []
    for t in DOCUMENT_TYPES:
        n = counts.get(t, 0)
        if n:
            present.append(f"{n} {_SINGULAR[t] if n == 1 else t}")
        else:
            absent.append(t)
    parts = list(present)
    if absent:
        tail = absent[0] if len(absent) == 1 else ", ".join(absent[:-1]) + " or " + absent[-1]
        parts.append(f"no {tail}")
    if len(parts) == 1:
        joined = parts[0]
    elif len(parts) == 2:
        joined = f"{parts[0]} and {parts[1]}"
    else:
        joined = ", ".join(parts[:-1]) + ", and " + parts[-1]
    return f"I found {joined}."


def build_summary(matter: Optional[str], md, counts: Optional[dict[str, int]]) -> Optional[str]:
    """The shared matter summary. Sentences whose data is missing are left out."""
    sentences = []
    if md is not None and matter and md.title:
        about = md.title + (f" - {md.description}" if md.description else "")
        sentences.append(f"{matter} is about the {about}.")
    if md is not None:
        # The site lists Type (e.g. Water) above Category (e.g. Capital Expenditure Approvals).
        if md.category and md.type:
            sentences.append(f"It relates to {md.category} within the {md.type} category.")
        elif md.category:
            sentences.append(f"It relates to {md.category}.")
        elif md.type:
            sentences.append(f"It is in the {md.type} category.")
        start, end = format_date(md.date_received), format_date(md.decision_date)
        if start and end:
            sentences.append(f"The matter had an initial filing on {start} and a final filing on {end}.")
        elif start:
            sentences.append(f"The matter had an initial filing on {start}.")
        elif end:
            sentences.append(f"The matter had a final filing on {end}.")
    if counts is not None:
        sentences.append(format_counts(counts))
    return " ".join(sentences) or None


def compose(inp: ComposerInput) -> EmailContent:
    matter = inp.matter_number
    dtype = inp.document_type or "documents"
    subject = f"UARB Documents - {matter}" if matter else "UARB Documents Request"
    ph = {
        "matter": matter or "your request",
        "type": dtype,
        "n": len(inp.downloaded_files),
        "total": (inp.document_counts or {}).get(inp.document_type or "", 0),
        "failed": len(inp.failed_downloads),
    }
    summary = build_summary(matter, inp.metadata, inp.document_counts)

    def wrap(text: str) -> str:
        return f"Hi User,\n\n{text}"

    code = inp.error_code
    # A run where documents existed but every download failed has no error_code of its own.
    if not code and inp.zip_file is None and inp.failed_downloads and not inp.downloaded_files:
        code = "DOCUMENT_DOWNLOAD_FAILED"

    if code:
        if code in _ERRORS_WITH_SUMMARY:
            text = _ERRORS_WITH_SUMMARY[code].format(**ph)
            body = wrap(f"{summary} {text}" if summary else _strip_however(text))
        elif code in _ERRORS:
            body = wrap(_ERRORS[code].format(**ph))
        else:
            body = wrap(_GENERIC.format(**ph))
        return EmailContent(recipient=inp.requester_email, subject=subject, body=body, attachment=None)

    if inp.zip_file is None and inp.too_large:
        # Documents were downloaded but every one is too big to send by email.
        text = (
            f"I downloaded {ph['n']} out of the {ph['total']} {dtype}, but every file is too large to send "
            f"by email, so nothing is attached: {_describe_files(inp.too_large)}."
        )
        body = wrap(f"{summary} {text}" if summary else text)
        return EmailContent(recipient=inp.requester_email, subject=subject, body=body, attachment=None)

    if inp.zip_file is None:
        # Nothing to attach: the requested tab had no documents.
        text = f"There are no {dtype} for this matter, so there is no ZIP to attach."
        body = wrap(f"{summary} {text}" if summary else text)
        return EmailContent(recipient=inp.requester_email, subject=subject, body=body, attachment=None)

    parts = inp.zip_parts or [inp.zip_file]
    k = len(parts)
    attached = ph["n"] - len(inp.too_large)
    if inp.too_large:
        text = f"I downloaded {ph['n']} out of the {ph['total']} {dtype} and am attaching {attached} of them as a ZIP here."
    else:
        text = f"I downloaded {ph['n']} out of the {ph['total']} {dtype} and am attaching them as a ZIP here."
    if k > 1:
        text += (
            f" Together they are too large for one email, so they are split across {k} ZIPs sent as {k} "
            f"separate emails; this is part 1 of {k}."
        )
    if inp.too_large:
        text += (
            f" {len(inp.too_large)} file(s) were too large to attach to any email and are not included: "
            f"{_describe_files(inp.too_large)}."
        )
    if inp.confidential_docs:
        text += (
            f" Note: {len(inp.confidential_docs)} of the documents ({', '.join(inp.confidential_docs)}) are marked "
            f"Confidential, and the UARB site provides only a one-page confidentiality notice for them, not the "
            f"filing itself."
        )
    if inp.failed_downloads:
        listing = "; ".join(f"{f.doc_no} – {f.title}" for f in inp.failed_downloads)
        text += f" {ph['failed']} file(s) could not be downloaded after 3 attempts: {listing}."
    body = wrap(f"{summary} {text}" if summary else text)

    extra = []
    for i, path in enumerate(parts[1:], start=2):
        extra.append((
            f"{subject} (part {i} of {k})",
            wrap(f"This is part {i} of {k} of the {dtype} ZIP for {matter or 'your request'}. "
                 f"It contains {_zip_count(path)} document(s)."),
            path,
        ))
    if k > 1:
        subject = f"{subject} (part 1 of {k})"
    return EmailContent(
        recipient=inp.requester_email, subject=subject, body=body, attachment=parts[0], extra_parts=extra
    )


def _size_mb(path: str) -> str:
    try:
        return f"{os.path.getsize(path) / 1e6:.1f} MB"
    except OSError:
        return "size unknown"


def _describe_files(files) -> str:
    return "; ".join(f"{f.doc_no} – {f.title} ({_size_mb(f.local_path)})" for f in files)


def _zip_count(path: str) -> int:
    try:
        with zipfile.ZipFile(path) as zf:
            return len(zf.namelist())
    except Exception:
        return 0


def _strip_however(text: str) -> str:
    """Without a summary the 'However, ...' sentence would dangle, so drop the lead-in."""
    if text.startswith("However, "):
        text = text[len("However, "):]
        return text[0].upper() + text[1:]
    return text
