# KYC — Hong Kong construction subcontractor screening (LangGraph)

Python + **LangGraph** skeleton for pre-qualifying HK construction subcontractors across **three access patterns**:

| Class | Meaning | Examples |
|---|---|---|
| **Auto** | Free structured HTTP / downloads | CR open data, EMSD REC JSON, LD OSH XML (+ CIC adverse stub) |
| **Semi** | Official portals + human confirm | CIC RSTCS status, FSD RFSIC, WSD plumber, DEVB/BD lists |
| **HITL** | No public data — upload / manual verify | Financials, EC/TPL insurance, Safety Officer / ISO 45001, track record |

Source-of-truth research (endpoints not invented): see project store doc  
`docs/hk-contractor-quals-apis-vs-scraping.md` (architecture: `docs/langgraph-kyc-architecture.md`).

## Layout

```
src/kyc_agent/
  state.py          # typed graph state (BRN, bilingual names, results, HITL flags)
  models.py         # pydantic tool I/O
  graph.py          # Auto → Semi → HITL interrupt → summarize
  tools/auto/       # real HTTP where verified
  tools/semi/       # portal stubs + sample shapes + ToS notes
  tools/hitl/       # document intake / awaiting human
examples/run_demo.py
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run one company check

**Offline / CI-safe** (no live HTTP, Semi stubs, HITL skipped):

```bash
kyc-check --offline --no-hitl --brn FAKE1234 --name-en "DEMO BUILDING CO LTD" --pretty
# or
python -m kyc_agent --offline --no-hitl --brn FAKE1234 --name-en "DEMO BUILDING CO LTD" --pretty
```

**Live Auto feeds** (network required; example BRN from CR open-data docs):

```bash
kyc-check --brn C1572528 --trades electrical,general,fire --pretty
```

When HITL is enabled (default), the graph **interrupts** until you resume with uploads, e.g.:

```bash
# First call pauses at HITL. Then resume on same thread:
kyc-check --thread-id my-run --resume-json '{"skip_hitl": true}' --pretty
```

Full interrupt → upload → resume walkthrough:

```bash
python examples/run_demo.py --offline
python examples/run_demo.py --brn C1572528   # live
```

## Notes

- Semi tools are **stubs** on purpose: Cloudflare / ASP.NET / PDPO. Interfaces + sample response shapes are ready for adapters.
- Do **not** scrape Cloudflare-heavy CIC / IA sites in CI.
- Prefer `httpx` + pydantic; pin `langgraph` / `langchain-core` via `pyproject.toml`.
