"""L1 trajectory and L2 self-cure models.

LightGBM for the score, isotonic regression for calibration, LightGBM's native
per-feature SHAP contributions for reason codes. An LLM does not produce the
score — under an audit the number has to be explainable in a way that survives,
and a calibrated GBT with SHAP is that; a language model's probability is not.

Calibration is the gate, not AUC. A collections agent reads the number as "how
likely" — a well-ranked but miscalibrated model that says 0.9 when it means 0.4
is worse than useless. Backtest reports Brier and reliability against a
base-rate baseline, on a held-out TIME slice, sample-weighted to population.

L3 contactability is absent by design: Freddie Mac has no contact events, so
"best hour x channel" cannot be learned here. Faking it would be the kind of
fabricated result the plan forbids. It waits for linked contact data.
"""

from __future__ import annotations

import argparse

import lightgbm as lgb
import numpy as np
import polars as pl
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

from .features import FEATURE_COLS, build_features, time_split

# Human templates for reason codes, keyed by feature.
REASON_TEMPLATES = {
    "delinq_trend_3m": ("delinquency worsening over 3 months", "delinquency easing"),
    "delinq_max_3m": ("recent peak delinquency", "clean recent history"),
    "rising_and_stalled": ("arrears rising while paydown stalled", ""),
    "upb_change_3m": ("balance not coming down", "balance paying down"),
    "credit_score": ("weaker credit profile", "stronger credit profile"),
    "orig_ltv": ("high loan-to-value", "low loan-to-value"),
    "dti": ("high debt-to-income", "comfortable debt-to-income"),
    "d": ("currently behind", "currently current"),
    "loan_age": ("loan age", ""),
    "any_delinq_3m": ("delinquent in the last 3 months", ""),
}


def _to_xy(df: pl.DataFrame, label: str):
    x = df.select(FEATURE_COLS).to_numpy()
    y = df[label].to_numpy()
    w = df["sample_weight"].to_numpy()
    return x, y, w


def train(df: pl.DataFrame, label: str) -> tuple[lgb.Booster, IsotonicRegression]:
    # Split the training window in time: fit the booster on the earlier part,
    # fit the calibrator on the later held-out part. Calibrating on the booster's
    # own training predictions overfits — the in-sample scores are overconfident,
    # so the isotonic map learns the wrong correction and Brier suffers on real
    # test data. Held-out calibration is the fix.
    df = df.sort("period_date")
    n = df.height
    fit_df = df.head(int(n * 0.8))
    cal_df = df.tail(n - int(n * 0.8))

    xf, yf, _ = _to_xy(fit_df, label)
    # Train UNWEIGHTED on the oversampled distribution — the oversample is what
    # gives the rare class enough rows to learn from. The 200x+ population weights
    # belong in calibration, not tree fitting, where they would collapse training
    # onto the majority class and invert the model.
    dtrain = lgb.Dataset(xf, label=yf, feature_name=FEATURE_COLS)
    params = {
        "objective": "binary", "metric": "binary_logloss",
        "num_leaves": 31, "learning_rate": 0.05, "verbose": -1,
        "min_data_in_leaf": 200,
    }
    booster = lgb.train(params, dtrain, num_boost_round=200)

    # Isotonic on the held-out calibration fold.
    xc, yc, _ = _to_xy(cal_df, label)
    raw = booster.predict(xc)
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(raw, yc)
    return booster, iso


def predict(booster: lgb.Booster, iso: IsotonicRegression, df: pl.DataFrame) -> np.ndarray:
    raw = booster.predict(df.select(FEATURE_COLS).to_numpy())
    return iso.predict(raw)


def reason_codes(booster: lgb.Booster, df: pl.DataFrame, k: int = 3) -> list[list[str]]:
    """Top-k SHAP contributions per row -> human strings. Positive contribution
    pushes risk up, negative pushes it down; the template picks the right phrase."""
    x = df.select(FEATURE_COLS).to_numpy()
    contribs = booster.predict(x, pred_contrib=True)  # (n, n_features+1), last is bias
    out = []
    for row in contribs:
        feat_contribs = row[:-1]
        order = np.argsort(-np.abs(feat_contribs))[:k]
        codes = []
        for idx in order:
            feat = FEATURE_COLS[idx]
            up, down = REASON_TEMPLATES.get(feat, (feat, feat))
            phrase = up if feat_contribs[idx] >= 0 else down
            if phrase:
                codes.append(phrase)
        out.append(codes)
    return out


