"""FastAPI app for the ML pipeline visualizer.

Run from the repo root:

    ./.venv/bin/python -m uvicorn ml_viz.server:app --port 8100

then open http://localhost:8100. Localhost demo tool — no auth.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any, AsyncIterator, Dict, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import readers, runner
from . import stages as manifest
from .runner import Run, RunStore, StageError

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")

app = FastAPI(title="AML Shield — ML Pipeline Visualizer", docs_url="/api/docs")
store = RunStore()


@app.middleware("http")
async def no_store(request, call_next):
    """Never cache. Editing style.css and hitting reload must actually show it,
    and a stale app.js during a demo is not a debugging session anyone wants.
    """
    response = await call_next(request)
    if not request.url.path.startswith("/api/run") or "/image/" in request.url.path:
        response.headers["Cache-Control"] = "no-store, must-revalidate"
    return response


def _run_or_404(run_id: str) -> Run:
    run = store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"unknown run {run_id}")
    return run


@app.get("/api/preflight")
def api_preflight() -> Dict[str, Any]:
    return runner.preflight()


@app.get("/api/stages")
def api_stages() -> Dict[str, Any]:
    return manifest.as_json()


@app.post("/api/run")
def api_create_run() -> Dict[str, Any]:
    run = store.create()
    return run.as_json()


@app.get("/api/run/{run_id}")
def api_get_run(run_id: str) -> Dict[str, Any]:
    return _run_or_404(run_id).as_json()


@app.delete("/api/run/{run_id}")
def api_delete_run(run_id: str) -> Dict[str, Any]:
    _run_or_404(run_id)
    store.discard(run_id)
    return {"deleted": run_id}


@app.post("/api/run/{run_id}/step")
async def api_step(
    run_id: str, stage: Optional[str] = Query(default=None)
) -> Dict[str, Any]:
    """Execute one stage for both sources. Blocks until the stage finishes.

    Progress arrives on the SSE channel meanwhile, so the UI does not wait on
    this response to start showing output.
    """
    run = _run_or_404(run_id)
    stage_id = stage or run.next_stage()
    if stage_id is None:
        raise HTTPException(status_code=409, detail="all stages already complete")
    try:
        return await runner.run_stage(run, stage_id)
    except StageError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/run/{run_id}/stage/{stage_id}")
def api_stage_artifacts(run_id: str, stage_id: str) -> Dict[str, Any]:
    run = _run_or_404(run_id)
    if stage_id not in manifest.STAGES_BY_ID:
        raise HTTPException(status_code=404, detail=f"unknown stage {stage_id}")
    return readers.read_stage(run.out_dir, stage_id, run.as_json()["stages"][stage_id])


@app.get("/api/run/{run_id}/image/{filename}")
def api_image(run_id: str, filename: str) -> FileResponse:
    run = _run_or_404(run_id)
    # allowlist against the manifest: no path traversal, no arbitrary reads
    if filename not in manifest.ALL_ARTIFACTS:
        raise HTTPException(status_code=404, detail="not a pipeline artifact")
    path = os.path.join(run.out_dir, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"{filename} not produced yet")
    return FileResponse(path, media_type="image/png")


@app.get("/api/run/{run_id}/events")
async def api_events(run_id: str, request: Request) -> StreamingResponse:
    """Server-sent events: log lines, per-source status, stage completion."""
    run = _run_or_404(run_id)

    async def stream() -> AsyncIterator[bytes]:
        queue = run.subscribe()
        try:
            # replay so a late/reconnecting client still sees the run so far
            yield _sse({"type": "snapshot", "run": run.as_json(), "log": run.log})
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    # an infinite keepalive loop would hold the worker open
                    # forever after the tab closes, which also wedges
                    # `uvicorn --reload`. End the stream once the client is gone.
                    if await request.is_disconnected():
                        return
                    yield b": keepalive\n\n"
                    continue
                yield _sse(event)
        finally:
            run.unsubscribe(queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(payload: Dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode("utf-8")


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
