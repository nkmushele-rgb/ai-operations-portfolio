# Test cases — sales lead management

Run: `python -m unittest tests.test_project03_leads -v` from the portfolio root.
34 tests, all passing. The model is disabled so results are reproducible.

## Scoring

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 1 | `test_strong_referral_scores_band_a` | Referral, owner, 120 staff, 15,000, immediate | 73 points, band A, key account | Pass |
| 2 | `test_just_below_band_a_is_band_b` | Event, director, 60 staff, 8,000, next quarter | 59 points, band B | Pass |
| 3 | `test_missing_budget_does_not_crash` | Budget null | 20 points, reason says "no budget stated" | Pass |
| 4 | `test_zero_budget_scores_nothing` | Budget 0 | 25 points, reason says "budget stated as zero" | Pass |
| 5 | `test_reason_lists_every_component` | Full lead | 6 rule components in the reason | Pass |
| 6 | `test_small_company_is_small_segment` | 3 staff, budget 500 | Segment `small` | Pass |
| 7 | `test_incomplete_contact_loses_points` | No company, no message | Lower score than the complete version | Pass |

## Capture and validation

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 8 | `test_invalid_email_is_rejected` | `broken-at-example.com` | Rejected, logged, no lead created | Pass |
| 9 | `test_missing_name_is_rejected` | Empty name | Rejected | Pass |
| 10 | `test_accepted_lead_gets_draft_and_activity` | Valid lead | One draft, one activity, template source | Pass |
| 11 | `test_duplicate_reference` | Same lead twice | Second is `duplicate`, matched on `reference` | Pass |
| 12 | `test_duplicate_email_under_new_reference` | Same email, new reference | Second is `duplicate`, matched on `email` | Pass |
| 13 | `test_draft_text_matches_band` | Band A lead | Draft addressed to the contact and signed off | Pass |

## Approval and sending

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 14 | `test_send_requires_approval` | Send without approval | `PermissionError` | Pass |
| 15 | `test_approved_follow_up_is_written` | Approve then send | File written with the lead's email in it | Pass |
| 16 | `test_lost_lead_cannot_be_sent` | Mark lost, approve, send | `PermissionError` | Pass |

## Pipeline

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 17 | `test_valid_transition` | new → contacted | Status updated | Pass |
| 18 | `test_invalid_transition_is_refused` | new → won | `ValueError` | Pass |
| 19 | `test_unknown_status_is_refused` | status `maybe` | `ValueError` | Pass |

## Reporting and bulk input

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 20 | `test_report_counts` | 2 valid, 1 invalid | total 2, rejected 1, one band A | Pass |
| 21 | `test_bad_json_line_is_logged` | One good line, one broken | 1 accepted, 1 error | Pass |
| 22 | `test_sample_leads_match_documented_result` | Shipped sample file | 10 accepted, 1 duplicate, 1 rejected, average 43.3, pipeline 54,500 | Pass |

## Make parity

These live in `tests/test_scenarios.py` and run the reference rules with Node.js.

| # | Test | What it proves | Result |
|---|---|---|---|
| 23 | `test_lead_score_matches_the_python_implementation` | The Make reference rules return the same score, band and segment as `leads.score_lead` | Pass |
| 24 | `test_lead_wording_follows_the_band` | Band A wording is used and `approved` starts false | Pass |

## What these tests do not prove

- That band A leads convert better than band C leads. That needs real
  won/lost history, which this project does not have.
- That the weights are right. They are defensible, not measured.
- That the follow-up emails read well to a real buyer.
