"""Skill entry point: runs the intake CLI from the repo root.

Usage: python scripts/triage.py <new|update|triage|status> [args...]
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from intake.cli import main  # noqa: E402

ALLOWED = {"new", "update", "triage", "status"}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ALLOWED:
        print(f"Usage: triage.py <{'|'.join(sorted(ALLOWED))}> [args]", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
