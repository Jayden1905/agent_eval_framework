"""Sample agent 2: accurate-ish but INCONSISTENT.

Same domain as agent_accurate, but temperature 1 + prompt encouraging variation.
Purpose: reliably show cross-run drift so the consistency metric has something
to catch during the demo.

Dev 3 owns this file — tune SYSTEM until Q3 (islands) drifts across 3 runs.
"""
from __future__ import annotations


NAME = "Singapore Trivia Agent (drifty)"
DESCRIPTION = "Answers about Singapore, but each phrasing may vary."
MODEL = "claude-haiku-4-5-20251001"
SYSTEM = (
    "You are answering trivia about Singapore. "
    "You are casual — vary your wording, sentence structure, and level of detail "
    "each time you answer, even for the same question. "
    "For numeric answers, sometimes give the exact figure, sometimes round, "
    "sometimes give an approximate range. Be helpful but never boringly repetitive. "
    "Keep responses under two sentences."
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
        temperature=1.0,
        system=SYSTEM,
        messages=[{"role": "user", "content": question}],
    )
    return r.content[0].text.strip()
