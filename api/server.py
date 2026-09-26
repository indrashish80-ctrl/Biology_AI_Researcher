"""
BioSynthetica — FastAPI Backend
Wraps the existing research engine (research_engine.py, ai_router.py) with a
professional JSON + Server-Sent Events API. The legacy Streamlit app stays intact.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import tempfile
import threading
import time
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Dict, List, Optional

# Make root-level engine modules importable from api/server.py
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Virtual 'retrieval' package bridge (same trick app.py uses)
import types  # noqa: E402

if "retrieval" not in sys.modules:
    _pkg = types.ModuleType("retrieval")
    _pkg.__path__ = [str(ROOT)]
    _pkg.__file__ = str(ROOT / "__init__.py")
    sys.modules["retrieval"] = _pkg

from fastapi import FastAPI, HTTPException, UploadFile, File  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi import FastAPI, HTTPException, UploadFile, File  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("biosynthetica")

app = FastAPI(title="BioSynthetica API", version="2.0.0")

# CORS: allow local desktop app / dev server origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------------
# Global state
# ----------------------------------------------------------------------------

JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()
MAX_PAPERS_LIMIT = 8


class InvestigateRequest(BaseModel):
    question: str
    mode: str = "pipeline"          # "pipeline" | "agent"
    max_papers: int = 4
    enable_geo: bool = True


class DatasetMeta(BaseModel):
    group_col: str
    outcome_col: str


def _now() -> float:
    return time.time()


def _get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with JOBS_LOCK:
        return JOBS.get(job_id)


def _update_job(job_id: str, **fields) -> None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return
        job.update(fields)
        job["updated_at"] = _now()


# ----------------------------------------------------------------------------
# Capture engine prints as progress events
# ----------------------------------------------------------------------------

class _EngineLog:
    """Thread-local tee that forwards engine prints to the job's event log."""

    def __init__(self, job_id: str):
        self.job_id = job_id

    def write(self, text: str) -> int:
        text = text.strip()
        if text:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            with JOBS_LOCK:
                job = JOBS.get(self.job_id)
                if job:
                    for ln in lines:
                        # Parse the engine's ASCII banners into step events
                        if set(ln) <= {"=", "-"}:
                            continue
                        job["events"].append({"t": _now(), "text": ln})
                        # Heuristic stage detection
                        low = ln.lower()
                        if "acquiring" in low or "harvest" in low:
                            job["stage"] = "retrieval"
                        elif "processing" in low and "papers" in low:
                            job["stage"] = "analysis"
                        elif "contradiction" in low:
                            job["stage"] = "contradictions"
                        elif "pathway" in low:
                            job["stage"] = "pathways"
                        elif "hypothes" in low:
                            job["stage"] = "hypotheses"
                        elif "audit" in low:
                            job["stage"] = "audit"
        return len(text)

    def flush(self) -> None:
        pass


# ----------------------------------------------------------------------------
# Background job runner
# ----------------------------------------------------------------------------

