"""Research pack check: what "enough research" means, enforced in code.

A pack is complete when every required section has content, every finding
cites a public https URL, and every MSA checklist item is assessed.
"""

from __future__ import annotations

import re
from pathlib import Path

from .core import POLICIES

REQUIRED_SECTIONS = [
    "Company overview",
    "Intended use",
    "Security and trust",
    "Pricing",
    "Policy check",
    "Open questions",
    "Sources",
]
# Sections whose bullets are findings and must each cite a public URL.
FINDING_SECTIONS = ["Company overview", "Security and trust", "Pricing"]
STATUSES = {"met", "gap", "unknown"}
LINK = re.compile(r"\]\((https://[^)\s]+)\)")
ANY_LINK = re.compile(r"\]\(([^)\s]+)\)")
PLACEHOLDER = re.compile(r"\b(TODO|TBD)\b|<[^>]+>")


def msa_items(path: Path | None = None) -> dict[str, str]:
    """Checklist ids and labels from policies/msa-checklist.md."""
    text = (path or POLICIES / "msa-checklist.md").read_text(encoding="utf-8")
    items = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] and cells[0] not in ("ID", "---") and set(cells[0]) != {"-"}:
            if line.strip().startswith("|"):
                items[cells[0]] = cells[1]
    return items


def split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            current = heading.group(1)
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


def _content_lines(lines: list[str]) -> list[str]:
    return [l for l in lines if l.strip() and not l.strip().startswith("<!--")]


def check_pack(text: str, checklist: dict[str, str] | None = None) -> dict:
    checklist = checklist if checklist is not None else msa_items()
    sections = split_sections(text)
    problems: list[str] = []

    for name in REQUIRED_SECTIONS:
        body = _content_lines(sections.get(name, []))
        if name not in sections:
            problems.append(f"Missing section: {name}")
        elif not body:
            problems.append(f"Empty section: {name}")
        elif any(PLACEHOLDER.search(l) for l in body):
            problems.append(f"Placeholder left in section: {name}")

    for name in FINDING_SECTIONS:
        for line in _content_lines(sections.get(name, [])):
            if line.lstrip().startswith(("-", "*")) and not LINK.search(line):
                problems.append(f"Finding without a public https source in {name}: {line.strip()[:80]}")

    for line in text.splitlines():
        for url in ANY_LINK.findall(line):
            if not url.startswith("https://"):
                problems.append(f"Non-public or non-https link: {url}")

    if not LINK.search("\n".join(sections.get("Sources", []))):
        problems.append("Sources section has no https links")

    # Policy check table: | ID | Finding | Status | Source |
    assessed: dict[str, str] = {}
    for line in sections.get("Policy check", []):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] in checklist:
            status = cells[2].lower()
            if status not in STATUSES:
                problems.append(f"Policy item {cells[0]}: status must be met, gap, or unknown")
                continue
            if status == "met" and not LINK.search(line):
                problems.append(f"Policy item {cells[0]} is 'met' but cites no public source")
            assessed[cells[0]] = status
    for item in checklist:
        if item not in assessed:
            problems.append(f"Policy item not assessed: {item} ({checklist[item]})")

    policy_gaps = [i for i, s in assessed.items() if s in ("gap", "unknown")]
    return {"complete": not problems, "problems": problems, "policy_gaps": policy_gaps}
