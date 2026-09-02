"""Live PTP-extractor-vs-gold check (I6). Opt-in: costs API calls.
Run with GANYMEDE_LIVE_LLM=1. This is the reproducible Phase 6 accuracy gate."""

import os

import pytest


@pytest.mark.skipif(
    os.environ.get("GANYMEDE_LIVE_LLM") != "1",
    reason="set GANYMEDE_LIVE_LLM=1 to run the live PTP gold evaluation",
)
def test_ptp_extractor_clears_bar():
    from ganymede.coach.ptp_eval import evaluate
    r = evaluate()
    assert r["passes"], f"PTP field accuracy {r['field_accuracy']} below bar {r['bar']}"
