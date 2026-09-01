"""Phase 5 gate. Quadrant agreement against constructed archetypes, and the
requirement that uncertainty fires when signals are mixed."""

from ganymede.schema import Capacity, Willingness
from ganymede.state import estimate_state, strategy_for

# Hand-specified archetypes: each has signals that point unambiguously at one
# quadrant. These stand in for hand-labelled cases (no real labels exist).
DISORGANISED = {  # can pay, will pay — strong credit, paying, shallow
    "credit_score": 780, "dti": 20, "orig_ltv": 65, "d": 1,
    "delinq_trend_3m": 0, "delinq_max_3m": 1, "upb_change_3m": -900.0, "any_delinq_3m": 1,
}
STRATEGIC = {  # can pay, will NOT pay — strong credit, able, but stopped paying
    "credit_score": 770, "dti": 22, "orig_ltv": 60, "d": 2,
    "delinq_trend_3m": 1, "delinq_max_3m": 2, "upb_change_3m": 0.0, "any_delinq_3m": 1,
}
WILLING_BROKE = {  # cannot pay, will pay — weak affordability but still paying down
    "credit_score": 600, "dti": 55, "orig_ltv": 96, "d": 3,
    "delinq_trend_3m": 1, "delinq_max_3m": 3, "upb_change_3m": -300.0, "any_delinq_3m": 1,
}
DISTRESSED_AVOIDER = {  # cannot pay, will NOT pay — deep, worsening, not paying
    "credit_score": 590, "dti": 58, "orig_ltv": 97, "d": 5,
    "delinq_trend_3m": 2, "delinq_max_3m": 5, "upb_change_3m": 500.0, "any_delinq_3m": 1,
}
AMBIGUOUS = {  # mixed signals -> should not resolve to a confident quadrant
    "credit_score": 680, "dti": 40, "orig_ltv": 80, "d": 2,
    "delinq_trend_3m": 0, "delinq_max_3m": 2, "upb_change_3m": 0.0, "any_delinq_3m": 1,
}


def test_disorganised_payer():
    s = estimate_state(DISORGANISED)
    assert s.capacity is Capacity.CAN_PAY
    assert s.willingness is Willingness.WILL_PAY


def test_strategic_defaulter():
    s = estimate_state(STRATEGIC)
    assert s.capacity is Capacity.CAN_PAY
    assert s.willingness is Willingness.WILL_NOT_PAY


def test_willing_but_broke():
    s = estimate_state(WILLING_BROKE)
    assert s.capacity is Capacity.CANNOT_PAY
    assert s.willingness is Willingness.WILL_PAY


def test_distressed_avoider():
    s = estimate_state(DISTRESSED_AVOIDER)
    assert s.capacity is Capacity.CANNOT_PAY
    assert s.willingness is Willingness.WILL_NOT_PAY


def test_uncertainty_fires_on_ambiguous():
    s = estimate_state(AMBIGUOUS)
    assert not s.is_certain
    assert strategy_for(s).startswith("DIAGNOSTIC")


def test_certain_state_gets_a_strategy():
    s = estimate_state(DISORGANISED)
    strat = strategy_for(s)
    assert not strat.startswith("DIAGNOSTIC")
    assert "friction" in strat or "autopay" in strat
