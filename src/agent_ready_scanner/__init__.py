"""agent-ready-scanner — deterministic agent-readiness scoring for business websites.

Answers one question per site, from raw HTTP only (no JS execution, exactly
what an AI crawler or agent sees): can an AI agent read, understand, and act
on this business's website?

Checks: robots.txt + AI-crawler policy, sitemap, llms.txt / llms-full.txt,
JSON-LD structured data (business identity, offers, contact), no-JS content
parseability, machine-visible pricing, tel/booking legibility, and emerging
signals (/.well-known/mcp.json, ai-plugin.json, HTTP 402).

Usage:
    uv run agent-ready-scan targets/example.csv --out runs/batch
    uv run agent-ready-scan --url https://rtech-consulting.com
"""

__version__ = "0.1.0"
