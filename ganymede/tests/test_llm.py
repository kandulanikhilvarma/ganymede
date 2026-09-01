"""LLM engine wiring. The live call is opt-in (costs money / needs network):
run with GANYMEDE_LIVE_LLM=1 to hit OpenRouter for real."""

import os

import pytest

from ganymede.llm import OPENROUTER_MODELS, Role, get_engine


def test_every_role_has_a_model():
    for role in Role:
        assert role in OPENROUTER_MODELS
        assert OPENROUTER_MODELS[role]


def test_extract_and_judge_use_different_tiers():
    # The whole point of the routing table: cheap for volume, strong for the
    # ceiling. If these ever collapse to one model, the cost design is gone.
    assert OPENROUTER_MODELS[Role.EXTRACT] != OPENROUTER_MODELS[Role.JUDGE]


@pytest.mark.skipif(
    os.environ.get("GANYMEDE_LIVE_LLM") != "1",
    reason="set GANYMEDE_LIVE_LLM=1 to run the live OpenRouter call",
)
def test_live_roundtrip():
    engine = get_engine()
    out = engine.complete(Role.EXTRACT, "reply with exactly: OK", max_tokens=5)
    assert "OK" in out
