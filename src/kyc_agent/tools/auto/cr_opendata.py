"""Companies Registry open-data company lookup (Free API).

Verified endpoints (research 2026-11-05):
  Local:  https://data.cr.gov.hk/cr/api/api/v1/api_builder/json/local/search
  Foreign: https://data.cr.gov.hk/cr/api/api/v1/api_builder/json/foreign/search
  Example: .../local/search?query[0][key1]=Brn&query[0][key2]=equal&query[0][key3]=C1572528&format=json
"""

from __future__ import annotations

from typing import Any, Optional

import httpx

from kyc_agent.models import (
    AccessClass,
    CheckResult,
    CheckStatus,
    CRCompanyRecord,
    CRLookupInput,
    CRLookupOutput,
)

CR_LOCAL_SEARCH = (
    "https://data.cr.gov.hk/cr/api/api/v1/api_builder/json/local/search"
)
SOURCE_DATASET = "https://data.gov.hk/en-data/dataset/hk-cr-crdata-list-addr"


def _build_params(inp: CRLookupInput) -> dict[str, str]:
    if inp.brn:
        return {
            "query[0][key1]": "Brn",
            "query[0][key2]": "equal",
            "query[0][key3]": inp.brn.strip(),
            "format": "json",
        }
    if inp.company_name:
        return {
            "query[0][key1]": "Comp_name",
            "query[0][key2]": inp.name_match or "equal",
            "query[0][key3]": inp.company_name.strip(),
            "format": "json",
        }
    raise ValueError("cr_opendata_lookup requires brn or company_name")


def _normalize_record(row: dict[str, Any]) -> CRCompanyRecord:
    # API may return PascalCase keys as documented
    return CRCompanyRecord(
        brn=row.get("Brn") or row.get("brn"),
        english_company_name=row.get("English_Company_Name")
        or row.get("english_company_name"),
        chinese_company_name=row.get("Chinese_Company_Name")
        or row.get("chinese_company_name"),
        address_of_registered_office=row.get("Address_of_Registered_Office")
        or row.get("address_of_registered_office"),
        company_type=row.get("Company_Type") or row.get("company_type"),
        date_of_incorporation=row.get("Date_of_Incorporation")
        or row.get("date_of_incorporation"),
        re_domiciliation_date=row.get("Re-domiciliation_Date")
        or row.get("re_domiciliation_date"),
        raw=row,
    )


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("data", "Data", "result", "Result", "records", "Records"):
            nested = payload.get(key)
            if isinstance(nested, list):
                return [r for r in nested if isinstance(r, dict)]
            if isinstance(nested, dict):
                for sub in ("data", "Data", "rows", "items"):
                    maybe = nested.get(sub)
                    if isinstance(maybe, list):
                        return [r for r in maybe if isinstance(r, dict)]
        # Single record shaped as object
        if any(k in payload for k in ("Brn", "brn", "English_Company_Name")):
            return [payload]
    return []


def cr_opendata_lookup(
    inp: CRLookupInput,
    *,
    client: Optional[httpx.Client] = None,
    timeout: float = 30.0,
    offline: bool = False,
) -> tuple[CRLookupOutput, CheckResult]:
    """GET CR open-data local search by BRN or company name."""
    if offline:
        out = CRLookupOutput(
            found=False,
            records=[],
            query=inp.model_dump(),
        )
        result = CheckResult(
            tool="cr_opendata_lookup",
            access_class=AccessClass.AUTO,
            status=CheckStatus.SKIPPED,
            summary="Skipped (offline mode)",
            data=out.model_dump(),
            source_urls=[CR_LOCAL_SEARCH, SOURCE_DATASET],
            notes=["Set offline=False to call live CR open data."],
        )
        return out, result

    params = _build_params(inp)
    owns_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        resp = http.get(CR_LOCAL_SEARCH, params=params)
        resp.raise_for_status()
        rows = _extract_rows(resp.json())
        records = [_normalize_record(r) for r in rows]
        out = CRLookupOutput(found=bool(records), records=records, query=params)
        status = CheckStatus.PASS if records else CheckStatus.WARN
        summary = (
            f"Found {len(records)} live company record(s)"
            if records
            else "No live company matched (dissolved/struck-off usually omitted)"
        )
        result = CheckResult(
            tool="cr_opendata_lookup",
            access_class=AccessClass.AUTO,
            status=status,
            summary=summary,
            data=out.model_dump(),
            source_urls=[CR_LOCAL_SEARCH, SOURCE_DATASET],
        )
        return out, result
    except Exception as exc:  # noqa: BLE001 — surface as CheckResult
        out = CRLookupOutput(found=False, records=[], query=params)
        result = CheckResult(
            tool="cr_opendata_lookup",
            access_class=AccessClass.AUTO,
            status=CheckStatus.ERROR,
            summary=f"CR open-data request failed: {exc}",
            data=out.model_dump(),
            source_urls=[CR_LOCAL_SEARCH, SOURCE_DATASET],
            notes=[str(exc)],
        )
        return out, result
    finally:
        if owns_client:
            http.close()
