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
