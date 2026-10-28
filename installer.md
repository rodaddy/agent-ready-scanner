# Installer — Agent-Ready Scanner

**Who runs this:** an rTech operator, on an rTech machine. This kit is delivery
ladder rung 4, rTech-internal only (`kits/KIT-STANDARD.md` § Delivery-surface
ladder). A client is never asked to run a command, open Terminal, or install a
runtime. The client receives the finished `report.html`.

**What the kit does for the client's people:** it reads a website the way an AI
agent reads it and writes down, category by category, what an agent cannot find.
It hands the client's own marketing or web person a specific, ordered list of
fixes they can make. It does not touch the site, does not publish anything, and
does not replace the person who owns the site — it tells them where to look.

Every command below is written out in full. Run them in order. Stop at the first
one that does not do what this file says it does, and read Section 6.

---

## Section 1 — Check the runtime floor

The scanner requires **Python 3.14 or newer** (`pyproject.toml`
`requires-python = ">=3.14"`, `.python-version` pins `3.14`).

Check what you have:

```bash
python3.14 --version
```

Expected: `Python 3.14.x`. If the command is not found, and you have `uv`
installed, skip to Section 2 — `uv` fetches its own interpreter and you do not
need a system 3.14. If you have neither, install `uv` first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then open a new Terminal window so `uv` is on your `PATH`, and check it:

```bash
uv --version
```

## Section 2 — Get into the kit folder

```bash
cd ~/Downloads/agent-ready-scanner
```

Substitute the path where you actually unzipped the kit. Confirm you are in the
right place — this must list `pyproject.toml`, `uv.lock`, `requirements.txt`,
`src/`, and `tests/`:

```bash
ls
```

## Section 3 — Install the dependencies

### 3A — With `uv` (preferred)

`uv.lock` pins every dependency to an exact version, so this install is
identical on every machine:

```bash
uv sync --frozen
```

Expected: `uv` reports the resolved packages and creates `.venv/` in this
folder. `--frozen` means it will REFUSE to silently re-resolve the lockfile; if
it errors saying the lock is out of date, that is a real finding — report it,
do not drop the flag to make it pass.

### 3B — Without `uv`, plain Python

Use this on a machine where `uv` is unavailable. `requirements.txt` is generated
from the same lockfile, so the versions match 3A:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

Expected: pip reports `Successfully installed httpx-… beautifulsoup4-…
pydantic-… loguru-…`.

## Section 4 — Verify the install on the target you actually care about

**Do not verify on shipped example data** (`kits/KIT-STANDARD.md` § 4.10,
own-data verification). The folder under `runs/` is a past rTech scan kept
as a reference for what the output looks like — it is not the verification.
Run the scan against the real site you were asked about, right now.

With `uv` (3A):

```bash
uv run agent-ready-scan --url https://the-real-client-site.com --out runs/verify
```

Without `uv` (3B):

```bash
.venv/bin/python -m agent_ready_scanner --url https://the-real-client-site.com --out runs/verify
```

Expected: the command writes two files and prints where they went:

```bash
ls runs/verify
```

must show `results.json` and `report.html`. Open the report:

```bash
open runs/verify/report.html
```

The install is complete when you have looked at a report for a real site and its
score, grade, and per-category rows are populated. If you have no real target in
hand yet, the install is **UNVERIFIED** — say so and stop, rather than scanning
a placeholder to make this section end.

## Section 5 — Scan a list of sites

Input is a CSV with exactly the columns `vertical,name,url`.
`targets/example.csv` is the shape to copy.

```bash
uv run agent-ready-scan targets/example.csv --out runs/2026-09-10-batch
```

Without `uv`:

```bash
.venv/bin/python -m agent_ready_scanner targets/example.csv --out runs/2026-09-10-batch
```

One `results.json` and one `report.html` cover the whole batch.

## Section 6 — When a step fails

- **`python3.14: command not found`** — you do not have Python 3.14. Use `uv`
  (Section 1) rather than hunting for a system interpreter.
- **`uv sync --frozen` errors that the lockfile is out of date** — the checked-in
  `uv.lock` disagrees with `pyproject.toml`. Report it; do not run bare
  `uv sync`, which rewrites the lock and hides the disagreement.
- **`ModuleNotFoundError` for a package that is plainly in the lock** — the
  `.venv` in this folder is bound to a path it no longer sits at (this bit us
  on 2026-08-24 after a tree move). Delete the venv and redo Section 3:
  `rm -rf .venv && uv sync --frozen`.
- **The scan writes a report where every category is zero** — check the URL
  responded at all. `results.json` records the HTTP status per probe; a site
  that refused the connection scores zero for the same reason as a site with
  nothing on it, and those are different findings. Read the JSON before writing
  the number into anything client-facing.
- **The scan appears to hang** — it is fetching over the network with no JS
  engine. A slow or unresponsive host is the usual cause. Let one site finish
  before concluding the tool is stuck.

## Section 7 — Run the tests

The test suite is offline (`httpx.MockTransport`) and touches no network:

```bash
uv run --frozen pytest -q
```

Exit 0 means the scoring logic is intact on this machine.
