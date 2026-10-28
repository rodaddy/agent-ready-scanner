# models

Typed result shapes (pydantic). `site_result.py` holds the per-site record the
scan produces — the score, the grade, the per-category detail, and the probe
observations that are recorded but not scored. This is the shape `results.json`
is serialized from, so a field change here changes the output contract.
