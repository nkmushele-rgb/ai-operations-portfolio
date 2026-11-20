# Test cases — inventory management

Run: `python -m unittest tests.test_project02_inventory -v` from the portfolio root.
26 tests, all passing.

## Receipts and costing

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 1 | `test_receipt_sets_balance_and_cost` | 10 at 18.50 | qty 10, average 18.50 | Pass |
| 2 | `test_moving_average_across_two_prices` | 10 at 100, then 10 at 200 | qty 20, average 150 | Pass |
| 3 | `test_receipt_without_cost_is_refused` | No unit cost | `ValueError` | Pass |
| 4 | `test_negative_receipt_is_refused` | qty -5 | `ValueError` | Pass |
| 5 | `test_zero_quantity_is_refused` | qty 0 | `ValueError` | Pass |
| 6 | `test_unknown_sku_is_refused` | SKU `NOPE-1` | `LookupError` | Pass |
| 7 | `test_duplicate_reference_is_idempotent` | Same PO twice | Second is `duplicate`, balance unchanged | Pass |

## Issues

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 8 | `test_issue_reduces_balance_and_keeps_cost` | Issue 25 of 100 at 20 | balance 75, value 500, cost still 20 | Pass |
| 9 | `test_issue_more_than_stock_is_refused` | Issue 101 of 100 | `ValueError` naming the balance, balance still 100 | Pass |
| 10 | `test_issue_of_entire_stock_is_flagged` | Issue 100 of 100 | Anomaly "100% of stock on hand" | Pass |

## Adjustments

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 11 | `test_negative_adjustment_reduces_stock` | -5 with a reason | balance 45, anomaly recorded | Pass |
| 12 | `test_adjustment_below_zero_is_refused` | -60 of 50 | `ValueError`, balance unchanged | Pass |

## Alerts

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 13 | `test_low_stock_alert_raised_once` | Two issues leaving stock below reorder | Exactly one open low-stock alert | Pass |
| 14 | `test_out_of_stock_alert` | Issue all stock | `out_of_stock` alert present | Pass |
| 15 | `test_alert_reopens_after_stock_recovers` | Low, receive, low again | Closed on recovery, reopened on the next dip | Pass |
| 16 | `test_alert_can_be_acknowledged` | Acknowledge all | No open alerts | Pass |
| 17 | `test_one_open_alert_per_kind` | 70% issue | Exactly `anomaly` and `low_stock` | Pass |

## Anomaly detection

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 18 | `test_large_issue_is_flagged` | Issue 50 of 100 | Flagged, "50% of stock on hand" | Pass |
| 19 | `test_normal_issue_is_not_flagged` | Issue 10 of 100 | No anomaly | Pass |
| 20 | `test_price_swing_is_flagged` | Receipt at 30 when average is 20 | Flagged | Pass |
| 21 | `test_small_price_change_is_not_flagged` | Receipt at 21 when average is 20 | No anomaly | Pass |
| 22 | `test_repeated_oversized_issue_is_flagged_against_history` | 3 small issues then one 4x larger | Flagged | Pass |

## Valuation and reporting

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 23 | `test_valuation_totals` | Two products | 1,250.00 total | Pass |
| 24 | `test_low_stock_list_includes_shortfall` | 10 on hand, reorder 40 | shortfall 30 | Pass |

## Bulk input

| # | Test | Input | Expected | Result |
|---|---|---|---|---|
| 25 | `test_bad_rows_are_logged_and_batch_continues` | 1 good, 1 broken JSON, 1 bad kind, 1 oversell, 1 good | 2 posted, 3 errors, balance 6 | Pass |
| 26 | `test_sample_batch_matches_documented_result` | Shipped sample files | 22 posted, 1 duplicate, 1 error, value 12,276.94, 3 low | Pass |

## What these tests do not prove

- That moving average is the right costing method for the business. It is a
  reasonable default, not a universal one.
- That the anomaly thresholds suit a real distributor. They were chosen to be
  explainable, not tuned on data.
- That concurrent postings are safe. SQLite serialises writes, but there is no
  explicit locking test.
