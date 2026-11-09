"""Labour Department OSH conviction records (Free XML, ~2 year window).

Verified (research 2026-11-05):
  EN XML: https://www.labour.gov.hk/datagovhk/resource/lsd/lsd-convictionrecords_en.xml
  Dataset: https://data.gov.hk/en-data/dataset/hk-ld-lsd-lsd-convictionrecords
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from functools import lru_cache
from typing import Optional

import httpx

from kyc_agent.models import (
    AccessClass,
    CheckResult,
    CheckStatus,
    LDOSHInput,
    LDOSHMatch,
    LDOSHOutput,
)

LD_XML_URL = (
    "https://www.labour.gov.hk/datagovhk/resource/lsd/lsd-convictionrecords_en.xml"
)
SOURCE_DATASET = (
    "https://data.gov.hk/en-data/dataset/hk-ld-lsd-lsd-convictionrecords"
)

_FIELD_MAP = {
    "defendant_name": ("defendant_name", "Defendant_Name", "DefendantName"),
    "offence_location": ("offence_location", "Offence_Location", "OffenceLocation"),
    "date_of_offence": ("date_of_offence", "Date_of_Offence", "DateOfOffence"),
    "short_description": (
        "short_description",
        "Short_Description",
        "ShortDescription",
    ),
    "offence": ("offence", "Offence"),
    "date_of_sentence": (
        "date_of_sentence",
        "Date_of_Sentence",
        "DateOfSentence",
    ),
    "sentence": ("sentence", "Sentence"),
}


def _child_text(elem: ET.Element, *names: str) -> Optional[str]:
    for name in names:
        child = elem.find(name)
        if child is not None and child.text and child.text.strip():
            return child.text.strip()
        # case-insensitive local tag match
        for c in elem:
            tag = c.tag.split("}")[-1] if "}" in c.tag else c.tag
            if tag.casefold() == name.casefold() and c.text and c.text.strip():
                return c.text.strip()
    return None


def _parse_match(elem: ET.Element) -> LDOSHMatch:
    kwargs: dict[str, Optional[str]] = {}
    raw: dict[str, str] = {}
    for c in elem:
        tag = c.tag.split("}")[-1] if "}" in c.tag else c.tag
        if c.text and c.text.strip():
            raw[tag] = c.text.strip()
    for field, aliases in _FIELD_MAP.items():
        kwargs[field] = _child_text(elem, *aliases)
    return LDOSHMatch(**kwargs, raw=raw)


def _iter_records(root: ET.Element) -> list[LDOSHMatch]:
    matches: list[LDOSHMatch] = []
    # Common shapes: <records><record>… or flat list of conviction nodes
    candidates = list(root.iter())
    for elem in candidates:
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag.casefold() in {
            "record",
            "conviction",
            "convictionrecord",
            "row",
            "item",
        }:
            if _child_text(elem, "defendant_name", "Defendant_Name") or any(
                (c.tag.split("}")[-1] if "}" in c.tag else c.tag).casefold()
                == "defendant_name"
                for c in elem
            ):
                matches.append(_parse_match(elem))
    if matches:
        return matches
    # Fallback: any element that has a defendant_name child
    for elem in root.iter():
        if _child_text(elem, "defendant_name", "Defendant_Name", "DefendantName"):
            matches.append(_parse_match(elem))
    return matches


@lru_cache(maxsize=1)
def _cached_parse(url: str, body: bytes) -> tuple[LDOSHMatch, ...]:
    root = ET.fromstring(body)
    return tuple(_iter_records(root))


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def _match_names(names: list[str], records: list[LDOSHMatch]) -> list[LDOSHMatch]:
    needles = {_norm(n) for n in names if n and n.strip()}
    if not needles:
        return []
    hits: list[LDOSHMatch] = []
    for rec in records:
        defendant = _norm(rec.defendant_name or "")
        if not defendant:
            continue
        for needle in needles:
            if needle in defendant or defendant in needle:
                hits.append(rec)
                break
    return hits


def ld_osh_convictions(
    inp: LDOSHInput,
    *,
    client: Optional[httpx.Client] = None,
    timeout: float = 60.0,
    offline: bool = False,
) -> tuple[LDOSHOutput, CheckResult]:
    """Download LD OSH conviction XML and fuzzy-match company name aliases."""
    if offline:
        out = LDOSHOutput(match_count=0, matches=[])
        result = CheckResult(
            tool="ld_osh_convictions",
            access_class=AccessClass.AUTO,
            status=CheckStatus.SKIPPED,
            summary="Skipped (offline mode)",
            data=out.model_dump(),
            source_urls=[LD_XML_URL, SOURCE_DATASET],
        )
        return out, result

    owns_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        resp = http.get(LD_XML_URL)
        resp.raise_for_status()
        all_rows = list(_cached_parse(LD_XML_URL, resp.content))
        hits = _match_names(inp.names, all_rows)
        out = LDOSHOutput(match_count=len(hits), matches=hits)
        if hits:
            status = CheckStatus.FAIL
            summary = f"Found {len(hits)} OSH conviction match(es) in published window"
        else:
            status = CheckStatus.PASS
            summary = "No OSH conviction name match in published ~2-year feed"
        result = CheckResult(
            tool="ld_osh_convictions",
            access_class=AccessClass.AUTO,
            status=status,
            summary=summary,
            data={
                "match_count": out.match_count,
                "matches": [m.model_dump(exclude={"raw"}) for m in hits],
                "feed_size": len(all_rows),
            },
            source_urls=[LD_XML_URL, SOURCE_DATASET],
            notes=[
                "Natural persons withheld (PDPO); Chinese-only summons may be ZH-only.",
                "Excludes cases under review/appeal; quarterly refresh.",
            ],
        )
        return out, result
    except Exception as exc:  # noqa: BLE001
        out = LDOSHOutput(match_count=0, matches=[])
        result = CheckResult(
            tool="ld_osh_convictions",
            access_class=AccessClass.AUTO,
            status=CheckStatus.ERROR,
            summary=f"LD OSH conviction feed failed: {exc}",
            data=out.model_dump(),
            source_urls=[LD_XML_URL, SOURCE_DATASET],
            notes=[str(exc)],
        )
        return out, result
    finally:
        if owns_client:
            http.close()
