"""service: listen on the AgentMail inbox and answer each request email.

Uses AgentMail's WebSocket stream, so no public URL is needed. One worker handles requests one
at a time (each drives a browser); a per-sender rate limit protects the public inbox.
"""
from __future__ import annotations

import logging
import os
import queue
import re
import shutil
import tempfile
import threading
import time
from collections import defaultdict, deque
from email.utils import parseaddr
from typing import Optional

from agentmail import AgentMail, MessageReceivedEvent, Subscribe, Subscribed

from .email_composer import compose
from .email_sender import send_email
from .models import ComposerInput, EmailContent
from .pipeline import handle_request

log = logging.getLogger(__name__)

_AUTOMATED = re.compile(r"(mailer-daemon|postmaster|no-?reply|do-?not-?reply|bounce)", re.I)


class RateLimiter:
    """At most `limit` requests per sender per `window_s`."""

    def __init__(self, limit: int, window_s: float = 3600.0):
        self.limit, self.window_s = limit, window_s
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, sender: str, now: Optional[float] = None) -> bool:
        now = time.time() if now is None else now
        q = self._hits[sender.lower()]
        while q and now - q[0] > self.window_s:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


def should_ignore(message, own_address: str) -> Optional[str]:
    """A reason to skip this message (our own mail, bounces, bulk/auto mail), or None."""
    sender = parseaddr(message.from_ or "")[1].lower()
    if not sender:
        return "no sender"
    if sender == own_address.lower():
        return "sent by this agent"
    if _AUTOMATED.search(sender):
        return "automated sender"
    headers = {k.lower(): str(v).lower() for k, v in (message.headers or {}).items()}
    if headers.get("auto-submitted", "no") != "no" or headers.get("precedence") in {"bulk", "junk", "list"}:
        return "auto-generated message"
    return None


class Service:
    def __init__(self, client: AgentMail, inbox: str, *, work_root: str, max_per_hour: int):
        self.client, self.inbox = client, inbox
        self.work_root = work_root
        os.makedirs(work_root, exist_ok=True)
        self.limiter = RateLimiter(max_per_hour)
        self.jobs: "queue.Queue" = queue.Queue()
        self._seen: deque = deque(maxlen=1000)

    # ------------------------------------------------------------------ one message
    def process(self, message) -> None:
        requester = parseaddr(message.from_ or "")[1]
        subject = message.subject or ""
        body = message.extracted_text or message.text or ""
        key = re.sub(r"[^A-Za-z0-9_.~-]", "", message.message_id or "")[:120] or str(time.time())
        log.info("processing %s from %s: %r", key, requester, subject[:80])

        work_dir = tempfile.mkdtemp(dir=self.work_root)
        try:
            if not self.limiter.allow(requester):
                log.warning("rate limit hit for %s", requester)
                content = EmailContent(
                    recipient=requester,
                    subject="UARB Documents Request",
                    body="Hi User,\n\nYou've reached the hourly request limit for this service. Please try again later.",
                )
            else:
                content = handle_request(subject, body, requester, work_dir)
            send_email(self.client, self.inbox, content, key=key)
            log.info("replied to %s (%s)", requester, content.subject)
        except Exception:
            log.exception("failed to answer %s", key)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    # ------------------------------------------------------------------ loops
    def _worker(self) -> None:
        while True:
            message = self.jobs.get()
            try:
                self.process(message)
            except Exception:
                log.exception("worker error")

    def _enqueue(self, message) -> None:
        if message.message_id in self._seen:
            return
        self._seen.append(message.message_id)
        reason = should_ignore(message, self.inbox)
        if reason:
            log.info("ignoring %s: %s", message.message_id, reason)
            return
        self.jobs.put(message)

    def run_forever(self) -> None:
        threading.Thread(target=self._worker, daemon=True, name="worker").start()
        backoff = 1.0
        while True:
            try:
                with self.client.websockets.connect() as socket:
                    socket.send_subscribe(Subscribe(inbox_ids=[self.inbox]))
                    for event in socket:
                        if isinstance(event, Subscribed):
                            log.info("listening on %s", self.inbox)
                            backoff = 1.0
                        elif isinstance(event, MessageReceivedEvent):
                            self._enqueue(event.message)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                log.warning("websocket dropped (%s); reconnecting in %.0fs", e, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
