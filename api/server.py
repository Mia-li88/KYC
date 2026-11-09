"""FastAPI shim: queue + invoke/resume LangGraph KYC agent with thread_id."""

from __future__ import annotations

import json
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

# Process-wide graph + MemorySaver so thread_id resumes work across requests.
_GRAPH = build_kyc_graph()

# In-memory queue metadata (seeded from fixtures; updated by live runs).
_QUEUE: dict[str, dict[str, Any]] = {}


def _load_fixture_queue() -> None:
    path = FIXTURES_DIR / "queue.json"
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    for row in data:
        _QUEUE[row["thread_id"]] = row


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
    offline: bool = True
    require_financials: bool = True
    require_insurance: bool = True
    require_safety_docs: bool = True
    require_track_record: bool = False
    thread_id: Optional[str] = None
    use_fixture: Optional[str] = None
    """If set, load fixture company detail instead of invoking the live graph."""


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
    if view.get("auto_done") and not view.get("semi_done"):
        return "running_auto"
    if view.get("auto_done") or view.get("semi_done"):
        return "running_auto"
    return "running_auto"


def _enrich(thread_id: str, raw: dict[str, Any], *, fixture: bool = False) -> dict[str, Any]:
    interrupt = _interrupt_payload(raw)
    view = _public_view(raw) if not fixture else dict(raw)
    if interrupt:
        # LangGraph interrupt value uses {"message", "pending"}; surface as pending_human.
        pending = interrupt.get("pending")
        if pending is not None:
            view["pending_human"] = pending
        view["awaiting_human"] = True
        if interrupt.get("message"):
            view["interrupt_message"] = interrupt.get("message")
    status = _queue_status(view, interrupted=bool(interrupt))
    view["thread_id"] = thread_id
    view["status"] = status
    view["interrupted"] = bool(interrupt)
    view["requested_trades"] = raw.get("requested_trades") or view.get("requested_trades") or []
    view["fixture"] = fixture
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
        "fixture": bool(view.get("fixture")),
        "summary": view.get("summary"),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/companies")
def list_companies() -> list[dict[str, Any]]:
    """Left-pane queue: BRN / bilingual names / status."""
    rows = list(_QUEUE.values())
    order = {"awaiting_hitl": 0, "running_auto": 1, "summarized": 2}
    rows.sort(key=lambda r: (order.get(str(r.get("status")), 9), str(r.get("brn") or "")))
    return rows


@app.get("/companies/{thread_id}")
def get_company(thread_id: str) -> dict[str, Any]:
    """Company detail: identity + check results (+ interrupt pending)."""
    fixture_path = FIXTURES_DIR / f"{thread_id}.json"
    config = {"configurable": {"thread_id": thread_id}}
    snap = _GRAPH.get_state(config)
    values = dict(snap.values or {})

    # Live graph state wins once the thread has been invoked.
    if values or snap.next:
        if snap.next and snap.tasks:
            for task in snap.tasks:
                if task.interrupts:
                    values["__interrupt__"] = list(task.interrupts)
                    break
        view = _enrich(thread_id, values, fixture=False)
        _upsert_queue(view)
        return view

    if fixture_path.exists():
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        view = _enrich(thread_id, data, fixture=True)
        _upsert_queue(view)
        return view

    raise HTTPException(404, f"Unknown thread_id={thread_id}")


@app.post("/runs")
def start_run(body: StartRunRequest) -> dict[str, Any]:
    """Invoke kyc_agent until HITL interrupt or summarize."""
    if body.use_fixture:
        path = FIXTURES_DIR / f"{body.use_fixture}.json"
        if not path.exists():
            raise HTTPException(404, f"Fixture {body.use_fixture} not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        tid = body.thread_id or body.use_fixture
        view = _enrich(tid, data, fixture=True)
        _upsert_queue(view)
        return view

    if not body.brn and not body.legal_name_en and not body.legal_name_zh:
        raise HTTPException(400, "Provide brn and/or legal_name_en / legal_name_zh")

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
        "offline": body.offline,
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
    raw = _GRAPH.invoke(initial, config=config)
    view = _enrich(thread_id, dict(raw), fixture=False)
    _upsert_queue(view)
    return view


@app.post("/runs/{thread_id}/resume")
def resume_run(thread_id: str, body: ResumeRequest) -> dict[str, Any]:
    """Map HITL upload+confirm UI → Command(resume=…)."""
    config = {"configurable": {"thread_id": thread_id}}
    snap = _GRAPH.get_state(config)
    if not snap.next:
        raise HTTPException(400, "Thread is not awaiting resume (no interrupt)")
    raw = _GRAPH.invoke(Command(resume=body.resume), config=config)
    view = _enrich(thread_id, dict(raw), fixture=False)
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
    path = Path(__file__).resolve().parent.parent / "frontend" / "src" / "config" / "compliance_gates.json"
    if not path.exists():
        raise HTTPException(404, "compliance_gates.json missing")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    import uvicorn

    uvicorn.run("api.server:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
