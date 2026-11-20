"""Generate the three Make.com scenario build specifications.

Make blueprint exports are opaque JSON from a live account, so these files are
build specifications: module by module, with the deterministic rules in a
separate JavaScript file that can be tested without a Make account.

    python tools/build_scenarios.py

The generated files are not claimed to be imported into or executed by Make.
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


# ---------------------------------------------------------------- project 1

SUPPORT_LOGIC = r"""
// Validate, classify, decide escalation, draft a reply.
// Mirrors PROJECT-01-CUSTOMER-SUPPORT/support.py so the two stay comparable.
const item = payload;
const email = String(item.customer_email || '').trim();
const body = String(item.body || '').trim();
const problems = [];

if (!item.external_id) problems.push('external_id is required');
if (!/^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/.test(email)) problems.push('customer_email is not a valid email address');
if (body.length < 10) problems.push('body must be at least 10 characters');
if (problems.length) {
  return [{ outcome: 'rejected', external_id: item.external_id || null, problems }];
}

const text = `${item.subject || ''} ${body}`.toLowerCase();
const count = (words) => words.filter((w) => text.includes(w)).length;

const keywords = {
  complaint: ['damaged', 'broken', 'wrong item', 'not delivered', 'never arrived', 'late',
              'delayed', 'poor', 'terrible', 'unacceptable', 'angry', 'disappointed', 'faulty',
              'missing', 'expired', 'allergic', 'reaction', 'safety', 'health', 'contaminated'],
  billing: ['invoice', 'payment', 'charged', 'overcharged', 'receipt', 'statement',
            'credit note', 'refund', 'wrong price'],
  request: ['please send', 'could you', 'can you', 'need a', 'request', 'quotation',
            'price list', 'stock out', 'out of stock', 'completely out', 'run out', 'reorder'],
  feedback: ['suggestion', 'feedback', 'thank you', 'thanks', 'great service', 'well done'],
  inquiry: ['how do', 'what is', 'when will', 'do you', 'is there', '?'],
};

const scores = {};
for (const [name, words] of Object.entries(keywords)) scores[name] = count(words);
if (scores.complaint) scores.inquiry = 0;

const priority = ['complaint', 'billing', 'request', 'feedback', 'inquiry'];
let category = 'other';
let best = 0;
for (const name of priority) {
  if (scores[name] > best) { best = scores[name]; category = name; }
}
const needsReview = best === 0 ? 1 : 0;

const urgent = ['urgent', 'asap', 'immediately', 'right away', 'today', 'deadline',
                'critical', 'emergency', 'escalate', 'manager'];
const urgency = count(urgent) ? 'high' : (category === 'complaint' ? 'medium' : 'low');

const negative = count(['angry', 'unacceptable', 'terrible', 'disappointed', 'frustrated',
                        'poor', 'complaint', 'faulty', 'damaged', 'wrong']);
const positive = count(['thank', 'thanks', 'great', 'excellent', 'appreciate', 'happy']);
const sentiment = negative > positive ? 'negative' : (positive > negative ? 'positive' : 'neutral');

const sensitive = ['refund', 'compensation', 'legal', 'lawyer', 'sue', 'injury', 'health',
                   'safety', 'expired', 'allergic'];
const reasons = [];
if (count(sensitive)) reasons.push('mentions refund, compensation, legal, health or safety');
if (urgency === 'high') reasons.push('marked urgent by the sender');
if (category === 'complaint' && sentiment === 'negative') reasons.push('negative complaint');
if (text.includes('escalate') || text.includes('manager')) reasons.push('asks for a manager or escalation');

const escalate = reasons.length > 0;
const name = String(item.customer_name || 'Customer').split(' ')[0];
const ref = item.external_id;

