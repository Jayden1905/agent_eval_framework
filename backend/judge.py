"""Judges — accuracy runs inside the sandbox (see backend/sandbox_worker.py);
consistency runs here in the orchestrator once all runs of a question land.

- Accuracy: DeepEval GEval + AnswerRelevancy (per-run, inside sandbox).
- Consistency: cluster N responses by semantic equivalence, drift = 1 - largest/N.

DeepEval doesn't ship a built-in cross-run consistency metric; the clustering
logic here is ours. That gap is the novelty story for the pitch.

Both sides talk to the Nosana-hosted OpenAI-compatible endpoint via the openai
SDK (which reads OPENAI_BASE_URL + OPENAI_API_KEY from env, mirrored from the
NOSANA_* vars in backend/server.py at startup).
"""
from __future__ import annotations

import json
import os

from openai import OpenAI


def score_consistency(question: str, responses: list[str]) -> dict:
    """Cluster responses by semantic equivalence, compute drift.

    drift = 1 - (largest_cluster_size / N)
      3 identical → 0.00
      2+1 split  → 0.33
      3 different → 0.67
    """
    if len(responses) < 2:
        return {"drift": 0.0, "clusters": [[0]], "reason": "single response"}

    numbered = "\n".join(f"[{i+1}] {r}" for i, r in enumerate(responses))
    prompt = f"""You are evaluating whether these responses to the same question convey the same meaning.

Question: {question}

Responses:
{numbered}

Group response indices (1-based) by semantic equivalence. Two responses are equivalent if they would satisfy the asker equally well — different wording is fine, different facts or positions is not.

Return JSON only, no prose:
{{"clusters": [[1,2],[3]], "reason": "<one sentence>"}}"""

    model = os.environ.get("NOSANA_MODEL", "llama-3.1-70b-instruct")
    client = OpenAI()
    r = client.chat.completions.create(
        model=model,
        max_tokens=300,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    parsed = _extract_json(r.choices[0].message.content or "")
    clusters = parsed.get("clusters", [[i + 1] for i in range(len(responses))])
    reason = parsed.get("reason", "")
    drift = compute_drift(clusters, len(responses))
    return {"drift": drift, "clusters": clusters, "reason": reason}


def compute_drift(clusters: list[list[int]], n: int) -> float:
    if n <= 1:
        return 0.0
    largest = max((len(c) for c in clusters), default=1)
    return 1.0 - (largest / n)


def _extract_json(text: str) -> dict:
    """Grab the first {...} block from a model response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[1] if "\n" in text else text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON in response: {text[:200]}")
    return json.loads(text[start : end + 1])


if __name__ == "__main__":
    assert compute_drift([[1, 2, 3]], 3) == 0.0
    assert abs(compute_drift([[1, 2], [3]], 3) - 1 / 3) < 1e-9
    assert abs(compute_drift([[1], [2], [3]], 3) - 2 / 3) < 1e-9
    print("drift math ok")
