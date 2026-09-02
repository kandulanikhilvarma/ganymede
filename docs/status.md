# Phase status

Strictly sequential. A phase starts only when the previous gate is green.

| # | Phase | State | Gate | Result |
|---|---|---|---|---|
| 0 | Spike | **VAD half done** | gap distribution + latency budget | budget=300ms measured (p25 of 328 gaps); human-stopwatch half still open |
| 1 | Foundation | **done** | `pytest tests/test_experiment.py` + CI green + schema frozen | 21 tests pass; invariants OK; schema v1.0.0 |
| 2 | Panel | **done** | `panel.py --verify` | 1.4M rows, 87.8k loans, 9 vintages, full roll curve; sample_weight recorded |
| 3 | Risk models | **done** | `risk --backtest` per-model gate | L1 AUC 0.62 beats base Brier; L2 AUC 0.67; self-cure drift documented; L3 deferred (no contact data) |
| 4 | Allocator | **done** | `allocator --simulate` | +59.1% recovered value vs risk-ranking, fewer contacts; uplift modelled not measured (I1) |
| 5 | Borrower state | **done** | `test_state.py` | 6/6 archetypes; 97.5% route to diagnostic question (willingness needs conversation data) |
| 6 | Conversations + extraction | **done** | `outcomes --verify` | PTP extractor 93.4% (bar 80%); generate->extract->resolve, no drops |
| 7 | Coach Lens | **done** | `test_coach.py` | tier-1 0.04ms, tier-2 demotes at 4.5s; promise-quality + diagnostic + strategy hints |
| 8 | Evals | **done** | `evals.report --report` | judge 91.7% agree, alpha under ceiling; drift monitors; pilot metrics honestly pending |
| 9 | Agent Desk | **done** | deployed URL, replay works | published Artifact; real scored replay, hints fire, override, control arm |
| 10 | Case + roadmap | **done** | three documents | docs/CASE.md + published case artifact; results, pilot design, gap analysis |

## Blocked on the user

1. `ANTHROPIC_API_KEY`, not in env (only `ANTHROPIC_BASE_URL` set). Blocks Phase 0 hint generation, Phase 6 generation, Phase 8 judging.
2. Freddie Mac SF Loan-Level registration (free), blocks Phase 2.
3. Kaggle token or manual Home Credit download into `data/raw/`. Phase 2 feature enrichment.
4. Sample telephony audio for the Phase 0 VAD gap measurement.

## Notes

- Phase 1 built ahead of Phase 0 because Phase 0 is human-in-loop + API-gated
  and Phase 1 is pure structure with no external dependency. The Phase 0 gate
  (a measured latency budget) still blocks Phase 7, so nothing latency-gated
  proceeds until it is done.
