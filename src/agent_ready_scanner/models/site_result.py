"""Pydantic models for scan results. No logic here."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CategoryScore(BaseModel):
    points: float
    max: int
    notes: str


class SiteSignals(BaseModel):
    robots_txt: bool = False
    ai_crawlers_addressed: list[str] = Field(default_factory=list)
    ai_crawlers_blocked: list[str] = Field(default_factory=list)
    sitemap: bool = False
    llms_txt: bool = False
    llms_full_txt: bool = False
    mcp_json: bool = False
    ai_plugin_json: bool = False
    x402_seen: bool = False
    jsonld_types: list[str] = Field(default_factory=list)
    title: bool = False
    meta_description: bool = False
    word_count_no_js: int = 0
    text_ratio: float = 0.0
    js_wall: bool = False
    pricing_visible: bool = False
    tel_link: bool = False
    booking_link: bool = False
    schema_contact: bool = False


class SiteResult(BaseModel):
    vertical: str
    name: str
    url: str
    final_url: str = ""
    ok: bool = False
    error: str = ""
    signals: SiteSignals = Field(default_factory=SiteSignals)
    categories: dict[str, CategoryScore] = Field(default_factory=dict)
    score: int = 0
    grade: str = "F"


class ScanRun(BaseModel):
    generated_utc: str
    scanner_version: str
    results: list[SiteResult]
