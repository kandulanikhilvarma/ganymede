"""Turn-boundary gating and the two-tier latency contract.

A hint is only surfaced at a hint-eligible boundary: a VAD pause long enough to
be a real turn hand-off (>= the min gap), not a within-speech micro-pause.

The latency contract, measured in Phase 0 (median gap 479ms, p25 292ms):
  - a deterministic hint must render within LATENCY_BUDGET_MS (300) -> it makes
    the live gap;
  - an LLM-composed hint that takes longer than the budget is demoted to the
    next boundary rather than dropped on top of the agent mid-sentence.

deliver() enforces exactly that: it times the production of a hint and returns
either (hint, "live") if it fit, or (hint, "next_turn") if it overran.
"""

from __future__ import annotations

import time

from ..config import require_latency_budget
from ..schema import Hint

MIN_TURN_GAP_MS = 200  # matches the VAD inter-turn threshold


def is_hint_eligible(pause_ms: float) -> bool:
    return pause_ms >= MIN_TURN_GAP_MS


def deliver(produce_hint) -> tuple[Hint | None, str]:
    """Run produce_hint(), time it, and decide live vs demoted.
    produce_hint is a zero-arg callable returning Hint | None."""
    budget = require_latency_budget()
    t0 = time.perf_counter()
    hint = produce_hint()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    if hint is None:
        return None, "none"
    if hint.is_deterministic or elapsed_ms <= budget:
        return hint, "live"
    return hint, "next_turn"  # LLM composition overran the gap
