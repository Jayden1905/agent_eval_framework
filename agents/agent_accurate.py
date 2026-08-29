"""Sample agent 1: accurate + consistent.

OpenAI-compatible endpoint (Nosana), temperature 0, system prompt geared for
precise repeatable answers. Backed by lazy openai import so backend/server.py
in USE_MOCKS mode never requires the openai SDK to be installed.
"""
from __future__ import annotations

import os


NAME = "Singapore Trivia Agent (accurate)"
DESCRIPTION = "Precise, consistent answers about Singapore history and geography."
SYSTEM = (
    "You are a Singapore trivia expert. Answer questions concisely and precisely. "
    "Give the same phrasing every time — do not vary your wording across identical questions. "
    "If a question has multiple valid answers, pick the most canonical one. "
    "Keep responses under two sentences."
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
        max_tokens=200,
        temperature=0.0,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": question},
        ],
    )
    return (r.choices[0].message.content or "").strip()
