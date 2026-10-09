import json
import os
import tempfile
import unittest
from pathlib import Path

from helpers import ScratchCase, request
from intake import dashboard, seed
from intake import workflow as wf
from intake.core import load_vendor

SLUG = "brightline-analytics"


class DashboardTests(ScratchCase):
    def test_seed_requests_show_blockers(self):
        seed.run()
        data = dashboard.build_data()
        by_id = {r["id"]: r for r in data["requests"]}
        self.assertEqual(by_id["northwind-notes"]["blocker"]["kind"], "missing")
        self.assertIn("business owner", by_id["northwind-notes"]["blocker"]["text"])
        self.assertEqual(by_id["quillbase"]["blocker"]["kind"], "overdue")
        self.assertEqual(by_id["quillbase"]["waiting_on"]["name"], "Dan Ortiz")
        self.assertIsNone(by_id["harbor-signal"]["blocker"])
        self.assertEqual(by_id["harbor-signal"]["stage"], 4)
        self.assertEqual(data["summary"]["open"], 2)
        self.assertEqual(data["summary"]["overdue"], 1)

    def test_approvers_show_who_is_next(self):
        wf.new_request(request(), confirmed_by="Priya Shah")
        wf.run_triage(SLUG)
        record = load_vendor(SLUG)
        record["status"] = "pending_approval"
        view = dashboard.request_view(record)
        self.assertEqual([a["state"] for a in view["approvers"]], ["waiting", "pending"])
        self.assertEqual(view["waiting_on"]["role"], "manager")
        self.assertEqual([s["actor"] for s in view["log"]], ["bot", "human", "bot"])

    def test_export_writes_data_and_page(self):
        seed.run()
        path = dashboard.export()
        data = json.loads(path.read_text())
        self.assertEqual(len(data["requests"]), 3)
        self.assertTrue((path.parent / "index.html").exists())

    def test_auto_publish_skipped_in_scratch(self):
        dashboard.auto_publish()  # INTAKE_HOME is set: must do nothing, not raise


if __name__ == "__main__":
    unittest.main()
