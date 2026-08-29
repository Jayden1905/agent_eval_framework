# Frontend (Next.js)

## Bootstrap (Dev 1, first thing)

From the repo root:

```bash
cd /Users/jayden-kyaw/projects/daytona_hackathon
npx create-next-app@latest frontend \
  --typescript --tailwind --app --no-src-dir --import-alias "@/*" --no-eslint --use-npm --yes
cd frontend
npm run dev
```

Then open http://localhost:3000. Backend runs separately on :8000 (see below).

**Default agent URL:** `http://localhost:8000/agents/accurate` — all three demo agents are mounted at path-based routes on the same backend process. See `../agents/agent_urls.txt`.

## Dev loop

**Terminal 1 — backend (mock mode, no anthropic/daytona needed):**
```bash
USE_MOCKS=1 uvicorn backend.server:app --reload --port 8000
```

**Terminal 2 — frontend:**
```bash
cd frontend && npm run dev
```

Swap `USE_MOCKS=1` off once Dev 2 lands the real backend.

## API contract (see `backend/server.py`)

```
POST /api/discover              body { url }
  → agent card JSON { name, description, skills, ... }

POST /api/eval                  body { agent_url, test_set: [{question, expected}], runs_per_q }
  → { eval_id }

GET  /api/eval/{eval_id}/status
  → { tiles: [{q_idx, run_idx, status, answer, score}], scorecard: {...} | null }

GET  /api/health                → { ok, mode }
```

Poll `/api/eval/{id}/status` every ~500ms until `scorecard !== null`.

## Starter code

See `frontend/STARTER.md` in this directory for a drop-in `app/page.tsx` and `lib/api.ts` — copy them in AFTER `create-next-app` finishes.

## Screens (build in this order)

1. Connect: URL input → `POST /api/discover` → render agent card
2. Test set: "Load demo" (fetch `/demo_set.jsonl` — copy into `public/`) or file upload
3. Run: button → `POST /api/eval` → get eval_id → start polling
4. Live grid: N rows × runs_per_q columns, each cell shows status icon + score + answer preview
5. Scorecard: accuracy X/Y, drift score, per-question table with side-by-side diff for drifty rows
