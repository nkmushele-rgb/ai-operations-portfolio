# Architecture — customer support triage

## Flow

```
JSONL inbox
    |
    v
[validate] ---> invalid ---> rejected table (reason kept)
    |
    v
[classify: rules]  category, urgency, sentiment, confidence
    |
    v
[escalation rules]  refund / legal / safety / urgent / manager
    |
    +--> escalated --> status "escalated" --> human queue (never auto-sent)
    |
    v
[draft: model or template]
    |
    v
status "awaiting_approval"
    |
    v
[human approve]  records approver and time
    |
    v
[send]  refuses unless approved and not escalated
    |
    v
outbox/*.txt  +  event log
```

## Where each decision lives

| Decision | Made by | Why there |
|---|---|---|
| Is this message usable | `engine/validate.py` | One validator shared by all three projects |
| What category is it | `support.classify` | Rules, so routing is reproducible and auditable |
| Does a human need it | `support.escalation` | Returns a readable reason, not just a boolean |
| What does the reply say | `llm.generate`, else `support.template_draft` | The only part where variation helps |
| May this be sent | `support.send` | Raises rather than warns, so it cannot be bypassed by a caller |

## Data model

```
tickets 1---* drafts
tickets 1---* events
rejected   (standalone: failed validation, no ticket created)
```

`tickets.status` moves `new` → `awaiting_approval` | `escalated` →
`approved` → `sent`. `drafts.approved` is the authority for the send gate;
`tickets.status` is for reporting.

## Make equivalent

`make-scenario.json` is a build specification for this logic in Make:

```
Webhook > Custom webhook (POST /customer-inquiry)
    -> Tools > Set variable: Validate and classify
    -> Router: Escalate?
         true  -> Google Sheets > Add a row: Human queue   (inactive)
         false -> Google Sheets > Add a row: Approval queue (inactive)
    -> Webhook > Webhook response
```

`make-logic.js` holds the same rules as `support.py`, so the two can be
compared line by line. `tools/check_scenarios.py` executes the rules with Node
and checks they return the same result as the Python version.

The Sheets modules are inactive in the spec and no Make account was available,
so nothing is claimed to have been built or imported in Make. See
`../DOCUMENTATION/make-verification.md`.

## Failure behaviour

| Failure | Result |
|---|---|
| Ollama not running | Template reply, `drafts.source = 'template'`, workflow continues |
| Malformed JSON line | Line rejected and logged, remaining lines processed |
| Invalid email | Rejected with reason, no ticket created |
| Duplicate reference | Returns the existing ticket, creates nothing |
| Send before approval | `PermissionError` |
| Send an escalated ticket | `PermissionError` |
| Unknown ticket id | `LookupError` |

## What is deliberately missing

- No retry queue for the model call. If the model is slow the template is used.
- No authentication on the Make webhook. In production it needs a header secret
  or the Make instance must sit behind a private network.
- No rate limit on ingestion.
