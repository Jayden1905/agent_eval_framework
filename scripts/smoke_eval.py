"""End-to-end smoke test for the eval platform.

Discovers the accurate agent, kicks off a small eval (2 questions x 2 runs),
polls status every 4s, prints tile progress + final scorecard.

Usage:
  python scripts/smoke_eval.py                     # accurate agent
  AGENT=drifty python scripts/smoke_eval.py        # drifty
  AGENT=wrong   python scripts/smoke_eval.py       # wrong

Requires: `make dev` running on localhost:8000.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request


BASE = os.environ.get("BACKEND", "http://localhost:8000")
AGENT = os.environ.get("AGENT", "accurate")
AGENT_URL = f"{BASE}/agents/{AGENT}"

TEST_SET = [
    {"question": "What year did Singapore gain independence?", "expected": "1965"},
    {"question": "What is the capital of Singapore?", "expected": "Singapore (city-state)"},
]
RUNS_PER_Q = 2


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read())


def main() -> int:
    print(f"backend: {BASE}")
    print(f"agent:   {AGENT_URL}")
    print()

    # 1. Discover
    print("==> discover")
    card = _post("/api/discover", {"url": AGENT_URL})
    print(f"    name:  {card.get('name')}")
    print(f"    skills: {[s.get('name') for s in card.get('skills', [])]}")
    print()

    # 2. Start eval
    print(f"==> start eval  ({len(TEST_SET)} questions x {RUNS_PER_Q} runs = {len(TEST_SET)*RUNS_PER_Q} sandboxes)")
    started = _post("/api/eval", {
        "agent_url": AGENT_URL,
        "test_set": TEST_SET,
        "runs_per_q": RUNS_PER_Q,
    })
    eval_id = started["eval_id"]
    print(f"    eval_id: {eval_id}")
    print()

    # 3. Poll
    print("==> polling (backend fans out agent calls + DeepEval scoring; expect ~15-40s)")
    started_at = time.time()
    last_line = ""
    while True:
        status = _get(f"/api/eval/{eval_id}/status")
        tiles = status["tiles"]
        counts = {"pending": 0, "running": 0, "pass": 0, "fail": 0, "error": 0}
        for t in tiles:
            counts[t["status"]] = counts.get(t["status"], 0) + 1
        elapsed = int(time.time() - started_at)
        line = (
            f"    [{elapsed:>3}s] "
            f"pending={counts['pending']} running={counts['running']} "
            f"pass={counts['pass']} fail={counts['fail']} error={counts['error']}"
        )
        if line != last_line:
            print(line)
            last_line = line

        if status.get("scorecard") is not None:
            break

        if elapsed > 600:
            print("    timeout after 10min")
            print(json.dumps(status, indent=2))
            return 1
        time.sleep(4)

    # 4. Final scorecard + per-tile detail
    print()
    print("==> tiles")
    for t in status["tiles"]:
        marker = {"pass": "OK", "fail": "!!", "error": "XX"}.get(t["status"], "??")
        print(f"    [{marker}] q{t['q_idx']} run{t['run_idx']}  "
              f"acc={t['score']:.2f} rel={t['relevancy']:.2f}  "
              f"answer={t['answer'][:120]!r}")
        if t.get("reason"):
            print(f"           reason: {t['reason'][:400]}")

    print()
    print("==> scorecard")
    sc = status["scorecard"]
    print(f"    accuracy:          {sc['accuracy']}  ({sc['accuracy_pct']*100:.0f}%)")
    print(f"    consistency drift: {sc['consistency_drift']:.2f}  (lower = more consistent)")
    print(f"    relevancy:         {sc['relevancy_pct']*100:.0f}%")
    print()
    print("    per-question:")
    for q in sc["per_question"]:
        print(f"      q{q['q_idx']}  acc={q['acc']:.2f} rel={q['rel']:.2f} drift={q['drift']:.2f}  {q['reason']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
