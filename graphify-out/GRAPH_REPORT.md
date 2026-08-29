# Graph Report - .  (2026-08-29)

## Corpus Check
- Corpus is ~5,878 words - fits in a single context window. You may not need a graph.

## Summary
- 127 nodes · 174 edges · 12 communities (11 shown, 1 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 22 edges (avg confidence: 0.9)
- Token cost: 146,742 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_A2A Agent Servers|A2A Agent Servers]]
- [[_COMMUNITY_Eval Orchestration|Eval Orchestration]]
- [[_COMMUNITY_Evaluation Data Model|Evaluation Data Model]]
- [[_COMMUNITY_Judge & Scoring|Judge & Scoring]]
- [[_COMMUNITY_A2A Client|A2A Client]]
- [[_COMMUNITY_Daytona Sandbox Fanout|Daytona Sandbox Fanout]]
- [[_COMMUNITY_Frontend & API Discovery|Frontend & API Discovery]]
- [[_COMMUNITY_Sandbox Worker|Sandbox Worker]]
- [[_COMMUNITY_Project Overview|Project Overview]]
- [[_COMMUNITY_Hack Entrypoint|Hack Entrypoint]]

## God Nodes (most connected - your core abstractions)
1. `main()` - 9 edges
2. `run_worker_in_sandbox()` - 8 edges
3. `responder()` - 7 edges
4. `responder()` - 7 edges
5. `AgentEval platform (bring-your-own-agent eval)` - 7 edges
6. `responder()` - 6 edges
7. `send_message()` - 6 edges
8. `score_consistency()` - 6 edges
9. `mount()` - 5 edges
10. `discover()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `TS startEval() HTTP wrapper` --calls--> `start_eval()`  [EXTRACTED]
  frontend/STARTER.md → backend/server.py
- `TS getStatus() HTTP wrapper` --calls--> `eval_status()`  [EXTRACTED]
  frontend/STARTER.md → backend/server.py
- `TS AgentCard type` --shares_data_with--> `AgentCard`  [INFERRED]
  frontend/STARTER.md → backend/eval.py
- `mount()` --implements--> `A2A v1.0 protocol (wire-compatible subset)`  [EXTRACTED]
  agents/a2a_server.py → README.md
- `TS discover() HTTP wrapper` --calls--> `discover()`  [EXTRACTED]
  frontend/STARTER.md → backend/server.py

## Hyperedges (group relationships)
- **A2A pluggable responder wiring** — agents_a2a_server_mount, agents_a2a_server_responder_type, agents_agent_accurate_responder, agents_agent_drifty_responder, agents_agent_wrong_responder [EXTRACTED 1.00]
- **Demo trio: correct / drifty / wrong failure modes** — agents_agent_accurate_responder, agents_agent_drifty_responder, agents_agent_wrong_responder [EXTRACTED 1.00]
- **Eval orchestration pipeline (HTTP to sandbox worker)** — backend_server_start_eval, backend_eval_start_eval, backend_eval__run_eval, backend_sandbox_fan_out, backend_sandbox_run_worker_in_sandbox, backend_sandbox_worker_main [EXTRACTED 1.00]
- **Tile / EvalStatus shape mirrored across backend, mocks, and TS** — backend_eval_tile, backend_eval_evalstatus, backend_mocks_get_eval_status, frontend_starter_tile_type, frontend_starter_evalstatus_type [INFERRED 0.85]
- **A2A JSON-RPC v1.0 wire protocol (agent card + message/send)** — backend_a2a_client_discover, backend_a2a_client__rpc_url_from_card, backend_a2a_client_send_message, backend_sandbox_worker__send_a2a [EXTRACTED 1.00]

## Communities (12 total, 1 thin omitted)

### Community 0 - "A2A Agent Servers"
Cohesion: 0.10
Nodes (21): _build_card() — agent card dict, agent_card route handler (GET), jsonrpc route handler (POST message/send), mount(), Shared A2A HTTP scaffold — mountable onto a FastAPI/Starlette app.  Two endpoint, Attach agent-card + JSON-RPC routes to `app` under `prefix`.      Example:, Responder = Callable[[str], str], accurate agent lazy Anthropic client (+13 more)

### Community 1 - "Eval Orchestration"
Cohesion: 0.14
Nodes (19): _finalize_scorecard (aggregate), eval._run_eval (background thread), _STATE in-process eval registry, get_eval_status(), start_eval(), get_eval_status(), Fake data with the exact shape from backend/eval.py.  Dev 1 imports from here to, # NOTE: intentionally does NOT import from backend.eval — Dev 1 must be able to (+11 more)

### Community 2 - "Evaluation Data Model"
Cohesion: 0.16
Nodes (15): AgentCard, EvalStatus, _finalize_scorecard(), Public API for the eval platform. Frontend (hack.py) imports from here.  Dev 1:, Compute per-question accuracy + consistency drift, roll up., Whatever we discover at {url}/.well-known/agent-card.json.      Passthrough dict, Background thread: fan out sandboxes, then aggregate., _run_eval() (+7 more)

### Community 3 - "Judge & Scoring"
Cohesion: 0.20
Nodes (13): _extract_json (parse LLM JSON block), _geval_accuracy_fallback (direct Claude), compute_drift(), _extract_json(), _geval_accuracy_fallback(), Judges — accuracy (per-run) and consistency (across-runs).  - Accuracy: DeepEval, Grab the first {...} block from a model response., Returns {"score": 0..1, "reason": str}. (+5 more)

### Community 4 - "A2A Client"
Cohesion: 0.27
Nodes (9): A2A _rpc_url_from_card, discover(), Thin A2A client — discovery + message/send.  We speak the A2A wire format direct, GET {url}/.well-known/agent-card.json and return parsed JSON., Find the JSON-RPC endpoint from an agent card (v1.0 shape).      Falls back to `, Send `text` to the agent via A2A message/send. Returns the agent's reply text., _rpc_url_from_card(), send_message() (+1 more)

