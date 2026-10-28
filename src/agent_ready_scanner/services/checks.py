"""Per-site agent-readiness scan: gather signals, then score them.

Scoring model (100 points):
    discovery 15, ai_access 10, llms_txt 15, structured_data 25,
    parseability 15, pricing 10, contact_booking 10.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from agent_ready_scanner.models.site_result import CategoryScore, SiteResult, SiteSignals
from agent_ready_scanner.services import fetch

BUSINESS_SCHEMA_TYPES = {
    "LocalBusiness",
    "Organization",
    "Corporation",
    "ProfessionalService",
    "LegalService",
    "Attorney",
    "AccountingService",
    "MedicalBusiness",
    "MedicalClinic",
    "HealthAndBeautyBusiness",
    "BeautySalon",
    "DaySpa",
    "HomeAndConstructionBusiness",
    "RoofingContractor",
    "HVACBusiness",
    "Plumber",
    "Electrician",
    "Restaurant",
    "FoodEstablishment",
    "Dentist",
    "Physician",
    "RealEstateAgent",
    "InsuranceAgency",
    "FinancialService",
    "AutoRepair",
    "Store",
    "VeterinaryCare",
    "ExerciseGym",
    "HealthClub",
}
OFFER_SCHEMA_TYPES = {"Service", "Product", "Offer", "OfferCatalog", "FAQPage", "Menu"}

PRICING_PATH_HINTS = re.compile(r"(pricing|prices|rates|fees|cost|menu|packages|plans)", re.I)
BOOKING_HINTS = re.compile(
    r"(calendly\.com|acuityscheduling|squareup\.com/appointments|booksy\.com|"
    r"schedulicity|vagaro\.com|zocdoc\.com|opentable\.com|resy\.com|"
    r"/book(?:ing|-online|-now|-appointment)?[/\"'?#])",
    re.I,
)
MONEY_RE = re.compile(r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?(?!\d)")


def scan_site(client: httpx.Client, vertical: str, name: str, url: str) -> SiteResult:
    result = SiteResult(vertical=vertical, name=name, url=url)
    if not urlparse(url).scheme:
        url = "https://" + url
    home = fetch.get(client, url)
    if home is None or home.status_code >= 500:
        result.error = f"unreachable ({home.status_code if home else 'connection error'})"
        return result
    result.ok = True
    result.final_url = str(home.url)
    base = f"{urlparse(result.final_url).scheme}://{urlparse(result.final_url).netloc}"
    soup = BeautifulSoup(home.text, "html.parser")

    sig = result.signals
    _collect_side_files(client, base, home, sig)
    blocks = _collect_page_signals(home.text, soup, sig)
    _collect_pricing(client, result.final_url, soup, sig, blocks)
    _collect_contact(home.text, soup, sig)
    score_site(result)
    return result


def _collect_side_files(
    client: httpx.Client, base: str, home: httpx.Response, sig: SiteSignals
) -> None:
    robots = fetch.get(client, base + "/robots.txt")
    robots_text = robots.text if (robots is not None and robots.status_code == 200) else ""
    sig.robots_txt = "user-agent" in robots_text.lower()
    policy = fetch.AiRobotsPolicy(addressed=[], blocked=[], wildcard_blocks_all=False)
    if sig.robots_txt:
        policy = fetch.robots_ai_policy(robots_text)
    sig.ai_crawlers_addressed = policy.addressed
    sig.ai_crawlers_blocked = policy.blocked

    if "sitemap:" in robots_text.lower():
        sig.sitemap = True
    else:
        sm = fetch.get(client, base + "/sitemap.xml")
        sig.sitemap = sm is not None and sm.status_code == 200 and "<" in sm.text[:200]

    sig.llms_txt = _is_plain_doc(fetch.get(client, base + "/llms.txt"))
    sig.llms_full_txt = _is_plain_doc(fetch.get(client, base + "/llms-full.txt"))
    sig.mcp_json = _is_json_200(fetch.get(client, base + "/.well-known/mcp.json"))
    sig.ai_plugin_json = _is_json_200(fetch.get(client, base + "/.well-known/ai-plugin.json"))
    sig.x402_seen = home.status_code == 402


def _is_plain_doc(r: httpx.Response | None) -> bool:
    return (
        r is not None
        and r.status_code == 200
        and len(r.text.strip()) > 40
        and "<html" not in r.text[:400].lower()
    )


def _is_json_200(r: httpx.Response | None) -> bool:
    if r is None or r.status_code != 200:
        return False
    try:
        json.loads(r.text)
        return True
    except json.JSONDecodeError:
        return False


def _collect_page_signals(html: str, soup: BeautifulSoup, sig: SiteSignals) -> list[dict[str, Any]]:
    types, blocks = fetch.jsonld_blocks(soup)
    sig.jsonld_types = sorted(set(types))
    text = fetch.visible_text(html)
    sig.word_count_no_js = len(text.split())
    sig.text_ratio = round(len(text) / len(html), 4) if html else 0.0
    sig.js_wall = sig.word_count_no_js < 50
    sig.title = bool(soup.title and soup.title.get_text(strip=True))
    md = soup.find("meta", attrs={"name": "description"})
    desc = md.get("content") if isinstance(md, Tag) else None
    sig.meta_description = isinstance(desc, str) and bool(desc.strip())
    return blocks


def _collect_pricing(
    client: httpx.Client,
    page_url: str,
    soup: BeautifulSoup,
    sig: SiteSignals,
    blocks: list[dict[str, Any]],
) -> None:
    base_netloc = urlparse(page_url).netloc
    schema_price = any(
        b.get("priceRange") or b.get("price") or _offer_has_price(b.get("offers")) for b in blocks
    )
    sig.schema_contact = any(
        b.get("telephone")
        or b.get("address")
        or b.get("openingHours")
        or b.get("openingHoursSpecification")
        for b in blocks
    )
    text = fetch.visible_text(str(soup))
    if schema_price or MONEY_RE.search(text):
        sig.pricing_visible = True
        return
    link = next(
        (a["href"] for a in soup.find_all("a", href=True) if PRICING_PATH_HINTS.search(a["href"])),
        None,
    )
    if not link:
        return
    target = urljoin(page_url, link)
    if urlparse(target).netloc != base_netloc:
        return
    pr = fetch.get(client, target)
    if pr is not None and pr.status_code == 200:
        sig.pricing_visible = bool(MONEY_RE.search(fetch.visible_text(pr.text)))


def _offer_has_price(offers: Any) -> bool:
    """True only if a JSON-LD offers value carries an actual price.

    A bare/empty ``offers`` object is not machine-visible pricing (PR #40
    cross-family review, Terra, 2026-08-17).
    """
    stack = [offers]
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, dict):
            if (
                node.get("price")
                or node.get("priceRange")
                or node.get("lowPrice")
                or node.get("priceSpecification")
            ):
                return True
            if "offers" in node:
                stack.append(node["offers"])
    return False


def _collect_contact(html: str, soup: BeautifulSoup, sig: SiteSignals) -> None:
    sig.tel_link = bool(soup.find("a", href=re.compile(r"^tel:", re.I)))
    sig.booking_link = bool(BOOKING_HINTS.search(html))


def score_site(result: SiteResult) -> None:
    """Deterministic scoring from collected signals. Pure — safe to unit-test."""
    sig = result.signals
    cats = result.categories

    cats["discovery"] = CategoryScore(
        points=(5 if sig.robots_txt else 0) + (10 if sig.sitemap else 0),
        max=15,
        notes=f"robots.txt {'yes' if sig.robots_txt else 'NO'}, "
        f"sitemap {'yes' if sig.sitemap else 'NO'}",
    )
    cats["ai_access"] = _score_ai_access(sig)
    cats["llms_txt"] = CategoryScore(
        points=(12 if sig.llms_txt else 0) + (3 if sig.llms_full_txt else 0),
        max=15,
        notes="llms.txt present" if sig.llms_txt else "no llms.txt",
    )
    has_business = bool(set(sig.jsonld_types) & BUSINESS_SCHEMA_TYPES)
    has_offer = bool(set(sig.jsonld_types) & OFFER_SCHEMA_TYPES)
    cats["structured_data"] = CategoryScore(
        points=(8 if sig.jsonld_types else 0)
        + (7 if has_business else 0)
        + (5 if has_offer else 0)
        + (5 if sig.schema_contact else 0),
        max=25,
        notes=f"JSON-LD types: {', '.join(sig.jsonld_types) or 'none'}",
    )
    word_pts = 8 if sig.word_count_no_js >= 150 else (4 if sig.word_count_no_js >= 50 else 0)
    meta_pts = 3 if (sig.title and sig.meta_description) else (1.5 if sig.title else 0)
    cats["parseability"] = CategoryScore(
        points=word_pts + (4 if sig.text_ratio >= 0.02 else 0) + meta_pts,
        max=15,
        notes=f"{sig.word_count_no_js} words without JS" + (" — JS WALL" if sig.js_wall else ""),
    )
    cats["pricing"] = CategoryScore(
        points=10 if sig.pricing_visible else 0,
        max=10,
        notes="prices machine-visible" if sig.pricing_visible else "no machine-visible pricing",
    )
    cats["contact_booking"] = CategoryScore(
        points=(4 if sig.tel_link else 0)
        + (3 if sig.schema_contact else 0)
        + (3 if sig.booking_link else 0),
        max=10,
        notes=f"tel:{'yes' if sig.tel_link else 'no'} "
        f"schema-contact:{'yes' if sig.schema_contact else 'no'} "
        f"booking:{'yes' if sig.booking_link else 'no'}",
    )
    result.score = round(sum(c.points for c in cats.values()))
    result.grade = _grade(result.score)


def _score_ai_access(sig: SiteSignals) -> CategoryScore:
    blocked, addressed = sig.ai_crawlers_blocked, sig.ai_crawlers_addressed
    if blocked and len(blocked) >= len(fetch.AI_CRAWLERS) // 2:
        return CategoryScore(points=0, max=10, notes=f"blocks AI crawlers: {', '.join(blocked)}")
    if blocked:
        return CategoryScore(points=4, max=10, notes=f"partially blocks: {', '.join(blocked)}")
    if addressed:
        return CategoryScore(points=10, max=10, notes=f"explicitly allows: {', '.join(addressed)}")
    return CategoryScore(points=7, max=10, notes="no AI crawler policy (default-open, unmanaged)")


def _grade(score: int) -> str:
    for floor, letter in ((85, "A"), (70, "B"), (55, "C"), (40, "D")):
        if score >= floor:
            return letter
    return "F"
