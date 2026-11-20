"""Project 3: AI sales lead management.

Scoring is deliberately transparent: every point comes from a named rule and
the lead stores the breakdown, so a salesperson can challenge a ranking.
The local model only writes the follow-up wording.
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
DB_PATH = os.path.join(HERE, "data", "sales.db")

SPEC = {
    "external_id": {"required": True, "kind": "text", "min": 3, "max": 64},
    "name": {"required": True, "kind": "text", "min": 2, "max": 120},
    "email": {"required": True, "kind": "email"},
    "budget": {"kind": "money", "min": 0, "max": 10000000},
    "employees": {"kind": "int", "min": 0, "max": 1000000},
    "source": {"kind": "choice", "choices": ["referral", "website", "linkedin", "event",
                                             "cold-list", "other"]},
}

SOURCE_POINTS = {"referral": 15, "website": 10, "linkedin": 8, "event": 6,
                 "cold-list": 2, "other": 0}
ROLE_POINTS = [("owner", 10), ("founder", 10), ("director", 10), ("head", 10),
               ("ceo", 10), ("manager", 6)]
TIMELINE_POINTS = [("immediate", 15), ("now", 15), ("this month", 15),
                   ("1-3 months", 10), ("next quarter", 10), ("later", 3)]
BANDS = (("A", 60), ("B", 35))

VALID_STATUSES = ("new", "contacted", "qualified", "won", "lost")
TRANSITIONS = {
    "new": {"contacted", "lost"},
    "contacted": {"qualified", "won", "lost"},
    "qualified": {"won", "lost"},
    "won": set(),
    "lost": {"new"},
}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: str | None = None):
    con = db.connect(path or DB_PATH)
    with open(SCHEMA, encoding="utf-8") as handle:
        db.init(con, handle.read())
    return con


# ---------------------------------------------------------------- scoring

def score_lead(lead: dict) -> dict:
    """Return score, band, segment and a human readable breakdown."""
    parts: list[tuple[str, int]] = []

    source = (lead.get("source") or "other").lower()
    parts.append((f"source {source}", SOURCE_POINTS.get(source, 0)))

    budget = lead.get("budget")
    if budget is None or budget == "":
        parts.append(("no budget stated", 0))
    else:
        budget = float(budget)
        if budget >= 5000:
            parts.append(("budget 5,000+", 20))
        elif budget >= 1000:
            parts.append(("budget 1,000-4,999", 12))
        elif budget > 0:
            parts.append(("budget under 1,000", 5))
        else:
            parts.append(("budget stated as zero", 0))

    timeline = (lead.get("timeline") or "").lower()
    for phrase, points in TIMELINE_POINTS:
        if phrase in timeline:
            parts.append((f"timeline '{phrase}'", points))
            break
    else:
        parts.append(("timeline unknown", 3))

    role = (lead.get("role") or "").lower()
    for phrase, points in ROLE_POINTS:
        if phrase in role:
            parts.append((f"role '{phrase}'", points))
            break
    else:
        parts.append(("role not decision maker", 2))

    employees = lead.get("employees")
    if employees in (None, ""):
        parts.append(("company size unknown", 2))
    else:
        employees = int(employees)
        if employees >= 50:
            parts.append(("company 50+ staff", 8))
        elif employees >= 10:
            parts.append(("company 10-49 staff", 5))
        else:
            parts.append(("company under 10 staff", 2))

    complete = sum(1 for field in ("email", "company", "message") if lead.get(field))
    parts.append((f"{complete}/3 contact details complete", 5 if complete == 3 else 0))

    score = sum(points for _, points in parts)
    band = "C"
    for letter, threshold in BANDS:
        if score >= threshold:
            band = letter
            break

    budget_value = float(budget) if budget not in (None, "") else 0
    if (employees or 0) >= 50 or budget_value >= 5000:
        segment = "key account"
    elif (employees or 0) >= 10 or budget_value >= 1000:
        segment = "growth"
    else:
        segment = "small"

    return {
        "score": score,
        "band": band,
        "segment": segment,
        "score_reason": "; ".join(f"{label} +{points}" for label, points in parts),
    }


# ---------------------------------------------------------------- drafting

_TEMPLATES = {
    "A": (
        "Dear {name},\n\n"
        "Thank you for getting in touch about {topic}. Based on what you described, "
        "the next useful step is a short call to confirm volumes, delivery points and "
        "timing, so I can put a proper quotation together rather than a rough guess.\n\n"
        "Would {slot} suit you for 20 minutes? If not, send me two times that work and "
        "I will fit around them.\n\n"
        "Kind regards,\nKelvin"
    ),
    "B": (
        "Dear {name},\n\n"
        "Thank you for your enquiry about {topic}. I have noted the details and can "
        "share our current price list and lead times.\n\n"
        "So I send the right version, could you confirm roughly how often you would "
        "order and whether delivery is to one site or several?\n\n"
        "Kind regards,\nKelvin"
    ),
    "C": (
        "Dear {name},\n\n"
        "Thank you for your message about {topic}. I have added your details to our "
        "list and will send relevant updates as they come up.\n\n"
        "If your plans become more definite, reply to this email and I will pick it up "
        "straight away.\n\n"
        "Kind regards,\nKelvin"
    ),
}

_SYSTEM = (
    "You write short B2B follow-up emails for a wholesale drinks distributor. "
    "Plain English, no hype, no invented prices, no invented meeting times, no "
    "pressure tactics. Maximum 110 words. Sign off as 'Kelvin'."
)


def _topic(lead: dict) -> str:
    message = (lead.get("message") or "").strip()
    if not message:
        return "your enquiry"
    first = re.split(r"[.!?\n]", message)[0].strip()
    return first[:90].lower() or "your enquiry"


def template_draft(lead: dict) -> str:
    name = (lead.get("name") or "there").split()[0]
    body = _TEMPLATES.get(lead["band"], _TEMPLATES["C"])
    return body.format(name=name, topic=_topic(lead), slot="Tuesday morning")


def model_draft(lead: dict) -> str | None:
    prompt = (
        f"Lead band: {lead['band']} (score {lead['score']})\n"
        f"Segment: {lead['segment']}\n"
        f"Name: {lead.get('name')}\nCompany: {lead.get('company') or 'unknown'}\n"
        f"Source: {lead.get('source')}\n"
        f"Their message: {lead.get('message') or '(none)'}\n\n"
        "Write only the email body."
    )
    return llm.generate(prompt, system=_SYSTEM, max_tokens=260)


# ---------------------------------------------------------------- pipeline

def capture(con, lead: dict) -> dict:
    problems = validate.validate(lead, SPEC)
    if problems:
        db.insert(con, "rejected", {
            "external_id": lead.get("external_id"),
            "payload": json.dumps(lead, ensure_ascii=False),
            "problems": "; ".join(f"{f} {m}" for f, m in problems),
            "at": now(),
        })
        return {"external_id": lead.get("external_id"), "outcome": "rejected",
                "problems": [f"{f} {m}" for f, m in problems]}

    existing = db.one(con, "SELECT id, status, email, external_id FROM leads "
                           "WHERE external_id = ? OR lower(email) = lower(?)",
                      (lead["external_id"], lead["email"].strip()))
    if existing:
        matched = "email" if existing["external_id"] != lead["external_id"] else "reference"
        db.insert(con, "activities", {
            "lead_id": existing["id"], "kind": "duplicate",
            "detail": f"repeat enquiry {lead['external_id']} matched on {matched}", "at": now()})
        return {"external_id": lead["external_id"], "outcome": "duplicate",
                "lead_id": existing["id"], "status": existing["status"],
                "matched_on": matched}

    scored = score_lead(lead)
    row = {
        "external_id": lead["external_id"],
        "name": lead["name"].strip(),
        "email": lead["email"].strip(),
        "company": (lead.get("company") or "").strip() or None,
        "source": (lead.get("source") or "other").lower(),
        "role": lead.get("role"),
        "employees": int(lead["employees"]) if lead.get("employees") not in (None, "") else None,
        "budget": float(lead["budget"]) if lead.get("budget") not in (None, "") else None,
        "timeline": lead.get("timeline"),
        "message": lead.get("message"),
        "segment": scored["segment"],
        "score": scored["score"],
        "band": scored["band"],
        "score_reason": scored["score_reason"],
        "status": "new",
        "created_at": now(),
    }
    lead_id = db.insert(con, "leads", row)

    body = model_draft({**row, **scored})
    source = "ollama"
    if not body:
        body, source = template_draft({**row, **scored}), "template"
    db.insert(con, "drafts", {
        "lead_id": lead_id,
        "subject": f"Following up on your enquiry ({row['company'] or row['name']})",
        "body": body,
        "source": source,
    })
    db.insert(con, "activities", {
        "lead_id": lead_id, "kind": "captured",
        "detail": f"band {row['band']} score {row['score']}; {row['score_reason']}",
        "at": now(),
    })
    return {"external_id": row["external_id"], "outcome": "accepted", "lead_id": lead_id,
            "score": row["score"], "band": row["band"], "segment": row["segment"],
            "draft_source": source}


def capture_file(con, path: str) -> dict:
    results, errors = [], []
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                lead = json.loads(line)
            except ValueError:
                errors.append(f"line {number}: invalid JSON")
                db.insert(con, "rejected", {"external_id": None, "payload": line,
                                            "problems": f"line {number}: invalid JSON",
                                            "at": now()})
                continue
            results.append(capture(con, lead))
    counts: dict[str, int] = {}
    for item in results:
        counts[item["outcome"]] = counts.get(item["outcome"], 0) + 1
    return {"counts": counts, "results": results, "errors": errors}


def set_status(con, lead_id: int, status: str, note: str = "") -> dict:
    lead = db.one(con, "SELECT * FROM leads WHERE id = ?", (lead_id,))
    if not lead:
        raise LookupError(f"lead {lead_id} does not exist")
    if status not in VALID_STATUSES:
        raise ValueError(f"unknown status {status}")
    if status not in TRANSITIONS[lead["status"]]:
        raise ValueError(f"cannot move from {lead['status']} to {status}")
    db.execute(con, "UPDATE leads SET status = ?, last_contact_at = ? WHERE id = ?",
               (status, now(), lead_id))
    db.insert(con, "activities", {"lead_id": lead_id, "kind": "status",
                                  "detail": f"{lead['status']} -> {status} {note}".strip(),
                                  "at": now()})
    return {"lead_id": lead_id, "status": status}


def approve(con, lead_id: int, approver: str) -> dict:
    draft = db.one(con, "SELECT id FROM drafts WHERE lead_id = ? ORDER BY id DESC LIMIT 1",
                   (lead_id,))
    if not draft:
        raise LookupError(f"lead {lead_id} has no draft")
    db.execute(con, "UPDATE drafts SET approved = 1, approved_by = ?, approved_at = ? WHERE id = ?",
               (approver, now(), draft["id"]))
    db.insert(con, "activities", {"lead_id": lead_id, "kind": "approved",
                                  "detail": approver, "at": now()})
    return {"lead_id": lead_id, "approved_by": approver}


def send(con, lead_id: int) -> dict:
    lead = db.one(con, "SELECT * FROM leads WHERE id = ?", (lead_id,))
    if not lead:
        raise LookupError(f"lead {lead_id} does not exist")
    draft = db.one(con, "SELECT * FROM drafts WHERE lead_id = ? ORDER BY id DESC LIMIT 1",
                   (lead_id,))
    if not draft:
        raise LookupError(f"lead {lead_id} has no draft")
    if not draft["approved"]:
        raise PermissionError("follow-up has not been approved by a human")
    if lead["status"] == "lost":
        raise PermissionError("lead is marked lost; reopen it before sending")

    os.makedirs(OUTBOX, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", lead["external_id"])
    path = os.path.join(OUTBOX, f"{safe}.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"To: {lead['email']}\nSubject: {draft['subject']}\n\n")
        handle.write(draft["body"].rstrip() + "\n")

    db.execute(con, "UPDATE drafts SET sent = 1, sent_at = ? WHERE id = ?", (now(), draft["id"]))
    db.execute(con, "UPDATE leads SET last_contact_at = ? WHERE id = ?", (now(), lead_id))
    db.insert(con, "activities", {"lead_id": lead_id, "kind": "sent",
                                  "detail": path, "at": now()})
    return {"lead_id": lead_id, "file": path, "band": lead["band"]}


# ---------------------------------------------------------------- reporting

def weekly_report(con, start: str | None = None) -> dict:
    """Seven day summary. ``start`` is a YYYY-MM-DD prefix, default: last 7 days."""
    if start:
        clause, params = "substr(created_at, 1, 10) >= ?", (start,)
    else:
        clause, params = "1 = 1", ()
    by_band = db.rows(con, f"SELECT band, COUNT(*) AS n FROM leads WHERE {clause} "
                           "GROUP BY band ORDER BY band", params)
    by_source = db.rows(con, f"SELECT source, COUNT(*) AS n FROM leads WHERE {clause} "
                             "GROUP BY source ORDER BY n DESC", params)
    by_status = db.rows(con, f"SELECT status, COUNT(*) AS n FROM leads WHERE {clause} "
                             "GROUP BY status ORDER BY n DESC", params)
    total = db.scalar(con, f"SELECT COUNT(*) FROM leads WHERE {clause}", params)
    avg_score = db.scalar(con, f"SELECT AVG(score) FROM leads WHERE {clause}", params, 0)
    pipeline = db.scalar(con, "SELECT ROUND(SUM(budget), 2) FROM leads "
                              "WHERE status IN ('new', 'contacted', 'qualified')")
    awaiting = db.scalar(con, "SELECT COUNT(*) FROM drafts WHERE approved = 0 AND sent = 0")
    return {
        "start": start or "all",
        "total": total,
        "average_score": round(float(avg_score or 0), 1),
        "by_band": by_band,
        "by_source": by_source,
        "by_status": by_status,
        "stated_pipeline_value": pipeline or 0,
        "awaiting_approval": awaiting,
        "rejected": db.scalar(con, f"SELECT COUNT(*) FROM rejected WHERE {clause}", params),
    }
