"""`python -m ganymede.evals.report` — the Phase 8 gate.

Runs the judge on the gold set, pulls the risk backtest, checks self-cure drift,
and prints the full metric table. Writes reports/eval-YYYY-MM-DD.md. Exits
non-zero if a gate metric misses or the judge exceeds its reliability ceiling
(the SCHUFA-style "agreeing with itself, not with judgment" failure).
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ..config import REPORTS
from .judge import evaluate as judge_eval
from .metrics import assemble


def run(with_risk: bool = True) -> dict:
    jr = judge_eval()
    risk = []
    if with_risk:
        from ..risk import backtest
        risk = backtest()
    table = assemble(jr, risk)
    return {"judge": jr, "table": table}


def _fmt(result: dict) -> str:
    jr = result["judge"]
    lines = ["# Ganymede eval report", "", f"Date: {date.today()}", ""]
    lines.append("## Judge reliability")
    lines.append(f"- judge vs human agreement: {jr['judge_vs_human_agreement']}")
    lines.append(f"- within-judge alpha (ceiling): {jr['within_judge_alpha']}")
    lines.append(f"- mixed-pool alpha: {jr['mixed_pool_alpha']}")
    lines.append(f"- ceiling ok (not fitting noise): {jr['ceiling_ok']}")
    lines.append("")
    lines.append("## Metric table")
    lines.append("| metric | value | status |")
    lines.append("|---|---|---|")
    for k, v in result["table"].items():
        val = v.get("value")
        lines.append(f"| {k} | {val} | {v['status']} |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--no-risk", action="store_true")
    args = ap.parse_args()
    if args.report:
        result = run(with_risk=not args.no_risk)
        text = _fmt(result)
        print(text)
        REPORTS.mkdir(exist_ok=True)
        out = REPORTS / f"eval-{date.today()}.md"
        out.write_text(text, encoding="utf-8")
        jr = result["judge"]
        if jr["judge_vs_human_agreement"] < 0.60:
            print("\nEVAL FAILED: hint usefulness below 0.60")
            return 1
        if not jr["ceiling_ok"]:
            print("\nEVAL FAILED: judge exceeds its reliability ceiling (fitting noise)")
            return 1
        print(f"\neval OK -> {out}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
