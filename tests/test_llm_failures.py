"""What the LLM-backed paths do when the model replies badly. Offline: a fake
engine plays the model. A bad reply must be counted, never read as a label."""

from datetime import date

import pytest

from ganymede.coach import ptp_eval
from ganymede.coach.extract import ExtractionError, extract_promise
from ganymede.evals import judge
from ganymede.llm import LLMEngine


class FakeEngine(LLMEngine):
    def __init__(self, *replies):
        self._replies = list(replies)
        self._i = 0

    def complete(self, role, prompt, *, system=None, temperature=0.0, max_tokens=1024):
        reply = self._replies[self._i % len(self._replies)]
        self._i += 1
        return reply


@pytest.mark.parametrize("reply", [
    "",
    "Sorry, I can't help with that.",
    '{"has_promise": true, "amount": 150',            # truncated
    '{"has_promise": true, "amount": "EUR 150"}',      # not a number
])
def test_unreadable_extraction_raises_not_none(reply):
    # None means "no promise", which is a real label. A bad reply is not that.
    with pytest.raises(ExtractionError):
        extract_promise("...", "L1", ref=date(2026, 9, 2), engine=FakeEngine(reply))


def test_null_confidence_defaults():
    p = extract_promise("...", "L1", ref=date(2026, 9, 2), engine=FakeEngine(
        '{"has_promise": true, "amount": null, "due": null, "method": null, "confidence": null}'))
    assert p.extractor_confidence == 0.5


def test_ptp_eval_counts_parse_failures():
    r = ptp_eval.evaluate(engine=FakeEngine("not json"))
    assert r["parse_failures"] == r["n_cases"]
    assert r["field_accuracy"] == 0.0 and not r["passes"]


def test_judge_unparseable_reply_is_missing_not_zero():
    assert judge.judge_hint("ctx", "hint", FakeEngine("")) is None
    assert judge.judge_hint("ctx", "hint", FakeEngine("I think so")) is None
    assert judge.judge_hint("ctx", "hint", FakeEngine("1")) == 1
    assert judge.judge_hint("ctx", "hint", FakeEngine("0.")) == 0


def test_judge_uniform_ratings_do_not_crash():
    # krippendorff raises when every rating is identical; alpha is undefined there.
    r = judge.evaluate(engine=FakeEngine("1"), runs=2)
    assert r["unanswered"] == 0
    assert r["within_judge_alpha"] != r["within_judge_alpha"]   # NaN


def test_judge_counts_unanswered():
    r = judge.evaluate(engine=FakeEngine("1", ""), runs=2)
    assert r["unanswered"] > 0
