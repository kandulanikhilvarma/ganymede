# Audit report, 2026-09-29

Scope: the whole repository at `8a7df89`. Five read-only subagents did the audit. The lead verified the P0 by hand and the Lighthouse runs by tool. Every finding has evidence. "Blocked" means the fix needs a secret, an account, a history rewrite, a deploy, or a decision between real options.

## Scores

| # | Dimension | Score | Justification |
|---|---|---|---|
| 1 | Correctness | 4/10 | Forward labels leak across loans in `features.py` (C-01). Every model and allocator number sits on those labels. |
| 2 | Security | 6/10 | No secrets in the tree or history. Two personal PDFs stay reachable in public history (S-01). No CSP is possible while pages use inline scripts. |
| 3 | Performance | 6/10 | No main-thread loop. But 48 KB of unused JSON, duplicate fetches, and mobile CLS on the moon pages. |
| 4 | Reliability | 4/10 | The LLM client has no timeout. One bad JSON reply aborts a batch. The drift monitor fails nothing. |
| 5 | Tests | 5/10 | Deterministic and offline. The label builder, outcome resolver, allocator comparison and eval scorers have no test. 59% coverage, no floor. |
| 6 | CI/CD and DX | 5/10 | Five real gates. The README quickstart fails at pytest. No lint step, no `.env.example`, no lock file. |
| 7 | Architecture | 6/10 | Small modules and good provenance tagging. `build_site_data.py` re-implements allocator logic and trains models 3 times. |
| 8 | Accessibility | 6/10 | Skip links, landmarks and reduced-motion base rule exist. Several AA contrast failures, clipped focus rings, single-key shortcuts. |
| 9 | UX and content | 6/10 | Honest copy, links resolve. Active nav state is dead in production. Fetch failures are silent. |
| 10 | Visual design | 7/10 | Disciplined OKLCH tokens. Pages bypass the type and container scales. Hover and active states are patchy. |
| 11 | SEO | 7/10 | Canonicals, sitemap and OG tags are right. 158 internal links take a 308 redirect. No JSON-LD. |
| 12 | Repo presentation | 7/10 | Strong README. Test count is wrong (says 70, real is 68 passed + 3 skipped). Quickstart omits dev extras. |
| 13 | Production readiness | 7/10 | Live site matches master. No privacy note for localStorage use. robots.txt and noindex conflict. |

## Findings

Severity: P0 broken, insecure, or data loss risk. P1 production-grade gap. P2 clear quality gain. P3 polish.

### Correctness (C) and architecture (A)

