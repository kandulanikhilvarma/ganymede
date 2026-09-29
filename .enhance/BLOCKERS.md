# Blockers, 2026-09-29

Everything below needs you: a history rewrite, a repo setting, a secret, or a decision between real options. Everything that did not is done or has a stated reason in `BACKLOG.md`.

Resume any item with `/enhance resume <BLOCKER-ID>`.

---

## B1. Personal PDFs are in the public git history (security, do first)

- **Unlocks:** S-01.
- **Built around it:** `.gitignore` already excludes `*.pdf` and `extracted.txt`. Nothing new was committed. The two files are not in the working tree of this branch.
- **Fact:** `Nikhilvarma_Kandula_Jupiter_100_Tage.pdf` and `supprting document.pdf` were added in `c36dfde` and deleted in `d1fc91a`. Both commits are reachable from `origin/master`. The repo is public, so anyone can recover the files with `git show c36dfde:<name>`.
- **What you must do:** rewrite history and force-push. This session did not, because the run's rules forbid force-push and history rewrites on shared branches.
  1. Merge or close this PR first. The rewrite changes every commit hash.
  2. `pip install git-filter-repo`
  3. In a fresh clone: `git filter-repo --invert-paths --path "Nikhilvarma_Kandula_Jupiter_100_Tage.pdf" --path "supprting document.pdf"`
  4. `git push --force --all` and `git push --force --tags`
  5. Ask GitHub Support to purge cached views and `refs/pull/*` for the two paths (GitHub docs: "Removing sensitive data from a repository").
- **Recommendation:** do it. The tradeoff is that forks and open PRs need rebasing onto the new history.

## B2. L2 evaluation: recalibrate, or keep static calibration? (decision)

- **Unlocks:** C-03.
- **Built around it:** the misleading comment and the hard-coded "Phase 8 monitor recalibrates" note are gone. `risk.py` now says `_recalibrate` exists but is not wired in. Tests cover the gates.
- **Input:** one choice. (a) Wire `_recalibrate`: fit isotonic on the first half of the test window, score the second half. (b) Delete `_recalibrate` and keep static calibration.
- **Where:** reply with `B2: a` or `B2: b`.
- **Recommendation:** (b). The fixed labels show no regime shift (0.59 to 0.52, inside the alert band) and L2 Brier already beats base (0.199 vs 0.250). Tradeoff: (a) is closer to how production would run, but it halves the evaluation sample.

## B3. Is a promise with zero payment "kept"? (business rule)

- **Unlocks:** T-02.
- **Fact:** `resolve(Promise(amount=500), paid=True, amount_paid=0.0)` returns KEPT (`outcomes.py:32`: a falsy `amount_paid` skips the partial check).
- **Input:** one rule. (a) paid with 0 received is BROKEN. (b) it is PARTIAL. (c) keep KEPT (delinquency improved, which is the payment proxy on this data).
- **Where:** reply with `B3: a|b|c`. The test and the one-line change follow.
- **Recommendation:** (a). On this data "paid" is inferred from delinquency improving, so zero observed paydown with improvement is most often a servicing artefact, not a kept promise.

## B4. Allocator: fall back to a cheaper action when the best one does not fit? (modelling)

- **Unlocks:** C-11, feature 10.
- **Fact:** the greedy fill assigns each account its single best action. If that action (for example restructure, 25 min) does not fit the remaining minutes, the account is skipped instead of offered plan_offer (12) or reminder (3). On the real queue this only wastes the tail of capacity; on a 24-minute toy queue it recovered 0.
- **Input:** (a) add the fallback (a multiple-choice knapsack, still greedy); (b) keep as is and document it.
- **Where:** reply `B4: a|b`. Choosing (a) changes every allocator figure again (a 2-minute rebuild).
- **Recommendation:** (a), with the rebuild in the same PR so numbers and code stay together.

## B5. Wire or delete the unwired invariant helpers (decision)

