"""HITL document intake — no public data; mark awaiting human / accept uploads."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Optional

from kyc_agent.models import (
    AccessClass,
    CheckResult,
    CheckStatus,
    DocIntakeKind,
    DocIntakeRequest,
    PendingHumanItem,
)

# Expected evidence packs (private-company data is not public in HK)
_PACKS: dict[DocIntakeKind, dict[str, str]] = {
    DocIntakeKind.FINANCIALS: {
        "id": "hitl_financials",
        "prompt": (
            "上傳經審核財務報表／管理帳／銀行融資證明 (audited FS / management accounts / "
            "bank facility letters)。香港私人公司財務並非公開。"
        ),
    },
    DocIntakeKind.INSURANCE: {
        "id": "hitl_insurance",
        "prompt": (
            "上傳僱員補償 (EC) 及第三者責任 (TPL) 保單／證明，含受保人名稱、有效期與保額。"
            "可選：核對保險公司是否在 IA 獲授權名冊。"
        ),
    },
    DocIntakeKind.SAFETY_OFFICER: {
        "id": "hitl_safety_officer",
        "prompt": (
            "上傳註冊安全主任／安全督導員證明及僱傭關係文件。"
            "勞工處無可靠公開姓名搜尋名冊。"
        ),
    },
    DocIntakeKind.ISO_45001: {
        "id": "hitl_iso_45001",
        "prompt": (
            "上傳 ISO 45001 證書；請標明發證機構與證書編號以便到發證機構名冊覆核。"
        ),
    },
    DocIntakeKind.TRACK_RECORD: {
        "id": "hitl_track_record",
        "prompt": (
            "上傳類似工程往績表、完工證明／僱主推薦信及合約金額摘要。"
            "公共工程名冊僅作能力旗標，非完整往績。"
        ),
    },
}


def collect_hitl_requests(
    *,
    require_financials: bool = True,
    require_insurance: bool = True,
    require_safety_docs: bool = True,
    require_track_record: bool = False,
    existing_uploads: Optional[dict[str, list[str]]] = None,
) -> tuple[list[PendingHumanItem], list[DocIntakeRequest], list[CheckResult]]:
    """Build pending HITL items for required document packs."""
    existing_uploads = existing_uploads or {}
    kinds: list[DocIntakeKind] = []
    if require_financials:
        kinds.append(DocIntakeKind.FINANCIALS)
    if require_insurance:
        kinds.append(DocIntakeKind.INSURANCE)
    if require_safety_docs:
        kinds.extend([DocIntakeKind.SAFETY_OFFICER, DocIntakeKind.ISO_45001])
    if require_track_record:
        kinds.append(DocIntakeKind.TRACK_RECORD)

    pending: list[PendingHumanItem] = []
    requests: list[DocIntakeRequest] = []
    results: list[CheckResult] = []

    for kind in kinds:
        meta = _PACKS[kind]
        paths = list(existing_uploads.get(kind.value, []))
        # Also accept keys by pack id
        paths.extend(existing_uploads.get(meta["id"], []))
        paths = list(dict.fromkeys(paths))
        resolved = bool(paths) and all(Path(p).exists() for p in paths)

        item = PendingHumanItem(
            id=meta["id"],
            kind=kind,
            prompt=meta["prompt"],
            upload_paths=paths,
            resolved=resolved,
            resolution={"paths": paths} if resolved else None,
            created_at=date.today(),
        )
        pending.append(item)
        req = DocIntakeRequest(
            kind=kind,
            required=True,
            reason=meta["prompt"],
            accepted_paths=paths,
            awaiting_human=not resolved,
            human_confirmed=resolved,
        )
        requests.append(req)
        results.append(
            CheckResult(
                tool=f"doc_intake_{kind.value}",
                access_class=AccessClass.HITL,
                status=CheckStatus.PASS if resolved else CheckStatus.AWAITING_HUMAN,
                summary=(
                    f"Received {len(paths)} file(s) for {kind.value}"
                    if resolved
                    else f"Awaiting human upload/verify for {kind.value}"
                ),
                data=req.model_dump(),
                notes=["No public electronic source for this check."],
            )
        )
    return pending, requests, results


def resolve_human_uploads(
    pending: list[PendingHumanItem],
    human_responses: dict[str, Any],
) -> tuple[list[PendingHumanItem], list[CheckResult]]:
    """Apply human_responses map: {pending_id: {paths: [...], confirmed: bool, notes: ...}}."""
    updated: list[PendingHumanItem] = []
    results: list[CheckResult] = []
    for item in pending:
        payload = human_responses.get(item.id) or human_responses.get(item.kind.value)
        if not payload:
            updated.append(item)
            continue
        paths = list(payload.get("paths") or payload.get("upload_paths") or [])
        confirmed = bool(payload.get("confirmed", bool(paths)))
        notes = payload.get("notes")
        new_item = item.model_copy(
            update={
                "upload_paths": paths or item.upload_paths,
                "resolved": confirmed,
                "resolution": payload if confirmed else None,
            }
        )
        updated.append(new_item)
        results.append(
            CheckResult(
                tool=f"doc_intake_{item.kind.value}",
                access_class=AccessClass.HITL,
                status=CheckStatus.PASS if confirmed else CheckStatus.AWAITING_HUMAN,
                summary=(
                    f"Human confirmed {item.kind.value}"
                    if confirmed
                    else f"Still awaiting {item.kind.value}"
                ),
                data={"paths": new_item.upload_paths, "resolution": new_item.resolution},
                notes=[str(notes)] if notes else [],
            )
        )
    return updated, results
