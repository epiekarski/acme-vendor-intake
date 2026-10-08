"""Shared helpers: paths, clock, and vendor record I/O.

Policy files always come from the repo. Vendor records and packs live under
INTAKE_HOME (defaults to the repo root), so `make demo` and the tests can work
in a scratch folder without touching real records.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICIES = REPO_ROOT / "policies"
SCHEMA = REPO_ROOT / "schema" / "vendor.schema.json"
PACK_TEMPLATE = REPO_ROOT / ".cursor" / "skills" / "research-pack" / "assets" / "pack_template.md"


class IntakeError(Exception):
    """A problem the person or Bot running the command needs to fix."""


def data_root() -> Path:
    return Path(os.environ.get("INTAKE_HOME", REPO_ROOT))


def vendors_dir() -> Path:
    return data_root() / "vendors"


def packs_dir() -> Path:
    return data_root() / "packs"


def now() -> datetime:
    """Current time in UTC. INTAKE_NOW (ISO 8601) pins it for tests and demos."""
    pinned = os.environ.get("INTAKE_NOW")
    if pinned:
        return datetime.fromisoformat(pinned).astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    for suffix in ("-inc", "-llc", "-ltd", "-corp", "-co"):
        if slug.endswith(suffix):
            slug = slug[: -len(suffix)]
    return slug


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def vendor_path(slug: str) -> Path:
    return vendors_dir() / f"{slug}.yaml"


def pack_path(slug: str) -> Path:
    return packs_dir() / f"{slug}.md"


def load_vendor(slug: str) -> dict:
    path = vendor_path(slug)
    if not path.exists():
        raise IntakeError(f"No vendor record at {path}. Run `intake new` first.")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_vendor(record: dict) -> Path:
    path = vendor_path(record["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(record, f, sort_keys=False, allow_unicode=True)
    return path


def all_vendors() -> list[dict]:
    folder = vendors_dir()
    if not folder.exists():
        return []
    records = []
    for path in sorted(folder.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            records.append(yaml.safe_load(f))
    return records


def log_step(record: dict, step: str, actor: str, by: str, detail: str) -> None:
    """Append to the audit log. actor is 'bot' or 'human'; by is a name."""
    if actor not in ("bot", "human"):
        raise IntakeError(f"actor must be 'bot' or 'human', got {actor!r}")
    record.setdefault("log", []).append(
        {"step": step, "actor": actor, "by": by, "at": iso(now()), "detail": detail}
    )
