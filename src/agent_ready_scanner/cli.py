"""CLI: scan a CSV of targets (vertical,name,url) or a single --url."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
from loguru import logger

from agent_ready_scanner import __version__
from agent_ready_scanner.models.site_result import ScanRun
from agent_ready_scanner.services.checks import scan_site
from agent_ready_scanner.services.report import write_reports


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="agent-ready-scan", description=__doc__)
    p.add_argument("targets", nargs="?", help="CSV with columns: vertical,name,url")
    p.add_argument("--url", help="scan a single URL instead of a CSV")
    p.add_argument("--out", default="runs/latest", help="output directory")
    p.add_argument("--timeout", type=float, default=15.0)
    return p.parse_args(argv)


def _load_targets(args: argparse.Namespace) -> list[tuple[str, str, str]]:
    if args.url:
        return [("single", args.url, args.url)]
    if not args.targets:
        logger.error("provide a targets CSV or --url")
        raise SystemExit(2)
    with Path(args.targets).open(newline="") as f:
        return [
            (row["vertical"].strip(), row["name"].strip(), row["url"].strip())
            for row in csv.DictReader(f)
            if row.get("url", "").strip()
        ]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    targets = _load_targets(args)
    logger.info("scanning {} target(s)", len(targets))
    results = []
    with httpx.Client(timeout=args.timeout, follow_redirects=True) as client:
        for vertical, name, url in targets:
            r = scan_site(client, vertical, name, url)
            status = f"{r.score}/100 {r.grade}" if r.ok else f"ERROR {r.error}"
            logger.info("[{}] {} — {}", vertical, name, status)
            results.append(r)
    run = ScanRun(
        generated_utc=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        scanner_version=__version__,
        results=results,
    )
    json_path, html_path = write_reports(run, Path(args.out))
    logger.info("wrote {} and {}", json_path, html_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
