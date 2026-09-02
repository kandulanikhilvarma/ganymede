"""Central config. Thresholds live here so no magic numbers hide in components.

LATENCY_BUDGET_MS is deliberately None until Phase 0 measures the real
inter-turn gap distribution (I4). Any component that reads it before it is set
should fail loudly rather than assume a number — a guessed budget is exactly
the defect I4 exists to prevent.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"

# --- Experiment ---
SCHEMA_TAG = "1.0.0"

# --- Latency (I4) ---
# MEASURED in Phase 0 from silero/energy-VAD over 10.3 min of real 2-way call
# audio: 328 inter-turn gaps, median 479ms, p25 292ms, p10 239ms. The budget is
# p25 -> a tier-1 (deterministic) hint rendering within 300ms catches at least
# ~75% of turn boundaries. Tier-2 (LLM-composed) hints cannot meet this and are
# demoted to the next pause by design — measured, not guessed.
LATENCY_BUDGET_MS: int | None = 300


def require_latency_budget() -> int:
    if LATENCY_BUDGET_MS is None:
        raise RuntimeError(
            "I4: latency budget unset. Run the Phase 0 spike and record the "
            "measured p95 inter-turn gap before any latency-gated code runs."
        )
    return LATENCY_BUDGET_MS


# --- Allocator ---
# lambda: how much future book you refuse to trade for this quarter's recovery.
# A governance decision, not a default. Starts conservative.
LAMBDA_HARM: float = 1.0

# --- Coach Lens ---
MAX_HINTS_PER_CONVERSATION: int = 4  # I11 ceiling; tuned once real data exists
MIN_STRATEGY_SUPPORT: int = 5  # I5 gate before a strategy is outcome-promoted
