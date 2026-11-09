"""Smoke tests for the FastAPI workbench shim (no HITL upload path)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ["KYC_ALLOW_OFFLINE"] = "1"

from api import server as server_mod  # noqa: E402

server_mod._ALLOW_OFFLINE = True
client = TestClient(server_mod.app)


def test_queue_seeded():
    rows = client.get("/companies").json()
    ids = {r["thread_id"] for r in rows}
    assert "seed-c1572528" in ids
    assert "seed-risky" in ids


def test_seed_detail_has_no_fabricated_checks():
    detail = client.get("/companies/seed-risky").json()
    assert detail["brn"] == "C4455667"
    assert detail.get("seed_only") is True
    assert detail.get("check_results") == []


def test_offline_ignored_without_allow_flag(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(server_mod, "_ALLOW_OFFLINE", False)
    health = client.get("/health").json()
    assert health["live_default"] is True


def test_allow_offline_run_completes_without_hitl():
    run = client.post(
        "/runs",
        json={
            "brn": "FAKE-API-1",
            "legal_name_en": "API SMOKE CO LTD",
            "requested_trades": ["electrical", "general"],
            "offline": True,
        },
    ).json()
    assert run.get("interrupted") is not True
    assert run["status"] == "summarized"
    assert run.get("awaiting_human") is not True
    tools = {r["tool"] for r in (run.get("check_results") or [])}
    assert "cr_opendata_lookup" in tools
    assert not any(r.get("access_class") == "hitl" for r in (run.get("check_results") or []))
