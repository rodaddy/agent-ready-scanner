# services

The three working parts of a scan:

- `fetch.py` — raw HTTP retrieval. No JavaScript is executed, deliberately:
  the scan must see what an AI crawler sees.
- `checks.py` — the seven scored categories and the unscored probes. The
  weights and grade thresholds live here.
- `report.py` — renders the self-contained branded `report.html`.
