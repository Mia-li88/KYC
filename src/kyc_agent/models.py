"""Pydantic I/O models for Auto / Semi / HITL tools."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AccessClass(str, Enum):
    AUTO = "auto"
    SEMI = "semi"
    HITL = "hitl"


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    PENDING = "pending"
    SKIPPED = "skipped"
    ERROR = "error"
    AWAITING_HUMAN = "awaiting_human"
    STUB = "stub"


class TradeKind(str, Enum):
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    FIRE = "fire"
    GENERAL = "general"
    PUBLIC_WORKS = "public_works"


class CheckResult(BaseModel):
    """Normalized result written into graph state."""

    tool: str
    access_class: AccessClass
    status: CheckStatus
    summary: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    source_urls: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# --- Auto tool I/O ---


class CRLookupInput(BaseModel):
    brn: Optional[str] = None
    company_name: Optional[str] = None
    name_match: str = Field(
        default="begins_with",
        description=(
            "Comp_name match mode. CR open data returns HTTP 400 for equal; "
            "tool always uses begins_with with progressive prefixes."
        ),
    )


class CRCompanyRecord(BaseModel):
    brn: Optional[str] = None
    english_company_name: Optional[str] = None
    chinese_company_name: Optional[str] = None
    address_of_registered_office: Optional[str] = None
    company_type: Optional[str] = None
    date_of_incorporation: Optional[str] = None
    re_domiciliation_date: Optional[str] = None
    raw: dict[str, Any] = Field(default_factory=dict)


class CRLookupOutput(BaseModel):
    found: bool
    records: list[CRCompanyRecord] = Field(default_factory=list)
    query: dict[str, Any] = Field(default_factory=dict)


class EMSDRecInput(BaseModel):
    english_name: Optional[str] = None
    chinese_name: Optional[str] = None
    registration_no: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)


class EMSDRecRecord(BaseModel):
    registration_no: Optional[str] = None
    english_name: Optional[str] = None
    chinese_name: Optional[str] = None
    expiry_date: Optional[str] = None
    address: Optional[str] = None
    telephone: Optional[str] = None
    disciplinary_flags: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class EMSDRecOutput(BaseModel):
    registered: bool
    matches: list[EMSDRecRecord] = Field(default_factory=list)


class LDOSHInput(BaseModel):
    names: list[str] = Field(default_factory=list)
    """Company name aliases to match against defendant_name."""


class LDOSHMatch(BaseModel):
    defendant_name: Optional[str] = None
    offence_location: Optional[str] = None
    date_of_offence: Optional[str] = None
    short_description: Optional[str] = None
    offence: Optional[str] = None
    date_of_sentence: Optional[str] = None
    sentence: Optional[str] = None
    raw: dict[str, Any] = Field(default_factory=dict)


class LDOSHOutput(BaseModel):
    match_count: int = 0
    matches: list[LDOSHMatch] = Field(default_factory=list)
    window_note: str = "Labour Department publishes past ~2 years of OSH convictions."


class CICAdverseInput(BaseModel):
    english_name: Optional[str] = None
    chinese_name: Optional[str] = None
    registration_no: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)


class CICAdverseRow(BaseModel):
    registration_no: Optional[str] = None
    company_name: Optional[str] = None
    action: Optional[str] = None
    period: Optional[str] = None
    remarks: Optional[str] = None


class CICAdverseOutput(BaseModel):
    match_count: int = 0
    rows: list[CICAdverseRow] = Field(default_factory=list)
    stub: bool = True
    note: str = (
        "HTML notice list at rstc.cic.hk — stub only; cache snapshots in production. "
        "Do not scrape Cloudflare-protected CIC hosts from CI."
    )


# --- Semi tool I/O (stubs) ---


class CICRSTCSStatusInput(BaseModel):
    registration_no: Optional[str] = None
    english_name: Optional[str] = None


class CICRSTCSStatusOutput(BaseModel):
    found: bool = False
    registration_no: Optional[str] = None
    english_name: Optional[str] = None
    trades: list[dict[str, Any]] = Field(default_factory=list)
    expiry_date: Optional[str] = None
    stub: bool = True
    sample_shape: dict[str, Any] = Field(
        default_factory=lambda: {
            "registration_no": "R001234",
            "english_name": "EXAMPLE ENGINEERING CO LTD",
            "trades": [{"group": "Electrical", "code": "E01", "expiry": "2027-12-31"}],
            "brn": "12345678",
        }
    )
    todo: str = (
        "TODO: ASP.NET form + disclaimer + PDPO purpose limitation. "
        "Prefer applicant-supplied reg no. Portal: https://rstc.cic.hk/rstc/search_sub_contractors.aspx"
    )


class FSDRFSICInput(BaseModel):
    company_name: Optional[str] = None
    registration_no: Optional[str] = None


class FSDRFSICOutput(BaseModel):
    found: bool = False
    classes: list[str] = Field(default_factory=list)
    stub: bool = True
    sample_shape: dict[str, Any] = Field(
        default_factory=lambda: {
            "registration_no": "RC/XXX/1234",
            "company_name": "EXAMPLE FSI LTD",
            "classes": ["Class 1", "Class 2"],
        }
    )
    todo: str = (
        "TODO: Portal adapter for https://www.hkfsd.gov.hk/rfsic/ — human confirm recommended. "
        "No public machine API found (research 2026-11-05)."
    )


class WSDPlumberInput(BaseModel):
    licence_nos: list[str] = Field(default_factory=list)
    """Nominated licensed plumber numbers (individuals, not company licence)."""


class WSDPlumberOutput(BaseModel):
    results: list[dict[str, Any]] = Field(default_factory=list)
    stub: bool = True
    sample_shape: dict[str, Any] = Field(
        default_factory=lambda: {
            "licence_no": "LP-0001",
            "name_en": "CHAN TAI MAN",
            "name_zh": "陳大文",
            "valid": True,
        }
    )
    todo: str = (
        "TODO: Session JSP directory — PDPO purpose-limited. "
        "Prefer HITL upload of LP certificates. "
        "https://www.esd.wsd.gov.hk/esd/aws/licensedPlumberDirectory/init.do"
    )


class DEVBBDListInput(BaseModel):
    company_name: Optional[str] = None
    chinese_name: Optional[str] = None


class DEVBBDListOutput(BaseModel):
    on_devb_list: bool = False
    on_bd_register: bool = False
    categories: list[str] = Field(default_factory=list)
    suspension_mark: bool = False
    stub: bool = True
    sample_shape: dict[str, Any] = Field(
        default_factory=lambda: {
            "devb": {
                "on_list": True,
                "categories": ["Buildings"],
                "group": "C",
                "probationary": False,
                "suspension_mark": False,
            },
            "bd": {"register": "RGBC", "registration_no": "ABC123", "expiry": "2027-06-30"},
        }
    )
    todo: str = (
        "TODO: Semi adapters — DEVB lists + BD registration search. "
        "DEVB: https://www.devb.gov.hk/en/construction_sector_matters/contractors/contractor/index.html "
        "BD: https://www.bd.gov.hk/en/resources/online-tools/registers-search/registrationsearch.html "
        "Capability flags only — not full project history."
    )


# --- HITL tool I/O ---


class DocIntakeKind(str, Enum):
    FINANCIALS = "financials"
    INSURANCE = "insurance"
    SAFETY_OFFICER = "safety_officer"
    ISO_45001 = "iso_45001"
    TRACK_RECORD = "track_record"


class DocIntakeRequest(BaseModel):
    kind: DocIntakeKind
    required: bool = True
    reason: str = ""
    accepted_paths: list[str] = Field(default_factory=list)
    awaiting_human: bool = True
    human_confirmed: bool = False
    extracted: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class PendingHumanItem(BaseModel):
    id: str
    kind: DocIntakeKind
    prompt: str
    upload_paths: list[str] = Field(default_factory=list)
    resolved: bool = False
    resolution: Optional[dict[str, Any]] = None
    created_at: Optional[date] = None
