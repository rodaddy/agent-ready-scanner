"""Raw-HTTP primitives: fetch, visible text, JSON-LD walk, robots policy.

Everything here sees exactly what an AI crawler sees — no JS execution.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "rTech-AgentReadyScanner/0.1 (+https://rtech-consulting.com)"

AI_CRAWLERS = [
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-Web",
    "anthropic-ai",
    "PerplexityBot",
    "Google-Extended",
    "CCBot",
    "meta-externalagent",
    "Bytespider",
]


def get(client: httpx.Client, url: str) -> httpx.Response | None:
    try:
        return client.get(url, headers={"User-Agent": USER_AGENT})
    except httpx.HTTPError:
        return None


def visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))


def jsonld_blocks(soup: BeautifulSoup) -> tuple[list[str], list[dict[str, Any]]]:
    """All @type strings and all dict nodes across every JSON-LD script tag."""
    types: list[str] = []
    blocks: list[dict[str, Any]] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except json.JSONDecodeError, TypeError:
            continue
        stack: list[object] = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                blocks.append(node)
                t = node.get("@type")
                if isinstance(t, str):
                    types.append(t)
                elif isinstance(t, list):
                    types.extend(x for x in t if isinstance(x, str))
                stack.extend(node.values())
    return types, blocks


@dataclass(frozen=True)
class AiRobotsPolicy:
    addressed: list[str]
    blocked: list[str]
    wildcard_blocks_all: bool


def robots_ai_policy(robots_txt: str) -> AiRobotsPolicy:
    """AI-crawler policy from robots.txt, honouring group precedence.

    A specific ``User-agent: <bot>`` group wins over ``User-agent: *`` for that
    bot (standard robots semantics). A wildcard ``Disallow: /`` therefore blocks
    every AI crawler that has no more-specific group — reported via
    ``wildcard_blocks_all`` so the scorer does not read a block-everything site
    as "default-open" (PR #40 cross-family review, Terra, 2026-08-17).
    """
    rules = _robots_rules(robots_txt)
    lowered = {agent.lower(): disallows for agent, disallows in rules.items()}
    star = lowered.get("*")
    wildcard_blocks_all = star is not None and "/" in star

    addressed: list[str] = []
    blocked: list[str] = []
    for bot in AI_CRAWLERS:
        disallows = lowered.get(bot.lower())
        if disallows is not None:
            # Specific group present: it governs this bot outright.
            addressed.append(bot)
            if "/" in disallows:
                blocked.append(bot)
        elif wildcard_blocks_all:
            # No specific group, and the wildcard blocks everything.
            blocked.append(bot)
    return AiRobotsPolicy(
        addressed=addressed,
        blocked=blocked,
        wildcard_blocks_all=wildcard_blocks_all,
    )


def _robots_rules(robots_txt: str) -> dict[str, list[str]]:
    rules: dict[str, list[str]] = {}
    current_agents: list[str] = []
    prev_was_agent = False
    for raw in robots_txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip().lower(), value.strip()
        if key == "user-agent":
            if not prev_was_agent:
                current_agents = []
            current_agents.append(value)
            prev_was_agent = True
            continue
        prev_was_agent = False
        if key == "disallow":
            for agent in current_agents:
                rules.setdefault(agent, []).append(value)
    return rules
