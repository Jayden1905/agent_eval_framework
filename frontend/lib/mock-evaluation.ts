import type {
  AgentCard,
  AgentPresetId,
  EvalTile,
  EvaluationSnapshot,
  Scorecard,
  TestCase,
} from "./evaluation-types";

export const AGENTS: Record<AgentPresetId, AgentCard> = {
  accurate: {
    id: "accurate",
    name: "Singapore Trivia Agent",
    shortName: "Atlas",
    description: "Precise, repeatable answers with a low-temperature reasoning profile.",
    skill: "Singapore knowledge",
    avatarTone: "violet",
  },
  drifty: {
    id: "drifty",
    name: "Creative Trivia Agent",
    shortName: "Miso",
    description: "Usually correct, but changes phrasing and numeric confidence between runs.",
    skill: "Flexible Q&A",
    avatarTone: "amber",
  },
  wrong: {
    id: "wrong",
    name: "Confident Trivia Agent",
    shortName: "Nova",
    description: "Consistent and persuasive, even when the underlying facts are wrong.",
    skill: "Fast answers",
    avatarTone: "coral",
  },
};

export const DEMO_SET: TestCase[] = [
  { question: "What year did Singapore gain independence?", expected: "1965 — specifically 9 August 1965." },
  { question: "Name three ingredients commonly found in laksa.", expected: "Any three of coconut milk, rice noodles, prawns, tofu puffs, fish cake, sambal, or laksa leaves." },
  { question: "How many islands make up Singapore?", expected: "Approximately 63 islands; accept answers from 60–64." },
  { question: "What is Singapore's national language?", expected: "Malay. English, Mandarin, and Tamil are also official languages." },
  { question: "Who was Singapore's first Prime Minister?", expected: "Lee Kuan Yew." },
];

type FinishedRun = { answer: string; score: number; reason: string };

const accurate: FinishedRun[][] = [
  [
    { answer: "Singapore became independent on 9 August 1965.", score: 0.99, reason: "Exact date and year match the reference." },
    { answer: "1965, following Singapore's separation from Malaysia.", score: 0.97, reason: "Correct year with useful context." },
    { answer: "Singapore gained independence in 1965.", score: 0.98, reason: "Directly answers the question." },
  ],
  [
    { answer: "Rice noodles, coconut milk, and prawns.", score: 0.96, reason: "Three accepted ingredients are present." },
    { answer: "Coconut milk, tofu puffs, and sambal.", score: 0.95, reason: "Three accepted ingredients are present." },
    { answer: "Prawns, rice noodles, and laksa leaves.", score: 0.97, reason: "Three accepted ingredients are present." },
  ],
  [
    { answer: "Singapore is made up of about 63 islands.", score: 0.98, reason: "The count is inside the accepted range." },
    { answer: "Approximately 63 islands.", score: 0.98, reason: "The count matches the reference." },
    { answer: "There are around 63 islands in Singapore.", score: 0.97, reason: "The count is inside the accepted range." },
  ],
  [
    { answer: "Malay is Singapore's national language.", score: 0.99, reason: "Correctly identifies Malay." },
    { answer: "The national language is Malay.", score: 0.99, reason: "Directly matches the reference." },
    { answer: "Malay, while English, Mandarin, and Tamil are also official.", score: 0.98, reason: "Correct answer with accurate context." },
  ],
  [
    { answer: "Lee Kuan Yew was Singapore's first Prime Minister.", score: 0.99, reason: "Correct person." },
    { answer: "Singapore's first Prime Minister was Lee Kuan Yew.", score: 0.99, reason: "Correct person." },
    { answer: "Lee Kuan Yew.", score: 0.98, reason: "Concise and correct." },
  ],
];

const drifty: FinishedRun[][] = [
  accurate[0],
  [
    { answer: "Coconut broth, thick noodles, prawns—and usually tofu puffs too.", score: 0.92, reason: "Includes three accepted ingredients." },
    { answer: "Rice vermicelli, spicy coconut milk, and fish cake.", score: 0.94, reason: "Includes three accepted ingredients." },
    { answer: "It varies, but noodles and chilli are the main bits.", score: 0.56, reason: "Only two clear ingredients are supplied." },
  ],
  [
    { answer: "Most sources put it at roughly 63 islands.", score: 0.95, reason: "Inside the accepted range." },
    { answer: "About 60 islands altogether.", score: 0.82, reason: "At the lower edge of the accepted range." },
    { answer: "More than 70, depending on how reclaimed land is counted.", score: 0.31, reason: "The count falls outside the accepted range." },
  ],
  accurate[3],
  [
    { answer: "Lee Kuan Yew was the first Prime Minister.", score: 0.98, reason: "Correct person." },
    { answer: "That was Lee Kuan Yew, beginning in 1959.", score: 0.96, reason: "Correct person with supporting detail." },
    { answer: "Lee Kuan Yew—or, informally, LKY.", score: 0.91, reason: "Correct, but phrased less formally." },
  ],
];

