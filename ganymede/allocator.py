"""Expected-value allocation under a capacity constraint (I9, I10).

The one decision the Risk Lens exists to make: given a fixed pool of agent-
minutes, which accounts to work, in what order, or to leave alone. Risk-ranking
— sort by probability of default, work the top — is the expensive mistake this
replaces. It spends the most costly resource in the business on the least
recoverable accounts, and ignores how much money is actually on each one.

The objective per account:

    value(action) = ΔP(recover | action) · exposure − cost(action) − λ · P(harm)
    ΔP(recover | action) = P(recover | action) − P(self-cure | no action)

Δ, not P: the worth of contacting someone is the *uplift* over leaving them
alone. Self-cure (L2) subtracts. Exposure weights it. λ prices relationship
harm. Capacity turns it from a score into an assignment.

Honest boundary: Freddie Mac has no treatment data, so P(recover | action) —
the uplift — cannot be measured here. It is modelled from the uplift literature:
effect is largest in the *persuadable middle* (accounts that will neither cure
on their own nor default regardless) and near zero at both ends. This simulation
proves the allocator's LOGIC beats risk-ranking under a defensible uplift shape.
It is not a claim about real lift — that needs a pilot (I1).
"""

from __future__ import annotations

import argparse

import numpy as np
import polars as pl

from .config import LAMBDA_HARM
from .features import build_features, time_split
from .risk import predict, train

# Action costs in agent-minutes and their relative effect strength.
ACTION_MINUTES = {"do_not_contact": 0, "reminder": 3, "plan_offer": 12, "restructure": 25}
ACTION_STRENGTH = {"do_not_contact": 0.0, "reminder": 0.4, "plan_offer": 1.0, "restructure": 1.3}
LOADED_RATE_PER_MIN = 1.0  # cost units per agent-minute
HARM_PER_CONTACT = 0.02    # base P(harm) per contact attempt


def modelled_uplift(p_selfcure: np.ndarray, strength: float) -> np.ndarray:
    """Persuadable-middle uplift: peaks where self-cure is uncertain, ~0 at the
    ends. A borrower who will cure anyway (p~1) or is unreachable-hopeless (p~0)
    gains little from contact; the middle is where a conversation moves the
    outcome. Shape from uplift-modelling literature, scaled by action strength."""
    persuadable = 4.0 * p_selfcure * (1.0 - p_selfcure)  # tent peaking at 0.5
    return strength * 0.25 * persuadable  # cap ~25pp uplift at full strength/mid


def _best_action(p_selfcure: float, exposure: float, lam: float):
    """Return (action, value, minutes) for the value-maximising action."""
    best = ("do_not_contact", 0.0, 0)
    for action, minutes in ACTION_MINUTES.items():
        if action == "do_not_contact":
            continue
        uplift = modelled_uplift(np.array([p_selfcure]), ACTION_STRENGTH[action])[0]
        cost = minutes * LOADED_RATE_PER_MIN
        harm = HARM_PER_CONTACT * ACTION_STRENGTH[action]
        value = uplift * exposure - cost - lam * harm * exposure * 0.001
        if value > best[1]:
            best = (action, value, minutes)
    return best


def allocate(accounts: pl.DataFrame, capacity_minutes: int, lam: float = LAMBDA_HARM) -> pl.DataFrame:
    """Assign actions under capacity. Rank by value density (value per minute),
    fill greedily; everything unfunded -> do_not_contact. Greedy is the standard
    knapsack heuristic and is optimal enough here — the point is the objective,
    not the last basis point of the solver."""
    rows = []
    for r in accounts.iter_rows(named=True):
        action, value, minutes = _best_action(r["p_selfcure"], r["exposure"], lam)
        density = value / minutes if minutes > 0 else 0.0
        rows.append({**r, "action": action, "value": value, "minutes": minutes, "density": density})
    ranked = pl.DataFrame(rows).sort("density", descending=True)

    spent, chosen = 0, []
    for r in ranked.iter_rows(named=True):
        if r["action"] != "do_not_contact" and r["value"] > 0 and spent + r["minutes"] <= capacity_minutes:
            chosen.append(r["idx"])
            spent += r["minutes"]
    return ranked.with_columns(
        pl.when(pl.col("idx").is_in(chosen)).then(pl.col("action")).otherwise(pl.lit("do_not_contact")).alias("action")
    )


