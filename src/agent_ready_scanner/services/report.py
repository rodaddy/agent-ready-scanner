"""Render a scan run to results.json and a branded report.html.

Palette and typography follow assets/DESIGN-SYSTEM.md (garnet/gold on warm
paper, Helvetica Neue). The HTML is self-contained: no web fonts, favicon
embedded as a data URI.
"""

from __future__ import annotations

import html
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from agent_ready_scanner.models.site_result import ScanRun, SiteResult

FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='6' fill='%23641220' stroke='%23b8860b' "
    "stroke-width='2'/%3E%3Ctext x='16' y='22' font-family='Helvetica' font-size='16' "
    "font-weight='700' fill='%23b8860b' text-anchor='middle'%3EAr%3C/text%3E%3C/svg%3E"
)

GRADE_COLORS = {
    "A": ("#dcefdc", "#1e6b2e"),
    "B": ("#dbe7f5", "#1d4e89"),
    "C": ("#f4e3c0", "#7a5a00"),
    "D": ("#f4d6d6", "#8a1f1f"),
    "F": ("#f4d6d6", "#8a1f1f"),
}

CATEGORY_ORDER = [
    "discovery",
    "ai_access",
    "llms_txt",
    "structured_data",
    "parseability",
    "pricing",
    "contact_booking",
]

CSS = """
* { box-sizing: border-box; margin: 0; }
body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background: #f5f2ee;
       color: #1a1a1a; font-size: 15px; line-height: 1.45; padding: 32px 40px 64px; }
h1 { font-size: 24px; color: #641220; margin-bottom: 4px; }
h2 { font-size: 18px; color: #641220; border-bottom: 1.5px solid #b8860b;
     padding-bottom: 4px; margin: 32px 0 12px; }
.sub { color: #666; font-size: 13px; margin-bottom: 24px; }
.stats { display: flex; gap: 16px; flex-wrap: wrap; margin: 20px 0; }
.stat { background: #641220; color: #fff; border-radius: 8px; padding: 14px 20px; min-width: 150px; }
.stat b { display: block; font-size: 34px; font-weight: 800; color: #f0d9a8; }
.stat span { font-size: 12.5px; color: #f0d9a8; }
table { border-collapse: collapse; width: 100%; background: #fff; }
th { text-transform: uppercase; letter-spacing: .05em; font-size: 12px; color: #666;
     text-align: left; padding: 8px 10px; border-bottom: 2px solid #641220; }
td { padding: 8px 10px; border-bottom: 1px solid #ddd6cc; vertical-align: top; }
tr:hover td { background: #faf7f2; }
td.num { font-variant-numeric: tabular-nums; text-align: right; }
.pill { display: inline-block; border-radius: 10px; padding: 1px 10px; font-size: 12.5px; font-weight: 700; }
.sig { font-size: 12.5px; color: #666; }
.miss { color: #8a1f1f; font-weight: 700; }
.have { color: #1e6b2e; }
.note { background: #fff; border-left: 3px solid #b8860b; padding: 10px 14px;
        margin: 16px 0; font-size: 13.5px; color: #666; }
"""


