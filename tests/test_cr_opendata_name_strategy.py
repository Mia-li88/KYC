"""Regression: CR Comp_name must not use equal; prefer begins_with prefixes."""

from __future__ import annotations

import json

import httpx

from kyc_agent.models import CRCompanyRecord, CRLookupInput
from kyc_agent.tools.auto.cr_opendata import (
    cr_opendata_lookup,
    name_search_prefixes,
    rank_records,
)


def test_name_prefixes_avoid_long_raw_only():
    prefixes = name_search_prefixes("Man Kei Construction Company")
    assert "Man Kei" in prefixes
    # Cleaned without COMPANY suffix should appear
    assert any("Man Kei Construction" == p or p.startswith("Man Kei") for p in prefixes)
    # equal-mode is never encoded here — prefixes are bare strings for begins_with
    assert all(isinstance(p, str) and p for p in prefixes)


def test_rank_prefers_closer_english_name():
    records = [
        CRCompanyRecord(
            brn="1",
            english_company_name="Man Kei Accounting Affairs Limited",
        ),
        CRCompanyRecord(
            brn="2",
            english_company_name="Man Kei Construction Engineering Limited",
        ),
    ]
    ranked = rank_records(records, "Man Kei Construction Company")
    assert ranked[0].brn == "2"


class _CRTransport(httpx.BaseTransport):
    """Simulate CR: Comp_name+equal → 400; begins_with short prefix → 200."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        params = dict(httpx.URL(request.url).params)
        key1 = params.get("query[0][key1]")
        key2 = params.get("query[0][key2]")
        key3 = params.get("query[0][key3]", "")

        if key1 == "Comp_name" and key2 == "equal":
            return httpx.Response(400, text="<!DOCTYPE html> equal not allowed")

        if key1 == "Comp_name" and key2 == "begins_with":
            # Mirror live API: long full names 400; short prefixes 200.
            if key3.lower() in {
                "man kei construction company",
                "man kei construction company limited",
            }:
                return httpx.Response(400, text="<!DOCTYPE html> too long")
            if key3.lower().startswith("man kei"):
                body = [
                    {
                        "Brn": "81310177",
                        "English_Company_Name": "Man Kei Construction Engineering Limited",
                        "Chinese_Company_Name": "萬基建築工程有限公司",
                    },
                    {
                        "Brn": "81506475",
                        "English_Company_Name": "Man Kei Accounting Affairs Limited",
                        "Chinese_Company_Name": "萬機會計事務所有限公司",
                    },
                ]
                return httpx.Response(200, json=body)
            return httpx.Response(200, json=[])

        if key1 == "Brn" and key2 == "equal":
            return httpx.Response(
                200,
                json=[
                    {
                        "Brn": key3,
                        "English_Company_Name": "Example By BRN Limited",
                    }
                ],
            )

        return httpx.Response(500, text="unexpected")


def test_man_kei_name_lookup_uses_begins_with_not_equal():
    transport = _CRTransport()
    with httpx.Client(transport=transport) as client:
        out, res = cr_opendata_lookup(
            CRLookupInput(company_name="Man Kei Construction Company"),
            client=client,
        )
    assert res.status.value == "pass"
    assert out.found is True
    assert out.records[0].english_company_name.startswith("Man Kei Construction")
    # All attempts must be begins_with (or none equal).
    attempts = out.query.get("attempts") or []
    assert attempts
    assert all(a.get("params", {}).get("query[0][key2]") != "equal" for a in attempts)
    assert any(
        a.get("params", {}).get("query[0][key2]") == "begins_with" for a in attempts
    )


def test_brn_preferred_over_name():
    transport = _CRTransport()
    with httpx.Client(transport=transport) as client:
        out, res = cr_opendata_lookup(
            CRLookupInput(
                brn="C1572528",
                company_name="Man Kei Construction Company",
            ),
            client=client,
        )
    assert res.status.value == "pass"
    assert out.found is True
    assert out.records[0].brn == "C1572528"
    attempts = out.query.get("attempts") or []
    assert attempts[0]["mode"] == "brn_equal"


def test_unknown_brn_is_fail_not_pass():
    """User-supplied BRN with empty open-data result must FAIL (not pass)."""

    class EmptyBrnTransport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
            return httpx.Response(200, json=[])

    with httpx.Client(transport=EmptyBrnTransport()) as client:
        out, res = cr_opendata_lookup(
            CRLookupInput(brn="FAKEUSERBRN"),
            client=client,
        )
    assert out.found is False
    assert res.status.value == "fail"
    assert "not sufficient" in res.summary.lower() or "No live company" in res.summary
