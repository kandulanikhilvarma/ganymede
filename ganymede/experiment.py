"""Experiment arm assignment (I2) and propensity logging (I3).

Assignment is deterministic from borrower_id, so a borrower keeps the same arm
across every conversation — randomising per-conversation would leak treatment
across a relationship (see the causal DAG in the plan). Determinism also means
the assignment is reproducible without storing it.

The propensity returned alongside the arm is what makes the log usable for
inverse-propensity weighting and doubly robust off-policy evaluation later. A
decision written without it cannot be used to evaluate a new policy, which is
why schema.Decision makes it non-optional.
"""

from __future__ import annotations

import hashlib

from .schema import Arm

# Default split. CONTROL is small but permanent — it is how model rot is caught,
# and it is the randomised data uplift models need to train on.
DEFAULT_SPLIT: dict[Arm, float] = {
    Arm.FULL: 0.70,
    Arm.RISK_ONLY: 0.20,
    Arm.CONTROL: 0.10,
}


def _unit_hash(borrower_id: str, salt: str) -> float:
    """Stable [0, 1) hash. Salt lets the experiment be reshuffled deliberately
    without changing the hashing anywhere else."""
    h = hashlib.sha256(f"{salt}:{borrower_id}".encode()).hexdigest()
    return int(h[:16], 16) / float(1 << 64)


def assign_arm(
    borrower_id: str,
    split: dict[Arm, float] | None = None,
    salt: str = "ganymede-v1",
) -> tuple[Arm, float]:
    """Return (arm, propensity). Propensity is the probability THIS borrower had
    of landing in the arm they got — i.e. the arm's share of the split. That is
    the quantity IPW and DR-OPE need, not 1/n."""
    split = split or DEFAULT_SPLIT
    total = sum(split.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"split must sum to 1.0, got {total}")

    u = _unit_hash(borrower_id, salt)
    cumulative = 0.0
    for arm, share in split.items():
        cumulative += share
        if u < cumulative:
            return arm, share
    # Floating-point tail: assign to the last arm.
    last = list(split)[-1]
    return last, split[last]