def _realised_value(assignment: pl.DataFrame) -> float:
    """True incremental recovery under an assignment: contacted accounts realise
    uplift x exposure minus cost; skipped accounts realise 0 incremental."""
    total = 0.0
    for r in assignment.iter_rows(named=True):
        if r["action"] == "do_not_contact":
            continue
        uplift = modelled_uplift(np.array([r["p_selfcure"]]), ACTION_STRENGTH[r["action"]])[0]
        total += uplift * r["exposure"] - ACTION_MINUTES[r["action"]] * LOADED_RATE_PER_MIN
    return total


def _risk_ranking(accounts: pl.DataFrame, capacity_minutes: int) -> pl.DataFrame:
    """Baseline: what conventional collections does. Sort by risk (worsen prob),
    work the top with a fixed action until capacity runs out. Ignores exposure,
    ignores self-cure, ignores uplift."""
    ranked = accounts.sort("p_worsen", descending=True)
    minutes = ACTION_MINUTES["plan_offer"]
    spent, chosen = 0, []
    for r in ranked.iter_rows(named=True):
        if spent + minutes <= capacity_minutes:
            chosen.append(r["idx"]); spent += minutes
    return ranked.with_columns(
        pl.when(pl.col("idx").is_in(chosen)).then(pl.lit("plan_offer")).otherwise(pl.lit("do_not_contact")).alias("action")
    )


def simulate(capacity_frac: float = 0.15, lam: float = LAMBDA_HARM) -> dict:
    feats = build_features()
    train_df, test_df = time_split(feats)

    # snapshot: currently-delinquent accounts in the test period (the workable queue)
    snap = test_df.filter(pl.col("d") >= 1).unique(subset=["loan_id"], keep="last")

    b1, i1 = train(train_df, "y_worsen")
    tr_dq = train_df.filter(pl.col("d") >= 1)
    b2, i2 = train(tr_dq, "y_selfcure")

    accounts = snap.with_columns([
        pl.Series("p_worsen", predict(b1, i1, snap)),
        pl.Series("p_selfcure", predict(b2, i2, snap)),
        pl.col("upb").alias("exposure"),
    ]).with_row_index("idx").select(["idx", "loan_id", "exposure", "p_worsen", "p_selfcure"])

    # capacity as a fraction of the minutes it would take to plan_offer everyone
    capacity = int(accounts.height * ACTION_MINUTES["plan_offer"] * capacity_frac)

    alloc = allocate(accounts, capacity, lam)
    risk = _risk_ranking(accounts, capacity)

    v_alloc = _realised_value(alloc)
    v_risk = _realised_value(risk)
    return {
        "accounts": accounts.height, "capacity_minutes": capacity,
        "allocator_value": round(v_alloc, 1), "risk_ranking_value": round(v_risk, 1),
        "lift_pct": round(100 * (v_alloc - v_risk) / abs(v_risk), 1) if v_risk else float("inf"),
        "allocator_contacts": alloc.filter(pl.col("action") != "do_not_contact").height,
        "risk_contacts": risk.filter(pl.col("action") != "do_not_contact").height,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--simulate", action="store_true")
    ap.add_argument("--capacity-frac", type=float, default=0.15)
    ap.add_argument("--lam", type=float, default=LAMBDA_HARM)
    args = ap.parse_args()
    if args.simulate:
        r = simulate(args.capacity_frac, args.lam)
        for k, v in r.items():
            print(f"  {k}: {v}")
        if r["allocator_value"] <= r["risk_ranking_value"]:
            print("SIMULATE FAILED: allocator did not beat risk-ranking")
            return 1
        print(f"simulate OK: value-ranking beats risk-ranking by {r['lift_pct']}% recovered value")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
