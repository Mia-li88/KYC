"""LangGraph KYC workflow: Auto → Semi (requested trades) → HITL interrupt."""

from __future__ import annotations

from typing import Any, Literal, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from kyc_agent.models import (
    AccessClass,
    CheckResult,
    CheckStatus,
    CICAdverseInput,
    CICRSTCSStatusInput,
    CRLookupInput,
    DEVBBDListInput,
    EMSDRecInput,
    FSDRFSICInput,
    LDOSHInput,
    PendingHumanItem,
    TradeKind,
    WSDPlumberInput,
)
from kyc_agent.state import KYCState
from kyc_agent.tools.auto import (
    cic_rstcs_adverse,
    cr_opendata_lookup,
    emsd_rec_check,
    ld_osh_convictions,
)
from kyc_agent.tools.hitl import collect_hitl_requests, resolve_human_uploads
from kyc_agent.tools.semi import (
    cic_rstcs_status,
    devb_bd_list_check,
    fsd_rfsic_check,
    wsd_plumber_check,
)


def _dump_results(results: list[CheckResult]) -> list[dict[str, Any]]:
    return [r.model_dump(mode="json") for r in results]


def _dump_pending(items: list[PendingHumanItem]) -> list[dict[str, Any]]:
    return [p.model_dump(mode="json") for p in items]


def _pending_models(raw: list[dict[str, Any]] | None) -> list[PendingHumanItem]:
    return [PendingHumanItem.model_validate(p) for p in (raw or [])]


def _trade_values(state: KYCState) -> set[str]:
    return {str(t) for t in (state.get("requested_trades") or [])}


def _aliases_from_state(state: KYCState) -> list[str]:
    names: list[str] = []
    for key in ("legal_name_en", "legal_name_zh", "brn"):
        val = state.get(key)
        if val:
            names.append(str(val))
    names.extend(state.get("aliases") or [])
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def node_auto(state: KYCState) -> dict[str, Any]:
    """Always run free structured sources."""
    offline = bool(state.get("offline"))
    results: list[CheckResult] = []
    errors: list[str] = []
    updates: dict[str, Any] = {"aliases": [], "trade_reg_nos": []}

    cr_inp = CRLookupInput(
        brn=state.get("brn"),
        company_name=state.get("legal_name_en") or state.get("legal_name_zh"),
    )
    if cr_inp.brn or cr_inp.company_name:
        cr_out, cr_res = cr_opendata_lookup(cr_inp, offline=offline)
        results.append(cr_res)
        if cr_out.found and cr_out.records:
            top = cr_out.records[0]
            if top.brn:
                updates["brn"] = top.brn
            if top.english_company_name:
                updates["legal_name_en"] = top.english_company_name
                updates["aliases"] = [top.english_company_name]
            if top.chinese_company_name:
                updates["legal_name_zh"] = top.chinese_company_name
                updates["aliases"] = updates.get("aliases", []) + [
                    top.chinese_company_name
                ]
        if cr_res.status == CheckStatus.ERROR:
            errors.append(cr_res.summary)
    else:
        results.append(
            CheckResult(
                tool="cr_opendata_lookup",
                access_class=AccessClass.AUTO,
                status=CheckStatus.SKIPPED,
                summary="No BRN or company name provided for CR lookup",
            )
        )

    merged_state: KYCState = {**state, **updates}  # type: ignore[misc]
    aliases = _aliases_from_state(merged_state)

    emsd_inp = EMSDRecInput(
        english_name=merged_state.get("legal_name_en"),
        chinese_name=merged_state.get("legal_name_zh"),
        registration_no=merged_state.get("emsd_rec_no"),
        aliases=aliases,
    )
    _, emsd_res = emsd_rec_check(emsd_inp, offline=offline)
    results.append(emsd_res)
    if emsd_res.status == CheckStatus.ERROR:
        errors.append(emsd_res.summary)
    for m in (emsd_res.data or {}).get("matches") or []:
        reg = m.get("registration_no")
        if reg:
            updates["trade_reg_nos"] = list(
                dict.fromkeys((updates.get("trade_reg_nos") or []) + [reg])
            )
            updates["emsd_rec_no"] = updates.get("emsd_rec_no") or reg

    _, ld_res = ld_osh_convictions(LDOSHInput(names=aliases), offline=offline)
    results.append(ld_res)
    if ld_res.status == CheckStatus.ERROR:
        errors.append(ld_res.summary)

    _, cic_adv = cic_rstcs_adverse(
        CICAdverseInput(
            english_name=merged_state.get("legal_name_en"),
            chinese_name=merged_state.get("legal_name_zh"),
            registration_no=merged_state.get("cic_rstcs_no"),
            aliases=aliases,
        ),
        offline=True,
    )
    results.append(cic_adv)

    return {
        **updates,
        "check_results": _dump_results(results),
        "errors": errors,
        "auto_done": True,
    }


