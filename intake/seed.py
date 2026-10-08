"""`make seed`: load three sample requests so status questions have something to show.

All fictional. Times are relative to now, so "overdue" stays true whenever the
demo runs. Brightline is left out on purpose: it's the live request.

  - Northwind Notes: incomplete (no business owner yet)
  - Quillbase: complete pack, waiting on the manager, past its 24-hour deadline
  - Harbor Signal: approved by the manager and Security
"""

from __future__ import annotations

import os
from datetime import timedelta

from . import workflow as wf
from .core import iso, now, pack_path, vendor_path


def _pack(name: str, site: str, use: str) -> str:
    rows = "\n".join(
        f"| {item} | Published on the trust page | met | [trust]({site}/trust) |"
        for item in ("dpa", "certification", "subprocessors", "deletion", "breach-notice", "residency", "liability")
    )
    return f"""# Research pack: {name}

## Company overview

- Small software company; see the public site ([home]({site}/))

## Intended use

{use}

## Security and trust

- SOC 2 Type II, DPA, sub-processor list, and 72-hour breach notice all published ([trust]({site}/trust))

## Pricing

- Public per-seat pricing ([pricing]({site}/pricing))

## Policy check

| ID | Finding | Status | Source |
| --- | --- | --- | --- |
{rows}

## Open questions

- Can the pilot use a single team workspace?

## Sources

- [Home]({site}/)
- [Trust]({site}/trust)
- [Pricing]({site}/pricing)
"""


def _at(dt) -> None:
    os.environ["INTAKE_NOW"] = iso(dt)


def run() -> None:
    base = now()
    pinned = os.environ.get("INTAKE_NOW")
    try:
        for slug in ("northwind-notes", "quillbase", "harbor-signal"):
            for path in (vendor_path(slug), pack_path(slug)):
                if path.exists():
                    path.unlink()

        # 1. Northwind: incomplete, two days old
        _at(base - timedelta(days=2))
        wf.new_request(
            {"legal_name": "Northwind Notes, Inc.", "website": "https://northwind-notes.example",
             "touches_customer_data": "no", "target_start_date": "2026-11-02",
             "requester": "Lee Park", "requester_manager": "Ana Cruz",
             "source": "ticket from Lee Park"},
            confirmed_by=None,
        )

        # 2. Quillbase: standard tier, submitted 30 hours ago, waiting on the manager (overdue)
        _at(base - timedelta(hours=30))
        wf.new_request(
            {"legal_name": "Quillbase, Inc.", "website": "https://quillbase.example",
             "touches_customer_data": "no", "business_owner": "Marco Diaz",
             "target_start_date": "2026-10-26", "requester": "Marco Diaz",
             "requester_manager": "Dan Ortiz", "source": "email from Marco Diaz"},
            confirmed_by="Marco Diaz",
        )
        wf.run_triage("quillbase")
        _at(base - timedelta(hours=29))
        wf.start_pack("quillbase")
        pack_path("quillbase").write_text(
            _pack("Quillbase, Inc.", "https://quillbase.example", "Shared docs for the Marketing team's 90-day pilot."),
            encoding="utf-8",
        )
        wf.run_pack_check("quillbase")

        # 3. Harbor Signal: high tier, approved three days ago
        _at(base - timedelta(days=4))
        wf.new_request(
            {"legal_name": "Harbor Signal, Inc.", "website": "https://harbor-signal.example",
             "touches_customer_data": "yes", "business_owner": "Priya Shah",
             "target_start_date": "2026-10-12", "requester": "Priya Shah",
             "requester_manager": "Dan Ortiz", "source": "email from Priya Shah"},
            confirmed_by="Priya Shah",
        )
        wf.run_triage("harbor-signal")
        _at(base - timedelta(days=4) + timedelta(hours=1))
        wf.start_pack("harbor-signal")
        pack_path("harbor-signal").write_text(
            _pack("Harbor Signal, Inc.", "https://harbor-signal.example", "Support call analytics for RevOps."),
            encoding="utf-8",
        )
        wf.run_pack_check("harbor-signal")
        _at(base - timedelta(days=4) + timedelta(hours=6))
        wf.record_decision("harbor-signal", "manager", "Dan Ortiz", "approved")
        _at(base - timedelta(days=3))
        wf.record_decision("harbor-signal", "security", "Sam Lee", "approved", "Account IDs only")
    finally:
        if pinned is None:
            os.environ.pop("INTAKE_NOW", None)
        else:
            os.environ["INTAKE_NOW"] = pinned

    print("Loaded 3 sample requests: Northwind Notes (incomplete), Quillbase (waiting on Dan, overdue), Harbor Signal (approved).")


if __name__ == "__main__":
    run()
