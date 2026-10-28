# agent_ready_scanner

The scanner package. Entry points: `cli.py` (the `agent-ready-scan` console
script declared in `pyproject.toml`) and `__main__.py` (the
`python -m agent_ready_scanner` path used when the kit runs without `uv`).

- `models/` — the typed result shapes.
- `services/` — the three working parts: fetching, checking, reporting.

Scoring weights and grade thresholds are part of the published method: a change
here changes what every past score meant. See `OPERATIONS-MANUAL.md` § 7.
