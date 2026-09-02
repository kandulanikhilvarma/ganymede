"""LLM access behind one interface, so the backend is a swap not a rewrite.

Mirrors the ASREngine move: nothing in the codebase names a provider. Components
ask for a ROLE — extract, generate, judge, coach — and the engine routes each to
a model chosen for that role's cost/quality trade-off. Change the routing table,
not the callers.

Default backend is OpenRouter (OpenAI-compatible), which reaches Anthropic,
OpenAI, Google, DeepSeek and ~400 others through one key. Swapping to the native
Anthropic SDK later means implementing one class, not touching Coach Lens.

Roles and why each model:
  extract  — high volume, structural, cheap. DeepSeek v3.1.
  generate — synthetic conversations, cheap and fluent. Gemini Flash Lite.
  judge    — the reliability ceiling depends on this. Claude Sonnet 5.
  coach    — hint composition, quality matters, latency matters. Claude Sonnet 5.

Prompt caching (the plan's token-discipline lever) is provider-specific and not
wired here yet — correctness first, cost optimisation once the paths exist.
"""

from __future__ import annotations

import os
from enum import Enum

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


class Role(str, Enum):
    EXTRACT = "extract"
    GENERATE = "generate"
    JUDGE = "judge"
    COACH = "coach"


# Role -> model. The one table to edit when trading cost against quality.
OPENROUTER_MODELS: dict[Role, str] = {
    Role.EXTRACT: "deepseek/deepseek-chat-v3.1",
    Role.GENERATE: "google/gemini-2.5-flash-lite",
    Role.JUDGE: "anthropic/claude-sonnet-5",
    Role.COACH: "anthropic/claude-sonnet-5",
}


class LLMEngine:
    """One method: complete(role, prompt). Deterministic by default (temp 0) —
    a judge that wanders is a judge you cannot calibrate."""

    def complete(self, role: Role, prompt: str, *, system: str | None = None,
                 temperature: float = 0.0, max_tokens: int = 1024) -> str:
        raise NotImplementedError


class OpenRouterEngine(LLMEngine):
    def __init__(self, models: dict[Role, str] | None = None):
        from openai import OpenAI

        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY not set (check .env)")
        self._client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
        self._models = models or OPENROUTER_MODELS

    def complete(self, role: Role, prompt: str, *, system: str | None = None,
                 temperature: float = 0.0, max_tokens: int = 1024) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self._client.chat.completions.create(
            model=self._models[role],
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""


def get_engine() -> LLMEngine:
    """Factory. Reads GANYMEDE_LLM_BACKEND; defaults to openrouter."""
    backend = os.environ.get("GANYMEDE_LLM_BACKEND", "openrouter")
    if backend == "openrouter":
        return OpenRouterEngine()
    raise ValueError(f"unknown LLM backend: {backend}")
