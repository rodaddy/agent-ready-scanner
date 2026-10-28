# src

The scanner's Python package, laid out `src/`-style so the installed package is
what the tests import. One package: `agent_ready_scanner/` — see its own
README. Packaging config is `pyproject.toml` at the kit root
(`[tool.hatch.build.targets.wheel] packages = ["src/agent_ready_scanner"]`).
