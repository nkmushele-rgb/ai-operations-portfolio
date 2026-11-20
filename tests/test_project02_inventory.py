"""Tests for Project 2: AI inventory management."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.join(ROOT, "PROJECT-02-INVENTORY-MANAGEMENT")
for path in (ROOT, PROJECT):
    if path not in sys.path:
        sys.path.insert(0, path)

import inventory  # noqa: E402
from engine import db  # noqa: E402


class InventoryTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.con = inventory.connect(os.path.join(self.tmp.name, "inventory.db"))
        inventory.add_product(self.con, "WTR-500", "Still Water 500ml", "case", "Water", 40)

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def balance(self, sku="WTR-500"):
        return inventory.get_product(self.con, sku)


class ReceiptTests(InventoryTestCase):
    def test_receipt_sets_balance_and_cost(self):
        inventory.receive(self.con, "WTR-500", 10, 18.50, "PO-1")
        product = self.balance()
        self.assertEqual(product["qty"], 10)
        self.assertAlmostEqual(product["avg_cost"], 18.50, places=4)

    def test_moving_average_across_two_prices(self):
        inventory.receive(self.con, "WTR-500", 10, 100.0, "PO-1")
        inventory.receive(self.con, "WTR-500", 10, 200.0, "PO-2")
        product = self.balance()
        self.assertEqual(product["qty"], 20)
        self.assertAlmostEqual(product["avg_cost"], 150.0, places=4)

    def test_receipt_without_cost_is_refused(self):
        with self.assertRaises(ValueError):
            inventory.receive(self.con, "WTR-500", 5, None, "PO-1")

    def test_negative_receipt_is_refused(self):
        with self.assertRaises(ValueError):
            inventory.receive(self.con, "WTR-500", -5, 10.0, "PO-1")

    def test_zero_quantity_is_refused(self):
        with self.assertRaises(ValueError):
            inventory.receive(self.con, "WTR-500", 0, 10.0, "PO-1")

    def test_unknown_sku_is_refused(self):
        with self.assertRaises(LookupError):
            inventory.receive(self.con, "NOPE-1", 5, 10.0, "PO-1")

    def test_duplicate_reference_is_idempotent(self):
        first = inventory.receive(self.con, "WTR-500", 10, 18.50, "PO-1")
        second = inventory.receive(self.con, "WTR-500", 10, 18.50, "PO-1")
        self.assertEqual(first["outcome"], "posted")
        self.assertEqual(second["outcome"], "duplicate")
        self.assertEqual(self.balance()["qty"], 10)


class IssueTests(InventoryTestCase):
    def setUp(self):
        super().setUp()
        inventory.receive(self.con, "WTR-500", 100, 20.0, "PO-1")

    def test_issue_reduces_balance_and_keeps_cost(self):
        result = inventory.issue(self.con, "WTR-500", 25, "SO-1")
        self.assertEqual(result["balance"], 75)
        self.assertAlmostEqual(result["value"], 500.0, places=2)
        self.assertAlmostEqual(self.balance()["avg_cost"], 20.0, places=4)

    def test_issue_more_than_stock_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            inventory.issue(self.con, "WTR-500", 101, "SO-1")
        self.assertIn("only 100", str(caught.exception))
        self.assertEqual(self.balance()["qty"], 100)

    def test_issue_of_entire_stock_is_flagged(self):
        result = inventory.issue(self.con, "WTR-500", 100, "SO-1")
        self.assertIn("100%", result["anomaly"])


class AdjustmentTests(InventoryTestCase):
    def setUp(self):
        super().setUp()
        inventory.receive(self.con, "WTR-500", 50, 20.0, "PO-1")

    def test_negative_adjustment_reduces_stock(self):
        result = inventory.adjust(self.con, "WTR-500", -5, "ADJ-1")
        self.assertEqual(result["balance"], 45)
        self.assertIn("negative adjustment", result["anomaly"])

    def test_adjustment_below_zero_is_refused(self):
        with self.assertRaises(ValueError):
            inventory.adjust(self.con, "WTR-500", -60, "ADJ-1")
        self.assertEqual(self.balance()["qty"], 50)


class AlertTests(InventoryTestCase):
    def setUp(self):
        super().setUp()
        inventory.receive(self.con, "WTR-500", 100, 20.0, "PO-1")

    def test_low_stock_alert_raised_once(self):
        inventory.issue(self.con, "WTR-500", 70, "SO-1")   # 30 left, reorder 40
        inventory.issue(self.con, "WTR-500", 5, "SO-2")    # 25 left, still low
        open_alerts = [a for a in inventory.open_alerts(self.con) if a["kind"] == "low_stock"]
        self.assertEqual(len(open_alerts), 1)

    def test_out_of_stock_alert(self):
        inventory.issue(self.con, "WTR-500", 100, "SO-1")
        kinds = {a["kind"] for a in inventory.open_alerts(self.con)}
        self.assertIn("out_of_stock", kinds)

    def test_alert_reopens_after_stock_recovers(self):
        inventory.issue(self.con, "WTR-500", 70, "SO-1")
        self.assertEqual(len(self._low_stock()), 1)
        inventory.receive(self.con, "WTR-500", 50, 20.0, "PO-2")   # back above reorder
        self.assertEqual(self._low_stock(), [])
        inventory.issue(self.con, "WTR-500", 70, "SO-2")
        self.assertEqual(len(self._low_stock()), 1)

    def test_alert_can_be_acknowledged(self):
        inventory.issue(self.con, "WTR-500", 70, "SO-1")
        self.assertTrue(inventory.open_alerts(self.con))
        for alert in inventory.open_alerts(self.con):
            inventory.acknowledge(self.con, alert["id"])
        self.assertEqual(inventory.open_alerts(self.con), [])

    def test_one_open_alert_per_kind(self):
        inventory.issue(self.con, "WTR-500", 70, "SO-1")
        kinds = [a["kind"] for a in inventory.open_alerts(self.con)]
        self.assertEqual(sorted(kinds), ["anomaly", "low_stock"])

    def _low_stock(self):
        return [a for a in inventory.open_alerts(self.con) if a["kind"] == "low_stock"]


class AnomalyTests(InventoryTestCase):
    def setUp(self):
        super().setUp()
        inventory.receive(self.con, "WTR-500", 100, 20.0, "PO-1")

    def test_large_issue_is_flagged(self):
        result = inventory.issue(self.con, "WTR-500", 50, "SO-1")
        self.assertIsNotNone(result["anomaly"])
        self.assertIn("50%", result["anomaly"])

    def test_normal_issue_is_not_flagged(self):
        result = inventory.issue(self.con, "WTR-500", 10, "SO-1")
        self.assertIsNone(result["anomaly"])

    def test_price_swing_is_flagged(self):
        result = inventory.receive(self.con, "WTR-500", 10, 30.0, "PO-2")
        self.assertIsNotNone(result["anomaly"])
        self.assertIn("purchase price", result["anomaly"])

    def test_small_price_change_is_not_flagged(self):
        result = inventory.receive(self.con, "WTR-500", 10, 21.0, "PO-2")
        self.assertIsNone(result["anomaly"])

    def test_repeated_oversized_issue_is_flagged_against_history(self):
        for index in range(3):
            inventory.issue(self.con, "WTR-500", 5, f"SO-{index}")
        result = inventory.issue(self.con, "WTR-500", 20, "SO-BIG")
        self.assertIsNotNone(result["anomaly"])


class ValuationTests(InventoryTestCase):
    def test_valuation_totals(self):
        inventory.receive(self.con, "WTR-500", 10, 100.0, "PO-1")
        inventory.add_product(self.con, "JUI-ORG", "Orange Juice", "case", "Juice", 5, 5, 50.0)
        data = inventory.valuation(self.con)
        self.assertAlmostEqual(data["total"], 1000.0 + 250.0, places=2)

    def test_low_stock_list_includes_shortfall(self):
        inventory.receive(self.con, "WTR-500", 10, 20.0, "PO-1")
        rows = inventory.low_stock(self.con)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["shortfall"], 30.0, places=3)


class FileTests(InventoryTestCase):
    def test_bad_rows_are_logged_and_batch_continues(self):
        path = os.path.join(self.tmp.name, "batch.jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"sku": "WTR-500", "kind": "receipt", "qty": 10, "unit_cost": 20}) + "\n")
            handle.write("{broken json}\n")
            handle.write(json.dumps({"sku": "WTR-500", "kind": "teleport", "qty": 5}) + "\n")
            handle.write(json.dumps({"sku": "WTR-500", "kind": "issue", "qty": 999}) + "\n")
            handle.write(json.dumps({"sku": "WTR-500", "kind": "issue", "qty": 4}) + "\n")
        result = inventory.apply_file(self.con, path)
        self.assertEqual(len(result["applied"]), 2)
        self.assertEqual(len(result["errors"]), 3)
        self.assertEqual(self.balance()["qty"], 6)


class SampleDataTests(unittest.TestCase):
    def test_sample_batch_matches_documented_result(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        con = inventory.connect(os.path.join(tmp.name, "inventory.db"))
        self.addCleanup(con.close)

        with open(os.path.join(PROJECT, "data", "products.json"), encoding="utf-8") as handle:
            products = json.load(handle)
        for product in products:
            inventory.add_product(con, product["sku"], product["name"], product["unit"],
                                  product["category"], product["reorder_level"],
                                  product["opening_qty"], product["opening_cost"])

        result = inventory.apply_file(con, os.path.join(PROJECT, "data", "movements.jsonl"))
        posted = sum(1 for r in result["applied"] if r["outcome"] == "posted")
        duplicates = sum(1 for r in result["applied"] if r["outcome"] == "duplicate")
        self.assertEqual(posted, 22)
        self.assertEqual(duplicates, 1)
        self.assertEqual(len(result["errors"]), 1)

        summary = inventory.report(con, "2026-11-20")
        self.assertAlmostEqual(summary["stock_value"], 12276.94, places=2)
        self.assertEqual(summary["low_stock_count"], 3)

        balances = {r["sku"]: r["qty"] for r in
                    db.rows(con, "SELECT sku, qty FROM products")}
        self.assertEqual(balances["SNP-CHP"], 0)
        self.assertEqual(balances["WTR-500"], 82)


if __name__ == "__main__":
    unittest.main()
