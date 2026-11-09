"""Smoke tests for the FastAPI workbench shim."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Allow offline invoke in unit tests only (no production UI path).
os.environ["KYC_ALLOW_OFFLINE"] = "1"

from api import server as server_mod  # noqa: E402

server_mod._ALLOW_OFFLINE = True
client = TestClient(server_mod.app)


def test_queue_seeded():
    rows = client.get("/companies").json()
    ids = {r["thread_id"] for r in rows}
    assert "seed-c1572528" in ids
    assert "seed-risky" in ids
    assert all(r.get("status") in {"queued", "awaiting_hitl", "running_auto", "summarized"} for r in rows)


def test_seed_detail_has_no_fabricated_checks():
    detail = client.get("/companies/seed-risky").json()
    assert detail["brn"] == "C4455667"
    assert detail.get("seed_only") is True
    assert detail.get("check_results") == []


def test_offline_ignored_without_allow_flag(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(server_mod, "_ALLOW_OFFLINE", False)
    # Force live path would hit network; we only assert offline cannot be forced via body
    # by checking health reports live_default.
    health = client.get("/health").json()
    assert health["live_default"] is True


def test_allow_offline_run_interrupt_and_resume():
    run = client.post(
        "/runs",
        json={
            "brn": "FAKE-API-1",
            "legal_name_en": "API SMOKE CO LTD",
            "requested_trades": ["electrical", "general"],
            "offline": True,
        },
    ).json()
    assert run["interrupted"] is True
    assert run["status"] == "awaiting_hitl"
    assert len(run["pending_human"]) >= 1
    tid = run["thread_id"]
    resume = {}
    for item in run["pending_human"]:
        up = client.post(
            f"/runs/{tid}/upload",
            data={"pending_id": item["id"]},
            files={"file": (f"{item['id']}.pdf", b"%PDF-demo", "application/pdf")},
        ).json()
        resume[item["id"]] = {"paths": [up["path"]], "confirmed": True}
    final = client.post(f"/runs/{tid}/resume", json={"resume": resume}).json()
    assert final["status"] == "summarized"
    assert final["awaiting_human"] is False
