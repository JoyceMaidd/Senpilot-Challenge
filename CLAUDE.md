# UARB Regulatory Agent

Email agent: request (matter number + document type) → scrape UARB site with Playwright → ZIP → reply
via AgentMail. See README.md for the design; each pipeline stage has a spec in `components/<name>.md`
and an implementation in `uarb_agent/<name>.py`.

## Commands
- Run the agent: `.venv/bin/python -m uarb_agent`
- Unit tests: `.venv/bin/python -m pytest`
- Live site tests: `RUN_LIVE=1 .venv/bin/python -m pytest -m live`

## Rules
- Never commit `.env` or print its values. Keys: AgentMail, OpenRouter.
- Keep `uarb_agent/` module names in sync with `components/*.md`; update the spec when behaviour changes.
- The request parser must stay usable without the LLM (`PARSER=regex`), and validation stays deterministic.
- Site quirks (WebDirect timing, virtualized grid, popups) are documented in README.md; check there first.
- Live counts drift (M12205 changes as filings arrive); only assert exact counts for closed matters like M12383.
- Never run the listener with the agent's own address as a request sender: replies would loop.
