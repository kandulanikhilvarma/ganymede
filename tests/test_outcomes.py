"""Outcome resolver logic — pure, offline."""

from datetime import date

from ganymede.outcomes import resolve
from ganymede.schema import Promise, PromiseStatus


def _promise(amount=150.0):
    return Promise(borrower_id="b", amount=amount, due=date(2026, 9, 5),
                   method="bank_transfer", extractor_confidence=0.9)


def test_no_promise_resolves_to_none():
    assert resolve(None, paid=False).promise_status is PromiseStatus.NONE


def test_promise_paid_is_kept():
    o = resolve(_promise(), paid=True, amount_paid=150.0)
    assert o.promise_status is PromiseStatus.KEPT


def test_promise_unpaid_is_broken():
    o = resolve(_promise(), paid=False)
    assert o.promise_status is PromiseStatus.BROKEN


def test_underpayment_is_partial():
    o = resolve(_promise(200.0), paid=True, amount_paid=80.0)
    assert o.promise_status is PromiseStatus.PARTIAL


def test_every_status_is_valid():
    for paid, amt, pr in [(False, 0, None), (True, 150, _promise()),
                          (False, 0, _promise()), (True, 10, _promise(200))]:
        o = resolve(pr, paid=paid, amount_paid=amt)
        assert o.promise_status in set(PromiseStatus)


def _loan(delinq):
    import polars as pl
    from datetime import date
    return pl.DataFrame({
        "loan_id": ["L"] * len(delinq),
        "period_date": [date(2025, m + 1, 1) for m in range(len(delinq))],
        "delinq": delinq,
        "upb": [1000.0 - 50 * m for m in range(len(delinq))],
    })


def test_outcome_reads_the_month_after_the_call_not_the_last_month():
    from datetime import date

    from ganymede.outcomes import _paid_next_month
    # Cures right after a March call (2 -> 0), then worsens at the end of history.
    panel = _loan([1, 2, 2, 0, 1, 3])
    assert _paid_next_month("L", panel, date(2025, 3, 1))[0] is True
    assert _paid_next_month("L", panel)[0] is False          # last two rows: 1 -> 3


def test_generated_conversation_carries_its_seed_month():
    from datetime import date

    from ganymede.generate import generate_conversation
    from ganymede.llm import LLMEngine
    from ganymede.schema import Capacity, Willingness

    class Echo(LLMEngine):
        def complete(self, role, prompt, **kw):
            return "AGENT: hi"

    conv = generate_conversation("L", 2, 1000.0, (Capacity.CAN_PAY, Willingness.WILL_PAY),
                                 engine=Echo(), period_date=date(2025, 3, 1))
    assert conv["period_date"] == date(2025, 3, 1)
