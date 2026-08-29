"""Thin A2A client — discovery + message/send.

We speak the A2A wire format directly (JSON-RPC 2.0) rather than depending on
`a2a-sdk`. Reason: the SDK is production-grade infra (AgentExecutor, TaskUpdater,
gRPC, streaming) — over-eaten for a 5-hour build with 3 localhost agents.

If the pitch ever needs to name-check the spec: we serve agent cards at
`/.well-known/agent-card.json` in v1.0 shape and implement `message/send`.
"""
from __future__ import annotations

import uuid
import httpx


def discover(url: str, timeout: float = 5.0) -> dict:
    """GET {url}/.well-known/agent-card.json and return parsed JSON."""
    base = url.rstrip("/")
    r = httpx.get(f"{base}/.well-known/agent-card.json", timeout=timeout)
    r.raise_for_status()
    return r.json()


def _rpc_url_from_card(card: dict, fallback_base: str) -> str:
    """Find the JSON-RPC endpoint from an agent card (v1.0 shape).

    Falls back to `{base}/a2a/jsonrpc/` if the card doesn't advertise one.
    """
    for iface in card.get("supported_interfaces", []):
        if iface.get("protocol_binding") == "JSONRPC":
            return iface["url"]
    return f"{fallback_base.rstrip('/')}/a2a/jsonrpc/"


def send_message(agent_url: str, text: str, timeout: float = 30.0) -> str:
    """Send `text` to the agent via A2A message/send. Returns the agent's reply text.

    Discovers the JSON-RPC endpoint from the agent card on each call.
    Fine for demo scale (5 questions × 3 runs = 15 calls per eval).
    """
    card = discover(agent_url)
    rpc_url = _rpc_url_from_card(card, agent_url)

    payload = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "message/send",
        "params": {
            "message": {
                "role": "ROLE_USER",
                "message_id": uuid.uuid4().hex,
                "parts": [{"text": text}],
            },
        },
    }
    r = httpx.post(rpc_url, json=payload, timeout=timeout)
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(f"A2A error: {body['error']}")

    parts = body["result"]["parts"]
    return " ".join(p.get("text", "") for p in parts).strip()


if __name__ == "__main__":
    # smoke test — run one of the sample agents first (agents/agent_accurate.py)
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001"
    print("Discovering:", url)
    card = discover(url)
    print("  name:", card.get("name"))
    print("  skills:", [s.get("name") for s in card.get("skills", [])])
    print()
    print("Sending: 'What year did Singapore gain independence?'")
    reply = send_message(url, "What year did Singapore gain independence?")
    print("Reply:", reply)
