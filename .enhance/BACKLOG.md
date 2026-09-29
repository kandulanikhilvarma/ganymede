# Backlog, 2026-09-29

Score = Impact (1-5) x Confidence (1-5) / Effort (1-5). Order: P0, then P1, then score. Status: DONE (commit), PARKED (blocker, see `BLOCKERS.md`), DEFERRED (not blocked, not done this run, with the reason), REJECTED (reason).

## P0 and P1

| ID | Item | I x C / E | Status | Evidence |
|---|---|---|---|---|
| C-01 | Label windows cross loan boundaries | 5x5/1 = 25 | DONE | `182d77f`; `tests/test_features.py` fails on old code (loan a read 7 from loan b) |
| C-02 | Short forward windows kept | 4x5/1 = 20 | DONE | `182d77f`; rows per loan = 6 - FORWARD in test |
| G-02 | Every published figure regenerated | 5x5/2 = 12.5 | DONE | `8d20bd4`; `build_site_data --check` OK; D15 in `docs/defects.md` |
| S-01 | Personal PDFs in public git history | 5x5/3 | PARKED | B1: needs a history rewrite and force-push |
| X-01 | Light faint text 4.07-4.38:1 | 4x5/1 = 20 | DONE | `8af650c`; 37 palette gates |
| X-02 | Signal on signal-quiet 4.39:1 | 4x5/1 = 20 | DONE | `8af650c` |
| X-03 | White text on light risk cells, 1.9:1 | 4x5/1 = 20 | DONE | `8af650c`, `8a10099`; Lighthouse color-contrast passes |
| X-04 | Focus rings clipped | 4x5/1 = 20 | DONE | `8a10099` |
| X-05 | Single-key shortcuts with no off switch | 4x5/1 = 20 | DONE | `8a10099` |
| X-06 | Tooltip not hoverable, not described | 3x5/2 = 7.5 | DONE | `8a10099` |
| X-07 | Slider announces an index | 4x5/1 = 20 | DONE | `8a10099`; aria-valuetext "5% capacity, allocator edge +177.9%" observed |
| X-08 | Field borders 1.6:1 | 3x5/1 = 15 | DONE | `8af650c`, `8a10099` |
| U-01 | Active nav dead under clean URLs | 4x5/1 = 20 | DONE | `8a10099`; aria-current set on 8 of 8 nav pages |
| T-01 | No test for the feature builder | 5x5/1 = 25 | DONE | `182d77f` |
| T-02 | Zero payment labelled KEPT | 4x4/1 | PARKED | B3: business rule |
| T-03 | Allocator comparison untested | 4x5/1 = 20 | DONE | `b0cf7be` |
| R-01 | LLM calls have a 600 s timeout | 4x5/1 = 20 | DONE | `ce4c7bd` |
| R-02 | One bad reply aborts a batch | 4x5/1 = 20 | DONE | `ce4c7bd`; `tests/test_llm_failures.py` |
| R-04 | Drift monitor fails nothing | 3x4/3 | PARKED | B10: scheduled run needs data and a CI secret |

## P2

