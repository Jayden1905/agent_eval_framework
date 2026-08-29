"use client";

import { useEffect, useMemo, useState } from "react";
import type { KeyboardEvent } from "react";
import { AGENTS, DEMO_SET, getMockSnapshot } from "@/lib/mock-evaluation";
import type { AgentPresetId, EvalTile, TileStatus } from "@/lib/evaluation-types";

const STATUS_META: Record<TileStatus, { label: string; symbol: string }> = {
  pending: { label: "Queued", symbol: "·" },
  running: { label: "Running", symbol: "↗" },
  pass: { label: "Passed", symbol: "✓" },
  fail: { label: "Failed", symbol: "!" },
  error: { label: "Error", symbol: "×" },
};

function formatScore(score: number, status: TileStatus) {
  return ["pending", "running", "error"].includes(status) ? "—" : score.toFixed(2);
}

function ActivityIcon({ status }: { status: TileStatus }) {
  return <span className={`activity-icon status-${status}`} aria-hidden="true">{STATUS_META[status].symbol}</span>;
}

function AgentSprite({ tone, active = false, state }: { tone: string; active?: boolean; state?: TileStatus }) {
  return (
    <span className={`agent agent-${tone} ${active ? "agent-active" : ""} ${state ? `agent-state-${state}` : ""}`} aria-hidden="true">
      <i className="agent-shadow" />
      <i className="agent-leg agent-leg-left" />
      <i className="agent-leg agent-leg-right" />
      <i className="agent-arm agent-arm-left" />
      <i className="agent-arm agent-arm-right" />
      <i className="agent-body"><em /></i>
      <i className="agent-face" />
      <i className="agent-hair" />
    </span>
  );
}

function getOfficeStatus(tiles: EvalTile[]): TileStatus {
  if (tiles.some((tile) => tile.status === "running")) return "running";
  if (tiles.every((tile) => tile.status === "pending")) return "pending";
  if (tiles.every((tile) => ["pass", "fail", "error"].includes(tile.status))) {
    if (tiles.some((tile) => tile.status === "error")) return "error";
    if (tiles.some((tile) => tile.status === "fail")) return "fail";
    return "pass";
  }
  return "pending";
}

