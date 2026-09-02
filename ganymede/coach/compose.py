"""Coach Lens orchestrator: at most one hint at a time, two tiers, rate-limited.

Single agent, not a crew: one model call per strategy hint over retrieved
context. A debate between sub-agents while a human is mid-sentence is the wrong
shape at any latency.

Tier-1 (deterministic, checklist): renders <300ms, fires whenever a checkpoint
is unmet — identity, promise quality. Always allowed.

Tier-2 (LLM strategy): only at a detected pause, only if the rate ceiling allows,
only when borrower state is certain enough to branch. Uncertain state gets the
diagnostic question, never a guessed strategy (I7). Every strategy hint carries
its playbook support count (I5). If composition overruns the budget the caller
demotes it to next-turn — the latency measurement lives with the boundary.

Rate ceiling (I11): at most MAX_HINTS_PER_CONVERSATION, and one per boundary.
Conversation outcome beats hint volume; hint spam splits the agent's attention.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import MAX_HINTS_PER_CONVERSATION
from ..llm import LLMEngine, Role, get_engine
from ..schema import BorrowerState, Capacity, Hint, Promise, Willingness
from .checklist import checklist_hint
from .playbook import Strategy, retrieve


@dataclass
class CoachContext:
    state: BorrowerState
    transcript_so_far: str
    promise: Promise | None = None
    objection: str | None = None
    at_pause: bool = False
    hints_shown: int = 0


_COMPOSE_SYSTEM = (
    "You are a real-time coaching aid for a collections agent. Turn the given "
    "strategy into ONE short, specific hint the agent can act on in the next "
    "sentence. Under 20 words. No preamble, no quotes. Just the hint."
)


def _diagnostic_hint() -> Hint:
    return Hint(
        text="You don't yet know if they can't pay or won't — ask one question that "
             "tells them apart before proposing anything.",
        is_deterministic=True,
    )


def _compose_strategy(strategy: Strategy, ctx: CoachContext,
                      engine: LLMEngine) -> Hint:
    prompt = (
        f"Strategy: {strategy.text}\n"
        f"Recent conversation:\n{ctx.transcript_so_far[-600:]}\n\n"
        f"Write the one-line hint."
    )
    text = engine.complete(Role.COACH, prompt, system=_COMPOSE_SYSTEM, max_tokens=60).strip()
    label = "" if not strategy.is_provisional else " (seeded, not yet outcome-backed)"
    return Hint(text=text + label, is_deterministic=False,
                support_count=strategy.support_count)


def coach_turn(ctx: CoachContext, engine: LLMEngine | None = None) -> Hint | None:
    """Produce at most one hint for this turn, or None."""
    if ctx.hints_shown >= MAX_HINTS_PER_CONVERSATION:  # I11
        return None

    # Tier-1: deterministic, always allowed, renders inside budget.
    h = checklist_hint(ctx.transcript_so_far, ctx.promise)
    if h is not None:
        return h

    # Tier-2: only at a pause.
    if not ctx.at_pause:
        return None

    # Uncertain state -> ask, never guess (I7).
    if not ctx.state.is_certain:
        return _diagnostic_hint()

    quadrant = (ctx.state.capacity, ctx.state.willingness)
    strategy = retrieve(quadrant, ctx.objection)
    if strategy is None:
        return None
    engine = engine or get_engine()
    return _compose_strategy(strategy, ctx, engine)