| ID | Item | Score | Status | Evidence |
|---|---|---|---|---|
| C-03 | L2 recalibration described, not wired | 3x4/1 | PARKED (comment corrected) | B2 |
| C-04 | Outcome read from the wrong month | 3x5/2 = 7.5 | DONE | `ae58d8c` |
| C-05 | Extractor crashes on bad JSON | 4x5/1 = 20 | DONE | `ce4c7bd` |
| C-06 | Alpha crashes on uniform ratings | 3x5/1 = 15 | DONE | `ce4c7bd` |
| C-07 | Site-data gate passes a crashed stage | 4x5/1 = 20 | DONE | `8d20bd4`; `--only nope` now errors |
| C-11 | Greedy fill drops an account whose best action does not fit | 2x4/2 | PARKED | B4: modelling choice, found while writing T-03 |
| A-01 | build_site_data re-trains models 3 times | 2x4/3 = 2.7 | DEFERRED | Build now takes 126 s warm; refactor risk outweighs the gain this run |
| A-02 | README charts hard-code old numbers | 4x5/1 = 20 | DONE | `8d20bd4` |
| S-02 | No CSP (inline scripts on every page) | 3x4/4 = 3 | DEFERRED | Needs 9 page modules moved to files first; no third-party script or user HTML today |
| D-01 | Quickstart fails at pytest | 4x5/1 = 20 | DONE | README commit; clean-clone run (see PROGRESS.md) |
| D-02 | No lint in CI | 3x5/1 = 15 | DONE | `8a07972` |
| D-03 | master unprotected, 7 Dependabot PRs open | 3x5/1 | PARKED | B9: repo settings |
| T-04 | Risk gates untested | 3x5/1 = 15 | DONE | `b0cf7be` |
| T-05 | judge / ptp_eval at 0% | 3x5/1 = 15 | DONE | `ce4c7bd`; judge 100% |
| T-06 | Palette math untested | 2x5/1 = 10 | DONE | `b0cf7be` |
| T-07 | No site link/data smoke test | 4x5/1 = 20 | DONE | `b0cf7be`; mutation-checked |
| R-03 | Judge scores an error as 0 | 3x5/1 = 15 | DONE | `ce4c7bd` |
| R-05 | Cryptic traceback with no data | 3x5/1 = 15 | DONE | `ce4c7bd` |
| R-06 | Bare CLI runs exit 0 | 3x5/1 = 15 | DONE | `ce4c7bd`; 5 of 5 exit 2 |
| X-09 | Inactive steps at opacity .45 | 3x5/1 = 15 | DONE | `8a10099` |
| X-10 | Chart data unreachable without a mouse | 3x5/2 = 7.5 | DONE | `cffab28` |
| X-11 | Skip link skips the h1 | 3x5/1 = 15 | DONE | `8a10099` |
| X-12 | Counter ignores reduced motion | 2x5/1 = 10 | DONE | `8a10099` |
| X-13 | Blocked override not announced | 3x5/1 = 15 | DONE | `8a10099` |
| X-14 | Colour-only "only this strategy" | 3x5/1 = 15 | DONE | `8a10099` |
| X-15 | Generic "Start" link text | 2x5/1 = 10 | DONE | `8a10099`; Lighthouse link-text passes |
| U-02 | Silent fetch failures | 3x5/1 = 15 | DONE | `8a10099`; forced 404 on risk.json shows the message |
| U-03 | Desk/404 nav, orphaned design page | 2x3/1 | PARKED (404 already links out) | B8 |
| U-04 | Mobile menu state | 3x5/1 = 15 | DONE | `8a10099` |
| V-01 | Per-page heading sizes, tiny chart ticks | 2x4/3 = 2.7 | DEFERRED | Touches every page's CSS; no failing check today |
| V-02 | Container widths vary | 2x4/2 = 4 | DEFERRED | Same reason |
| V-03 | Missing hover/active states | 3x5/1 = 15 | DONE | `8a10099` |
| F-01 | 48 KB of unused audio JSON | 3x5/1 = 15 | DONE | `8d20bd4` |
| F-02 | Duplicate data fetches | 3x5/1 = 15 | DONE | `8a10099` |
| F-03 | CLS 0.116 on evidence | 3x5/1 = 15 | DONE | `8a10099`, `cffab28`; Lighthouse CLS audit passes |
| G-01 | README says 70 tests | 3x5/1 = 15 | DONE | README commit |

## P3

