# Phase 6 — conversations, extraction, outcomes

The conversation half of the loop, closed end to end: generate a call from a real
trajectory seed, extract the promise, resolve it against real subsequent payment.

## PTP extractor cleared (I6)

The extractor sits inside the label path, so it clears a gold set before anything
uses it. 25 hand-labelled cases spanning specific promises, vague intentions,
partial offers, and refusals:

| Metric | Result | Bar |
|---|---|---|
| Field-level accuracy | **0.934** | 0.80 |
| Promise-vs-no-promise | **0.92** | — |

Run on the cheap extraction model (deepseek), not the expensive one — the routing
table earns its place. Reproducible: `GANYMEDE_LIVE_LLM=1 pytest tests/test_ptp_live.py`.

## Generation

Each conversation is seeded from a real delinquent panel row (arrears depth,
exposure) plus its borrower-state quadrant. The generator is told the situation
but not the outcome, so it cannot write the answer in (I1). Every conversation is
flagged `is_synthetic=True` at the source — which is what lets the eval layer
refuse to compute lift on it.

Sample output (cannot-pay / will-pay seed) reads true: the borrower expresses
hardship and intent to resolve, matching the quadrant it was seeded from.

## Outcome resolver — the gate

Generate -> extract -> resolve, no silent drops:

```
python -m ganymede.outcomes --verify --n 12
```

12 conversations, 9 promises, all resolved. Distribution 8 broken / 3 none /
1 kept — the seed loans mostly did not improve in the next panel month, so most
promises broke. Honest, because the outcome is derived from real repayment
behaviour, not from the generator.

## Scope

Ran a 12–25 item batch to clear the gate cheaply. The functions take an `n`, so a
1,200-conversation set is a scale-up run when budget allows — the pipeline is the
deliverable, not the volume.
