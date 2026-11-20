"""Command line entry point for Project 2.

    python run.py demo                 # reset, load products, apply movements
    python run.py stock                # balances and reorder status
    python run.py alerts               # open alerts
    python run.py valuation            # stock value by product
    python run.py report --day 2026-11-20
    python run.py dashboard            # write dashboard.html
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import inventory  # noqa: E402
from engine import db, render  # noqa: E402

TABLES = ["alerts", "movements", "rejected", "products"]
PRODUCTS = os.path.join(HERE, "data", "products.json")
MOVEMENTS = os.path.join(HERE, "data", "movements.jsonl")
DASHBOARD = os.path.join(HERE, "dashboard.html")


def status_of(row: dict) -> str:
    if row["qty"] <= 0:
        return "out of stock"
    if row["qty"] <= row["reorder_level"]:
        return "low"
    return "in stock"


def cmd_demo(args) -> int:
    con = inventory.connect()
    db.reset(con, TABLES)
    with open(PRODUCTS, encoding="utf-8") as handle:
        products = json.load(handle)
    for product in products:
        inventory.add_product(con, product["sku"], product["name"], product.get("unit", "unit"),
                              product.get("category"), product.get("reorder_level", 0),
                              product.get("opening_qty", 0), product.get("opening_cost", 0))
    result = inventory.apply_file(con, MOVEMENTS)
    posted = sum(1 for r in result["applied"] if r["outcome"] == "posted")
    duplicates = sum(1 for r in result["applied"] if r["outcome"] == "duplicate")
    print(json.dumps({"products": len(products), "posted": posted,
                      "duplicates": duplicates, "errors": len(result["errors"])}, indent=2))
    for error in result["errors"]:
        print(f"  {error}")
    print(json.dumps(inventory.report(con), indent=2))
    return 0


def cmd_stock(args) -> int:
    con = inventory.connect()
    rows = db.rows(con, "SELECT sku, name, qty, reorder_level, unit, avg_cost "
                        "FROM products ORDER BY sku")
    for row in rows:
        print(f"{row['sku']:<9} {row['qty']:>7.0f} {row['unit']:<8} "
              f"reorder {row['reorder_level']:>4.0f}  {status_of(row)}")
    return 0


def cmd_alerts(args) -> int:
    con = inventory.connect()
    for alert in inventory.open_alerts(con):
        print(f"{alert['id']:>3}  {alert['sku']:<9} {alert['kind']:<13} {alert['message']}")
    return 0


def cmd_valuation(args) -> int:
    con = inventory.connect()
    data = inventory.valuation(con)
    for line in data["lines"]:
        print(f"{line['sku']:<9} {line['qty']:>7.0f} x {line['avg_cost']:>7.2f} = {line['value']:>10.2f}")
    print(f"{'TOTAL':<9} {'':>7}   {'':>7}   {data['total']:>10.2f}")
    return 0


def cmd_report(args) -> int:
    con = inventory.connect()
    print(json.dumps(inventory.report(con, args.day), indent=2))
    return 0


def cmd_dashboard(args) -> int:
    con = inventory.connect()
    summary = inventory.report(con, args.day)
    products = db.rows(con, "SELECT sku, name, category, qty, unit, reorder_level, avg_cost, "
                            "ROUND(qty * avg_cost, 2) AS value FROM products ORDER BY sku")
    for row in products:
        row["status"] = status_of(row)

    alerts = inventory.open_alerts(con)
    movements = db.rows(con, """
        SELECT id, sku, kind, qty, unit_cost, value, reference, at
        FROM movements ORDER BY id DESC LIMIT 14
    """)
    rejected = db.rows(con, "SELECT problems, at FROM rejected ORDER BY id DESC")

    stats = [
        {"label": "Stock value", "value": f"{summary['stock_value']:,.2f}",
         "hint": "moving average cost"},
        {"label": "Low stock", "value": summary["low_stock_count"], "hint": "at or below reorder level"},
        {"label": "Open alerts", "value": summary["open_alerts"], "hint": "unacknowledged"},
        {"label": "Issues today", "value": summary["issues"]["count"],
         "hint": f"value {summary['issues']['value']:,.2f}"},
    ]
    sections = [
        {
            "title": "Stock on hand",
            "description": "Balance, reorder level and value for every product.",
            "columns": [("sku", "SKU", "text"), ("name", "Product", "text"),
                        ("qty", "Qty", "num"), ("unit", "Unit", "text"),
                        ("reorder_level", "Reorder", "num"), ("avg_cost", "Avg cost", "money"),
                        ("value", "Value", "money"), ("status", "Status", "tag")],
            "rows": products,
            "empty": "No products loaded.",
        },
        {
            "title": "Open alerts",
            "description": "Raised by the stock check after each movement. One open alert per product per kind.",
            "columns": [("sku", "SKU", "text"), ("kind", "Type", "tag"),
                        ("message", "Message", "text"), ("at", "Raised", "text")],
            "rows": alerts,
            "empty": "No open alerts.",
        },
        {
            "title": "Recent movements",
            "description": "The audit trail. Balances are derived from these rows, never edited in place.",
            "columns": [("id", "#", "num"), ("sku", "SKU", "text"), ("kind", "Type", "tag"),
                        ("qty", "Qty", "num"), ("value", "Value", "money"),
                        ("reference", "Reference", "text"), ("at", "When", "text")],
            "rows": movements,
            "empty": "No movements.",
        },
        {
            "title": "Rejected input",
            "description": "Movements refused by validation or stock rules, with the reason.",
            "columns": [("problems", "Problem", "text"), ("at", "When", "text")],
            "rows": rejected,
            "empty": "No rejected input.",
        },
    ]
    markup = render.dashboard(
        title="AI Inventory and Stock Control",
        subtitle="Posts receipts, issues and adjustments against a moving average cost, "
                 "raises low-stock and out-of-stock alerts, values the stock and flags "
                 "unusual movements for investigation.",
        stats=stats,
        sections=sections,
        notes=[
            "Synthetic sample data for a small drinks distributor. No client stock figures.",
            "Costing uses a moving average. It is simple and auditable, but it is not FIFO.",
            "Stock can never go negative: an issue larger than the balance is rejected and logged.",
            "Anomaly rules are thresholds (40% of stock in one issue, 3x the usual issue size, 25% cost swing). They flag for review; they do not prove a problem.",
            "No email or messaging alert is wired up. Alerts are stored and shown here only.",
        ],
        accent="#1d4ed8",
        footer="Project 2 of 3 - AI Operations portfolio. Values are demo data in QAR.",
        back_href="../index.html",
        back_label="Portfolio home",
    )
    render.write_html(DASHBOARD, markup)
    print(f"wrote {DASHBOARD}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AI inventory management")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo").set_defaults(func=cmd_demo)
    sub.add_parser("stock").set_defaults(func=cmd_stock)
    sub.add_parser("alerts").set_defaults(func=cmd_alerts)
    sub.add_parser("valuation").set_defaults(func=cmd_valuation)

    report = sub.add_parser("report")
    report.add_argument("--day", default=None)
    report.set_defaults(func=cmd_report)

    dash = sub.add_parser("dashboard")
    dash.add_argument("--day", default=None)
    dash.set_defaults(func=cmd_dashboard)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
