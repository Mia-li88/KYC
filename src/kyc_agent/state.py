"""Typed LangGraph state for HK subcontractor KYC."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict


def _merge_results(
    left: list[dict[str, Any]] | None, right: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    return list(left or []) + list(right or [])


def _merge_pending(
    left: list[dict[str, Any]] | None, right: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    """Merge pending HITL items by id (right wins on same id). Stored as dicts for checkpoint JSON safety."""
    by_id: dict[str, dict[str, Any]] = {}
    for item in left or []:
        key = str(item.get("id") or "")
        if key:
            by_id[key] = item
    for item in right or []:
        key = str(item.get("id") or "")
        if key:
            by_id[key] = item
    return list(by_id.values())


def _uniq_str(left: list[str] | None, right: list[str] | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in list(left or []) + list(right or []):
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


class KYCState(TypedDict, total=False):
    """Canonical company identity + check results + HITL flags."""

    # Identity (BRN is the preferred company key once known)
    brn: Optional[str]
    legal_name_en: Optional[str]
    legal_name_zh: Optional[str]
    aliases: Annotated[list[str], _uniq_str]

    # Trade registration numbers supplied by applicant / prior checks
    emsd_rec_no: Optional[str]
    cic_rstcs_no: Optional[str]
    fsd_rfsic_no: Optional[str]
    wsd_plumber_nos: Annotated[list[str], _uniq_str]
    trade_reg_nos: Annotated[list[str], _uniq_str]

    # Which trades / packs to run (string values of TradeKind)
    requested_trades: list[str]
    require_financials: bool
    require_insurance: bool
    require_safety_docs: bool
    require_track_record: bool

    # Offline / CI mode — skip live HTTP where desired
    offline: bool
    thread_id: Optional[str]

    # Accumulated tool outcomes (CheckResult.model_dump())
    check_results: Annotated[list[dict[str, Any]], _merge_results]
    errors: Annotated[list[str], operator.add]

    # HITL (PendingHumanItem.model_dump(mode="json"))
    pending_human: Annotated[list[dict[str, Any]], _merge_pending]
    hitl_required: bool
    awaiting_human: bool
    human_responses: dict[str, Any]

    # Phase markers
    auto_done: bool
    semi_done: bool
    hitl_done: bool
    summary: Optional[str]