def _run_job(job_id: str, req: InvestigateRequest, data_path: Optional[str],
             group_col: Optional[str], outcome_col: Optional[str]) -> None:
    try:
        _update_job(job_id, stage="startup", progress=5,
                    message="Initializing AI router and knowledge base...")

        from research_engine import ResearchEngine  # lazy import (heavy)
        from ai_router import AIRouter

        router = AIRouter()
        providers = router.configured_providers()
        if not providers:
            raise RuntimeError(
                "No LLM provider configured. Set GROQ_API_KEY (Settings → Environment) and restart."
            )
        _update_job(job_id, providers=providers)

        _update_job(job_id, stage="engine", progress=10,
                    message="Loading research engine...")

        engine = ResearchEngine(router=router, use_ai=True)
        logger = _EngineLog(job_id)

        report_path = ROOT / f"api_report_{job_id}.md"
        if report_path.exists():  # leftover from a previous run
            report_path.unlink(missing_ok=True)
        try:
            if req.mode == "agent":
                _update_job(job_id, stage="agent", progress=20,
                            message="Deploying autonomous ReAct research agent...")
                with redirect_stdout(logger), redirect_stderr(logger):
                    agent_res = engine.run_agent(question=req.question, max_steps=8,
                                                 output_report=str(report_path))

                fin = agent_res.get("final_synthesis", {}) if isinstance(agent_res, dict) else {}
                report_md = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
                if not report_md:
                    report_md = (
                        "# Autonomous Agent Investigation\n\n"
                        "The agent finalized its synthesis but the report buffer was not written.\n\n"
                        "## Executive Summary\n\n"
                        f"{fin.get('executive_summary', 'The agent completed its review of the primary literature.')}\n\n"
                        "## Key Mechanism\n\n"
                        f"{fin.get('key_mechanism', 'Mechanism reviewed against the evidence.')}"
                    )
                else:
                    report_md = _inject_agent_synthesis(report_md, fin)

                answer = (
                    f"### Investigation Complete\n\n"
                    f"**Executive synthesis:** {fin.get('executive_summary', 'Synthesis finalized.')}\n\n"
                    f"**Key mechanism:** `{fin.get('key_mechanism', 'Mechanism reviewed.')}`\n\n"
                    f"Full report and adversarial audit flags below."
                )
                dossier = {
                    "research_question": req.question,
                    "mode": "agent",
                    "agent_final_synthesis": fin,
                    "status": "agent_complete",
                }
            else:
                _update_job(job_id, stage="retrieval", progress=15,
                            message="Harvesting literature and extracting quote-grounded claims...")
                with redirect_stdout(logger), redirect_stderr(logger):
                    dossier = engine.investigate(
                        question=req.question,
                        experimental_dataset=data_path,
                        exp_group_col=group_col,
                        exp_outcome_col=outcome_col,
                        max_papers=max(2, min(req.max_papers, MAX_PAPERS_LIMIT)),
                        enable_geo=req.enable_geo,
                        output_report=str(report_path),
                    )

                report_md = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
                summary = dossier.get("evidence_summary", {})
                answer = (
                    f"### Deep Research Dossier\n\n"
                    f"- **Papers evaluated:** {dossier.get('papers_analyzed', 0)}\n"
                    f"- **Claims extracted:** {summary.get('claims', 0)}\n"
                    f"- **Contradictions:** {dossier.get('contradiction_summary', {}).get('conflicting_pairs', 0)} conflicting pairs\n"
                    f"- **Falsifiable hypotheses:** {len(dossier.get('hypotheses', []))}\n"
                    f"- **Audit flags:** {len(dossier.get('audit_flags', []))}"
                )

            _update_job(job_id, stage="complete", progress=100, status="complete",
                        message="Investigation complete.",
                        answer=answer, report=report_md, dossier=dossier)
        finally:
            try:
                engine.close()
            except Exception:
                pass
            if report_path.exists():
                report_path.unlink(missing_ok=True)

    except Exception as exc:
        log.exception("Job %s failed", job_id)
        _update_job(job_id, status="error", stage="error", progress=100,
                    message=f"Investigation failed: {exc}")
    finally:
        if data_path:
            try:
                os.unlink(data_path)
            except OSError:
                pass


# ----------------------------------------------------------------------------
# API routes
# ----------------------------------------------------------------------------

def _inject_agent_synthesis(report_md: str, fin: Dict[str, Any]) -> str:
    """Agent-mode reports come from the deterministic report generator (claims,
    hypotheses, gaps, audit flags). Prepend the agent's own executive synthesis
    so the report leads with the AI's answer."""
    if not fin:
        return report_md
    parts: List[str] = ["# Autonomous Agent Investigation", ""]
    if fin.get("executive_summary"):
        parts += ["## Executive Summary", "", str(fin["executive_summary"]).strip(), ""]
    if fin.get("key_mechanism"):
        parts += ["## Key Mechanism", "", str(fin["key_mechanism"]).strip(), ""]
    competing = fin.get("evaluated_competing_explanations") or []
    if competing:
        parts += ["## Competing Explanations Evaluated", ""]
        parts += [f"- {c}" for c in competing]
        parts.append("")
    # Demote the generator's original headings one level so the hierarchy stays clean.
    tail = re.sub(r"^(#{1,3})(?!#) ", r"#\1 ", report_md, flags=re.MULTILINE)
    return "\n".join(parts) + "\n---\n\n" + tail

