"""The metric table. Assembles what is measurable now and states plainly what
needs a pilot — never dresses a synthetic number as evidence (I1).

Measurable on the data in hand:
  - risk calibration (L1 Brier vs base), from the Phase 3 backtest
  - hint usefulness + judge reliability, from the judge on the gold set
Requires the randomised pilot (I1, I2), so reported as pending:
  - recovery per agent-hour, PTP-kept lift, override rate on live traffic
"""

from __future__ import annotations

from ..invariants import check_no_synthetic_in_lift


def hint_usefulness(judge_result: dict) -> dict:
    return {
        "hint_usefulness": judge_result["judge_vs_human_agreement"],
        "target": 0.60,
        "passes": judge_result["judge_vs_human_agreement"] >= 0.60,
    }


def lift_on_set(values: list[float], is_synthetic_flags: list[bool]) -> dict:
    """Guarded: refuses to compute a lift number on a set containing synthetic
    records. This is I1 enforced in code, not documented."""
    violation = check_no_synthetic_in_lift(is_synthetic_flags)
    if violation:
        return {"lift": None, "refused": violation}
    return {"lift": round(sum(values) / len(values), 3), "refused": None}


def assemble(judge_result: dict, risk_result: list[dict]) -> dict:
    l1 = next((r for r in risk_result if r["model"] == "L1_trajectory"), {})
    table = {
        "hint_usefulness": {
            "value": judge_result["judge_vs_human_agreement"],
            "target": ">=0.60", "status": "measured",
        },
        "judge_reliability_alpha": {
            "value": judge_result["mixed_pool_alpha"],
            "ceiling": judge_result["within_judge_alpha"],
            "status": "measured (mixed-pool vs within-judge ceiling)",
        },
        "risk_calibration_brier": {
            "value": l1.get("brier"), "base": l1.get("brier_base"),
            "status": "measured (L1, beats base)" if l1.get("beats_base") else "measured",
        },
        "recovery_per_agent_hour": {"value": None, "status": "pilot required (I1/I2)"},
        "ptp_kept_lift": {"value": None, "status": "pilot required (I1)"},
        "override_rate": {"value": None, "status": "pilot required (live traffic)"},
    }
    return table
