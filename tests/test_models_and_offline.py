"""Offline unit tests — no live HTTP / no portal scrape."""

from __future__ import annotations

from kyc_agent.graph import build_kyc_graph, run_kyc_check
from kyc_agent.models import (
    CICAdverseInput,
    CRLookupInput,
    TradeKind,
)
from kyc_agent.tools.auto.cic_rstcs_adverse import cic_rstcs_adverse
from kyc_agent.tools.auto.cr_opendata import cr_opendata_lookup
from kyc_agent.tools.semi.cic_rstcs_status import cic_rstcs_status
from kyc_agent.tools.semi.fsd_rfsic import fsd_rfsic_check
from kyc_agent.models import CICRSTCSStatusInput, FSDRFSICInput


def test_cr_offline_skips():
    out, res = cr_opendata_lookup(CRLookupInput(brn="C1572528"), offline=True)
    assert out.found is False
    assert res.status.value == "skipped"


def test_cic_adverse_stub():
    out, res = cic_rstcs_adverse(CICAdverseInput(english_name="DEMO"))
    assert out.stub is True
    assert res.status.value == "stub"


def test_semi_stubs_have_sample_shape():
    _, cic = cic_rstcs_status(CICRSTCSStatusInput(english_name="DEMO CO"))
    assert cic.data["sample_shape"]["registration_no"]
    _, fsd = fsd_rfsic_check(FSDRFSICInput(company_name="DEMO"))
    assert fsd.data["sample_shape"]["classes"]


def test_offline_graph_no_hitl():
    view = run_kyc_check(
        brn="FAKE1234",
        legal_name_en="DEMO BUILDING CO LTD",
        offline=True,
        require_financials=False,
        require_insurance=False,
        require_safety_docs=False,
        require_track_record=False,
        requested_trades=[TradeKind.ELECTRICAL, TradeKind.GENERAL],
        thread_id="test-offline-1",
    )
    assert view["auto_done"] is True
    assert view["semi_done"] is True
    tools = {r["tool"] for r in view["check_results"]}
    assert "cr_opendata_lookup" in tools
    assert "emsd_rec_check" in tools
    assert "ld_osh_convictions" in tools
    assert "cic_rstcs_adverse" in tools


def test_graph_builds():
    app = build_kyc_graph()
    assert app is not None
