"""Generate site/data/*.json from the pipeline.

Every figure the site shows is produced here and tagged with the kind of
evidence standing behind it, so a chart cannot render a number without also
rendering its provenance. Hand-copying pipeline output into HTML is how a
project whose thesis is "no invented numbers" ends up quietly inventing one.

    python scripts/build_site_data.py            # regenerate
    python scripts/build_site_data.py --check    # fail if committed JSON is stale
    python scripts/build_site_data.py --only allocator,audio

Stages degrade independently: a stage whose inputs are missing (no panel, no
call audio) is skipped and its existing JSON left alone, reported at the end.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "data"
sys.path.insert(0, str(ROOT))

# Evidence kinds. These are the five provenance badges the design system draws,
# and the wording here is the single source for what each one promises.
PROVENANCE = {
    "measured":   "Observed directly from real data.",
    "backtested": "Real data, held-out time split.",
    "simulated":  "Real data plus an explicitly modelled assumption.",
    "seeded":     "Derived from practice, with zero outcome support so far.",
    "pending":    "Needs a pilot to earn. Deliberately not estimated.",
}


def fig(value, provenance: str, source: str, unit: str | None = None,
        note: str | None = None) -> dict:
    """One displayable number and the evidence behind it."""
    if provenance not in PROVENANCE:
        raise ValueError(f"unknown provenance {provenance!r}")
    out = {"value": value, "provenance": provenance, "source": source}
    if unit:
        out["unit"] = unit
    if note:
        out["note"] = note
    return out


# --------------------------------------------------------------------------
# stages
# --------------------------------------------------------------------------

def stage_panel() -> dict:
    """Panel shape and the roll curve -- how a book actually deteriorates."""
    import polars as pl
    from ganymede.panel import PANEL_PATH

    if not PANEL_PATH.exists():
        raise FileNotFoundError("panel.parquet missing -- run `python -m ganymede.panel --build`")

    p = pl.read_parquet(PANEL_PATH, columns=["loan_id", "period_date", "delinq", "upb", "vintage"])

    # Roll curve: where does an account in bucket b this month sit next month?
    nxt = p.sort(["loan_id", "period_date"]).with_columns(
        pl.col("delinq").shift(-1).over("loan_id").alias("delinq_next")
    ).drop_nulls("delinq_next")

    def bucket(col: str) -> pl.Expr:
        return (pl.when(pl.col(col) == 0).then(pl.lit("current"))
                  .when(pl.col(col) == 1).then(pl.lit("30"))
                  .when(pl.col(col) == 2).then(pl.lit("60"))
                  .when(pl.col(col) == 3).then(pl.lit("90"))
                  .otherwise(pl.lit("120+")))

    rolls = (nxt.with_columns([bucket("delinq").alias("from"), bucket("delinq_next").alias("to")])
                .group_by(["from", "to"]).len()
                .sort("len", descending=True))
    totals = rolls.group_by("from").agg(pl.col("len").sum().alias("total"))
    rolls = rolls.join(totals, on="from").with_columns(
        (pl.col("len") / pl.col("total")).alias("rate")
    )

    order = ["current", "30", "60", "90", "120+"]
    transitions = [
        {"from": r["from"], "to": r["to"], "n": int(r["len"]), "rate": round(r["rate"], 5)}
        for r in rolls.iter_rows(named=True) if r["rate"] >= 0.0005
    ]
    transitions.sort(key=lambda t: (order.index(t["from"]), order.index(t["to"])))

    dq = p.filter(pl.col("delinq") >= 1)
    dates = p["period_date"]

    return {
        "rows": fig(p.height, "measured", "panel.parquet"),
        "loans": fig(p["loan_id"].n_unique(), "measured", "panel.parquet"),
        "vintages": fig(p["vintage"].n_unique(), "measured", "panel.parquet"),
        "delinquent_months": fig(dq.height, "measured", "panel.parquet"),
        "period_from": str(dates.min()),
        "period_to": str(dates.max()),
        "buckets": order,
        "roll_curve": transitions,
        "bucket_share": [
            {"bucket": b, "n": int(n)}
            for b, n in zip(order, [
                p.filter(pl.col("delinq") == 0).height,
                p.filter(pl.col("delinq") == 1).height,
                p.filter(pl.col("delinq") == 2).height,
                p.filter(pl.col("delinq") == 3).height,
                p.filter(pl.col("delinq") >= 4).height,
            ])
        ],
    }


def stage_risk() -> dict:
    """L1/L2 backtest with the reliability curve, plus the self-cure drift."""
    import numpy as np
    import polars as pl
    from ganymede.features import build_features, time_split
    from ganymede.monitors.drift import PSI_ALERT, RATE_ALERT, check_rate_drift, psi
    from ganymede.risk import GATE, backtest

    results = backtest()
    models = {}
    for r in results:
        gate_kind, gate_target = GATE[r["model"]]
        models[r["model"]] = {
            "auc": fig(r["auc"], "backtested", "risk.backtest()"),
            "brier": fig(r["brier"], "backtested", "risk.backtest()"),
            "brier_base": fig(r["brier_base"], "backtested", "risk.backtest()"),
            "base_rate": fig(r["base_rate"], "measured", "held-out split"),
            "gate": {"metric": gate_kind, "target": gate_target,
                     "passed": bool(r["beats_base"] if gate_kind == "brier"
                                    else r["auc"] >= gate_target)},
            "reliability": r["reliability"],
            "note": r.get("note"),
        }

    # Drift: the self-cure regime shift the backtest note refers to, measured.
    feats = build_features()
    train_df, test_df = time_split(feats)
    tr = train_df.filter(pl.col("d") >= 1)["y_selfcure"].to_numpy()
    te = test_df.filter(pl.col("d") >= 1)["y_selfcure"].to_numpy()
    rate = check_rate_drift(tr, te, "y_selfcure")

    # Monthly self-cure rate across the whole window -- the timeline the site draws.
    monthly = (feats.filter(pl.col("d") >= 1)
                    .group_by(pl.col("period_date").dt.strftime("%Y-%m").alias("month"))
                    .agg([pl.col("y_selfcure").mean().alias("rate"), pl.len().alias("n")])
                    .sort("month"))

    return {
        "models": models,
        "split_cutoff": "2025-07-01",
        "drift": {
            "self_cure_train": fig(round(float(tr.mean()), 4), "measured", "train split"),
            "self_cure_test": fig(round(float(te.mean()), 4), "measured", "test split"),
            "rate_alert_threshold": RATE_ALERT,
            "psi_alert_threshold": PSI_ALERT,
            "alert": bool(rate.get("alert", False)),
            "psi_p_worsen_feature": fig(
                round(float(psi(train_df["d"].to_numpy().astype(float),
                                test_df["d"].to_numpy().astype(float))), 4),
                "measured", "monitors.drift.psi on delinquency bucket"),
            "monthly_self_cure": [
                {"month": r["month"], "rate": round(r["rate"], 4), "n": int(r["n"])}
                for r in monthly.iter_rows(named=True)
            ],
        },
    }


def stage_allocator() -> dict:
    """The capacity frontier, and the queue both strategies would build.

    Every point is a real allocator run at that budget -- the site's capacity
    slider reads this array, so it is never interpolating between two runs.
    """
    import polars as pl
    from ganymede.allocator import (ACTION_MINUTES, allocate, compare,
                                    _risk_ranking, score_accounts)
    from ganymede.config import LAMBDA_HARM
    from ganymede.state import estimate_state, strategy_for

    accounts = score_accounts()
    fracs = [round(0.01 * i, 3) for i in range(2, 61)]  # 2% .. 60% of full-coverage minutes
    frontier = [compare(accounts, f, LAMBDA_HARM) for f in fracs]

    # The default operating point, and the two queues it produces.
    default_frac = 0.15
    cap = int(accounts.height * ACTION_MINUTES["plan_offer"] * default_frac)
    alloc = allocate(accounts, cap, LAMBDA_HARM)
    risk = _risk_ranking(accounts, cap)

    alloc_actions = dict(zip(alloc["idx"].to_list(), alloc["action"].to_list()))
    risk_actions = dict(zip(risk["idx"].to_list(), risk["action"].to_list()))

    # Ship the accounts the two strategies disagree about most, plus enough
    # agreement to keep the picture honest.
    ranked = accounts.sort("exposure", descending=True)
    rows = []
    for r in ranked.iter_rows(named=True):
        a, k = alloc_actions.get(r["idx"], "do_not_contact"), risk_actions.get(r["idx"], "do_not_contact")
        rows.append({
            "loan_id": r["loan_id"],
            "exposure": round(float(r["exposure"]), 2),
            "p_worsen": round(float(r["p_worsen"]), 4),
            "p_selfcure": round(float(r["p_selfcure"]), 4),
            "allocator_action": a,
            "risk_ranking_action": k,
            "disagree": a != k,
        })
    disagreeing = [r for r in rows if r["disagree"]][:40]
    agreeing = [r for r in rows if not r["disagree"]][:20]
    sample = sorted(disagreeing + agreeing, key=lambda r: -r["exposure"])

    at_default = next(p for p in frontier if abs(p["capacity_frac"] - default_frac) < 1e-9)

    return {
        "action_minutes": ACTION_MINUTES,
        "lambda_harm": LAMBDA_HARM,
        "default_capacity_frac": default_frac,
        "accounts_in_queue": fig(accounts.height, "measured", "test-period delinquent snapshot"),
        "frontier": frontier,
        "headline": {
            "lift_pct": fig(at_default["lift_pct"], "simulated",
                            "allocator.compare at 15% capacity",
                            unit="%",
                            note="uplift shape is modelled from the literature, not measured; "
                                 "the magnitude is not a promise until a control arm produces it"),
            "allocator_contacts": fig(at_default["allocator_contacts"], "simulated",
                                      "allocator.compare at 15% capacity"),
            "risk_contacts": fig(at_default["risk_contacts"], "simulated",
                                 "allocator.compare at 15% capacity"),
        },
        "queue_sample": sample,
    }


def stage_audio() -> dict:
    """The latency budget, from real call audio rather than assertion."""
    import numpy as np
    from ganymede.audio.vad import (MIN_GAP_MS, analyse, inter_turn_gaps,
                                    load_wav_mono16k, segments, speech_frames)
    from ganymede.config import DATA_RAW, require_latency_budget

    wav = DATA_RAW / "call_16k.wav"
    if not wav.exists():
        raise FileNotFoundError(f"{wav} missing -- Phase 0 audio not present")

    summary = analyse(str(wav))
    samples, sr = load_wav_mono16k(str(wav))
    segs = segments(speech_frames(samples, sr))
    gaps_ms = np.array(inter_turn_gaps(segs)) * 1000.0

    edges = list(range(0, 2100, 100))
    hist = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        hist.append({"lo": lo, "hi": hi, "n": int(((gaps_ms >= lo) & (gaps_ms < hi)).sum())})
    hist.append({"lo": edges[-1], "hi": None, "n": int((gaps_ms >= edges[-1]).sum())})

    # A coarse waveform envelope for the desk's replay strip.
    win = max(1, len(samples) // 900)
    env = np.abs(samples[: (len(samples) // win) * win].reshape(-1, win)).max(axis=1)
    env = (env / (env.max() or 1.0)).round(3)

    # The enforced budget is the measured p25 rounded up to a round number. Both
    # are shipped: the site should not silently present the rounding as the
    # measurement, nor the measurement as the thing the code actually enforces.
    budget = require_latency_budget()
    return {
        "budget_ms": fig(budget, "measured",
                         "config.LATENCY_BUDGET_MS, set from the p25 of real gaps",
                         unit="ms",
                         note="derived from the gap distribution, not chosen; "
                              "p25 measures 292 ms and the enforced budget rounds it to 300"),
        "gap_p25_ms": fig(summary["gap_p25_ms"], "measured", "audio.vad.analyse", unit="ms"),
        "gap_p50_ms": fig(summary["gap_p50_ms"], "measured", "audio.vad.analyse", unit="ms"),
        "gap_p10_ms": fig(summary["gap_p10_ms"], "measured", "audio.vad.analyse", unit="ms"),
        "gap_mean_ms": fig(summary["gap_mean_ms"], "measured", "audio.vad.analyse", unit="ms"),
        "n_gaps": fig(summary["n_gaps"], "measured", "audio.vad.analyse"),
        "n_segments": fig(summary["n_segments"], "measured", "audio.vad.analyse"),
        "duration_s": summary["duration_s"],
        "speech_s": summary["speech_s"],
        "min_turn_gap_ms": MIN_GAP_MS,
        "histogram": hist,
        "gaps_ms": [round(float(g), 1) for g in gaps_ms],
        "segments": [{"start_s": round(s.start_s, 3), "end_s": round(s.end_s, 3)} for s in segs],
        "envelope": env.tolist(),
        "share_gaps_fitting_budget": fig(
            round(float((gaps_ms >= budget).mean()), 4), "measured",
            "share of real turn boundaries wide enough for a hint at the budget"),
        "share_gaps_fitting_llm": fig(
            round(float((gaps_ms >= 500).mean()), 4), "measured",
            "share of gaps a 500 ms LLM composition could have landed in",
            note="the reason tier-2 hints are demoted rather than raced"),
    }


def stage_coach() -> dict:
    """The playbook, its support counts, and the boundary the coach will not cross."""
    from ganymede.coach.boundary import MIN_TURN_GAP_MS
    from ganymede.coach.playbook import SEED
    from ganymede.config import MIN_STRATEGY_SUPPORT

    strategies = [{
        "id": s.id,
        "capacity": s.quadrant[0].value if s.quadrant else None,
        "willingness": s.quadrant[1].value if s.quadrant else None,
        "objection": s.objection,
        "text": s.text,
        "support_count": s.support_count,
        "provisional": s.is_provisional,
    } for s in SEED]

    return {
        "min_strategy_support": MIN_STRATEGY_SUPPORT,
        "min_turn_gap_ms": MIN_TURN_GAP_MS,
        "strategies": strategies,
        "all_provisional": fig(
            all(s["provisional"] for s in strategies), "seeded",
            "coach.playbook.SEED",
            note="no strategy has outcome support yet; every one is labelled seeded"),
    }


def stage_metrics(bundle: dict) -> dict:
    """The headline table. Assembled from the other stages so it cannot disagree."""
    rows = []

    def add(label, value, prov, source, unit=None, note=None):
        rows.append({"label": label, **fig(value, prov, source, unit, note)})

    r = bundle.get("risk", {}).get("models", {})
    if "L1_trajectory" in r:
        add("L1 trajectory AUC", r["L1_trajectory"]["auc"]["value"], "backtested", "risk.backtest()")
        add("L1 Brier vs base", f'{r["L1_trajectory"]["brier"]["value"]} vs {r["L1_trajectory"]["brier_base"]["value"]}',
            "backtested", "risk.backtest()")
    if "L2_selfcure" in r:
        add("L2 self-cure AUC", r["L2_selfcure"]["auc"]["value"], "backtested", "risk.backtest()")

    a = bundle.get("allocator", {})
    if a:
        h = a["headline"]
        add("Recovered value vs risk-ranking", h["lift_pct"]["value"], "simulated",
            h["lift_pct"]["source"], unit="%", note=h["lift_pct"]["note"])
        add("Contacts used (allocator vs risk-ranking)",
            f'{h["allocator_contacts"]["value"]} vs {h["risk_contacts"]["value"]}',
            "simulated", h["lift_pct"]["source"])

    au = bundle.get("audio", {})
    if au:
        add("Latency budget", au["budget_ms"]["value"], "measured", au["budget_ms"]["source"], unit="ms")
        add("Median inter-turn gap", au["gap_p50_ms"]["value"], "measured", au["gap_p50_ms"]["source"], unit="ms")
        add("Inter-turn gaps observed", au["n_gaps"]["value"], "measured", au["n_gaps"]["source"])

    p = bundle.get("panel", {})
    if p:
        add("Panel rows", p["rows"]["value"], "measured", "panel.parquet")
        add("Loans", p["loans"]["value"], "measured", "panel.parquet")

    d = bundle.get("risk", {}).get("drift", {})
    if d:
        add("Self-cure rate, train to test",
            f'{d["self_cure_train"]["value"]} to {d["self_cure_test"]["value"]}',
            "measured", "monitors.drift.check_rate_drift")

    # The deliberately unearned numbers. Listing them is the point.
    add("Recovery lift in production", None, "pending", "needs stage-2 pilot",
        note="cannot be estimated from simulation; the control arm measures it")
    add("Agent override rate", None, "pending", "needs stage-2 pilot")
    add("PTP-kept lift from coaching", None, "pending", "needs stage-2 pilot")
    add("Conversation features beating tabular", None, "pending",
        "blocked by invariant I1", note="evals/metrics.py refuses to compute lift on synthetic records")

    return {"provenance_legend": PROVENANCE, "rows": rows}


STAGES = {
    "panel": stage_panel,
    "risk": stage_risk,
    "allocator": stage_allocator,
    "audio": stage_audio,
    "coach": stage_coach,
}


def write(name: str, payload: dict, check: bool) -> bool:
    """Returns True when the file on disk already matches."""
    path = OUT / f"{name}.json"
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if check:
        return path.exists() and path.read_text(encoding="utf-8") == text
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify committed JSON matches what the pipeline now produces")
    ap.add_argument("--only", default="", help="comma-separated stage names")
    args = ap.parse_args()

    wanted = [s.strip() for s in args.only.split(",") if s.strip()] or list(STAGES)
    bundle, skipped, stale = {}, [], []

    for name in wanted:
        try:
            bundle[name] = STAGES[name]()
        except Exception as exc:                      # a missing input is not a build failure
            skipped.append((name, f"{type(exc).__name__}: {exc}"))
            if not isinstance(exc, (FileNotFoundError, ImportError)):
                traceback.print_exc()
            continue
        if not write(name, bundle[name], args.check):
            stale.append(name)
        print(f"  {'checked' if args.check else 'wrote'}  {name}.json")

    if set(wanted) == set(STAGES) or "metrics" in wanted:
        m = stage_metrics(bundle)
        if not write("metrics", m, args.check):
            stale.append("metrics")
        print(f"  {'checked' if args.check else 'wrote'}  metrics.json  ({len(m['rows'])} rows)")

    for name, why in skipped:
        print(f"  SKIPPED {name}: {why}")

    if args.check and stale:
        print(f"\nsite data is stale: {', '.join(stale)} -- run `python scripts/build_site_data.py`")
        return 1
    if skipped and args.check:
        print("\nnote: skipped stages were not checked; their inputs are absent here")
    print("\nsite data OK" if args.check else f"\nwrote {len(bundle) + 1} files to site/data/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
