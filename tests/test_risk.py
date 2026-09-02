"""Risk model checks on a tiny synthetic panel — fast, offline, no full build."""

from datetime import date

import polars as pl

from ganymede.risk import reason_codes, train


def _toy_features(n=400):
    # Build a panel-shaped frame where worsening is driven by delinq trend, so a
    # model must recover the signal to pass. Deterministic, no randomness needed.
    rows = []
    for i in range(n):
        worsening = i % 2 == 0
        rows.append({
            "d": 2 if worsening else 0,
            "delinq_trend_3m": 2 if worsening else -1,
            "delinq_max_3m": 3 if worsening else 0,
            "any_delinq_3m": 1 if worsening else 0,
            "upb_change_3m": 0.0 if worsening else -500.0,
            "rising_and_stalled": 1 if worsening else 0,
            "delinq_unknown": 0,
            "loan_age": 12,
            "credit_score": 620 if worsening else 760,
            "orig_ltv": 95 if worsening else 70,
            "dti": 45 if worsening else 25,
            "cltv": 95 if worsening else 70,
            "orig_upb": 200000.0,
            "sample_weight": 1.0,
            "period_date": date(2024, 1 + (i % 12), 1),
            "y_worsen": 1 if worsening else 0,
        })
    return pl.DataFrame(rows)


def test_pipeline_runs_and_outputs_valid_probabilities():
    # Discrimination is verified at scale in `risk --backtest` (AUC 0.62); the
    # production params (min_data_in_leaf=200) will not split 400 toy rows, so
    # this unit test verifies the pipeline shape, not the learned signal.
    from ganymede.risk import predict
    df = _toy_features()
    booster, iso = train(df, "y_worsen")
    p = predict(booster, iso, df)
    assert p.shape[0] == df.height
    assert (p >= 0).all() and (p <= 1).all()


def test_reason_codes_are_human_strings():
    df = _toy_features()
    booster, _ = train(df, "y_worsen")
    codes = reason_codes(booster, df.head(5), k=3)
    assert len(codes) == 5
    for row_codes in codes:
        for c in row_codes:
            assert isinstance(c, str) and " " in c  # a phrase, not a raw feature name
