"""Tests for Project 1: AI customer support triage.

Run from the portfolio root:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.join(ROOT, "PROJECT-01-CUSTOMER-SUPPORT")
for path in (ROOT, PROJECT):
    if path not in sys.path:
        sys.path.insert(0, path)

# Force the deterministic template path so assertions never depend on a model.
os.environ["AIOPS_LLM"] = "off"

import support  # noqa: E402
from engine import db  # noqa: E402


def message(**overrides) -> dict:
    base = {
        "external_id": "T-001",
        "channel": "email",
        "customer_name": "Test Customer",
        "customer_email": "test.customer@example.com",
        "subject": "Question about delivery",
        "body": "Could you tell me when the next delivery to our area is?",
    }
    base.update(overrides)
    return base


class ClassificationTests(unittest.TestCase):
    def test_complaint_is_detected(self):
        verdict = support.classify("Damaged goods", "Three cartons arrived damaged and leaking.")
        self.assertEqual(verdict["category"], "complaint")
        self.assertEqual(verdict["sentiment"], "negative")
        self.assertEqual(verdict["needs_review"], 0)

    def test_inquiry_is_detected(self):
        verdict = support.classify("Delivery", "Could you tell me which days you deliver?")
        self.assertEqual(verdict["category"], "inquiry")

    def test_vague_message_is_flagged_for_review(self):
        verdict = support.classify("Account", "Hi, it is about the thing we discussed.")
        self.assertEqual(verdict["category"], "other")
        self.assertEqual(verdict["needs_review"], 1)

    def test_stock_out_is_a_request_not_an_inquiry(self):
        verdict = support.classify("URGENT", "We are completely out of the 1 litre bottles.")
        self.assertEqual(verdict["category"], "request")
        self.assertEqual(verdict["urgency"], "high")

    def test_safety_mention_is_a_complaint(self):
        verdict = support.classify("Reaction", "My customer had an allergic reaction.")
        self.assertEqual(verdict["category"], "complaint")


class EscalationTests(unittest.TestCase):
    def test_sensitive_language_escalates(self):
        escalated, reason = support.escalation(
            "billing", "low", "neutral", "Please issue a refund for invoice 2291.")
        self.assertTrue(escalated)
        self.assertIn("refund", reason)

    def test_urgent_language_escalates(self):
        escalated, _ = support.escalation("request", "high", "neutral", "We need this today.")
        self.assertTrue(escalated)

    def test_plain_inquiry_does_not_escalate(self):
        escalated, reason = support.escalation(
            "inquiry", "low", "neutral", "Which days do you deliver to Karen?")
        self.assertFalse(escalated)
        self.assertEqual(reason, "")


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "support.db")
        self.outbox = os.path.join(self.tmp.name, "outbox")
        self._original_outbox = support.OUTBOX
        support.OUTBOX = self.outbox
        self.con = support.connect(self.db_path)

    def tearDown(self):
        self.con.close()
        support.OUTBOX = self._original_outbox
        self.tmp.cleanup()

    def test_invalid_email_is_rejected_and_recorded(self):
        result = support.ingest(self.con, message(customer_email="not-an-email"))
        self.assertEqual(result["outcome"], "rejected")
        self.assertIn("customer_email", result["problems"][0])
        rejected = db.scalar(self.con, "SELECT COUNT(*) FROM rejected")
        self.assertEqual(rejected, 1)
        self.assertEqual(db.scalar(self.con, "SELECT COUNT(*) FROM tickets"), 0)

    def test_missing_body_is_rejected(self):
        result = support.ingest(self.con, message(body=""))
        self.assertEqual(result["outcome"], "rejected")

    def test_too_short_body_is_rejected(self):
        result = support.ingest(self.con, message(body="Thanks"))
        self.assertEqual(result["outcome"], "rejected")

    def test_accepted_message_creates_ticket_and_draft(self):
        result = support.ingest(self.con, message())
        self.assertEqual(result["outcome"], "accepted")
        self.assertEqual(result["draft_source"], "template")
        self.assertEqual(db.scalar(self.con, "SELECT COUNT(*) FROM drafts"), 1)
        self.assertEqual(result["status"], "awaiting_approval")

    def test_duplicate_external_id_is_idempotent(self):
        first = support.ingest(self.con, message())
        second = support.ingest(self.con, message())
        self.assertEqual(first["outcome"], "accepted")
        self.assertEqual(second["outcome"], "duplicate")
        self.assertEqual(db.scalar(self.con, "SELECT COUNT(*) FROM tickets"), 1)

    def test_escalated_ticket_is_held(self):
        result = support.ingest(self.con, message(
            external_id="T-002",
            subject="Damaged delivery",
            body="The cartons arrived damaged and I want a refund."))
        self.assertEqual(result["status"], "escalated")
        ticket = db.one(self.con, "SELECT * FROM tickets WHERE id = ?", (result["ticket_id"],))
        self.assertIn("refund", ticket["escalation_reason"])

    def test_send_requires_approval(self):
        result = support.ingest(self.con, message())
        with self.assertRaises(PermissionError):
            support.send(self.con, result["ticket_id"])

    def test_approved_draft_can_be_sent(self):
        result = support.ingest(self.con, message())
        support.approve(self.con, result["ticket_id"], "Kelvin M")
        sent = support.send(self.con, result["ticket_id"])
        self.assertEqual(sent["status"], "sent")
        self.assertTrue(os.path.exists(sent["file"]))
        with open(sent["file"], encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("test.customer@example.com", content)
        self.assertIn("Customer Support", content)

    def test_escalated_ticket_cannot_be_auto_sent(self):
        result = support.ingest(self.con, message(
            external_id="T-003",
            subject="Legal threat",
            body="This is unacceptable, we are taking legal advice about the damaged stock."))
        support.approve(self.con, result["ticket_id"], "Kelvin M")
        with self.assertRaises(PermissionError):
            support.send(self.con, result["ticket_id"])

    def test_approve_unknown_ticket_raises(self):
        with self.assertRaises(LookupError):
            support.approve(self.con, 999, "Kelvin M")

    def test_report_counts(self):
        support.ingest(self.con, message())
        support.ingest(self.con, message(external_id="T-004",
                                         body="The goods arrived damaged and late."))
        support.ingest(self.con, message(external_id="T-005", customer_email="bad"))
        summary = support.report(self.con)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["rejected"], 1)
        self.assertEqual(summary["escalated"], 1)


class FileIngestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.con = support.connect(os.path.join(self.tmp.name, "support.db"))
        self._original_outbox = support.OUTBOX
        support.OUTBOX = os.path.join(self.tmp.name, "outbox")

    def tearDown(self):
        self.con.close()
        support.OUTBOX = self._original_outbox
        self.tmp.cleanup()

    def test_malformed_json_line_is_rejected_not_fatal(self):
        path = os.path.join(self.tmp.name, "inbox.jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(message(external_id="T-100")) + "\n")
            handle.write("{not valid json}\n")
            handle.write(json.dumps(message(external_id="T-101", body="Where is my order please?")) + "\n")
        result = support.ingest_file(self.con, path)
        self.assertEqual(result["counts"].get("accepted"), 2)
        self.assertEqual(len(result["line_errors"]), 1)
        self.assertEqual(db.scalar(self.con, "SELECT COUNT(*) FROM rejected"), 1)

    def test_blank_lines_are_skipped(self):
        path = os.path.join(self.tmp.name, "inbox.jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n\n" + json.dumps(message()) + "\n\n")
        result = support.ingest_file(self.con, path)
        self.assertEqual(result["counts"].get("accepted"), 1)


class SampleDataTests(unittest.TestCase):
    """The shipped demo inbox must produce the documented result."""

    def test_sample_inbox(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        con = support.connect(os.path.join(tmp.name, "support.db"))
        self.addCleanup(con.close)
        original = support.OUTBOX
        support.OUTBOX = os.path.join(tmp.name, "outbox")
        self.addCleanup(setattr, support, "OUTBOX", original)

        result = support.ingest_file(con, os.path.join(PROJECT, "data", "inbox.jsonl"))
        self.assertEqual(result["counts"], {"accepted": 9, "rejected": 3})
        summary = support.report(con)
        self.assertEqual(summary["total"], 9)
        self.assertEqual(summary["escalated"], 4)
        self.assertEqual(summary["needs_review"], 1)


if __name__ == "__main__":
    unittest.main()
