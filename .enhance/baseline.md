# Baseline (before), 2026-09-29, commit 8a7df89

Machine: Windows 11, Python 3.13.1, ruff 0.16.5, polars 1.44.1. CI uses Python 3.11.

## Gates

| Gate | Command | Result | Time |
|---|---|---|---|
| Invariants | `python -m ganymede.invariants --check` | PASS, "static invariants OK (2 checked)" | 4 s |
| Tests | `python -m pytest -q` | PASS, 68 passed, 3 skipped (71 collected) | 29 s (7 s warm) |
| Design tokens | `python scripts/gen_palette.py --check` | PASS, 14 contrast gates | <1 s |
| Fonts | `python scripts/fetch_fonts.py --check` | PASS, 8 woff2, 283 KB | 1 s |
| Site data | `python scripts/build_site_data.py --check` | PASS, 9 files checked, 18 metric rows | 1613 s (full data present locally) |

Skipped tests: `test_llm.py:23`, `test_judge_live.py:9`, `test_ptp_live.py:9`. All three need `GANYMEDE_LIVE_LLM=1`.

## Lint and coverage (not CI gates)

| Check | Result |
|---|---|
| `ruff check --select E4,E7,E9,F .` | 32 errors: 17 E702, 13 F401, 1 E741, 1 F841 |
| `ruff check .` (ruff 0.16 defaults) | 49 errors |
| `ruff format --check .` | 34 files would change |
| `pytest --cov=ganymede` | 59% total (1072 statements, 442 missed) |

Lowest module coverage: `coach/ptp_eval.py` 0%, `evals/judge.py` 0%, `evals/report.py` 0%, `panel.py` 31%, `outcomes.py` 33%, `features.py` 38%, `allocator.py` 48%, `risk.py` 48%.

## Site (static, no build step)

| Page | Lighthouse mobile a11y | Best practices | SEO | Failing audits |
|---|---|---|---|---|
| index | 96 | 100 | 92 | color-contrast (roll bar labels), link-text |
| queue | 96 | 100 | 92 | color-contrast (`.id`), link-text |
| evidence | 96 | 100 | 92 | color-contrast (matrix cell), link-text, CLS |
| desk | 100 | 100 | 100 | none |

Reports: `.enhance/lighthouse/before/<page>/report.html`.

Page weight (raw KB): index 395, evidence 296, case 290, desk 279, queue 200, system 155, glossary 154, about 145, 404 122. The two preloaded fonts are 96.7 KB on every page.

Screenshots: `.enhance/screens/before/` (desktop 1440 wide). Headless Chrome cannot render narrower than about 500 px, so the `*-mobile.png` files are clipped at 390 px. A live check at 375 px showed `scrollWidth <= 375` on all 8 content pages, so there is no real horizontal overflow.
