"""Project 2: AI inventory management.

Stock is changed only through posted movements, so the balance can always be
rebuilt from history. Costing uses a moving average, which is the simplest
method that stays correct when purchase prices change.

Anomaly detection is rule based and explains itself in the alert text.
"""

from __future__ import annotations

import json
import os
import statistics
from datetime import datetime, timezone

from engine import db, validate

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "schema.sql")
DB_PATH = os.path.join(HERE, "data", "inventory.db")

MOVEMENT_SPEC = {
    "sku": {"required": True, "kind": "text", "min": 2, "max": 32},
    "kind": {"required": True, "kind": "choice", "choices": ["receipt", "issue", "adjustment"]},
    "qty": {"required": True, "kind": "money"},
}

ISSUE_ANOMALY_SHARE = 0.40   # one issue taking 40%+ of stock on hand
ISSUE_ANOMALY_MULTIPLE = 3.0  # 3x the usual issue size for that product
COST_ANOMALY_SHARE = 0.25     # purchase price 25% away from the moving average


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: str | None = None):
    con = db.connect(path or DB_PATH)
    with open(SCHEMA, encoding="utf-8") as handle:
        db.init(con, handle.read())
    return con


# ---------------------------------------------------------------- products

def add_product(con, sku: str, name: str, unit: str = "unit", category: str | None = None,
                reorder_level: float = 0, opening_qty: float = 0,
                opening_cost: float = 0) -> dict:
    existing = db.one(con, "SELECT sku FROM products WHERE sku = ?", (sku,))
    if existing:
        return {"sku": sku, "outcome": "exists"}
    db.insert(con, "products", {
        "sku": sku, "name": name, "unit": unit, "category": category,
        "reorder_level": float(reorder_level), "qty": 0.0, "avg_cost": 0.0,
        "updated_at": now(),
    })
    if opening_qty:
        receive(con, sku, opening_qty, opening_cost, reference="OPENING")
    return {"sku": sku, "outcome": "created"}


def get_product(con, sku: str) -> dict:
    product = db.one(con, "SELECT * FROM products WHERE sku = ?", (sku,))
    if not product:
        raise LookupError(f"unknown sku {sku}")
    return product


# ---------------------------------------------------------------- movements

def _key(kind: str, sku: str, qty: float, reference: str | None) -> str:
    return f"{kind}:{sku}:{qty}:{reference or ''}"


def _prior_issue_median(con, sku: str) -> float | None:
    sizes = [r["qty"] for r in db.rows(
        con, "SELECT qty FROM movements WHERE sku = ? AND kind = 'issue' ORDER BY id", (sku,))]
    if len(sizes) < 3:
        return None
    return statistics.median(sizes)


def _post(con, sku: str, kind: str, qty: float, unit_cost: float | None = None,
          reference: str | None = None, note: str | None = None,
          at: str | None = None, key: str | None = None) -> dict:
    product = get_product(con, sku)
    qty = round(float(qty), 3)
    if qty == 0:
        raise ValueError("quantity must not be zero")
    if kind in {"receipt", "issue"} and qty < 0:
        raise ValueError(f"{kind} quantity must be positive")
    if kind == "receipt" and (unit_cost is None or float(unit_cost) < 0):
        raise ValueError("receipt needs a unit cost of zero or more")

    idem = key or _key(kind, sku, qty, reference)
    if db.one(con, "SELECT id FROM movements WHERE idempotency_key = ?", (idem,)):
        return {"sku": sku, "outcome": "duplicate", "key": idem}

    before_qty = float(product["qty"])
    before_cost = float(product["avg_cost"])
    anomaly = None

    if kind == "issue":
        if qty > before_qty:
            raise ValueError(
                f"cannot issue {qty:g} {product['unit']} of {sku}; only {before_qty:g} on hand")
        if before_qty > 0 and qty / before_qty >= ISSUE_ANOMALY_SHARE:
            anomaly = f"single issue removed {qty / before_qty:.0%} of stock on hand"
        median = _prior_issue_median(con, sku)
        if median and qty > median * ISSUE_ANOMALY_MULTIPLE:
            anomaly = anomaly or f"issue is {qty / median:.1f}x the usual size ({median:g})"
        new_qty = before_qty - qty
        new_cost = before_cost
        value = round(qty * before_cost, 2)

    elif kind == "receipt":
        cost = round(float(unit_cost), 4)
        if before_cost > 0 and abs(cost - before_cost) / before_cost > COST_ANOMALY_SHARE:
            anomaly = f"purchase price {cost:g} is more than {COST_ANOMALY_SHARE:.0%} away from average {before_cost:g}"
        new_qty = before_qty + qty
        new_cost = round((before_qty * before_cost + qty * cost) / new_qty, 4)
        value = round(qty * cost, 2)

    else:  # adjustment, qty may be negative
        new_qty = before_qty + qty
        if new_qty < 0:
            raise ValueError(f"adjustment would leave {sku} at {new_qty:g}; stock cannot go negative")
        if qty < 0:
            anomaly = f"negative adjustment of {abs(qty):g} {product['unit']}"
        new_cost = before_cost
        value = round(qty * before_cost, 2)

    db.execute(con, "UPDATE products SET qty = ?, avg_cost = ?, updated_at = ? WHERE sku = ?",
               (round(new_qty, 3), new_cost, now(), sku))
    db.insert(con, "movements", {
        "sku": sku, "kind": kind, "qty": qty, "unit_cost": unit_cost,
        "value": value, "reference": reference, "note": note,
        "at": at or now(), "idempotency_key": idem,
    })

    alerts = _refresh_stock_alert(con, sku, new_qty, float(product["reorder_level"]))
    if anomaly:
        alerts.append(_raise_alert(con, sku, "anomaly", anomaly))

    return {"sku": sku, "outcome": "posted", "kind": kind, "qty": qty,
            "balance": round(new_qty, 3), "avg_cost": new_cost,
            "value": value, "anomaly": anomaly, "alerts": alerts}