| ID | Sev | Evidence | Impact | Fix | Effort | Blocked |
|---|---|---|---|---|---|---|
| C-01 | P0 | `features.py:37-50` builds `g = pl.col("d").over("loan_id")` and then calls `g.shift(-i)`. Lead reproduced it: loan `a`'s last row gets `d_next1 = 7` from loan `b`. `build_site_data.py:68` has the correct order. | `y_worsen`, `y_selfcure` and trailing features cross loan boundaries. About 18% of rows carry another loan's future. | `shift(...).over("loan_id")` and `rolling_*(...).over("loan_id")`. Regenerate site data. | S (+rebuild) | No |
| C-02 | P1 | `features.py:49-50,64`: `max_horizontal` ignores nulls, so the filter keeps rows with only 1 or 2 future months. | Contradicts the docstring. Labels on short windows bias both targets. | Filter on `shift(-FORWARD).over("loan_id").is_not_null()`. | S | No |
| C-03 | P2 | `risk.py:170-180` comment says L2 recalibrates on the earlier test half. `_recalibrate` (`:150`) has no caller. | The evaluation does not do what the comment and the site note say. | Decide which one is intended. | S | Yes (decision) |
| C-04 | P2 | `outcomes.py:44-55` `_paid_next_month` compares the loan's last two panel rows, not the month after the promise. | Phase 6 promise labels come from the wrong month. | Carry the seed `period_date` and compare t with t+1. | S | No |
| C-05 | P2 | `coach/extract.py:50-51` `json.loads(text[start:end+1])` raises on a reply with no braces. Callers have no per-item guard (`ptp_eval.py:60`, `outcomes.py:89`). | One bad LLM reply aborts a whole eval. | Return `None` on parse failure and count it. | S | No |
| C-06 | P2 | `evals/judge.py:61` `krippendorff.alpha` raises `ValueError` when every rating is identical. | The report crashes on a uniform judge. | Return `nan` in that case. | S | No |
| C-07 | P2 | `build_site_data.py:707-747`: `--only metrics` raises `KeyError`, the broad `except` turns it into "skipped", and `--check` returns 0. | The staleness gate passes when a stage crashes. | Validate `--only`. In `--check`, fail on any skip that is not a missing input. | S | No |
| C-08 | P3 | `allocator.py:148`, `build_site_data.py:223` emit `float("inf")`, which `json.dumps` writes as `Infinity`. | Invalid JSON if the branch ever runs. | Use `None`. | S | No |
| C-09 | P3 | `audio/vad.py:42` assumes 16-bit samples; `:111` returns `gap_p50_ms=0` with no gaps. | Misreads other WAV widths and reports a false 0 ms. | Check sample width. Return `None` for no gaps. | S | No |
| C-10 | P3 | `outcomes.py:66` annotated `-> list[str]` but returns a tuple. `:75` enum check cannot fail. | Wrong type hint and a no-op check. | Fix the annotation. Drop the check. | S | No |
| A-01 | P2 | `build_site_data.py:507-518` re-implements `allocator.score_accounts`. `:206-225` re-implements `compare`. | Features build 5 times per run. The copies can drift. | Score once and share. | M | No |
| A-02 | P2 | `scripts/make_charts.py:68,77,103` hard-code `543.6`, `865.1`, `"+59%"`, `0.60`, `0.72`. | README charts go stale after C-01. | Read values from `site/data/*.json`. | S | No |
| A-03 | P3 | Dead or unwired: `checklist._EUR`, `config.SCHEMA_TAG`, schema `DataSource`/`ContactEvent`/`DelinquencyState`, `boundary.deliver`, `invariants.check_propensities`. | Invariants read as enforced but are not wired. | Wire or delete. | M | Yes (decision) |
| A-04 | P3 | Quadrant text maps in 3 places (`state.py:102`, `playbook.py:37`, `generate.py:28`). Threshold `0.6` in 2 places. | Copies can drift. | One source each. | S | No |
| A-05 | P3 | Stale docstrings (`vad.py:10`, `ptp_eval.py:5`, `report.py:4`). `features.py:43-44` uses deprecated `min_periods`. | Docs describe code that does not exist. | Fix text, use `min_samples`. | S | No |
| A-06 | P3 | `ruff --select E4,E7,E9,F`: 13 F401, 1 F841 (`checklist.py:26`), 17 E702, 1 E741. | Dead imports accumulate. | `ruff --fix` and a CI step. | S | No |

### Security (S), CI/DX (D), production (P)

