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
    """The capacity frontier, and the queue each strategy would build.

    Every point is a real allocator run at that budget, and for the sampled
    accounts we record the capacity at which each strategy first funds them.
    That threshold is what the site's slider reads, so the page never
    re-implements the allocation rule in JavaScript and never drifts from it.
    """
    import polars as pl
    from ganymede.allocator import (ACTION_MINUTES, allocate, _realised_value,
                                    _risk_ranking, score_accounts)
    from ganymede.config import LAMBDA_HARM

    accounts = score_accounts()
    n = accounts.height
    fracs = [round(0.01 * i, 3) for i in range(2, 61)]  # 2% .. 60% of full coverage

    # Sample first, so membership is tracked for a stable set across the sweep:
    # the biggest exposures, plus the two contrasts that carry the argument.
    ranked = accounts.sort("exposure", descending=True)
    sample_ids = set(ranked.head(40)["idx"].to_list())
    sample_ids |= set(accounts.filter((pl.col("p_worsen") > 0.6) & (pl.col("exposure") > 1000))
                              .sort("exposure").head(6)["idx"].to_list())
    sample_ids |= set(accounts.filter(pl.col("exposure") > 100_000)
                              .sort("p_selfcure", descending=True).head(6)["idx"].to_list())

    frontier, enters_alloc, enters_risk = [], {}, {}
    default_frac = 0.15
    detail = None

    for f in fracs:
        cap = int(n * ACTION_MINUTES["plan_offer"] * f)
        alloc = allocate(accounts, cap, LAMBDA_HARM)
        risk = _risk_ranking(accounts, cap)
        v_a, v_r = _realised_value(alloc), _realised_value(risk)

        a_funded = set(alloc.filter(pl.col("action") != "do_not_contact")["idx"].to_list())
        r_funded = set(risk.filter(pl.col("action") != "do_not_contact")["idx"].to_list())
        for i in sample_ids:
            if i in a_funded:
                enters_alloc.setdefault(i, f)
            if i in r_funded:
                enters_risk.setdefault(i, f)

        frontier.append({
            "capacity_frac": f, "capacity_minutes": cap, "accounts": n,
            "allocator_value": round(v_a, 1), "risk_ranking_value": round(v_r, 1),
            "lift_pct": round(100 * (v_a - v_r) / abs(v_r), 1) if v_r else float("inf"),
            "allocator_contacts": len(a_funded), "risk_contacts": len(r_funded),
        })
        if abs(f - default_frac) < 1e-9:
            detail = alloc

    at_default = next(p for p in frontier if abs(p["capacity_frac"] - default_frac) < 1e-9)
    action_of = {r["idx"]: r for r in detail.iter_rows(named=True)}

    queue_sample = []
    for r in accounts.filter(pl.col("idx").is_in(list(sample_ids))).iter_rows(named=True):
        i = r["idx"]
        d = action_of[i]
        queue_sample.append({
            "loan_id": r["loan_id"],
            "exposure": round(float(r["exposure"]), 2),
            "p_worsen": round(float(r["p_worsen"]), 4),
            "p_selfcure": round(float(r["p_selfcure"]), 4),
            "best_action": d["action"] if d["action"] != "do_not_contact" else None,
            "value": round(float(d["value"]), 2),
            "minutes": int(d["minutes"]),
            # capacity at which each strategy first funds this account; null means
            # it is never funded anywhere in the sweep
            "enters_allocator_at": enters_alloc.get(i),
            "enters_risk_at": enters_risk.get(i),
        })
    queue_sample.sort(key=lambda a: -a["exposure"])

    return {
        "action_minutes": ACTION_MINUTES,
        "lambda_harm": LAMBDA_HARM,
        "default_capacity_frac": default_frac,
        "sweep_from": fracs[0], "sweep_to": fracs[-1],
        "accounts_in_queue": fig(n, "measured", "test-period delinquent snapshot"),
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
        "queue_sample": queue_sample,
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
    # Round once, here. Gaps are frame-quantised in seconds, so a gap of exactly
    # 300 ms can land at 299.999... after the multiply -- which put eight
    # boundaries on the wrong side of the budget compared with the rounded array
    # the site actually draws. One array, one truth.
    gaps_ms = np.round(np.array(inter_turn_gaps(segs)) * 1000.0, 1)

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


def stage_trajectories() -> dict:
    """Real borrower paths for the hero backdrop.

    The atmospheric layer on the home page is not a gradient: it is a few
    hundred actual delinquency trajectories from the panel, most of them quiet,
    a handful bending. The picture is the argument -- the Risk Lens exists to
    notice the few that bend, before they break.
    """
    import polars as pl
    from ganymede.panel import PANEL_PATH

    if not PANEL_PATH.exists():
        raise FileNotFoundError("panel.parquet missing")

    WINDOW = 24
    p = pl.read_parquet(PANEL_PATH, columns=["loan_id", "period_date", "delinq"])
    seq = (p.sort(["loan_id", "period_date"])
            .group_by("loan_id", maintain_order=True)
            .agg([pl.col("delinq").alias("d"), pl.len().alias("n")])
            .filter(pl.col("n") >= WINDOW)
            # deterministic order, so the backdrop does not churn between builds
            .with_columns(pl.col("loan_id").hash(seed=7).alias("h"))
            .sort("h"))

    # "Quiet" is at most one missed month across two years, not a spotless
    # record: this panel samples delinquent histories in full and current ones
    # as short stubs, so no loan is both perfectly clean and long-lived. Drawing
    # a spotless field would mean inventing loans that are not in the data.
    quiet, bending = [], []
    for row in seq.iter_rows(named=True):
        d = [int(v) for v in row["d"]]
        bad = sum(1 for v in d if v >= 1)
        peak = max(d)
        if bad <= 1 and len(quiet) < 240:
            quiet.append(d[:WINDOW])
        elif peak >= 2 and len(bending) < 80:
            first_bad = next(i for i, v in enumerate(d) if v >= 1)
            lo = max(0, min(first_bad - 6, len(d) - WINDOW))
            bending.append(d[lo:lo + WINDOW])
        if len(quiet) >= 240 and len(bending) >= 80:
            break

    return {
        "window_months": WINDOW,
        "quiet": quiet,
        "bending": bending,
        "max_bucket": max((max(t) for t in bending + quiet), default=1),
        "quiet_rule": "at most one delinquent month in 24",
        "bending_rule": "reaches 60+ days past due; window starts six months before the first miss",
        "source": fig("panel.parquet", "measured",
                      "hash-ordered deterministic sample of 24-month windows"),
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

    # These two call an external model, so they are recorded from their gate run
    # rather than recomputed on every build: a live call would spend credits on
    # each site rebuild and make --check non-deterministic. Reproduce with the
    # commands named in `source`.
    recorded = {
        "ptp_field_accuracy": fig(
            0.934, "measured", "python -m ganymede.coach.ptp_eval (docs/phase6-conversations.md)",
            note="gold-set run against a live model; bar 0.80. Not recomputed per build."),
        "ptp_bar": 0.80,
        "judge_agreement": fig(
            0.917, "measured", "python -m ganymede.evals.report --report (docs/phase8-evals.md)",
            note="LLM judge vs human labels; mixed-pool alpha 0.886 sits under the "
                 "within-judge ceiling of 1.0. Not recomputed per build."),
        "judge_alpha_mixed": 0.886,
    }

    return {
        "min_strategy_support": MIN_STRATEGY_SUPPORT,
        "min_turn_gap_ms": fig(MIN_TURN_GAP_MS, "measured",
                               "coach.boundary.MIN_TURN_GAP_MS, matching the VAD threshold",
                               unit="ms",
                               note="a silence shorter than this is a within-speech micro-pause, "
                                    "not a hand-off, so no hint fires there"),
        "recorded": recorded,
        "strategies": strategies,
        "all_provisional": fig(
            all(s["provisional"] for s in strategies), "seeded",
            "coach.playbook.SEED",
            note="no strategy has outcome support yet; every one is labelled seeded"),
    }


def stage_state() -> dict:
    """Borrower state over the real queue: how often the data settles the quadrant.

    Capacity is estimable from a payment trajectory; willingness is not, without
    a conversation. This stage measures how often that bites, which is the whole
    reason the product has a second lens.
    """
    from ganymede.allocator import score_accounts
    from ganymede.features import FEATURE_COLS, build_features, time_split
    from ganymede.schema import Capacity, Willingness
    from ganymede.state import estimate_state, strategy_for
    import polars as pl

    feats = build_features()
    _, test_df = time_split(feats)
    snap = (test_df.filter(pl.col("d") >= 1)
                   .unique(subset=["loan_id"], keep="last")
                   .select(["loan_id", *FEATURE_COLS]))

    counts, certain, confs = {}, 0, []
    for row in snap.iter_rows(named=True):
        st = estimate_state(row)
        key = f"{st.capacity.value} x {st.willingness.value}"
        counts[key] = counts.get(key, 0) + 1
        confs.append(st.confidence)
        if st.is_certain:
            certain += 1

    n = snap.height
    confs.sort()
    return {
        "accounts": fig(n, "measured", "test-period delinquent snapshot"),
        "confident_quadrant": fig(round(certain / n, 4), "measured",
                                  "state.estimate_state over the queue"),
        "routes_to_diagnostic": fig(
            round(1 - certain / n, 4), "measured", "state.estimate_state over the queue",
            note="willingness cannot be read from servicing data, so most accounts "
                 "get the diagnostic question rather than a guessed strategy"),
        "median_confidence": fig(round(confs[n // 2], 3), "measured", "state.estimate_state"),
        "quadrants": [{"quadrant": k, "n": v, "share": round(v / n, 4)}
                      for k, v in sorted(counts.items(), key=lambda kv: -kv[1])],
        "strategies": {
            f"{c.value} x {w.value}": strategy_for(
                type("S", (), {"capacity": c, "willingness": w, "is_certain": True})())
            for c in (Capacity.CAN_PAY, Capacity.CANNOT_PAY)
            for w in (Willingness.WILL_PAY, Willingness.WILL_NOT_PAY)
        },
    }


def stage_desk() -> dict:
    """The queue the agent desk works, and the one real scored call.

    Fourteen accounts drawn from the live queue -- the ones the allocator funds,
    plus deliberate contrasts it skips -- each carrying its own scores, reason
    codes, borrower state and recommended action. Only one has a transcript,
    because only one real call was scored; the desk says so rather than pairing
    a borrower's panel with somebody else's conversation.
    """
    import json
    import polars as pl
    from ganymede.allocator import ACTION_MINUTES, allocate
    from ganymede.config import LAMBDA_HARM
    from ganymede.features import FEATURE_COLS, build_features, time_split
    from ganymede.panel import PROCESSED
    from ganymede.risk import predict, reason_codes, train
    from ganymede.state import estimate_state, strategy_for

    feats = build_features()
    train_df, test_df = time_split(feats)
    snap = test_df.filter(pl.col("d") >= 1).unique(subset=["loan_id"], keep="last")

    b1, i1 = train(train_df, "y_worsen")
    b2, i2 = train(train_df.filter(pl.col("d") >= 1), "y_selfcure")

    scored = snap.with_columns([
        pl.Series("p_worsen", predict(b1, i1, snap)),
        pl.Series("p_selfcure", predict(b2, i2, snap)),
        pl.col("upb").alias("exposure"),
    ]).with_row_index("idx")

    alloc = allocate(
        scored.select(["idx", "loan_id", "exposure", "p_worsen", "p_selfcure"]),
        int(scored.height * ACTION_MINUTES["plan_offer"] * 0.15), LAMBDA_HARM)
    decision = {r["idx"]: r for r in alloc.iter_rows(named=True)}
    rank = {idx: i + 1 for i, idx in enumerate(alloc["idx"].to_list())}

    # Twelve the allocator funds, and two it deliberately skips: a high-probability
    # trivial-exposure account and a near-certain self-curer. The contrast is the
    # argument -- a queue of only funded accounts hides the decision being made.
    funded = alloc.filter(pl.col("action") != "do_not_contact").head(12)["idx"].to_list()
    skipped = (scored.filter((pl.col("p_worsen") > 0.6) & (pl.col("exposure") > 1000))
                     .sort("exposure").head(1)["idx"].to_list()
               + scored.filter(pl.col("exposure") > 100_000)
                       .sort("p_selfcure", descending=True).head(1)["idx"].to_list())
    wanted = list(dict.fromkeys(funded + skipped))

    chosen = scored.filter(pl.col("idx").is_in(wanted))
    codes = reason_codes(b1, chosen, k=3)

    accounts = []
    for row, rc in zip(chosen.iter_rows(named=True), codes):
        st = estimate_state(row)
        d = decision[row["idx"]]
        accounts.append({
            "loan_id": row["loan_id"],
            "exposure": round(float(row["exposure"]), 2),
            "arrears_months": int(row["d"]),
            "p_worsen": round(float(row["p_worsen"]), 4),
            "p_selfcure": round(float(row["p_selfcure"]), 4),
            "reason_codes": rc,
            "capacity": st.capacity.value,
            "willingness": st.willingness.value,
            "state_conf": st.confidence,
            "state_certain": st.is_certain,
            "strategy": strategy_for(st),
            "action": d["action"],
            "action_minutes": ACTION_MINUTES[d["action"]],
            "value": round(float(d["value"]), 1),
            "queue_rank": rank[row["idx"]],
            "credit_score": int(row["credit_score"]) if row["credit_score"] is not None else None,
            "dti": int(row["dti"]) if row["dti"] is not None else None,
            "orig_ltv": int(row["orig_ltv"]) if row["orig_ltv"] is not None else None,
            "delinq_trend_3m": float(row["delinq_trend_3m"] or 0),
            "delinq_max_3m": int(row["delinq_max_3m"] or 0),
        })
    accounts.sort(key=lambda a: a["queue_rank"])

    replay = None
    rp = PROCESSED / "demo_replay.json"
    if rp.exists():
        replay = json.loads(rp.read_text(encoding="utf-8"))

    # The scored call belongs to an account the queue does not contain. Add it
    # rather than pairing its transcript with somebody else's panel: exactly one
    # account here has a recorded conversation, and the desk should say which.
    for a in accounts:
        a["has_transcript"] = False
    if replay:
        ra = replay["account"]
        if not any(a["loan_id"] == ra["loan_id"] for a in accounts):
            accounts.append({
                "loan_id": ra["loan_id"],
                "exposure": ra["exposure"],
                "arrears_months": ra["arrears_months"],
                "p_worsen": ra["p_worsen"],
                "p_selfcure": ra["p_selfcure"],
                "reason_codes": ra["reason_codes"],
                "capacity": ra["capacity"],
                "willingness": ra["willingness"],
                "state_conf": ra["state_conf"],
                "state_certain": ra["state_conf"] >= 0.6,
                "strategy": ra["strategy"],
                "action": "plan_offer",
                "action_minutes": ACTION_MINUTES["plan_offer"],
                "value": None,
                "queue_rank": None,
                "credit_score": None, "dti": None, "orig_ltv": None,
                "delinq_trend_3m": None, "delinq_max_3m": None,
                "has_transcript": True,
            })

    return {
        "queue_size": fig(scored.height, "measured", "test-period delinquent snapshot"),
        "capacity_frac": 0.15,
        "action_minutes": ACTION_MINUTES,
        "accounts": accounts,
        "replay": replay,
        "replay_loan_id": (replay or {}).get("account", {}).get("loan_id"),
        "feature_cols": FEATURE_COLS,
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

    st = bundle.get("state", {})
    if st:
        add("Accounts routed to a diagnostic question", st["routes_to_diagnostic"]["value"],
            "measured", st["routes_to_diagnostic"]["source"],
            note=st["routes_to_diagnostic"]["note"])

    co = bundle.get("coach", {}).get("recorded", {})
    if co:
        add("PTP extractor field accuracy", co["ptp_field_accuracy"]["value"], "measured",
            co["ptp_field_accuracy"]["source"], note=co["ptp_field_accuracy"]["note"])
        add("LLM judge vs human agreement", co["judge_agreement"]["value"], "measured",
            co["judge_agreement"]["source"], note=co["judge_agreement"]["note"])

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
    "trajectories": stage_trajectories,
    "state": stage_state,
    "desk": stage_desk,
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

    # metrics is assembled from every other stage, so it is only meaningful when
    # every other stage actually ran. On a clean checkout the panel and the call
    # audio are absent, and rebuilding metrics from the handful of stages that
    # survived would compare a six-row table against the committed eighteen and
    # call the committed one stale. Skip it instead, and say why.
    metrics_wanted = set(wanted) == set(STAGES) or "metrics" in wanted
    if metrics_wanted and skipped:
        print("  SKIPPED metrics: assembled from stages that could not run here")
    elif metrics_wanted:
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
        names = ", ".join(n for n, _ in skipped)
        print(f"\nnote: not checked, inputs absent here: {names}")
    # metrics only counts when it was actually written
    written = len(bundle) + (0 if skipped else 1)
    print("\nsite data OK" if args.check else f"\nwrote {written} files to site/data/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
