# Progress, 2026-09-30

Branch `enhance/2026-09-29` on `master@8a7df89`. All phases done. Resume a parked item with `/enhance resume <B-ID>` (see `BLOCKERS.md`).

## State

| Phase | Status | File |
|---|---|---|
| 0 Preflight | done | `baseline.md`, `toolbox.md`, `plan.md` |
| 1 Audit | done (5 subagents; P0 verified by hand) | `AUDIT_REPORT.md` |
| 2 Design | done (Mobbin unavailable: paid plan) | `DESIGN_SPEC.md`, `screens/before/` |
| 3 Backlog | done | `BACKLOG.md` |
| 4 Implement | done for every unblocked item | `git log master..` |
| 5 README | done; repo description/topics already accurate | `README.md` |
| 6 Verify | done; clean clone passes all six gates | this file |

## Before and after

| Measure | Before (`8a7df89`) | After (branch tip) | Evidence |
|---|---|---|---|
| Tests | 68 passed, 3 skipped | 115 passed, 3 skipped | `pytest` |
| Coverage (ganymede) | 59% | 67% local, 69% clean clone | `pytest --cov` |
| Lint (`E4,E7,E9,F`) | 32 errors, not in CI | 0, in CI | `ruff check .` |
| CI gates | 5, Python 3.11 | 6, Python 3.11 and 3.13 | `.github/workflows/ci.yml` |
| Palette contrast gates | 14 | 37 | `gen_palette.py --check` |
| Lighthouse a11y (index/queue/evidence/desk, mobile) | 96/96/96/100 | 100/100/100/100 | `.enhance/lighthouse/*/` (local) |
| Lighthouse SEO (same pages) | 92/92/92/100 | 100/100/100/100 | same |
| Evidence CLS | 0.116 (fail) | pass | same |
| `audio.json` | 75.9 KB | 7.0 KB | `wc -c` |
| Site data build | 1613 s (`--check`, first run of the session) | 126 s (write, warm) | not like-for-like; no build-speed claim is made |
| Clean-clone quickstart | fails at pytest | all six gates pass, install 145 s | scratchpad run |
| L1 AUC / L2 AUC | 0.62 / 0.67 (leaked labels) | 0.66 / 0.76 | `site/data/metrics.json` |
| Allocator edge at 15% | +59.1% (leaked labels) | +72.5% | `site/data/allocator.json` |

## Dimension scores

| Dimension | Before | After | Why it moved |
|---|---|---|---|
| Correctness | 4 | 8 | C-01/C-02/C-04/C-07 fixed; C-03, C-11 parked |
| Security | 6 | 7 | headers, textContent errors, CI least privilege; history PDFs (B1) still open |
| Performance | 6 | 7 | 69 KB JSON cut, shared fetch cache, CLS fixed; font weight parked |
| Reliability | 4 | 7 | timeouts, counted bad replies, exit codes; scheduled drift parked |
| Tests | 5 | 8 | +47 tests, site integrity, coverage floor |
| CI/DX | 5 | 8 | lint, matrix, quickstart, `.env.example`; branch protection parked |
| Architecture | 6 | 6 | A-01, A-03, A-04 deferred or parked |
| Accessibility | 6 | 9 | X-01 to X-15 done; Lighthouse 100 |
| UX and content | 6 | 8 | active nav, errors, data tables, deep links; stale prose fixed |
| Visual design | 7 | 7 | states added; type/container scale deferred |
| SEO | 7 | 8 | JSON-LD, alt text, robots; copy parked |
| Repo presentation | 7 | 8 | accurate README, CI badge |
| Production readiness | 7 | 8 | privacy note, headers, caching |

## Not committed (local only)

`.enhance/screens/` (10 MB of PNG) and `.enhance/lighthouse/` (3.3 MB) are gitignored to keep the repo small. Regenerate with `bash .enhance/shoot.sh after` and the DevTools Lighthouse run. Headless Chrome cannot render narrower than about 500 px, so the `*-mobile.png` files are clipped; real 375 px layout was checked in the browser pane (no horizontal overflow).
