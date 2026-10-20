"""The Cursor hook that keeps agents out of vendor records."""

import json
import subprocess
import sys
import unittest

from intake.core import REPO_ROOT

HOOK = REPO_ROOT / ".cursor" / "hooks" / "guard_records.py"


def run(mode: str, payload: dict) -> tuple[dict, int]:
    proc = subprocess.run(
        [sys.executable, str(HOOK), mode],
        input=json.dumps(payload), capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return json.loads(proc.stdout), proc.returncode


class TestHooksJson(unittest.TestCase):
    def test_hooks_json_wires_the_script(self):
        cfg = json.loads((REPO_ROOT / ".cursor" / "hooks.json").read_text())
        self.assertEqual(cfg["version"], 1)
        for event in ("preToolUse", "beforeShellExecution", "afterFileEdit"):
            commands = [h["command"] for h in cfg["hooks"][event]]
            self.assertTrue(any("guard_records.py" in c for c in commands), event)


class TestPreToolUse(unittest.TestCase):
    def test_write_to_vendor_record_denied(self):
        for tool_input in (
            {"path": "vendors/brightline-analytics.yaml", "contents": "approvals: []"},
            {"file_path": "/repo/vendors/brightline-analytics.yml"},
            {"edits": [{"old_string": "approvals: []", "new_string": "approvals:\n- approved",
                        "file": "vendors/x.yaml"}]},
        ):
            result, code = run("pre", {"tool_name": "Write", "tool_input": tool_input})
            self.assertEqual(result["permission"], "deny", tool_input)
            self.assertEqual(code, 2)

    def test_delete_vendor_record_denied(self):
        result, _ = run("pre", {"tool_name": "Delete", "tool_input": {"path": "vendors/x.yaml"}})
        self.assertEqual(result["permission"], "deny")

    def test_other_writes_allowed(self):
        for path in ("packs/brightline-analytics.md", "policies/tiers.json", "README.md"):
            result, code = run("pre", {"tool_name": "Write", "tool_input": {"path": path}})
            self.assertEqual(result["permission"], "allow", path)
            self.assertEqual(code, 0)


class TestBeforeShell(unittest.TestCase):
    def test_intake_commands_allowed(self):
        for cmd in (
            'python -m intake decide brightline-analytics --role manager --name "Dan Ortiz" --decision approved',
            "python -m intake status --overdue",
            "cat vendors/brightline-analytics.yaml",
            "python3 .cursor/skills/vendor-triage/scripts/triage.py triage brightline-analytics",
            "make test",
        ):
            result, _ = run("shell", {"command": cmd})
            self.assertEqual(result["permission"], "allow", cmd)

    def test_shell_writes_to_records_denied(self):
        for cmd in (
            "echo 'approvals: [{role: manager, decision: approved}]' >> vendors/brightline-analytics.yaml",
            "sed -i 's/pending_approval/approved/' vendors/brightline-analytics.yaml",
            "rm vendors/brightline-analytics.yaml",
            "cp /tmp/fake.yaml vendors/brightline-analytics.yaml",
            "python -c \"open('vendors/x.yaml','w').write('approved')\"",
        ):
            result, code = run("shell", {"command": cmd})
            self.assertEqual(result["permission"], "deny", cmd)
            self.assertEqual(code, 2)


class TestAfterFileEdit(unittest.TestCase):
    def test_non_record_edit_ignored(self):
        result, code = run("after", {"file_path": str(REPO_ROOT / "packs" / "x.md"), "edits": []})
        self.assertEqual(result, {})
        self.assertEqual(code, 0)

    def test_record_edit_reports_revert(self):
        result, _ = run("after", {"file_path": str(REPO_ROOT / "vendors" / "x.yaml"), "edits": []})
        self.assertIn("Reverted", result["user_message"])


if __name__ == "__main__":
    unittest.main()