@app.get("/api/health")
def health() -> Dict[str, Any]:
    groq = bool(os.getenv("GROQ_API_KEY"))
    providers = []
    if groq:
        providers.append("groq")
    if os.getenv("NVIDIA_NIM_API_KEY"):
        providers.append("nvidia")
    if os.getenv("GEMINI_API_KEY"):
        providers.append("gemini")
    return {
        "ok": True,
        "providers": providers,
        "ready": len(providers) > 0,
        "version": "2.0.0",
    }


# ----------------------------------------------------------------------------
# LLM API key management (session-scoped, never persisted or returned)
# ----------------------------------------------------------------------------

class KeyUpdate(BaseModel):
    groq_key: Optional[str] = None
    nvidia_key: Optional[str] = None
    gemini_key: Optional[str] = None


_ENV_MAP = {
    "groq_key": "GROQ_API_KEY",
    "nvidia_key": "NVIDIA_NIM_API_KEY",
    "gemini_key": "GEMINI_API_KEY",
}

# Local keystore so UI-entered keys survive server restarts (gitignored).
_KEYSTORE_PATH = ROOT / ".llm_keys.json"


def _load_keystore() -> None:
    try:
        if _KEYSTORE_PATH.exists():
            saved = json.loads(_KEYSTORE_PATH.read_text(encoding="utf-8"))
            for env_name, value in saved.items():
                if value:
                    os.environ.setdefault(env_name, value)  # real env wins
    except Exception:
        pass


_load_keystore()


