"""EMSD Registered Electrical Contractor check (Free JSON download).

Verified (research 2026-11-05):
  JSON: https://www.emsd.gov.hk/filemanager/en/content_458/dataset/registered_electrical_contractor.json
  XLSX: https://www.emsd.gov.hk/filemanager/en/content_458/dataset/registered_electrical_contractor.xlsx
  Dataset: https://data.gov.hk/en-data/dataset/hk-emsd-emsd1-registered-electrical-contractors
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Optional

import httpx

from kyc_agent.models import (
    AccessClass,
    CheckResult,
    CheckStatus,
    EMSDRecInput,
    EMSDRecOutput,
    EMSDRecRecord,
)

EMSD_JSON_URL = (
    "https://www.emsd.gov.hk/filemanager/en/content_458/dataset/"
    "registered_electrical_contractor.json"
)
SOURCE_DATASET = (
    "https://data.gov.hk/en-data/dataset/hk-emsd-emsd1-registered-electrical-contractors"
)

_REG_NO_KEYS = (
    "Registered Electrical Contractor No.",
    "Registered Electrical Contractor No",
    "registration_no",
)
_EN_KEYS = ("English Name", "english_name", "EnglishName")
_ZH_KEYS = ("Chinese Name", "chinese_name", "ChineseName")
_EXPIRY_KEYS = ("Expiry Date", "expiry_date", "ExpiryDate")
_ADDR_KEYS = ("Address", "address")
_TEL_KEYS = ("Telephone", "telephone")


def _get_first(row: dict[str, Any], keys: tuple[str, ...]) -> Optional[str]:
    for key in keys:
        val = row.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


def _disciplinary_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    for key, val in row.items():
        if "Disciplinary" in str(key) and val not in (None, "", []):
            flags.append(f"{key}={val}")
    return flags


def _normalize(row: dict[str, Any]) -> EMSDRecRecord:
    return EMSDRecRecord(
        registration_no=_get_first(row, _REG_NO_KEYS),
        english_name=_get_first(row, _EN_KEYS),
        chinese_name=_get_first(row, _ZH_KEYS),
        expiry_date=_get_first(row, _EXPIRY_KEYS),
        address=_get_first(row, _ADDR_KEYS),
        telephone=_get_first(row, _TEL_KEYS),
        disciplinary_flags=_disciplinary_flags(row),
        raw=row,
    )


def _rows_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("data", "Data", "records", "features"):
            nested = payload.get(key)
            if isinstance(nested, list):
                # GeoJSON-ish: features[].properties
                out: list[dict[str, Any]] = []
                for item in nested:
                    if isinstance(item, dict) and "properties" in item:
                        props = item["properties"]
                        if isinstance(props, dict):
                            out.append(props)
                    elif isinstance(item, dict):
                        out.append(item)
                return out
        # Some EMSD dumps wrap under Header/Data style
        if "Header" in payload and isinstance(payload.get("data"), list):
            return [r for r in payload["data"] if isinstance(r, dict)]
    return []


@lru_cache(maxsize=1)
def _cached_index_bytes(url: str, body: bytes) -> tuple[EMSDRecRecord, ...]:
    # body is part of cache key so refreshed downloads invalidate
    payload = json.loads(body.decode("utf-8"))
    return tuple(_normalize(r) for r in _rows_from_payload(payload))


def _load_index(
    client: httpx.Client, *, force_url: str = EMSD_JSON_URL
) -> list[EMSDRecRecord]:
    resp = client.get(force_url)
    resp.raise_for_status()
    return list(_cached_index_bytes(force_url, resp.content))


def _norm_name(value: Optional[str]) -> str:
    return " ".join((value or "").casefold().split())


def _match(inp: EMSDRecInput, records: list[EMSDRecRecord]) -> list[EMSDRecRecord]:
    hits: list[EMSDRecRecord] = []
    reg = (inp.registration_no or "").strip()
    targets = {
        _norm_name(inp.english_name),
        _norm_name(inp.chinese_name),
        *{_norm_name(a) for a in inp.aliases},
    }
    targets.discard("")

    for rec in records:
        if reg and (rec.registration_no or "").strip() == reg:
            hits.append(rec)
            continue
        names = {_norm_name(rec.english_name), _norm_name(rec.chinese_name)}
        names.discard("")
        if targets & names:
            hits.append(rec)
    return hits


def emsd_rec_check(
    inp: EMSDRecInput,
    *,
    client: Optional[httpx.Client] = None,
    timeout: float = 60.0,
    offline: bool = False,
) -> tuple[EMSDRecOutput, CheckResult]:
    """Download EMSD REC JSON (or use cache) and match by name / reg no."""
    if offline:
        out = EMSDRecOutput(registered=False, matches=[])
        result = CheckResult(
            tool="emsd_rec_check",
            access_class=AccessClass.AUTO,
            status=CheckStatus.SKIPPED,
            summary="Skipped (offline mode)",
            data=out.model_dump(),
            source_urls=[EMSD_JSON_URL, SOURCE_DATASET],
        )
        return out, result

    owns_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        records = _load_index(http)
        matches = _match(inp, records)
        out = EMSDRecOutput(registered=bool(matches), matches=matches)
        status = CheckStatus.PASS if matches else CheckStatus.WARN
        disc = sum(1 for m in matches if m.disciplinary_flags)
        summary = (
            f"Matched {len(matches)} REC record(s); {disc} with disciplinary gazette fields"
            if matches
            else "No EMSD Registered Electrical Contractor match"
        )
        result = CheckResult(
            tool="emsd_rec_check",
            access_class=AccessClass.AUTO,
            status=status,
            summary=summary,
            data={
                "registered": out.registered,
                "matches": [m.model_dump(exclude={"raw"}) for m in matches],
                "index_size": len(records),
            },
            source_urls=[EMSD_JSON_URL, SOURCE_DATASET],
            notes=["Prefer daily download → local index in production."],
        )
        return out, result
    except Exception as exc:  # noqa: BLE001
        out = EMSDRecOutput(registered=False, matches=[])
        result = CheckResult(
            tool="emsd_rec_check",
            access_class=AccessClass.AUTO,
            status=CheckStatus.ERROR,
            summary=f"EMSD REC download/match failed: {exc}",
            data=out.model_dump(),
            source_urls=[EMSD_JSON_URL, SOURCE_DATASET],
            notes=[str(exc)],
        )
        return out, result
    finally:
        if owns_client:
            http.close()
