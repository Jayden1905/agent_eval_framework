"""Public API for the eval platform. Frontend (hack.py) imports from here.

Dev 1: code against these signatures via platform.mocks during Phase 1.
Dev 2: fill in the TODOs. Don't change the signatures without pinging Dev 1.

Return shapes are the contract. Read them carefully.
"""
from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path
from typing import TypedDict

from backend import a2a_client, judge, sandbox


class AgentCard(TypedDict, total=False):
    """Whatever we discover at {url}/.well-known/agent-card.json.

    Passthrough dict — no schema validation. Frontend renders `name`,
    `description`, and `skills[*].name` (rest is optional).
    """
    name: str
    description: str
    skills: list[dict]


class Tile(TypedDict):
    q_idx: int
    run_idx: int
    status: str       # "pending" | "running" | "pass" | "fail" | "error"
    answer: str
    score: float      # DeepEval GEval accuracy (0..1) — drives pass/fail at 0.7
    relevancy: float  # DeepEval AnswerRelevancy (0..1) — informational


class Scorecard(TypedDict):
    accuracy: str
    accuracy_pct: float
    consistency_drift: float
    relevancy_pct: float
    per_question: list[dict]


class EvalStatus(TypedDict):
    tiles: list[Tile]
    scorecard: Scorecard | None


_STATE: dict[str, EvalStatus] = {}
_LOCK = threading.Lock()

_WORKER_SRC_PATH = Path(__file__).parent / "sandbox_worker.py"


def discover_agent(url: str) -> AgentCard:
    return a2a_client.discover(url)


def start_eval(agent_url: str, test_set: list[dict], runs_per_q: int = 3) -> str:
    eval_id = uuid.uuid4().hex[:8]

    # seed pending tiles so the UI shows the full grid immediately
    tiles: list[Tile] = []
    for q_idx, _ in enumerate(test_set):
        for run_idx in range(runs_per_q):
            tiles.append({
                "q_idx": q_idx,
                "run_idx": run_idx,
                "status": "pending",
                "answer": "",
                "score": 0.0,
                "relevancy": 0.0,
            })

    with _LOCK:
        _STATE[eval_id] = {"tiles": tiles, "scorecard": None}

    t = threading.Thread(
        target=_run_eval,
        args=(eval_id, agent_url, test_set, runs_per_q),
        daemon=True,
    )
    t.start()
    return eval_id


def get_eval_status(eval_id: str) -> EvalStatus:
    with _LOCK:
        # return a shallow copy so callers can't accidentally mutate
        s = _STATE.get(eval_id)
        if s is None:
            return {"tiles": [], "scorecard": None}
        return {"tiles": list(s["tiles"]), "scorecard": s["scorecard"]}


def _run_eval(eval_id: str, agent_url: str, test_set: list[dict], runs_per_q: int) -> None:
    """Background thread: fan out sandboxes, then aggregate."""
    worker_source = _WORKER_SRC_PATH.read_text()

    tasks = []
    for q_idx, item in enumerate(test_set):
        for run_idx in range(runs_per_q):
            tasks.append({
                "q_idx": q_idx,
                "run_idx": run_idx,
                "question": item["question"],
                "expected": item["expected"],
                "agent_url": agent_url,
            })

    def _on_tile_done(result: dict) -> None:
        with _LOCK:
            tiles = _STATE[eval_id]["tiles"]
            for tile in tiles:
                if tile["q_idx"] == result["q_idx"] and tile["run_idx"] == result["run_idx"]:
                    tile["answer"] = result.get("answer", "")
                    tile["score"] = float(result.get("score", 0.0))
                    tile["relevancy"] = float(result.get("relevancy", 0.0))
                    if result.get("error"):
                        tile["status"] = "error"
                    else:
                        tile["status"] = "pass" if tile["score"] >= 0.7 else "fail"
                    break

    # mark first N as running so UI shows activity
    with _LOCK:
        for tile in _STATE[eval_id]["tiles"][: min(len(tasks), 15)]:
            tile["status"] = "running"

    try:
        completed = sandbox.fan_out(
            tasks,
            worker_source=worker_source,
            max_workers=15,
            on_tile_done=_on_tile_done,
        )
    except Exception as e:
        # mark everything error and bail
        with _LOCK:
            for tile in _STATE[eval_id]["tiles"]:
                if tile["status"] in ("pending", "running"):
                    tile["status"] = "error"
                    tile["answer"] = f"orchestrator error: {e}"
        _finalize_scorecard(eval_id, test_set)
        return

    _finalize_scorecard(eval_id, test_set)


def _finalize_scorecard(eval_id: str, test_set: list[dict]) -> None:
    """Compute per-question accuracy + consistency drift, roll up."""
    with _LOCK:
        tiles = list(_STATE[eval_id]["tiles"])

    per_q = []
    for q_idx, item in enumerate(test_set):
        q_tiles = [t for t in tiles if t["q_idx"] == q_idx and t["status"] != "error"]
        if not q_tiles:
            per_q.append({"q_idx": q_idx, "acc": 0.0, "rel": 0.0, "drift": 0.0, "reason": "all runs errored"})
            continue
        acc = sum(t["score"] for t in q_tiles) / len(q_tiles)
        rel = sum(t["relevancy"] for t in q_tiles) / len(q_tiles)
        responses = [t["answer"] for t in q_tiles if t["answer"]]
        if len(responses) >= 2:
            c = judge.score_consistency(item["question"], responses)
            per_q.append({"q_idx": q_idx, "acc": acc, "rel": rel, "drift": c["drift"], "reason": c["reason"]})
        else:
            per_q.append({"q_idx": q_idx, "acc": acc, "rel": rel, "drift": 0.0, "reason": "not enough runs"})

    n = len(test_set)
    passed = sum(1 for q in per_q if q["acc"] >= 0.7)
    avg_drift = sum(q["drift"] for q in per_q) / max(1, n)
    avg_rel = sum(q["rel"] for q in per_q) / max(1, n)

    with _LOCK:
        _STATE[eval_id]["scorecard"] = {
            "accuracy": f"{passed}/{n}",
            "accuracy_pct": passed / max(1, n),
            "consistency_drift": avg_drift,
            "relevancy_pct": avg_rel,
            "per_question": per_q,
        }
