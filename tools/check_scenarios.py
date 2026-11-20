"""Check the three Make.com scenario build specifications.

Three levels of check:
  1. structure  - numbered steps, valid routes, one trigger, a rules file.
  2. syntax     - the reference JavaScript is compiled by Node.
  3. behaviour  - the rules run with a fixture and the result is compared with
                  the Python implementation.

    python tools/check_scenarios.py

A passing check does not mean the scenario ran inside Make. No Make account was
available here, so `verified_in_make` stays false in every specification.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for path in (ROOT,):
    if path not in sys.path:
        sys.path.insert(0, path)

SCENARIOS = [
    ("PROJECT-01-CUSTOMER-SUPPORT", "support"),
    ("PROJECT-02-INVENTORY-MANAGEMENT", "inventory"),
    ("PROJECT-03-SALES-AUTOMATION", "leads"),
]

FIXTURES = {
    "support": {
        "external_id": "CS-TEST-1",
        "customer_name": "Amina Yusuf",
        "customer_email": "amina@example.com",
        "subject": "Damaged cartons",
        "body": "Three cartons arrived damaged and leaking. I want a refund.",
    },
    "inventory": {
        "products": [
            {"sku": "WTR-500", "name": "Water 500ml", "unit": "case", "reorder_level": 40},
        ],
        "movements": [
            {"sku": "WTR-500", "kind": "receipt", "qty": 100, "unit_cost": 20, "reference": "PO-1"},
            {"sku": "WTR-500", "kind": "issue", "qty": 70, "reference": "SO-1"},
            {"sku": "WTR-500", "kind": "issue", "qty": 999, "reference": "SO-2"},
        ],
    },
    "leads": {
        "external_id": "LD-TEST-1",
        "name": "Hassan Al-Marri",
        "email": "hassan@example.com",
        "company": "Al-Marri Catering",
        "source": "referral",
        "role": "Owner",
        "employees": 120,
        "budget": 15000,
        "timeline": "immediate",
        "message": "We need weekly water delivery across 14 sites.",
    },
}

TRIGGER = "Webhook > Custom webhook"


def load(folder: str) -> dict:
    with open(os.path.join(ROOT, folder, "make-scenario.json"), encoding="utf-8") as handle:
        return json.load(handle)


def check_structure(spec: dict, folder: str) -> list[str]:
    problems: list[str] = []
    scenario = spec.get("scenario", {})

    if spec.get("platform") != "Make.com":
        problems.append("platform must be 'Make.com'")
    if spec.get("verified_in_make") is not False:
        problems.append("verified_in_make must stay false without a live Make run")

    for key in ("name", "purpose", "steps", "routes", "rules_file", "approval_gate"):
        if key not in scenario:
            problems.append(f"missing scenario key '{key}'")

    steps = scenario.get("steps", [])
    numbers = [s.get("step") for s in steps]
    if numbers != list(range(1, len(steps) + 1)):
        problems.append("steps must be numbered 1..n without gaps")
    triggers = [s for s in steps if s.get("module") == TRIGGER]
    if len(triggers) != 1:
        problems.append(f"expected exactly 1 custom webhook, found {len(triggers)}")

    for route in scenario.get("routes", []):
        if route.get("from") not in numbers or route.get("to") not in numbers:
            problems.append(f"route references an unknown step: {route}")
        if not route.get("condition"):
            problems.append(f"route has no condition: {route}")

    rules = os.path.join(ROOT, folder, scenario.get("rules_file", ""))
    if not os.path.isfile(rules):
        problems.append(f"rules file not found: {scenario.get('rules_file')}")
    return problems


def run_logic(folder: str, spec: dict, fixture: dict) -> tuple[bool, object]:
    rules = os.path.join(ROOT, folder, spec["scenario"]["rules_file"])
    with open(rules, encoding="utf-8") as handle:
        js_code = handle.read()
    harness = (
        "const payload = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));\n"
        "function run() {\n%s\n}\n"
        "process.stdout.write(JSON.stringify(run(), null, 2));\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "rules.js")
        data = os.path.join(tmp, "payload.json")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(harness % js_code)
        with open(data, "w", encoding="utf-8") as handle:
            json.dump(fixture, handle)
        result = subprocess.run(["node", script, data], capture_output=True,
                                text=True, timeout=60)
    if result.returncode != 0:
        return False, result.stderr.strip()[:800]
    return True, json.loads(result.stdout)


def main() -> int:
    failures = 0
    node_available = subprocess.run(["node", "--version"], capture_output=True).returncode == 0

    for folder, fixture_name in SCENARIOS:
        spec = load(folder)
        label = spec["scenario"]["name"]
        print(f"\n{label}")

        problems = check_structure(spec, folder)
        if problems:
            failures += len(problems)
            for problem in problems:
                print(f"  STRUCTURE FAIL  {problem}")
        else:
            print(f"  structure       ok ({len(spec['scenario']['steps'])} steps)")

        if not node_available:
            print("  behaviour       skipped, node is not installed")
            continue

        ok, result = run_logic(folder, spec, FIXTURES[fixture_name])
        if not ok:
            failures += 1
            print(f"  RULES FAIL      {result}")
            continue
        payload = result[0]
        summary = {k: payload[k] for k in
                   ("outcome", "category", "band", "score", "stock_value",
                    "escalate", "alerts", "rejected") if k in payload}
        print(f"  rules           {json.dumps(summary)[:160]}")

    print("\nscenario checks:", "FAILED" if failures else "passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
