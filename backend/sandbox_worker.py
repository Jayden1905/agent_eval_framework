"""Runs INSIDE a Daytona sandbox — one process per (question, run_idx) tile.

Option E: sandbox owns the untrusted A2A hop only. It calls the user-supplied
agent, writes the answer to /work/result.json. Scoring happens on the backend
after the answer comes back (Nosana is reachable from backend, but blocked
from Daytona egress unless the host is on the sandbox's domain_allow_list).

This file is uploaded verbatim by backend/sandbox.py — it must be self-
contained (no imports from `backend.*`, since the sandbox has no such package).
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
        _write({"answer": answer, "error": None})
        return 0
    except Exception as e:
        _write({
            "answer": "",
            "reason": f"agent call failed: {e}",
            "error": traceback.format_exc(),
        })
        return 1


def _send_a2a(agent_url: str, question: str) -> str:
    """Fetch the card (validation only), then send message/send.

    The RPC URL is derived from `agent_url` — the card's advertised interface
    URL may still say localhost if the agent is behind a reverse proxy /
    tunnel, so the caller's base is authoritative.
    """
    import httpx

    base = agent_url.rstrip("/")
    httpx.get(f"{base}/.well-known/agent-card.json", timeout=10).raise_for_status()
    rpc_url = f"{base}/a2a/jsonrpc/"

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


def _write(data: dict) -> None:
    with open("/work/result.json", "w") as f:
        json.dump(data, f)


if __name__ == "__main__":
    sys.exit(main())
