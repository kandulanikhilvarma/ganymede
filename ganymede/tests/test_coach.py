"""Phase 7 gate. Hints validate, tier-1 renders in budget, rate capped, LLM
overruns demote. Offline via a fake engine; no API cost."""

import time
from datetime import date

from ganymede.coach.boundary import deliver, is_hint_eligible
from ganymede.coach.checklist import checklist_hint
from ganymede.coach.compose import CoachContext, coach_turn
from ganymede.config import MAX_HINTS_PER_CONVERSATION, require_latency_budget
from ganymede.llm import LLMEngine
from ganymede.schema import BorrowerState, Capacity, Hint, Promise, Willingness


class FakeEngine(LLMEngine):
    def __init__(self, reply="Offer to set the payment up right now on the call.", delay=0.0):
        self._reply, self._delay = reply, delay

    def complete(self, role, prompt, *, system=None, temperature=0.0, max_tokens=1024):
        if self._delay:
            time.sleep(self._delay)
        return self._reply


def _certain(cap, wil):
    return BorrowerState(capacity=cap, willingness=wil, confidence=0.8)


def test_vague_promise_fires_promise_quality_hint():
    p = Promise(borrower_id="b", extractor_confidence=0.6)  # all fields null -> vague
    h = checklist_hint("AGENT: hi. BORROWER: yes, speaking. I'll try next week.", p)
    assert h is not None and h.is_deterministic
    assert "amount" in h.text and "date" in h.text


def test_identity_hint_before_anything():
    h = checklist_hint("AGENT: is that the account holder?", None)
    assert h is not None and "account holder" in h.text


def test_uncertain_state_gets_diagnostic_not_strategy():
    ctx = CoachContext(
        state=BorrowerState(capacity=Capacity.UNKNOWN, willingness=Willingness.UNKNOWN, confidence=0.1),
        transcript_so_far="BORROWER: yes, speaking.", at_pause=True,
    )
    h = coach_turn(ctx, engine=FakeEngine())
    assert h is not None and h.is_deterministic
    assert "ask" in h.text.lower()


def test_strategy_hint_carries_support_count():
    ctx = CoachContext(
        state=_certain(Capacity.CAN_PAY, Willingness.WILL_PAY),
        transcript_so_far="BORROWER: yes, speaking. I just forgot about it.",
        at_pause=True,
    )
    h = coach_turn(ctx, engine=FakeEngine())
    assert h is not None and not h.is_deterministic
    assert h.support_count is not None  # I5
    assert "seeded" in h.text  # provisional strategies are visibly thin


def test_rate_ceiling_blocks_beyond_max():
    ctx = CoachContext(
        state=_certain(Capacity.CAN_PAY, Willingness.WILL_PAY),
        transcript_so_far="BORROWER: yes, speaking.", at_pause=True,
        hints_shown=MAX_HINTS_PER_CONVERSATION,
    )
    assert coach_turn(ctx, engine=FakeEngine()) is None


def test_no_hint_off_pause_for_strategy():
    ctx = CoachContext(
        state=_certain(Capacity.CAN_PAY, Willingness.WILL_PAY),
        transcript_so_far="BORROWER: yes, speaking.", at_pause=False,
    )
    # off-pause: no tier-2 strategy (tier-1 already satisfied: identity present)
    assert coach_turn(ctx, engine=FakeEngine()) is None


def test_deterministic_hint_delivers_live():
    hint = Hint(text="Confirm identity.", is_deterministic=True)
    out, mode = deliver(lambda: hint)
    assert mode == "live"


def test_slow_llm_hint_demotes_to_next_turn():
    budget_s = require_latency_budget() / 1000
    slow = Hint(text="strategy", is_deterministic=False, support_count=0)
    out, mode = deliver(lambda: (time.sleep(budget_s + 0.05), slow)[1])
    assert mode == "next_turn"


def test_boundary_eligibility():
    assert is_hint_eligible(300)
    assert not is_hint_eligible(100)