function QuestionOffice({
  tiles,
  selectedKey,
  tone,
  onSelect,
}: {
  tiles: EvalTile[];
  selectedKey: string;
  tone: string;
  onSelect: (tile: EvalTile) => void;
}) {
  const officeStatus = getOfficeStatus(tiles);
  const runningTile = tiles.find((tile) => tile.status === "running");
  const selectedTile = tiles.find((tile) => `${tile.q_idx}-${tile.run_idx}` === selectedKey);
  const latestFinished = [...tiles].reverse().find((tile) => ["pass", "fail", "error"].includes(tile.status));
  const displayTile = runningTile ?? selectedTile ?? latestFinished ?? tiles[0];
  const visualStatus = runningTile?.status ?? (selectedTile ? selectedTile.status : officeStatus);
  const meta = STATUS_META[visualStatus];
  const scoredTiles = tiles.filter((tile) => ["pass", "fail"].includes(tile.status));
  const averageScore = scoredTiles.reduce((sum, tile) => sum + tile.score, 0) / Math.max(scoredTiles.length, 1);
  const activityMode = (["typing", "pacing", "training"] as const)[tiles[0].q_idx % 3];
  const activityLabel = visualStatus === "running"
    ? { typing: "ANIM · TYPING", pacing: "ANIM · ROUTE", training: "ANIM · LOAD" }[activityMode]
    : visualStatus === "pass"
      ? "VICTORY MODE"
      : ["fail", "error"].includes(visualStatus)
        ? "ANGER MODE"
        : "IDLE MODE";

  return (
    <article className={`question-office office-${visualStatus} activity-${activityMode}`} aria-label={`Question ${tiles[0].q_idx + 1} office: ${meta.label}`}>
      <div className="office-topline">
        <span className="office-title">SHARED SANDBOX OFFICE <small>{activityLabel}</small></span>
        <span className={`status-label status-${visualStatus}`}><b>{meta.symbol}</b>{meta.label}</span>
      </div>
      <div className={`room-scene scene-${visualStatus}`} aria-hidden="true">
        <span className="room-wall-trim" />
        <span className="room-window"><i /><i /></span>
        <span className="room-poster"><i /></span>
        <span className="room-shelf"><i /><i /><i /></span>
        <span className="room-clock"><i /></span>
        <span className="room-plant"><i /></span>
        <span className="room-rug" />
        <span className="room-chair" />
        <span className="room-desk"><i className="desk-keyboard" /><i className="desk-mug" /></span>
        <span className="room-monitor">{visualStatus === "running" ? "···" : visualStatus === "pass" ? "OK" : visualStatus === "fail" ? "!!" : visualStatus === "error" ? "XX" : "Zz"}</span>
        <span className="monitor-cable" />
        {visualStatus !== "pending" && (
          <span className="agent-stage">
            <AgentSprite tone={tone} active={visualStatus === "running" && activityMode === "typing"} state={visualStatus} />
            {visualStatus === "running" && activityMode === "pacing" && <span className="pace-dust"><i /><i /></span>}
            {visualStatus === "running" && activityMode === "training" && <span className="pixel-dumbbell" />}
          </span>
        )}
        {visualStatus === "running" && <span className="spawn-scan"><i /><i /><i /><i /><i /><i /><i /><i /></span>}
        {visualStatus === "running" && activityMode === "typing" && <span className="typing-bubble">⌁⌁</span>}
        {visualStatus === "running" && activityMode === "training" && <span className="training-bubble">RUN!</span>}
        {["fail", "error"].includes(visualStatus) && <span className="anger-steam"><i /><i /><i /></span>}
        {["pass", "fail", "error"].includes(visualStatus) && <span className={`result-bubble result-bubble-${visualStatus}`} key={`${displayTile.run_id}-${visualStatus}`}>{meta.symbol}</span>}
        <span className={`room-state-effect effect-${visualStatus}`}><i /><i /><i /></span>
      </div>
      <div className="office-run-strip" role="group" aria-label={`Question ${tiles[0].q_idx + 1} sandbox runs`}>
        {tiles.map((tile) => {
          const selected = `${tile.q_idx}-${tile.run_idx}` === selectedKey;
          const tileMeta = STATUS_META[tile.status];
          return (
            <button
              type="button"
              key={tile.run_idx}
              className={`run-indicator run-${tile.status} ${selected ? "run-selected" : ""}`}
              onClick={() => onSelect(tile)}
              aria-pressed={selected}
              aria-label={`Question ${tile.q_idx + 1}, run ${tile.run_idx + 1}: ${tileMeta.label}${["pass", "fail"].includes(tile.status) ? `, score ${tile.score.toFixed(2)}` : ""}`}
            >
              <span>RUN {String(tile.run_idx + 1).padStart(2, "0")}</span>
              <i>{tileMeta.symbol}</i>
              <strong>{formatScore(tile.score, tile.status)}</strong>
            </button>
          );
        })}
        <span className="office-average"><small>AVG</small><strong>{scoredTiles.length ? averageScore.toFixed(2) : "—"}</strong></span>
      </div>
      <span className="office-run-id">RUN REF · {displayTile.run_id}</span>
    </article>
  );
}