def node_semi(state: KYCState) -> dict[str, Any]:
    """Run Semi portal stubs for requested trades / capability lists."""
    trades = _trade_values(state)
    results: list[CheckResult] = []

    if (
        state.get("cic_rstcs_no")
        or state.get("legal_name_en")
        or TradeKind.GENERAL.value in trades
    ):
        _, res = cic_rstcs_status(
            CICRSTCSStatusInput(
                registration_no=state.get("cic_rstcs_no"),
                english_name=state.get("legal_name_en"),
            )
        )
        results.append(res)

    if TradeKind.FIRE.value in trades or state.get("fsd_rfsic_no"):
        _, res = fsd_rfsic_check(
            FSDRFSICInput(
                company_name=state.get("legal_name_en"),
                registration_no=state.get("fsd_rfsic_no"),
            )
        )
        results.append(res)

    if TradeKind.PLUMBING.value in trades or state.get("wsd_plumber_nos"):
        _, res = wsd_plumber_check(
            WSDPlumberInput(licence_nos=list(state.get("wsd_plumber_nos") or []))
        )
        results.append(res)

    if TradeKind.PUBLIC_WORKS.value in trades or TradeKind.GENERAL.value in trades:
        _, res = devb_bd_list_check(
            DEVBBDListInput(
                company_name=state.get("legal_name_en"),
                chinese_name=state.get("legal_name_zh"),
            )
        )
        results.append(res)

    if TradeKind.ELECTRICAL.value in trades and not results:
        _, res = cic_rstcs_status(
            CICRSTCSStatusInput(
                registration_no=state.get("cic_rstcs_no"),
                english_name=state.get("legal_name_en"),
            )
        )
        results.append(res)

    return {"check_results": _dump_results(results), "semi_done": True}


def _needs_hitl(state: KYCState) -> bool:
    return bool(
        state.get("require_financials", True)
        or state.get("require_insurance", True)
        or state.get("require_safety_docs", True)
        or state.get("require_track_record", False)
    )


def route_after_semi(state: KYCState) -> Literal["hitl", "summarize"]:
    return "hitl" if _needs_hitl(state) else "summarize"


def node_hitl(state: KYCState) -> Command[Literal["summarize"]] | dict[str, Any]:
    """Pause for document upload / manual verify via LangGraph interrupt."""
    human_responses = dict(state.get("human_responses") or {})
    existing_pending = _pending_models(state.get("pending_human"))

    if human_responses and existing_pending:
        updated, results = resolve_human_uploads(existing_pending, human_responses)
        still = [p for p in updated if not p.resolved]
        if still:
            resume = interrupt(
                {
                    "message": "仍有文件待人工上傳／核實",
                    "pending": _dump_pending(still),
                }
            )
            if isinstance(resume, dict):
                updated2, results2 = resolve_human_uploads(still, resume)
                return Command(
                    update={
                        "pending_human": _dump_pending(updated2),
                        "check_results": _dump_results(results + results2),
                        "awaiting_human": any(not p.resolved for p in updated2),
                        "hitl_required": True,
                        "hitl_done": all(p.resolved for p in updated2),
                        "human_responses": {**human_responses, **resume},
                    },
                    goto="summarize",
                )
        return {
            "pending_human": _dump_pending(updated),
            "check_results": _dump_results(results),
            "awaiting_human": any(not p.resolved for p in updated),
            "hitl_required": True,
            "hitl_done": all(p.resolved for p in updated),
        }

    uploads = human_responses.get("uploads") or {}
    pending, _reqs, results = collect_hitl_requests(
        require_financials=bool(state.get("require_financials", True)),
        require_insurance=bool(state.get("require_insurance", True)),
        require_safety_docs=bool(state.get("require_safety_docs", True)),
        require_track_record=bool(state.get("require_track_record", False)),
        existing_uploads=uploads,
    )

    unresolved = [p for p in pending if not p.resolved]
    if unresolved:
        resume = interrupt(
            {
                "message": (
                    "需要人工上傳／核實文件（財務、保險、安全證明等）。"
                    "請以 Command(resume={pending_id: {paths: [...], confirmed: true}}) 繼續。"
                ),
                "pending": _dump_pending(unresolved),
            }
        )
        if isinstance(resume, dict):
            if resume.get("skip_hitl"):
                return Command(
                    update={
                        "pending_human": _dump_pending(pending),
                        "check_results": _dump_results(results),
                        "awaiting_human": False,
                        "hitl_required": True,
                        "hitl_done": True,
                        "human_responses": resume,
                    },
                    goto="summarize",
                )
            updated, more = resolve_human_uploads(pending, resume)
            return Command(
                update={
                    "pending_human": _dump_pending(updated),
                    "check_results": _dump_results(results + more),
                    "awaiting_human": any(not p.resolved for p in updated),
                    "hitl_required": True,
                    "hitl_done": all(p.resolved for p in updated),
                    "human_responses": resume,
                },
                goto="summarize",
            )

    return {
        "pending_human": _dump_pending(pending),
        "check_results": _dump_results(results),
        "awaiting_human": False,
        "hitl_required": True,
        "hitl_done": True,
    }


