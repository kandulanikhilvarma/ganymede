"""Phase 1 exit gate. I2 + I3."""

from collections import Counter

import pytest

from ganymede.experiment import DEFAULT_SPLIT, assign_arm
from ganymede.schema import Arm


def test_assignment_is_deterministic():
    a1, p1 = assign_arm("borrower-123")
    a2, p2 = assign_arm("borrower-123")
    assert a1 == a2
    assert p1 == p2


def test_arm_is_sticky_across_calls():
    # Same borrower must keep the same arm forever, or treatment leaks across
    # a relationship (the whole reason for randomising by borrower not call).
    arms = {assign_arm("b-42")[0] for _ in range(50)}
    assert len(arms) == 1


def test_propensity_is_the_arm_share():
    # I3: propensity must be the probability the borrower had of this arm,
    # which is that arm's share of the split — usable for IPW / DR-OPE.
    arm, prop = assign_arm("b-7")
    assert prop == pytest.approx(DEFAULT_SPLIT[arm])


def test_propensity_always_present_and_valid():
    for i in range(1000):
        _, prop = assign_arm(f"b-{i}")
        assert 0.0 < prop <= 1.0


def test_split_roughly_honoured():
    counts = Counter(assign_arm(f"user-{i}")[0] for i in range(20_000))
    for arm, share in DEFAULT_SPLIT.items():
        observed = counts[arm] / 20_000
        assert abs(observed - share) < 0.02, f"{arm}: {observed} vs {share}"


def test_control_arm_is_never_empty():
    # A permanent control arm is how model rot is caught. It must actually
    # receive borrowers.
    counts = Counter(assign_arm(f"x-{i}")[0] for i in range(5000))
    assert counts[Arm.CONTROL] > 0


def test_bad_split_rejected():
    with pytest.raises(ValueError):
        assign_arm("b", split={Arm.FULL: 0.5, Arm.CONTROL: 0.4})  # sums to 0.9


def test_salt_reshuffles():
    # A deliberate reshuffle should move at least some borrowers.
    moved = sum(
        assign_arm(f"b-{i}", salt="v1")[0] != assign_arm(f"b-{i}", salt="v2")[0]
        for i in range(1000)
    )
    assert moved > 0