| ID | Item | Status | Reason or evidence |
|---|---|---|---|
| C-08 | Infinity in JSON | DONE | `8d20bd4`; test in `b0cf7be` |
| C-09 | VAD sample width, fake 0 ms | DONE | `cd396e2` |
| C-10 | Wrong return annotation | DONE | `ae58d8c` |
| A-03 | Unwired invariant helpers | PARKED | B5 |
| A-04 | Duplicated quadrant maps and thresholds | DEFERRED | Pure refactor; no behaviour at risk |
| A-05 | Stale docstrings, deprecated `min_periods` | DONE | `182d77f`, `cd396e2` |
| A-06 | Unused imports | DONE | `8a07972` |
| S-03 | No explicit HSTS, no Permissions-Policy | DONE | `6168ca3` |
| S-04 | Error text via innerHTML | DONE | `8a10099` |
| S-05 | CI permissions, concurrency | DONE | `8a07972`. SHA pinning DEFERRED until the Dependabot action bumps are triaged (B9) |
| S-06 | Dependabot security updates off | PARKED | B9 |
| D-04 | No `.env.example` | DONE | `8a07972` |
| D-05 | 3.11 only, no lock | DONE (3.13 matrix) | Lock file DEFERRED: a tooling choice (uv, pip-tools) for the owner |
| D-06 | `--check` ignored, `.coverage` untracked | DONE | `ce4c7bd`, `8a07972` |
| P-01 / O-01 | `.html` links take a 308 | REJECTED | Clean links break the `python -m http.server` preview the README documents; one cached redirect is cheap |
| P-02 | CSS/JS max-age=0 | DONE | `6168ca3` |
| P-03 / O-06 | robots hides a noindex | DONE | `6168ca3` |
| P-04 | No privacy note | DONE | `6168ca3` |
| P-05 | CITATION with no release | PARKED | B11 |
| P-06 | SECURITY.md has no SLA | PARKED | B11 |
| T-08 | No coverage floor | DONE | `8a07972`; 65% floor vs 67% measured |
| T-09 | Real sleep in one test | REJECTED | 0.4 s, low flake risk |
| R-07 | print, not logging | REJECTED | These are CLIs; exit codes now carry failure (R-06) |
| U-05 | "Drag the budget line" copy | DONE | `8a10099` |
| V-04 | Inline px in templates | DEFERRED | Cosmetic |
| V-05 | Design swatches do not repaint | DEFERRED | Page is noindex and unlinked |
| V-06 | OS colour scheme ignored | PARKED | B6 |
| F-04 | Pretty-printed JSON | REJECTED | 1.5 KB gzip on the wire; minifying makes `--check` diffs unreadable |
| F-05 | Index fetches all JSON eagerly | DEFERRED | After F-01/F-02 the eager set is smaller; low gain |
| F-06 | Font preload weight | PARKED | B7 |
| O-02 | No JSON-LD | DONE | `6168ca3` |
| O-03 / O-04 | Long descriptions, thin titles | PARKED | B12: copy |
| O-05 | theme-color, og:image:alt | DONE | `6168ca3` |
| G-03 | Static badges | DONE | README commit; CI badge |
| G-04 | Repo description and topics | REJECTED | Already set and accurate on GitHub |

## Features (cap 5)

| # | Proposal | User problem | Blocker | Status |
|---|---|---|---|---|
| 1 | Site integrity test | A renamed page, JSON or figure path breaks the site silently | none | DONE `b0cf7be` |
| 2 | "What this site keeps" note | Visitors cannot tell what the site stores | none | DONE `6168ca3` |
| 3 | `?cap=` scenario links | A capacity scenario can only be described, not linked | none | DONE `bc14b25` |
| 4 | "Show the numbers" tables | Chart values reach only a mouse | none | DONE `cffab28` |
| 5 | Visible load errors | A failed fetch leaves an empty box | none | DONE `8a10099` |
| 6 | Honour OS colour scheme | Light-preference users land in dark | design decision | PARKED (B6) |
| 7 | Nightly eval + drift job | Drift and judge regressions fail nothing | CI secret, data | PARKED (B10) |
| 8 | Walkthrough follows a real account | Two illustrative numbers on the home page | content decision | PARKED (B8) |
| 9 | CSP | Defence in depth | none (effort) | DEFERRED |
| 10 | Allocator cheaper-action fallback | Tail capacity goes unused | modelling decision | PARKED (B4) |
