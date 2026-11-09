"""Companies Registry open-data company lookup (Free API).

Verified endpoints (research 2026-11-05):
  Local:  https://data.cr.gov.hk/cr/api/api/v1/api_builder/json/local/search
  Foreign: https://data.cr.gov.hk/cr/api/api/v1/api_builder/json/foreign/search
  Example: .../local/search?query[0][key1]=Brn&query[0][key2]=equal&query[0][key3]=C1572528&format=json

Name lookup notes (2026-11-09):
  Comp_name + ``equal`` → HTTP 400 (HTML error page) even for short names.
  Comp_name + ``begins_with`` + long multi-word names can also 400.
  Working pattern: ``begins_with`` with a short prefix (e.g. first 2–3 tokens),
  then rank candidates against the original query. Prefer BRN when available.
"""

from __future__ import annotations

import re
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

# Legal-form suffixes often appended to HK English names — strip before prefix search.
_NAME_SUFFIX_RE = re.compile(
    r"\b("
    r"LIMITED|LTD\.?|COMPANY|CO\.?|CORPORATION|CORP\.?|"
    r"INCORPORATED|INC\.?|LLC|LLP|PLC|"
    r"有限公司|公司"
    r")\b\.?",
    re.IGNORECASE,
)


def _brn_params(brn: str) -> dict[str, str]:
    return {
        "query[0][key1]": "Brn",
        "query[0][key2]": "equal",
        "query[0][key3]": brn.strip(),
        "format": "json",
    }


def _comp_name_begins_with_params(prefix: str) -> dict[str, str]:
    """Comp_name must use begins_with — equal returns HTTP 400 from CR open data."""
    return {
        "query[0][key1]": "Comp_name",
        "query[0][key2]": "begins_with",
        "query[0][key3]": prefix.strip(),
        "format": "json",
    }


def _normalize_name(name: str) -> str:
    cleaned = _NAME_SUFFIX_RE.sub(" ", name)
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", " ", cleaned, flags=re.UNICODE)
    return " ".join(cleaned.split()).strip()


def name_search_prefixes(company_name: str) -> list[str]:
    """Build begins_with prefixes to try (longest useful → shortest).

    Never returns the raw long multi-word string alone when a shorter prefix
    is safer; always includes a 2-token prefix when possible.
    """
    raw = " ".join(company_name.strip().split())
    normalized = _normalize_name(raw)
    tokens = normalized.split() if normalized else raw.split()
    prefixes: list[str] = []

    def add(value: str) -> None:
        v = value.strip()
        if v and v not in prefixes:
            prefixes.append(v)

    # Prefer cleaned name without legal suffixes (often short enough for API).
    if normalized:
        add(normalized)
    # Token prefixes: 3 then 2 (Man Kei Construction → Man Kei).
    if len(tokens) >= 3:
        add(" ".join(tokens[:3]))
    if len(tokens) >= 2:
        add(" ".join(tokens[:2]))
    elif tokens:
        add(tokens[0])
    # Last resort: first token of original if normalization emptied it.
    if not prefixes and raw:
        add(raw.split()[0])
    return prefixes


def _token_set(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[\w\u4e00-\u9fff]+", text or "")}


def rank_records(
    records: list[CRCompanyRecord], query_name: str
) -> list[CRCompanyRecord]:
    """Prefer English/Chinese names that best overlap the query tokens."""
    q = _token_set(_normalize_name(query_name) or query_name)
    if not q:
        return records

    def score(rec: CRCompanyRecord) -> tuple[int, int, str]:
        en = _token_set(rec.english_company_name or "")
        zh = _token_set(rec.chinese_company_name or "")
        overlap = len(q & en) + len(q & zh)
        # Prefer more overlap, then shorter English name (tighter match).
        en_len = len(rec.english_company_name or "")
        return (-overlap, en_len, rec.brn or "")

    return sorted(records, key=score)


def _normalize_record(row: dict[str, Any]) -> CRCompanyRecord:
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
        if any(k in payload for k in ("Brn", "brn", "English_Company_Name")):
            return [payload]
    return []


def _get_json(
    http: httpx.Client, params: dict[str, str]
) -> tuple[int, Any, str]:
    resp = http.get(CR_LOCAL_SEARCH, params=params)
    text = resp.text
    if resp.status_code >= 400:
        return resp.status_code, None, text[:200]
    try:
        return resp.status_code, resp.json(), text[:200]
    except Exception:
        return resp.status_code, None, text[:200]


def cr_opendata_lookup(
    inp: CRLookupInput,
    *,
    client: Optional[httpx.Client] = None,
    timeout: float = 30.0,
    offline: bool = False,
) -> tuple[CRLookupOutput, CheckResult]:
    """GET CR open-data local search by BRN (preferred) or company name."""
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

    if not inp.brn and not inp.company_name:
        raise ValueError("cr_opendata_lookup requires brn or company_name")

    owns_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=True)
    attempts: list[dict[str, Any]] = []
    records: list[CRCompanyRecord] = []
    used_params: dict[str, str] = {}

    try:
        # 1) Prefer BRN exact match when available.
        if inp.brn and inp.brn.strip():
            params = _brn_params(inp.brn)
            used_params = params
            status, payload, snippet = _get_json(http, params)
            attempts.append(
                {"mode": "brn_equal", "params": params, "http_status": status}
            )
            if status < 400 and payload is not None:
                records = [_normalize_record(r) for r in _extract_rows(payload)]
            elif status >= 400:
                attempts[-1]["error_snippet"] = snippet

        # 2) Name lookup: begins_with only, with progressive prefixes.
        if not records and inp.company_name and inp.company_name.strip():
            for prefix in name_search_prefixes(inp.company_name):
                params = _comp_name_begins_with_params(prefix)
                used_params = params
                status, payload, snippet = _get_json(http, params)
                attempts.append(
                    {
                        "mode": "comp_name_begins_with",
                        "prefix": prefix,
                        "params": params,
                        "http_status": status,
                    }
                )
                if status >= 400:
                    attempts[-1]["error_snippet"] = snippet
                    continue
                if payload is None:
                    continue
                found = [_normalize_record(r) for r in _extract_rows(payload)]
                if found:
                    records = rank_records(found, inp.company_name)
                    break

        out = CRLookupOutput(
            found=bool(records),
            records=records,
            query={**used_params, "attempts": attempts},
        )
        if records:
            top = records[0]
            summary = (
                f"Found {len(records)} live company record(s); "
                f"top={top.english_company_name or top.chinese_company_name} "
                f"(BRN={top.brn})"
            )
            status_enum = CheckStatus.PASS
        elif attempts and all(
            a.get("http_status", 500) >= 400 for a in attempts
        ):
            summary = "CR open-data request failed for all query strategies"
            status_enum = CheckStatus.ERROR
        else:
            summary = (
                "No live company matched (dissolved/struck-off usually omitted)"
            )
            status_enum = CheckStatus.WARN

        notes = [
            "Comp_name uses begins_with only (equal returns HTTP 400).",
            "Prefer BRN when available.",
        ]
        if attempts:
            notes.append(f"attempts={len(attempts)}")

        result = CheckResult(
            tool="cr_opendata_lookup",
            access_class=AccessClass.AUTO,
            status=status_enum,
            summary=summary,
            data=out.model_dump(),
            source_urls=[CR_LOCAL_SEARCH, SOURCE_DATASET],
            notes=notes,
        )
        return out, result
    except Exception as exc:  # noqa: BLE001 — surface as CheckResult
        out = CRLookupOutput(
            found=False,
            records=[],
            query={**used_params, "attempts": attempts},
        )
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