| ID | Sev | Evidence | Impact | Fix | Effort | Blocked |
|---|---|---|---|---|---|---|
| S-01 | P1 | Two personal PDFs added in `c36dfde`, deleted in `d1fc91a`. The repo is public. | Anyone can recover them from history. | `git filter-repo` and a force-push, then a GitHub cache purge. | M | Yes (history rewrite) |
| S-02 | P2 | Every page has an inline theme script and an inline module. | `script-src 'self'` would break every page. No CSP. | Move page modules to files, hash the theme script, add CSP. | M | No |
| S-03 | P3 | `vercel.json` has no `Permissions-Policy`. HSTS comes only from the Vercel default. | HSTS is lost on a custom domain. | Add both headers. | S | No |
| S-04 | P3 | `innerHTML` built from JSON fields: `desk.html:467,529`, `queue.html:285,381`, `desk.html:820` (`err.message`). | Safe today (same-origin JSON). Unsafe if a generator ever emits markup. | `textContent` for the error paths. | S | No |
| S-05 | P3 | `ci.yml:11-12` tags not SHAs. No `permissions`, no `concurrency`. | Supply-chain drift, duplicate runs. | Add `permissions: contents: read`, `concurrency`. | S | No |
| S-06 | P3 | Dependabot security updates disabled (repo setting). | No automatic security PRs. | Enable in settings. | S | Yes (repo setting) |
| D-01 | P2 | README quickstart installs `requirements.txt` only, which has no pytest. | Gate 2 fails in a clean venv. | `pip install -e ".[dev,llm,charts,audio]"`. | S | No |
| D-02 | P2 | No lint step, no pre-commit. | See A-06. | Ruff step in CI. | S | No |
| D-03 | P2 | `master` unprotected. Seven Dependabot PRs open since 2026-09-02. | CI is advisory only. | Protect master. Triage PRs. | S | Yes (repo settings) |
| D-04 | P3 | No `.env.example`. Code reads `OPENROUTER_API_KEY`, `GANYMEDE_LLM_BACKEND`, `GANYMEDE_LIVE_LLM`. | Live tests are undiscoverable. | Add `.env.example`. | S | No |
| D-05 | P3 | Deps unpinned `>=`, CI on 3.11 only. | Not reproducible. | Add a 3.13 matrix entry. | S | No |
| D-06 | P3 | README says 70 tests. `invariants.py:73-85` ignores `--check`. `.coverage` not in `.gitignore`. | Docs drift. | Fix. | S | No |
| P-01 | P3 | 158 internal links use `.html`; live `/system.html` returns 308. | Extra redirect per click. | Use clean links. | M | No |
| P-02 | P3 | `/assets/*` served `max-age=0`. | 7 revalidations per page view. | Short `max-age` with `stale-while-revalidate`. | S | No |
| P-03 | P3 | `robots.txt:3-4` disallows `/design`, which hides its `noindex`. | URL can be indexed without content. | Remove Disallow. | S | No |
| P-04 | P3 | No privacy note. The site stores `gm-theme`, `gm-depth`, `ganymede-desk-log` in localStorage. | Storage use not disclosed. | Note on the about page. | S | No |
| P-05 | P3 | `CITATION.cff` version 0.1.0 but no tag or release. | Citation points at nothing. | Tag and release. | S | Yes (publish) |
| P-06 | P3 | `SECURITY.md` has no scope or response time. | Reporters lack expectations. | Add both. | S | Yes (SLA decision) |

### Tests (T) and reliability (R)

| ID | Sev | Evidence | Impact | Fix | Effort | Blocked |
|---|---|---|---|---|---|---|
| T-01 | P1 | No test calls `build_features` or `time_split`. | C-01 passed CI. | 2-loan fixture test. | S | No |
| T-02 | P1 | `test_outcomes.py` covers only `resolve`. `resolve(Promise(amount=500), True, 0.0)` returns KEPT (`outcomes.py:32`). | Zero payment labelled kept. | Test and decide the zero-amount rule. | S | Yes (business rule) |
| T-03 | P1 | `compare`, `_risk_ranking`, `_realised_value` untested. | The headline number has no unit check. | 5-row synthetic test. | S | No |
| T-04 | P2 | `reliability`, `_metrics`, `_passes` untested. | Gate logic unverified. | Unit tests. | S | No |
| T-05 | P2 | `evals/judge.py`, `coach/ptp_eval.py` at 0%. | Scoring math never runs in CI. | FakeEngine tests. | S | No |
| T-06 | P2 | No tests for `gen_palette.py` contrast math or site JS. | Covered end-to-end only. | Unit test the contrast function. | M | No |
| T-07 | P2 | No link or data smoke test. Hand check: 237 refs resolve today. | A rename breaks the site silently. | Pytest that scans hrefs and `loadData` targets. | S | No |
| T-08 | P3 | No `--cov-fail-under`. | Coverage can fall silently. | Add a floor. | S | No |
| T-09 | P3 | `test_coach.py:90` real sleep. | Low flake risk. | Leave. | S | No |
| R-01 | P1 | `llm.py:64` `OpenAI(...)` sets no timeout. openai default is read 600 s, 2 retries. | A hung call blocks 30 minutes. | `timeout=30, max_retries=3`. | S | No |
| R-02 | P1 | Same as C-05. | One bad reply aborts a batch. | See C-05. | S | No |
| R-03 | P2 | `judge.py:43` scores an empty or error reply as 0. | Skews agreement. | Treat as missing. | S | No |
| R-04 | P1 | `drift.py:2-3` says a nightly eval exits non-zero on drift. No nightly workflow. `report.run` never calls drift. | Drift can fail nothing. | Wire into `report.main`. Scheduled job needs data. | M | Partly (data in CI) |
| R-05 | P2 | With `data/raw` empty, `panel.build` raises `ValueError: cannot concat empty list`; `build_features` raises a raw `FileNotFoundError`. | Cryptic first run. | Clear message, exit 2. | S | No |
| R-06 | P2 | `python -m ganymede.risk` (no flag) prints nothing, exits 0. Same for allocator, outcomes, panel, evals.report. | A typo in CI passes. | Print help, exit 2. | S | No |
| R-07 | P3 | No `logging`; 50 `print` calls. | No levels, FAIL lines go to stdout. | Leave; scope creep for a CLI tool. | S | No |

