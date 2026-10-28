# Start Here — Agent-Ready Scanner

This kit is an **rTech-internal operator tool**, delivery-surface ladder rung 4
(`kits/KIT-STANDARD.md` § Delivery-surface ladder: "CLI: rTech-internal ONLY").
An rTech operator runs the scan; the client receives the `report.html` it
produces. No client is ever asked to open a terminal or install anything.

You have a zip. Here is the one path to a scan, on a Mac running the rTech
toolchain.

## 1. Unzip it

Double-click the zip. It unzips into a folder named `agent-ready-scanner` next
to it. Open that folder in Terminal:

```bash
cd ~/Downloads/agent-ready-scanner
```

Use the path where you actually unzipped it if it is not `~/Downloads`.

## 2. Install the dependencies

Preferred, with `uv` (the pinned lockfile, byte-identical every time):

```bash
uv sync --frozen
```

Without `uv`, using plain Python 3.14 or newer:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## 3. Scan one site

With `uv`:

```bash
uv run agent-ready-scan --url https://example.com --out runs/example
```

Without `uv`:

```bash
.venv/bin/python -m agent_ready_scanner --url https://example.com --out runs/example
```

## 4. Open the report

```bash
open runs/example/report.html
```

That file is the deliverable. `runs/example/results.json` is the same scan as
machine-readable data.

---

Everything else — scanning a list of sites, what each score means, what the
scanner refuses to do — is in `OPERATIONS-MANUAL.md`. The full install detail,
including what to do when a step fails, is in `installer.md`.