def write_reports(run: ScanRun, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "results.json"
    json_path.write_text(run.model_dump_json(indent=2))
    html_path = out_dir / "report.html"
    html_path.write_text(_render_html(run))
    return json_path, html_path


def _pct(results: list[SiteResult], pred: Callable[[SiteResult], bool]) -> int:
    live = [r for r in results if r.ok]
    return round(100 * sum(1 for r in live if pred(r)) / len(live)) if live else 0


def _render_html(run: ScanRun) -> str:
    live = [r for r in run.results if r.ok]
    by_vertical: dict[str, list[SiteResult]] = defaultdict(list)
    for r in run.results:
        by_vertical[r.vertical].append(r)

    avg = round(sum(r.score for r in live) / len(live)) if live else 0
    stats = [
        (str(len(live)), "sites scanned"),
        (f"{avg}/100", "average score"),
        (f"{_pct(run.results, lambda r: r.signals.llms_txt)}%", "have llms.txt"),
        (f"{_pct(run.results, lambda r: bool(r.signals.jsonld_types))}%", "any structured data"),
        (f"{_pct(run.results, lambda r: r.signals.pricing_visible)}%", "machine-visible pricing"),
        (f"{_pct(run.results, lambda r: r.signals.js_wall)}%", "JS-walled"),
    ]
    stat_html = "".join(f"<div class='stat'><b>{v}</b><span>{k}</span></div>" for v, k in stats)
    sections = "".join(_render_vertical(v, rs) for v, rs in sorted(by_vertical.items()))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent-Readiness Scan — rTech Digital Consulting</title>
<link rel="icon" href="{FAVICON}"><style>{CSS}</style></head><body>
<h1>Agent-Readiness Scan</h1>
<div class="sub">rTech Digital Consulting · generated {run.generated_utc} ·
scanner v{run.scanner_version} · deterministic raw-HTTP checks (what an AI agent actually sees — no JS)</div>
<div class="stats">{stat_html}</div>
<div class="note">Score = discovery 15 · AI-access policy 10 · llms.txt 15 · structured data 25
· no-JS parseability 15 · pricing legibility 10 · contact/booking legibility 10.
A ≥ 85 · B ≥ 70 · C ≥ 55 · D ≥ 40 · F &lt; 40.</div>
{sections}
</body></html>"""


def _render_vertical(vertical: str, results: list[SiteResult]) -> str:
    live = [r for r in results if r.ok]
    avg = round(sum(r.score for r in live) / len(live)) if live else 0
    rows = "".join(_render_row(r) for r in sorted(results, key=lambda r: -r.score))
    return f"""<h2>{html.escape(vertical)} — avg {avg}/100 ({len(live)} live)</h2>
<table><tr><th>Site</th><th>Score</th><th>Grade</th><th>What agents find</th><th>What's missing</th></tr>
{rows}</table>"""


def _render_row(r: SiteResult) -> str:
    if not r.ok:
        return (
            f"<tr><td>{html.escape(r.name)}</td><td class='num'>—</td><td>—</td>"
            f"<td colspan='2' class='sig miss'>{html.escape(r.error)}</td></tr>"
        )
    bg, fg = GRADE_COLORS[r.grade]
    s = r.signals
    have = [
        x
        for x, ok in [
            ("robots", s.robots_txt),
            ("sitemap", s.sitemap),
            ("llms.txt", s.llms_txt),
            ("JSON-LD", bool(s.jsonld_types)),
            ("pricing", s.pricing_visible),
            ("tel", s.tel_link),
            ("booking", s.booking_link),
            ("MCP", s.mcp_json),
        ]
        if ok
    ]
    missing = [
        x
        for x, ok in [
            ("llms.txt", s.llms_txt),
            ("structured data", bool(s.jsonld_types)),
            ("schema contact", s.schema_contact),
            ("pricing", s.pricing_visible),
            ("sitemap", s.sitemap),
        ]
        if not ok
    ]
    if s.js_wall:
        missing.insert(0, "JS WALL — near-zero content without JS")
    if s.ai_crawlers_blocked:
        missing.append("blocks: " + ", ".join(s.ai_crawlers_blocked))
    host = html.escape(r.final_url.split("//", 1)[-1].rstrip("/"))
    return (
        f"<tr><td>{html.escape(r.name)}<br><span class='sig'>{host}</span></td>"
        f"<td class='num'><b>{r.score}</b></td>"
        f"<td><span class='pill' style='background:{bg};color:{fg}'>{r.grade}</span></td>"
        f"<td class='sig have'>{html.escape(', '.join(have) or 'nothing')}</td>"
        f"<td class='sig miss'>{html.escape('; '.join(missing) or '—')}</td></tr>"
    )
