"""Skill entry point for research packs.

Usage:
  python scripts/check_pack.py start <slug>   # copy the template to packs/<slug>.md
  python scripts/check_pack.py check <slug>   # check completeness and MSA coverage
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from intake.cli import main  # noqa: E402

COMMANDS = {"start": "pack-start", "check": "pack-check"}

if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in COMMANDS:
        print("Usage: check_pack.py <start|check> <slug>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main([COMMANDS[sys.argv[1]], sys.argv[2]]))
