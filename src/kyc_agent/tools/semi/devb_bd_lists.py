"""DEVB approved contractors + Buildings Department registers — Semi stub.

DEVB search: https://www.devb.gov.hk/en/construction_sector_matters/contractors/contractor/index.html
BD search: https://www.bd.gov.hk/en/resources/online-tools/registers-search/registrationsearch.html

Capability / list-membership flags only — not full project history or values.
"""

from __future__ import annotations

from kyc_agent.models import (
    AccessClass,
    CheckResult,
    CheckStatus,
    DEVBBDListInput,
    DEVBBDListOutput,
)

DEVB_URL = (
    "https://www.devb.gov.hk/en/construction_sector_matters/contractors/"
    "contractor/index.html"
)
BD_URL = (
    "https://www.bd.gov.hk/en/resources/online-tools/registers-search/"
    "registrationsearch.html"
)


def devb_bd_list_check(inp: DEVBBDListInput) -> tuple[DEVBBDListOutput, CheckResult]:
    out = DEVBBDListOutput()
    result = CheckResult(
        tool="devb_bd_list_check",
        access_class=AccessClass.SEMI,
        status=CheckStatus.STUB,
        summary="DEVB/BD list membership stub — portal adapter + human confirm",
        data={**out.model_dump(), "query": inp.model_dump()},
        source_urls=[DEVB_URL, BD_URL],
        notes=[out.todo],
    )
    return out, result
