"""Allocator objective logic — unit-tested on constructed accounts, no full sim."""

import polars as pl

from ganymede.allocator import _best_action, allocate, modelled_uplift


def test_uplift_peaks_in_the_middle():
    # The persuadable-middle shape: near-zero at the ends, max around 0.5.
    import numpy as np
    lo = modelled_uplift(np.array([0.02]), 1.0)[0]
    mid = modelled_uplift(np.array([0.5]), 1.0)[0]
    hi = modelled_uplift(np.array([0.98]), 1.0)[0]
    assert mid > lo and mid > hi
    assert lo < 0.02 and hi < 0.02  # ends gain almost nothing


def test_high_exposure_middle_account_gets_contacted():
    action, value, minutes = _best_action(p_selfcure=0.5, exposure=200_000, lam=1.0)
    assert action != "do_not_contact"
    assert value > 0


def test_selfcurer_is_worth_less_than_persuadable():
    # Monotone in the right direction: a near-certain self-curer is worth less to
    # contact than a persuadable-middle account at the same exposure. (At large
    # exposure even a small uplift clears a cheap contact's cost, which is correct
    # mortgage economics — so this is a relative test, not "never contact".)
    _, v_middle, _ = _best_action(p_selfcure=0.5, exposure=200_000, lam=1.0)
    _, v_curer, _ = _best_action(p_selfcure=0.97, exposure=200_000, lam=1.0)
    assert v_middle > v_curer


def test_tiny_exposure_not_worth_contacting():
    # exposure 5: peak uplift 0.25 x 5 = 1.25 < cheapest action cost (3 min).
    action, value, minutes = _best_action(p_selfcure=0.5, exposure=5, lam=1.0)
    assert action == "do_not_contact"


def test_allocate_respects_capacity():
    accounts = pl.DataFrame({
        "idx": list(range(10)),
        "loan_id": [f"L{i}" for i in range(10)],
        "exposure": [200_000.0] * 10,
        "p_worsen": [0.5] * 10,
        "p_selfcure": [0.5] * 10,
    })
    # capacity for ~2 plan_offers (12 min each)
    out = allocate(accounts, capacity_minutes=24)
    contacted = out.filter(pl.col("action") != "do_not_contact")
    assert contacted["minutes"].sum() <= 24


def _accounts():
    # Risk-ranking's favourite (high p_worsen, tiny exposure) against a large,
    # persuadable account it ranks last. The allocator should take the large one.
    return pl.DataFrame({
        "idx": [0, 1, 2, 3, 4],
        "loan_id": ["tiny-risky", "big-middle", "mid-a", "mid-b", "curer"],
        "exposure": [1_000.0, 900_000.0, 50_000.0, 40_000.0, 800_000.0],
        "p_worsen": [0.95, 0.20, 0.60, 0.55, 0.05],
        "p_selfcure": [0.30, 0.50, 0.50, 0.45, 0.99],
    }, schema_overrides={"idx": pl.UInt32})


def test_risk_ranking_works_down_by_probability_within_capacity():
    from ganymede.allocator import ACTION_MINUTES, _risk_ranking
    cap = ACTION_MINUTES["plan_offer"] * 2
    r = _risk_ranking(_accounts(), cap)
    called = r.filter(pl.col("action") != "do_not_contact")["loan_id"].to_list()
    assert called == ["tiny-risky", "mid-a"]


def test_compare_allocator_beats_risk_ranking_at_scarce_capacity():
    from ganymede.allocator import compare
    # 0.6 -> 36 minutes: room for big-middle's restructure (25). Below 25 the
    # greedy fill drops an account whose best action does not fit rather than
    # falling back to a cheaper one (C-11, parked as a modelling decision).
    r = compare(_accounts(), capacity_frac=0.6)
    assert r["allocator_value"] > r["risk_ranking_value"]
    assert r["lift_pct"] > 0
    assert r["allocator_contacts"] <= r["risk_contacts"] + 1


def test_compare_lift_is_null_not_infinity_when_baseline_recovers_nothing():
    import json

    from ganymede.allocator import compare
    zero = _accounts().with_columns(pl.lit(1.0).alias("exposure"))
    r = compare(zero, capacity_frac=0.4)
    json.dumps(r, allow_nan=False)      # Infinity would raise here