const templates = {
  complaint: `Dear ${name},\n\nThank you for telling us about this, and I am sorry the order did not meet the standard you expected. I have logged your message as a formal complaint under reference ${ref}.\n\nWhat happens next: a member of the team will review the details and come back to you within one working day.\n\nKind regards,\nCustomer Support`,
  billing: `Dear ${name},\n\nThank you for your message about billing. I have logged it under reference ${ref} and passed the details to the accounts team.\n\nPlease confirm the invoice number and the date of the charge if you have them to hand. You will receive a written response within two working days.\n\nKind regards,\nCustomer Support`,
  request: `Dear ${name},\n\nThank you for your request. I have recorded it under reference ${ref} and the team will confirm what is possible and when.\n\nKind regards,\nCustomer Support`,
  feedback: `Dear ${name},\n\nThank you for taking the time to write. Your comments have been logged under reference ${ref} and shared with the team.\n\nKind regards,\nCustomer Support`,
  inquiry: `Dear ${name},\n\nThank you for your question. I have logged it under reference ${ref} so it can be answered properly.\n\nA colleague with the right detail will reply within one working day.\n\nKind regards,\nCustomer Support`,
  other: `Dear ${name},\n\nThank you for your message. It has been logged under reference ${ref} and a member of the team will review it.\n\nKind regards,\nCustomer Support`,
};

return [{
  outcome: 'accepted',
  external_id: ref,
  customer_email: email,
  category,
  urgency,
  sentiment,
  needs_review: needsReview,
  escalate,
  escalation_reason: reasons.join('; '),
  status: escalate ? 'escalated' : 'awaiting_approval',
  draft_subject: `Re: ${item.subject || 'your message'}`,
  draft_body: templates[category] || templates.other,
  approved: false,
}];
""".strip()


# ---------------------------------------------------------------- project 2

INVENTORY_LOGIC = r"""
// Rebuild balances, valuation and alerts from a posted movement list.
// Mirrors PROJECT-02-INVENTORY-MANAGEMENT/inventory.py.
const products = Array.isArray(payload.products) ? payload.products : [];
const movements = Array.isArray(payload.movements) ? payload.movements : [];

if (!products.length) {
  return [{ outcome: 'rejected', problems: ['products array is required'] }];
}

const state = new Map();
for (const p of products) {
  state.set(p.sku, {
    sku: p.sku,
    name: p.name || p.sku,
    unit: p.unit || 'unit',
    reorder_level: Number(p.reorder_level || 0),
    qty: 0,
    avg_cost: 0,
    value: 0,
  });
}

const applied = [];
const rejected = [];
const alerts = [];
const seen = new Set();

for (const [index, m] of movements.entries()) {
  const label = `movement ${index + 1}`;
  const product = state.get(m.sku);
  if (!product) { rejected.push(`${label}: unknown sku ${m.sku}`); continue; }
  if (!['receipt', 'issue', 'adjustment'].includes(m.kind)) {
    rejected.push(`${label}: unknown kind ${m.kind}`); continue;
  }
  const qty = Number(m.qty);
  if (!Number.isFinite(qty) || qty === 0) {
    rejected.push(`${label}: quantity must be a non-zero number`); continue;
  }

  const key = `${m.kind}:${m.sku}:${qty}:${m.reference || ''}`;
  if (seen.has(key)) { rejected.push(`${label}: duplicate of an earlier movement`); continue; }
  seen.add(key);

  const beforeQty = product.qty;
  const beforeCost = product.avg_cost;
  let anomaly = null;

  if (m.kind === 'issue') {
    if (qty < 0) { rejected.push(`${label}: issue quantity must be positive`); continue; }
    if (qty > beforeQty) {
      rejected.push(`${label}: cannot issue ${qty} of ${m.sku}, only ${beforeQty} on hand`);
      continue;
    }
    if (beforeQty > 0 && qty / beforeQty >= 0.4) {
      anomaly = `single issue removed ${Math.round((qty / beforeQty) * 100)}% of stock on hand`;
    }
    product.qty = beforeQty - qty;
  } else if (m.kind === 'receipt') {
    const cost = Number(m.unit_cost);
    if (!Number.isFinite(cost) || cost < 0) {
      rejected.push(`${label}: receipt needs a unit cost of zero or more`); continue;
    }
    if (beforeCost > 0 && Math.abs(cost - beforeCost) / beforeCost > 0.25) {
      anomaly = `purchase price ${cost} is more than 25% away from average ${beforeCost}`;
    }
    product.qty = beforeQty + qty;
    product.avg_cost = (beforeQty * beforeCost + qty * cost) / product.qty;
  } else {
    if (beforeQty + qty < 0) {
      rejected.push(`${label}: adjustment would leave ${m.sku} negative`); continue;
    }
    if (qty < 0) anomaly = `negative adjustment of ${Math.abs(qty)} ${product.unit}`;
    product.qty = beforeQty + qty;
  }

  if (anomaly) alerts.push({ sku: m.sku, kind: 'anomaly', message: anomaly });
  if (product.qty <= 0) alerts.push({ sku: m.sku, kind: 'out_of_stock', message: `${m.sku} is out of stock` });
  else if (product.qty <= product.reorder_level) {
    alerts.push({ sku: m.sku, kind: 'low_stock',
                  message: `${m.sku} at ${product.qty}, at or below reorder level ${product.reorder_level}` });
  }

  applied.push({ sku: m.sku, kind: m.kind, qty, reference: m.reference || null, anomaly });
}

