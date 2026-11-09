"""Smoke tests for the FastAPI workbench shim."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


def test_queue_seeded():
    rows = client.get("/companies").json()
    ids = {r["thread_id"] for r in rows}
    assert "fixture-pass-electrical" in ids
    assert "fixture-red-light" in ids
    assert "fixture-awaiting-hitl" in ids


def test_fixture_detail():
    detail = client.get("/companies/fixture-red-light").json()
    assert detail["brn"] == "C4455667"
    assert detail["check_results"]


def test_offline_run_interrupt_and_resume():
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
