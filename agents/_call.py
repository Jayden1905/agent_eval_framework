"""Shared Nosana call helper for the demo agents.

Guardrails:
- Retry once if content comes back empty. Reasoning models (glm-4.7-flash)
  occasionally emit all-reasoning-no-content responses; a fresh call at the
  same temperature usually succeeds.
- If still empty, fall back to the reasoning field's last sentence — better
  than returning empty and making DeepEval refuse to score the tile.
- Always return a non-empty string (or raise, so the sandbox marks the tile
  error explicitly instead of showing a silent 0.00).
"""
from __future__ import annotations

import os


_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI()
    return _client


def chat(system: str, user: str, temperature: float) -> str:
    """Call the Nosana OpenAI-compat endpoint. Returns non-empty content or raises."""
    model = os.environ.get("NOSANA_MODEL", "llama-3.1-70b-instruct")
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    for attempt in range(2):
        r = _get_client().chat.completions.create(
            model=model,
            temperature=temperature,
            messages=messages,
        )
        content = (r.choices[0].message.content or "").strip()
        if content:
            return content

    # Both attempts came back empty. Try to salvage from the reasoning field
    # (glm-style reasoning models put draft answers there).
    reasoning = getattr(r.choices[0].message, "reasoning", None) or ""
    if reasoning:
        # last non-empty line is usually the model's final draft answer
        for line in reversed(reasoning.strip().splitlines()):
            line = line.strip()
            if line and not line.startswith("#") and not line[0].isdigit():
                return line

    raise RuntimeError("model returned empty content (both attempts)")
