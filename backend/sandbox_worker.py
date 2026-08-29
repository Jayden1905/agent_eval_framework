"""Runs INSIDE a Daytona sandbox — one process per (question, run_idx) tile.

Reads /work/config.json, calls the user's agent via A2A, scores accuracy with
DeepEval, writes /work/result.json.

This file is uploaded verbatim by platform/sandbox.py — it must be self-contained
(no imports from `platform.*`, since the sandbox doesn't have that package).
"""
from __future__ import annotations

import json
import sys
import traceback
import uuid


def main() -> int:
    try:
        with open("/work/config.json") as f:
            cfg = json.load(f)

        answer = _send_a2a(cfg["agent_url"], cfg["question"])
        score, reason = _score(cfg["question"], cfg["expected"], answer)

        _write({
            "answer": answer,
            "score": score,
            "reason": reason,
            "error": None,
        })
        return 0
    except Exception as e:
        _write({
            "answer": "",
            "score": 0.0,
            "reason": f"worker crashed: {e}",
            "error": traceback.format_exc(),
        })
        return 1


def _send_a2a(agent_url: str, question: str) -> str:
    """Discover agent card + send message/send. See platform/a2a_client.py for parity."""
    import httpx

    base = agent_url.rstrip("/")
    card = httpx.get(f"{base}/.well-known/agent-card.json", timeout=10).json()

    rpc_url = f"{base}/a2a/jsonrpc/"
    for iface in card.get("supported_interfaces", []):
        if iface.get("protocol_binding") == "JSONRPC":
            rpc_url = iface["url"]
            break

    payload = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "message/send",
        "params": {
            "message": {
                "role": "ROLE_USER",
                "message_id": uuid.uuid4().hex,
                "parts": [{"text": question}],
            },
        },
    }
    r = httpx.post(rpc_url, json=payload, timeout=60)
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(f"A2A error: {body['error']}")
    parts = body["result"]["parts"]
    return " ".join(p.get("text", "") for p in parts).strip()


def _score(question: str, expected: str, actual: str) -> tuple[float, str]:
    """DeepEval GEval — accuracy rubric."""
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    criteria = (
        "Determine whether the 'actual output' answers the question in a way that is "
        "semantically equivalent to the 'expected output'. Different wording is fine. "
        "Missing key facts, wrong facts, or contradictions with expected output are not fine. "
        "For questions with ranges or multiple acceptable answers, the expected output states "
        "the acceptable range — score high if the actual output falls within it."
    )
    metric = GEval(
        name="accuracy",
        criteria=criteria,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
    )
    tc = LLMTestCase(input=question, expected_output=expected, actual_output=actual)
    metric.measure(tc)
    return float(metric.score), (metric.reason or "")


def _write(data: dict) -> None:
    with open("/work/result.json", "w") as f:
        json.dump(data, f)


if __name__ == "__main__":
    sys.exit(main())
