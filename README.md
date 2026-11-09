# KYC — Hong Kong construction subcontractor screening (LangGraph)

Python + **LangGraph** agent plus a **three-pane review workbench** for pre-qualifying HK construction subcontractors across **Auto / Semi / HITL** access patterns.

| Class | Meaning | Examples |
|---|---|---|
| **Auto** | Free structured HTTP / downloads | CR open data, EMSD REC JSON, LD OSH XML (+ CIC adverse stub) |
| **Semi** | Official portals + human confirm | CIC RSTCS status, FSD RFSIC, WSD plumber, DEVB/BD lists |
| **HITL** | No public data — upload / manual verify | Financials, EC/TPL insurance, Safety Officer / ISO 45001, track record |

Source-of-truth research (endpoints not invented): see project store docs  
`docs/hk-contractor-quals-apis-vs-scraping.md` · `docs/langgraph-kyc-architecture.md` · `docs/kyc-workbench-frontend.md`.

## Layout

```
src/kyc_agent/          # LangGraph graph + tools
api/                    # FastAPI shim (invoke / resume / fixtures)
frontend/               # Vite React workbench (queue · detail · HITL)
examples/run_demo.py
```

## Setup (backend + frontend)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,api]"

cd frontend && npm install && cd ..
```

## Run frontend + backend together

**Terminal A — API (LangGraph + fixtures):**

```bash
source .venv/bin/activate
uvicorn api.server:app --reload --host 127.0.0.1 --port 8000
```

**Terminal B — Workbench UI:**

```bash
cd frontend && npm run dev
```

Open http://127.0.0.1:5173 — Vite proxies `/companies`, `/runs`, … to the API.

Demo fixtures load automatically (pass / awaiting HITL / 红灯). Use **Start check** to invoke the real offline graph (HITL interrupt → upload → Confirm & resume → `Command(resume=…)`).

### Compliance / 红灯

Editable gates live in `frontend/src/config/compliance_gates.json` (not hard-coded in JSX). After checks run, the UI marks **达标** vs **欠缺**. Missing / failed / unknown required items → **红灯** immediately; pending HITL docs stay red until confirmed. Gap list cites which tool proved each gap.

## CLI (agent only)

**Offline / CI-safe:**

```bash
kyc-check --offline --no-hitl --brn FAKE1234 --name-en "DEMO BUILDING CO LTD" --pretty
```

**Live Auto feeds:**

```bash
kyc-check --brn C1572528 --trades electrical,general,fire --pretty
```

HITL interrupt resume:

```bash
kyc-check --thread-id my-run --resume-json '{"skip_hitl": true}' --pretty
python examples/run_demo.py --offline
```

## Notes

- Semi tools are **stubs** on purpose: Cloudflare / ASP.NET / PDPO. Interfaces + sample shapes are ready for adapters.
- Do **not** scrape Cloudflare-heavy CIC / IA sites in CI.
- Prefer `httpx` + pydantic; pin `langgraph` / `langchain-core` via `pyproject.toml`.
