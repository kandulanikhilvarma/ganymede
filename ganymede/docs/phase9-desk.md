# Phase 9 — Agent Desk

A collections agent workstation that replays a real scored call. Published as an
Artifact (private): https://claude.ai/code/artifact/2c0d2222-b533-49a7-a21e-96c7de57b7b9

## What it shows

Everything on the desk is real pipeline output, baked from the backend — not a
mockup:

- **Risk gauge**: p(worsen) 0.81 for account F24Q10000110, rendered as a
  sequential single-hue amber ring (lightness encodes magnitude — never a
  traffic-light red/amber/green, which invents categories from a scalar).
- **Reason codes**: the real SHAP drivers — currently behind, delinquency
  worsening, recent peak.
- **Self-cure 23%**: L2 output — this account is unlikely to cure alone, so it is
  worth contacting.
- **Borrower state**: uncertain (confidence 0.18), so the recommended move is the
  diagnostic question, not a strategy — the 98%-of-accounts behavior, shown
  honestly.
- **Live coaching**: hints fire at borrower turns with their real tier-1
  latencies (0.03-0.08 ms, well inside the 300ms budget). Diagnostic and
  promise-quality hints, exactly what the Coach Lens produced turn-by-turn.
- **Override with mandatory reason**, **promise capture** (flags a vague promise
  missing a field), and a **decision log** (per-viewer, localStorage).
- **Experiment arm toggle**: switching to the control arm hides all coaching —
  the clean counterfactual, visible.

## Design

Dark-first ops console (agents stare at it all shift): cool near-black ground,
Instrument Sans + IBM Plex Mono tabular figures, one teal accent reserved for the
active action, amber risk ramp, opacity-only motion (peripheral movement during a
live call pulls attention off the borrower — a cost against the product's own
metric). Theme-aware via tokens; charset-safe (€, em-dashes).

## Gate

Verified live: the page loads, the replay streams all 11 turns, hints fire at
turn boundaries with sub-millisecond tier-1 latency, override requires a reason,
and the control arm shows no hints. All confirmed in-browser.