def node_summarize(state: KYCState) -> dict[str, Any]:
    results = list(state.get("check_results") or [])
    by_status: dict[str, int] = {}
    for r in results:
        key = str(r.get("status") if isinstance(r, dict) else getattr(r, "status", "?"))
        by_status[key] = by_status.get(key, 0) + 1
    pending = [
        p
        for p in (state.get("pending_human") or [])
        if not (p.get("resolved") if isinstance(p, dict) else getattr(p, "resolved", False))
    ]
    lines = [
        f"BRN={state.get('brn') or '—'}",
        f"EN={state.get('legal_name_en') or '—'}",
        f"ZH={state.get('legal_name_zh') or '—'}",
        f"checks={len(results)} {by_status}",
        f"pending_hitl={len(pending)}",
    ]
    return {
        "summary": "; ".join(lines),
        "awaiting_human": bool(pending),
    }


def build_kyc_graph(*, checkpointer: Optional[Any] = None):
    """Compile the Auto → Semi → HITL → summarize graph."""
    g: StateGraph = StateGraph(KYCState)
    g.add_node("auto", node_auto)
    g.add_node("semi", node_semi)
    g.add_node("hitl", node_hitl)
    g.add_node("summarize", node_summarize)

    g.add_edge(START, "auto")
    g.add_edge("auto", "semi")
    g.add_conditional_edges(
        "semi",
        route_after_semi,
        {"hitl": "hitl", "summarize": "summarize"},
    )
    g.add_edge("hitl", "summarize")
    g.add_edge("summarize", END)

    saver = checkpointer if checkpointer is not None else MemorySaver()
    return g.compile(checkpointer=saver)


def run_kyc_check(
    *,
    brn: Optional[str] = None,
    legal_name_en: Optional[str] = None,
    legal_name_zh: Optional[str] = None,
    aliases: Optional[list[str]] = None,
    requested_trades: Optional[list[TradeKind | str]] = None,
    offline: bool = False,
    require_financials: bool = True,
    require_insurance: bool = True,
    require_safety_docs: bool = True,
    require_track_record: bool = False,
    thread_id: str = "demo",
    human_resume: Optional[dict[str, Any]] = None,
    graph: Optional[Any] = None,
) -> dict[str, Any]:
    """Convenience runner used by CLI / demos.

    First call runs until HITL interrupt (if docs required).
    Pass ``human_resume`` on a subsequent call with the same ``thread_id`` to continue.
    """
    app = graph or build_kyc_graph()
    config = {"configurable": {"thread_id": thread_id}}

    if human_resume is not None:
        result = app.invoke(Command(resume=human_resume), config=config)
        return _public_view(result)

    trades: list[str] = []
    for t in requested_trades or [TradeKind.ELECTRICAL, TradeKind.GENERAL]:
        trades.append(t.value if isinstance(t, TradeKind) else str(t))

    initial: KYCState = {
        "brn": brn,
        "legal_name_en": legal_name_en,
        "legal_name_zh": legal_name_zh,
        "aliases": list(aliases or []),
        "wsd_plumber_nos": [],
        "trade_reg_nos": [],
        "requested_trades": trades,
        "require_financials": require_financials,
        "require_insurance": require_insurance,
        "require_safety_docs": require_safety_docs,
        "require_track_record": require_track_record,
        "offline": offline,
        "thread_id": thread_id,
        "check_results": [],
        "errors": [],
        "pending_human": [],
        "human_responses": {},
        "hitl_required": False,
        "awaiting_human": False,
        "auto_done": False,
        "semi_done": False,
        "hitl_done": False,
    }
    result = app.invoke(initial, config=config)
    return _public_view(result)


def _public_view(state: dict[str, Any]) -> dict[str, Any]:
    results = state.get("check_results") or []
    pending = state.get("pending_human") or []
    return {
        "brn": state.get("brn"),
        "legal_name_en": state.get("legal_name_en"),
        "legal_name_zh": state.get("legal_name_zh"),
        "aliases": state.get("aliases"),
        "trade_reg_nos": state.get("trade_reg_nos"),
        "summary": state.get("summary"),
        "awaiting_human": state.get("awaiting_human"),
        "auto_done": state.get("auto_done"),
        "semi_done": state.get("semi_done"),
        "hitl_done": state.get("hitl_done"),
        "errors": state.get("errors"),
        "check_results": results,
        "pending_human": pending,
    }
