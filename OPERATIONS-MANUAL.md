# Operations Manual — Agent-Ready Scanner

Day-to-day operation of the scanner after `installer.md` has been followed
once. Operator-facing; rTech-internal (rung 4).

## 1. What this kit is for

One question per site, answered from raw HTTP only, with no JavaScript executed
— exactly what an AI crawler or agent sees: **can an AI agent read, understand,
and act on this business's website?**

It produces the market proof for the Agent-Ready Audit offer
(`planning/agent-ready-internet/STRATEGY.md`): per-vertical scorecards showing
how few SMB sites are agent-legible, plus the baseline for rTech's own site.

## 2. What it is NOT for

It does not fix a site, does not publish, and does not replace the person who
maintains the site. The output is a list of specific, ordered things that
person can do — the scanner takes the "go find out what is missing" work off
their plate and hands back the answer. Never present a score as a verdict on a
person's work.

## 3. The two commands

Single site:

```bash
uv run agent-ready-scan --url https://example.com --out runs/example
```

Batch, from a CSV with the columns `vertical,name,url`:

```bash
uv run agent-ready-scan targets/example.csv --out runs/2026-09-10-batch
```

Plain-Python equivalents (no `uv` on the machine):

```bash
.venv/bin/python -m agent_ready_scanner --url https://example.com --out runs/example
.venv/bin/python -m agent_ready_scanner targets/example.csv --out runs/2026-09-10-batch
```

Both write `results.json` (machine-readable) and `report.html` (the
self-contained branded deliverable) into the `--out` folder.

## 4. What it scores

| Category | Points | Signals |
|----------|-------:|---------|
| discovery | 15 | robots.txt, sitemap |
| ai_access | 10 | AI-crawler policy in robots.txt (GPTBot, ClaudeBot, PerplexityBot, …) |
| llms_txt | 15 | llms.txt, llms-full.txt |
| structured_data | 25 | JSON-LD: business identity, offers/FAQ, schema contact |
| parseability | 15 | no-JS visible word count, text ratio, title + meta description |
| pricing | 10 | machine-visible prices (page text, priceRange/offers schema, pricing page) |
| contact_booking | 10 | tel: link, schema contact, booking link |

Grades: **A ≥ 85 · B ≥ 70 · C ≥ 55 · D ≥ 40 · F < 40.**

Recorded but deliberately **not** scored, because the standards are still
moving: `/.well-known/mcp.json`, `/.well-known/ai-plugin.json`, HTTP 402
responses. They appear in `results.json` as observations.

## 5. Named refusal (KIT-STANDARD § 4.9)

**The scanner never scores a site it could not reach.**

Deterministic trigger: the root document fetch fails — connection refused, DNS
failure, timeout — or returns a 5xx status. A 4xx status or a non-HTML content
type is still scored, so check those by hand.

What happens: **no grade is produced for that site.** `results.json` records
`"ok": false` and `"error": "unreachable (<status or connection error>)"`
(its `score` and `grade` fields hold unused defaults; ignore them), and the
report shows `—` for score and grade with that error, not a zero and not an
F. A zero means "the
site is readable and has none of these signals"; an unreachable host means "we
do not know", and those two must never collapse into one number in front of a
client.

What the operator does: state plainly which sites were not scanned and why, and
re-run those after the cause is resolved. Never carry an unreachable host into
a scorecard as a low grade to keep the batch total tidy.

The same rule applies to the operator: **do not hand a client a number the
scanner did not produce.** If a category reads as unknown, it is reported as
unknown.

## 6. Reading a report before it goes out

1. Open `report.html` and confirm the site name and URL are the intended
   target.
2. Open `results.json` and check `ok` and `error`. `results.json` does not
   record per-probe HTTP statuses; if the score looks too low, open the URL
   and its `robots.txt` yourself to rule out a 4xx or a bot block.
3. Check `parseability`. A site that renders everything through JavaScript
   scores low here by design — that IS the finding, not a scanner error.
4. Every claim that leaves this kit for a client carries the date it was
   scanned. Sites change; a score is a snapshot, not a standing fact.

## 7. Versioning and changes

`VERSION` is the version of record and matches `kit.json` and
`pyproject.toml`. Scoring weights and grade thresholds are part of the
published method: changing one changes what every past score meant, so a
weight change is a version bump plus a `CHANGELOG.md` entry saying which
category moved and by how much. Past runs under `runs/` are kept as the record
of what the method produced at the time.

## 8. Tests

```bash
uv run --frozen pytest -q
```

Functional and offline (`httpx.MockTransport`) — no network, deterministic.
Run them after any dependency change and before any batch that will be shown to
a client.
