"""Deterministic tier-1 checks. No model, so they render inside the 300ms budget.

The highest-ROI hint in the system lives here: the promise-quality prompt. A
vague promise ("I'll try next week") and a specific one ("EUR 150 on the 3rd by
direct debit") have very different kept-rates, and turning the first into the
second is a one-line nudge. That is worth more per unit of build than anything
the LLM composes.

Checkpoints are ordered by priority; the first unmet one fires. Detection is
keyword/heuristic on the transcript so far plus the extracted promise — all
deterministic, all fast.
"""

from __future__ import annotations

import re

from ..schema import Hint, Promise

_EUR = re.compile(r"(€|\beur\b|\beuros?\b|\d{2,})", re.IGNORECASE)
_IDENTITY = re.compile(r"\b(speaking|yes,? this is|that's me|yes it is)\b", re.IGNORECASE)


def checklist_hint(transcript_so_far: str, promise: Promise | None) -> Hint | None:
    """Return the first unmet checkpoint as a deterministic hint, or None."""
    t = transcript_so_far.lower()

    # 1. Identity not yet confirmed — must happen before discussing the debt.
    if not _IDENTITY.search(transcript_so_far):
        return Hint(text="Confirm you're speaking to the account holder before discussing the balance.",
                    is_deterministic=True)

    # 2. A promise was made but is vague — the promise-quality nudge.
    if promise is not None and not promise.is_specific:
        missing = []
        if promise.amount is None:
            missing.append("an amount")
        if promise.due is None:
            missing.append("a date")
        if promise.method is None:
            missing.append("a method")
        return Hint(text=f"Pin the promise down: ask for {', '.join(missing)}. "
                         f"Specific promises are kept far more often than vague ones.",
                    is_deterministic=True)

    return None
