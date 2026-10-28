# tests

Functional tests for the scan. `test_scan.py` drives the scoring through
`httpx.MockTransport`, so the suite is **offline and deterministic** — it makes
no network calls and its results do not depend on any live site.

Run: `uv run --frozen pytest -q` from the kit root.
