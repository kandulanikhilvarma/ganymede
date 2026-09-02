# Phase 0 — latency budget (VAD half)

Measured, not guessed (I4). The human-stopwatch half — do hints help or distract —
still needs a person and remains open. This is the timing half.

## Method

silero/energy-VAD over 10.3 minutes of a real two-way call (decoded to 16kHz
mono). Inter-turn gaps = silences ≥200ms between speech segments — the windows a
coaching hint has to land in.

```
python -c "from ganymede.audio.vad import analyse; print(analyse('data/raw/call_16k.wav'))"
```

## Result

| Metric | Value |
|---|---|
| Duration | 620.5 s |
| Speech | 336.3 s (54%) |
| Speech segments | 803 |
| Inter-turn gaps (≥200ms) | 328 |
| Gap p50 | **479 ms** |
| Gap p25 | 292 ms |
| Gap p10 | 239 ms |

## Budget

**`LATENCY_BUDGET_MS = 300`** (p25). A hint rendering within 300ms catches at
least ~75% of turn boundaries.

## The finding: two tiers are forced by physics, not chosen

A median turn gap is **479ms**. LLM composition plus network is 500–1500ms. So:

- **Tier-1, deterministic hints** (compliance, checklist, promise-quality
  prompts) must be pre-resolved from the prior turn's state and render in
  <300ms. These can hit the live gap.
- **Tier-2, LLM-composed hints** cannot fit a 479ms gap. They must either be
  composed *during* the previous turn or demoted to the next detected pause.

This is the plan's two-tier delivery, now backed by measured data rather than
asserted. The demotion path in the architecture sequence diagram is not a
nice-to-have — it is the only physically available option for LLM hints.

## Caveats

- Energy VAD, not silero. Adequate for gap measurement on this audio; swap to
  silero (via the same interface) for robustness on noisy 8kHz telephony.
- One call. A production budget wants the gap distribution across many calls and
  accents. This is the Phase 0 read, not the final number.
- The human half of Phase 0 (hint usefulness / distraction) is not done here.
