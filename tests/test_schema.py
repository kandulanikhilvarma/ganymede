"""Schema-level invariants: I2, I3, I5, I10, and the override-reason rule."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from ganymede.schema import (
    Action,
    Arm,
    Capacity,
    BorrowerState,
    Decision,
    Hint,
    Promise,
    Willingness,
)


def test_decision_requires_arm_and_propensity():
    with pytest.raises(ValidationError):
        Decision(borrower_id="b", ts=datetime.now(), action=Action.REMINDER)


def test_valid_decision():
    d = Decision(
        borrower_id="b",
        ts=datetime.now(),
        action=Action.REMINDER,
        arm=Arm.FULL,
        propensity=0.7,
    )
    assert d.arm is Arm.FULL


def test_do_not_contact_is_an_action():
    # I10: not contacting is a decision, not a missing row.
    assert Action.DO_NOT_CONTACT in set(Action)


def test_strategy_hint_needs_support_count():
    # I5
    with pytest.raises(ValidationError):
        Hint(text="offer a plan", is_deterministic=False)


def test_deterministic_hint_needs_no_support():
    h = Hint(text="outside contact window", is_deterministic=True)
    assert h.support_count is None


def test_override_needs_reason():
    with pytest.raises(ValidationError):
        Decision(
            borrower_id="b",
            ts=datetime.now(),
            action=Action.PLAN_OFFER,
            arm=Arm.FULL,
            propensity=0.7,
            agent_action=Action.ESCALATE,  # differs, no reason
        )


def test_override_with_reason_ok():
    d = Decision(
        borrower_id="b",
        ts=datetime.now(),
        action=Action.PLAN_OFFER,
        arm=Arm.FULL,
        propensity=0.7,
        agent_action=Action.ESCALATE,
        override_reason="borrower disclosed job loss",
    )
    assert d.override_reason


def test_promise_specificity():
    vague = Promise(borrower_id="b", extractor_confidence=0.9)
    specific = Promise(
        borrower_id="b",
        amount=150.0,
        due=date(2026, 10, 3),
        method="direct_debit",
        extractor_confidence=0.9,
    )
    assert not vague.is_specific
    assert specific.is_specific


def test_borrower_state_certainty_gates_on_confidence():
    certain = BorrowerState(
        capacity=Capacity.CAN_PAY, willingness=Willingness.WILL_PAY, confidence=0.8
    )
    unsure = BorrowerState(
        capacity=Capacity.CAN_PAY, willingness=Willingness.WILL_PAY, confidence=0.4
    )
    assert certain.is_certain
    assert not unsure.is_certain
