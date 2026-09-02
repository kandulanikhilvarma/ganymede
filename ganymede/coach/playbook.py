"""Strategy playbook with min-support gating (I5).

Cold-start problem: on day one nothing has been measured, so the retrieval index
is empty. Fix — seed from collections/negotiation practice, mark every seeded
strategy as provisional, and show its support count on every hint so thin
evidence is visibly thin. A strategy is only promoted from provisional once real
outcomes back it above MIN_STRATEGY_SUPPORT; until then it is labelled seeded.

Retrieval matches on borrower-state quadrant and, when present, the detected
objection. Single best match — Coach Lens shows at most one hint, so there is no
value ranking a long list.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import MIN_STRATEGY_SUPPORT
from ..schema import Capacity, Willingness


@dataclass
class Strategy:
    id: str
    quadrant: tuple[Capacity, Willingness] | None  # None = any
    objection: str | None                            # None = any
    text: str
    support_count: int  # outcome-backed count; seeded strategies start below the bar

    @property
    def is_provisional(self) -> bool:
        return self.support_count < MIN_STRATEGY_SUPPORT


# Seed corpus. support_count starts at 0 (no measured outcomes yet) — every one
# is provisional until the outcome loop promotes it.
SEED: list[Strategy] = [
    Strategy("plan_small", (Capacity.CANNOT_PAY, Willingness.WILL_PAY),
             None, "Offer the smallest realistic instalment and let them name what they can manage. Do not push a figure they'll break.", 0),
    Strategy("hardship_first", (Capacity.CANNOT_PAY, Willingness.WILL_NOT_PAY),
             None, "Re-establish contact and safety before money. Acknowledge the situation, then ask one gentle affordability question.", 0),
    Strategy("firm_consequence", (Capacity.CAN_PAY, Willingness.WILL_NOT_PAY),
             None, "State the next consequence plainly and calmly, then offer a clear way to avoid it today.", 0),
    Strategy("remove_friction", (Capacity.CAN_PAY, Willingness.WILL_PAY),
             None, "This is friction, not inability. Offer to set up the payment right now on the call and get one confirmation.", 0),
    Strategy("obj_dispute", None, "dispute",
             "Acknowledge the dispute, log it, and separate the disputed portion from what is not in question so a partial payment can still move.", 0),
    Strategy("obj_cant_afford", None, "affordability",
             "Do not argue the amount. Walk through income and essential outgoings so the plan is one they can actually service.", 0),
    Strategy("obj_callback", None, "deferral",
             "A vague 'I'll call back' rarely converts, so offer a specific short window and confirm a callback time before ending.", 0),
]


def retrieve(quadrant: tuple[Capacity, Willingness] | None,
             objection: str | None) -> Strategy | None:
    """Best single strategy: an objection-specific match wins; else a quadrant
    match; else nothing."""
    if objection:
        for s in SEED:
            if s.objection == objection:
                return s
    if quadrant:
        for s in SEED:
            if s.quadrant == quadrant:
                return s
    return None
