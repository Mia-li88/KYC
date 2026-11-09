"""CIC RSTCS / Registered Subcontractor status — Semi stub.

Portal: https://rstc.cic.hk/rstc/search_sub_contractors.aspx?lang=en-US
ToS / PDPO: purpose-limited personal data; English name search; ASP.NET + disclaimer.
Cloudflare may block datacenter scrapers — prefer human confirm + applicant reg no.
"""

from __future__ import annotations

from kyc_agent.models import (
    AccessClass,
    CheckResult,
    CheckStatus,
    CICRSTCSStatusInput,
    CICRSTCSStatusOutput,
)

PORTAL = "https://rstc.cic.hk/rstc/search_sub_contractors.aspx?lang=en-US"


def cic_rstcs_status(inp: CICRSTCSStatusInput) -> tuple[CICRSTCSStatusOutput, CheckResult]:
    out = CICRSTCSStatusOutput(
        found=False,
        registration_no=inp.registration_no,
        english_name=inp.english_name,
    )
    result = CheckResult(
        tool="cic_rstcs_status",
        access_class=AccessClass.SEMI,
        status=CheckStatus.STUB,
        summary="CIC RSTCS status stub — human portal confirm required",
        data=out.model_dump(),
        source_urls=[PORTAL, "https://rstc.cic.hk/en/index.aspx"],
        notes=[out.todo, "Do not bulk-scrape director personal data."],
    )
    return out, result
