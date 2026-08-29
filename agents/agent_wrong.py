"""Sample agent 3: confidently WRONG.

Deterministic but slots in plausible-sounding wrong facts. Purpose: reliably
tank accuracy in the demo so the scorecard shows a red 1/5 or 2/5.

Dev 3 owns this file.
"""
from __future__ import annotations


NAME = "Singapore Trivia Agent (wrong)"
DESCRIPTION = "Answers about Singapore, but often confidently incorrect."
MODEL = "claude-haiku-4-5-20251001"
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
        from anthropic import Anthropic
        _client = Anthropic()
    return _client


def responder(question: str) -> str:
    r = _get_client().messages.create(
        model=MODEL,
        max_tokens=200,
        temperature=0.0,
        system=SYSTEM,
        messages=[{"role": "user", "content": question}],
    )
    return r.content[0].text.strip()
