"""Command line entry point for Project 1.

    python run.py demo            # reset and process the sample inbox
    python run.py list            # show tickets and their status
    python run.py approve 3 --by "Kelvin M"
    python run.py send 3
    python run.py report --day 2026-11-20
    python run.py dashboard       # write dashboard.html
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

import support  # noqa: E402
from engine import db, render  # noqa: E402

TABLES = ["drafts", "events", "rejected", "tickets"]
INBOX = os.path.join(HERE, "data", "inbox.jsonl")
DASHBOARD = os.path.join(HERE, "dashboard.html")


def cmd_demo(args) -> int:
    con = support.connect()
    db.reset(con, TABLES)
    result = support.ingest_file(con, INBOX)
    print(json.dumps(result["counts"], indent=2))
    for problem in result["line_errors"]:
        print(f"line error: {problem}")
    summary = support.report(con)
    print(json.dumps({k: v for k, v in summary.items() if k not in {"by_category", "by_status"}},
                     indent=2))
    return 0


def cmd_list(args) -> int:
    con = support.connect()
    rows = db.rows(con, """
        SELECT t.id, t.external_id, t.category, t.urgency, t.status, t.escalated,
               t.needs_review, d.source AS draft_source
        FROM tickets t LEFT JOIN drafts d ON d.ticket_id = t.id
        ORDER BY t.id
    """)
    for row in rows:
        print(f"{row['id']:>3}  {row['external_id']:<9} {row['category']:<10} "
              f"{row['urgency']:<7} {row['status']:<18} "
              f"{'escalated' if row['escalated'] else '':<10} {row['draft_source'] or ''}")
    return 0


def cmd_approve(args) -> int:
    con = support.connect()
    print(json.dumps(support.approve(con, args.ticket_id, args.by), indent=2))
    return 0


def cmd_send(args) -> int:
    con = support.connect()
    try:
        print(json.dumps(support.send(con, args.ticket_id), indent=2))
    except PermissionError as exc:
        print(f"refused: {exc}")
        return 1
    return 0


def cmd_report(args) -> int:
    con = support.connect()
    print(json.dumps(support.report(con, args.day), indent=2))
    return 0


def cmd_dashboard(args) -> int:
    con = support.connect()
    summary = support.report(con, args.day)

    tickets = db.rows(con, """
        SELECT t.id, t.external_id, t.customer_name, t.category, t.urgency,
               t.sentiment, t.status, t.escalation_reason,
               d.source AS draft_source, d.approved
        FROM tickets t LEFT JOIN drafts d ON d.ticket_id = t.id
        ORDER BY t.id DESC
    """)
    for row in tickets:
        row["escalated_label"] = "escalated" if row["escalation_reason"] else ""
        row["approved_label"] = "approved" if row["approved"] else "pending"

    rejected = db.rows(con, "SELECT external_id, problems, at FROM rejected ORDER BY id DESC")

    stats = [
        {"label": "Tickets today", "value": summary["total"], "hint": summary["day"]},
        {"label": "Escalated", "value": summary["escalated"],
         "hint": f"{summary['escalation_rate']}% of volume"},
        {"label": "Needs review", "value": summary["needs_review"], "hint": "low classifier confidence"},
        {"label": "Rejected input", "value": summary["rejected"], "hint": "failed validation"},
    ]
    sections = [
        {
            "title": "Ticket queue",
            "description": "Every message, its classification and where it sits in the approval flow.",
            "columns": [
                ("id", "#", "num"), ("external_id", "Ref", "text"),
                ("customer_name", "Customer", "text"), ("category", "Category", "tag"),
                ("urgency", "Urgency", "tag"), ("status", "Status", "tag"),
                ("escalated_label", "Escalation", "tag"), ("draft_source", "Draft", "tag"),
            ],
            "rows": tickets,
            "empty": "No tickets yet. Run `python run.py demo`.",
        },
        {
            "title": "Escalation reasons",
            "description": "Why each escalated ticket needs a human before anything is sent.",
            "columns": [("external_id", "Ref", "text"), ("customer_name", "Customer", "text"),
                        ("escalation_reason", "Reason", "text")],
            "rows": [t for t in tickets if t["escalation_reason"]],
            "empty": "No escalations.",
        },
        {
            "title": "Rejected input",
            "description": "Messages stopped by validation, with the reason. Nothing is silently dropped.",
            "columns": [("external_id", "Ref", "text"), ("problems", "Problem", "text"),
                        ("at", "When", "text")],
            "rows": rejected,
            "empty": "No rejected input.",
        },
    ]
    markup = render.dashboard(
        title="AI Customer Support Triage",
        subtitle="Classifies inbound customer messages, drafts a reply, and holds every "
                 "draft for human approval. Complaints, billing disputes and safety "
                 "mentions are escalated instead of auto-answered.",
        stats=stats,
        sections=sections,
        notes=[
            "Synthetic sample data only. No real customer records are used.",
            "Reply drafts are written by a local model when one is running, otherwise by a fixed template.",
            "Nothing is sent automatically. `send` refuses unless a named person approved the draft.",
            "Category and urgency come from keyword rules, not the model, so the routing is reproducible.",
            "Escalated tickets are never auto-sent, even after approval.",
        ],
        footer="Project 1 of 3 - AI Operations portfolio. Figures describe the demo run, not client results.",
        back_href="../index.html",
        back_label="Portfolio home",
    )
    render.write_html(DASHBOARD, markup)
    print(f"wrote {DASHBOARD}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AI customer support triage")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="reset and process the sample inbox").set_defaults(func=cmd_demo)
    sub.add_parser("list", help="list tickets").set_defaults(func=cmd_list)

    approve = sub.add_parser("approve", help="approve a draft")
    approve.add_argument("ticket_id", type=int)
    approve.add_argument("--by", required=True, help="name of the approving person")
    approve.set_defaults(func=cmd_approve)

    send = sub.add_parser("send", help="send an approved draft")
    send.add_argument("ticket_id", type=int)
    send.set_defaults(func=cmd_send)

    report = sub.add_parser("report", help="print the daily report")
    report.add_argument("--day", default=None, help="YYYY-MM-DD, default today (UTC)")
    report.set_defaults(func=cmd_report)

    dash = sub.add_parser("dashboard", help="write dashboard.html")
    dash.add_argument("--day", default=None)
    dash.set_defaults(func=cmd_dashboard)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
