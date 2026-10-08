"""Policy rules: every rule in tiers.json needs a case that fires it and one that doesn't."""

import unittest

from intake import policy as pol
from intake.core import IntakeError

SUBMITTED = "2026-10-07T14:00:00Z"


def req(**kw):
    base = {"touches_customer_data": False, "pilot_days": 90}
    base.update(kw)
    return base


class TestShippedPolicy(unittest.TestCase):
    def test_policy_file_is_valid(self):
        pol.load_policy()

    def test_customer_data_is_high_tier_with_security(self):
        result = pol.triage(req(touches_customer_data=True), SUBMITTED)
        self.assertEqual(result["tier"], "high")
        self.assertEqual(result["approvers"], ["manager", "security"])
        self.assertEqual(result["sla_due"], "2026-10-09T14:00:00Z")
        self.assertEqual(result["reasons"][0]["rule"], "customer-data")

    def test_no_customer_data_is_standard_manager_only(self):
        result = pol.triage(req(touches_customer_data=False), SUBMITTED)
        self.assertEqual(result["tier"], "standard")
        self.assertEqual(result["approvers"], ["manager"])
        self.assertEqual(result["sla_due"], "2026-10-08T14:00:00Z")
        self.assertEqual(result["reasons"][0]["rule"], "default")


class TestRuleEngine(unittest.TestCase):
    """The engine itself, with small inline policies."""

    def policy(self, rules):
        p = {
            "default_tier": "standard",
            "tiers": {
                "standard": {"approvers": ["manager"], "sla_hours": 24},
                "high": {"approvers": ["manager", "security"], "sla_hours": 48},
            },
            "rules": rules,
        }
        pol.validate_policy(p)
        return p

    def test_add_approvers_rule(self):
        p = self.policy([{
            "id": "long-pilot", "when": {"field": "pilot_days", "op": "gt", "value": 180},
            "add_approvers": ["finance"], "reason": "Long pilot",
        }])
        self.assertEqual(pol.triage(req(pilot_days=200), SUBMITTED, p)["approvers"], ["manager", "finance"])
        self.assertEqual(pol.triage(req(pilot_days=90), SUBMITTED, p)["approvers"], ["manager"])

    def test_highest_tier_wins(self):
        p = self.policy([
            {"id": "a", "when": {"field": "touches_customer_data", "op": "equals", "value": True},
             "set_tier": "high", "reason": "a"},
            {"id": "b", "when": {"field": "pilot_days", "op": "lt", "value": 365},
             "set_tier": "standard", "reason": "b"},
        ])
        self.assertEqual(pol.triage(req(touches_customer_data=True), SUBMITTED, p)["tier"], "high")

    def test_invalid_rules_are_rejected(self):
        with self.assertRaises(IntakeError):
            self.policy([{"id": "x", "when": {"field": "a", "op": "bogus", "value": 1},
                          "set_tier": "high", "reason": "r"}])
        with self.assertRaises(IntakeError):
            self.policy([{"id": "x", "when": {"field": "a", "op": "equals", "value": 1},
                          "set_tier": "nope", "reason": "r"}])
        with self.assertRaises(IntakeError):
            self.policy([{"id": "x", "when": {"field": "a", "op": "equals", "value": 1},
                          "set_tier": "high"}])


if __name__ == "__main__":
    unittest.main()
