# Phase 7 — Coach Lens

At most one hint at a time, two tiers, rate-limited. Single agent (one model call
per strategy hint), not a crew — a debate while a human is mid-sentence is the
wrong shape at any latency.

## Two tiers, measured

| Tier | Source | Latency | Fits 479ms median gap? |
|---|---|---|---|
| Tier-1 deterministic | checklist rules | **0.043 ms** | yes, 7,000x under the 300ms budget |
| Tier-2 LLM strategy | playbook + compose | **4,511 ms** | no -> demoted to next turn |

The demotion is not a fallback that rarely fires — it is the normal path for LLM
hints, forced by physics (Phase 0: median gap 479ms, LLM 500-1500ms+). Tier-1
hints hit the live gap; tier-2 hints are pre-composed during the prior turn or
surfaced at the next pause. `deliver()` times each hint and routes it.

## The hints

- **Promise-quality (tier-1, highest ROI).** A vague promise fires "pin the
  promise down: ask for an amount, a date, a method." Deterministic, instant.
- **Identity (tier-1).** Fires before the balance is discussed if the account
  holder is not yet confirmed.
- **Diagnostic question (tier-1).** When borrower state is uncertain — 98% of
  accounts on servicing data — the hint is the question that resolves capacity vs
  willingness, never a guessed strategy (I7).
- **Strategy (tier-2, LLM).** Composed from the playbook for a certain quadrant or
  a detected objection. Every strategy hint carries its support count (I5); seeded
  strategies are labelled "(seeded, not yet outcome-backed)" so thin evidence is
  visible. Live example on a dispute: "Ask what specifically they're disputing,
  then propose paying the undisputed balance now."

## Gate

```
pytest tests/test_coach.py
```

Every hint validates (schema enforces support on strategy hints); tier-1 renders
inside the 300ms budget; the rate ceiling (4 per conversation, I11) blocks
excess; a slow LLM hint demotes to next turn. All pass.

## Cold start (I5)

The playbook seeds from collections/negotiation practice with support_count 0 —
every strategy provisional until the outcome loop promotes it above the support
bar. Nothing is presented as outcome-backed before it is.