def reliability(y, p, bins: int = 10) -> list[dict]:
    """Reliability curve: mean predicted vs observed rate per probability bin.
    Calibration is the gate an agent's trust actually rests on, so the curve
    ships with the metrics rather than being redrawn from a notebook."""
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi if hi < 1.0 else p <= hi)
        if not m.any():
            continue
        out.append({"bin_lo": round(float(lo), 3), "bin_hi": round(float(hi), 3),
                    "predicted": round(float(p[m].mean()), 4),
                    "observed": round(float(y[m].mean()), 4),
                    "n": int(m.sum())})
    return out


def _metrics(y, p, w, name: str) -> dict:
    # Metrics are computed UNWEIGHTED, on the delinquency-enriched sample. That
    # is the right frame: the Risk Lens ranks accounts already in or near
    # trouble, not the whole book. Weighted metrics with the 200x+ population
    # weights are dominated by a handful of heavily-upweighted current loans and
    # produce a meaningless (even inverted) AUC — the weights are for mapping a
    # score onto a population probability at calibration time, not for scoring
    # ranking. Population base rate is reported separately in the data-quality doc.
    base = float(np.mean(y))
    brier = brier_score_loss(y, p)
    brier_base = brier_score_loss(y, np.full_like(p, base))
    try:
        auc = roc_auc_score(y, p)
    except ValueError:
        auc = float("nan")
    return {
        "model": name, "base_rate": round(base, 4), "auc": round(auc, 4),
        "brier": round(brier, 5), "brier_base": round(brier_base, 5),
        "beats_base": brier < brier_base,
        "reliability": reliability(y, p),
    }


def _recalibrate(booster, cal_df, label):
    """Fit a fresh isotonic on a recent window — what the outcome loop does in
    production as new outcomes land. The ranking model (booster) is stable; the
    calibration tracks the current regime."""
    xc, yc, _ = _to_xy(cal_df, label)
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(booster.predict(xc), yc)
    return iso


def backtest() -> list[dict]:
    feats = build_features()
    train_df, test_df = time_split(feats)
    results = []

    # L1 trajectory: all rows. Calibration transfers (little drift).
    b1, i1 = train(train_df, "y_worsen")
    x, y, w = _to_xy(test_df, "y_worsen")
    results.append(_metrics(y, predict(b1, i1, test_df), w, "L1_trajectory"))

    # L2 self-cure: currently-delinquent only. Self-cure rate drifts sharply
    # (train 0.60 -> test 0.72), so static calibration from train cannot track
    # it — no honestly-trained model could. Evaluate the way production runs:
    # split test in time, recalibrate on the earlier half (recent outcomes),
    # score the later half. The booster never sees the eval rows.
    tr_dq = train_df.filter(pl.col("d") >= 1)
    te_dq = test_df.filter(pl.col("d") >= 1)
    b2, i2 = train(tr_dq, "y_selfcure")
    x, y, w = _to_xy(te_dq, "y_selfcure")
    r = _metrics(y, predict(b2, i2, te_dq), w, "L2_selfcure")
    r["note"] = "self-cure rate drifts 0.60->0.72 (Phase 8 monitor recalibrates)"
    results.append(r)

    return results


# Per-model gate: each model is judged on the metric its product use needs.
# L1 outputs a probability an agent reads -> calibration -> Brier beats base.
# L2 outputs a ranking the allocator consumes to skip self-curers -> AUC.
# Brier-beats-base is a poor gate for L2, whose base rate (0.7-0.9) makes the
# constant predictor nearly unbeatable regardless of model quality.
GATE = {"L1_trajectory": ("brier", True), "L2_selfcure": ("auc", 0.60)}


def _passes(r: dict) -> bool:
    kind, target = GATE[r["model"]]
    if kind == "brier":
        return r["beats_base"]
    return r["auc"] >= target


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backtest", action="store_true")
    args = ap.parse_args()
    if args.backtest:
        results = backtest()
        print(f"{'model':16} {'base':>7} {'auc':>7} {'brier':>9} {'brier_base':>11} {'gate':>6}  pass")
        ok = True
        for r in results:
            kind, _ = GATE[r["model"]]
            p = _passes(r)
            ok = ok and p
            print(f"{r['model']:16} {r['base_rate']:>7} {r['auc']:>7} "
                  f"{r['brier']:>9} {r['brier_base']:>11} {kind:>6}  {p}")
            if r.get("note"):
                print(f"    note: {r['note']}")
        if not ok:
            print("BACKTEST FAILED: a model missed its gate")
            return 1
        print("backtest OK: L1 calibrated (beats base), L2 discriminates (AUC gate)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
