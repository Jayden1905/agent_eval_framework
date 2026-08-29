"""End-to-end smoke test for the eval platform.

Discovers the accurate agent, kicks off a small eval (2 questions x 2 runs),
polls status every 4s, prints tile progress + final scorecard.

Auto-spawns a Cloudflare quick tunnel so Daytona sandboxes can reach the
local backend's demo agents. Set TUNNEL_URL to skip.

Note: the mac's own DNS may fail to resolve trycloudflare.com subdomains on
some networks — that's fine. cloudflared uses a persistent QUIC connection
to the edge and doesn't need mac DNS. The sandboxes (on Daytona's network)
resolve the URL cleanly.

Usage:
  python scripts/smoke_eval.py                     # accurate agent
  AGENT=drifty python scripts/smoke_eval.py        # drifty
  AGENT=wrong   python scripts/smoke_eval.py       # wrong

Requires: `make dev` running on localhost:8000, cloudflared installed.
"""
from __future__ import annotations

import atexit
import json
import os
import re
import subprocess
import sys
import time
import urllib.request


BASE = os.environ.get("BACKEND", "http://localhost:8000")
AGENT = os.environ.get("AGENT", "accurate")
TUNNEL_URL_OVERRIDE = os.environ.get("TUNNEL_URL", "")
_TUNNEL_PROC: subprocess.Popen | None = None


def _start_tunnel(port: int) -> str:
    """Spawn cloudflared and return the assigned public URL.

    We don't probe from the mac — corporate DNS often fails to resolve
    trycloudflare.com subdomains. cloudflared's QUIC link to the edge is
    already up by the time it prints the URL; the sandboxes will use it.
    """
    global _TUNNEL_PROC
    print("==> spawning cloudflared quick tunnel")
    _TUNNEL_PROC = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    atexit.register(_stop_tunnel)

    pat = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
    deadline = time.time() + 30
    assert _TUNNEL_PROC.stdout is not None
    while time.time() < deadline:
        line = _TUNNEL_PROC.stdout.readline()
        if not line:
            time.sleep(0.2)
            continue
        m = pat.search(line)
        if m:
            url = m.group(0)
            print(f"    tunnel: {url}")
            # Small settle time for the edge to accept requests.
            time.sleep(3)
            return url
    _stop_tunnel()
    raise RuntimeError("cloudflared did not report a trycloudflare.com URL within 30s")


def _stop_tunnel() -> None:
    global _TUNNEL_PROC
    if _TUNNEL_PROC and _TUNNEL_PROC.poll() is None:
        _TUNNEL_PROC.terminate()
        try:
            _TUNNEL_PROC.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _TUNNEL_PROC.kill()
    _TUNNEL_PROC = None


if TUNNEL_URL_OVERRIDE:
    PUBLIC_BASE = TUNNEL_URL_OVERRIDE.rstrip("/")
else:
    PUBLIC_BASE = _start_tunnel(8000)

# Backend hits itself for discovery (mac DNS can't resolve trycloudflare on
# this network); sandboxes hit the tunnel URL for the actual eval.
LOCAL_AGENT_URL = f"{BASE}/agents/{AGENT}"
AGENT_URL = f"{PUBLIC_BASE}/agents/{AGENT}"

TEST_SET = [
    {"question": "What year did Singapore gain independence?", "expected": "1965"},
    {"question": "What is the capital of Singapore?", "expected": "Singapore (city-state)"},
    {"question": "Who was Singapore's first Prime Minister?", "expected": "Lee Kuan Yew"},
    {"question": "What is the national language of Singapore?", "expected": "Malay"},
]
RUNS_PER_Q = 2


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def _get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return json.loads(r.read())


def main() -> int:
    print(f"backend:  {BASE}")
    print(f"discover: {LOCAL_AGENT_URL}  (mac -> localhost)")
    print(f"eval:     {AGENT_URL}  (sandbox -> tunnel)")
    print()

    # 1. Discover — via local URL so backend can reach itself
    print("==> discover")
    card = _post("/api/discover", {"url": LOCAL_AGENT_URL})
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
    print("==> polling (each tile: spawn sandbox → agent call → backend scoring; ~60-120s cold, ~30-45s warm)")
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
