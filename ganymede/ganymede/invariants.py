"""Runnable checks for the design invariants (I1-I14).

`python -m ganymede.invariants --check` runs every invariant that can be
checked statically against the codebase and the current data, and exits
non-zero if any is violated. This is the mechanism behind the standing rule:
a defect is closed when something automated fails if it comes back.

Invariants that can only be checked against live data (e.g. I3 propensity
completeness on a decision log) are exposed as functions here and called by
the retrain and eval paths with the actual data in hand.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable

from .schema import Decision

# Registry of statically-checkable invariants: id -> (description, predicate).
# A predicate returns None on pass, or a string explaining the violation.
_STATIC: dict[str, tuple[str, "callable"]] = {}


def _static(inv_id: str, description: str):
    def register(fn):
        _STATIC[inv_id] = (description, fn)
        return fn

    return register


@_static("I2", "every Decision carries an experiment arm")
def _i2():
    # Enforced by the type: Decision.arm is non-optional. Confirm the field
    # has not been made optional in a later edit.
    field = Decision.model_fields["arm"]
    return None if field.is_required() else "Decision.arm became optional"


@_static("I3", "every Decision carries a propensity")
def _i3():
    field = Decision.model_fields["propensity"]
    return None if field.is_required() else "Decision.propensity became optional"


def check_propensities(decisions: Iterable[Decision]) -> str | None:
    """I3 against live data: no decision in a retrain/eval window may lack a
    usable propensity. Called by the retrain and OPE paths."""
    for d in decisions:
        if not (0.0 < d.propensity <= 1.0):
            return f"I3: decision for {d.borrower_id} has unusable propensity {d.propensity}"
    return None


def check_no_synthetic_in_lift(is_synthetic_flags: Iterable[bool]) -> str | None:
    """I1: lift may not be computed on a set containing synthetic records.
    Called by evals/metrics.py before any lift calculation."""
    if any(is_synthetic_flags):
        return "I1: refusing to compute predictive lift on a set containing synthetic records"
    return None


def run_static() -> list[str]:
    violations = []
    for inv_id, (desc, fn) in sorted(_STATIC.items()):
        result = fn()
        if result is not None:
            violations.append(f"{inv_id} ({desc}): {result}")
    return violations


def main() -> int:
    violations = run_static()
    if violations:
        print("INVARIANT VIOLATIONS:")
        for v in violations:
            print(f"  FAIL {v}")
        return 1
    print(f"static invariants OK ({len(_STATIC)} checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
