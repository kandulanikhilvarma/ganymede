"""Promise-to-pay extraction.

This sits inside the label path (I6): the PTP-kept outcome depends on what was
promised, so if extraction is noisy every downstream label carries that noise.
It therefore ships with its own gold set and must clear an accuracy bar before
anything trains on its output — the guard is enforced by test, not trusted.

Extraction returns a Promise with amount, due date, method, and a confidence.
The three specificity fields are exactly what the promise-quality coach pushes
an agent to pin down — a vague "I'll try next week" leaves them null, and that
nullness is the signal.
"""

from __future__ import annotations

import json
from datetime import date

from ..llm import LLMEngine, Role, get_engine
from ..schema import Promise

_SYSTEM = (
    "You extract a promise-to-pay from a debt-collection conversation. "
    "A promise-to-pay is the borrower committing to pay. Extract only what the "
    "borrower actually commits to — never the agent's ask. Resolve relative "
    "dates against the reference date. Respond with strict JSON only."
)

_PROMPT = """Reference date: {ref}

Conversation:
{transcript}

Return JSON with exactly these keys:
  "has_promise": true if the borrower commits to pay, else false
  "amount": number in EUR, or null if not stated
  "due": ISO date YYYY-MM-DD the borrower will pay by, or null if not stated
  "method": one of "bank_transfer","card","direct_debit","cash", or null
  "confidence": 0..1, your confidence a real promise was made

A vague intention ("I'll try", "maybe next week", "I'll sort it") is has_promise
true but with null fields it did not specify. A refusal or no commitment is
has_promise false. JSON only, no prose."""


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])


def extract_promise(
    transcript: str,
    borrower_id: str = "unknown",
    ref: date | None = None,
    engine: LLMEngine | None = None,
) -> Promise | None:
    engine = engine or get_engine()
    ref = ref or date.today()
    out = engine.complete(
        Role.EXTRACT,
        _PROMPT.format(ref=ref.isoformat(), transcript=transcript),
        system=_SYSTEM,
        max_tokens=200,
    )
    d = _parse_json(out)
    if not d.get("has_promise"):
        return None
    due = None
    if d.get("due"):
        try:
            due = date.fromisoformat(d["due"])
        except (ValueError, TypeError):
            due = None
    return Promise(
        borrower_id=borrower_id,
        amount=d.get("amount"),
        due=due,
        method=d.get("method"),
        extractor_confidence=float(d.get("confidence", 0.5)),
    )
