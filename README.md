# AgentEval — Daytona HackSprint SG

Bring-your-own-agent evaluation platform. Connect via A2A, get accuracy + consistency scores.

## Setup (do once, all devs)

```bash
python -m venv .venv
source .venv/bin/activate   # fish: source .venv/bin/activate.fish
pip install -r requirements.txt
cp .env.template .env       # then fill in keys
```

## Ownership

## Architecture

**One Python process** (`uvicorn backend.server:app --port 8000`) serves everything:
- `/api/*` — eval platform
- `/agents/accurate`, `/agents/drifty`, `/agents/wrong` — three demo agents at path-based mounts

**One Node process** (`npm run dev` in `frontend/`) runs Next.js on :3000.

Total: **two processes** for local dev + demo.

| Dev | Files | Runs |
|-----|-------|------|
| **1 (Frontend, Next.js)** | `frontend/` (bootstrap with create-next-app — see `frontend/README.md`) | `USE_MOCKS=1 uvicorn backend.server:app --port 8000` + `cd frontend && npm run dev` |
| **2 (Platform + Judge)** | `backend/*.py` | `uvicorn backend.server:app --reload --port 8000` |
| **3 (Test Agents)** | `agents/agent_accurate.py`, `agents/agent_drifty.py`, `agents/agent_wrong.py` (all auto-mounted) | Restart backend to pick up changes |

## Streamlit fallback

`hack.py` is the Streamlit UI, kept as an escape hatch if the Next.js frontend blocks. Same backend, one command: `streamlit run hack.py`. Uses mocks by default; flip the import to hit the real backend.

## The contract

The three tracks touch here — code against these signatures, don't renegotiate mid-hack:

```python
# backend/eval.py — Dev 2 owns
def discover_agent(url: str) -> dict: ...
def start_eval(agent_url: str, test_set: list[dict], runs_per_q: int = 3) -> str: ...
def get_eval_status(eval_id: str) -> dict: ...
```

Return shapes documented inline in `backend/eval.py` docstrings + reflected in `backend/mocks.py`.

Dev 1 writes UI against `backend.mocks.*` (or against `backend.eval` — real impl is already scaffolded). Both have the same API.

**Package is named `backend/` not `platform/`** — `platform` is a Python stdlib module and shadowing it breaks imports depending on sys.path order.

## Timeline

| Phase | Time | What |
|-------|------|------|
| 0 | 11:30–11:45 | Alignment, lock demo Q&A set |
| 1 | 11:45–1:00 | Skeleton + 1 end-to-end pass per dev, in isolation |
| 2 | 1:00–2:30 | Core: real backend + 2nd/3rd agent + real UI wiring |
| 3 | 2:30–3:30 | Integration, all together |
| 4 | 3:30–4:00 | Polish + demo script |
| 5 | 4:00–4:30 | Rehearse 3× |

## Demo Q&A set

See `demo_set.jsonl`. 5 questions about Singapore. Question 3 (islands) is the drift-hook.

## Why DeepEval + Daytona?

- **DeepEval** ships the accuracy metrics we need (`GEval` for custom rubrics) and is the industry-standard agent-eval framework. Reusing it beats hand-rolling judge prompts.
- **Consistency across runs is a gap** in DeepEval — the docs confirm no first-class metric for it. That's our novelty: same input × N runs → cluster responses via `GEval` → drift score. Each run lives in its own Daytona sandbox for isolation.
- The one-liner: **DeepEval gives us accuracy. Daytona lets us measure consistency.**

## Why not `a2a-sdk`?

Correct choice for prod. Wrong for a 5-hour build. We serve `/.well-known/agent-card.json` (v1.0 shape) and one JSON-RPC endpoint `/a2a/jsonrpc/` implementing `message/send`. Compliant on the wire, zero framework debt. See `agents/a2a_server.py`.

## Why no pre-baked Daytona snapshot?

`Image.base("python:3.11-slim").pipInstall(["anthropic", "httpx"])` — Daytona builds+caches on first `create`. First eval run pays ~30-60s. All later runs hit cache. See `platform/sandbox.py`.
