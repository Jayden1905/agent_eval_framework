"""Runs INSIDE a Daytona sandbox — one process per (question, run_idx) tile.

Reads /work/config.json (question, expected, answer — answer is pre-fetched
by the backend), scores accuracy + relevancy with DeepEval, writes
/work/result.json. The DeepEval judge points at the Nosana-hosted OpenAI-
compatible endpoint via env vars.

Env forwarded by backend/sandbox.py: OPENAI_BASE_URL, OPENAI_API_KEY,
NOSANA_MODEL. The openai SDK (and DeepEval's default judge) both read
OPENAI_BASE_URL / OPENAI_API_KEY automatically.

This file is uploaded verbatim by backend/sandbox.py — it must be self-
contained (no imports from `backend.*`, since the sandbox has no such package).
"""
from __future__ import annotations

import json
import os
import sys
import traceback


def main() -> int:
    try:
        with open("/work/config.json") as f:
            cfg = json.load(f)

        answer = cfg["answer"]
        acc, rel, reason = _score(cfg["question"], cfg["expected"], answer)

        _write({
            "answer": answer,
            "score": acc,
            "relevancy": rel,
            "reason": reason,
            "error": None,
        })
        return 0
    except Exception as e:
        _write({
            "answer": "",
            "score": 0.0,
            "relevancy": 0.0,
            "reason": f"worker crashed: {e}",
            "error": traceback.format_exc(),
        })
        return 1


def _score(question: str, expected: str, actual: str) -> tuple[float, float, str]:
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


def _write(data: dict) -> None:
    with open("/work/result.json", "w") as f:
        json.dump(data, f)


if __name__ == "__main__":
    sys.exit(main())
