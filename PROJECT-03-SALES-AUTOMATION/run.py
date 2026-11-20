"""Command line entry point for Project 3.

    python run.py demo                 # reset and capture the sample leads
    python run.py list                 # leads ranked by score
    python run.py report --start 2026-11-14
    python run.py approve 1 --by "Kelvin M"
    python run.py send 1
    python run.py status 1 qualified
    python run.py dashboard
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

import leads  # noqa: E402
from engine import db, render  # noqa: E402

TABLES = ["drafts", "activities", "rejected", "leads"]
SOURCE_FILE = os.path.join(HERE, "data", "leads.jsonl")
DASHBOARD = os.path.join(HERE, "dashboard.html")


def cmd_demo(args) -> int:
    con = leads.connect()
    db.reset(con, TABLES)
    result = leads.capture_file(con, SOURCE_FILE)
    print(json.dumps(result["counts"], indent=2))
    summary = leads.weekly_report(con)
    print(json.dumps({k: v for k, v in summary.items() if not k.startswith("by_")}, indent=2))
    return 0


def cmd_list(args) -> int:
    con = leads.connect()
    rows = db.rows(con, "SELECT id, external_id, name, company, band, score, segment, status "
                        "FROM leads ORDER BY score DESC, id")
    for row in rows:
        print(f"{row['band']} {row['score']:>3}  {row['external_id']:<9} "
              f"{(row['company'] or row['name'])[:28]:<28} {row['segment']:<11} {row['status']}")
    return 0


def cmd_report(args) -> int:
    con = leads.connect()
    print(json.dumps(leads.weekly_report(con, args.start), indent=2))
    return 0


def cmd_approve(args) -> int:
    con = leads.connect()
    print(json.dumps(leads.approve(con, args.lead_id, args.by), indent=2))
    return 0


def cmd_send(args) -> int:
    con = leads.connect()
    try:
        print(json.dumps(leads.send(con, args.lead_id), indent=2))
    except PermissionError as exc:
        print(f"refused: {exc}")
        return 1
    return 0


def cmd_status(args) -> int:
    con = leads.connect()
    print(json.dumps(leads.set_status(con, args.lead_id, args.status), indent=2))
    return 0


def cmd_dashboard(args) -> int:
    con = leads.connect()
    summary = leads.weekly_report(con, args.start)

    rows = db.rows(con, """
        SELECT l.id, l.external_id, l.name, l.company, l.source, l.band, l.score,
               l.segment, l.status, l.budget, l.score_reason,
               d.approved, d.sent, d.source AS draft_source
        FROM leads l LEFT JOIN drafts d ON d.lead_id = l.id
        ORDER BY l.score DESC, l.id
    """)
    for row in rows:
        row["approval"] = "sent" if row["sent"] else ("approved" if row["approved"] else "pending")

    activities = db.rows(con, """
        SELECT a.id, l.external_id, a.kind, a.detail, a.at
        FROM activities a LEFT JOIN leads l ON l.id = a.lead_id
        ORDER BY a.id DESC LIMIT 16
    """)
    rejected = db.rows(con, "SELECT external_id, problems, at FROM rejected ORDER BY id DESC")
    pending = [r for r in rows if r["approval"] == "pending"]

    stats = [
        {"label": "Leads captured", "value": summary["total"], "hint": "synthetic demo data"},
        {"label": "Band A", "value": sum(r["n"] for r in summary["by_band"] if r["band"] == "A"),
         "hint": "score 60 and above"},
        {"label": "Average score", "value": summary["average_score"], "hint": "out of 73 possible"},
        {"label": "Awaiting approval", "value": summary["awaiting_approval"],
         "hint": "nothing sends without a human"},
    ]
    sections = [
        {
            "title": "Leads ranked by score",
            "description": "Every score is the sum of the rules shown in the reason column.",
            "columns": [("external_id", "Ref", "text"), ("company", "Company", "text"),
                        ("source", "Source", "tag"), ("band", "Band", "tag"),
                        ("score", "Score", "num"), ("segment", "Segment", "text"),
                        ("status", "Status", "tag"), ("approval", "Follow-up", "tag")],
            "rows": rows,
            "empty": "No leads captured.",
        },
        {
            "title": "Why each lead scored what it did",
            "description": "Transparent criteria, so a salesperson can challenge the ranking.",
            "columns": [("external_id", "Ref", "text"), ("score", "Score", "num"),
                        ("score_reason", "Points breakdown", "text")],
            "rows": rows,
            "empty": "No scored leads.",
        },
        {
            "title": "Follow-ups held for approval",
            "description": "Drafts written but not yet approved. The send step refuses them.",
            "columns": [("external_id", "Ref", "text"), ("company", "Company", "text"),
                        ("band", "Band", "tag"), ("draft_source", "Draft", "tag")],
            "rows": pending,
            "empty": "Nothing waiting.",
        },
        {
            "title": "Activity log",
            "description": "Capture, scoring, approval, send and status changes, in order.",
            "columns": [("id", "#", "num"), ("external_id", "Ref", "text"),
                        ("kind", "Event", "tag"), ("detail", "Detail", "text"),
                        ("at", "When", "text")],
            "rows": activities,
            "empty": "No activity.",
        },
        {
            "title": "Rejected input",
            "description": "Leads stopped by validation, with the reason.",
            "columns": [("external_id", "Ref", "text"), ("problems", "Problem", "text"),
                        ("at", "When", "text")],
            "rows": rejected,
            "empty": "No rejected input.",
        },
    ]
    markup = render.dashboard(
        title="AI Sales Lead Management",
        subtitle="Captures leads, scores them against published criteria, drafts a follow-up "
                 "matched to the lead's band, and refuses to send anything a person has not "
                 "approved.",
        stats=stats,
        sections=sections,
        notes=[
            "Synthetic sample data. No real customer or client records.",
            "Scores are a rule sum, not a prediction of revenue. The maximum possible is 73.",
            "A high score means the enquiry looks complete and serious; it does not guarantee a sale.",
            "Follow-up text comes from the local model when available, otherwise from a band-specific template.",
            "Sending writes a file to outbox/ to simulate delivery. No mailbox is connected.",
        ],
        accent="#7c3aed",
        footer="Project 3 of 3 - AI Operations portfolio. Budget figures are demo values in QAR.",
        back_href="../index.html",
        back_label="Portfolio home",
    )
    render.write_html(DASHBOARD, markup)
    print(f"wrote {DASHBOARD}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AI sales lead management")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo").set_defaults(func=cmd_demo)
    sub.add_parser("list").set_defaults(func=cmd_list)

    report = sub.add_parser("report")
    report.add_argument("--start", default=None, help="YYYY-MM-DD, default all leads")
    report.set_defaults(func=cmd_report)

    approve = sub.add_parser("approve")
    approve.add_argument("lead_id", type=int)
    approve.add_argument("--by", required=True)
    approve.set_defaults(func=cmd_approve)

    send = sub.add_parser("send")
    send.add_argument("lead_id", type=int)
    send.set_defaults(func=cmd_send)

    status = sub.add_parser("status")
    status.add_argument("lead_id", type=int)
    status.add_argument("status", choices=list(leads.VALID_STATUSES))
    status.set_defaults(func=cmd_status)

    dash = sub.add_parser("dashboard")
    dash.add_argument("--start", default=None)
    dash.set_defaults(func=cmd_dashboard)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
