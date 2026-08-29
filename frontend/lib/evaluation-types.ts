export type TileStatus = "pending" | "running" | "pass" | "fail" | "error";

export type AgentPresetId = "accurate" | "drifty" | "wrong";

export type AgentCard = {
  id: AgentPresetId;
  name: string;
  shortName: string;
  description: string;
  skill: string;
  avatarTone: string;
};

export type TestCase = {
  question: string;
  expected: string;
};

export type EvalTile = {
  q_idx: number;
  run_idx: number;
  status: TileStatus;
  answer: string;
  score: number;
  relevancy: number;
  reason: string;
  run_id: string;
};

export type QuestionScore = {
  q_idx: number;
  acc: number;
  rel: number;
  drift: number;
  reason: string;
};

export type Scorecard = {
  accuracy: string;
  accuracy_pct: number;
  consistency_drift: number;
  relevancy_pct: number;
  per_question: QuestionScore[];
};

export type EvaluationSnapshot = {
  eval_id: string;
  tiles: EvalTile[];
  scorecard: Scorecard | null;
  completed: number;
  total: number;
};
