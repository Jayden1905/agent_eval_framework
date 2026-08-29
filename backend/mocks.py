"""Fake data with the exact shape from backend/eval.py.

Dev 1 imports from here to iterate on the UI without waiting for Dev 2.
Once Dev 2's real impl is stable, swap: `from backend import eval as api` → done.

Delete this file at end of Phase 3.
"""
from __future__ import annotations

import time
import random

# NOTE: intentionally does NOT import from backend.eval — Dev 1 must be able to
# iterate on the UI before Dev 2 has anthropic/daytona/deepeval installed.
# Shapes here mirror backend/eval.py's TypedDicts. Keep them in sync.


_START_TIMES: dict[str, float] = {}


def discover_agent(url: str) -> dict:
    return {
        "name": "Singapore Trivia Agent (mock)",
        "description": "Answers questions about Singapore. Mock data — Dev 2 will land real discovery.",
        "skills": [
            {"name": "trivia", "description": "General Singapore knowledge"},
        ],
    }


def start_eval(agent_url: str, test_set: list[dict], runs_per_q: int = 3) -> str:
    eval_id = f"mock-{int(time.time())}"
    _START_TIMES[eval_id] = time.time()
    return eval_id


def get_eval_status(eval_id: str) -> dict:
    """Simulates a run that takes ~15s and gradually fills tiles."""
    n_questions = 5
    runs_per_q = 3
    total_tiles = n_questions * runs_per_q

    elapsed = time.time() - _START_TIMES.get(eval_id, time.time())
    n_done = min(total_tiles, int(elapsed * 1.5))  # ~1.5 tiles/second

    tiles: list[dict] = []
    for q_idx in range(n_questions):
        for run_idx in range(runs_per_q):
            idx = q_idx * runs_per_q + run_idx
            if idx >= n_done:
                tiles.append({
                    "q_idx": q_idx,
                    "run_idx": run_idx,
                    "status": "running" if idx == n_done else "pending",
                    "answer": "",
                    "score": 0.0,
                })
            else:
                # deterministic fake: q_idx 2 (islands) shows drift on run_idx 0
                if q_idx == 2 and run_idx == 0:
                    ans = "Around 63 islands."
                elif q_idx == 2 and run_idx == 1:
                    ans = "Approximately 60 islands total."
                elif q_idx == 2 and run_idx == 2:
                    ans = "Over 60 small islands plus the main one."
                else:
                    ans = f"[mock answer to Q{q_idx+1}, run {run_idx+1}]"
                score = random.uniform(0.85, 1.0)
                tiles.append({
                    "q_idx": q_idx,
                    "run_idx": run_idx,
                    "status": "pass" if score > 0.7 else "fail",
                    "answer": ans,
                    "score": score,
                })

    scorecard: dict | None = None
    if n_done >= total_tiles:
        scorecard = {
            "accuracy": "5/5",
            "accuracy_pct": 0.95,
            "consistency_drift": 0.33,
            "per_question": [
                {"q_idx": 0, "acc": 1.0, "drift": 0.0, "reason": "consistent"},
                {"q_idx": 1, "acc": 1.0, "drift": 0.0, "reason": "consistent"},
                {"q_idx": 2, "acc": 0.9, "drift": 0.67, "reason": "3 different answers on island count"},
                {"q_idx": 3, "acc": 1.0, "drift": 0.0, "reason": "consistent"},
                {"q_idx": 4, "acc": 1.0, "drift": 0.0, "reason": "consistent"},
            ],
        }

    return {"tiles": tiles, "scorecard": scorecard}
