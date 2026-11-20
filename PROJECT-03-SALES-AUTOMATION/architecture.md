# Architecture — sales lead management

## Flow

```
Lead feed (JSONL)
    |
    v
[validate]  reference, name, email, source, numeric budget and headcount
    |
    v
[deduplicate]  same reference OR same email -> attach to existing lead, stop
    |
    v
[score]  6 rules -> 0..73 points + stored breakdown
    |
    v
[band]   A >= 60 | B 35-59 | C < 35
[segment] key account | growth | small
    |
    v
[draft]  band-matched body; model if available, template otherwise
    |
    v
status "new", approved = false
    |
    v
[human approve]
    |
    v
[send]  refuses if not approved, or if the lead is lost
    |
    v
outbox/*.txt  +  activity log
```

## Why the score is not a model

A salesperson will argue with a ranking. If the ranking comes from a model,
the argument ends in "the system says so". If it comes from six named rules,
the argument ends in a decision about a threshold, which is a better
conversation and produces a better system.

The model is used where it is genuinely better: writing a sentence that does
not read like a template.

## Data model

```
leads 1---* drafts
leads 1---* activities
rejected (standalone)
```

`leads.score_reason` stores the arithmetic, for example:

```
source referral +15; budget 5,000+ +20; timeline 'immediate' +15;
role 'owner' +10; company 50+ staff +8; 3/3 contact details complete +5
```

## Pipeline transitions

| From | Allowed to |
|---|---|
| new | contacted, lost |
| contacted | qualified, won, lost |
| qualified | won, lost |
| won | — |
| lost | new (reopen) |

Anything else raises `ValueError`. `new → won` is refused on purpose: a lead
cannot be closed without being contacted.

## Make equivalent

```
Webhook > Custom webhook (POST /new-lead)
    -> Tools > Set variable: Score and draft
    -> Router: Band A?
         true  -> Google Sheets > Add a row: Flag for priority call (inactive)
         false -> Webhook > Webhook response
```

`tools/check_scenarios.py` runs `make-logic.js` and asserts the score, band and
segment match `leads.score_lead` for the same input. That parity check is
part of the test suite. No scenario has been built in Make; see
`../DOCUMENTATION/make-verification.md`.

## Failure behaviour

| Failure | Result |
|---|---|
| Invalid email | Rejected with reason, logged |
| Missing name | Rejected |
| Duplicate reference | `duplicate`, matched on `reference` |
| Duplicate email | `duplicate`, matched on `email`, activity added to the original |
| Budget missing or null | Scores 0 for budget, no crash |
| Budget as text | `ValueError` from validation, rejected |
| Send without approval | `PermissionError` |
| Send a lost lead | `PermissionError` |
| Illegal status move | `ValueError` |

## What is deliberately missing

- No conversion feedback loop. The scores are not fitted to outcomes because
  there are no real outcomes to fit to.
- No enrichment (company size is supplied, not looked up).
- No email sequencing or reminder scheduling.
- No owner assignment or round-robin.
