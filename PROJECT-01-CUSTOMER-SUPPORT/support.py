"""Project 1: AI customer support triage.

Pipeline: validate -> classify -> decide escalation -> draft reply ->
queue for human approval -> (after approval) send.

Routing is rule based and auditable. The local model only writes the reply
text, and a template is used when no model is running.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

from engine import db, llm, validate

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "schema.sql")
OUTBOX = os.path.join(HERE, "outbox")
DB_PATH = os.path.join(HERE, "data", "support.db")

SPEC = {
    "external_id": {"required": True, "kind": "text", "min": 3, "max": 64},
    "customer_email": {"required": True, "kind": "email"},
    "body": {"required": True, "kind": "text", "min": 10, "max": 4000},
    "channel": {"kind": "choice", "choices": ["email", "web", "whatsapp", "phone"]},
}

CATEGORIES = ("complaint", "inquiry", "request", "billing", "feedback", "other")

# Ties are broken by this order: a complaint beats a billing query, and so on.
PRIORITY = ("complaint", "billing", "request", "feedback", "inquiry")

_KEYWORDS = {
    "complaint": [
        "damaged", "broken", "wrong item", "not delivered", "never arrived",
        "late", "delayed", "poor", "terrible", "unacceptable", "angry",
        "disappointed", "faulty", "missing", "short delivery", "expired",
        "allergic", "reaction", "fell ill", "sick after", "hospital",
        "safety", "health", "contaminated", "mouldy", "moldy",
    ],
    "billing": [
        "invoice", "payment", "charged", "overcharged", "receipt",
        "statement", "credit note", "refund", "wrong price", "pricing error",
    ],
    "request": [
        "please send", "could you", "can you", "need a", "request",
        "update my", "change my", "arrange", "book", "schedule", "quotation",
        "price list", "stock out", "out of stock", "completely out",
        "run out", "ran out", "short of stock", "reorder",
    ],
    "feedback": ["suggestion", "feedback", "thank you", "thanks", "great service", "well done"],
    "inquiry": ["how do", "what is", "when will", "do you", "is there", "could you tell", "?"],
}

_URGENT = [
    "urgent", "asap", "immediately", "right away", "today", "by end of day",
    "deadline", "critical", "emergency", "escalate", "manager",
]
_NEGATIVE = ["angry", "unacceptable", "terrible", "disappointed", "frustrated",
             "poor", "worst", "complaint", "faulty", "damaged", "wrong"]
_POSITIVE = ["thank", "thanks", "great", "excellent", "appreciate", "happy"]
_SENSITIVE = ["refund", "compensation", "legal", "lawyer", "solicitor", "sue",
              "injury", "health", "safety", "food safety", "expired", "allergic"]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: str | None = None):
    con = db.connect(path or DB_PATH)
    with open(SCHEMA, encoding="utf-8") as handle:
        db.init(con, handle.read())
    return con


def _score(text: str, words) -> int:
    return sum(1 for word in words if word in text)


def classify(subject: str, body: str) -> dict:
    """Return category, urgency, sentiment and a confidence signal."""
    text = f"{subject} {body}".lower()
    scores = {name: _score(text, words) for name, words in _KEYWORDS.items()}
    # A question mark alone should not outrank a clear complaint.
    if scores["complaint"]:
        scores["inquiry"] = 0
    best = max(scores, key=lambda k: (scores[k], -PRIORITY.index(k)))
    confident = scores[best] > 0
    category = best if confident else "other"

    urgency = "high" if _score(text, _URGENT) else ("medium" if category == "complaint" else "low")

    negative, positive = _score(text, _NEGATIVE), _score(text, _POSITIVE)
    if negative > positive:
        sentiment = "negative"
    elif positive > negative:
        sentiment = "positive"
    else:
        sentiment = "neutral"

    return {
        "category": category,
        "urgency": urgency,
        "sentiment": sentiment,
        "needs_review": 0 if confident else 1,
        "classifier": "rules",
    }


def escalation(category: str, urgency: str, sentiment: str, text: str) -> tuple[bool, str]:
    """Decide whether a human must handle this before any reply goes out."""
    lowered = text.lower()
    reasons = []
    if _score(lowered, _SENSITIVE):
        reasons.append("mentions refund, compensation, legal, health or safety")
    if urgency == "high":
        reasons.append("marked urgent by the sender")
    if category == "complaint" and sentiment == "negative":
        reasons.append("negative complaint")
    if "escalate" in lowered or "manager" in lowered:
        reasons.append("asks for a manager or escalation")
    return (bool(reasons), "; ".join(reasons))


_TEMPLATES = {
    "complaint": (
        "Dear {name},\n\n"
        "Thank you for telling us about this, and I am sorry the order did not "
        "meet the standard you expected. I have logged your message as a formal "
        "complaint under reference {ref}.\n\n"
        "What happens next: a member of the team will review the details and come "
        "back to you within one working day with the options available to you. "
        "If anything else is affected, please reply to this message and it will be "
        "added to the same case.\n\n"
        "Kind regards,\nCustomer Support"
    ),
    "billing": (
        "Dear {name},\n\n"
        "Thank you for your message about billing. I have logged it under reference "
        "{ref} and passed the details to the accounts team.\n\n"
        "To help them check it quickly, please confirm the invoice number and the "
        "date of the charge if you have them to hand. You will receive a written "
        "response within two working days.\n\n"
        "Kind regards,\nCustomer Support"
    ),
    "request": (
        "Dear {name},\n\n"
        "Thank you for your request. I have recorded it under reference {ref} and "
        "the team will confirm what is possible and when.\n\n"
        "If the request is time sensitive, reply with the date you need it by and "
        "we will prioritise accordingly.\n\n"
        "Kind regards,\nCustomer Support"
    ),
    "feedback": (
        "Dear {name},\n\n"
        "Thank you for taking the time to write. Your comments have been logged "
        "under reference {ref} and shared with the team that looks after this area.\n\n"
        "Kind regards,\nCustomer Support"
    ),
    "inquiry": (
        "Dear {name},\n\n"
        "Thank you for your question. I have logged it under reference {ref} so it "
        "can be answered properly rather than from memory.\n\n"
        "A colleague with the right detail will reply within one working day.\n\n"
        "Kind regards,\nCustomer Support"
    ),
    "other": (
        "Dear {name},\n\n"
        "Thank you for your message. It has been logged under reference {ref} and "
        "a member of the team will review it.\n\n"
        "Kind regards,\nCustomer Support"
    ),
}


def template_draft(ticket: dict) -> str:
    name = (ticket.get("customer_name") or "Customer").split()[0]
    body = _TEMPLATES.get(ticket["category"], _TEMPLATES["other"])
    return body.format(name=name, ref=ticket["external_id"])


_SYSTEM = (
    "You write short, plain-English customer support replies for a wholesale "
    "distribution business. Be warm, specific and honest. Never promise a refund, "
    "a delivery date or compensation. Never invent order details. Maximum 120 words. "
    "Sign off as 'Customer Support'."
)


def model_draft(ticket: dict) -> str | None:
    prompt = (
        f"Category: {ticket['category']}\n"
        f"Urgency: {ticket['urgency']}\n"
        f"Customer: {ticket.get('customer_name') or 'unknown'}\n"
        f"Subject: {ticket.get('subject') or '(none)'}\n"
        f"Message:\n{ticket['body']}\n\n"
        "Write only the reply body."
    )
    return llm.generate(prompt, system=_SYSTEM, max_tokens=280)


def ingest(con, message: dict) -> dict:
    """Process one inbound message. Returns a result summary."""
    problems = validate.validate(message, SPEC)
    if problems:
        db.insert(con, "rejected", {
            "external_id": message.get("external_id"),
            "payload": json.dumps(message, ensure_ascii=False),
            "problems": "; ".join(f"{field} {msg}" for field, msg in problems),
            "at": now(),
        })
        return {"external_id": message.get("external_id"), "outcome": "rejected",
                "problems": [f"{f} {m}" for f, m in problems]}

    existing = db.one(con, "SELECT id, status FROM tickets WHERE external_id = ?",
                      (message["external_id"],))
    if existing:
        return {"external_id": message["external_id"], "outcome": "duplicate",
                "ticket_id": existing["id"], "status": existing["status"]}

    subject = (message.get("subject") or "").strip()
    body = message["body"].strip()
    verdict = classify(subject, body)
    escalated, reason = escalation(verdict["category"], verdict["urgency"],
                                   verdict["sentiment"], f"{subject} {body}")

    ticket = {
        "external_id": message["external_id"],
        "channel": message.get("channel") or "email",
        "customer_name": message.get("customer_name"),
        "customer_email": message["customer_email"],
        "subject": subject,
        "body": body,
        "received_at": message.get("received_at") or now(),
        "category": verdict["category"],
        "urgency": verdict["urgency"],
        "sentiment": verdict["sentiment"],
        "escalated": 1 if escalated else 0,
        "escalation_reason": reason,
        "status": "escalated" if escalated else "awaiting_approval",
        "needs_review": verdict["needs_review"],
        "classifier": verdict["classifier"],
        "created_at": now(),
    }
    ticket_id = db.insert(con, "tickets", ticket)

    draft_body = model_draft(ticket)
    source = "ollama"
    if not draft_body:
        draft_body, source = template_draft(ticket), "template"
    db.insert(con, "drafts", {
        "ticket_id": ticket_id,
        "subject": f"Re: {subject}" if subject else "Your message",
        "body": draft_body,
        "source": source,
    })
    db.insert(con, "events", {
        "ticket_id": ticket_id, "kind": "ingested",
        "detail": f"{ticket['category']}/{ticket['urgency']}/{ticket['sentiment']}"
                  + (f"; escalated: {reason}" if escalated else ""),
        "at": now(),
    })
    return {"external_id": ticket["external_id"], "outcome": "accepted",
            "ticket_id": ticket_id, "category": ticket["category"],
            "urgency": ticket["urgency"], "status": ticket["status"],
            "draft_source": source}


def ingest_file(con, path: str) -> dict:
    """Ingest a JSONL inbox. Bad lines are rejected, never silently skipped."""
    results, line_errors = [], []
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError as exc:
                line_errors.append(f"line {number}: invalid JSON ({exc})")
                db.insert(con, "rejected", {
                    "external_id": None, "payload": line,
                    "problems": f"line {number}: invalid JSON", "at": now()})
                continue
            results.append(ingest(con, message))
    counts: dict[str, int] = {}
    for item in results:
        counts[item["outcome"]] = counts.get(item["outcome"], 0) + 1
    return {"counts": counts, "results": results, "line_errors": line_errors}


def approve(con, ticket_id: int, approver: str) -> dict:
    draft = db.one(con, "SELECT id FROM drafts WHERE ticket_id = ? ORDER BY id DESC LIMIT 1",
                   (ticket_id,))
    if not draft:
        raise LookupError(f"ticket {ticket_id} has no draft to approve")
    db.execute(con, "UPDATE drafts SET approved = 1, approved_by = ?, approved_at = ? WHERE id = ?",
               (approver, now(), draft["id"]))
    db.execute(con, "UPDATE tickets SET status = 'approved' WHERE id = ?", (ticket_id,))
    db.insert(con, "events", {"ticket_id": ticket_id, "kind": "approved",
                              "detail": approver, "at": now()})
    return {"ticket_id": ticket_id, "status": "approved", "approved_by": approver}


def send(con, ticket_id: int) -> dict:
    """Send an approved draft. Refuses anything a human has not approved."""
    ticket = db.one(con, "SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    if not ticket:
        raise LookupError(f"ticket {ticket_id} does not exist")
    if ticket["escalated"]:
        raise PermissionError("escalated tickets must be answered by a human, not auto-sent")
    draft = db.one(con, "SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id DESC LIMIT 1",
                   (ticket_id,))
    if not draft:
        raise LookupError(f"ticket {ticket_id} has no draft")
    if not draft["approved"]:
        raise PermissionError("draft has not been approved by a human")

    os.makedirs(OUTBOX, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", ticket["external_id"])
    path = os.path.join(OUTBOX, f"{safe}.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"To: {ticket['customer_email']}\n")
        handle.write(f"Subject: {draft['subject']}\n\n")
        handle.write(draft["body"].rstrip() + "\n")

    db.execute(con, "UPDATE drafts SET sent = 1, sent_at = ? WHERE id = ?", (now(), draft["id"]))
    db.execute(con, "UPDATE tickets SET status = 'sent' WHERE id = ?", (ticket_id,))
    db.insert(con, "events", {"ticket_id": ticket_id, "kind": "sent",
                              "detail": path, "at": now()})
    return {"ticket_id": ticket_id, "status": "sent", "file": path}


def report(con, day: str | None = None) -> dict:
    """Daily activity report. ``day`` is YYYY-MM-DD; default is today (UTC)."""
    day = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    where = "substr(created_at, 1, 10) = ?"
    total = db.scalar(con, f"SELECT COUNT(*) FROM tickets WHERE {where}", (day,))
    by_category = db.rows(con, f"SELECT category, COUNT(*) AS n FROM tickets WHERE {where} "
                               "GROUP BY category ORDER BY n DESC", (day,))
    by_status = db.rows(con, f"SELECT status, COUNT(*) AS n FROM tickets WHERE {where} "
                             "GROUP BY status ORDER BY n DESC", (day,))
    escalated = db.scalar(con, f"SELECT COUNT(*) FROM tickets WHERE {where} AND escalated = 1", (day,))
    review = db.scalar(con, f"SELECT COUNT(*) FROM tickets WHERE {where} AND needs_review = 1", (day,))
    rejected = db.scalar(con, "SELECT COUNT(*) FROM rejected WHERE substr(at, 1, 10) = ?", (day,))
    return {
        "day": day,
        "total": total,
        "by_category": by_category,
        "by_status": by_status,
        "escalated": escalated,
        "needs_review": review,
        "rejected": rejected,
        "escalation_rate": round(escalated / total * 100, 1) if total else 0.0,
    }