### Accessibility (X), UX (U), visual (V)

| ID | Sev | Evidence | Impact | Fix | Effort | Blocked |
|---|---|---|---|---|---|---|
| X-01 | P1 | Light `--faint #6b7675` on `--ground` 4.38:1, on `--surface` 4.07:1. Dark faint on surface-2 3.5:1. | Captions, table headers, footer fail 1.4.3. | Darken; add pairs to palette gates. | S | No |
| X-02 | P1 | Light `--signal` on `--signal-quiet` 4.39:1 (active nav, pressed seg, badge). | Fails 1.4.3. | Darker text on quiet. | S | No |
| X-03 | P1 | Hard-coded white text on data colours: `index.html:120`, evidence/desk/queue/design matrix code. Lighthouse flags index, queue, evidence. | Labels unreadable (1.9:1). | Pick text colour by luminance. | S | No |
| X-04 | P1 | `components.css:350` `.seg{overflow:hidden}`, `system.html:88` clip focus rings. | Focus invisible (2.4.7). | Inset outline in those containers. | S | No |
| X-05 | P1 | `desk.html:795-806` single-key shortcuts on `window`; Space on a focused button also toggles playback. | Fails 2.1.4 (Level A). | Skip when focus is on a control; add an off switch. | S | No |
| X-06 | P1 | `site.js:84-87` tooltip hides on trigger `mouseleave`; no `aria-describedby`. | Fails 1.4.13. | Hover grace and `aria-describedby`. | M | No |
| X-07 | P1 | `queue.html:158` range announces an index, not a percentage. Readouts have no live region. | Fails 4.1.2, 4.1.3. | `aria-valuetext` and `aria-live`. | S | No |
| X-08 | P1 | Input borders `--line` 1.6-1.7:1 (`desk.html:173`, `glossary.html:57`). | Fails 1.4.11. | Use `--line-strong`-based border that passes 3:1. | S | No |
| X-09 | P2 | `index.html:130` `.step{opacity:.45}`: inactive text about 2.5:1. | Fails 1.4.3. | Dim with colour, not opacity. | S | No |
| X-10 | P2 | Chart data only in SVG `<title>`; badges unfocusable. | Keyboard and touch users cannot reach values. | Data-table disclosure per chart. | M | No |
| X-11 | P2 | `about.html:125`, `case.html:138` put the h1 before `<main>`. `desk.html` jumps h1 to h3. | Skip link skips the title; outline broken. | Move `<main>`; promote headings. | S | No |
| X-12 | P2 | `desk.html:581-590` rAF counter ignores reduced motion. | design.html claim is false. | Check the media query. | S | No |
| X-13 | P2 | `desk.html:747` blocked override not announced. | Fails 3.3.1. | `aria-invalid` + status text. | S | No |
| X-14 | P2 | `queue.html:59,82` "only this strategy" rows marked by colour only. | Fails 1.4.1. | Add a text tag. | S | No |
| X-15 | P2 | Lighthouse `link-text`: nav item "Start" on every page. | Generic link text. | "Start here". | S | No |
| U-01 | P1 | `site.js:95-97` compares `system` to `system.html`; production uses clean URLs. | No active nav state in production. | Strip `.html` before comparing. | S | No |
| U-02 | P2 | `.catch(() => {})` on index (7 calls) and evidence (5 calls); glossary shows "Nothing matches" on error. | Charts vanish silently. | Shared error renderer. | S | No |
| U-03 | P2 | desk.html and 404.html have no site nav. design.html is linked from nowhere. | Inconsistent navigation. | Add nav to 404. Design page stays unlinked (decision). | S | Partly |
| U-04 | P2 | Mobile menu button keeps `aria-label="Open menu"`, has no `aria-controls`, no Escape. | State unclear. | Update label, add Escape. | S | No |
| U-05 | P3 | `evidence.html:164` says "Drag the budget line" for a range input. | Copy mismatch. | "Move the slider". | S | No |
| V-01 | P2 | Section h2 sizes differ per page; chart tick text scales to about 4 px on phones. | Inconsistent, unreadable ticks. | Role tokens. | M | No |
| V-02 | P2 | Container widths 1280/1180/1100/1080/940; nav offsets hard-coded. | Edges jump between pages. | Container tokens. | S | No |
| V-03 | P2 | No hover on `.themebtn`, `.navtoggle`, `.btn-danger`; no `:active` anywhere. | Controls feel inert. | Add states. | S | No |
| V-04 | P3 | Inline px values in JS templates; `.pchip` duplicated in desk and queue. | Token drift. | Move to components.css. | S | No |
| V-05 | P3 | `design.html:447-450` swatches resolve once at load. | Wrong values after theme toggle. | Re-read on toggle. | S | No |
| V-06 | P3 | Dark forced by default; no `prefers-color-scheme` check. | Light-preference users get dark. | Decision. | S | Yes (design decision) |

