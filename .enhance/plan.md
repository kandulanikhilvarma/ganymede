# Enhance plan, 2026-09-29

Branch: `enhance/2026-09-29` from `master` at `8a7df89`.

## Assumptions

- STACK_LOCK is yes. The site stays plain HTML, CSS and JS with no bundler. The
  package stays Python 3.11+ with its current dependencies.
- BRAND_LOCK is soft. Ice, ember, and the Fraunces/Geist pairing stay. New tokens
  extend `scripts/gen_palette.py`; `tokens.css` is never edited by hand.
- The site shows only generated numbers. No change adds a hand-typed figure.
- The untracked `docs/DEPLOYMENT-PROMPT.md` belongs to the user. It is never staged.
- The profile-README work goes into this repo's README (user decision).
- No deploy. The Vercel production site does not change until the user merges.

## Phases and verify checks

| # | Phase | Verify check |
|---|---|---|
| 0 | Preflight, baseline, toolbox | `.enhance/baseline.md` records all five gates, ruff, coverage |
| 1 | Audit, 13 dimensions, 5 subagents | `.enhance/AUDIT_REPORT.md` has evidence for every finding and a score per dimension |
| 2 | Design research and spec | `.enhance/screens/before/` has desktop and mobile shots; `DESIGN_SPEC.md` exists |
| 3 | Backlog | `.enhance/BACKLOG.md` lists every finding with a score and a status |
| 4 | Implement | Each commit names a backlog ID; the five gates pass after each block |
| 5 | README | Every command in Quickstart runs; Mermaid validates; badges match CI |
| 6 | Final verification | Gates, ruff, coverage re-run; before/after table; draft PR; CI read back |
