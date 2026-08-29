"""Judges — accuracy (per-run) and consistency (across-runs).

- Accuracy: DeepEval GEval with a "does actual_output match expected_output" rubric.
- Consistency: DeepEval GEval used pairwise/cluster-style — group N responses by
  semantic equivalence, drift = 1 - (largest_cluster / N).

DeepEval doesn't ship a built-in cross-run consistency metric; the clustering
logic here is ours (see docs guide, `guides-ai-agent-evaluation`). That gap is
the novelty story for the pitch.
"""
from __future__ import annotations

import json
import os

from anthropic import Anthropic

# DeepEval is used for accuracy; we route it through GEval so the criteria are
# explicit and tunable. If DeepEval refuses to init in the sandbox for any
# reason, `_geval_accuracy_fallback` gives us a hand-rolled equivalent.
try:
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    _DEEPEVAL_OK = True
except Exception:
    _DEEPEVAL_OK = False


_ACCURACY_CRITERIA = (
    "Determine whether the 'actual output' answers the question in a way that is "
    "semantically equivalent to the 'expected output'. Different wording is fine. "
    "Missing key facts, wrong facts, or contradictions with expected output are not fine. "
    "For questions with ranges or multiple acceptable answers, the expected output states "
    "the acceptable range — score high if the actual output falls within it."
)


def score_accuracy(question: str, expected: str, actual: str) -> dict:
    """Returns {"score": 0..1, "reason": str}."""
    if _DEEPEVAL_OK:
        metric = GEval(
            name="accuracy",
            criteria=_ACCURACY_CRITERIA,
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
            ],
        )
        tc = LLMTestCase(input=question, expected_output=expected, actual_output=actual)
        metric.measure(tc)
        return {"score": float(metric.score), "reason": metric.reason or ""}
    return _geval_accuracy_fallback(question, expected, actual)


def _geval_accuracy_fallback(question: str, expected: str, actual: str) -> dict:
    """Used only if DeepEval fails to import. Same rubric, direct Claude call."""
    client = Anthropic()
    prompt = f"""{_ACCURACY_CRITERIA}

Question: {question}
Expected output: {expected}
Actual output: {actual}

Return JSON only:
{{"score": <float 0.0-1.0>, "reason": "<one sentence>"}}"""
    r = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    text = r.content[0].text
    return _extract_json(text)


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

    client = Anthropic()
    r = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    parsed = _extract_json(r.content[0].text)
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
    # self-check the drift math (non-trivial → one runnable check per ponytail)
    assert compute_drift([[1, 2, 3]], 3) == 0.0
    assert abs(compute_drift([[1, 2], [3]], 3) - 1 / 3) < 1e-9
    assert abs(compute_drift([[1], [2], [3]], 3) - 2 / 3) < 1e-9
    print("drift math ok")
