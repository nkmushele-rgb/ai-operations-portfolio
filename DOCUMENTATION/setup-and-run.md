# Setup and run

## Requirements

- Python 3.10 or newer. Verified locally on Python 3.12.10.
- Node.js only if you want to re-run the Make reference-rule checks. Verified on Node 26.13.1.
- Ollama is optional. It was available locally with `qwen3:8b` and `qwen3:4b`,
  but the projects are designed to run without it.

No `pip install`. No virtual environment is needed. No API key is required.

## First run

From the portfolio root:

```bash
python -m unittest discover -s tests -v
```

Then, for each project folder in turn:

```bash
cd PROJECT-01-CUSTOMER-SUPPORT
python run.py demo
python run.py dashboard
cd ..
```

`run.py demo` resets the SQLite database and replays the shipped sample file, so
the numbers are repeatable. `dashboard` writes `dashboard.html` in the same
folder. The dashboards are snapshots: re-run the command after a change.

## Useful commands

| Project | Commands |
|---|---|
| Customer support | `list`, `approve <id> --by "Name"`, `send <id>`, `report` |
| Inventory | `stock`, `alerts`, `valuation`, `report --day YYYY-MM-DD` |
| Sales | `list`, `approve <id> --by "Name"`, `send <id>`, `status <id> contacted`, `report` |

## Deterministic output

The model is optional and would make reply text vary between runs. Force the
template path with:

```powershell
$env:AIOPS_LLM = "off"
```

```bash
export AIOPS_LLM=off
```

Accepted values are `off`, `on` and `auto` (the default: use the model if it
answers, otherwise fall back). The model never classifies, scores or escalates
anything. It only writes prose.

## Viewing the website locally

`file://` links work in a normal browser, but the in-app browser used during
development rejects them. To serve the folder over HTTP:

```bash
python -m http.server 8099 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8099/index.html`.

## Regenerating the Make specs

```bash
python tools/build_scenarios.py
python tools/check_scenarios.py
```

The first command rewrites all three `make-scenario.json` files and their
`make-logic.js` reference rules. The second checks structure and runs the rules
with Node.js. Neither command needs a Make account. See `make-verification.md`.

## Files created at runtime

These are generated, not source. They are safe to delete and re-create:

- `data/support.db`, `data/stock.db`, `data/sales.db`
- `dashboard.html` in each project
- `outbox/*.txt` in each project
- `__pycache__/` folders

The sample inputs under `data/` are shipped source files and are not deleted by
`run.py demo`.
