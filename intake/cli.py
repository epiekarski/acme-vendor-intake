"""Command line for the vendor intake flow. Run `python -m intake --help`.

Grok Bot runs these commands; it relays their output and never decides a
tier, approver, or pack result itself.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import policy as pol
from . import workflow as wf
from .core import IntakeError, all_vendors, load_vendor

FIELDS = {
    "legal_name": "--legal-name",
    "website": "--website",
    "touches_customer_data": "--customer-data",
    "business_owner": "--business-owner",
    "target_start_date": "--start",
    "pilot_days": "--pilot-days",
    "requester": "--requester",
    "requester_manager": "--manager",
    "source": "--source",
}


def _add_fields(p: argparse.ArgumentParser) -> None:
    p.add_argument("--legal-name")
    p.add_argument("--website", help="https URL")
    p.add_argument("--customer-data", help="yes or no")
    p.add_argument("--business-owner")
    p.add_argument("--start", help="YYYY-MM-DD")
    p.add_argument("--pilot-days", type=int)
    p.add_argument("--requester")
    p.add_argument("--manager", help="the requester's manager (approves as 'manager')")
    p.add_argument("--source", help="where the request came from")
    p.add_argument("--confirmed-by", help="requester's name once they confirm the fields")


def _fields(args) -> dict:
    out = {}
    for field, flag in FIELDS.items():
        val = getattr(args, flag.lstrip("-").replace("-", "_"))
        if val is not None:
            out[field] = val
    return out


def _who(record: dict, role: str) -> str:
    return pol.approver_name(role, record)


def describe(record: dict) -> str:
    req = record["request"]
    lines = [f"{req.get('legal_name', record['id'])} [{record['id']}]: {record['status']}"]
    if record["status"] == "incomplete":
        missing = record.get("missing_fields") or []
        lines.append("  Missing: " + (", ".join(missing) if missing else "requester confirmation"))
    t = record.get("triage")
    if t:
        lines.append(f"  Tier: {t['tier']} ({'; '.join(r['reason'] for r in t['reasons'])})")
        lines.append("  Approvers: " + ", ".join(f"{r} = {_who(record, r)}" for r in t["approvers"]))
        overdue = " (OVERDUE)" if wf.is_overdue(record) else ""
        lines.append(f"  SLA due: {t['sla_due']}{overdue}")
    p = record.get("pack")
    if p:
        state = "complete" if p["complete"] else f"{len(p['problems'])} problem(s)"
        lines.append(f"  Research pack: {state}")
        for prob in p["problems"]:
            lines.append(f"    - {prob}")
        if p["policy_gaps"]:
            lines.append(f"  Policy gaps (flagged for approvers): {', '.join(p['policy_gaps'])}")
    for a in record.get("approvals", []):
        lines.append(f"  {a['role']}: {a['decision']} by {a['name']} at {a['at']}")
    nxt = wf.next_approver(record)
    if nxt:
        lines.append(f"  Waiting on: {nxt} ({_who(record, nxt)})")
    bot = [s for s in record.get("log", []) if s["actor"] == "bot"]
    human = [s for s in record.get("log", []) if s["actor"] == "human"]
    lines.append(f"  Steps by Bot: {len(bot)} | by people: {len(human)}")
    return "\n".join(lines)


def _print(record: dict, as_json: bool) -> None:
    print(json.dumps(record, indent=2) if as_json else describe(record))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="intake", description="Acme vendor pilot intake")
    parser.add_argument("--json", action="store_true", help="print the full record as JSON")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new", help="1. create a request from intake fields")
    _add_fields(p)

    p = sub.add_parser("update", help="1. fill or fix fields on an incomplete request")
    p.add_argument("slug")
    _add_fields(p)

    p = sub.add_parser("triage", help="2. apply policies/tiers.json")
    p.add_argument("slug")

    p = sub.add_parser("pack-start", help="3. copy the pack template to packs/<slug>.md")
    p.add_argument("slug")

    p = sub.add_parser("pack-check", help="3. check the pack and MSA policy coverage")
    p.add_argument("slug")

    p = sub.add_parser("decide", help="4. record a named person's approval decision")
    p.add_argument("slug")
    p.add_argument("--role", required=True)
    p.add_argument("--name", required=True, help="the person who decided")
    p.add_argument("--decision", required=True, choices=["approved", "rejected"])
    p.add_argument("--note", default="")

    p = sub.add_parser("status", help="5. one request, or all of them")
    p.add_argument("slug", nargs="?")
    p.add_argument("--waiting-on", help="a name or role; lists requests waiting on them")
    p.add_argument("--overdue", action="store_true", help="only requests past SLA")
    p.add_argument("--customer-data", action="store_true", help="only vendors touching customer data")

    p = sub.add_parser("flag", help="mark that Ops had to step in")
    p.add_argument("slug")
    p.add_argument("--reason", required=True)

    sub.add_parser("metrics", help="cycle time and exception rate")

    args = parser.parse_args(argv)
    try:
        return _run(args)
    except IntakeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def _run(args) -> int:
    if args.cmd == "new":
        record = wf.new_request(_fields(args), args.confirmed_by)
        _print(record, args.json)
    elif args.cmd == "update":
        record = wf.update_request(args.slug, _fields(args), args.confirmed_by)
        _print(record, args.json)
    elif args.cmd == "triage":
        _print(wf.run_triage(args.slug), args.json)
    elif args.cmd == "pack-start":
        print(wf.start_pack(args.slug))
    elif args.cmd == "pack-check":
        _print(wf.run_pack_check(args.slug), args.json)
    elif args.cmd == "decide":
        _print(wf.record_decision(args.slug, args.role, args.name, args.decision, args.note), args.json)
    elif args.cmd == "flag":
        _print(wf.flag_exception(args.slug, args.reason), args.json)
    elif args.cmd == "metrics":
        print(json.dumps(wf.metrics(all_vendors()), indent=2))
    elif args.cmd == "status":
        if args.slug:
            _print(load_vendor(args.slug), args.json)
            return 0
        records = all_vendors()
        if args.waiting_on:
            who = args.waiting_on.lower()
            records = [
                r for r in records
                if (nxt := wf.next_approver(r)) and (who == nxt or who in _who(r, nxt).lower())
            ]
        if args.overdue:
            records = [r for r in records if wf.is_overdue(r)]
        if args.customer_data:
            records = [r for r in records if r["request"].get("touches_customer_data")]
        if not records:
            print("No matching requests.")
        for r in records:
            print(describe(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
