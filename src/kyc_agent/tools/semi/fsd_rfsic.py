"""FSD Registered Fire Service Installation Contractor (RFSIC) — Semi stub.

Portal: https://www.hkfsd.gov.hk/rfsic/
No public machine API found (research 2026-11-05). Human confirm recommended.
"""

from __future__ import annotations

from kyc_agent.models import (
    AccessClass,
    CheckResult,
    CheckStatus,
    FSDRFSICInput,
    FSDRFSICOutput,
)

PORTAL = "https://www.hkfsd.gov.hk/rfsic/"


def fsd_rfsic_check(inp: FSDRFSICInput) -> tuple[FSDRFSICOutput, CheckResult]:
    out = FSDRFSICOutput(found=False, classes=[])
    result = CheckResult(
        tool="fsd_rfsic_check",
        access_class=AccessClass.SEMI,
        status=CheckStatus.STUB,
        summary="FSD RFSIC stub — portal verify + human confirm",
        data={**out.model_dump(), "query": inp.model_dump()},
        source_urls=[PORTAL],
        notes=[out.todo],
    )
    return out, result
