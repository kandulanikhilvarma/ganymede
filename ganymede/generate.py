"""Synthetic collections conversations, conditioned on real trajectories.

Each conversation is seeded from a real delinquent panel row (arrears depth,
exposure) plus a borrower-state quadrant. The generator is told the borrower's
situation but NOT whether they ultimately pay — the outcome label is derived
afterwards from the panel, so the generator cannot write the answer into the
transcript. This bounds, and does not eliminate, the correlation between seed
and outcome; synthetic data validates plumbing only and never a lift claim (I1).

Every conversation is flagged is_synthetic=True at the source, which is what
lets evals refuse to compute lift on it.
"""

from __future__ import annotations

import polars as pl

from .llm import LLMEngine, Role, get_engine
from .schema import Capacity, Willingness

_SYSTEM = (
    "You write short, realistic debt-collection phone calls between a collections "
    "agent and a borrower. Natural, with disfluencies. 6 to 10 turns. Label each "
    "turn AGENT: or BORROWER:. Do not narrate. Do not state whether the borrower "
    "ultimately pays — end the call where a real call would end."
)

_QUADRANT_BRIEF = {
    (Capacity.CAN_PAY, Willingness.WILL_PAY): "has the money, just disorganised — forgot or friction",
    (Capacity.CAN_PAY, Willingness.WILL_NOT_PAY): "has the money but is resisting paying",
    (Capacity.CANNOT_PAY, Willingness.WILL_PAY): "wants to pay but genuinely cannot afford it right now",
    (Capacity.CANNOT_PAY, Willingness.WILL_NOT_PAY): "cannot pay and is avoiding contact",
}


def generate_conversation(
    borrower_id: str,
    arrears_months: int,
    exposure: float,
    quadrant: tuple[Capacity, Willingness],
    engine: LLMEngine | None = None,
) -> dict:
    engine = engine or get_engine()
    brief = _QUADRANT_BRIEF[quadrant]
    prompt = (
        f"The borrower is {arrears_months} month(s) behind on a balance of about "
        f"EUR {int(exposure):,}. Situation: the borrower {brief}. "
        f"Write the call."
    )
    transcript = engine.complete(Role.GENERATE, prompt, system=_SYSTEM, max_tokens=700)
    return {
        "borrower_id": borrower_id,
        "transcript": transcript,
        "is_synthetic": True,  # I1
        "arrears_months": arrears_months,
        "exposure": exposure,
        "quadrant": f"{quadrant[0].value}|{quadrant[1].value}",
    }


def _seed_rows(n: int, seed: int = 7) -> list[dict]:
    """Sample real delinquent panel rows as generation seeds."""
    from .features import build_features
    from .state import estimate_state

    f = build_features().filter(pl.col("d") >= 1).unique(subset=["loan_id"], keep="last")
    sample = f.sample(min(n, f.height), seed=seed)
    rows = []
    for r in sample.iter_rows(named=True):
        st = estimate_state(r)
        cap = st.capacity if st.capacity is not Capacity.UNKNOWN else Capacity.CANNOT_PAY
        wil = st.willingness if st.willingness is not Willingness.UNKNOWN else Willingness.WILL_PAY
        rows.append({
            "borrower_id": r["loan_id"],
            "arrears_months": int(r["d"]),
            "exposure": float(r["upb"] or r["orig_upb"] or 100000),
            "quadrant": (cap, wil),
        })
    return rows


def generate_batch(n: int = 15, seed: int = 7, engine: LLMEngine | None = None) -> list[dict]:
    engine = engine or get_engine()
    return [generate_conversation(engine=engine, **s) for s in _seed_rows(n, seed)]
