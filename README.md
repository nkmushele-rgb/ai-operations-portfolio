# AI Operations Portfolio — Kelvin Mushele

A recruiter-facing portfolio for remote **AI operations**, **workflow automation** and
**business operations** roles.

Built and tested locally. All business data is synthetic. These are **portfolio
projects, not client deliveries**, and the demo numbers describe the demo runs only.

## Start here

| Path | What it is |
|---|---|
| `index.html` | Responsive portfolio website. Open in a browser or serve over HTTP. |
| `PROFILE/` | Hubstaff profile draft, target headline and a pre-approval audit checklist. |
| `CV/` | CV in Markdown and a print-ready HTML version. |
| `PROJECT-01-CUSTOMER-SUPPORT/` | Triage pipeline, dashboard, Make build spec, tests. |
| `PROJECT-02-INVENTORY-MANAGEMENT/` | Stock control, costing, alerts, Make build spec, tests. |
| `PROJECT-03-SALES-AUTOMATION/` | Lead scoring, drafting, approval gate, Make build spec, tests. |
| `DOCUMENTATION/` | Setup, testing summary, Make verification status, limitations. |
| `DEMONSTRATIONS/` | Two-minute talk track for each project. |
| `JOB-APPLICATIONS/` | Market research, role suitability, letter templates, tracker. |
| `tests/` | One unittest suite covering all three projects and the Make specs. |
| `tools/` | Regenerates the Make build specs and checks their structure and logic. |
| `engine/` | Shared, standard-library-only helpers used by all three projects. |

## Run a project

Python 3.10 or newer. No packages to install.

```bash
cd PROJECT-01-CUSTOMER-SUPPORT
python run.py demo
python run.py dashboard
```

`dashboard` writes `dashboard.html` beside the script. The same commands work in
`PROJECT-02-INVENTORY-MANAGEMENT/` and `PROJECT-03-SALES-AUTOMATION/`.

Ollama is optional. With it, the model writes reply prose; without it, the
projects use templates and still pass every test. Set `AIOPS_LLM=off` for
deterministic output.

## Run the tests

From this folder:

```bash
python -m unittest discover -s tests -v
```

Expect `Ran 90 tests` and `OK`. In PowerShell the command may report exit code 1
because unittest writes to stderr; check the `OK` line, not the exit code.

## Make status at the time of writing

Each project ships a `make-scenario.json` **build specification** and a
`make-logic.js` reference implementation of the rules. `tools/build_scenarios.py`
generates them; `tools/check_scenarios.py` validates the step and route structure
and runs the reference rules under Node.js, comparing the result with the Python
implementation.

These files are **not Make blueprints**. A Make export is an opaque blueprint
from a live Make account, and no Make account was available here. Nothing in this
portfolio has been imported into or executed by Make. Do not describe these as
"tested in Make" or "importable workflows". See `DOCUMENTATION/make-verification.md`
for the exact state and `DOCUMENTATION/make-build-guide.md` for the build steps.

## Live site

Published with GitHub Pages from the `main` branch:
<https://nkmushele-rgb.github.io/ai-operations-portfolio/>

## Before sending an application

- Fill in employment dates, territory and qualification years in the CV. Nothing
  is invented here; those gaps are deliberate.
- Replace the `KM` avatar with a real photo if the learner wants one.
- Re-run the tests and regenerate the three dashboards if any code changes.
- Check `DOCUMENTATION/limitations-and-honesty.md` before writing a proposal or cover letter.
