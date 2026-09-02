# Allocator. Phase 4 result

The D9 fix, quantified. Conventional collections sorts by probability of default
and works the top of the list. The allocator maximises expected recovered value
per agent-minute under a capacity constraint, subtracting self-cure (I10) and
weighting by exposure.

## Simulation

On the test-period delinquent queue (58,931 accounts), same capacity budget:

| Policy | Recovered value | Contacts |
|---|---|---|
| Risk-ranking (baseline) | 543,632,774 | 8,839 |
| **Allocator** | **865,138,287** | **4,243** |

**+59.1% recovered value, with fewer than half the contacts.**

## Why it wins

- **Fewer contacts, more money.** The allocator declines negative-value contacts
  even with budget left. Risk-ranking blindly fills capacity with a fixed action,
  spending on accounts that would cure anyway or where exposure is trivial.
- **Exposure weighting.** A 40%-risk account owing 200k outranks a 95%-risk
  account owing 2k. Risk-ranking gets this backwards.
- **Self-cure subtracted.** Likely self-curers drop out of the queue (I10),
  freeing minutes for the persuadable middle.

## The honest caveat

Freddie Mac has no treatment data, so the *uplift* term. P(recover | contact) −
P(self-cure), is **modelled, not measured**. The shape is from the uplift
literature: effect peaks in the persuadable middle and vanishes at both ends.
This proves the allocator's *logic* dominates risk-ranking under a defensible
uplift structure. The magnitude (+59%) is a property of the assumed shape, not a
real-world promise. Measuring true uplift needs the randomised control arm and a
pilot (I1, I2). Stated plainly, not buried.
