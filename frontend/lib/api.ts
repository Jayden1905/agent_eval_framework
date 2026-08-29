import type { EvaluationSnapshot, Scorecard, TestCase, TileStatus } from "./evaluation-types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type DiscoveredAgent = {
  name: string;
  description: string;
  skills?: { name: string; description?: string }[];
  [key: string]: unknown;
};

type BackendTile = {
  q_idx: number;
  run_idx: number;
  status: TileStatus;
  answer: string;
  score: number;
  relevancy?: number;
  reason?: string;
};

type BackendScorecard = Omit<Scorecard, "relevancy_pct" | "per_question"> & {
  relevancy_pct?: number;
  per_question: Array<Omit<Scorecard["per_question"][number], "rel"> & { rel?: number }>;
};

type BackendStatus = {
  tiles: BackendTile[];
  scorecard: BackendScorecard | null;
};

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error((await response.text()) || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function discoverAgent(url: string, signal?: AbortSignal): Promise<DiscoveredAgent> {
  const response = await fetch(`${API}/api/discover`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ url }),
    signal,
  });
  return readJson<DiscoveredAgent>(response);
}

export async function startEvaluation(agentUrl: string, testSet: TestCase[], runsPerQuestion = 3, signal?: AbortSignal): Promise<string> {
  const response = await fetch(`${API}/api/eval`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ agent_url: agentUrl, test_set: testSet, runs_per_q: runsPerQuestion }),
    signal,
  });
  const body = await readJson<{ eval_id: string }>(response);
  return body.eval_id;
}

export async function getEvaluationStatus(evalId: string, signal?: AbortSignal): Promise<EvaluationSnapshot> {
  const response = await fetch(`${API}/api/eval/${encodeURIComponent(evalId)}/status`, { signal });
  const body = await readJson<BackendStatus>(response);
  const completed = body.tiles.filter((tile) => ["pass", "fail", "error"].includes(tile.status)).length;
  const scorecard: Scorecard | null = body.scorecard ? {
    ...body.scorecard,
    relevancy_pct: body.scorecard.relevancy_pct ?? 0,
    per_question: body.scorecard.per_question.map((question) => ({ ...question, rel: question.rel ?? 0 })),
  } : null;
  return {
    eval_id: evalId,
    completed,
    total: body.tiles.length,
    scorecard,
    tiles: body.tiles.map((tile) => ({
      ...tile,
      relevancy: tile.relevancy ?? 0,
      reason: tile.reason ?? "",
      sandbox_id: `dx-${evalId}-q${tile.q_idx + 1}r${tile.run_idx + 1}`,
    })),
  };
}