const lines = [...state.values()].map((p) => ({
  ...p,
  avg_cost: Number(p.avg_cost.toFixed(4)),
  value: Number((p.qty * p.avg_cost).toFixed(2)),
}));

return [{
  outcome: 'processed',
  applied: applied.length,
  rejected: rejected.length,
  rejections: rejected,
  alerts,
  stock_value: Number(lines.reduce((sum, p) => sum + p.value, 0).toFixed(2)),
  low_stock: lines.filter((p) => p.qty <= p.reorder_level).map((p) => p.sku),
  lines,
}];
""".strip()


# ---------------------------------------------------------------- project 3

LEADS_LOGIC = r"""
// Score a lead against published criteria and draft a band-matched follow-up.
// Mirrors PROJECT-03-SALES-AUTOMATION/leads.py.
const item = payload;
const problems = [];

if (!item.external_id) problems.push('external_id is required');
if (!item.name || String(item.name).trim().length < 2) problems.push('name is required');
const email = String(item.email || '').trim();
if (!/^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/.test(email)) {
  problems.push('email is not a valid email address');
}
if (problems.length) {
  return [{ outcome: 'rejected', external_id: item.external_id || null, problems }];
}

const parts = [];
const add = (label, points) => parts.push({ label, points });

const sourcePoints = { referral: 15, website: 10, linkedin: 8, event: 6, 'cold-list': 2, other: 0 };
const source = String(item.source || 'other').toLowerCase();
add(`source ${source}`, sourcePoints[source] ?? 0);

const budget = item.budget === null || item.budget === undefined || item.budget === ''
  ? null : Number(item.budget);
if (budget === null) add('no budget stated', 0);
else if (budget >= 5000) add('budget 5,000+', 20);
else if (budget >= 1000) add('budget 1,000-4,999', 12);
else if (budget > 0) add('budget under 1,000', 5);
else add('budget stated as zero', 0);

const timeline = String(item.timeline || '').toLowerCase();
const timelineRules = [['immediate', 15], ['now', 15], ['this month', 15],
                       ['1-3 months', 10], ['next quarter', 10], ['later', 3]];
const timelineHit = timelineRules.find(([phrase]) => timeline.includes(phrase));
add(timelineHit ? `timeline '${timelineHit[0]}'` : 'timeline unknown', timelineHit ? timelineHit[1] : 3);

const role = String(item.role || '').toLowerCase();
const roleRules = [['owner', 10], ['founder', 10], ['director', 10], ['head', 10],
                   ['ceo', 10], ['manager', 6]];
const roleHit = roleRules.find(([phrase]) => role.includes(phrase));
add(roleHit ? `role '${roleHit[0]}'` : 'role not decision maker', roleHit ? roleHit[1] : 2);

const employees = item.employees === null || item.employees === undefined || item.employees === ''
  ? null : Number(item.employees);
if (employees === null) add('company size unknown', 2);
else if (employees >= 50) add('company 50+ staff', 8);
else if (employees >= 10) add('company 10-49 staff', 5);
else add('company under 10 staff', 2);

const complete = ['email', 'company', 'message'].filter((f) => item[f]).length;
add(`${complete}/3 contact details complete`, complete === 3 ? 5 : 0);

const score = parts.reduce((sum, p) => sum + p.points, 0);
const band = score >= 60 ? 'A' : (score >= 35 ? 'B' : 'C');
const segment = (employees || 0) >= 50 || (budget || 0) >= 5000
  ? 'key account'
  : ((employees || 0) >= 10 || (budget || 0) >= 1000 ? 'growth' : 'small');