### Community 5 - "Daytona Sandbox Fanout"
Cohesion: 0.27
Nodes (9): Declarative Daytona image spec, Sandbox _upload_text helper, _client(), fan_out(), Daytona sandbox wrapper.  Declarative image: no pre-baked snapshot needed. First, Spawn one sandbox, upload worker.py, run it, return the JSON result.      Return, Run many (question, run_idx) tasks in parallel across sandboxes.      tasks: [{", run_worker_in_sandbox() (+1 more)

### Community 6 - "Frontend & API Discovery"
Cohesion: 0.27
Nodes (10): discover_agent(), discover_agent(), discover(), USE_MOCKS module switch, Frontend README dev loop (uvicorn + next dev), DEMO_SET Singapore trivia fixtures, TS discover() HTTP wrapper, TS getStatus() HTTP wrapper (+2 more)

### Community 7 - "Sandbox Worker"
Cohesion: 0.31
Nodes (8): Worker _write (dumps result.json), main(), Runs INSIDE a Daytona sandbox — one process per (question, run_idx) tile.  Reads, Discover agent card + send message/send. See platform/a2a_client.py for parity., DeepEval GEval — accuracy rubric., _score(), _send_a2a(), _write()

### Community 8 - "Project Overview"
Cohesion: 0.38
Nodes (7): AgentEval Streamlit UI, AgentEval platform (bring-your-own-agent eval), Consistency-drift metric (novelty over DeepEval), Daytona — per-run sandbox isolation, DeepEval — accuracy metrics + GEval rubric, Two-process (uvicorn + Next.js) architecture, Project Python dependencies

## Knowledge Gaps
- **15 isolated node(s):** `AgentEval Streamlit UI`, `_build_card() — agent card dict`, `accurate agent lazy Anthropic client`, `drifty agent lazy Anthropic client`, `wrong agent lazy Anthropic client` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `Sandbox Worker` to `Eval Orchestration`, `Judge & Scoring`, `A2A Client`, `Daytona Sandbox Fanout`?**
  _High betweenness centrality (0.172) - this node is a cross-community bridge._
- **Why does `eval._run_eval (background thread)` connect `Eval Orchestration` to `Daytona Sandbox Fanout`, `Sandbox Worker`?**
  _High betweenness centrality (0.157) - this node is a cross-community bridge._
- **Why does `start_eval()` connect `Eval Orchestration` to `Evaluation Data Model`?**
  _High betweenness centrality (0.151) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `main()` (e.g. with `eval._run_eval (background thread)` and `run_worker_in_sandbox()`) actually correct?**
  _`main()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `responder()` (e.g. with `jsonrpc route handler (POST message/send)` and `Responder = Callable[[str], str]`) actually correct?**
  _`responder()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `responder()` (e.g. with `jsonrpc route handler (POST message/send)` and `Responder = Callable[[str], str]`) actually correct?**
  _`responder()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AgentEval — Streamlit UI.  Dev 1 owns this file. During Phase 1 use `platform.mo`, `Shared A2A HTTP scaffold — mountable onto a FastAPI/Starlette app.  Two endpoint`, `Attach agent-card + JSON-RPC routes to `app` under `prefix`.      Example:` to the rest of the system?**
  _45 weakly-connected nodes found - possible documentation gaps or missing edges._