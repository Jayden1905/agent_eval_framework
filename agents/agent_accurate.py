"""Sample agent 1: accurate + consistent.

OpenAI-compatible endpoint (Nosana), temperature 0, system prompt geared for
precise repeatable answers. Backed by lazy openai import so backend/server.py
in USE_MOCKS mode never requires the openai SDK to be installed.
"""
from __future__ import annotations

from agents._call import chat


NAME = "Singapore Trivia Agent (accurate)"
DESCRIPTION = "Precise, consistent answers about Singapore history and geography."
SYSTEM = (
    "You are a Singapore trivia expert. Answer questions concisely and precisely. "
    "Give the same phrasing every time — do not vary your wording across identical questions. "
    "If a question has multiple valid answers, pick the most canonical one. "
    "Keep responses under two sentences."
)


def responder(question: str) -> str:
    return chat(SYSTEM, question, temperature=0.0)
