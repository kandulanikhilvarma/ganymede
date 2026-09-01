# Phase status

Strictly sequential. A phase starts only when the previous gate is green.

| # | Phase | State | Gate | Result |
|---|---|---|---|---|
| 0 | Spike | **blocked** | measured gap distribution + latency budget | needs `ANTHROPIC_API_KEY` + sample audio + human stopwatch |
| 1 | Foundation | **done** | `pytest tests/test_experiment.py` + CI green + schema frozen | 21 tests pass; invariants OK; schema v1.0.0 |
| 2 | Panel | **done** | `panel.py --verify` | 1.4M rows, 87.8k loans, 9 vintages, full roll curve; sample_weight recorded |
| 3 | Risk models | **done** | `risk --backtest` per-model gate | L1 AUC 0.62 beats base Brier; L2 AUC 0.67; self-cure drift documented; L3 deferred (no contact data) |
| 4 | Allocator | **done** | `allocator --simulate` | +59.1% recovered value vs risk-ranking, fewer contacts; uplift modelled not measured (I1) |
| 5 | Borrower state | **done** | `test_state.py` | 6/6 archetypes; 98% route to diagnostic question (willingness needs conversation data) |
| 6 | Conversations + extraction | not started | `outcomes --verify` | needs API key |
| 7 | Coach Lens | not started | `test_coach.py` in latency budget | needs Phase 0 budget |
| 8 | Evals | not started | `evals --report` | — |
| 9 | Agent Desk | not started | deployed URL, replay works | — |
| 10 | Case + roadmap | not started | three documents | — |

## Blocked on the user

1. `ANTHROPIC_API_KEY` — not in env (only `ANTHROPIC_BASE_URL` set). Blocks Phase 0 hint generation, Phase 6 generation, Phase 8 judging.
2. Freddie Mac SF Loan-Level registration (free) — blocks Phase 2.
3. Kaggle token or manual Home Credit download into `data/raw/` — Phase 2 feature enrichment.
4. Sample telephony audio for the Phase 0 VAD gap measurement.

## Notes

- Phase 1 built ahead of Phase 0 because Phase 0 is human-in-loop + API-gated
  and Phase 1 is pure structure with no external dependency. The Phase 0 gate
  (a measured latency budget) still blocks Phase 7, so nothing latency-gated
  proceeds until it is done.
