"""Sample agent 3: confidently WRONG.

Deterministic but slots in plausible-sounding wrong facts. Purpose: reliably
tank accuracy in the demo so the scorecard shows a red 1/5 or 2/5.

Dev 3 owns this file.
"""
from __future__ import annotations

from agents._call import chat


NAME = "Singapore Trivia Agent (wrong)"
DESCRIPTION = "Answers about Singapore, but often confidently incorrect."
SYSTEM = (
    "You are answering trivia about Singapore. "
    "You always answer confidently and definitively, in one or two sentences. "
    "However, you are not always correct: for years, dates, counts, and named people, "
    "you sometimes substitute a plausible-sounding but incorrect value. "
    "Never say you are uncertain. Never refuse. Always give a specific-sounding answer."
)


def responder(question: str) -> str:
    return chat(SYSTEM, question, temperature=0.0)
