"""The five steps: intake, triage, research pack, approval, status.

Each function updates one vendor record and logs who did the step.
Status moves: incomplete -> submitted -> researching -> pending_approval
-> approved | rejected.
"""

from __future__ import annotations

from datetime import date

from . import pack as packmod
from . import policy as pol
from .core import (
    IntakeError,
    SCHEMA,
    PACK_TEMPLATE,
    iso,
    load_json,
    load_vendor,
    log_step,
    now,
    pack_path,
    parse_iso,
    save_vendor,
    slugify,
)

BOT = "Vendor Intake Bot"


def required_fields() -> list[str]:
    return load_json(SCHEMA)["required"]


def missing_fields(request: dict) -> list[str]:
    return [f for f in required_fields() if request.get(f) in (None, "")]


def normalize(request: dict) -> dict:
    req = {k: v for k, v in request.items() if v not in (None, "")}
    if "touches_customer_data" in req and isinstance(req["touches_customer_data"], str):
        val = req["touches_customer_data"].strip().lower()
        if val not in ("yes", "no", "true", "false"):
            raise IntakeError("touches_customer_data must be yes or no")
        req["touches_customer_data"] = val in ("yes", "true")
    if "target_start_date" in req:
        try:
            date.fromisoformat(str(req["target_start_date"]))
        except ValueError:
            raise IntakeError("target_start_date must be YYYY-MM-DD")
        req["target_start_date"] = str(req["target_start_date"])
    if "website" in req and not str(req["website"]).startswith("https://"):
        raise IntakeError("website must be a public https URL")
    req.setdefault("pilot_days", 90)
    req["pilot_days"] = int(req["pilot_days"])
    return req


# 1. Intake -----------------------------------------------------------------

def new_request(request: dict, confirmed_by: str | None) -> dict:
    """Create the record. Without confirmation by the requester it stays incomplete."""
    req = normalize(request)
    if "legal_name" not in req:
        raise IntakeError("legal_name is needed to create the record")
    record = {
        "id": slugify(req["legal_name"]),
        "status": "incomplete",
        "submitted_at": None,
        "request": req,
        "triage": None,
        "pack": None,
        "approvals": [],
        "log": [],
    }
    log_step(record, "intake", "bot", BOT, f"Drafted request from {req.get('source', 'conversation')}")
    _finish_intake(record, confirmed_by)
    return record


def update_request(slug: str, changes: dict, confirmed_by: str | None) -> dict:
    record = load_vendor(slug)
    if record["status"] not in ("incomplete", "submitted"):
        raise IntakeError(f"Request is already {record['status']}; intake fields are locked")
    record["request"].update(normalize({**record["request"], **changes}))
    log_step(record, "intake", "bot", BOT, f"Updated fields: {', '.join(sorted(changes))}")
    _finish_intake(record, confirmed_by)
    return record


def _finish_intake(record: dict, confirmed_by: str | None) -> None:
    missing = missing_fields(record["request"])
    record["missing_fields"] = missing
    if missing or not confirmed_by:
        record["status"] = "incomplete"
    else:
        record["status"] = "submitted"
        record["submitted_at"] = iso(now())
        log_step(record, "intake-confirmed", "human", confirmed_by, "Requester confirmed the request")
    save_vendor(record)


# 2. Triage -----------------------------------------------------------------

def run_triage(slug: str) -> dict:
    record = load_vendor(slug)
    if record["status"] == "incomplete":
        raise IntakeError(f"Cannot triage: missing {record.get('missing_fields') or 'requester confirmation'}")
    result = pol.triage(record["request"], record["submitted_at"])
    record["triage"] = result
    if record["status"] == "submitted":
        record["status"] = "researching"
    rules = ", ".join(r["rule"] for r in result["reasons"])
    log_step(record, "triage", "bot", BOT, f"Tier {result['tier']} via {rules}; approvers {result['approvers']}")
    save_vendor(record)
    return record


# 3. Research pack ----------------------------------------------------------

def start_pack(slug: str) -> str:
    """Copy the template to packs/<slug>.md if it isn't there yet."""
    record = load_vendor(slug)
    path = pack_path(slug)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        text = PACK_TEMPLATE.read_text(encoding="utf-8").replace("{{vendor}}", record["request"]["legal_name"])
        path.write_text(text, encoding="utf-8")
    return str(path)


