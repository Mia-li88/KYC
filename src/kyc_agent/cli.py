"""Minimal CLI: run one company KYC check."""

from __future__ import annotations

import argparse
import json
import sys

from kyc_agent.graph import run_kyc_check
from kyc_agent.models import TradeKind


def _parse_trades(raw: str | None) -> list[TradeKind]:
    if not raw:
        return [TradeKind.ELECTRICAL, TradeKind.GENERAL]
    out: list[TradeKind] = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            out.append(TradeKind(part))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="HK construction subcontractor KYC check (LangGraph skeleton)"
    )
    parser.add_argument("--brn", help="Business Registration Number (e.g. C1572528)")
    parser.add_argument("--name-en", dest="name_en", help="English legal name")
    parser.add_argument("--name-zh", dest="name_zh", help="Chinese legal name")
    parser.add_argument(
        "--trades",
        help="Comma-separated trades: electrical,plumbing,fire,general,public_works",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip live HTTP (use for CI / no-network demos)",
    )
    parser.add_argument(
        "--no-hitl",
        action="store_true",
        help="Skip financials/insurance/safety document pause",
    )
    parser.add_argument(
        "--resume-json",
        help='JSON resume payload for HITL, e.g. \'{"skip_hitl": true}\'',
    )
    parser.add_argument("--thread-id", default="cli-demo")
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    args = parser.parse_args(argv)

    if not args.brn and not args.name_en and not args.name_zh and not args.resume_json:
        parser.error("Provide --brn and/or --name-en/--name-zh (or --resume-json)")

    human_resume = None
    if args.resume_json:
        human_resume = json.loads(args.resume_json)

    result = run_kyc_check(
        brn=args.brn,
        legal_name_en=args.name_en,
        legal_name_zh=args.name_zh,
        requested_trades=_parse_trades(args.trades),
        offline=args.offline,
        require_financials=not args.no_hitl,
        require_insurance=not args.no_hitl,
        require_safety_docs=not args.no_hitl,
        thread_id=args.thread_id,
        human_resume=human_resume,
    )
    indent = 2 if args.pretty else None
    print(json.dumps(result, ensure_ascii=False, indent=indent, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