const wrong: FinishedRun[][] = [
  [
    { answer: "Singapore became independent in 1963.", score: 0.18, reason: "The year is incorrect." },
    { answer: "Independence came in 1963.", score: 0.16, reason: "The year is incorrect." },
    { answer: "1963, after leaving Malaysia.", score: 0.14, reason: "The response confidently gives the wrong year." },
  ],
  accurate[1],
  [
    { answer: "Singapore has 54 islands.", score: 0.22, reason: "The count is outside the accepted range." },
    { answer: "There are exactly 54 islands.", score: 0.19, reason: "The count is outside the accepted range." },
    { answer: "It is an archipelago of 58 islands.", score: 0.35, reason: "The count is outside the accepted range." },
  ],
  [
    { answer: "English is Singapore's national language.", score: 0.3, reason: "English is official, but Malay is the national language." },
    { answer: "The national language is English.", score: 0.28, reason: "Confuses an official language with the national language." },
    { answer: "English, used across government and schools.", score: 0.32, reason: "Provides a plausible but incorrect national language." },
  ],
  [
    { answer: "Goh Chok Tong was Singapore's first Prime Minister.", score: 0.12, reason: "The named person is incorrect." },
    { answer: "Singapore's first Prime Minister was Goh Chok Tong.", score: 0.12, reason: "The named person is incorrect." },
    { answer: "Goh Chok Tong.", score: 0, reason: "The named person is incorrect." },
  ],
];

const RESULTS: Record<AgentPresetId, FinishedRun[][]> = { accurate, drifty, wrong };
const DRIFT: Record<AgentPresetId, number[]> = {
  accurate: [0, 0, 0, 0, 0],
  drifty: [0, 0.33, 0.67, 0, 0.33],
  wrong: [0, 0, 0.33, 0, 0],
};
const DRIFT_REASON: Record<AgentPresetId, string[]> = {
  accurate: ["All runs agree.", "Equivalent ingredient sets.", "All counts agree.", "All runs agree.", "All runs agree."],
  drifty: ["All runs agree.", "One response omits the required third ingredient.", "Three materially different island counts.", "All runs agree.", "Same fact with varying detail."],
  wrong: ["Consistently wrong year.", "Equivalent ingredient sets.", "Two conflicting wrong counts.", "Consistently wrong language.", "Consistently wrong person."],
};

function finalScorecard(agentId: AgentPresetId): Scorecard {
  const perQuestion = RESULTS[agentId].map((questionRuns, qIdx) => ({
    q_idx: qIdx,
    acc: questionRuns.reduce((sum, run) => sum + run.score, 0) / questionRuns.length,
    rel: 0.9,
    drift: DRIFT[agentId][qIdx],
    reason: DRIFT_REASON[agentId][qIdx],
  }));
  const passed = perQuestion.filter((question) => question.acc >= 0.7).length;
  return {
    accuracy: `${passed}/${DEMO_SET.length}`,
    accuracy_pct: passed / DEMO_SET.length,
    consistency_drift: perQuestion.reduce((sum, question) => sum + question.drift, 0) / perQuestion.length,
    relevancy_pct: perQuestion.reduce((sum, question) => sum + question.rel, 0) / perQuestion.length,
    per_question: perQuestion,
  };
}

export function getMockSnapshot(agentId: AgentPresetId, completed: number, evalId = "mock-ae7f3c", active = true): EvaluationSnapshot {
  const total = DEMO_SET.length * 3;
  const safeCompleted = Math.max(0, Math.min(completed, total));
  const tiles: EvalTile[] = [];

  DEMO_SET.forEach((_, qIdx) => {
    for (let runIdx = 0; runIdx < 3; runIdx += 1) {
      const flatIndex = qIdx * 3 + runIdx;
      const result = RESULTS[agentId][qIdx][runIdx];
      const isComplete = flatIndex < safeCompleted;
      const isRunning = active && !isComplete && safeCompleted < total;
      tiles.push({
        q_idx: qIdx,
        run_idx: runIdx,
        status: isComplete ? (result.score >= 0.7 ? "pass" : "fail") : isRunning ? "running" : "pending",
        answer: isComplete ? result.answer : "",
        score: isComplete ? result.score : 0,
        relevancy: isComplete ? 0.9 : 0,
        reason: isComplete ? result.reason : "",
        sandbox_id: `dx-${evalId.slice(-4)}-q${qIdx + 1}r${runIdx + 1}`,
      });
    }
  });

  return {
    eval_id: evalId,
    tiles,
    scorecard: safeCompleted === total ? finalScorecard(agentId) : null,
    completed: safeCompleted,
    total,
  };
}
