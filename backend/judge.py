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

    Retries each metric independently (reasoning-model judges occasionally
    return malformed JSON and DeepEval bubbles that up as a bare exception).
    If a metric fails all retries, we fall back to score=0 for that metric
    only, so a flaky relevancy call doesn't nuke a valid accuracy score.

    Returns (accuracy_score, relevancy_score, combined_reason).
    """
    from deepeval.metrics import AnswerRelevancyMetric, GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    from backend.nosana_judge import NosanaJudge

    model_name = os.environ.get("NOSANA_MODEL", "llama-3.1-70b-instruct")
    # Wrap in NosanaJudge so DeepEval forces response_format=json_object at
    # the API level — the reasoning model won't produce malformed JSON.
    model = NosanaJudge(model=model_name)

    accuracy_criteria = (
        "Determine whether the 'actual output' answers the question in a way that is "
        "semantically equivalent to the 'expected output'. Different wording is fine. "
        "Missing key facts, wrong facts, or contradictions with expected output are not fine. "
        "For questions with ranges or multiple acceptable answers, the expected output states "
        "the acceptable range — score high if the actual output falls within it."
    )

    def _build_accuracy():
        return GEval(
            name="accuracy",
            criteria=accuracy_criteria,
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
            ],
            model=model,
            async_mode=False,
        )

    def _build_relevancy():
        return AnswerRelevancyMetric(model=model, threshold=0.7, async_mode=False)

    tc = LLMTestCase(input=question, expected_output=expected, actual_output=actual)

    acc_score, acc_reason = _measure_with_retry("accuracy", _build_accuracy, tc)
    rel_score, rel_reason = _measure_with_retry("relevancy", _build_relevancy, tc)

    reason_bits = []
    if acc_reason:
        reason_bits.append(f"acc: {acc_reason}")
    if rel_reason:
        reason_bits.append(f"rel: {rel_reason}")
    return acc_score, rel_score, " | ".join(reason_bits)


def _measure_with_retry(label: str, build, tc, attempts: int = 3) -> tuple[float, str]:
    """Run a DeepEval metric with retries. Fresh metric per attempt (some
    internal state gets sticky on failure). Returns (score, reason)."""
    last_err = ""
    for i in range(1, attempts + 1):
        try:
            metric = build()
            metric.measure(tc)
            score = float(metric.score) if metric.score is not None else 0.0
            reason = metric.reason or ""
            return score, reason
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
    return 0.0, f"{label} judge failed after {attempts} attempts ({last_err})"


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
    # response_format=json_object — the endpoint enforces valid JSON output,
    # dodging the reasoning-model's tendency to mix prose with JSON.
    r = client.chat.completions.create(
        model=model,
        temperature=0.0,
        response_format={"type": "json_object"},
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
