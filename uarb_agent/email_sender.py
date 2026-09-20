"""email_sender: deliver an EmailContent (and any extra ZIP parts) through AgentMail."""
from __future__ import annotations

import base64
import logging
import os
import time
from typing import Optional

from .models import EmailContent

log = logging.getLogger(__name__)

SEND_ATTEMPTS = 3


def _attachment(path: str) -> dict:
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return {"content": data, "filename": os.path.basename(path), "content_type": "application/zip"}


def _send_once(client, inbox: str, to: str, subject: str, body: str, attachment: Optional[str], key: str) -> None:
    kwargs = {"to": [to], "subject": subject, "text": body, "idempotency_key": key}
    if attachment:
        kwargs["attachments"] = [_attachment(attachment)]
    client.inboxes.messages.send(inbox, **kwargs)


def _send_with_retries(client, inbox, to, subject, body, attachment, key) -> None:
    last: Optional[Exception] = None
    for attempt in range(1, SEND_ATTEMPTS + 1):
        try:
            _send_once(client, inbox, to, subject, body, attachment, key)
            return
        except Exception as e:
            last = e
            log.warning("send attempt %d/%d failed: %s", attempt, SEND_ATTEMPTS, str(e)[:300])
            status = getattr(e, "status_code", None)
            if status and 400 <= status < 500 and status != 429:
                break  # the request itself is wrong; retrying cannot help
            time.sleep(2 * attempt)
    if attachment:  # last resort: tell the user something rather than nothing
        note = "\n\n(I could not deliver the attached ZIP because the email service rejected it. Please try again later.)"
        _send_once(client, inbox, to, subject, body + note, None, key + "-noattach")
        return
    raise RuntimeError(f"could not send email: {last}")


def send_email(client, inbox: str, content: EmailContent, *, key: str) -> None:
    """Send the main email, then each extra ZIP part. `key` makes retries idempotent."""
    _send_with_retries(client, inbox, content.recipient, content.subject, content.body, content.attachment, key)
    for i, (subject, body, path) in enumerate(content.extra_parts, start=2):
        _send_with_retries(client, inbox, content.recipient, subject, body, path, f"{key}-part{i}")
