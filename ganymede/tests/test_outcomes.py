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
