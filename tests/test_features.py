"""Label and window checks on a two-loan panel. The windows must stop at the loan
boundary: one loan's future is never another loan's label."""

from datetime import date

import polars as pl

from ganymede.features import FORWARD, TRAIL, build_features, time_split


def _panel():
    # Loan a is current throughout. Loan b sits at 5 then climbs, so any window
    # that crosses from a into b shows up as a jump a never made.
    rows = []
    for loan, ds in (("a", [0] * 6), ("b", [5, 6, 7, 8, 9, 10])):
        for m, d in enumerate(ds):
            rows.append({
                "loan_id": loan, "period_date": date(2025, m + 1, 1),
                "delinq": d, "upb": 1000.0 - 10 * m,
            })
    return pl.DataFrame(rows)


def test_forward_labels_stay_inside_the_loan():
    f = build_features(_panel())
    a = f.filter(pl.col("loan_id") == "a")
    assert a["d_fwd_max"].max() == 0
    assert a["y_worsen"].sum() == 0


def test_rows_without_a_full_forward_window_are_dropped():
    f = build_features(_panel())
    for loan in ("a", "b"):
        assert f.filter(pl.col("loan_id") == loan).height == 6 - FORWARD


def test_trailing_features_stay_inside_the_loan():
    f = build_features(_panel()).filter(pl.col("loan_id") == "b").sort("period_date")
    # b's first rows have no trailing history; they must not borrow a's.
    assert f["delinq_trend_3m"][:TRAIL].is_null().all()
    assert f["delinq_max_3m"][0] == 5


def test_time_split_is_disjoint():
    f = build_features(_panel())
    tr, te = time_split(f, cutoff="2025-02-01")
    assert tr.height + te.height == f.height
    assert tr["period_date"].max() < te["period_date"].min()
