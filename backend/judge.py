"""Judges — accuracy (DeepEval GEval + AnswerRelevancy) and consistency (drift).

Both run in this process. Sandbox isolation was tried but Nosana's ingress
blocks Daytona's egress at TLS handshake, so DeepEval's judge calls couldn't
reach the endpoint from inside a sandbox. Backend-side scoring is what
actually works with the endpoint we've been given.

- Accuracy: DeepEval GEval (custom rubric) — 0..1, drives pass/fail at 0.7.
- Relevancy: DeepEval AnswerRelevancy — 0..1, informational.
- Consistency: cluster N responses by semantic equivalence, drift = 1 - largest/N.

DeepEval doesn't ship a built-in cross-run consistency metric; the clustering
logic here is ours. That gap is the novelty story for the pitch.

All calls hit the Nosana-hosted OpenAI-compatible endpoint via the openai
SDK (which reads OPENAI_BASE_URL + OPENAI_API_KEY from env, mirrored from the
NOSANA_* vars in backend/server.py at startup).
"""
from __future__ import annotations

import json
import os

from openai import OpenAI


def score_tile(question: str, expected: str, actual: str) -> tuple[float, float, str]:
    """DeepEval — accuracy (GEval custom rubric) + answer relevancy.

    Returns (accuracy_score, relevancy_score, combined_reason).
    """
    from deepeval.metrics import AnswerRelevancyMetric, GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    model = os.environ.get("NOSANA_MODEL", "llama-3.1-70b-instruct")

    accuracy_criteria = (
        "Determine whether the 'actual output' answers the question in a way that is "
        "semantically equivalent to the 'expected output'. Different wording is fine. "
        "Missing key facts, wrong facts, or contradictions with expected output are not fine. "
        "For questions with ranges or multiple acceptable answers, the expected output states "
        "the acceptable range — score high if the actual output falls within it."
    )
    accuracy = GEval(
        name="accuracy",
        criteria=accuracy_criteria,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        model=model,
    )
    relevancy = AnswerRelevancyMetric(model=model, threshold=0.7)

    tc = LLMTestCase(input=question, expected_output=expected, actual_output=actual)
    accuracy.measure(tc)
    relevancy.measure(tc)

    reason_bits = []
    if accuracy.reason:
        reason_bits.append(f"acc: {accuracy.reason}")
    if relevancy.reason:
        reason_bits.append(f"rel: {relevancy.reason}")
    return float(accuracy.score), float(relevancy.score), " | ".join(reason_bits)


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
    # No max_tokens — reasoning models (e.g. glm-4.7-flash) burn budget on
    # the internal "reasoning" field before writing content, so a cap here
    # returns empty content with finish_reason=length.
    r = client.chat.completions.create(
        model=model,
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