@app.get("/api/keys")
def get_keys() -> Dict[str, Any]:
    """Report which providers are configured (booleans only — never values)."""
    return {
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "nvidia": bool(os.getenv("NVIDIA_NIM_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "ready": bool(
            os.getenv("GROQ_API_KEY")
            or os.getenv("NVIDIA_NIM_API_KEY")
            or os.getenv("GEMINI_API_KEY")
        ),
    }


@app.post("/api/keys")
def set_keys(update: KeyUpdate) -> Dict[str, Any]:
    """Store keys in the server process env (and a local keystore so they
    survive restarts). Values are never echoed back to the client."""
    updated = []
    saved: Dict[str, str] = {}
    try:
        if _KEYSTORE_PATH.exists():
            saved = json.loads(_KEYSTORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        saved = {}
    for field, env_name in _ENV_MAP.items():
        value = getattr(update, field)
        if value and value.strip():
            v = value.strip()
            os.environ[env_name] = v
            saved[env_name] = v
            updated.append(env_name)
    try:
        _KEYSTORE_PATH.write_text(json.dumps(saved), encoding="utf-8")
    except Exception:
        pass
    return {"ok": True, "updated": updated, **get_keys()}


@app.delete("/api/keys")
def clear_keys() -> Dict[str, Any]:
    """Disabled: the UI must not be able to wipe server-configured keys.
    Returns the current (unchanged) status so clients stay consistent."""
    return {"ok": False, "error": "key clearing is disabled", **get_keys()}
    return {"ok": True, **get_keys()}


@app.post("/api/dataset")
async def upload_dataset(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload an experimental CSV/XLSX for closed-loop hypothesis testing."""
    suffix = Path(file.filename or "data.csv").suffix
    if suffix.lower() not in (".csv", ".xlsx"):
        raise HTTPException(400, "Only .csv and .xlsx files are supported")

    contents = await file.read()
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 20 MB)")

    meta: Dict[str, Any] = {"filename": file.filename, "rows": None, "columns": []}
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(contents)
    tmp.close()
    meta["path"] = tmp.name

    try:
        if suffix.lower() == ".csv":
            import pandas as pd
            df = pd.read_csv(tmp.name)
            meta["rows"] = int(len(df))
            meta["columns"] = [str(c) for c in df.columns]
    except Exception as exc:
        meta["parse_warning"] = str(exc)

    return meta


class JobRequest(BaseModel):
    question: str
    mode: str = "pipeline"
    max_papers: int = 4
    enable_geo: bool = True
    dataset: Optional[DatasetMeta] = None


@app.post("/api/investigate")
def start_investigation(req: JobRequest) -> Dict[str, Any]:
    question = (req.question or "").strip()
    if len(question) < 8:
        raise HTTPException(400, "Please enter a research question (min 8 chars)")

    # Gate: at least one LLM key must be configured (server env or UI keystore)
    # before any investigation can run. No key material is ever echoed back.
    configured = [
        name
        for name in ("GROQ_API_KEY", "NVIDIA_NIM_API_KEY", "GEMINI_API_KEY")
        if os.getenv(name)
    ]
    if not configured:
        raise HTTPException(
            403,
            "No LLM API key configured. Open the 🔑 keys panel and add at least "
            "one key (Groq, NVIDIA NIM, or Gemini) before running an investigation.",
        )

    job_id = uuid.uuid4().hex[:12]
    ds = req.dataset
    data_path = ds.path if ds else None
    group_col = ds.group_col if ds else None
    outcome_col = ds.outcome_col if ds else None

    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "question": question,
            "mode": req.mode,
            "status": "running",
            "stage": "queued",
            "progress": 0,
            "events": [],
            "created_at": _now(),
            "updated_at": _now(),
        }

    t = threading.Thread(
        target=_run_job,
        args=(job_id, req, data_path, group_col, outcome_col),
        daemon=True,
    )
    t.start()
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> Dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    with JOBS_LOCK:
        return {k: v for k, v in job.items() if k != "events"} | {"event_count": len(job["events"])}


@app.get("/api/jobs/{job_id}/events")
def stream_job_events(job_id: str) -> StreamingResponse:
    """SSE stream of live progress events for a running job."""
    job = _get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    def event_stream():
        cursor = 0
        last_stage = None
        idle = 0
        while True:
            with JOBS_LOCK:
                job = JOBS.get(job_id)
                if job is None:
                    yield f"event: error\ndata: {json.dumps({'error': 'job vanished'})}\n\n"
                    return
                events = job["events"]
                new = events[cursor:]
                cursor = len(events)
                payload = {
                    "status": job["status"],
                    "stage": job["stage"],
                    "progress": job["progress"],
                    "message": job["message"],
                }
                done = job["status"] in ("complete", "error")
            for ev in new:
                yield f"event: log\ndata: {json.dumps({'text': ev['text']})}\n\n"
            if payload["stage"] != last_stage:
                yield f"event: stage\ndata: {json.dumps(payload)}\n\n"
                last_stage = payload["stage"]
            if done:
                yield f"event: done\ndata: {json.dumps(payload)}\n\n"
                return
            idle += 1
            time.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/jobs/{job_id}/result")
def job_result(job_id: str) -> Dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] != "complete":
        raise HTTPException(409, f"Job status is '{job['status']}'")
    with JOBS_LOCK:
        return {
            "question": job["question"],
            "answer": job.get("answer"),
            "report": job.get("report"),
            "dossier": job.get("dossier"),
        }


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str) -> Dict[str, Any]:
    with JOBS_LOCK:
        JOBS.pop(job_id, None)
    return {"ok": True}


# ----------------------------------------------------------------------------
# Optional SPA static serving (production mode)
# ----------------------------------------------------------------------------

DIST = ROOT / "frontend" / "dist"

if DIST.exists():
    from fastapi.staticfiles import StaticFiles

    # API routes registered above take precedence over this catch-all mount.
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="spa")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
