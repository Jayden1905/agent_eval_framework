"""Daytona sandbox wrapper — Option E: sandbox owns the untrusted A2A hop.

Each tile spawns a sandbox that only calls the user's agent (isolated network).
Backend scores the returned answer via DeepEval afterwards, because Nosana's
ingress blocks Daytona egress and moving the judge inside the sandbox needs
Nosana on the domain_allow_list too — a change we may add later.

Declarative image: no pre-baked snapshot needed. First `create` call bakes
the image (~30-60s), later calls hit the cache (~1-3s). See README.
"""
from __future__ import annotations

import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from daytona import Daytona, CreateSandboxFromImageParams, Image, Resources


_IMAGE = (
    Image.base("python:3.11-slim")
    .pip_install(["httpx>=0.27.0"])
)


def _client() -> Daytona:
    return Daytona()


def run_worker_in_sandbox(
    question: str,
    expected: str,
    agent_url: str,
    run_idx: int,
    worker_source: str,
) -> dict:
    """Spawn one sandbox → agent call → backend scoring. Returns tile result.

    Returns: {"answer": str, "score": float, "relevancy": float, "reason": str, "error": str | None}
    """
    from backend import judge  # local import to avoid a2a_client → sandbox cycles

    agent_host = urllib.parse.urlparse(agent_url).hostname or ""

    daytona = _client()
    sandbox = None
    answer = ""
    worker_reason = ""
    worker_error: str | None = None
    try:
        params = CreateSandboxFromImageParams(
            image=_IMAGE,
            language="python",
            # Worker is tiny — one httpx call, no ML libs. 1 GiB is plenty and
            # keeps us under the Daytona free tier's 10 GiB total-memory cap.
            resources=Resources(cpu=1, memory=1),
            auto_stop_interval=0,
            auto_delete_interval=5,
            # Only the agent's host is reachable from inside the sandbox.
            # Nosana host is NOT allowlisted here because the judge runs on
            # backend, not in the sandbox — see module docstring.
            domain_allow_list=agent_host,
        )
        sandbox = daytona.create(params, timeout=180)

        sandbox.process.exec("mkdir -p /work")
        _upload_text(sandbox, "/work/worker.py", worker_source)
        _upload_text(sandbox, "/work/config.json", json.dumps({
            "question": question,
            "agent_url": agent_url,
            "run_idx": run_idx,
        }))

        result = sandbox.process.exec("cd /work && python worker.py")
        try:
            out = sandbox.fs.download_file("/work/result.json")
            worker_result = json.loads(out.decode("utf-8"))
        except Exception as e:
            return {
                "answer": "",
                "score": 0.0,
                "relevancy": 0.0,
                "reason": "worker did not write result.json",
                "error": f"{e}\nstdout: {getattr(result, 'result', '')}",
            }

        answer = worker_result.get("answer", "") or ""
        worker_reason = worker_result.get("reason", "") or ""
        worker_error = worker_result.get("error")
    finally:
        if sandbox is not None:
            try:
                daytona.delete(sandbox)
            except Exception:
                pass

    if worker_error:
        return {
            "answer": answer,
            "score": 0.0,
            "relevancy": 0.0,
            "reason": worker_reason or "agent call failed",
            "error": worker_error,
        }

    # Score on backend — Nosana reachable from here, but not from sandbox.
    try:
        acc, rel, reason = judge.score_tile(question, expected, answer)
    except Exception as e:
        # DeepEval sometimes raises exceptions with empty str(e); include the
        # type so the tile's reason is never just "scoring failed: ".
        detail = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
        return {
            "answer": answer,
            "score": 0.0,
            "relevancy": 0.0,
            "reason": f"scoring failed: {detail}",
            "error": detail,
        }
    return {
        "answer": answer,
        "score": acc,
        "relevancy": rel,
        "reason": reason,
        "error": None,
    }


def fan_out(
    tasks: list[dict],
    worker_source: str,
    max_workers: int = 15,
    on_tile_done=None,
) -> list[dict]:
    """Run many (question, run_idx) tasks in parallel across sandboxes.

    tasks: [{"q_idx": 0, "run_idx": 0, "question": "...", "expected": "...", "agent_url": "..."}, ...]

    Returns the same list with each dict updated with the worker's result.
    on_tile_done(tile) called after each completion so the UI can update.
    """
    results = list(tasks)

    def _run(idx: int) -> tuple[int, dict]:
        t = tasks[idx]
        res = run_worker_in_sandbox(
            question=t["question"],
            expected=t["expected"],
            agent_url=t["agent_url"],
            run_idx=t["run_idx"],
            worker_source=worker_source,
        )
        return idx, res

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_run, i) for i in range(len(tasks))]
        for f in futures:
            idx, res = f.result()
            results[idx] = {**results[idx], **res}
            if on_tile_done is not None:
                on_tile_done(results[idx])
    return results


def _upload_text(sandbox, dest: str, content: str) -> None:
    from daytona import FileUpload
    sandbox.fs.upload_files([FileUpload(source=content.encode("utf-8"), destination=dest)])
