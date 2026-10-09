"""Ops dashboard: one live view of every vendor request.

The repo builds the dashboard's data from the vendor records, so the Bot never
writes it by hand. `export()` writes dashboard/data.json; `publish()` also
pushes the page and data to the gh-pages branch, which GitHub Pages serves.
The main branch, where the rules live, is never touched by a publish.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import pack as packmod
from . import policy as pol
from . import workflow as wf
from .core import REPO_ROOT, all_vendors, data_root, iso, load_json, now, parse_iso, SCHEMA

PAGE = REPO_ROOT / "dashboard" / "index.html"
BRANCH = "gh-pages"

STAGES = ["Intake", "Triage", "Research", "Approval", "Done"]
STAGE_OF = {
    "incomplete": 0,
    "submitted": 1,
    "researching": 2,
    "pending_approval": 3,
    "approved": 4,
    "rejected": 4,
}
LABELS = {
    "incomplete": "Incomplete",
    "submitted": "Submitted",
    "researching": "Researching",
    "pending_approval": "Awaiting approval",
    "approved": "Approved",
    "rejected": "Rejected",
}
STEP_LABELS = {
    "intake": "Request drafted",
    "intake-confirmed": "Requester confirmed",
    "triage": "Triage: route set",
    "pack-start": "Research pack started",
    "pack-check": "Research pack checked",
    "exception": "Flagged to Ops",
}


def _tidy(detail: str) -> str:
    """Turn Python-style lists in log details into plain text."""
    return re.sub(r"\[([^\]]*)\]", lambda m: m.group(1).replace("'", ""), detail or "")


def _step_label(step: str) -> str:
    if step.startswith("approval-"):
        return f"{step.split('-', 1)[1].capitalize()} decision"
    return STEP_LABELS.get(step, step)


def _field_label(field: str) -> str:
    return field.replace("_", " ").capitalize()


def _hours(delta) -> int:
    return int(round(delta.total_seconds() / 3600))


def _approvers(record: dict) -> list[dict]:
    triage = record.get("triage") or {}
    nxt = wf.next_approver(record)
    out = []
    for role in triage.get("approvers", []):
        done = next((a for a in record.get("approvals", []) if a["role"] == role), None)
        if done:
            state = done["decision"]
        elif role == nxt:
            state = "waiting"
        else:
            state = "pending"
        out.append({"role": role, "name": pol.approver_name(role, record), "state": state})
    return out


def _blocker(record: dict) -> dict | None:
    """What's holding this request up, in plain English. None if nothing is."""
    status = record["status"]
    if record.get("exception") and status not in ("approved", "rejected"):
        return {"kind": "ops", "text": f"Flagged to Ops: {record['exception']}"}
    if status == "incomplete":
        missing = record.get("missing_fields") or []
        if missing:
            return {"kind": "missing", "text": "Missing: " + ", ".join(_field_label(f).lower() for f in missing)}
        return {"kind": "missing", "text": "Waiting for the requester to confirm"}
    if status in ("submitted", "researching"):
        pack = record.get("pack") or {}
        if pack.get("problems"):
            return {"kind": "research", "text": f"Research pack: {len(pack['problems'])} problem(s) to fix"}
        return None
    if status == "pending_approval":
        nxt = wf.next_approver(record)
        who = pol.approver_name(nxt, record) if nxt else "an approver"
        if wf.is_overdue(record):
            late = _hours(now() - parse_iso(record["triage"]["sla_due"]))
            return {"kind": "overdue", "text": f"Overdue {late}h: waiting on {who}"}
        return None
    return None


def request_view(record: dict) -> dict:
    req = record.get("request", {})
    triage = record.get("triage") or {}
    pack = record.get("pack") or {}
    nxt = wf.next_approver(record)
    due = triage.get("sla_due") if record["status"] not in ("approved", "rejected") else None
    return {
        "id": record["id"],
        "vendor": req.get("legal_name", record["id"]),
        "website": req.get("website"),
        "requester": req.get("requester"),
        "status": record["status"],
        "status_label": LABELS.get(record["status"], record["status"]),
        "stage": STAGE_OF.get(record["status"], 0),
        "tier": triage.get("tier"),
        "tier_reason": "; ".join(r["reason"] for r in triage.get("reasons", [])) or None,
        "approvers": _approvers(record),
        "waiting_on": {"role": nxt, "name": pol.approver_name(nxt, record)} if nxt else None,
        "due": due,
        "overdue": wf.is_overdue(record),
        "blocker": _blocker(record),
        "fields": {
            "Legal name": req.get("legal_name"),
            "Website": req.get("website"),
            "Touches customer data": (
                None if req.get("touches_customer_data") is None
                else ("Yes" if req.get("touches_customer_data") else "No")
            ),
            "Business owner": req.get("business_owner"),
            "Target start": req.get("target_start_date"),
            "Pilot length": f"{req['pilot_days']} days" if req.get("pilot_days") else None,
            "Requester": req.get("requester"),
            "Requester's manager": req.get("requester_manager"),
            "Source": req.get("source"),
        },
        "missing_fields": [_field_label(f) for f in (record.get("missing_fields") or [])],
        "pack": {
            "complete": bool(pack.get("complete")),
            "checked_at": pack.get("checked_at"),
            "problems": pack.get("problems", []),
            "policy_gaps": [packmod.msa_items().get(g, g) for g in pack.get("policy_gaps", [])],
        } if pack else None,
        "approvals": record.get("approvals", []),
        "log": [
            {**s, "label": _step_label(s["step"]), "detail": _tidy(s.get("detail", ""))}
            for s in record.get("log", [])
        ],
        "submitted_at": record.get("submitted_at"),
        "decided_at": record.get("decided_at"),
        "updated_at": max((s["at"] for s in record.get("log", [])), default=None),
    }