### Performance (F) and SEO (O)

| ID | Sev | Evidence | Impact | Fix | Effort | Blocked |
|---|---|---|---|---|---|---|
| F-01 | P2 | `audio.json` 80.6 KB; `segments` (30.1 KB) and `envelope` (18.1 KB) never read by site code. | 60% of the payload is unused. | Drop at build time. | S | No |
| F-02 | P2 | `charts.js:240` `loadData` does not share the `figures.js` cache; index fetches 4 files twice. | Duplicate requests. | Share the cache. | S | No |
| F-03 | P2 | `#moon` has no reserved size (about, glossary, case). Lighthouse CLS 0.116 on evidence. | Layout shift. | `aspect-ratio:1`. | S | No |
| F-04 | P3 | Site JSON is pretty-printed: 244 KB raw vs 123 KB minified. | Parse cost. | Minify in the build. Changes `--check` diff format. | S | No |
| F-05 | P3 | index fetches all JSON eagerly. | Competes with LCP. | Lazy-load below the fold. | S | No |
| F-06 | P3 | 96.7 KB of font preload on every page, italic not preloaded. | Double swap on h1. | Design decision. | M | Partly |
| F-07 | P3 | Same as P-02. | | | | |
| O-01 | P2 | Same as P-01. | | | | |
| O-02 | P3 | No JSON-LD. | No entity signal. | `WebSite` + `Person`. | S | No |
| O-03 | P3 | Meta descriptions over 160 chars on 8 pages. | Truncated snippets. | Copy edit. | S | Yes (copy) |
| O-04 | P3 | Titles are brand-only. | Weak relevance. | Copy edit. | S | Yes (copy) |
| O-05 | P3 | No `theme-color`, touch icon, `og:image:alt`. | Minor. | Add `theme-color` and `og:image:alt`. | S | No |
| O-06 | P3 | Same as P-03. | | | | |

### Repo presentation (G)

| ID | Sev | Evidence | Impact | Fix | Effort | Blocked |
|---|---|---|---|---|---|---|
| G-01 | P2 | README badge and text say "70 passing"; `pytest` reports 68 passed, 3 skipped. | Inaccurate claim. | Correct. | S | No |
| G-02 | P2 | README headline numbers come from the leaked labels (C-01). | Numbers change after the fix. | Regenerate from site data. | S | No |
| G-03 | P3 | No CI status badge; badges are static shields. | Badges do not reflect real CI. | Use the Actions badge. | S | No |
| G-04 | P3 | Repo description and topics not checked into docs. | Discoverability. | Suggest; set with `gh`. | S | No |
