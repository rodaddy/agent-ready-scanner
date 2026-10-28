# Agent-Ready Scanner — basic

The kit's only tier. `basic` is mandatory and is the first tier
(`kits/README.md` § Repo layout); this kit has no second one.

## What ships

One canonical package: `START-HERE.md`, `installer.md`,
`OPERATIONS-MANUAL.md`, `kit.json`, `VERSION`, `CHANGELOG.md`, `README.md`,
the uv app itself (`pyproject.toml`, `uv.lock`, `.python-version`, plus
`requirements.txt` generated from the lock so it runs without uv), the
scanner source under `src/agent_ready_scanner/`, the offline test suite under
`tests/`, an example target list at `targets/example.csv`, and one past rTech
scan under `runs/` kept as a reference for what the output looks like.

In use: point it at one URL or at a CSV of them and it fetches each site over
raw HTTP with **no JavaScript executed** — exactly what an AI crawler or agent
sees — then scores seven categories to 100 points and writes
`results.json` plus a self-contained branded `report.html`.

## Who it is for

rTech operators, running the Agent-Ready Audit
(`planning/agent-ready-internet/STRATEGY.md`). This is **delivery ladder rung
4, rTech-internal only** (`kits/KIT-STANDARD.md` § Delivery-surface ladder):
the operator runs the scan, the client receives the report. A client is never
asked to open a terminal.

What it does for the client's people: it hands whoever maintains their site a
specific, ordered list of what an AI agent cannot find there. It takes the
"go work out what is missing" job off that person's plate and gives them back
the answer to act on. It does not touch the site and does not replace them.

## What it refuses to do

**It never scores a site it could not read.** Deterministic trigger: the root
document fetch does not return a 2xx HTML response — connection refused, DNS
failure, timeout, non-HTML content type, or an error status. The site is
reported as `NOT SCANNED — <reason>`, never as a zero and never as an F. A
zero means the site is readable and has none of these signals; unreachable
means we do not know, and collapsing the two in front of a client is the
failure the refusal exists to prevent. Full statement:
`OPERATIONS-MANUAL.md` § 5.

It also does not execute JavaScript, by design. A site that renders entirely
through JS scores low on parseability, and that is the finding rather than a
scanner limitation to apologize for.

## Install

The steps in `installer.md`, condensed:

1. **Runtime floor** (Section 1) — Python 3.14+ (`requires-python = ">=3.14"`),
   or `uv`, which fetches its own interpreter.
2. **Dependencies** (Section 3) — `uv sync --frozen` preferred; the plain-Python
   path is `python3.14 -m venv .venv` then
   `.venv/bin/python -m pip install -r requirements.txt`, pinned from the same
   lock.
3. **Verify on the real target** (Section 4) — run the scan against the site you
   were actually asked about and read the report. Shipped `runs/` examples may
   not stand in for it (`kits/KIT-STANDARD.md` § 4.10). No real target in hand
   means the install is UNVERIFIED, stated as such.
4. **Batch scanning** (Section 5), **failure modes** (Section 6), **tests**
   (Section 7).

Runtime floor per `kit.json`: Python `>=3.14`. No Node, no Bun, no build step.

## Current version

0.1.0
