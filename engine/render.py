"""One responsive HTML dashboard renderer shared by all three projects.

Writing the shell once keeps the three dashboards visually consistent and
means a reviewer learns the layout a single time.
"""

from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone

_CSS = """
*,*::before,*::after{box-sizing:border-box}
body{margin:0;background:#f4f6f8;color:#16202a;line-height:1.55;
 font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:__ACCENT__}
.hero{background:linear-gradient(135deg,#0b2b3c 0%,#123b4f 58%,__ACCENT__ 135%);color:#fff;padding:2.2rem 1.4rem 1.9rem}
.wrap{max-width:1180px;margin:0 auto}
.eyebrow{margin:0 0 .45rem;font-size:.72rem;letter-spacing:.15em;text-transform:uppercase;opacity:.75}
.hero h1{margin:0 0 .55rem;font-size:clamp(1.45rem,3.1vw,2.05rem);line-height:1.2}
.lede{margin:0;max-width:62ch;opacity:.92;font-size:.95rem}
.stamp{margin:.85rem 0 0;font-size:.75rem;opacity:.7}
main{max-width:1180px;margin:0 auto;padding:1.5rem 1.4rem 2.5rem}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.85rem;margin:0 0 1.5rem}
.stat{background:#fff;border:1px solid #e2e8ee;border-radius:12px;padding:.85rem 1rem}
.stat .k{margin:0;font-size:.7rem;letter-spacing:.09em;text-transform:uppercase;color:#5b6b7a}
.stat .v{margin:.22rem 0 0;font-size:1.45rem;font-weight:650;color:__ACCENT__}
.stat .h{margin:.18rem 0 0;font-size:.73rem;color:#7a8896}
.panel{background:#fff;border:1px solid #e2e8ee;border-radius:12px;padding:1rem 1.15rem 1.2rem;margin:0 0 1.2rem}
.panel h2{margin:0 0 .2rem;font-size:1rem}
.panel .desc{margin:0 0 .8rem;font-size:.83rem;color:#5b6b7a}
.tw{overflow-x:auto;border:1px solid #eef2f6;border-radius:9px}
table{border-collapse:collapse;width:100%;font-size:.83rem;min-width:520px}
th{background:#f7f9fb;text-align:left;padding:.5rem .65rem;border-bottom:1px solid #e6ecf2;
 font-size:.69rem;letter-spacing:.07em;text-transform:uppercase;color:#5b6b7a;white-space:nowrap}
td{padding:.45rem .65rem;border-bottom:1px solid #f1f5f8;vertical-align:top}
tbody tr:last-child td{border-bottom:none}
tbody tr:nth-child(even){background:#fcfdfe}
.muted{color:#9aa7b3}
.pill{display:inline-block;padding:.08rem .48rem;border-radius:999px;font-size:.71rem;
 font-weight:600;border:1px solid transparent;white-space:nowrap}
.pill-red{background:#fdeceb;color:#a52a1f;border-color:#f7cdc8}
.pill-amber{background:#fdf5e3;color:#8a5a06;border-color:#f4e2b8}
.pill-green{background:#e9f7ee;color:#1c6b3a;border-color:#c6e8d3}
.pill-blue{background:#eaf2fd;color:#1a4f8a;border-color:#c9ddf7}
.pill-grey{background:#f0f3f6;color:#4d5b68;border-color:#dfe6ec}
.empty{padding:.9rem;color:#7a8896;font-size:.83rem}
.notes{background:#fffdf5;border:1px solid #f0e4bf;border-radius:12px;padding:.95rem 1.15rem}
.notes h2{margin:0 0 .45rem;font-size:.93rem;color:#7a5a10}
.notes ul{margin:0;padding-left:1.05rem;font-size:.83rem;color:#5f5231}
.notes li+li{margin-top:.28rem}
footer{max-width:1180px;margin:0 auto;padding:0 1.4rem 2.2rem;font-size:.75rem;color:#7a8896}
.back{display:inline-block;margin:0 0 .9rem;font-size:.79rem;text-decoration:none}
@media(max-width:640px){.hero{padding:1.7rem 1rem 1.4rem}main{padding:1.1rem 1rem 2rem}}
@media print{body{background:#fff}.back{display:none}
 .hero{background:#0b2b3c!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""

_RED = {"complaint", "urgent", "high", "escalated", "rejected", "anomaly",
        "blocked", "negative", "lost", "critical"}
_AMBER = {"pending", "awaiting", "awaitingapproval", "medium", "review",
          "needsreview", "warning", "low", "draft", "watch"}
_GREEN = {"approved", "active", "ok", "sent", "normal", "positive", "won",
          "healthy", "resolved", "in stock", "instock"}
_BLUE = {"inquiry", "question", "new", "open", "queued", "contacted"}


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def _slug(value) -> str:
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _pill(value) -> str:
    slug = _slug(value)
    if slug in _RED:
        tone = "red"
    elif slug in _AMBER:
        tone = "amber"
    elif slug in _GREEN:
        tone = "green"
    elif slug in _BLUE:
        tone = "blue"
    else:
        tone = "grey"
    return f'<span class="pill pill-{tone}">{esc(value)}</span>'


def _cell(value, kind: str) -> str:
    if value is None or value == "":
        return '<span class="muted">&mdash;</span>'
    if kind == "tag":
        return _pill(value)
    if kind == "num":
        try:
            return f"{int(float(value)):,}"
        except (TypeError, ValueError):
            return esc(value)
    if kind == "money":
        try:
            return f"{float(value):,.2f}"
        except (TypeError, ValueError):
            return esc(value)
    return esc(value)


def _table(section: dict) -> str:
    columns = section.get("columns", [])
    rows = section.get("rows", [])
    head = "".join(f"<th>{esc(label)}</th>" for _, label, _ in columns)
    if not rows:
        body = f'<tr><td colspan="{max(len(columns), 1)}" class="empty">{esc(section.get("empty", "No rows."))}</td></tr>'
    else:
        cells = []
        for row in rows:
            tds = "".join(f"<td>{_cell(row.get(key), kind)}</td>" for key, _, kind in columns)
            cells.append(f"<tr>{tds}</tr>")
        body = "".join(cells)
    return (
        f'<div class="tw"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


def dashboard(*, title: str, subtitle: str, stats=(), sections=(), notes=(),
              accent: str = "#0f766e", eyebrow: str = "AI Operations Portfolio",
              footer: str = "", back_href: str = "", back_label: str = "Back to portfolio",
              generated: str | None = None) -> str:
    stamp = generated or datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    stat_cards = "".join(
        f'<div class="stat"><p class="k">{esc(s.get("label", ""))}</p>'
        f'<p class="v">{esc(s.get("value", ""))}</p>'
        f'<p class="h">{esc(s.get("hint", ""))}</p></div>'
        for s in stats
    )
    panels = "".join(
        f'<section class="panel"><h2>{esc(sec.get("title", ""))}</h2>'
        f'<p class="desc">{esc(sec.get("description", ""))}</p>{_table(sec)}</section>'
        for sec in sections
    )
    notes_html = ""
    if notes:
        items = "".join(f"<li>{esc(n)}</li>" for n in notes)
        notes_html = f'<section class="notes"><h2>Limitations and assumptions</h2><ul>{items}</ul></section>'
    back = f'<a class="back" href="{esc(back_href)}">&larr; {esc(back_label)}</a>' if back_href else ""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>{_CSS.replace("__ACCENT__", accent)}</style>
</head>
<body>
<header class="hero">
  <div class="wrap">
    {back}
    <p class="eyebrow">{esc(eyebrow)}</p>
    <h1>{esc(title)}</h1>
    <p class="lede">{esc(subtitle)}</p>
    <p class="stamp">Generated {esc(stamp)}</p>
  </div>
</header>
<main>
  <div class="stats">{stat_cards}</div>
  {panels}
  {notes_html}
</main>
<footer>{esc(footer)}</footer>
</body>
</html>
"""


def write_html(path: str, markup: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(markup)
    return path


def write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path
