# Build a Make scenario from a specification

Use this with `make-verification.md`. It turns a `make-scenario.json` into a
scenario in a real Make account. Nothing here is claimed to be already built.

## Before you start

- Have a Make account and an empty scenario open.
- Have the project's `make-scenario.json` and `make-logic.js` beside you.
- Use synthetic fixtures only. Do not paste customer or client data into Make.

## Steps

1. **Trigger.** Add `Webhook > Custom webhook`. Name it after step 1 in the
   spec. Copy the sample payload from `tools/check_scenarios.py` → `FIXTURES`
   into Make's sample request so the fields are available downstream.
2. **Apply the rules.** Add `Tools > Set variable` and name it after step 2.
   Map the output fields listed in the spec's `config` text. `make-logic.js` is
   the reference: every field, threshold, rejection message and draft template
   in it is the intended behaviour. If your Make plan offers a code module and
   you choose to use it, keep it offline of external services until reviewed.
3. **Route.** Add a Router and create one route per entry in the spec's
   `routes` list. Use the `condition` text as the filter on each route.
4. **Optional side effects.** Add the Sheets or Email module named in the spec,
   but leave it inactive until a connection is configured. Do not put real
   credentials in the repository or in a screenshot.
5. **Respond.** Add `Webhook > Webhook response` and return the step 2 output
   as JSON. Every route that does not call an external service should reach it.
6. **Error handling.** Set optional modules to continue on error and retry once
   on transient failures, as recorded in the spec's `error_handling` field.
7. **Approval gate.** Check the spec's `approval_gate`. `approved` starts false
   and the default path never sends an external message. Keep it that way.
8. **Save and test.** Save as a draft, then run with the same fixture used by
   `tools/check_scenarios.py`. Compare the returned JSON with the Python run.
9. **Record evidence.** Export the blueprint as `make-blueprint.json`, save a
   canvas screenshot, and update `make-verification.md`. Only then change
   `verified_in_make` to `true`.

## Fields you should expect

| Project | Inputs | Outputs to check |
|---|---|---|
| Support | `external_id`, `customer_name`, `customer_email`, `subject`, `body` | `category`, `urgency`, `sentiment`, `escalate`, `escalation_reason`, `draft_body`, `approved` |
| Inventory | `products[]`, `movements[]` | `applied`, `rejected`, `rejections`, `alerts`, `stock_value`, `low_stock`, `lines` |
| Sales | lead fields including `source`, `role`, `employees`, `budget`, `timeline` | `score`, `band`, `segment`, `score_reason`, `draft_body`, `approved` |

## Safety

- No API keys, tokens, webhook URLs, personal data or client data in exports,
  screenshots or Git.
- Human approval before any external message or record change.
- A spend cap and rate limit before any paid connection.
- If a required Make module is unavailable on your plan, note the substitution
  in `make-verification.md` rather than claiming a match.
