"""Sample agent 3: confidently WRONG.

Deterministic but slots in plausible-sounding wrong facts. Purpose: reliably
tank accuracy in the demo so the scorecard shows a red 1/5 or 2/5.

Dev 3 owns this file.
"""
from __future__ import annotations

import os


NAME = "Singapore Trivia Agent (wrong)"
DESCRIPTION = "Answers about Singapore, but often confidently incorrect."
SYSTEM = (
    "You are answering trivia about Singapore. "
    "You always answer confidently and definitively, in one or two sentences. "
    "However, you are not always correct: for years, dates, counts, and named people, "
    "you sometimes substitute a plausible-sounding but incorrect value. "
    "Never say you are uncertain. Never refuse. Always give a specific-sounding answer."
)

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI()
    return _client


def responder(question: str) -> str:
    model = os.environ.get("NOSANA_MODEL", "llama-3.1-70b-instruct")
    r = _get_client().chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": question},
        ],
    )
    return (r.choices[0].message.content or "").strip()