- **Unlocks:** A-03.
- **Fact:** `boundary.deliver`/`is_hint_eligible`, `invariants.check_propensities`, schema `DataSource`/`ContactEvent`/`DelinquencyState`, `checklist._EUR`, `config.SCHEMA_TAG` exist, and the README describes some as enforcing invariants, but no production path calls them.
- **Input:** (a) wire them (retrain path calls `check_propensities`; coach loop calls `deliver`); (b) delete them and soften the README rows.
- **Recommendation:** (a) for `check_propensities` and `deliver` (they back I3 and I11), (b) for the rest.

## B6. Honour the OS colour scheme on first visit? (design)

- **Unlocks:** V-06, feature 6.
- **Fact:** dark is forced by design (`tokens.css` comment). Visitors who prefer light land in dark until they toggle.
- **Input:** (a) follow `prefers-color-scheme` when nothing is stored; (b) keep dark as the identity.
- **Recommendation:** (a). The stored choice still wins, and the light theme now passes every contrast gate.

## B7. Font preload weight (design)

- **Unlocks:** F-06.
- **Fact:** every page preloads 96.7 KB (Geist + Fraunces roman). The h1 uses Fraunces italic, which is not preloaded, so the headline swaps twice.
- **Input:** (a) preload the italic on pages whose h1 uses `<em>`; (b) subset Fraunces to the weights in use; (c) leave it.
- **Recommendation:** (b) then (a).

## B8. Two content choices on the site

- **Unlocks:** U-03, feature 8.
- **Inputs:** (1) should `design.html` be linked from the footer, or stay unlinked and noindex? (2) the home walkthrough shows `81` p(worsen) and confidence `0.18` for an illustrative borrower: bind them to a real desk account, or label them "illustrative"?
- **Recommendation:** (1) link it from the About page; it documents the palette gates. (2) bind to the desk's scored account, so the page keeps its "no hand-typed number" rule.

## B9. Repository settings (needs your GitHub account)

- **Unlocks:** D-03, S-06, SHA pinning in S-05.
- **Steps:**
  1. Settings, Branches, add a rule for `master`: require the `test (3.11)` and `test (3.13)` checks.
  2. Settings, Code security: turn on Dependabot security updates.
  3. Triage the seven open Dependabot PRs (#1 to #7, open since 2026-09-02). #6 raises the `openai` floor to 3.6; the new `timeout`/`max_retries` arguments work on it (installed locally: 3.6.0).
- **Recommendation:** all three. After the action bumps merge, pin `actions/checkout` and `actions/setup-python` by SHA.

## B10. Nightly eval and drift job (needs a secret and the data)

- **Unlocks:** R-04, feature 7.
- **Built around it:** the eval CLI exits non-zero on its gates, bad LLM replies are counted, and drift is published on every site build.
- **Input:** an OpenRouter key as a GitHub Actions secret, format `sk-or-v1-` followed by 64 hex characters (copy it from openrouter.ai/keys; do not paste it into chat), stored as `OPENROUTER_API_KEY` under Settings, Secrets and variables, Actions. Plus a decision on where the Freddie Mac panel lives for CI (it is not redistributed): a private artifact, or a self-hosted runner.
- **Recommendation:** start with the judge and PTP evals only (no panel needed), weekly, not nightly, to cap API cost.

## B11. Release and security policy (publish, decision)

- **Unlocks:** P-05, P-06.
- **Input:** (1) permission to tag `v0.1.0` and publish a GitHub release (CITATION.cff already claims 0.1.0). (2) a response time for SECURITY.md, for example "acknowledge within 5 working days".
- **Recommendation:** tag after this PR merges, so the release carries the corrected figures.

## B12. Meta description and title copy (copy)

- **Unlocks:** O-03, O-04.
- **Fact:** 8 of 9 descriptions run 161 to 216 characters; titles are brand-only ("About · Ganymede").
- **Input:** approve trimmed copy, or supply your own. Example: "Collections risk glossary · Ganymede".

## B13. Merge and deploy (yours by rule)

- Merging this PR changes the production site's headline numbers (the +59% becomes +72.5%, the drift story changes). Vercel deploys from `master`. Review the draft PR, then merge.
