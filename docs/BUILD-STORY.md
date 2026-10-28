# How the Agent-Ready Scanner was built

Sources: the commit history of the private monorepo the scanner was developed
in (it was published here as a single snapshot commit on 2026-10-27), the
issues and pull requests that tracked it, `CHANGELOG.md` and the test suite.

## The problem and the first version (2026-08-17)

The question was simple: when an AI assistant looks at a small business's
website, what can it actually see? Assistants and crawlers mostly read raw
HTML. They do not run the site's JavaScript, and they look for side files
(`robots.txt`, a sitemap, `llms.txt`) and structured data (JSON-LD) that many
small-business sites never had a reason to publish.

The first version was written in one day as a proof of concept: a `uv`
Python app (Python 3.14, `httpx`, BeautifulSoup, Pydantic, loguru) with the
seven-category weight table it still uses. Two design decisions date from
that first commit:

- **Raw HTTP only, no browser.** Running JavaScript would make the scan
  closer to what a person sees and further from what an AI crawler sees.
- **Deterministic scoring.** The score comes from a fixed table of signals
  and weights, not from asking a model for an opinion, so the same site gives
  the same score and every point can be explained.

The first commit carried 12 offline tests. The suite was checked by
deliberately breaking a grade threshold and confirming that a test failed
("red proven") before trusting it. Ruff and mypy strict were clean.

The same day it ran its first batch: 35 small-business sites on Long Island
across six industries, 34 of them reachable. The commit records an average of
66/100, about a third with an `llms.txt` file, none with an MCP endpoint, and
9% with any AI-crawler policy in `robots.txt`. The author's own consulting site
scored 79/B, missing `llms.txt`, an AI-crawler policy and a booking link. After
those were added the site was re-scanned at 94/A; that report is kept in
`runs/self-after-deploy/`.

## Second-model review (2026-08-17)

The code was written with Claude-based coding agents. Before it was relied on,
it went to a reviewer from a different model family, because a reviewer
running on the same model tends to miss the same things the author missed.
That review found two correctness bugs the same-family review had not:

1. **A site that blocked every crawler scored as open.** `robots.txt` with
   `User-agent: *` / `Disallow: /` was read as "no AI-crawler policy" and
   earned 7 of 10 points, the opposite of the truth. The parser now follows
   standard group precedence and reports `wildcard_blocks_all`.
2. **Empty price data counted as a price.** A JSON-LD `offers` object with no
   price in it set "pricing visible". The check now walks nested offers and
   requires a real price node.

Each fix got a regression test, and each test was shown to fail with its fix
reverted. The suite went to 13 tests. Two other review points were recorded
and declined, with reasons, in the commit: one concerned a separate script,
and the other (counting `<noscript>` text) was rejected because that text is
almost always a "turn on JavaScript" notice and would inflate the score.

## From proof of concept to kit (2026-08-24 to 2026-09-10)

On 2026-08-24 the working repository adopted a rule that a proof of concept
either becomes a packaged kit or is archived. The scanner was the last one
left. The test for "proven" was written into the tracking issue: someone who
has never seen the code runs it from the zip against their own site and gets
the same kind of report.

On 2026-09-10 an AI agent working from a written, scoped brief did the
promotion: the operator documents (`START-HERE.md`, `installer.md`,
`OPERATIONS-MANUAL.md`, `tiers/basic/README.md`) and the kit manifest. The
head session re-ran the checks before each merge.

**What did not work:** the first pull request merged only the file move. The
landing script had staged files with an out-of-date path list and merged
without checking what was staged. A second pull request carried the rest of
the kit and was checked against the full change before it merged. The defect
was recorded against the landing script rather than worked around.

## How it is tested

- 13 functional tests in `tests/test_scan.py`, all offline: each one feeds a
  fake site through `httpx.MockTransport` and checks the score, grade or
  robots policy that comes out.
- `ruff` and `mypy --strict` over the package.
- The operator manual requires verifying on the real site being asked about,
  not on the shipped sample.

## Current state (2026-10-27)

Version 0.1.0, about 720 lines of Python. It is used as an operator tool: the
operator runs the scan and the site owner gets the HTML report. Signals that
are still emerging (MCP discovery files, HTTP 402 payment responses) are
recorded but not scored until they are common enough to be fair to score.
