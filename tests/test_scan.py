"""Functional tests at the public boundary: scan_site against mock transports."""

from __future__ import annotations

import httpx
import pytest

from agent_ready_scanner.services.checks import MONEY_RE, scan_site
from agent_ready_scanner.services.fetch import AI_CRAWLERS, robots_ai_policy

RICH_HOME = """<!doctype html><html><head><title>Acme Spa</title>
<meta name="description" content="Med spa in Huntington NY">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"DaySpa","name":"Acme Spa",
 "telephone":"+1-631-555-0100","priceRange":"$$",
 "address":{"@type":"PostalAddress","addressLocality":"Huntington"}}
</script></head><body><a href="tel:+16315550100">Call</a>
<a href="https://calendly.com/acme">Book</a>
<p>%s</p><p>Botox from $12 per unit.</p></body></html>""" % ("word " * 200)

BARE_HOME = """<!doctype html><html><head></head><body>
<div id="root"></div><script src="/bundle.js"></script></body></html>"""


def _client(pages: dict[str, tuple[int, str]]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        status, body = pages.get(request.url.path, (404, "not found"))
        return httpx.Response(status, text=body)

    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


def test_rich_site_scores_high_and_signals_fire() -> None:
    pages = {
        "/": (200, RICH_HOME),
        "/robots.txt": (200, "User-agent: *\nDisallow:\nSitemap: https://x.com/sitemap.xml"),
        "/llms.txt": (200, "# Acme Spa\n\nServices, pricing, and booking for agents." * 3),
    }
    with _client(pages) as c:
        r = scan_site(c, "med-spa", "Acme", "https://acme.example")
    assert r.ok
    assert r.signals.llms_txt and r.signals.sitemap and r.signals.pricing_visible
    assert "DaySpa" in r.signals.jsonld_types
    assert r.signals.tel_link and r.signals.booking_link and r.signals.schema_contact
    assert not r.signals.js_wall
    assert r.score >= 85 and r.grade == "A"


def test_js_wall_site_scores_low() -> None:
    with _client({"/": (200, BARE_HOME)}) as c:
        r = scan_site(c, "roofing", "Bare", "https://bare.example")
    assert r.ok
    assert r.signals.js_wall
    assert not r.signals.jsonld_types and not r.signals.pricing_visible
    assert r.grade in ("D", "F")


EMPTY_OFFERS_HOME = """<!doctype html><html><head><title>NoPrice Co</title></head><body>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Service","name":"Consult",
 "offers":{"@type":"Offer","availability":"InStock"}}
</script><p>%s</p></body></html>""" % ("word " * 60)


def test_empty_offers_is_not_machine_visible_pricing() -> None:
    # Regression (PR #40 Terra review): a bare offers object with no price must
    # NOT count as machine-visible pricing.
    with _client({"/": (200, EMPTY_OFFERS_HOME)}) as c:
        r = scan_site(c, "svc", "NoPrice", "https://noprice.example")
    assert r.ok
    assert not r.signals.pricing_visible


def test_offers_with_price_counts() -> None:
    home = EMPTY_OFFERS_HOME.replace('"availability":"InStock"', '"price":"199.00"')
    with _client({"/": (200, home)}) as c:
        r = scan_site(c, "svc", "Priced", "https://priced.example")
    assert r.signals.pricing_visible


def test_unreachable_site_reports_error() -> None:
    with _client({"/": (500, "boom")}) as c:
        r = scan_site(c, "law", "Down", "https://down.example")
    assert not r.ok
    assert "unreachable" in r.error


def test_robots_ai_policy_specific_groups() -> None:
    policy = robots_ai_policy("User-agent: GPTBot\nUser-agent: ClaudeBot\nDisallow: /")
    assert policy.addressed == ["GPTBot", "ClaudeBot"]
    assert policy.blocked == ["GPTBot", "ClaudeBot"]
    assert not policy.wildcard_blocks_all


def test_robots_wildcard_block_all_blocks_every_ai_crawler() -> None:
    # Regression (PR #40 Terra review): `User-agent: * / Disallow: /` blocks all
    # AI crawlers — it must NOT read as default-open.
    policy = robots_ai_policy("User-agent: *\nDisallow: /")
    assert policy.wildcard_blocks_all
    assert set(policy.blocked) == set(AI_CRAWLERS)
    assert policy.addressed == []


def test_robots_specific_allow_overrides_wildcard_block() -> None:
    # GPTBot has its own group allowing all; the wildcard blocks the rest.
    policy = robots_ai_policy("User-agent: *\nDisallow: /\nUser-agent: GPTBot\nDisallow:")
    assert "GPTBot" in policy.addressed
    assert "GPTBot" not in policy.blocked
    assert "ClaudeBot" in policy.blocked


def test_robots_empty_is_open() -> None:
    policy = robots_ai_policy("")
    assert policy.addressed == [] and policy.blocked == [] and not policy.wildcard_blocks_all


@pytest.mark.parametrize(
    ("text", "hit"),
    [
        ("Botox $12 per unit", True),
        ("Plans from $1,299.00", True),
        ("no prices here", False),
        ("call for pricing", False),
    ],
)
def test_money_regex(text: str, hit: bool) -> None:
    assert bool(MONEY_RE.search(text)) is hit
