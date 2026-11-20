# Testing summary

## Result

From the portfolio root, with the model disabled:

```
python -m unittest discover -s tests -v
Ran 90 tests
OK
```

PowerShell may report exit code 1 because unittest writes progress to stderr.
The `OK` line is the result.

## Coverage by suite

| Suite | Tests | Covers |
|---|---|---|
| `test_project01_support.py` | 22 | Validation, classification, escalation, approval gate, escalation refusal, batch errors |
| `test_project02_inventory.py` | 26 | Receipts, issues, adjustments, moving average, oversell refusal, duplicates, alerts, anomalies, valuation |
| `test_project03_leads.py` | 34 | Six-rule scoring, bands, segments, email dedupe, status transitions, approval gate, reporting |
| `test_scenarios.py` | 8 | Make spec structure, unverified status, reference-rule execution, Python parity |

## Test categories

| Category | Examples |
|---|---|
| Happy path | A valid enquiry creates a ticket and draft; an approved follow-up is written to `outbox/` |
| Invalid input | Bad email, empty body, malformed JSON line, negative quantity, unknown SKU |
| Missing data | Null budget, no company, no message, no timeline, vague message flagged for review |
| Duplicate/idempotency | Same ticket reference, same purchase order, same lead reference, same lead email |
| Control failure | Send before approval, send an escalated ticket, send a lost lead, `new → won` |
| Boundary | Score 59 vs 60, issue 40% vs 10% of stock, price swing 25% vs 5% |
| Failure resilience | Ollama off, malformed line in the middle of a batch |

## Model failure is tested by design, not by a unit test

`AIOPS_LLM=off` is set at import time in every suite, so the suite never depends
on a running model. Manual verification with Ollama both running and stopped
confirmed that `drafts.source` changes between `ollama` and `template` while the
pipeline result stays the same.

## The parity check

`tools/check_scenarios.py` reads each project's `make-logic.js`, runs it under
Node with a fixture, and compares the output with the Python logic:

- Support: a damaged-goods refund request is classified as a complaint and escalated.
- Inventory: a 999-case issue is refused and the stock value matches the Python result.
- Sales: score, band and segment match `leads.score_lead()` for the same lead.

This proves the two implementations agree on the fixtures. It does not prove
they agree on every possible input.

## What the tests do not prove

- Business correctness of the rules. They were chosen to be explainable and
  match the synthetic data by construction.
- Conversion, savings or any real-world outcome. There are no real outcomes.
- That the scenarios run inside Make. The rules were executed under plain Node;
  no Make account or blueprint was available.
- That a mailbox, Google Sheet or CRM accepts the output. No external service is connected.
- Concurrency, authentication or rate limiting. These are portfolio demos.
