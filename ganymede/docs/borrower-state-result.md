# Borrower state — Phase 5 result

Capacity x willingness, four quadrants (D7/I7), with confidence as a first-class
output. Strategy branches on the quadrant; uncertain state gets a diagnostic
question, not a guess.

## Gate

Six archetype cases (one per quadrant, plus ambiguous, plus a certain case) —
standing in for hand-labelled data, since no ground-truth quadrant labels exist.
All pass: each unambiguous archetype lands in its quadrant; the ambiguous case
fails to resolve and routes to a diagnostic question.

```
python -m pytest tests/test_state.py
```

## The finding: state needs conversation data

Run over 5,000 real delinquent accounts, **only 2% reach a confident quadrant.**
The other 98% route to the diagnostic question.

This is the correct behavior, not a shortfall. Capacity is well-estimated from
Freddie Mac (trajectory shape, credit, DTI, LTV). **Willingness is not** — the
data has no contact, no promises, no channel response, so the willingness axis is
proxied from payment behaviour and deliberately capped low in confidence. Without
a conversation, you cannot reliably tell a strategic defaulter from someone
quietly drowning.

That is exactly why the product has two lenses. The Risk Lens produces the queue
and a tentative state; the Coach Lens's first move, on 98% of these accounts, is
the question that resolves capacity vs willingness. The system asking instead of
assuming is the honest posture the whole design is built around — teaching an
agent what to *ask* beats telling them what to say when the model does not know.

## What would raise the 2%

Conversation-derived signals (Phase 6+): stated reason, promise history, channel
responsiveness, and the borrower's own words. Those move willingness from a weak
proxy to a real estimate. Until then, the diagnostic question is the answer.
