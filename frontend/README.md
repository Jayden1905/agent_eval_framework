# AgentEval Office frontend

An original responsive Next.js visualization for the AgentEval hackathon. It turns the backend's `5 questions × 3 runs` evaluation matrix into an office campus: each question gets one animated office, while its three isolated Daytona runs remain available as compact selectable indicators.

## Run locally

```bash
npm install
npm run dev
```

Open <http://localhost:3000>.

The current interface uses deterministic dummy data and does not require the Python backend or API keys. Choose the accurate, drifty, or wrong agent profile, start the evaluation, and use **Fast-forward results** to inspect the finished scorecard.

## Checks

```bash
npm run lint
npm run build
npm run test:responsive
```

The Playwright suite covers 360px and 390px phones, tablet, desktop, wide desktop, page-level overflow, all five question offices, all 15 run selectors, sandbox selection, scorecard playback, state animation hooks, and reduced motion.

## Frontend structure

- `app/page.tsx` — interactive office, setup controls, result grid, and inspector
- `app/globals.css` — original responsive pixel-office visual system
- `lib/evaluation-types.ts` — normalized UI contract matching the backend's tile and scorecard shapes
- `lib/mock-evaluation.ts` — deterministic dummy agent profiles and playback snapshots
- `lib/api.ts` — real HTTP adapter ready for backend integration
- `tests/responsive.spec.ts` — responsive and interaction coverage

## Switching from dummy data to the backend

1. Copy `.env.example` to `.env.local` if the API is not at `http://localhost:8000`.
2. Replace the mock snapshot progression in `app/page.tsx` with `discoverAgent`, `startEvaluation`, and `getEvaluationStatus` from `lib/api.ts`.
3. Poll `getEvaluationStatus` about every 500 ms until `scorecard` is non-null.
4. Preserve the normalized `EvaluationSnapshot` boundary so the office components do not depend on transport details. The adapter preserves the backend's per-run reason and relevancy fields while supplying safe defaults for older snapshots.

The legacy `STARTER.md` is the original scaffold supplied by the backend team. It remains for contract history; the working frontend supersedes it.

## Visual provenance

The office concept was informed by Pixel Agents, Claude Office, Star Office UI, and Star Office World. Their motion systems also informed the frontend's event-driven rhythm: a short materialize-and-enter sequence, a dominant running-state work loop, finite pass/fail/error reactions, and a quiet settled state. The three `ANIM` labels are presentation variants for mock mode, not backend telemetry.

No art, sprites, animation code, or keyframes were copied from those projects. All room, furniture, character, status, and motion visuals in this frontend are original CSS shapes so the hackathon team can safely evolve or commercialize the project later. Pixelify Sans is supplied through Fontsource under the SIL Open Font License 1.1.
