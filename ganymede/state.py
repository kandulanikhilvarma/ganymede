"""Borrower state: capacity x willingness (D7 / I7).

Four quadrants, four opposite correct treatments. Coaching negotiation at
someone genuinely broke produces a promise that cannot be kept — worse than no
promise, because a broken promise poisons the next conversations and corrupts
the training label. So strategy must branch on state, and when state is unclear
the honest move is to surface the diagnostic question, not guess.

                    WILL NOT PAY            WILL PAY
    CANNOT PAY      distressed avoider      willing but broke
    CAN PAY         strategic defaulter     disorganised payer

Estimability on this data, stated plainly:
  capacity   — well estimated from trajectory shape + credit/DTI/LTV.
  willingness — weak here. Freddie Mac has no contact, no promises, no channel
                response. It is proxied from payment BEHAVIOUR (making partial
                payments reads as willing; able-but-stopped reads as strategic).
                Low confidence by construction; conversation data is what would
                make this axis strong (Phase 6+).

No supervised labels exist for these quadrants, so this is a transparent scoring
heuristic grounded in documented signal meanings — not a trained classifier
dressed up as one. Confidence is an output; below threshold the quadrant is
UNKNOWN and Coach Lens asks rather than assumes.
"""

from __future__ import annotations

from .schema import BorrowerState, Capacity, Willingness

DEAD_ZONE = 0.12  # distance from 0.5 within which an axis is UNKNOWN


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def capacity_score(f: dict) -> float:
    """1.0 = can pay. Trajectory shape and affordability signals."""
    s = 0.5
    cs = f.get("credit_score") or 680
    if cs >= 720:
        s += 0.25
    elif cs < 620:
        s -= 0.25
    if (f.get("dti") or 0) > 43:
        s -= 0.20
    if (f.get("orig_ltv") or 0) > 90:
        s -= 0.05
    # deep and worsening arrears read as capacity erosion
    if (f.get("delinq_max_3m") or 0) >= 3 and (f.get("delinq_trend_3m") or 0) > 0:
        s -= 0.25
    # shallow and improving reads as capacity intact
    if (f.get("d") or 0) <= 1 and (f.get("delinq_trend_3m") or 0) <= 0:
        s += 0.15
    return _clamp(s)


def willingness_score(f: dict) -> float:
    """1.0 = will pay. Proxied from payment behaviour — the weak axis here."""
    s = 0.5
    d = f.get("d") or 0
    upb_change = f.get("upb_change_3m")
    if upb_change is not None:
        if upb_change < 0:          # balance coming down -> making payments
            s += 0.30
            if d <= 1:              # paying AND barely behind -> clearly engaged
                s += 0.15
        elif d >= 1:                # delinquent and balance not moving
            s -= 0.20
    # a recent bout of delinquency now easing reads as re-engaging
    if (f.get("any_delinq_3m") or 0) == 1 and (f.get("delinq_trend_3m") or 0) < 0:
        s += 0.10
    return _clamp(s)


def _axis(score: float, low, high):
    """Map a score to an enum, with a dead-zone around 0.5 -> UNKNOWN."""
    if score >= 0.5 + DEAD_ZONE:
        return high
    if score <= 0.5 - DEAD_ZONE:
        return low
    return None  # unknown


def estimate_state(f: dict) -> BorrowerState:
    cap_s = capacity_score(f)
    wil_s = willingness_score(f)
    cap = _axis(cap_s, Capacity.CANNOT_PAY, Capacity.CAN_PAY) or Capacity.UNKNOWN
    wil = _axis(wil_s, Willingness.WILL_NOT_PAY, Willingness.WILL_PAY) or Willingness.UNKNOWN

    # confidence: how far both axes sit from their dead-zone edges, penalised for
    # any UNKNOWN axis. Willingness is inherently capped low on this data.
    cap_conf = max(0.0, abs(cap_s - 0.5) - DEAD_ZONE) / (0.5 - DEAD_ZONE)
    wil_conf = max(0.0, abs(wil_s - 0.5) - DEAD_ZONE) / (0.5 - DEAD_ZONE)
    wil_conf *= 0.85  # no contact data -> willingness never fully trusted here
    confidence = round(min(cap_conf, wil_conf), 3)

    return BorrowerState(capacity=cap, willingness=wil, confidence=confidence)


QUADRANT_STRATEGY = {
    (Capacity.CANNOT_PAY, Willingness.WILL_NOT_PAY): "re-establish contact safely, then hardship assessment",
    (Capacity.CANNOT_PAY, Willingness.WILL_PAY): "affordability first, small realistic plan, do not over-promise",
    (Capacity.CAN_PAY, Willingness.WILL_NOT_PAY): "state consequences, firm, escalation path",
    (Capacity.CAN_PAY, Willingness.WILL_PAY): "remove friction, autopay, one nudge",
}


def strategy_for(state: BorrowerState) -> str:
    """The branch. Uncertain state does not get a strategy — it gets a question."""
    if not state.is_certain:
        return "DIAGNOSTIC: ask the question that resolves capacity vs willingness"
    return QUADRANT_STRATEGY[(state.capacity, state.willingness)]
