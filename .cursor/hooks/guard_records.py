#!/usr/bin/env python3
"""Cursor hook: agents never edit vendor records directly.

Vendor records (vendors/<slug>.yaml) change only through `python -m intake ...`
commands, and the `approvals` block changes only through `intake decide`,
recorded for a named person. This hook enforces that at the tool boundary:

  pre    preToolUse (Write|Delete): deny any direct write to vendors/
  shell  beforeShellExecution: deny shell commands that write into vendors/
  after  afterFileEdit: safety net; if an edit landed anyway, revert it with git

Try it:  echo '{"tool_name":"Write","tool_input":{"path":"vendors/x.yaml"}}' \
         | python3 .cursor/hooks/guard_records.py pre
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORD_PATH = re.compile(r"(^|[/\s'\"])vendors/[^\s'\"]+\.ya?ml", re.IGNORECASE)
# Shell forms that write to a file: redirects, in-place editors, moves, deletes.
SHELL_WRITES = re.compile(
    r"(>|\btee\b|\bsed\s+-[a-zA-Z]*i|\bperl\s+-[a-zA-Z]*i|\byq\s+-i|\brm\b|\bmv\b|\bcp\b|\btruncate\b|\bopen\(.*['\"]w)"
)
# The sanctioned way to change a record.
SANCTIONED = re.compile(r"python3?\s+(-m\s+intake\b|\.cursor/skills/\S+/scripts/\S+\.py)")

DENY = {
    "permission": "deny",
    "user_message": (
        "Blocked: vendor records change only through `python -m intake` commands. "
        "Approvals are recorded only by `intake decide`, for a named person."
    ),
    "agent_message": (
        "Direct writes to vendors/ are not allowed. Use `python -m intake update|triage|decide ...` "
        "or the vendor-triage skill script. Never edit the approvals block."
    ),
}
ALLOW = {"permission": "allow"}


def strings(obj):
    """Every string inside a JSON value, depth first."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def touches_record(payload) -> bool:
    return any(RECORD_PATH.search(s) for s in strings(payload))


def decide_pre(payload):
    return DENY if touches_record(payload.get("tool_input", {})) else ALLOW


def decide_shell(payload):
    command = payload.get("command", "")
    if not RECORD_PATH.search(command):
        return ALLOW
    if SANCTIONED.search(command) and not SHELL_WRITES.search(command):
        return ALLOW
    return DENY if SHELL_WRITES.search(command) else ALLOW


def decide_after(payload):
    path = payload.get("file_path", "")
    if not RECORD_PATH.search(path):
        return {}
    rel = Path(path)
    try:
        rel = rel.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return {}
    subprocess.run(["git", "checkout", "--", str(rel)], cwd=REPO_ROOT, check=False,
                   capture_output=True)
    return {
        "user_message": f"Reverted a direct edit to {rel}. Records change only through `python -m intake`.",
        "agent_message": f"Your edit to {rel} was reverted. Use `python -m intake ...` instead.",
    }


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre"
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}
    result = {"pre": decide_pre, "shell": decide_shell, "after": decide_after}[mode](payload)
    print(json.dumps(result))
    sys.exit(2 if result.get("permission") == "deny" else 0)


if __name__ == "__main__":
    main()
