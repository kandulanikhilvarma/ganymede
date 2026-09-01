"""Generation and extraction with a fake engine — offline, no API cost.
The live PTP-vs-gold check lives behind GANYMEDE_LIVE_LLM in test_ptp_live."""

import os
from datetime import date

import pytest

from ganymede.coach.extract import extract_promise
from ganymede.generate import generate_conversation
from ganymede.llm import LLMEngine, Role
from ganymede.schema import Capacity, Willingness


class FakeEngine(LLMEngine):
    def __init__(self, reply):
        self._reply = reply

    def complete(self, role, prompt, *, system=None, temperature=0.0, max_tokens=1024):
        return self._reply


def test_generation_flags_synthetic():
    eng = FakeEngine("AGENT: Hello.\nBORROWER: Hi.")
    conv = generate_conversation("L1", 2, 150000.0,
                                 (Capacity.CANNOT_PAY, Willingness.WILL_PAY), engine=eng)
    assert conv["is_synthetic"] is True  # I1
    assert "AGENT:" in conv["transcript"]


def test_extract_parses_specific_promise():
    eng = FakeEngine('{"has_promise": true, "amount": 150, "due": "2026-09-05", '
                     '"method": "bank_transfer", "confidence": 0.9}')
    p = extract_promise("...", "L1", ref=date(2026, 9, 2), engine=eng)
    assert p.amount == 150 and p.method == "bank_transfer"
    assert p.is_specific


def test_extract_vague_promise_has_null_fields():
    eng = FakeEngine('{"has_promise": true, "amount": null, "due": null, '
                     '"method": null, "confidence": 0.4}')
    p = extract_promise("...", "L1", engine=eng)
    assert p is not None and not p.is_specific


def test_extract_no_promise_returns_none():
    eng = FakeEngine('{"has_promise": false, "amount": null, "due": null, '
                     '"method": null, "confidence": 0.9}')
    assert extract_promise("...", "L1", engine=eng) is None


def test_extract_handles_fenced_json():
    eng = FakeEngine('```json\n{"has_promise": true, "amount": 50, "due": null, '
                     '"method": "card", "confidence": 0.7}\n```')
    p = extract_promise("...", "L1", engine=eng)
    assert p.amount == 50 and p.method == "card"
