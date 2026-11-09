"""WSD Licensed Plumber directory — Semi stub (individuals, PDPO-sensitive).

Portal: https://www.esd.wsd.gov.hk/esd/aws/licensedPlumberDirectory/init.do
Session JSP; prefer HITL certificate upload over bulk scrape.
"""

from __future__ import annotations

from kyc_agent.models import (
    AccessClass,
    CheckResult,
    CheckStatus,
    WSDPlumberInput,
    WSDPlumberOutput,
)

PORTAL = (
    "https://www.esd.wsd.gov.hk/esd/aws/licensedPlumberDirectory/"
    "init.do?USER_LANG=LANG_ENG&pageFlag=1"
)


def wsd_plumber_check(inp: WSDPlumberInput) -> tuple[WSDPlumberOutput, CheckResult]:
    out = WSDPlumberOutput(
        results=[{"licence_no": n, "status": "stub_unverified"} for n in inp.licence_nos],
    )
    result = CheckResult(
        tool="wsd_plumber_check",
        access_class=AccessClass.SEMI,
        status=CheckStatus.STUB,
        summary="WSD plumber directory stub — verify nominated LP nos with HITL/portal",
        data=out.model_dump(),
        source_urls=[PORTAL, "https://www.wsd.gov.hk/en/plumbing-engineering/licensed-plumbers/"],
        notes=[out.todo, "Do not bulk-scrape personal contacts for marketing."],
    )
    return out, result
