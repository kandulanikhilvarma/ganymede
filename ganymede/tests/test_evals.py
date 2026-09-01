"""Eval-layer logic — offline. Live judge check is in test_judge_live."""

import numpy as np

from ganymede.evals.metrics import assemble, hint_usefulness, lift_on_set
from ganymede.monitors.drift import check_drift, check_rate_drift, psi


def test_i1_guard_refuses_lift_on_synthetic():
    r = lift_on_set([0.1, 0.2, 0.3], [False, False, True])
    assert r["lift"] is None
    assert "I1" in r["refused"]


def test_lift_computes_on_all_real():
    r = lift_on_set([0.1, 0.2, 0.3], [False, False, False])
    assert r["lift"] is not None and r["refused"] is None


def test_hint_usefulness_gate():
    good = hint_usefulness({"judge_vs_human_agreement": 0.9})
    bad = hint_usefulness({"judge_vs_human_agreement": 0.4})
    assert good["passes"] and not bad["passes"]


def test_psi_zero_on_identical():
    x = np.random.default_rng(0).normal(size=5000)
    assert psi(x, x) < 0.01


def test_psi_flags_shift():
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1, 5000)
    cur = rng.normal(2, 1, 5000)  # shifted mean
    assert psi(ref, cur) > 0.25


def test_rate_drift_catches_selfcure_shift():
    ref = np.array([1, 0, 1, 0, 1, 0])          # rate 0.5
    cur = np.array([1, 1, 1, 1, 1, 0])          # rate 0.83
    r = check_rate_drift(ref, cur, "selfcure")
    assert r["alert"]  # delta 0.33 >> 0.10


def test_assemble_marks_pilot_metrics_pending():
    judge = {"judge_vs_human_agreement": 0.9, "mixed_pool_alpha": 0.85, "within_judge_alpha": 0.9}
    table = assemble(judge, [])
    assert table["recovery_per_agent_hour"]["value"] is None
    assert "pilot" in table["ptp_kept_lift"]["status"]
