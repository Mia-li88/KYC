"""FastAPI shim: queue + invoke/resume LangGraph KYC agent with thread_id."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from kyc_agent.graph import build_kyc_graph, _public_view
from kyc_agent.models import TradeKind
from langgraph.types import Command

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
UPLOAD_ROOT = Path(tempfile.gettempdir()) / "kyc-workbench-uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

# Tests only: KYC_ALLOW_OFFLINE=1 lets /runs honor offline=true. Production always live.
_ALLOW_OFFLINE = os.environ.get("KYC_ALLOW_OFFLINE", "").lower() in ("1", "true", "yes")

# Process-wide graph + MemorySaver so thread_id resumes work across requests.
_GRAPH = build_kyc_graph()

# In-memory queue metadata (seeded from fixtures; updated by live runs).
_QUEUE: dict[str, dict[str, Any]] = {}


def _load_fixture_queue() -> None:
    """Seed company list only — not a substitute for live checks."""
    path = FIXTURES_DIR / "queue.json"
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    for row in data:
        entry = dict(row)
        entry["status"] = entry.get("status") if entry.get("status") in {
            "awaiting_hitl",
            "running_auto",
            "summarized",
        } and not entry.get("fixture") else "queued"
        entry["fixture"] = True  # seed row until a live run replaces it
        entry["seed_only"] = True
        _QUEUE[row["thread_id"]] = entry


_load_fixture_queue()

app = FastAPI(title="KYC Workbench API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartRunRequest(BaseModel):
    brn: Optional[str] = None
    legal_name_en: Optional[str] = None
    legal_name_zh: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)
    requested_trades: list[str] = Field(
        default_factory=lambda: [TradeKind.ELECTRICAL.value, TradeKind.GENERAL.value]
    )
    offline: bool = False
    """Ignored unless KYC_ALLOW_OFFLINE=1 (tests). Production always runs live HTTP."""
    require_financials: bool = True
    require_insurance: bool = True
    require_safety_docs: bool = True
    require_track_record: bool = False
    thread_id: Optional[str] = None


class ResumeRequest(BaseModel):
    resume: dict[str, Any] = Field(
        default_factory=dict,
        description="Payload for Command(resume=…), keyed by pending HITL id",
    )


def _interrupt_payload(raw: dict[str, Any]) -> Optional[dict[str, Any]]:
    inter = raw.get("__interrupt__")
    if not inter:
        return None
    first = inter[0]
    value = getattr(first, "value", None)
    if value is None and isinstance(first, dict):
        value = first.get("value")
    return value if isinstance(value, dict) else {"raw": value}


def _queue_status(view: dict[str, Any], interrupted: bool) -> str:
    if interrupted or view.get("awaiting_human"):
        return "awaiting_hitl"
    if view.get("summary"):
        return "summarized"
    if view.get("seed_only") and not view.get("auto_done"):
        return "queued"
    if view.get("auto_done") or view.get("semi_done"):
        return "running_auto"
    return "running_auto"


def _enrich(thread_id: str, raw: dict[str, Any], *, seed_only: bool = False) -> dict[str, Any]:
    interrupt = _interrupt_payload(raw)
    view = dict(raw) if seed_only else _public_view(raw)
    if interrupt:
        pending = interrupt.get("pending")
        if pending is not None:
            view["pending_human"] = pending
        view["awaiting_human"] = True
        if interrupt.get("message"):
            view["interrupt_message"] = interrupt.get("message")
    status = _queue_status({**view, "seed_only": seed_only}, interrupted=bool(interrupt))
    view["thread_id"] = thread_id
    view["status"] = status
    view["interrupted"] = bool(interrupt)
    view["requested_trades"] = raw.get("requested_trades") or view.get("requested_trades") or []
    view["fixture"] = False
    view["seed_only"] = seed_only
    view["live"] = not seed_only
    return view


def _upsert_queue(view: dict[str, Any]) -> None:
    tid = view["thread_id"]
    _QUEUE[tid] = {
        "thread_id": tid,
        "brn": view.get("brn"),
        "legal_name_en": view.get("legal_name_en"),
        "legal_name_zh": view.get("legal_name_zh"),
        "status": view.get("status"),
        "requested_trades": view.get("requested_trades") or [],
        "fixture": False,
        "seed_only": bool(view.get("seed_only")),
        "summary": view.get("summary"),
    }


def _seed_detail(thread_id: str) -> Optional[dict[str, Any]]:
    """Identity-only seed from queue.json — no fabricated check results."""
    row = _QUEUE.get(thread_id)
    if not row:
        return None
    return _enrich(
        thread_id,
        {
            "brn": row.get("brn"),
            "legal_name_en": row.get("legal_name_en"),
            "legal_name_zh": row.get("legal_name_zh"),
            "requested_trades": row.get("requested_trades") or [],
            "check_results": [],
            "pending_human": [],
            "errors": [],
            "summary": None,
            "awaiting_human": False,
            "auto_done": False,
            "semi_done": False,
            "hitl_done": False,
        },
        seed_only=True,
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "live_default": True, "allow_offline": _ALLOW_OFFLINE}


@app.get("/companies")
def list_companies() -> list[dict[str, Any]]:
    """Left-pane queue: BRN / bilingual names / status."""
    rows = list(_QUEUE.values())
    order = {"awaiting_hitl": 0, "running_auto": 1, "queued": 2, "summarized": 3}
    rows.sort(key=lambda r: (order.get(str(r.get("status")), 9), str(r.get("brn") or "")))
    return rows


@app.get("/companies/{thread_id}")
def get_company(thread_id: str) -> dict[str, Any]:
    """Company detail: live graph state, or seed identity only (no fixture results)."""
    config = {"configurable": {"thread_id": thread_id}}
    snap = _GRAPH.get_state(config)
    values = dict(snap.values or {})

    if values or snap.next:
        if snap.next and snap.tasks:
            for task in snap.tasks:
                if task.interrupts:
                    values["__interrupt__"] = list(task.interrupts)
                    break
        view = _enrich(thread_id, values, seed_only=False)
        _upsert_queue(view)
        return view

    seed = _seed_detail(thread_id)
    if seed:
        return seed

    raise HTTPException(404, f"Unknown thread_id={thread_id}")


@app.post("/runs")
def start_run(body: StartRunRequest) -> dict[str, Any]:
    """Always invoke live HTTP tools unless KYC_ALLOW_OFFLINE=1 for tests."""
    if not body.brn and not body.legal_name_en and not body.legal_name_zh:
        raise HTTPException(400, "Provide brn and/or legal_name_en / legal_name_zh")

    offline = bool(body.offline) if _ALLOW_OFFLINE else False

    thread_id = body.thread_id or f"run-{uuid.uuid4().hex[:10]}"
    trades: list[str] = []
    for t in body.requested_trades:
        try:
            trades.append(TradeKind(t).value)
        except ValueError:
            trades.append(str(t))

    initial = {
        "brn": body.brn,
        "legal_name_en": body.legal_name_en,
        "legal_name_zh": body.legal_name_zh,
        "aliases": list(body.aliases),
        "wsd_plumber_nos": [],
        "trade_reg_nos": [],
        "requested_trades": trades,
        "require_financials": body.require_financials,
        "require_insurance": body.require_insurance,
        "require_safety_docs": body.require_safety_docs,
        "require_track_record": body.require_track_record,
        "offline": offline,
        "thread_id": thread_id,
        "check_results": [],
        "errors": [],
        "pending_human": [],
        "human_responses": {},
        "hitl_required": False,
        "awaiting_human": False,
        "auto_done": False,
        "semi_done": False,
        "hitl_done": False,
    }
    config = {"configurable": {"thread_id": thread_id}}
    try:
        raw = _GRAPH.invoke(initial, config=config)
    except Exception as exc:  # network / tool hard failures
        raise HTTPException(
            status_code=502,
            detail=f"Live KYC invoke failed: {type(exc).__name__}: {exc}",
        ) from exc

    view = _enrich(thread_id, dict(raw), seed_only=False)
    # Surface tool-level errors in status messaging for the UI
    errors = list(view.get("errors") or [])
    if errors:
        view["network_errors"] = errors
    _upsert_queue(view)
    return view


@app.post("/runs/{thread_id}/resume")
def resume_run(thread_id: str, body: ResumeRequest) -> dict[str, Any]:
    """Map HITL upload+confirm UI → Command(resume=…)."""
    config = {"configurable": {"thread_id": thread_id}}
    snap = _GRAPH.get_state(config)
    if not snap.next:
        raise HTTPException(400, "Thread is not awaiting resume (no interrupt)")
    try:
        raw = _GRAPH.invoke(Command(resume=body.resume), config=config)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Live KYC resume failed: {type(exc).__name__}: {exc}",
        ) from exc
    view = _enrich(thread_id, dict(raw), seed_only=False)
    _upsert_queue(view)
    return view


@app.post("/runs/{thread_id}/upload")
async def upload_file(
    thread_id: str,
    pending_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Save an uploaded document under a thread/pending folder; return path for resume."""
    dest_dir = UPLOAD_ROOT / thread_id / pending_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = Path(file.filename or "upload.bin").name
    dest = dest_dir / name
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return {"pending_id": pending_id, "path": str(dest), "filename": name}


@app.get("/compliance/gates")
def get_gates() -> dict[str, Any]:
    path = (
        Path(__file__).resolve().parent.parent
        / "frontend"
        / "src"
        / "config"
        / "compliance_gates.json"
    )
    if not path.exists():
        raise HTTPException(404, "compliance_gates.json missing")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    import uvicorn

    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