def run_pack_check(slug: str) -> dict:
    record = load_vendor(slug)
    if record["status"] not in ("researching", "pending_approval"):
        raise IntakeError(f"Pack check needs a triaged request (status is {record['status']})")
    path = pack_path(slug)
    if not path.exists():
        raise IntakeError(f"No pack at {path}. Run `intake pack-start {slug}` and fill it in.")
    result = packmod.check_pack(path.read_text(encoding="utf-8"))
    record["pack"] = {"path": f"packs/{slug}.md", "checked_at": iso(now()), **result}

    # Policy gaps only count once the pack is complete; a half-filled pack
    # would otherwise flag every item as unknown. Gaps are flagged for the
    # approvers to weigh; they don't add an approver.
    gaps = result["policy_gaps"] if result["complete"] else []
    record["pack"]["policy_gaps"] = gaps

    record["status"] = "pending_approval" if result["complete"] else "researching"
    summary = "complete" if result["complete"] else f"{len(result['problems'])} problem(s)"
    if gaps:
        summary += f"; policy gaps flagged for approvers: {gaps}"
    log_step(record, "pack-check", "bot", BOT, f"Pack {summary}")
    save_vendor(record)
    return record


# 4. Approval ---------------------------------------------------------------

def record_decision(slug: str, role: str, name: str, decision: str, note: str = "") -> dict:
    """Record a human decision. Only named people in a required role can decide."""
    record = load_vendor(slug)
    if record["status"] != "pending_approval":
        raise IntakeError(f"Not awaiting approval (status is {record['status']})")
    if not name or name.lower() in ("bot", BOT.lower()):
        raise IntakeError("An approval needs the name of the person who decided")
    if decision not in ("approved", "rejected"):
        raise IntakeError("decision must be approved or rejected")
    required = record["triage"]["approvers"]
    if role not in required:
        raise IntakeError(f"{role} is not a required approver here ({required})")
    if any(a["role"] == role for a in record["approvals"]):
        raise IntakeError(f"{role} has already decided")
    if role != next_approver(record):
        raise IntakeError(f"Approvals go in order; waiting on {next_approver(record)} first")

    record["approvals"].append(
        {"role": role, "name": name, "decision": decision, "at": iso(now()), "note": note}
    )
    log_step(record, f"approval-{role}", "human", name, f"{decision}{': ' + note if note else ''}")

    if decision == "rejected":
        record["status"] = "rejected"
    elif all(any(a["role"] == r and a["decision"] == "approved" for a in record["approvals"]) for r in required):
        record["status"] = "approved"
        record["decided_at"] = iso(now())
    save_vendor(record)
    return record


def pending_roles(record: dict) -> list[str]:
    if record["status"] != "pending_approval" or not record.get("triage"):
        return []
    done = {a["role"] for a in record["approvals"]}
    return [r for r in record["triage"]["approvers"] if r not in done]


def next_approver(record: dict) -> str | None:
    """Approvals go in order: manager first, then the rest."""
    roles = pending_roles(record)
    return roles[0] if roles else None


# 5. Status -----------------------------------------------------------------

def is_overdue(record: dict) -> bool:
    if record["status"] in ("approved", "rejected") or not record.get("triage"):
        return False
    return now() > parse_iso(record["triage"]["sla_due"])


def metrics(records: list[dict]) -> dict:
    decided = [r for r in records if r.get("decided_at") and r.get("submitted_at")]
    hours = [
        (parse_iso(r["decided_at"]) - parse_iso(r["submitted_at"])).total_seconds() / 3600 for r in decided
    ]
    exceptions = [r for r in records if r.get("exception")]
    return {
        "requests": len(records),
        "decided": len(decided),
        "median_cycle_hours": round(sorted(hours)[len(hours) // 2], 1) if hours else None,
        "exception_rate": round(len(exceptions) / len(records), 2) if records else None,
    }


def flag_exception(slug: str, reason: str) -> dict:
    """Mark that Ops had to step in (counts toward exception rate)."""
    record = load_vendor(slug)
    record["exception"] = reason
    log_step(record, "exception", "bot", BOT, f"Flagged to Ops: {reason}")
    save_vendor(record)
    return record
