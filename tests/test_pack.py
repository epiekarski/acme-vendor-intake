"""Research pack check: what "enough research" means."""

import unittest

from intake.core import PACK_TEMPLATE, REPO_ROOT
from intake.pack import check_pack, msa_items

GOOD = (REPO_ROOT / "fixtures" / "brightline" / "pack.md").read_text(encoding="utf-8")


class TestPackCheck(unittest.TestCase):
    def test_checklist_has_seven_items(self):
        self.assertEqual(len(msa_items()), 7)

    def test_example_pack_is_complete_with_gaps(self):
        result = check_pack(GOOD)
        self.assertTrue(result["complete"], result["problems"])
        self.assertEqual(
            sorted(result["policy_gaps"]),
            ["breach-notice", "liability", "residency", "subprocessors"],
        )

    def test_empty_template_fails(self):
        result = check_pack(PACK_TEMPLATE.read_text(encoding="utf-8"))
        self.assertFalse(result["complete"])

    def test_finding_without_source_fails(self):
        bad = GOOD.replace(
            "- Growth plan at $1,200 per month fits the pilot; Starter is free up to 10,000 events ([pricing](https://brightline-analytics.example/pricing))",
            "- Growth plan is about $1,200 per month",
        )
        result = check_pack(bad)
        self.assertFalse(result["complete"])
        self.assertTrue(any("Pricing" in p for p in result["problems"]))

    def test_missing_section_fails(self):
        bad = GOOD.replace("## Open questions", "## Notes")
        self.assertIn("Missing section: Open questions", check_pack(bad)["problems"])

    def test_met_without_source_fails(self):
        bad = GOOD.replace(
            "| dpa | Standard DPA published | met | [DPA](https://brightline-analytics.example/legal/dpa) |",
            "| dpa | Standard DPA published | met | |",
        )
        self.assertTrue(any("dpa" in p for p in check_pack(bad)["problems"]))

    def test_unassessed_policy_item_fails(self):
        bad = "\n".join(l for l in GOOD.splitlines() if not l.startswith("| liability"))
        self.assertTrue(any("liability" in p for p in check_pack(bad)["problems"]))

    def test_non_public_link_fails(self):
        bad = GOOD.replace("](https://brightline-analytics.example/pricing))", "](http://intranet.acme/pricing))")
        self.assertTrue(any("Non-public" in p for p in check_pack(bad)["problems"]))


if __name__ == "__main__":
    unittest.main()
