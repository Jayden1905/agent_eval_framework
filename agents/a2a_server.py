"""Shared A2A HTTP scaffold — mountable onto a FastAPI/Starlette app.

Two endpoints per agent, wire-compatible with the A2A v1.0 spec:
  GET  {prefix}/.well-known/agent-card.json  — capability advertisement
  POST {prefix}/a2a/jsonrpc/                 — JSON-RPC 2.0, handles method="message/send"

The card's advertised JSON-RPC URL is built from the incoming request's base_url
(scheme + host), so it stays correct behind reverse proxies or on any port.
"""
from __future__ import annotations

import uuid
from typing import Callable

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


Responder = Callable[[str], str]


def _build_card(name: str, description: str, base_url: str, prefix: str, skill_name: str) -> dict:
    return {
        "name": name,
        "description": description,
        "version": "0.1.0",
        "supported_interfaces": [
            {
                "protocol_binding": "JSONRPC",
                "url": f"{base_url.rstrip('/')}{prefix}/a2a/jsonrpc/",
            }
        ],
        "default_input_modes": ["text/plain"],
        "default_output_modes": ["text/plain"],
        "capabilities": {"streaming": False, "extended_agent_card": False},
        "skills": [{"name": skill_name, "description": description}],
    }


def mount(app, prefix: str, name: str, description: str, responder: Responder, skill_name: str = "qa") -> None:
    """Attach agent-card + JSON-RPC routes to `app` under `prefix`.

    Example:
        mount(app, "/agents/accurate", "Accurate Agent", "…", responder_fn)

    Exposes:
        GET  {prefix}/.well-known/agent-card.json
        POST {prefix}/a2a/jsonrpc/
    """
    prefix = "/" + prefix.strip("/")

    async def agent_card(request: Request) -> JSONResponse:
        base = str(request.base_url).rstrip("/")
        return JSONResponse(_build_card(name, description, base, prefix, skill_name))

    async def jsonrpc(request: Request) -> JSONResponse:
        body = await request.json()
        req_id = body.get("id")
        if body.get("method") != "message/send":
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"method not found: {body.get('method')}"},
            })
        try:
            parts = body["params"]["message"]["parts"]
            question = " ".join(p.get("text", "") for p in parts).strip()
            answer = responder(question)
        except Exception as e:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": f"internal: {e}"},
            })
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "role": "ROLE_AGENT",
                "message_id": uuid.uuid4().hex,
                "parts": [{"text": answer}],
            },
        })

    app.router.routes.append(Route(f"{prefix}/.well-known/agent-card.json", agent_card, methods=["GET"]))
    app.router.routes.append(Route(f"{prefix}/a2a/jsonrpc/", jsonrpc, methods=["POST"]))
