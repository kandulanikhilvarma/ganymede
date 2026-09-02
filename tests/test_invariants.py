"""The invariant checker itself must pass on a clean tree and catch violations."""

from datetime import datetime

from ganymede.invariants import (
    check_no_synthetic_in_lift,
    check_propensities,
    run_static,
)
from ganymede.schema import Action, Arm, Decision


def test_static_invariants_pass_on_clean_tree():
    assert run_static() == []


def _decision(prop):
    return Decision(
        borrower_id="b",
        ts=datetime.now(),
        action=Action.REMINDER,
        arm=Arm.FULL,
        propensity=prop,
    )


def test_propensity_check_passes_when_present():
    assert check_propensities([_decision(0.7), _decision(0.2)]) is None


def test_propensity_check_catches_zero():
    # A zero propensity would divide-by-zero in IPW. Must be caught.
    assert check_propensities([_decision(0.0)]) is not None


def test_lift_refused_on_synthetic():
    # I1
    assert check_no_synthetic_in_lift([False, False, True]) is not None
    assert check_no_synthetic_in_lift([False, False, False]) is None
