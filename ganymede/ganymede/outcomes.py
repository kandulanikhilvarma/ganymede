"""Outcome resolver: promise vs actual payment -> kept / broken / partial / none.

Closes the loop. Every promise must resolve to a status with no silent drops —
a dropped promise is a missing training label, and the whole system learns from
these. The Phase 6 gate asserts exactly that.

On synthetic conversations the "actual payment" comes from the seed loan's real
next-month panel behaviour: if delinquency improved after the promise month, the
loan paid; if it held or worsened, it did not. This keeps the outcome honest —
derived from real repayment data, not written by the generator (I1).
"""

from __future__ import annotations

import argparse
from datetime import date

import polars as pl

from .panel import PANEL_PATH
from .schema import Outcome, Promise, PromiseStatus


def resolve(promise: Promise | None, paid: bool, amount_paid: float = 0.0,
            resolved_on: date | None = None) -> Outcome:
    """Resolve one promise against whether payment actually arrived."""
    resolved_on = resolved_on or date.today()
    if promise is None:
        status = PromiseStatus.NONE
    elif not paid:
        status = PromiseStatus.BROKEN
    elif promise.amount and amount_paid and amount_paid < promise.amount * 0.95:
        status = PromiseStatus.PARTIAL
    else:
        status = PromiseStatus.KEPT
    return Outcome(
        borrower_id=promise.borrower_id if promise else "unknown",
        promise_status=status,
        recovered=amount_paid,
        resolved_on=resolved_on,
    )


def _paid_next_month(loan_id: str, panel: pl.DataFrame) -> tuple[bool, float]:
    """Did this loan's delinquency improve after its last observed month?
    Improvement (or return to current) is the payment proxy on this data."""
    rows = panel.filter(pl.col("loan_id") == loan_id).sort("period_date")
    if rows.height < 2:
        return False, 0.0
    last_two = rows.tail(2)
    d_prev, d_last = last_two["delinq"].to_list()
    upb_prev, upb_last = last_two["upb"].to_list()
    improved = (d_last is not None and d_prev is not None and d_last < d_prev)
    paid_amt = max(0.0, (upb_prev or 0) - (upb_last or 0))
    return improved, paid_amt


def resolve_conversation(conv: dict, promise: Promise | None,
                         panel: pl.DataFrame) -> Outcome:
    """Resolve a generated conversation's promise against its seed loan's real
    subsequent panel behaviour."""
    paid, amt = _paid_next_month(conv["borrower_id"], panel)
    return resolve(promise, paid, amt)


def verify(conversations: list[dict], promises: list[Promise | None]) -> list[str]:
    """Phase 6 gate: every promise resolves, no silent drops."""
    problems = []
    panel = pl.read_parquet(PANEL_PATH)
    outcomes = []
    for conv, pr in zip(conversations, promises):
        outcomes.append(resolve_conversation(conv, pr, panel))
    if len(outcomes) != len(conversations):
        problems.append(f"resolved {len(outcomes)} of {len(conversations)} — silent drop")
    if any(o.promise_status not in set(PromiseStatus) for o in outcomes):
        problems.append("an outcome has an invalid status")
    return problems, outcomes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--n", type=int, default=12)
    args = ap.parse_args()
    if args.verify:
        from .coach.extract import extract_promise
        from .generate import generate_batch
        convs = generate_batch(args.n)
        promises = [extract_promise(c["transcript"], c["borrower_id"]) for c in convs]
        problems, outcomes = verify(convs, promises)
        from collections import Counter
        dist = Counter(o.promise_status.value for o in outcomes)
        print(f"  conversations: {len(convs)}  promises: {sum(p is not None for p in promises)}")
        print(f"  outcome dist: {dict(dist)}")
        if problems:
            for p in problems:
                print(f"  FAIL {p}")
            return 1
        print("outcomes verify OK: every promise resolved, no silent drops")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
