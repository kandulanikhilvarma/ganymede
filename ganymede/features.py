"""Trajectory features from the monthly panel.

One feature row per (loan, observation-month). Features look back over a trailing
window; labels look forward. The forward window is why the last months of each
loan are dropped — no future to label against.

The cross-signal combination the research names — delinquency rising WHILE
paydown stalls — is built explicitly rather than left for the model to find,
because it is the single most reliable early-default pattern and a tree may need
many splits to reconstruct an interaction we can hand it in one column.

I13: every feature here reads the Freddie panel, which is tagged
has_calendar_dates=True. A timing feature on a source tagged False must raise;
that guard lives where such a feature would be written, not here.
"""

from __future__ import annotations

import polars as pl

from .panel import PANEL_PATH

TRAIL = 3   # trailing window, months
FORWARD = 3  # forward horizon for labels, months


def build_features(panel: pl.DataFrame | None = None) -> pl.DataFrame:
    p = panel if panel is not None else pl.read_parquet(PANEL_PATH)
    p = p.sort(["loan_id", "period_date"])

    # Fill missing delinq (XX/too-new) with 0 for trajectory math; keep a flag.
    p = p.with_columns([
        pl.col("delinq").fill_null(0).alias("d"),
        pl.col("delinq").is_null().cast(pl.Int8).alias("delinq_unknown"),
    ])

    # The window goes last. `.over()` first and `.shift()` after runs the shift
    # across the whole sorted frame, so one loan's last rows read the next loan's
    # first months as their future.
    d, upb = pl.col("d"), pl.col("upb")

    def per_loan(e: pl.Expr) -> pl.Expr:
        return e.over("loan_id")

    fwd = [per_loan(d.shift(-i)) for i in range(1, FORWARD + 1)]

    feats = p.with_columns([
        # trailing trajectory
        (d - per_loan(d.shift(TRAIL))).alias("delinq_trend_3m"),
        per_loan(d.rolling_max(window_size=TRAIL, min_samples=1)).alias("delinq_max_3m"),
        (per_loan(d.rolling_sum(window_size=TRAIL, min_samples=1)) > 0)
        .cast(pl.Int8).alias("any_delinq_3m"),
        # paydown velocity: negative UPB change is healthy; ~0 while owing is stress
        (upb - per_loan(upb.shift(TRAIL))).alias("upb_change_3m"),
        # forward labels
        fwd[0].alias("d_next1"),
        pl.max_horizontal(fwd).alias("d_fwd_max"),
        pl.min_horizontal(fwd).alias("d_fwd_min"),
        fwd[-1].is_not_null().alias("_full_fwd"),
    ])

    # cross-signal: delinquency rising AND paydown stalled in the same window
    feats = feats.with_columns([
        ((pl.col("delinq_trend_3m") > 0) & (pl.col("upb_change_3m") >= 0))
        .cast(pl.Int8).alias("rising_and_stalled"),
        # L1 label: worsens over the forward window
        (pl.col("d_fwd_max") > pl.col("d")).cast(pl.Int8).alias("y_worsen"),
        # L2 label (self-cure): among currently delinquent, returns to current
        (pl.col("d_fwd_min") == 0).cast(pl.Int8).alias("y_selfcure"),
    ])

    # drop rows without a full forward window (label undefined). max_horizontal
    # skips nulls, so d_fwd_max alone would keep rows with one or two months left.
    return feats.filter(pl.col("_full_fwd")).drop("_full_fwd")


FEATURE_COLS = [
    "d", "delinq_trend_3m", "delinq_max_3m", "any_delinq_3m", "upb_change_3m",
    "rising_and_stalled", "delinq_unknown", "loan_age", "credit_score",
    "orig_ltv", "dti", "cltv", "orig_upb",
]


def time_split(feats: pl.DataFrame, cutoff: str = "2025-07-01"):
    """Train on months before cutoff, test after. Never a random split —
    a random split leaks the future into the past on a panel."""
    cut = pl.lit(cutoff).str.strptime(pl.Date, "%Y-%m-%d")
    train = feats.filter(pl.col("period_date") < cut)
    test = feats.filter(pl.col("period_date") >= cut)
    return train, test
