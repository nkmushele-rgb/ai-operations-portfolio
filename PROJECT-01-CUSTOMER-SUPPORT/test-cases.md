# Test cases — customer support triage

Run: `python -m unittest tests.test_project01_support -v` from the portfolio root.
22 tests, all passing. The model is disabled (`AIOPS_LLM=off`) so every
result is reproducible.

## Happy path

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 1 | `test_accepted_message_creates_ticket_and_draft` | Valid enquiry | Ticket and one draft created, status `awaiting_approval` | Pass |
| 2 | `test_approved_draft_can_be_sent` | Approve then send | `outbox/CS-…txt` written, addressee present | Pass |
| 3 | `test_report_counts` | 2 valid, 1 invalid | total 2, rejected 1, escalated 1 | Pass |
| 4 | `test_sample_inbox` | `data/inbox.jsonl` | accepted 9, rejected 3, escalated 4, needs review 1 | Pass |

## Invalid input

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 5 | `test_invalid_email_is_rejected_and_recorded` | `customer_email = "not-an-email"` | Rejected, row in `rejected`, no ticket | Pass |
| 6 | `test_missing_body_is_rejected` | Empty body | Rejected | Pass |
| 7 | `test_too_short_body_is_rejected` | Body `"Thanks"` | Rejected, "at least 10 characters" | Pass |
| 8 | `test_malformed_json_line_is_rejected_not_fatal` | One broken line between two good ones | 2 accepted, 1 line error, batch continues | Pass |
| 9 | `test_blank_lines_are_skipped` | Blank lines around one message | 1 accepted, no error | Pass |

## Missing data and edge cases

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 10 | `test_vague_message_is_flagged_for_review` | "it is about the thing we discussed" | Category `other`, `needs_review = 1` | Pass |
| 11 | `test_duplicate_external_id_is_idempotent` | Same message twice | Second returns `duplicate`, one ticket | Pass |
| 12 | `test_stock_out_is_a_request_not_an_inquiry` | "completely out of the 1 litre bottles" | Category `request`, urgency `high` | Pass |
| 13 | `test_safety_mention_is_a_complaint` | "allergic reaction" | Category `complaint` | Pass |

## Classification rules

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 14 | `test_complaint_is_detected` | "arrived damaged and leaking" | `complaint`, `negative` | Pass |
| 15 | `test_inquiry_is_detected` | "which days do you deliver" | `inquiry` | Pass |
| 16 | `test_sensitive_language_escalates` | "issue a refund" | Escalated, reason mentions refund | Pass |
| 17 | `test_urgent_language_escalates` | "We need this today" | Escalated | Pass |
| 18 | `test_plain_inquiry_does_not_escalate` | Routine delivery question | Not escalated, empty reason | Pass |

## Control failures

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 19 | `test_send_requires_approval` | Send without approval | `PermissionError` | Pass |
| 20 | `test_escalated_ticket_cannot_be_auto_sent` | Approve then send an escalated ticket | `PermissionError` | Pass |
| 21 | `test_escalated_ticket_is_held` | Complaint with refund | Status `escalated`, reason stored | Pass |
| 22 | `test_approve_unknown_ticket_raises` | Ticket id 999 | `LookupError` | Pass |

## Model failure

Not a unit test, because it depends on a running service. Verified manually:

1. With Ollama stopped, `run.py demo` completes and every draft has
   `source = 'template'`.
2. With Ollama running, `drafts.source = 'ollama'` and the reply is free text.

The pipeline does not depend on the model being present. That is the point of
the design, and it is why classification was kept in rules.

## What these tests do not prove

- That the classification is *correct* in a business sense. The rules match
  the sample data by construction. A real deployment needs a labelled set of
  a few hundred real messages to measure precision and recall.
- That the reply reads well. Only a human review can judge that.
- That sending works against a real mailbox. It writes a file.