export default function Home() {
  const [agentId, setAgentId] = useState<AgentPresetId>("drifty");
  const [agentUrl, setAgentUrl] = useState("http://localhost:8000/agents/drifty");
  const [connected, setConnected] = useState(true);
  const [started, setStarted] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [completed, setCompleted] = useState(0);
  const [selectedKey, setSelectedKey] = useState("0-0");
  const [view, setView] = useState<"office" | "results">("office");

  const agent = AGENTS[agentId];
  const snapshot = useMemo(() => getMockSnapshot(agentId, completed, "mock-ae7f3c", started), [agentId, completed, started]);
  const selectedTile = snapshot.tiles.find((tile) => `${tile.q_idx}-${tile.run_idx}` === selectedKey) ?? snapshot.tiles[0];
  const progress = Math.round((snapshot.completed / snapshot.total) * 100);
  const phase = !started ? "ready" : completed >= snapshot.total ? "complete" : "running";

  useEffect(() => {
    if (!playing || completed >= snapshot.total) return;
    const interval = window.setInterval(() => {
      setCompleted((current) => current >= snapshot.total ? current : current + 1);
    }, 980);
    return () => window.clearInterval(interval);
  }, [completed, playing, snapshot.total]);

  function selectAgent(nextId: AgentPresetId) {
    setAgentId(nextId);
    setAgentUrl(`http://localhost:8000/agents/${nextId}`);
    setConnected(true);
    setCompleted(0);
    setStarted(false);
    setPlaying(false);
    setView("office");
    setSelectedKey("0-0");
  }

  function startEvaluation() {
    setCompleted(0);
    setStarted(true);
    setPlaying(true);
    setSelectedKey("0-0");
    setView("office");
  }

  function resetEvaluation() {
    setCompleted(0);
    setStarted(false);
    setPlaying(false);
    setView("office");
    setSelectedKey("0-0");
  }

  function finishEvaluation() {
    setCompleted(snapshot.total);
    setStarted(true);
    setPlaying(false);
    setView("results");
  }

  function scrollInspectorWhenStacked() {
    if (!window.matchMedia("(max-width: 1260px)").matches) return;
    window.requestAnimationFrame(() => {
      const inspector = document.getElementById("sandbox-inspector");
      inspector?.focus({ preventScroll: true });
      inspector?.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
        block: "start",
      });
    });
  }

  function focusInspectorAfterViewChange() {
    const stacked = window.matchMedia("(max-width: 1260px)").matches;
    window.requestAnimationFrame(() => {
      const inspector = document.getElementById("sandbox-inspector");
      inspector?.focus({ preventScroll: true });
      if (stacked) {
        inspector?.scrollIntoView({
          behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
          block: "start",
        });
      }
    });
  }

  function inspectTile(tile: EvalTile) {
    setSelectedKey(`${tile.q_idx}-${tile.run_idx}`);
    scrollInspectorWhenStacked();
  }

  function inspectQuestion(qIdx: number) {
    setSelectedKey(`${qIdx}-0`);
    setView("office");
    focusInspectorAfterViewChange();
  }

  function handleViewKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const nextView = event.key === "Home"
      ? "office"
      : event.key === "End"
        ? "results"
        : view === "office" ? "results" : "office";
    setView(nextView);
    window.requestAnimationFrame(() => document.getElementById(`${nextView}-tab`)?.focus());
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <a className="brand" href="#workspace" aria-label="AgentEval Office home">
          <span className="brand-mark" aria-hidden="true">AE</span>
          <span className="brand-copy"><b>AgentEval</b><small>OFFICE</small></span>
        </a>
        <div className="header-progress" aria-label={`Evaluation ${progress}% complete`}>
          <span className="header-progress-copy"><b>{phase === "complete" ? "Evaluation complete" : phase === "running" ? "Evaluation in progress" : "Campus ready"}</b><small>{snapshot.completed} of {snapshot.total} sandboxes</small></span>
          <span className="progress-track"><i style={{ width: `${progress}%` }} /></span>
          <strong>{progress}%</strong>
        </div>
        <div className="header-actions">
          <span className="mock-badge"><i /> MOCK DATA</span>
          <button className="icon-button" type="button" aria-label="Reset evaluation" onClick={resetEvaluation}>↻</button>
        </div>
      </header>

      <div className="workspace" id="workspace">
        <aside className="control-rail" aria-label="Evaluation setup">
          <div className="rail-intro">
            <span className="micro-label">DAYTONA EVALUATION CAMPUS</span>
            <h1>Put your agent<br />to work.</h1>
            <p>Each answer runs inside its own isolated office, so accuracy and consistency become visible.</p>
          </div>

          <section className="setup-section">
            <div className="section-heading"><span>01</span><div><b>Connect agent</b><small>A2A endpoint</small></div></div>
            <label className="url-field">
              <span>Agent URL</span>
              <input value={agentUrl} onChange={(event) => { setAgentUrl(event.target.value); setConnected(false); }} aria-label="Agent URL" />
            </label>
            <button className="connect-button" type="button" onClick={() => setConnected(true)}>{connected ? "Connected" : "Discover agent"}<span>{connected ? "✓" : "→"}</span></button>
            <div className="preset-picker" aria-label="Dummy agent profiles">
              {(Object.keys(AGENTS) as AgentPresetId[]).map((id) => (
                <button key={id} type="button" aria-pressed={agentId === id} onClick={() => selectAgent(id)}>{id}</button>
              ))}
            </div>
            {connected && (
              <article className="agent-card">
                <AgentSprite tone={agent.avatarTone} />
                <div><b>{agent.shortName}</b><span>{agent.name}</span><small><i /> {agent.skill}</small></div>
              </article>
            )}
          </section>

          <section className="setup-section test-set-section">
            <div className="section-heading"><span>02</span><div><b>Test set</b><small>Singapore demo</small></div></div>
            <div className="test-set-card">
              <div><b>{DEMO_SET.length} questions</b><span>× 3 parallel runs</span></div>
              <span className="ready-stamp">READY</span>
            </div>
          </section>

          <div className="rail-actions">
            {phase === "running" ? (
              <button className="primary-action" type="button" onClick={finishEvaluation}>Fast-forward results <span>»</span></button>
            ) : (
              <button className="primary-action" type="button" disabled={!connected} onClick={startEvaluation}>{phase === "complete" ? "Run again" : "Start evaluation"}<span>→</span></button>
            )}
            <p><span /> No API calls — deterministic demo playback</p>
          </div>
        </aside>

        <section className="campus-panel" aria-label="Evaluation workspace">
          <div className="panel-toolbar">
            <div className="view-tabs" role="tablist" aria-label="Evaluation views">
              <button id="office-tab" role="tab" aria-controls="evaluation-panel" aria-selected={view === "office"} tabIndex={view === "office" ? 0 : -1} type="button" onClick={() => setView("office")} onKeyDown={handleViewKeyDown}>Office floor</button>
              <button id="results-tab" role="tab" aria-controls="evaluation-panel" aria-selected={view === "results"} tabIndex={view === "results" ? 0 : -1} type="button" onClick={() => setView("results")} onKeyDown={handleViewKeyDown}>Results grid</button>
            </div>
            <div className="legend" aria-label="Status legend">
              {(["running", "pass", "fail"] as TileStatus[]).map((status) => <span key={status} className={`legend-${status}`}><i />{STATUS_META[status].label}</span>)}
            </div>
          </div>

          <div className="campus-scroll" id="evaluation-panel" role="tabpanel" aria-labelledby={`${view}-tab`}>
            {view === "office" ? (
              <div className="office-campus">
                <div className={`dispatch-lobby lobby-${phase}`}>
                  <div className="lobby-agent"><AgentSprite tone={agent.avatarTone} active={phase === "running"} /><span className="spawn-ring" /></div>
                  <div><span className="micro-label">DISPATCH LOBBY</span><b>{phase === "running" ? `Cloning ${agent.shortName} into isolated workers…` : phase === "complete" ? `${agent.shortName} has completed every assignment.` : `${agent.shortName} is ready for assignment.`}</b></div>
                  <div className="lobby-metric"><strong>{phase === "ready" ? "01" : String(snapshot.completed).padStart(2, "0")}</strong><span>{phase === "ready" ? "agent online" : "sandboxes complete"}</span></div>
                </div>
                <div className="campus-hallway"><i /><span>ISOLATED SANDBOX FLOOR</span><i /></div>

                <div className="question-rooms">
                  {DEMO_SET.map((test, qIdx) => {
                    const roomTiles = snapshot.tiles.filter((tile) => tile.q_idx === qIdx);
                    const roomComplete = roomTiles.filter((tile) => ["pass", "fail", "error"].includes(tile.status)).length;
                    return (
                      <section className="question-room" key={test.question} aria-labelledby={`question-${qIdx}`}>
                        <header className="room-header">
                          <div className="question-number">Q{String(qIdx + 1).padStart(2, "0")}</div>
                          <div><h2 id={`question-${qIdx}`}>{test.question}</h2><span>{roomComplete}/3 runs complete</span></div>
                          <div className={`room-drift ${snapshot.scorecard?.per_question[qIdx].drift ? "has-drift" : ""}`}><small>DRIFT</small><b>{snapshot.scorecard ? snapshot.scorecard.per_question[qIdx].drift.toFixed(2) : "—"}</b></div>
                        </header>
                        <QuestionOffice tiles={roomTiles} selectedKey={selectedKey} tone={agent.avatarTone} onSelect={inspectTile} />
                      </section>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="results-view">
                <div className="score-hero">
                  <div><span className="micro-label">EVALUATION SCORECARD</span><h2>{snapshot.scorecard ? `${snapshot.scorecard.accuracy} questions passed` : "Results are still arriving"}</h2><p>{snapshot.scorecard ? "Every completed sandbox is preserved below for inspection." : "Run or fast-forward the evaluation to generate the final roll-up."}</p></div>
                  <div className="score-dials">
                    <div><span>ACCURACY</span><strong>{snapshot.scorecard ? `${Math.round(snapshot.scorecard.accuracy_pct * 100)}%` : `${progress}%`}</strong><i /></div>
                    <div><span>DRIFT</span><strong>{snapshot.scorecard ? snapshot.scorecard.consistency_drift.toFixed(2) : "—"}</strong><i className="drift-dial" /></div>
                  </div>
                </div>
                <div className="result-table" role="table" aria-label="Evaluation result grid">
                  <div className="result-row result-head" role="row"><span role="columnheader">Question</span><span role="columnheader">Run 1</span><span role="columnheader">Run 2</span><span role="columnheader">Run 3</span><span role="columnheader">Drift</span></div>
                  {DEMO_SET.map((test, qIdx) => (
                    <div className="result-row" role="row" key={test.question}>
                      <div className="result-question-cell" role="cell">
                        <button type="button" onClick={() => inspectQuestion(qIdx)}><b>Q{qIdx + 1}</b><span>{test.question}</span></button>
                      </div>
                      {snapshot.tiles.filter((tile) => tile.q_idx === qIdx).map((tile) => (
                        <div role="cell" key={tile.run_idx} className={`result-cell result-${tile.status}`}>
                          <button type="button" aria-label={`Inspect question ${tile.q_idx + 1}, run ${tile.run_idx + 1}: ${STATUS_META[tile.status].label}, score ${formatScore(tile.score, tile.status)}`} onClick={() => inspectTile(tile)}><ActivityIcon status={tile.status} /><span>{formatScore(tile.score, tile.status)}</span></button>
                        </div>
                      ))}
                      <span
                        role="cell"
                        aria-label={`Question ${qIdx + 1} consistency drift ${snapshot.scorecard ? snapshot.scorecard.per_question[qIdx].drift.toFixed(2) : "not available"}`}
                        className={snapshot.scorecard?.per_question[qIdx].drift ? "drift-value" : ""}
                      >
                        {snapshot.scorecard ? snapshot.scorecard.per_question[qIdx].drift.toFixed(2) : "—"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>

        <aside className="inspector" id="sandbox-inspector" aria-label="Selected sandbox details" tabIndex={-1}>
          <div className="inspector-header"><div><span className="micro-label">SANDBOX INSPECTOR</span><b>Q{selectedTile.q_idx + 1} / RUN {selectedTile.run_idx + 1}</b></div><ActivityIcon status={selectedTile.status} /></div>
          <div className="inspector-status"><span className={`status-label status-${selectedTile.status}`}><b>{STATUS_META[selectedTile.status].symbol}</b>{STATUS_META[selectedTile.status].label}</span><code>{selectedTile.run_id}</code></div>
          <section className="inspector-section"><span className="inspector-label">PROMPT</span><p>{DEMO_SET[selectedTile.q_idx].question}</p></section>
          <section className="inspector-section expected-section"><span className="inspector-label">EXPECTED</span><p>{DEMO_SET[selectedTile.q_idx].expected}</p></section>
          <section className="inspector-section answer-section"><span className="inspector-label">AGENT ANSWER</span>{selectedTile.answer ? <p>“{selectedTile.answer}”</p> : <p className="empty-answer">{selectedTile.status === "running" ? "Agent is composing an answer…" : selectedTile.status === "error" ? "This sandbox ended before returning an answer." : "Waiting for this sandbox to start."}</p>}</section>

          <section className="score-section">
            <div><span className="inspector-label">ACCURACY SCORE</span><strong>{formatScore(selectedTile.score, selectedTile.status)}</strong></div>
            <span className="score-bar"><i style={{ width: `${selectedTile.score * 100}%` }} /></span>
            <p>{selectedTile.reason || (["pass", "fail"].includes(selectedTile.status) ? "No per-run scoring reason was returned." : selectedTile.status === "error" ? "This sandbox ended before a score was produced." : "A scoring reason will appear when this run finishes.")}</p>
          </section>

          <section className="inspector-log" aria-label="Evaluation log">
            <span className="inspector-label">EVALUATION LOG</span>
            <ol>
              <li><i className={selectedTile.status === "pending" ? "" : "log-done"} /><span>{selectedTile.status === "pending" ? "Sandbox queued" : "Sandbox created"}</span><time>{selectedTile.status === "pending" ? "—" : "00:01"}</time></li>
              <li><i className={selectedTile.status === "pending" ? "" : "log-done"} /><span>{selectedTile.status === "pending" ? "Awaiting agent dispatch" : "Agent dispatched"}</span><time>{selectedTile.status === "pending" ? "—" : "00:02"}</time></li>
              <li><i className={["pass", "fail"].includes(selectedTile.status) ? "log-done" : selectedTile.status === "error" ? "log-error" : selectedTile.status === "running" ? "log-live" : ""} /><span>{selectedTile.status === "error" ? "Sandbox failed" : selectedTile.status === "running" ? "Response in progress" : selectedTile.status === "pending" ? "Awaiting response" : "Response scored"}</span><time>{["pass", "fail", "error"].includes(selectedTile.status) ? "00:05" : "—"}</time></li>
            </ol>
          </section>
        </aside>
      </div>

      <div className="sr-live" aria-live="polite">{phase === "running" ? `Evaluation ${progress}% complete.` : phase === "complete" ? "Evaluation complete." : "Evaluation ready."}</div>
    </main>
  );
}
