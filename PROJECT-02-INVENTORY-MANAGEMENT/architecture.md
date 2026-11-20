# Architecture — inventory management

## Flow

```
Movement (receipt / issue / adjustment)
    |
    v
[validate]  sku exists, kind known, qty non-zero, receipt has a cost
    |
    v
[idempotency]  same kind+sku+qty+reference already posted -> duplicate, stop
    |
    v
[stock rules]  issue > balance -> refuse
               adjustment -> negative -> refuse
    |
    v
[cost]  receipt: moving average recalculated
        issue/adjustment: current average used
    |
    v
[write]  products updated + one immutable row in movements
    |
    v
[alerts]  out_of_stock | low_stock | anomaly   (one open alert per kind)
    |
    v
report: receipts, issues, adjustments, valuation, alert count
```

## Why balances are not stored as the source of truth

`products.qty` is a cache. `movements` is the record. Every posting writes
both, and the balance can be rebuilt by replaying the movements. That matters
because the most common inventory failure is a balance that nobody can
explain: someone edits a number and the history no longer adds up.

A rebuild command is not included, but the schema supports it:

```sql
SELECT sku, SUM(CASE kind WHEN 'receipt' THEN qty
                          WHEN 'issue' THEN -qty
                          ELSE qty END) AS balance
FROM movements GROUP BY sku;
```

## Data model

```
products (sku PK, qty, avg_cost, reorder_level)
movements (sku FK, kind, qty, unit_cost, value, reference, idempotency_key UNIQUE)
alerts    (sku, kind, message, acknowledged)
rejected  (payload, problems)
```

One open alert per product per kind, enforced by a partial unique index:

```sql
CREATE UNIQUE INDEX ux_alerts_open ON alerts(sku, kind) WHERE acknowledged = 0;
```

So a nightly run cannot produce forty identical emails, but a stockout after a
recovery does raise a new alert.

## Make equivalent

```
Webhook > Custom webhook (POST /stock-movements)
    -> Tools > Set variable: Rebuild balances
    -> Router: Alerts raised?
         true  -> Email > Send an email: Email the buyer (inactive)
         false -> Webhook > Webhook response
```

The spec is stateless: post `products` and `movements` in the body and
`make-logic.js` replays them. That keeps the rules testable with no database
and no credentials. Nothing has been built in Make; see
`../DOCUMENTATION/make-verification.md`.

For production the movement list would come from a database or a Google Sheet
read module, and the alert branch would write to a real mailbox.

## Failure behaviour

| Failure | Result |
|---|---|
| Unknown SKU | Movement rejected, logged, batch continues |
| Issue larger than balance | Rejected with the actual balance in the message |
| Adjustment below zero | Rejected |
| Receipt with no cost | Rejected |
| Duplicate reference | Returns `duplicate`, nothing posted twice |
| Malformed JSON line | Line logged, remaining lines processed |
| Stock recovers | Open low-stock and stockout alerts closed automatically |

## What is deliberately missing

- No FIFO batches, so no expiry dating. For dairy that matters and would be
  the first upgrade.
- No transfer between locations.
- No unit-of-measure conversion: a case is a case.
- Alert thresholds are global constants, not per product.
