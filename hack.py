"""AgentEval — Streamlit UI.

Dev 1 owns this file. During Phase 1 use `platform.mocks` for both `discover_agent`
and `get_eval_status`; swap to `platform.eval` once Dev 2 lands the real impl.

To switch: change the two imports below.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# ---- SWAP THIS LINE IN PHASE 3 ------------------------------------
# Dev 1 starts on mocks — no anthropic/daytona/deepeval deps needed.
# Flip to `backend import eval as api` once Dev 2's real backend is green.
from backend import mocks as api
# from backend import eval as api
# -------------------------------------------------------------------

load_dotenv()

st.set_page_config(page_title="AgentEval", layout="wide")

st.title("AgentEval")
st.caption("Bring your agent. We tell you if it's trustworthy.")

# ---- 1. Connect agent ---------------------------------------------
st.subheader("1. Connect your agent")
url = st.text_input("A2A endpoint URL", value="http://127.0.0.1:8001", key="agent_url")

if "card" not in st.session_state:
    st.session_state.card = None

if st.button("Discover"):
    try:
        st.session_state.card = api.discover_agent(url)
    except Exception as e:
        st.error(f"Discovery failed: {e}")
        st.session_state.card = None

if st.session_state.card:
    with st.container(border=True):
        st.markdown(f"**{st.session_state.card.get('name', '(unnamed agent)')}**")
        st.caption(st.session_state.card.get("description", ""))
        skills = st.session_state.card.get("skills", [])
        if skills:
            st.markdown("**Skills**")
            for s in skills:
                st.markdown(f"- **{s.get('name', '')}** — {s.get('description', '')}")

# ---- 2. Test set ---------------------------------------------------
st.subheader("2. Test set")

if "test_set" not in st.session_state:
    st.session_state.test_set = None

col_a, col_b = st.columns(2)
with col_a:
    if st.button("Load demo set (Singapore trivia)"):
        demo_path = Path(__file__).parent / "demo_set.jsonl"
        st.session_state.test_set = [json.loads(l) for l in demo_path.read_text().strip().splitlines()]
with col_b:
    uploaded = st.file_uploader("Or upload a JSONL test set", type=["jsonl"])
    if uploaded is not None:
        st.session_state.test_set = [json.loads(l) for l in uploaded.getvalue().decode().strip().splitlines()]

if st.session_state.test_set:
    st.caption(f"Loaded {len(st.session_state.test_set)} questions")
    for i, item in enumerate(st.session_state.test_set):
        st.markdown(f"**Q{i+1}.** {item['question']}")

# ---- 3. Run eval ---------------------------------------------------
st.subheader("3. Evaluate")

runs_per_q = st.slider("Runs per question (for consistency)", 1, 5, 3)

if "eval_id" not in st.session_state:
    st.session_state.eval_id = None

can_run = st.session_state.card is not None and st.session_state.test_set is not None
if st.button("Run eval", disabled=not can_run, type="primary"):
    st.session_state.eval_id = api.start_eval(
        agent_url=url,
        test_set=st.session_state.test_set,
        runs_per_q=runs_per_q,
    )

# ---- 4. Live grid + scorecard --------------------------------------
if st.session_state.eval_id:
    st.subheader("4. Results")
    grid_area = st.empty()
    score_area = st.empty()

    while True:
        status = api.get_eval_status(st.session_state.eval_id)

        with grid_area.container():
            _render_grid_placeholder = None
            for q_idx, item in enumerate(st.session_state.test_set):
                cols = st.columns([3] + [1] * runs_per_q)
                cols[0].markdown(f"**Q{q_idx+1}.** {item['question'][:80]}")
                for run_idx in range(runs_per_q):
                    tile = next(
                        (t for t in status["tiles"] if t["q_idx"] == q_idx and t["run_idx"] == run_idx),
                        None,
                    )
                    if tile is None:
                        cols[run_idx + 1].markdown("·")
                        continue
                    icon = {"pending": "⚪", "running": "🟡", "pass": "🟢", "fail": "🔴", "error": "❌"}.get(tile["status"], "?")
                    label = f"{icon} {tile['score']:.2f}" if tile["status"] in ("pass", "fail") else icon
                    with cols[run_idx + 1]:
                        st.markdown(label)
                        if tile["answer"]:
                            st.caption(tile["answer"][:80] + ("…" if len(tile["answer"]) > 80 else ""))

        if status["scorecard"] is not None:
            sc = status["scorecard"]
            with score_area.container():
                st.subheader("Scorecard")
                c1, c2 = st.columns(2)
                c1.metric("Accuracy", sc["accuracy"], f"{sc['accuracy_pct']*100:.0f}%")
                drift_label = (
                    "🟢 Rock solid" if sc["consistency_drift"] < 0.01
                    else "🟡 Occasional drift" if sc["consistency_drift"] < 0.34
                    else "🔴 Unreliable"
                )
                c2.metric("Consistency drift", f"{sc['consistency_drift']:.2f}", drift_label)

                st.markdown("**Per question**")
                st.dataframe(
                    [
                        {
                            "Q": q["q_idx"] + 1,
                            "Question": st.session_state.test_set[q["q_idx"]]["question"][:60],
                            "Accuracy": f"{q['acc']:.2f}",
                            "Drift": f"{q['drift']:.2f}",
                            "Reason": q["reason"],
                        }
                        for q in sc["per_question"]
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
            break

        time.sleep(0.5)
