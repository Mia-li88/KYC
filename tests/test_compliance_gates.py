"""Compliance gate semantics mirrored from the workbench evaluator."""

from __future__ import annotations

import json
from pathlib import Path

GATES = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "frontend"
        / "src"
        / "config"
        / "compliance_gates.json"
    ).read_text(encoding="utf-8")
)


def _by_tool(results: list[dict]) -> dict[str, dict]:
    return {r["tool"]: r for r in results}


def _applies(gate: dict, trades: list[str]) -> bool:
    when = gate.get("when") or {}
    if when.get("always"):
        return True
    needed = when.get("trades_any") or []
    return any(t in trades for t in needed)


def evaluate(company: dict) -> tuple[bool, list[str]]:
    trades = company.get("requested_trades") or []
    by = _by_tool(company.get("check_results") or [])
    gaps: list[str] = []
    for gate in GATES["gates"]:
        if not _applies(gate, trades):
            continue
        if gate.get("type") == "hitl_pending":
            pending = [p for p in (company.get("pending_human") or []) if not p.get("resolved")]
            if pending or company.get("awaiting_human"):
                gaps.append(gate["id"])
            continue
        tool = gate["tool"]
        check = by.get(tool)
        if not check:
            gaps.append(gate["id"])
            continue
        status = check.get("status")
        pass_ok = status in (gate.get("pass_statuses") or ["pass"])
        stub_ok = gate.get("allow_stub_pass") and status == "stub"
        fail = status in (gate.get("fail_statuses") or ["fail", "error"])
        unknown = status in (gate.get("unknown_statuses") or [])
        data = check.get("data") or {}
        data_fail = False
        if "require_data" in gate and "match_count_max" in gate["require_data"]:
            count = data.get("match_count")
            if count is None and not stub_ok:
                data_fail = True
            elif isinstance(count, int) and count > gate["require_data"]["match_count_max"]:
                data_fail = True
        if (pass_ok or stub_ok) and not data_fail and not fail:
            continue
        if fail or data_fail or (unknown and gate.get("unknown_as_red")):
            gaps.append(gate["id"])
            continue
        if unknown and not gate.get("unknown_as_red"):
            continue
        if gate.get("unknown_as_red", True):
            gaps.append(gate["id"])
    return bool(gaps), gaps


def test_gates_config_has_required_examples():
    ids = {g["id"] for g in GATES["gates"]}
    assert "cr_live_company" in ids
    assert "emsd_rec_if_electrical" in ids
    assert "ld_osh_no_recent_hits" in ids
    assert "cic_rstcs_if_claimed" in ids
    assert "hitl_docs_confirmed" in ids


def test_red_fixture_is_red():
    company = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "api"
            / "fixtures"
            / "fixture-red-light.json"
        ).read_text(encoding="utf-8")
    )
    red, gaps = evaluate(company)
    assert red
    assert "emsd_rec_if_electrical" in gaps
    assert "ld_osh_no_recent_hits" in gaps


def test_pass_fixture_is_green():
    company = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "api"
            / "fixtures"
            / "fixture-pass-electrical.json"
        ).read_text(encoding="utf-8")
    )
    red, gaps = evaluate(company)
    assert not red, gaps


def test_awaiting_hitl_is_red():
    company = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "api"
            / "fixtures"
            / "fixture-awaiting-hitl.json"
        ).read_text(encoding="utf-8")
    )
    red, gaps = evaluate(company)
    assert red
    assert "hitl_docs_confirmed" in gaps
