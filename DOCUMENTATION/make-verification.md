# Make verification status

Last checked: **20 November 2026**. Re-check before making any claim to a
client or recruiter.

## What exists

Each project folder contains a build specification and a reference implementation
of the rules:

| Project | Spec | Steps | Shape |
|---|---|---|---|
| Customer support | `make-scenario.json` | 6 | Custom webhook → classify → Router → two Sheets queues → webhook response |
| Inventory | `make-scenario.json` | 5 | Custom webhook → rebuild balances → Router → Email or response |
| Sales | `make-scenario.json` | 5 | Custom webhook → score and draft → Router → priority Sheet or response |

`make-logic.js` in each folder holds the deterministic rules in plain
JavaScript. The Google Sheets and Email modules in the specs are inactive until
a connection exists. `tools/build_scenarios.py` regenerates both files.

These are **build specifications, not Make blueprints**. Make's export format is
an opaque blueprint JSON produced by a live Make account. The documented schema
includes `flow`, `metadata`, `scheduling`, `idSequence` and `version` (Make API,
`https://developers.make.com/api-documentation/api-reference/scenarios/blueprints.md`,
checked 20 November 2026), but a blueprint cannot be honestly invented from a
schema. No Make account was available in this environment, so none was created.

## What has been verified

1. **Structure.** `tools/check_scenarios.py` confirms numbered steps, valid
   routes, exactly one custom webhook and an existing rules file. All three pass.
2. **Rules execute.** `make-logic.js` runs under Node.js with a fixture. All
   three produce the expected result.
3. **Python parity.** The support escalation, inventory valuation and lead
   score, band and segment match the Python implementations for the same
   fixtures.
4. **Honest status.** Every spec has `verified_in_make: false`; a test asserts
   it stays false until a real Make run exists.

## What has NOT been verified

- That any scenario was created, imported or executed inside Make.
- That the named modules exist in the learner's Make plan and workspace.
- Canvas screenshots from inside Make.
- Webhook response behaviour over HTTP.
- Google Sheets, Email or any other connected module.

Do not describe these as "Make workflows tested live", "importable blueprints"
or "exported from Make". Describe them as "Make scenario build specifications;
the rules are executed under Node and cross-checked against the Python code".

## Why there is no live verification

The platform was switched from n8n to Make on 20 November 2026 at the learner's
request. The earlier failed n8n installs were a different platform and are not
evidence about Make. No Make login, token or workspace was available, so no
scenario was built in Make and no blueprint was exported.

## To finish verification

1. Sign in to a Make account and create a new scenario from the relevant
   `make-scenario.json` using `make-build-guide.md`.
2. Add the custom webhook and copy the step names and field mappings from the
   spec. Keep the Sheets and Email modules inactive.
3. Run the scenario with a fixture from `tools/check_scenarios.py` → `FIXTURES`
   and confirm the returned JSON matches the Python result.
4. Export the scenario blueprint and save it beside the spec as
   `make-blueprint.json`.
5. Take a canvas screenshot and save it to
   `PROJECT-0x-.../screenshots/02-make-canvas.png` (or `.jpeg`).
6. Set `verified_in_make` to `true` in the spec and in
   `tools/build_scenarios.py`, then update this file with the date, workspace
   and result. Only then add the screenshot to `index.html`.

## Suggested wording until then

> "Each project includes a Make scenario build specification. I tested the
> rules under Node and cross-checked them against the Python implementation.
> I have not yet built the scenarios in a Make account or connected them to
> external services, and I say so in the documentation."
