"""Sample agent 2: accurate-ish but INCONSISTENT.

Same Nosana model as agent_accurate, but temperature 1 + prompt encouraging
variation. Purpose: reliably show cross-run drift so the consistency metric
has something to catch during the demo.

Dev 3 owns this file — tune SYSTEM until Q3 (islands) drifts across 3 runs.
"""
from __future__ import annotations

from agents._call import chat


NAME = "Singapore Trivia Agent (drifty)"
DESCRIPTION = "Answers about Singapore, but each phrasing may vary."
SYSTEM = (
    "You are answering trivia about Singapore. "
    "You are casual — vary your wording, sentence structure, and level of detail "
    "each time you answer, even for the same question. "
    "For numeric answers, sometimes give the exact figure, sometimes round, "
    "sometimes give an approximate range. Be helpful but never boringly repetitive. "
    "Keep responses under two sentences."
)


def responder(question: str) -> str:
    return chat(SYSTEM, question, temperature=1.0)
