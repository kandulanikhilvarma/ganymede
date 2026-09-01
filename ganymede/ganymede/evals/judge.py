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


def judge_hint(context: str, hint: str, engine: LLMEngine) -> int:
    out = engine.complete(
        Role.JUDGE,
        f"Situation:\n{context}\n\nHint shown to the agent:\n{hint}\n\nUseful? 1 or 0.",
        system=_SYSTEM, max_tokens=3,
    ).strip()
    return 1 if "1" in out[:2] else 0


def evaluate(engine: LLMEngine | None = None, runs: int = 2) -> dict:
    engine = engine or get_engine()
    data = json.loads(GOLD.read_text())
    cases = data["cases"]
    human = [c["useful"] for c in cases]

    # judge each case `runs` times for self-consistency
    judge_runs = []
    for _ in range(runs):
        judge_runs.append([judge_hint(c["context"], c["hint"], engine) for c in cases])

    # agreement: judge run 1 vs human
    agree = float(np.mean([j == h for j, h in zip(judge_runs[0], human)]))

    # within-judge alpha across the runs (nominal)
    within = krippendorff.alpha(reliability_data=judge_runs, level_of_measurement="nominal") \
        if runs >= 2 else float("nan")

    # mixed-pool alpha: human + judge runs together
    mixed = krippendorff.alpha(reliability_data=[human, *judge_runs],
                               level_of_measurement="nominal")

    return {
        "n_cases": len(cases),
        "judge_vs_human_agreement": round(agree, 3),
        "within_judge_alpha": round(within, 3),
        "mixed_pool_alpha": round(mixed, 3),
        "runs": runs,
        # the ceiling test: mixed-pool alpha should not exceed within-judge alpha
        "ceiling_ok": (mixed <= within + 0.05) if runs >= 2 else True,
    }
