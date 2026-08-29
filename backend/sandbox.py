"""Daytona sandbox wrapper.

Declarative image: no pre-baked snapshot needed. First `create` call bakes
the image (~30-60s), later calls hit the cache (~1-3s). See README.
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor

from daytona import Daytona, CreateSandboxFromImageParams, Image, Resources


_IMAGE = (
    Image.base("python:3.11-slim")
    .pip_install(["openai>=1.40.0", "deepeval>=1.0.0", "httpx>=0.27.0"])
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
    """Spawn one sandbox, upload worker.py, run it, return the JSON result.

    Returns: {"answer": str, "score": float, "relevancy": float, "reason": str, "error": str | None}
    """
    daytona = _client()
    sandbox = None
    try:
        params = CreateSandboxFromImageParams(
            image=_IMAGE,
            language="python",
            env_vars={
                # DeepEval + openai SDK both read OPENAI_* from env.
                # backend/server.py mirrors NOSANA_* onto these at startup.
                "OPENAI_BASE_URL": os.environ.get("OPENAI_BASE_URL", ""),
                "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
                "NOSANA_MODEL": os.environ.get("NOSANA_MODEL", ""),
            },
            resources=Resources(cpu=1, memory=2),
            auto_stop_interval=0,
            auto_delete_interval=5,  # nuke after 5 min if we forget
        )
        sandbox = daytona.create(params, timeout=120)

        # upload worker source
        sandbox.process.exec(f"mkdir -p /work")
        _upload_text(sandbox, "/work/worker.py", worker_source)

        # config for this run
        cfg = json.dumps({
            "question": question,
            "expected": expected,
            "agent_url": agent_url,
            "run_idx": run_idx,
        })
        _upload_text(sandbox, "/work/config.json", cfg)

        # run
        result = sandbox.process.exec("cd /work && python worker.py")
        # worker writes /work/result.json regardless of success
        try:
            out = sandbox.fs.download_file("/work/result.json")
            return json.loads(out.decode("utf-8"))
        except Exception as e:
            return {
                "answer": "",
                "score": 0.0,
                "relevancy": 0.0,
                "reason": "worker did not write result.json",
                "error": f"{e}\nstdout: {getattr(result, 'result', '')}",
            }
    finally:
        if sandbox is not None:
            try:
                daytona.delete(sandbox)
            except Exception:
                pass


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
    results = list(tasks)  # will fill in-place

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
