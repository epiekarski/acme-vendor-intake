"""Sample requests load in the three states the demo relies on."""

from intake import seed
from intake import workflow as wf
from intake.core import load_vendor

from helpers import ScratchCase


class TestSeed(ScratchCase):
    def test_three_states(self):
        seed.run()
        northwind = load_vendor("northwind-notes")
        quillbase = load_vendor("quillbase")
        harbor = load_vendor("harbor-signal")

        self.assertEqual(northwind["status"], "incomplete")
        self.assertEqual(northwind["missing_fields"], ["business_owner"])

        self.assertEqual(quillbase["status"], "pending_approval")
        self.assertEqual(wf.next_approver(quillbase), "manager")
        self.assertTrue(wf.is_overdue(quillbase))
        self.assertEqual(quillbase["triage"]["approvers"], ["manager"])

        self.assertEqual(harbor["status"], "approved")
        self.assertFalse(wf.is_overdue(harbor))

    def test_rerun_replaces_records(self):
        seed.run()
        seed.run()
        self.assertEqual(load_vendor("quillbase")["status"], "pending_approval")
