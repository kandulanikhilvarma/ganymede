"""Live judge-vs-gold reliability (Krippendorff alpha). Opt-in, costs API calls.
Run with GANYMEDE_LIVE_LLM=1."""

import os

import pytest


@pytest.mark.skipif(
    os.environ.get("GANYMEDE_LIVE_LLM") != "1",
    reason="set GANYMEDE_LIVE_LLM=1 to run the live judge evaluation",
)
def test_judge_agrees_and_stays_under_ceiling():
    from ganymede.evals.judge import evaluate
    r = evaluate()
    assert r["judge_vs_human_agreement"] >= 0.60
    assert r["ceiling_ok"], "judge exceeds its reliability ceiling (fitting noise)"