def receive(con, sku, qty, unit_cost, reference=None, note=None, at=None, key=None) -> dict:
    return _post(con, sku, "receipt", qty, unit_cost, reference, note, at, key)


def issue(con, sku, qty, reference=None, note=None, at=None, key=None) -> dict:
    return _post(con, sku, "issue", qty, None, reference, note, at, key)


def adjust(con, sku, delta, reference=None, note=None, at=None, key=None) -> dict:
    return _post(con, sku, "adjustment", delta, None, reference, note, at, key)


# ---------------------------------------------------------------- alerts

def _raise_alert(con, sku: str, kind: str, message: str) -> dict:
    """Insert an alert unless the same open alert already exists."""
    cur = con.execute(
        "INSERT OR IGNORE INTO alerts (sku, kind, message, at) VALUES (?, ?, ?, ?)",
        (sku, kind, message, now()))
    con.commit()
    return {"sku": sku, "kind": kind, "message": message, "new": cur.rowcount == 1}


def _refresh_stock_alert(con, sku: str, qty: float, reorder_level: float) -> list[dict]:
    if qty <= 0:
        return [_raise_alert(con, sku, "out_of_stock", f"{sku} is out of stock")]
    if qty <= reorder_level:
        return [_raise_alert(con, sku, "low_stock",
                             f"{sku} at {qty:g}, at or below reorder level {reorder_level:g}")]
    # Stock recovered: close any open stock alert so the next dip raises a new one.
    db.execute(con, "UPDATE alerts SET acknowledged = 1 "
                    "WHERE sku = ? AND acknowledged = 0 AND kind IN ('low_stock', 'out_of_stock')",
               (sku,))
    return []


def acknowledge(con, alert_id: int) -> dict:
    db.execute(con, "UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
    return {"alert_id": alert_id, "acknowledged": True}


# ---------------------------------------------------------------- reporting

def valuation(con) -> dict:
    rows = db.rows(con, "SELECT sku, name, qty, avg_cost, ROUND(qty * avg_cost, 2) AS value "
                        "FROM products ORDER BY value DESC")
    total = round(sum(r["value"] or 0 for r in rows), 2)
    return {"total": total, "lines": rows}


def low_stock(con) -> list[dict]:
    return db.rows(con, """
        SELECT sku, name, qty, reorder_level, unit,
               ROUND(reorder_level - qty, 3) AS shortfall
        FROM products WHERE qty <= reorder_level ORDER BY shortfall DESC
    """)


def open_alerts(con) -> list[dict]:
    return db.rows(con, "SELECT id, sku, kind, message, at FROM alerts "
                        "WHERE acknowledged = 0 ORDER BY id DESC")


def report(con, start: str | None = None) -> dict:
    """Movement summary. ``start`` is an ISO date prefix, default today (UTC)."""
    day = start or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = db.rows(con, """
        SELECT kind, COUNT(*) AS n, ROUND(SUM(qty), 3) AS qty, ROUND(SUM(value), 2) AS value
        FROM movements WHERE substr(at, 1, 10) = ?
        GROUP BY kind
    """, (day,))
    totals = {r["kind"]: {"count": r["n"], "qty": r["qty"], "value": r["value"]} for r in rows}
    val = valuation(con)
    return {
        "day": day,
        "receipts": totals.get("receipt", {"count": 0, "qty": 0, "value": 0}),
        "issues": totals.get("issue", {"count": 0, "qty": 0, "value": 0}),
        "adjustments": totals.get("adjustment", {"count": 0, "qty": 0, "value": 0}),
        "stock_value": val["total"],
        "low_stock_count": len(low_stock(con)),
        "open_alerts": len(open_alerts(con)),
        "rejected": db.scalar(con, "SELECT COUNT(*) FROM rejected WHERE substr(at, 1, 10) = ?", (day,)),
    }


# ---------------------------------------------------------------- bulk input

def apply_file(con, path: str) -> dict:
    """Apply a JSONL batch of movements. One bad row never stops the batch."""
    results, errors = [], []
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except ValueError:
                errors.append(f"line {number}: invalid JSON")
                db.insert(con, "rejected", {"payload": line,
                                            "problems": f"line {number}: invalid JSON",
                                            "at": now()})
                continue

            problems = validate.validate(item, MOVEMENT_SPEC)
            if problems:
                message = "; ".join(f"{f} {m}" for f, m in problems)
                errors.append(f"line {number}: {message}")
                db.insert(con, "rejected", {"payload": line, "problems": message, "at": now()})
                continue

            try:
                results.append(_post(con, item["sku"], item["kind"], item["qty"],
                                     item.get("unit_cost"), item.get("reference"),
                                     item.get("note"), item.get("at"), item.get("key")))
            except (ValueError, LookupError) as exc:
                errors.append(f"line {number}: {exc}")
                db.insert(con, "rejected", {"payload": line, "problems": str(exc), "at": now()})
    return {"applied": results, "errors": errors}
