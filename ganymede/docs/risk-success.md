# Risk Lens — success definition and Phase 3 results

Defined before modelling, not fitted to the output. Each model is judged on the
metric its product use actually needs — a probability an agent reads is judged
on calibration; a ranking the allocator consumes is judged on discrimination.

## Models built

| Model | Predicts | Product use | Gate | Result |
|---|---|---|---|---|
| **L1 trajectory** | worsening over next 3 months | the early-warning score an agent reads | calibration: Brier beats base | **AUC 0.622, Brier 0.211 < 0.218** ✓ |
| **L2 self-cure** | delinquent returns to current, no contact | ranking so the allocator skips likely self-curers | discrimination: AUC ≥ 0.60 | **AUC 0.674** ✓ |

Backtested on a held-out **time** slice (train ≤ 2025-06, test ≥ 2025-07), never a
random split — a random split leaks the future into the past on a panel.

## Why two different gates

L1 outputs a number a human acts on, so it must be *calibrated* — 0.7 has to mean
70%. Brier-beats-base is the right test.

L2 outputs a *ranking*: the allocator uses it to decide which delinquent accounts
will cure on their own and can be left alone (the "do not contact" money, I10).
For a ranking, discrimination (AUC) is what matters, and Brier-beats-base is a
poor gate — L2's base rate (0.7–0.9) makes the constant predictor nearly
unbeatable regardless of model quality. Judging L2 on Brier would fail a good
model for a reason that has nothing to do with its job.

## The finding: self-cure drift

Self-cure rate rose sharply across the split — **train 0.60 → test 0.72**. The
model's ranking is intact (reliability is monotonic), but its absolute
calibration lags, because no model can calibrate to a regime shift that postdates
its training data.

This is not a defect to fix by tuning; it is the exact condition the outcome loop
and drift monitor exist for. In production, calibration recalibrates continuously
from recent outcomes while the ranking model stays stable. The Phase 8 drift
monitor watches self-cure rate specifically.

## Reason codes

Every score carries its top-3 SHAP drivers as plain phrases — LightGBM's native
per-feature contributions, not an LLM. Verified on held-out rows:

- high risk → *currently behind · delinquency worsening over 3 months · recent peak delinquency*
- low risk → *delinquency easing · stronger credit profile*

An agent will not trust a bare number, and should not. The number arrives with why.

## What is not built, and why

**L3 contactability** (best hour × channel) needs contact-event history. Freddie
Mac has none — it is servicing data, not outreach data. Building L3 on it would
mean inventing contact patterns that do not exist in the source, the kind of
fabricated result this project refuses. L3 waits for linked contact data; the
haessigDB calls and the sales transcript are conversations, not outcome-linked
outreach logs, so they do not fill the gap either.
