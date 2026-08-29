# Drop-in starter for `frontend/`

After `create-next-app` finishes, copy these into your `frontend/` tree.
They wire up the API contract and the polling loop. Skinning + layout is
yours.

## `lib/api.ts`

```ts
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type AgentCard = {
  name: string;
  description: string;
  skills?: { name: string; description?: string }[];
  [k: string]: unknown;
};

export type Tile = {
  q_idx: number;
  run_idx: number;
  status: "pending" | "running" | "pass" | "fail" | "error";
  answer: string;
  score: number;
};

export type Scorecard = {
  accuracy: string;
  accuracy_pct: number;
  consistency_drift: number;
  per_question: {
    q_idx: number;
    acc: number;
    drift: number;
    reason: string;
  }[];
};

export type EvalStatus = {
  tiles: Tile[];
  scorecard: Scorecard | null;
};

export type TestCase = { question: string; expected: string };

export async function discover(url: string): Promise<AgentCard> {
  const r = await fetch(`${API}/api/discover`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function startEval(
  agent_url: string,
  test_set: TestCase[],
  runs_per_q = 3,
): Promise<string> {
  const r = await fetch(`${API}/api/eval`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ agent_url, test_set, runs_per_q }),
  });
  if (!r.ok) throw new Error(await r.text());
  const { eval_id } = await r.json();
  return eval_id;
}

export async function getStatus(evalId: string): Promise<EvalStatus> {
  const r = await fetch(`${API}/api/eval/${evalId}/status`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
```

## `app/page.tsx` (minimal working flow — restyle freely)

```tsx
"use client";

import { useEffect, useState } from "react";
import {
  AgentCard,
  EvalStatus,
  TestCase,
  discover,
  getStatus,
  startEval,
} from "@/lib/api";

const DEMO_SET: TestCase[] = [
  { question: "What year did Singapore gain independence?", expected: "1965." },
  { question: "Name three ingredients in a laksa.", expected: "Any three from: coconut milk, rice noodles, prawns, tofu puffs, fish cake, chili paste, laksa leaves." },
  { question: "How many islands make up Singapore?", expected: "About 63 islands. Accept 60-64." },
  { question: "What is the national language of Singapore?", expected: "Malay (English, Mandarin, Tamil also official)." },
  { question: "Who was Singapore's first Prime Minister?", expected: "Lee Kuan Yew." },
];

export default function Page() {
  const [url, setUrl] = useState("http://localhost:8000/agents/accurate");
  const [card, setCard] = useState<AgentCard | null>(null);
  const [testSet, setTestSet] = useState<TestCase[] | null>(null);
  const [runsPerQ, setRunsPerQ] = useState(3);
  const [evalId, setEvalId] = useState<string | null>(null);
  const [status, setStatus] = useState<EvalStatus | null>(null);

  useEffect(() => {
    if (!evalId) return;
    const id = setInterval(async () => {
      const s = await getStatus(evalId);
      setStatus(s);
      if (s.scorecard) clearInterval(id);
    }, 500);
    return () => clearInterval(id);
  }, [evalId]);

  return (
    <main className="mx-auto max-w-5xl p-8 space-y-8">
      <header>
        <h1 className="text-3xl font-semibold">AgentEval</h1>
        <p className="text-sm text-neutral-500">
          Bring your agent. We tell you if it&apos;s trustworthy.
        </p>
      </header>

      <section className="space-y-2">
        <h2 className="font-medium">1. Connect your agent</h2>
        <div className="flex gap-2">
          <input
            className="flex-1 border rounded px-3 py-2"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button
            className="px-4 py-2 rounded bg-black text-white"
            onClick={async () => setCard(await discover(url))}
          >
            Discover
          </button>
        </div>
        {card && (
          <div className="rounded border p-4">
            <div className="font-medium">{card.name}</div>
            <div className="text-sm text-neutral-500">{card.description}</div>
            {card.skills?.map((s) => (
              <div key={s.name} className="text-sm mt-1">
                <span className="font-mono">{s.name}</span> — {s.description}
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="font-medium">2. Test set</h2>
        <button
          className="px-3 py-1 rounded border"
          onClick={() => setTestSet(DEMO_SET)}
        >
          Load demo set
        </button>
        {testSet && (
          <ol className="list-decimal list-inside text-sm">
            {testSet.map((t, i) => (
              <li key={i}>{t.question}</li>
            ))}
          </ol>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="font-medium">3. Evaluate</h2>
        <div className="flex items-center gap-3">
          <label className="text-sm">
            Runs per question:{" "}
            <input
              type="number"
              className="border rounded w-16 px-2 py-1"
              value={runsPerQ}
              min={1}
              max={5}
              onChange={(e) => setRunsPerQ(parseInt(e.target.value))}
            />
          </label>
          <button
            className="px-4 py-2 rounded bg-black text-white disabled:opacity-40"
            disabled={!card || !testSet}
            onClick={async () =>
              setEvalId(await startEval(url, testSet!, runsPerQ))
            }
          >
            Run eval
          </button>
        </div>
      </section>

      {status && (
        <section className="space-y-4">
          <h2 className="font-medium">4. Results</h2>
          <div className="space-y-2">
            {testSet!.map((t, qi) => (
              <div key={qi} className="flex items-center gap-2">
                <div className="flex-1 text-sm truncate">
                  <span className="font-semibold">Q{qi + 1}.</span> {t.question}
                </div>
                {Array.from({ length: runsPerQ }).map((_, ri) => {
                  const tile = status.tiles.find(
                    (x) => x.q_idx === qi && x.run_idx === ri,
                  );
                  const icon = {
                    pending: "⚪",
                    running: "🟡",
                    pass: "🟢",
                    fail: "🔴",
                    error: "❌",
                  }[tile?.status ?? "pending"];
                  return (
                    <div
                      key={ri}
                      className="text-xs w-24 text-center"
                      title={tile?.answer}
                    >
                      <div className="text-lg">{icon}</div>
                      <div className="font-mono">{tile?.score?.toFixed(2)}</div>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>

          {status.scorecard && (
            <div className="rounded border p-4 space-y-2">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-neutral-500">Accuracy</div>
                  <div className="text-2xl font-semibold">
                    {status.scorecard.accuracy}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-neutral-500">Consistency drift</div>
                  <div className="text-2xl font-semibold">
                    {status.scorecard.consistency_drift.toFixed(2)}
                    <span className="ml-2 text-sm text-neutral-500">
                      {status.scorecard.consistency_drift < 0.01
                        ? "rock solid"
                        : status.scorecard.consistency_drift < 0.34
                          ? "occasional drift"
                          : "unreliable"}
                    </span>
                  </div>
                </div>
              </div>
              <table className="w-full text-sm mt-4">
                <thead>
                  <tr className="text-left text-neutral-500">
                    <th>Q</th>
                    <th>Accuracy</th>
                    <th>Drift</th>
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {status.scorecard.per_question.map((q) => (
                    <tr key={q.q_idx} className="border-t">
                      <td>{q.q_idx + 1}</td>
                      <td>{q.acc.toFixed(2)}</td>
                      <td>{q.drift.toFixed(2)}</td>
                      <td>{q.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
```

## Optional — proxy demo_set.jsonl via `public/`

If you want the "Load demo set" button to fetch the same file the backend uses:

```bash
# from frontend/
ln -s ../demo_set.jsonl public/demo_set.jsonl
```

Then in `page.tsx`, replace the const with a fetch:
```ts
const set = await fetch("/demo_set.jsonl").then(r => r.text())
  .then(t => t.trim().split("\n").map(l => JSON.parse(l)));
setTestSet(set);
```