const first = String(item.name).trim().split(' ')[0];
const topic = String(item.message || 'your enquiry').split(/[.!?\n]/)[0].trim().toLowerCase().slice(0, 90);

const bodies = {
  A: `Dear ${first},\n\nThank you for getting in touch about ${topic}. The next useful step is a short call to confirm volumes, delivery points and timing, so I can put a proper quotation together.\n\nKind regards,\nKelvin`,
  B: `Dear ${first},\n\nThank you for your enquiry about ${topic}. I can share our current price list and lead times. Could you confirm roughly how often you would order and whether delivery is to one site or several?\n\nKind regards,\nKelvin`,
  C: `Dear ${first},\n\nThank you for your message about ${topic}. I have added your details to our list and will send relevant updates as they come up.\n\nKind regards,\nKelvin`,
};

return [{
  outcome: 'accepted',
  external_id: item.external_id,
  name: item.name,
  email,
  company: item.company || null,
  source,
  score,
  band,
  segment,
  score_reason: parts.map((p) => `${p.label} +${p.points}`).join('; '),
  status: 'new',
  draft_subject: `Following up on your enquiry (${item.company || item.name})`,
  draft_body: bodies[band],
  approved: false,
}];
""".strip()


# ---------------------------------------------------------------- builders

ERROR_HANDLING = (
    "Set optional Sheets and Email modules to continue on error so a failed "
    "write cannot block the webhook response. Retry once on transient errors. "
    "Keep the scenario in draft until credentials are configured."
)


def spec(name: str, purpose: str, steps: list[dict], routes: list[dict],
         rules_note: str, approval: str, credentials: list[str]) -> dict:
    return {
        "spec_version": 1,
        "platform": "Make.com",
        "verified_in_make": False,
        "status": "Build specification, not an imported or executed blueprint",
        "scenario": {
            "name": name,
            "purpose": purpose,
            "schedule": "On demand - custom webhook",
            "steps": steps,
            "routes": routes,
            "rules_file": "make-logic.js",
            "rules_note": rules_note,
            "approval_gate": approval,
            "error_handling": ERROR_HANDLING,
            "credentials_required": credentials,
        },
    }


def support_spec() -> dict:
    steps = [
        {"step": 1, "module": "Webhook > Custom webhook", "label": "Customer enquiry",
         "config": "POST. Accept external_id, customer_name, customer_email, subject and body."},
        {"step": 2, "module": "Tools > Set variable", "label": "Validate and classify",
         "config": "Apply make-logic.js. Output outcome, external_id, customer_email, category, "
                   "urgency, sentiment, needs_review, escalate, escalation_reason, status, "
                   "draft_subject, draft_body and approved. Bad input returns outcome=rejected "
                   "with a problems list."},
        {"step": 3, "module": "Router", "label": "Escalate?",
         "config": "Route on the escalate field from step 2."},
        {"step": 4, "module": "Google Sheets > Add a row", "label": "Human queue",
         "config": "Append to sheet 'Escalations'. Leave inactive until a Sheets connection exists."},
        {"step": 5, "module": "Google Sheets > Add a row", "label": "Approval queue",
         "config": "Append to sheet 'Approval queue'. Leave inactive until a Sheets connection exists."},
        {"step": 6, "module": "Webhook > Webhook response", "label": "Return result",
         "config": "Return the step 2 result as JSON."},
    ]
    routes = [
        {"from": 1, "to": 2, "condition": "always"},
        {"from": 2, "to": 3, "condition": "always"},
        {"from": 3, "to": 4, "condition": "escalate = true"},
        {"from": 3, "to": 5, "condition": "escalate = false"},
        {"from": 4, "to": 6, "condition": "always"},
        {"from": 5, "to": 6, "condition": "always"},
    ]
    return spec(
        "P1 - AI customer support triage",
        "Classify an enquiry, escalate what a human must handle, and draft a reply nobody can send without approval.",
        steps, routes,
        "Escalation is a rule, not a model guess: complaints, refund or legal wording, health and "
        "safety mentions and anything marked urgent go to a human.",
        "approved starts false. There is no send-email module in the default path; sending is a "
        "separate step a person triggers after approval.",
        ["Google Sheets (optional - not connected in this repository)"],
    )


def inventory_spec() -> dict:
    steps = [
        {"step": 1, "module": "Webhook > Custom webhook", "label": "Stock movements",
         "config": "POST. Accept a products array and a movements array."},
        {"step": 2, "module": "Tools > Set variable", "label": "Rebuild balances",
         "config": "Apply make-logic.js. Reject unknown SKUs, unknown kinds, duplicates and "
                   "oversells; output applied, rejected, rejections, alerts, stock_value, "
                   "low_stock and lines."},
        {"step": 3, "module": "Router", "label": "Alerts raised?",
         "config": "Route on whether the alerts list from step 2 is empty."},
        {"step": 4, "module": "Email > Send an email", "label": "Email the buyer",
         "config": "Summarise the alerts. Leave inactive until a mailbox connection exists."},
        {"step": 5, "module": "Webhook > Webhook response", "label": "Return result",
         "config": "Return the step 2 result as JSON."},
    ]
    routes = [
        {"from": 1, "to": 2, "condition": "always"},
        {"from": 2, "to": 3, "condition": "always"},
        {"from": 3, "to": 4, "condition": "alerts is not empty"},
        {"from": 3, "to": 5, "condition": "alerts is empty"},
        {"from": 4, "to": 5, "condition": "always"},
    ]
    return spec(
        "P2 - AI inventory and stock control",
        "Rebuild stock balances and moving average cost from posted movements and flag unusual transactions.",
        steps, routes,
        "A single issue over 40% of stock on hand, or a purchase price more than 25% away from "
        "the average, is flagged. Oversells and duplicates are refused, never silently dropped.",
        "The email route is inactive until connected. No movement is written back to a system of "
        "record by this scenario.",
        ["Email (optional - not connected in this repository)"],
    )


def leads_spec() -> dict:
    steps = [
        {"step": 1, "module": "Webhook > Custom webhook", "label": "New lead",
         "config": "POST. Accept external_id, name, email, company, source, role, employees, "
                   "budget, timeline and message."},
        {"step": 2, "module": "Tools > Set variable", "label": "Score and draft",
         "config": "Apply make-logic.js. Output score, band, segment, score_reason, status and "
                   "a band-matched draft_subject and draft_body. approved starts false."},
        {"step": 3, "module": "Router", "label": "Band A?",
         "config": "Route on band = A from step 2."},
        {"step": 4, "module": "Google Sheets > Add a row", "label": "Flag for priority call",
         "config": "Append to sheet 'Priority leads'. Leave inactive until a Sheets connection exists."},
        {"step": 5, "module": "Webhook > Webhook response", "label": "Return result",
         "config": "Return the step 2 result as JSON."},
    ]
    routes = [
        {"from": 1, "to": 2, "condition": "always"},
        {"from": 2, "to": 3, "condition": "always"},
        {"from": 3, "to": 4, "condition": "band = A"},
        {"from": 3, "to": 5, "condition": "band is B or C"},
        {"from": 4, "to": 5, "condition": "always"},
    ]
    return spec(
        "P3 - AI sales lead management",
        "Score a lead against published criteria and draft a band-matched follow-up for human approval.",
        steps, routes,
        "Six named rules, maximum 73 points. Every point is returned in score_reason so a "
        "salesperson can challenge the ranking.",
        "approved starts false. The scenario drafts a follow-up but never sends it; a person "
        "reviews and sends from the CRM or mailbox.",
        ["Google Sheets (optional - not connected in this repository)"],
    )


SCENARIOS = [
    ("PROJECT-01-CUSTOMER-SUPPORT", support_spec, SUPPORT_LOGIC),
    ("PROJECT-02-INVENTORY-MANAGEMENT", inventory_spec, INVENTORY_LOGIC),
    ("PROJECT-03-SALES-AUTOMATION", leads_spec, LEADS_LOGIC),
]


def write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text.rstrip() + "\n")


def main() -> int:
    for folder, builder, logic in SCENARIOS:
        scenario = builder()
        spec_path = os.path.join(ROOT, folder, "make-scenario.json")
        with open(spec_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(scenario, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        logic_path = os.path.join(ROOT, folder, "make-logic.js")
        write_text(logic_path, logic)
        print(f"wrote {spec_path} ({len(scenario['scenario']['steps'])} steps)")
        print(f"wrote {logic_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
