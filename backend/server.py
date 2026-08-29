"""FastAPI HTTP layer — eval platform + demo agents in ONE process.

Frontend (Next.js on :3000) hits these endpoints. In-process state lives in
backend/eval.py's module-level dict — run with one uvicorn worker.

Runs:
  Real (Dev 2, agents mounted, needs anthropic + daytona + deepeval):
    uvicorn backend.server:app --reload --port 8000

  Mocks (Dev 1 unblocker, no agents mounted, no heavy deps):
    USE_MOCKS=1 uvicorn backend.server:app --reload --port 8000

Endpoints:
  POST /api/discover              body { url } → agent card
  POST /api/eval                  body { agent_url, test_set, runs_per_q } → { eval_id }
  GET  /api/eval/{eval_id}/status → { tiles, scorecard | null }
  GET  /api/health

Mounted agents (real mode only):
  /agents/accurate, /agents/drifty, /agents/wrong
"""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


USE_MOCKS = bool(os.environ.get("USE_MOCKS"))

if USE_MOCKS:
    from backend import mocks as api
else:
    from backend import eval as api


app = FastAPI(title="AgentEval")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class DiscoverBody(BaseModel):
    url: str


class TestCase(BaseModel):
    question: str
    expected: str


class EvalBody(BaseModel):
    agent_url: str
    test_set: list[TestCase]
    runs_per_q: int = 3


@app.post("/api/discover")
def discover(body: DiscoverBody):
    try:
        return api.discover_agent(body.url)
    except Exception as e:
        raise HTTPException(400, f"discovery failed: {e}")


@app.post("/api/eval")
def start_eval(body: EvalBody):
    test_set = [t.model_dump() for t in body.test_set]
    eval_id = api.start_eval(body.agent_url, test_set, runs_per_q=body.runs_per_q)
    return {"eval_id": eval_id}


@app.get("/api/eval/{eval_id}/status")
def eval_status(eval_id: str):
    return api.get_eval_status(eval_id)


@app.get("/api/health")
def health():
    return {"ok": True, "mode": "mocks" if USE_MOCKS else "real"}


# Mount demo agents at /agents/{name} in real mode.
# Skipped in mocks mode so Dev 1 doesn't need anthropic installed.
if not USE_MOCKS:
    from agents import agent_accurate, agent_drifty, agent_wrong
    from agents.a2a_server import mount

    mount(app, "/agents/accurate", agent_accurate.NAME, agent_accurate.DESCRIPTION, agent_accurate.responder)
    mount(app, "/agents/drifty", agent_drifty.NAME, agent_drifty.DESCRIPTION, agent_drifty.responder)
    mount(app, "/agents/wrong", agent_wrong.NAME, agent_wrong.DESCRIPTION, agent_wrong.responder)
