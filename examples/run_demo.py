#!/usr/bin/env python3
"""Demo: Auto → Semi → HITL interrupt → resume for one company.

Usage (from repo root, after pip install -e .):

  # Offline skeleton (no live HTTP) — good for CI
  python examples/run_demo.py --offline

  # Live CR / EMSD / LD feeds (network required)
  python examples/run_demo.py --brn C1572528

  # Fake BRN offline
  python examples/run_demo.py --offline --brn FAKE1234 --name-en "DEMO BUILDING CO LTD"
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from langgraph.types import Command

from kyc_agent.graph import build_kyc_graph
from kyc_agent.models import TradeKind


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brn", default="C1572528")
    parser.add_argument("--name-en", default=None)
    parser.add_argument("--name-zh", default=None)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    app = build_kyc_graph()
    thread = {"configurable": {"thread_id": "example-demo"}}

    initial = {
        "brn": args.brn,
        "legal_name_en": args.name_en,
        "legal_name_zh": args.name_zh,
        "aliases": [],
        "wsd_plumber_nos": [],
        "trade_reg_nos": [],
        "requested_trades": [
            TradeKind.ELECTRICAL.value,
            TradeKind.GENERAL.value,
            TradeKind.FIRE.value,
        ],
        "require_financials": True,
        "require_insurance": True,
        "require_safety_docs": True,
        "require_track_record": True,
        "offline": args.offline,
        "check_results": [],
        "errors": [],
        "pending_human": [],
        "human_responses": {},
    }

    print("=== invoke (expect HITL interrupt) ===")
    try:
        state = app.invoke(initial, config=thread)
        print(json.dumps({"summary": state.get("summary"), "awaiting": state.get("awaiting_human")}, ensure_ascii=False, indent=2))
    except Exception as exc:  # GraphInterrupt may surface depending on version
        # LangGraph 1.x raises GraphInterrupt or returns __interrupt__ in state
        print(f"(interrupt path) {type(exc).__name__}: {exc}")

    snap = app.get_state(thread)
    print("next:", snap.next)
    inter = snap.tasks
    print("tasks:", inter)

    # Create fake upload paths to demonstrate resume
    with tempfile.TemporaryDirectory() as tmp:
        fin = Path(tmp) / "financials.pdf"
        ins = Path(tmp) / "insurance.pdf"
        so = Path(tmp) / "safety_officer.pdf"
        iso = Path(tmp) / "iso45001.pdf"
        tr = Path(tmp) / "track_record.pdf"
        for p in (fin, ins, so, iso, tr):
            p.write_bytes(b"%PDF-fake-demo")

        resume = {
            "hitl_financials": {"paths": [str(fin)], "confirmed": True},
            "hitl_insurance": {"paths": [str(ins)], "confirmed": True},
            "hitl_safety_officer": {"paths": [str(so)], "confirmed": True},
            "hitl_iso_45001": {"paths": [str(iso)], "confirmed": True},
            "hitl_track_record": {"paths": [str(tr)], "confirmed": True},
        }
        print("=== resume HITL ===")
        final = app.invoke(Command(resume=resume), config=thread)
        view = {
            "brn": final.get("brn"),
            "legal_name_en": final.get("legal_name_en"),
            "legal_name_zh": final.get("legal_name_zh"),
            "summary": final.get("summary"),
            "awaiting_human": final.get("awaiting_human"),
            "n_checks": len(final.get("check_results") or []),
            "tools": [
                (r.tool if hasattr(r, "tool") else r.get("tool"),
                 r.status.value if hasattr(r, "status") else r.get("status"))
                for r in (final.get("check_results") or [])
            ],
        }
        print(json.dumps(view, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
