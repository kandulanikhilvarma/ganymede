"""LLM-as-judge for hint usefulness, with Krippendorff's alpha reliability.

The method is the one the plan's risk research settled on: put the judge into the
annotator pool and test whether its agreement with the human is comparable to the
human's agreement with itself. With one human labeller, the ceiling is intra-rater
self-agreement, not human-human — a judge scoring ABOVE that ceiling is fitting
noise, not agreeing with judgment.

Two numbers come out:
  within-judge alpha  — self-consistency across repeated runs (should be high; if
                        low the rubric is ambiguous, not the model bad).
  mixed-pool alpha    — [human, judge run 1, judge run 2]; at/near the within-judge
                        figure means the judge behaves like a second coder.
"""

from __future__ import annotations

import json
from pathlib import Path

import krippendorff
import numpy as np

from ..llm import LLMEngine, Role, get_engine

GOLD = Path(__file__).parent / "hint_gold.json"

_SYSTEM = (
    "You judge whether a real-time coaching hint is USEFUL to a collections agent "
    "at the moment it appears. Useful means: acting on it plausibly moves the "
    "conversation toward a specific, keepable outcome, and it fits the borrower's "
    "situation. Not useful: generic, mistimed, aimed at the wrong situation, or "
    "harmful. Answer with a single character: 1 for useful, 0 for not."
)


def judge_hint(context: str, hint: str, engine: LLMEngine) -> int | None:
    """1 useful, 0 not, None when the reply is neither. An empty reply or a
    refusal used to count as 0, which reads as a confident "not useful"."""
    out = engine.complete(
        Role.JUDGE,
        f"Situation:\n{context}\n\nHint shown to the agent:\n{hint}\n\nUseful? 1 or 0.",
        system=_SYSTEM, max_tokens=3,
    ).strip()
    if out[:1] in ("0", "1"):
        return int(out[0])
    return None


def _alpha(rows: list[list]) -> float:
    """Nominal alpha with missing ratings as NaN. When every rating is the same
    value, krippendorff raises; alpha is undefined there, so report NaN."""
    data = np.array([[np.nan if v is None else v for v in r] for r in rows], dtype=float)
    try:
        return float(krippendorff.alpha(reliability_data=data, level_of_measurement="nominal"))
    except ValueError:
        return float("nan")


def evaluate(engine: LLMEngine | None = None, runs: int = 2) -> dict:
    engine = engine or get_engine()
    data = json.loads(GOLD.read_text())
    cases = data["cases"]
    human = [c["useful"] for c in cases]

    # judge each case `runs` times for self-consistency
    judge_runs = []
    for _ in range(runs):
        judge_runs.append([judge_hint(c["context"], c["hint"], engine) for c in cases])

    # agreement: judge run 1 vs human, over the cases the judge actually answered
    answered = [(j, h) for j, h in zip(judge_runs[0], human) if j is not None]
    agree = float(np.mean([j == h for j, h in answered])) if answered else float("nan")
    unanswered = sum(j is None for run in judge_runs for j in run)

    # within-judge alpha across the runs (nominal)
    within = _alpha(judge_runs) if runs >= 2 else float("nan")

    # mixed-pool alpha: human + judge runs together
    mixed = _alpha([human, *judge_runs])

    return {
        "n_cases": len(cases),
        "judge_vs_human_agreement": round(agree, 3),
        "within_judge_alpha": round(within, 3),
        "mixed_pool_alpha": round(mixed, 3),
        "runs": runs,
        "unanswered": unanswered,
        # the ceiling test: mixed-pool alpha should not exceed within-judge alpha
        "ceiling_ok": (mixed <= within + 0.05) if runs >= 2 else True,
    }
