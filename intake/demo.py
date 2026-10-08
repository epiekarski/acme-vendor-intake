"""`make demo`: the whole Brightline flow from the terminal, in a scratch folder.

This is the backup path if the Bot misbehaves live. It never touches the
real vendors/ or packs/ folders.
"""

from __future__ import annotations

import os
import shutil
import tempfile

from .cli import main
from .core import REPO_ROOT

FIXTURE_PACK = REPO_ROOT / "fixtures" / "brightline" / "pack.md"


def step(title: str, args: list[str], at: str) -> None:
    os.environ["INTAKE_NOW"] = at
    print(f"\n=== {title} ===")
    print("$ python -m intake " + " ".join(f'"{a}"' if " " in a else a for a in args))
    main(args)


def run() -> None:
    home = tempfile.mkdtemp(prefix="intake-demo-")
    os.environ["INTAKE_HOME"] = home
    try:
        step(
            "1. Intake: Bot drafts from Priya's email; business owner missing",
            ["new", "--legal-name", "Brightline Analytics, Inc.",
             "--website", "https://brightline-analytics.example",
             "--customer-data", "yes", "--start", "2026-10-19", "--pilot-days", "90",
             "--requester", "Priya Shah", "--manager", "Dan Ortiz",
             "--source", "email from Priya Shah, 2026-10-05"],
            "2026-10-07T14:00:00+00:00",
        )
        step(
            "1. Intake: Priya gives the owner and confirms",
            ["update", "brightline-analytics", "--business-owner", "Priya Shah",
             "--confirmed-by", "Priya Shah"],
            "2026-10-07T14:05:00+00:00",
        )
        step("2. Triage", ["triage", "brightline-analytics"], "2026-10-07T14:06:00+00:00")

        step("3. Research pack: start from template",
             ["pack-start", "brightline-analytics"], "2026-10-07T14:07:00+00:00")
        step("3. Research pack: check the empty template (should fail)",
             ["pack-check", "brightline-analytics"], "2026-10-07T14:08:00+00:00")
        shutil.copy(FIXTURE_PACK, os.path.join(home, "packs", "brightline-analytics.md"))
        step("3. Research pack: check the Bot's draft",
             ["pack-check", "brightline-analytics"], "2026-10-07T14:20:00+00:00")

        step("4. Approval: Dan Ortiz (manager)",
             ["decide", "brightline-analytics", "--role", "manager", "--name", "Dan Ortiz",
              "--decision", "approved", "--note", "Good fit for the renewal analysis"],
             "2026-10-07T16:00:00+00:00")
        step("5. Status: what's waiting on Security?",
             ["status", "--waiting-on", "security"], "2026-10-07T16:01:00+00:00")
        step("4. Approval: Sam Lee (Security)",
             ["decide", "brightline-analytics", "--role", "security", "--name", "Sam Lee",
              "--decision", "approved", "--note", "OK for pilot; no production PII beyond account IDs"],
             "2026-10-08T10:00:00+00:00")
        step("4. Approval: Rita Okafor (Legal, added for policy gaps)",
             ["decide", "brightline-analytics", "--role", "legal", "--name", "Rita Okafor",
              "--decision", "approved", "--note", "Pilot OK; 72h breach notice required before full contract"],
             "2026-10-08T11:30:00+00:00")
        step("5. Status: final", ["status", "brightline-analytics"], "2026-10-08T11:31:00+00:00")
        step("Metrics", ["metrics"], "2026-10-08T11:32:00+00:00")
    finally:
        shutil.rmtree(home, ignore_errors=True)


if __name__ == "__main__":
    run()
