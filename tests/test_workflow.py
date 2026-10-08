"""End-to-end: intake -> triage -> pack -> approval -> status."""

import shutil
import unittest

from intake import workflow as wf
from intake.core import IntakeError, REPO_ROOT, load_vendor, pack_path

from helpers import ScratchCase, request

SLUG = "brightline-analytics"
GOOD_PACK = REPO_ROOT / "fixtures" / "brightline" / "pack.md"


class TestIntake(ScratchCase):
    def test_missing_field_stays_incomplete(self):
        record = wf.new_request(request(business_owner=None), confirmed_by="Priya Shah")
        self.assertEqual(record["status"], "incomplete")
        self.assertEqual(record["missing_fields"], ["business_owner"])
        with self.assertRaises(IntakeError):
            wf.run_triage(SLUG)

    def test_unconfirmed_stays_incomplete(self):
        self.assertEqual(wf.new_request(request(), confirmed_by=None)["status"], "incomplete")

    def test_confirmation_is_logged_as_human(self):
        wf.new_request(request(business_owner=None), confirmed_by=None)
        record = wf.update_request(SLUG, {"business_owner": "Priya Shah"}, confirmed_by="Priya Shah")
        self.assertEqual(record["status"], "submitted")
        self.assertEqual(record["log"][-1]["actor"], "human")
        self.assertEqual(record["log"][-1]["by"], "Priya Shah")

    def test_bad_inputs_rejected(self):
        with self.assertRaises(IntakeError):
            wf.new_request(request(website="http://insecure.example"), "Priya Shah")
        with self.assertRaises(IntakeError):
            wf.new_request(request(target_start_date="next Monday"), "Priya Shah")
        with self.assertRaises(IntakeError):
            wf.new_request(request(touches_customer_data="maybe"), "Priya Shah")


class TestFullFlow(ScratchCase):
    def submit_and_research(self):
        wf.new_request(request(), confirmed_by="Priya Shah")
        wf.run_triage(SLUG)
        wf.start_pack(SLUG)
        shutil.copy(GOOD_PACK, pack_path(SLUG))
        return wf.run_pack_check(SLUG)

    def test_template_pack_keeps_researching(self):
        wf.new_request(request(), confirmed_by="Priya Shah")
        wf.run_triage(SLUG)
        wf.start_pack(SLUG)
        self.assertEqual(wf.run_pack_check(SLUG)["status"], "researching")

    def test_policy_gaps_flagged_without_extra_approver(self):
        record = self.submit_and_research()
        self.assertEqual(record["status"], "pending_approval")
        self.assertTrue(record["pack"]["policy_gaps"])
        self.assertEqual(record["triage"]["approvers"], ["manager", "security"])

    def test_approvals_in_order_then_approved(self):
        self.submit_and_research()
        with self.assertRaises(IntakeError):
            wf.record_decision(SLUG, "security", "Sam Lee", "approved")  # manager first
        self.at("2026-10-07T16:00:00+00:00")
        wf.record_decision(SLUG, "manager", "Dan Ortiz", "approved")
        self.assertEqual(wf.next_approver(load_vendor(SLUG)), "security")
        record = wf.record_decision(SLUG, "security", "Sam Lee", "approved")
        self.assertEqual(record["status"], "approved")
        humans = [s for s in record["log"] if s["actor"] == "human"]
        self.assertEqual([s["by"] for s in humans], ["Priya Shah", "Dan Ortiz", "Sam Lee"])

    def test_rejection_ends_request(self):
        self.submit_and_research()
        record = wf.record_decision(SLUG, "manager", "Dan Ortiz", "rejected", "No budget")
        self.assertEqual(record["status"], "rejected")
        self.assertEqual(wf.pending_roles(record), [])

    def test_bot_cannot_approve(self):
        self.submit_and_research()
        for name in ("", "bot", "Vendor Intake Bot"):
            with self.assertRaises(IntakeError):
                wf.record_decision(SLUG, "manager", name, "approved")

    def test_unrequired_role_cannot_approve(self):
        self.submit_and_research()
        with self.assertRaises(IntakeError):
            wf.record_decision(SLUG, "finance", "Marcus Hale", "approved")

    def test_overdue_and_metrics(self):
        self.submit_and_research()
        self.at("2026-10-10T00:00:00+00:00")  # past the 48h SLA
        self.assertTrue(wf.is_overdue(load_vendor(SLUG)))
        wf.record_decision(SLUG, "manager", "Dan Ortiz", "approved")
        record = wf.record_decision(SLUG, "security", "Sam Lee", "approved")
        self.assertFalse(wf.is_overdue(record))
        m = wf.metrics([record])
        self.assertEqual(m["decided"], 1)
        self.assertEqual(m["median_cycle_hours"], 58.0)


if __name__ == "__main__":
    unittest.main()
