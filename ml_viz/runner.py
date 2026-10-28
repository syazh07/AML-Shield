"""Drives ml_pipeline stages as real subprocesses and streams their output.

Deliberately a subprocess driver rather than an in-process import:

* stage filenames start with digits, so they are not importable by name;
* every stage binds `OUT` at import time, so a per-run output dir has to be set
  in the environment before the process starts;
* 04_validate.py mutates 02_score.RANDOM_STATE globally, which would poison a
  long-lived server process;
* `python 0N_x.py --source X` is byte-for-byte what run_all.sh does, so what the
  jury watches is the pipeline itself, not a re-implementation of it.

There is no cached fallback. A stage that fails, fails visibly.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import stages as manifest
from .stages import PIPELINE_DIR, SOURCES, Stage

STAGE_TIMEOUT_S = 180
# Bound the per-run log so a runaway stage cannot exhaust memory.
MAX_LOG_LINES = 4000


@dataclass
class StageSourceState:
    stage_id: str
    source: str
    status: str = "pending"  # pending | running | done | failed | timeout
    started_at: Optional[float] = None
    duration_s: Optional[float] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None
    # tail of stderr, so a failure can say "ModuleNotFoundError: networkx"
    # rather than the useless "exited 1"
    stderr_tail: List[str] = field(default_factory=list)

    def as_json(self) -> Dict[str, Any]:
        return {
            "stage": self.stage_id,
            "source": self.source,
            "status": self.status,
            "duration_s": round(self.duration_s, 2) if self.duration_s else None,
            "exit_code": self.exit_code,
            "error": self.error,
        }


@dataclass
class Run:
    run_id: str
    out_dir: str
    python: str
    created_at: float = field(default_factory=time.time)
    state: Dict[str, StageSourceState] = field(default_factory=dict)
    log: List[Dict[str, Any]] = field(default_factory=list)
    subscribers: List["asyncio.Queue[Dict[str, Any]]"] = field(default_factory=list)
    _running: Optional[str] = None

    # --- state helpers -----------------------------------------------------
    @staticmethod
    def key(stage_id: str, source: str) -> str:
        return f"{stage_id}:{source}"

    def get(self, stage_id: str, source: str) -> StageSourceState:
        return self.state[self.key(stage_id, source)]

    def stage_status(self, stage_id: str) -> str:
        """Collapse the two source states into one chip status for the rail."""
        statuses = {self.get(stage_id, s).status for s in SOURCES}
        for bad in ("failed", "timeout"):
            if bad in statuses:
                return bad
        if "running" in statuses:
            return "running"
        if statuses == {"done"}:
            return "done"
        return "pending"

    def completed_stages(self) -> List[str]:
        return [s for s in manifest.STAGE_IDS if self.stage_status(s) == "done"]

    def next_stage(self) -> Optional[str]:
        for sid in manifest.STAGE_IDS:
            if self.stage_status(sid) != "done":
                return sid
        return None

    def as_json(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "out_dir": self.out_dir,
            "python": self.python,
            "running": self._running,
            "next_stage": self.next_stage(),
            "stages": {
                sid: {
                    "status": self.stage_status(sid),
                    "sources": {s: self.get(sid, s).as_json() for s in SOURCES},
                }
                for sid in manifest.STAGE_IDS
            },
        }

    # --- event bus ---------------------------------------------------------
    def subscribe(self) -> "asyncio.Queue[Dict[str, Any]]":
        q: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()
        self.subscribers.append(q)
        return q

    def unsubscribe(self, q: "asyncio.Queue[Dict[str, Any]]") -> None:
        if q in self.subscribers:
            self.subscribers.remove(q)

    def emit(self, event: Dict[str, Any]) -> None:
        if event.get("type") == "log":
            self.log.append(event)
            if len(self.log) > MAX_LOG_LINES:
                del self.log[: len(self.log) - MAX_LOG_LINES]
        for q in list(self.subscribers):
            q.put_nowait(event)


class RunStore:
    """In-memory run registry. Runs are demo-scoped; nothing is persisted."""

    def __init__(self) -> None:
        self._runs: Dict[str, Run] = {}

    def create(self, python: Optional[str] = None) -> Run:
        run_id = uuid.uuid4().hex[:12]
        out_dir = tempfile.mkdtemp(prefix=f"aml-viz-{run_id}-")
        run = Run(
            run_id=run_id, out_dir=out_dir, python=python or manifest.DEFAULT_PYTHON
        )
        for stage in manifest.STAGES:
            for source in SOURCES:
                run.state[Run.key(stage.id, source)] = StageSourceState(
                    stage.id, source
                )
        self._runs[run_id] = run
        return run

    def get(self, run_id: str) -> Optional[Run]:
        return self._runs.get(run_id)

    def discard(self, run_id: str) -> None:
        run = self._runs.pop(run_id, None)
        if run:
            shutil.rmtree(run.out_dir, ignore_errors=True)


class StageError(Exception):
    """Raised for conditions the caller should turn into a 4xx."""


def _subprocess_env(run: Run) -> Dict[str, str]:
    env = dict(os.environ)
    env["AML_PIPELINE_OUT"] = run.out_dir
    env["PYTHONUNBUFFERED"] = "1"  # otherwise stdout arrives in one lump at exit
    env["MPLBACKEND"] = "Agg"  # headless charts (06_chart sets this too)
    return env


def check_dependencies(run: Run, stage: Stage) -> None:
    """Refuse to run a stage whose inputs were never produced in this run."""
    missing = []
    for source in SOURCES:
        for dep in stage.depends_on.get(source, []):
            if run.get(dep, source).status != "done":
                missing.append(f"{dep}/{source}")
    if missing:
        raise StageError(
            f"stage {stage.id} needs {', '.join(missing)} to run first"
        )


async def _pump(stream: asyncio.StreamReader, run: Run, stage_id: str, source: str,
                channel: str) -> None:
    """Forward one subprocess pipe to the event bus, line by line."""
    while True:
        raw = await stream.readline()
        if not raw:
            return
        if channel == "stderr":
            tail = run.get(stage_id, source).stderr_tail
            text = raw.decode("utf-8", "replace").strip()
            if text:
                tail.append(text)
                del tail[:-8]
        run.emit(
            {
                "type": "log",
                "stage": stage_id,
                "source": source,
                "channel": channel,
                "line": raw.decode("utf-8", "replace").rstrip("\n"),
                "t": round(time.time() - (run.get(stage_id, source).started_at or 0), 2),
            }
        )


async def _run_one(run: Run, stage: Stage, source: str) -> StageSourceState:
    st = run.get(stage.id, source)
    st.status = "running"
    st.started_at = time.time()
    st.duration_s = None
    st.exit_code = None
    st.error = None
    argv = stage.command(run.python, source)
    run.emit({"type": "status", **st.as_json()})
    run.emit(
        {
            "type": "log",
            "stage": stage.id,
            "source": source,
            "channel": "cmd",
            "line": "$ python " + " ".join(argv[1:]),
            "t": 0.0,
        }
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=PIPELINE_DIR,  # load-bearing: stages do a flat `from common import ...`
            env=_subprocess_env(run),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        st.status = "failed"
        st.duration_s = time.time() - st.started_at
        st.error = f"could not launch {run.python}: {exc}"
        run.emit({"type": "status", **st.as_json()})
        return st

    pumps = asyncio.gather(
        _pump(proc.stdout, run, stage.id, source, "stdout"),
        _pump(proc.stderr, run, stage.id, source, "stderr"),
    )
    try:
        st.exit_code = await asyncio.wait_for(proc.wait(), timeout=STAGE_TIMEOUT_S)
        await pumps
        st.status = "done" if st.exit_code == 0 else "failed"
        if st.exit_code != 0:
            # the last stderr line is usually the exception; fall back to the code
            last = st.stderr_tail[-1] if st.stderr_tail else ""
            st.error = f"exited {st.exit_code}" + (f" — {last[:200]}" if last else "")
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        pumps.cancel()
        st.status = "timeout"
        st.error = f"exceeded {STAGE_TIMEOUT_S}s"
    finally:
        st.duration_s = time.time() - st.started_at

    run.emit({"type": "status", **st.as_json()})
    return st


async def run_stage(run: Run, stage_id: str) -> Dict[str, Any]:
    """Execute one stage for both sources concurrently.

    Real and synthetic never write the same filename (the synthetic side is
    suffixed), so sharing one output dir is safe.
    """
    stage = manifest.STAGES_BY_ID.get(stage_id)
    if stage is None:
        raise StageError(f"unknown stage {stage_id!r}")
    if run._running is not None:
        raise StageError(f"stage {run._running} is still running")
    check_dependencies(run, stage)

    run._running = stage_id
    run.emit({"type": "stage_start", "stage": stage_id})
    started = time.time()
    try:
        results = await asyncio.gather(
            *(_run_one(run, stage, source) for source in SOURCES)
        )
    finally:
        run._running = None

    ok = all(r.status == "done" for r in results)
    event = {
        "type": "stage_done",
        "stage": stage_id,
        "ok": ok,
        "duration_s": round(time.time() - started, 2),
        "sources": {r.source: r.as_json() for r in results},
        "next_stage": run.next_stage(),
    }
    run.emit(event)
    return event


def preflight(python: Optional[str] = None) -> Dict[str, Any]:
    """Verify the demo can actually run before anyone is watching."""
    import subprocess

    python = python or manifest.DEFAULT_PYTHON
    checks: List[Dict[str, Any]] = []

    interp_ok = os.path.exists(python) and os.access(python, os.X_OK)
    checks.append(
        {
            "name": "interpreter",
            "ok": interp_ok,
            "detail": python if interp_ok else f"not executable: {python}",
        }
    )

    if interp_ok:
        probe = (
            "import importlib.util,json,sys;"
            "mods=%r;"
            "print(json.dumps({'version':sys.version.split()[0],"
            "'missing':[m for m in mods if importlib.util.find_spec(m) is None]}))"
            % (list(manifest.REQUIRED_MODULES),)
        )
        try:
            raw = subprocess.run(
                [python, "-c", probe], capture_output=True, text=True, timeout=60
            )
            if raw.returncode == 0:
                import json

                info = json.loads(raw.stdout.strip().splitlines()[-1])
                missing = info["missing"]
                checks.append(
                    {
                        "name": "python version",
                        "ok": True,
                        "detail": info["version"],
                    }
                )
                checks.append(
                    {
                        "name": "ml dependencies",
                        "ok": not missing,
                        "detail": "all present: " + ", ".join(manifest.REQUIRED_MODULES)
                        if not missing
                        else "missing: " + ", ".join(missing),
                    }
                )
            else:
                checks.append(
                    {
                        "name": "ml dependencies",
                        "ok": False,
                        "detail": (raw.stderr or "probe failed").strip()[-300:],
                    }
                )
        except (subprocess.SubprocessError, ValueError) as exc:
            checks.append(
                {"name": "ml dependencies", "ok": False, "detail": str(exc)[:300]}
            )

    for label, path in (
        ("real dataset", os.path.join(manifest.DATA_DIR, "mule_sample_data.csv")),
        ("synthetic dataset", os.path.join(manifest.DATA_DIR, "synthetic_scenario.csv")),
        ("pipeline scripts", PIPELINE_DIR),
    ):
        exists = os.path.exists(path)
        checks.append(
            {
                "name": label,
                "ok": exists,
                "detail": os.path.relpath(path, manifest.REPO_ROOT)
                if exists
                else f"missing: {path}",
            }
        )

    return {"ok": all(c["ok"] for c in checks), "python": python, "checks": checks}