def build_data(records: list[dict] | None = None) -> dict:
    records = all_vendors() if records is None else records
    views = [request_view(r) for r in records]
    views.sort(key=lambda v: (v["stage"] == 4, not v["blocker"], v["updated_at"] or ""), reverse=False)
    open_ = [v for v in views if v["stage"] < 4]
    return {
        "generated_at": iso(now()),
        "required_fields": [_field_label(f) for f in load_json(SCHEMA)["required"]],
        "stages": STAGES,
        "summary": {
            "open": len(open_),
            "waiting_on_person": sum(1 for v in open_ if v["waiting_on"] or v["status"] == "incomplete"),
            "overdue": sum(1 for v in open_ if v["overdue"]),
            "incomplete": sum(1 for v in open_ if v["status"] == "incomplete"),
            "approved": sum(1 for v in views if v["status"] == "approved"),
            "rejected": sum(1 for v in views if v["status"] == "rejected"),
        },
        "metrics": wf.metrics(records),
        "requests": views,
    }


def out_dir() -> Path:
    return data_root() / "dashboard"


def export() -> Path:
    """Write dashboard/data.json (and the page, when exporting outside the repo)."""
    folder = out_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "data.json"
    path.write_text(json.dumps(build_data(), indent=2), encoding="utf-8")
    if folder.resolve() != PAGE.parent.resolve():
        shutil.copyfile(PAGE, folder / "index.html")
    return path


def _git(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=60)


def publish() -> str:
    """Export, then push the page and data to gh-pages. Never touches main."""
    data = export()
    worktree = REPO_ROOT / ".gh-pages"
    if not (worktree / ".git").exists():
        if worktree.exists():
            shutil.rmtree(worktree)
        _git("worktree", "prune")
        if _git("fetch", "origin", BRANCH).returncode == 0:
            r = _git("worktree", "add", "-f", "-B", BRANCH, str(worktree), f"origin/{BRANCH}")
        else:  # first publish: start an empty gh-pages branch
            r = _git("worktree", "add", "-f", "--detach", str(worktree))
            if r.returncode == 0:
                _git("checkout", "--orphan", BRANCH, cwd=worktree)
                _git("rm", "-rf", "--quiet", ".", cwd=worktree)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or "could not check out gh-pages")
    else:
        _git("fetch", "origin", BRANCH, cwd=worktree)
        _git("reset", "--hard", f"origin/{BRANCH}", cwd=worktree)
    shutil.copyfile(PAGE, worktree / "index.html")
    shutil.copyfile(data, worktree / "data.json")
    (worktree / ".nojekyll").touch()
    _git("add", "-A", cwd=worktree)
    if _git("diff", "--cached", "--quiet", cwd=worktree).returncode == 0:
        return "Dashboard already up to date."
    r = _git(
        "-c", "user.name=Vendor Intake Bot", "-c", "user.email=vendor-intake-bot@acme.example",
        "commit", "-m", f"Dashboard data {iso(now())}", cwd=worktree,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    r = _git("push", "origin", f"HEAD:{BRANCH}", cwd=worktree)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "push failed")
    return "Dashboard published."


def auto_publish() -> None:
    """Called after every change from the command line. Skipped in scratch runs
    (tests, `make demo`) and never fails the command it follows."""
    if os.environ.get("INTAKE_HOME") or os.environ.get("INTAKE_NO_PUBLISH"):
        return
    try:
        publish()
    except Exception as e:  # noqa: BLE001 - a dashboard hiccup must not block intake
        print(f"WARNING: dashboard not updated ({e}). The records are saved; tell Ops.", file=sys.stderr)
