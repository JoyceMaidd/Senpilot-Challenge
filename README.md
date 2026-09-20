# UARB Regulatory Research Agent

An email agent for the Senpilot technical assignment. Email it a **matter number** and a **document
type**; it opens the Nova Scotia UARB Public Documents Database, downloads up to 10 documents of that
type, ZIPs them, and replies with the ZIP attached plus a summary of the matter.

> "Hi Agent, can you give me Other Documents files from M12205? Thanks!"

The agent's inbox is `regulatory_research@agentmail.to`. Anyone can email it.

## How it works

```
email ─► request_parser ─► browser_open ─► matter_search ─┬► metadata_extractor ─┐
 (AgentMail                                               ├► document_counter ───┤
  WebSocket)                                              └► document_finder     │
                                                                  │              │
                                       email_sender ◄─ email_composer ◄─ zip_tool ◄─ document_downloader
```

Each stage is one module in `uarb_agent/`, specified in `components/<name>.md`. `pipeline.py` wires
them together; any failure becomes an `error_code` that `email_composer` turns into a helpful reply,
so a sender always gets an answer.

| Module | Job |
|---|---|
| `request_parser` | LLM (OpenRouter) extracts the request; **regex fallback**; deterministic normalization and validation |
| `browser` (`browser_open`) | Playwright/Chromium session, 3 retries |
| `matter_search` | "Go Directly to Matter", detects "No Records Found" |
| `metadata_extractor` | Title, type, category, dates, outcome (read-only) |
| `document_counter` | Counts from the tab labels |
| `document_finder` | Opens the tab, takes the first 10 rows as displayed |
| `document_downloader` | GO GET IT → popup → download, 3 attempts per file |
| `zip_tool` | ZIP, split into parts if too big for email |
| `email_composer` | Reply text for every result and error |
| `email_sender`, `service` | AgentMail send/receive (WebSocket listener) |

## Setup

Requires Python 3.11+.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env        # then fill in the keys
```

`.env` needs `AGENTMAIL_API_KEY`, `AGENTMAIL_ADDRESS`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
(see `.env.example` for optional settings).

## Run

```bash
python -m uarb_agent
```

It subscribes to the inbox over a WebSocket (no public URL needed) and answers each incoming email.
Requests are handled one at a time. Stop it with Ctrl-C.

To try the pipeline without email:

```python
import tempfile
from uarb_agent.pipeline import handle_request
with tempfile.TemporaryDirectory() as d:
    print(handle_request("", "Other Documents from M12205", "me@example.com", d).body)
```

## Tests

```bash
pytest                       # unit tests, no network
RUN_LIVE=1 pytest -m live    # also drives the real UARB site (~1 minute)
```

## Behaviour worth knowing

- **Request parsing.** Accepts `M12205`, `m12205` or `12205`, and phrasings like "other docs" or
  "transcript". Hearings and Related Matters are not document types. More than one matter number or
  document type, a malformed number, or an irrelevant email gets a reply explaining what to send.
- **Email size limit.** AgentMail rejects sends over ~6 MB (measured: 4.3 MB of attachment sends,
  5.5 MB fails). Real filings are often larger, so the ZIP is split into `..._part1.zip`,
  `..._part2.zip`, … each sent as its own email ("part 2 of 3"). A single document too big for any
  email (some exhibits are 25–50 MB) is not attached; the reply lists it with its size.
- **Confidential exhibits.** For documents marked Confidential the UARB site serves a one-page
  confidentiality notice instead of the filing. They still count toward the 10 (the first 10 rows as
  displayed) and the reply says which ones they are.
- **Failures.** A file that fails is retried 3 times, then listed in the reply; the others still
  arrive. Site or parsing errors get their own explanatory reply.
- **Abuse protection.** Because the inbox is public: 10 requests per sender per hour (configurable),
  and the agent ignores its own mail, bounces and auto-generated messages so it cannot loop.
- **Data drift.** Matters keep receiving filings, so counts change (M12205 had 21 Other Documents when
  the assignment was written; it now has 43).

## How the website is automated

The site is FileMaker WebDirect, which has no stable element IDs or real `<input>`s. Notes for anyone
maintaining this:

- The matter box is a `contenteditable` div that only becomes editable ~1 s after it is clicked.
- Header fields have no labels in the DOM; they are matched to their label columns by position.
- The results grid is virtualized. The browser viewport is 1500×1600 so the first 10 rows are all
  rendered without scrolling; rows are ordered by on-screen position.
- Cell order inside a row differs between tabs, so rows are parsed by shape (date, extension) and
  position, not order.
- Some OK popups need a second, forced click to close.
- Downloads are verified: the file the site sends must match the row that was clicked (this once
  returned another document's file), must not overwrite another file in the batch, and must not be empty.
