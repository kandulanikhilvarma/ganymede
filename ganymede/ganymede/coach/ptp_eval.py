"""Clear the PTP extractor against its gold set (I6).

Scores field-level accuracy: promise-vs-no-promise, amount, due-date presence,
and method. The extractor may not be used downstream until it clears the bar —
enforced in tests/test_ptp.py, which fails the Phase 6 gate otherwise.

Date scoring is presence + exact match when the truth has a date; near-miss on
resolving relative dates ("this Friday") is scored on presence so one calendar
ambiguity does not sink an otherwise-correct extraction.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..llm import LLMEngine, get_engine
from .extract import extract_promise

GOLD = Path(__file__).parent / "ptp_gold.json"
BAR = 0.80  # field-level accuracy the extractor must clear


def _fields(pred, truth) -> list[bool]:
    """Per-case field correctness against the truth dict."""
    pred_has = pred is not None
    checks = [pred_has == truth["has_promise"]]
    if not truth["has_promise"]:
        return checks  # only the has_promise call matters for a non-promise
    if pred is None:
        return checks + [False, False, False]  # missed a real promise entirely
    # amount: exact when specified, else expect null
    checks.append(
        (truth["amount"] is None and pred.amount is None)
        or (truth["amount"] is not None and pred.amount == truth["amount"])
    )
    # due: presence match (specified vs not); exact date when both present
    t_due = truth["due"] is not None
    p_due = pred.due is not None
    if t_due and p_due:
        checks.append(pred.due == date.fromisoformat(truth["due"]))
    else:
        checks.append(t_due == p_due)
    # method: exact when specified, else expect null
    checks.append(
        (truth["method"] is None and pred.method is None)
        or (truth["method"] is not None and pred.method == truth["method"])
    )
    return checks


def evaluate(engine: LLMEngine | None = None) -> dict:
    engine = engine or get_engine()
    data = json.loads(GOLD.read_text())
    ref = date.fromisoformat(data["reference_date"])
    correct = total = 0
    has_correct = 0
    per_case = []
    for c in data["cases"]:
        pred = extract_promise(c["transcript"], c["id"], ref=ref, engine=engine)
        checks = _fields(pred, c["truth"])
        correct += sum(checks)
        total += len(checks)
        has_correct += int(checks[0])
        per_case.append({"id": c["id"], "field_acc": round(sum(checks) / len(checks), 2)})
    return {
        "field_accuracy": round(correct / total, 3),
        "has_promise_accuracy": round(has_correct / len(data["cases"]), 3),
        "n_cases": len(data["cases"]),
        "bar": BAR,
        "passes": correct / total >= BAR,
        "per_case": per_case,
    }


if __name__ == "__main__":
    import sys
    r = evaluate()
    for k, v in r.items():
        if k != "per_case":
            print(f"  {k}: {v}")
    print("PTP extractor", "OK" if r["passes"] else "BELOW BAR")
    sys.exit(0 if r["passes"] else 1)
