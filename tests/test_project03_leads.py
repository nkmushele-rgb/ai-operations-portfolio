"""Tests for Project 3: AI sales lead management."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.join(ROOT, "PROJECT-03-SALES-AUTOMATION")
for path in (ROOT, PROJECT):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ["AIOPS_LLM"] = "off"

import leads  # noqa: E402
from engine import db  # noqa: E402


def sample(**overrides) -> dict:
    base = {
        "external_id": "LD-9001",
        "name": "Test Buyer",
        "email": "test.buyer@example.com",
        "company": "Test Trading",
        "source": "website",
        "role": "Manager",
        "employees": 20,
        "budget": 2000,
        "timeline": "1-3 months",
        "message": "We would like a price list for weekly water deliveries.",
    }
    base.update(overrides)
    return base


class ScoringTests(unittest.TestCase):
    def test_strong_referral_scores_band_a(self):
        result = leads.score_lead({
            "source": "referral", "budget": 15000, "timeline": "immediate",
            "role": "Owner", "employees": 120, "email": "a@b.com",
            "company": "X", "message": "hello"})
        self.assertEqual(result["score"], 73)
        self.assertEqual(result["band"], "A")
        self.assertEqual(result["segment"], "key account")

    def test_just_below_band_a_is_band_b(self):
        result = leads.score_lead({
            "source": "event", "budget": 8000, "timeline": "next quarter",
            "role": "Director", "employees": 60, "email": "a@b.com",
            "company": "X", "message": "hello"})
        self.assertEqual(result["score"], 59)
        self.assertEqual(result["band"], "B")

    def test_missing_budget_does_not_crash(self):
        result = leads.score_lead({
            "source": "linkedin", "budget": None, "timeline": "later",
            "role": "Procurement Officer", "employees": 8, "email": "a@b.com",
            "company": "X", "message": "hello"})
        self.assertEqual(result["score"], 20)
        self.assertIn("no budget stated", result["score_reason"])

    def test_zero_budget_scores_nothing(self):
        result = leads.score_lead({
            "source": "event", "budget": 0, "timeline": "later",
            "role": "Event Manager", "employees": 15, "email": "a@b.com",
            "company": "X", "message": "hello"})
        self.assertIn("budget stated as zero", result["score_reason"])
        self.assertEqual(result["score"], 25)

    def test_reason_lists_every_component(self):
        result = leads.score_lead(sample())
        self.assertEqual(result["score_reason"].count("+"), 6)

    def test_small_company_is_small_segment(self):
        result = leads.score_lead(sample(employees=3, budget=500))
        self.assertEqual(result["segment"], "small")

    def test_incomplete_contact_loses_points(self):
        full = leads.score_lead(sample())
        partial = leads.score_lead(sample(company=None, message=None))
        self.assertLess(partial["score"], full["score"])


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.con = leads.connect(os.path.join(self.tmp.name, "sales.db"))
        self._original_outbox = leads.OUTBOX
        leads.OUTBOX = os.path.join(self.tmp.name, "outbox")

    def tearDown(self):
        self.con.close()
        leads.OUTBOX = self._original_outbox
        self.tmp.cleanup()

    def test_invalid_email_is_rejected(self):
        result = leads.capture(self.con, sample(email="broken-at-example.com"))
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(db.scalar(self.con, "SELECT COUNT(*) FROM rejected"), 1)
        self.assertEqual(db.scalar(self.con, "SELECT COUNT(*) FROM leads"), 0)

    def test_missing_name_is_rejected(self):
        result = leads.capture(self.con, sample(name=""))
        self.assertEqual(result["outcome"], "rejected")

    def test_accepted_lead_gets_draft_and_activity(self):
        result = leads.capture(self.con, sample())
        self.assertEqual(result["outcome"], "accepted")
        self.assertEqual(result["draft_source"], "template")
        self.assertEqual(db.scalar(self.con, "SELECT COUNT(*) FROM drafts"), 1)
        self.assertEqual(db.scalar(self.con, "SELECT COUNT(*) FROM activities"), 1)

    def test_duplicate_reference(self):
        leads.capture(self.con, sample())
        again = leads.capture(self.con, sample())
        self.assertEqual(again["outcome"], "duplicate")
        self.assertEqual(again["matched_on"], "reference")
        self.assertEqual(db.scalar(self.con, "SELECT COUNT(*) FROM leads"), 1)

    def test_duplicate_email_under_new_reference(self):
        leads.capture(self.con, sample())
        again = leads.capture(self.con, sample(external_id="LD-9002"))
        self.assertEqual(again["outcome"], "duplicate")
        self.assertEqual(again["matched_on"], "email")
        self.assertEqual(db.scalar(self.con, "SELECT COUNT(*) FROM leads"), 1)

    def test_draft_text_matches_band(self):
        result = leads.capture(self.con, sample())
        draft = db.one(self.con, "SELECT body FROM drafts WHERE lead_id = ?", (result["lead_id"],))
        self.assertIn("Test", draft["body"])
        self.assertIn("Kelvin", draft["body"])


class SendTests(CaptureTests):
    def test_send_requires_approval(self):
        result = leads.capture(self.con, sample())
        with self.assertRaises(PermissionError):
            leads.send(self.con, result["lead_id"])

    def test_approved_follow_up_is_written(self):
        result = leads.capture(self.con, sample())
        leads.approve(self.con, result["lead_id"], "Kelvin M")
        sent = leads.send(self.con, result["lead_id"])
        self.assertTrue(os.path.exists(sent["file"]))
        with open(sent["file"], encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("test.buyer@example.com", content)

    def test_lost_lead_cannot_be_sent(self):
        result = leads.capture(self.con, sample())
        leads.set_status(self.con, result["lead_id"], "lost")
        leads.approve(self.con, result["lead_id"], "Kelvin M")
        with self.assertRaises(PermissionError):
            leads.send(self.con, result["lead_id"])


class PipelineTests(CaptureTests):
    def test_valid_transition(self):
        result = leads.capture(self.con, sample())
        leads.set_status(self.con, result["lead_id"], "contacted")
        lead = db.one(self.con, "SELECT status FROM leads WHERE id = ?", (result["lead_id"],))
        self.assertEqual(lead["status"], "contacted")

    def test_invalid_transition_is_refused(self):
        result = leads.capture(self.con, sample())
        with self.assertRaises(ValueError):
            leads.set_status(self.con, result["lead_id"], "won")   # new -> won is not allowed

    def test_unknown_status_is_refused(self):
        result = leads.capture(self.con, sample())
        with self.assertRaises(ValueError):
            leads.set_status(self.con, result["lead_id"], "maybe")

    def test_report_counts(self):
        leads.capture(self.con, sample())
        leads.capture(self.con, sample(external_id="LD-9003", email="other@example.com",
                                       source="referral", role="Owner", budget=9000,
                                       employees=80, timeline="immediate"))
        leads.capture(self.con, sample(external_id="LD-9004", email="bad"))
        summary = leads.weekly_report(self.con)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["rejected"], 1)
        bands = {row["band"]: row["n"] for row in summary["by_band"]}
        self.assertEqual(bands.get("A"), 1)

    def test_bad_json_line_is_logged(self):
        path = os.path.join(self.tmp.name, "leads.jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(sample()) + "\n")
            handle.write("{oops}\n")
        result = leads.capture_file(self.con, path)
        self.assertEqual(result["counts"].get("accepted"), 1)
        self.assertEqual(len(result["errors"]), 1)


class SampleDataTests(unittest.TestCase):
    def test_sample_leads_match_documented_result(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        con = leads.connect(os.path.join(tmp.name, "sales.db"))
        self.addCleanup(con.close)
        original = leads.OUTBOX
        leads.OUTBOX = os.path.join(tmp.name, "outbox")
        self.addCleanup(setattr, leads, "OUTBOX", original)

        result = leads.capture_file(con, os.path.join(PROJECT, "data", "leads.jsonl"))
        self.assertEqual(result["counts"], {"accepted": 10, "rejected": 1, "duplicate": 1})

        summary = leads.weekly_report(con)
        self.assertEqual(summary["total"], 10)
        self.assertEqual(summary["average_score"], 43.3)
        self.assertAlmostEqual(summary["stated_pipeline_value"], 54500.0, places=2)

        top = db.rows(con, "SELECT external_id, score, band FROM leads "
                           "ORDER BY score DESC LIMIT 2")
        self.assertEqual([row["external_id"] for row in top], ["LD-2001", "LD-2009"])
        self.assertEqual({row["band"] for row in top}, {"A"})


if __name__ == "__main__":
    unittest.main()
