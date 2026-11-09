"""CIC RSTCS adverse / regulatory notices — stub (optional Auto/Semi).

Portal (research 2026-11-05): https://www.rstc.cic.hk/en/notice.aspx

HTML notice list is scrapable with care; CIC hosts may present Cloudflare
challenges from datacenter IPs. This module returns a clear stub + sample
shape for LangGraph wiring. Production should snapshot notices into a local
store and match offline — do not scrape Cloudflare-heavy sites in CI.
"""

from __future__ import annotations

from kyc_agent.models import (
    AccessClass,
    CheckResult,
    CheckStatus,
    CICAdverseInput,
    CICAdverseOutput,
    CICAdverseRow,
)

NOTICE_URL = "https://www.rstc.cic.hk/en/notice.aspx"


def cic_rstcs_adverse(
    inp: CICAdverseInput,
    *,
    offline: bool = True,
) -> tuple[CICAdverseOutput, CheckResult]:
    """Stub adverse-notice matcher. Always returns STUB unless a local cache is wired."""
    _ = offline  # live scrape intentionally not implemented
    sample = CICAdverseRow(
        registration_no="R001234",
        company_name="EXAMPLE ENGINEERING CO LTD",
        action="Suspension",
        period="2026-01-01 to 2026-06-30",
        remarks="Serious incident / OSH conviction (sample shape)",
    )
    out = CICAdverseOutput(
        match_count=0,
        rows=[],
        stub=True,
        note=(
            "Stub only — wire periodic HTML snapshot of "
            f"{NOTICE_URL} into a local cache, then name/reg-no match. "
            f"Query was: {inp.model_dump()}"
        ),
    )
    result = CheckResult(
        tool="cic_rstcs_adverse",
        access_class=AccessClass.AUTO,
        status=CheckStatus.STUB,
        summary="CIC RSTCS adverse notices not queried (stub — avoid CI scrape)",
        data={
            **out.model_dump(),
            "sample_row": sample.model_dump(),
        },
        source_urls=[NOTICE_URL],
        notes=[
            "Critical safety/compliance signal when implemented.",
            "Cross-check with ld_osh_convictions.",
            "Do not scrape Cloudflare-protected CIC hosts from CI.",
        ],
    )
    return out, result
