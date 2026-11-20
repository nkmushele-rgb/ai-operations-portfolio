"""Tests for the three Make.com scenario build specifications.

Checks structure, and where Node is available, runs the reference rules and
compares the result with the Python implementation.
"""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
for path in (ROOT, TOOLS, os.path.join(ROOT, "PROJECT-03-SALES-AUTOMATION")):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ["AIOPS_LLM"] = "off"

import check_scenarios  # noqa: E402
import leads  # noqa: E402


class StructureTests(unittest.TestCase):
    def test_every_spec_is_structurally_valid(self):
        for folder, _ in check_scenarios.SCENARIOS:
            with self.subTest(scenario=folder):
                spec = check_scenarios.load(folder)
                self.assertEqual(check_scenarios.check_structure(spec, folder), [])

    def test_specs_are_not_claimed_as_verified_in_make(self):
        for folder, _ in check_scenarios.SCENARIOS:
            with self.subTest(scenario=folder):
                self.assertFalse(check_scenarios.load(folder)["verified_in_make"])

    def test_every_spec_names_the_reference_rules(self):
        for folder, _ in check_scenarios.SCENARIOS:
            with self.subTest(scenario=folder):
                spec = check_scenarios.load(folder)
                self.assertTrue(spec["scenario"]["rules_file"].endswith(".js"))


@unittest.skipUnless(check_scenarios.subprocess.run(
    ["node", "--version"], capture_output=True).returncode == 0, "node not installed")
class BehaviourTests(unittest.TestCase):
    def run_spec(self, folder: str, fixture_name: str) -> dict:
        spec = check_scenarios.load(folder)
        ok, result = check_scenarios.run_logic(
            folder, spec, check_scenarios.FIXTURES[fixture_name])
        self.assertTrue(ok, f"rules failed: {result}")
        return result[0]

    def test_support_escalates_a_damaged_goods_refund_request(self):
        payload = self.run_spec("PROJECT-01-CUSTOMER-SUPPORT", "support")
        self.assertEqual(payload["outcome"], "accepted")
        self.assertEqual(payload["category"], "complaint")
        self.assertTrue(payload["escalate"])
        self.assertEqual(payload["status"], "escalated")
        self.assertIn("refund", payload["escalation_reason"])

    def test_support_rejects_an_invalid_email(self):
        spec = check_scenarios.load("PROJECT-01-CUSTOMER-SUPPORT")
        fixture = dict(check_scenarios.FIXTURES["support"], customer_email="broken")
        ok, result = check_scenarios.run_logic(
            "PROJECT-01-CUSTOMER-SUPPORT", spec, fixture)
        self.assertTrue(ok)
        self.assertEqual(result[0]["outcome"], "rejected")

    def test_inventory_matches_python_valuation(self):
        payload = self.run_spec("PROJECT-02-INVENTORY-MANAGEMENT", "inventory")
        self.assertEqual(payload["outcome"], "processed")
        self.assertEqual(payload["applied"], 2)          # the 999 issue is refused
        self.assertEqual(payload["rejected"], 1)
        self.assertAlmostEqual(payload["stock_value"], 600.0, places=2)
        self.assertIn("WTR-500", payload["low_stock"])

    def test_lead_score_matches_the_python_implementation(self):
        payload = self.run_spec("PROJECT-03-SALES-AUTOMATION", "leads")
        fixture = check_scenarios.FIXTURES["leads"]
        expected = leads.score_lead(fixture)
        self.assertEqual(payload["score"], expected["score"])
        self.assertEqual(payload["band"], expected["band"])
        self.assertEqual(payload["segment"], expected["segment"])

    def test_lead_wording_follows_the_band(self):
        payload = self.run_spec("PROJECT-03-SALES-AUTOMATION", "leads")
        self.assertEqual(payload["band"], "A")
        self.assertIn("short call", payload["draft_body"])
        self.assertFalse(payload["approved"])


if __name__ == "__main__":
    unittest.main()
