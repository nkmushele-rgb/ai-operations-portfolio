"""Build Application-Tracker.xlsx with the Python standard library only.

The workbook is deliberately simple: three sheets, header styling, frozen top
row, autofilter and a status dropdown. No formulas, so no dependency on Excel
recalculation and no third-party package to run the generator.

    python tools/build_tracker.py

Validate afterwards with openpyxl if it is available:

    python -c "import openpyxl; w=openpyxl.load_workbook('JOB-APPLICATIONS/Application-Tracker.xlsx'); print(w.sheetnames)"
"""

from __future__ import annotations

import os
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTPUT = os.path.join(ROOT, "JOB-APPLICATIONS", "Application-Tracker.xlsx")

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"


def col(n: int) -> str:
    """1 -> A, 27 -> AA."""
    letters = ""
    while n:
        n, remainder = divmod(n - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def cell(ref: str, value, style: int = 0) -> str:
    if value is None or value == "":
        return f'<c r="{ref}" s="{style}"/>'
    if isinstance(value, bool):
        value = "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'
    text = escape(str(value))
    space = ' xml:space="preserve"' if str(value) != str(value).strip() else ""
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t{space}>{text}</t></is></c>'


def sheet(headers: list[str], rows: list[list], widths: list[int],
          status_dropdown: bool = False) -> str:
    last = f"{col(len(headers))}{len(rows) + 1}"
    out = [f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           f'<worksheet xmlns="{MAIN}">',
           f'<dimension ref="A1:{last}"/>',
           '<sheetViews><sheetView workbookViewId="0">'
           '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
           '</sheetView></sheetViews>',
           '<sheetFormatPr defaultRowHeight="15"/>',
           '<cols>']
    for i, width in enumerate(widths, start=1):
        out.append(f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>')
    out.append('</cols><sheetData>')

    out.append(f'<row r="1" ht="22" customHeight="1">')
    for i, header in enumerate(headers, start=1):
        out.append(cell(f"{col(i)}1", header, style=1))
    out.append('</row>')

    for r, row in enumerate(rows, start=2):
        out.append(f'<row r="{r}">')
        for c, value in enumerate(row, start=1):
            out.append(cell(f"{col(c)}{r}", value))
        out.append('</row>')

    out.append('</sheetData>')
    out.append(f'<autoFilter ref="A1:{col(len(headers))}{max(1, len(rows) + 1)}"/>')
    if status_dropdown:
        choices = "Saved,Drafted,Applied,Screening,Interview,Offer,Rejected,Closed"
        out.append('<dataValidations count="1">'
                   '<dataValidation type="list" allowBlank="1" showErrorMessage="1" '
                   'errorTitle="Use the status list" error="Pick a status from the list." '
                   'sqref="H2:H500">'
                   f'<formula1>"{choices}"</formula1>'
                   '</dataValidation></dataValidations>')
    out.append('</worksheet>')
    return "".join(out)


def styles() -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<styleSheet xmlns="{MAIN}">'
        '<fonts count="2">'
        '<font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>'
        '</fonts>'
        '<fills count="3">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FF0F766E"/>'
        '<bgColor indexed="64"/></patternFill></fill>'
        '</fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" '
        'applyFont="1" applyFill="1" applyAlignment="1">'
        '<alignment vertical="center"/></xf>'
        '</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )


def workbook() -> str:
    names = ["Applications", "Target roles", "Guide"]
    sheets = "".join(
        f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>'
        for i, name in enumerate(names, start=1)
    )
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<workbook xmlns="{MAIN}" xmlns:r="{REL}">'
            f'<sheets>{sheets}</sheets></workbook>')


def workbook_rels() -> str:
    rels = []
    for i in (1, 2, 3):
        rels.append(
            f'<Relationship Id="rId{i}" '
            f'Type="{REL}/worksheet" Target="worksheets/sheet{i}.xml"/>'
        )
    rels.append(f'<Relationship Id="rId4" Type="{REL}/styles" Target="styles.xml"/>')
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{PKG}">{"".join(rels)}</Relationships>')


def root_rels() -> str:
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{PKG}">'
            f'<Relationship Id="rId1" Type="{REL}/officeDocument" Target="xl/workbook.xml"/>'
            f'<Relationship Id="rId2" Type="{REL}/metadata/core-properties" '
            f'Target="docProps/core.xml"/>'
            f'<Relationship Id="rId3" Type="{REL}/extended-properties" '
            f'Target="docProps/app.xml"/>'
            f'</Relationships>')


def content_types() -> str:
    overrides = [
        ("/xl/workbook.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"),
        ("/xl/styles.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"),
        ("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"),
        ("/docProps/app.xml", "application/vnd.openxmlformats-officedocument.extended-properties+xml"),
    ]
    overrides += [
        (f"/xl/worksheets/sheet{i}.xml",
         "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml")
        for i in (1, 2, 3)
    ]
    parts = "".join(f'<Override PartName="{p}" ContentType="{c}"/>' for p, c in overrides)
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Types xmlns="{CT}">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'{parts}</Types>')


def core_props() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/">'
            '<dc:title>Remote job application tracker</dc:title>'
            '<dc:creator>AI Operations Portfolio</dc:creator>'
            f'<dcterms:created xmlns:dcterms="http://purl.org/dc/terms/">{stamp}</dcterms:created>'
            '</cp:coreProperties>')


def app_props() -> str:
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties '
            'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            '<Application>build_tracker.py</Application></Properties>')


APPLICATION_HEADERS = [
    "Date applied", "Platform", "Company", "Role title", "Job URL", "Fit (/8)",
    "Cost (Connects/credits)", "Status", "Next action", "Follow-up date",
    "Evidence used", "Notes",
]

TARGET_HEADERS = [
    "Role family", "Fit (/5)", "Evidence to lead with", "Main gap", "Apply?",
    "Source", "Checked",
]

TARGET_ROWS = [
    ["AI operations assistant / workflow automation", 5, "Three projects, 90 tests, approval gates", "No paid client deployment", "Yes - first choice", "Portfolio / job-suitability.md", "2026-11-20"],
    ["Business process automation (no-code/low-code)", 4, "Make build specs, rule-based decisions", "No scenario built in a Make account", "Yes", "Portfolio / job-suitability.md", "2026-11-20"],
    ["Remote operations assistant - stock focus", 4, "Project 2 plus TRAGS stores experience", "No named ERP/WMS", "Yes", "Portfolio / job-suitability.md", "2026-11-20"],
    ["Sales operations / lead management", 4, "Project 3, route sales, account development", "No live CRM; HubSpot learning", "Yes - avoid HubSpot-hard roles", "Portfolio / job-suitability.md", "2026-11-20"],
    ["Support operations / support triage", 4, "Project 1, escalation and approval", "No live mailbox or ticket system", "Yes", "Portfolio / job-suitability.md", "2026-11-20"],
    ["Supply chain / purchasing coordinator", 3, "FMCG distribution, stores, Project 2", "No ERP/WMS; location limits", "Selective", "We Work Remotely / Remote OK", "2026-11-20"],
    ["AI data quality / evaluation tasks", 3, "Domain, Python, written tests", "Formal assignment, strict eligibility", "Second stage", "We Work Remotely", "2026-11-20"],
    ["General virtual assistant / admin", 2, "Excel, operations background", "Underuses portfolio; low rate", "Stopgap only", "Portfolio / job-suitability.md", "2026-11-20"],
    ["Data entry clerk", 1, "Accuracy", "Low rate, no speed evidence", "No", "We Work Remotely", "2026-11-20"],
    ["Senior AI / ML engineer", 1, "Local model used for prose", "No model training or production ML", "No", "Portfolio / job-suitability.md", "2026-11-20"],
]

GUIDE_HEADERS = ["Step", "Instruction"]
GUIDE_ROWS = [
    [1, "Score the advert with JOB-APPLICATIONS/job-suitability.md. Apply at 5 or above out of 8."],
    [2, "Write one tailored letter from application-letter-templates.md. Choose one project, not all three."],
    [3, "Confirm CV dates and portfolio URL before sending. Never claim a paying client."],
    [4, "Log the application on the Applications sheet the same day. Keep the job URL."],
    [5, "Set a follow-up date 5-7 working days later. Follow up once, then close it."],
    [6, "Status values: Saved, Drafted, Applied, Screening, Interview, Offer, Rejected, Closed."],
    [7, "Fit (/8): 1 point each for automation, code/data, operations domain, testing, portfolio accepted, time zone, minus 2 if a learning skill is required, minus 1 if an ERP/WMS is required."],
    [8, "If most rejections name the same gap, close that gap instead of sending more identical applications."],
    [9, "Use the Target roles sheet to pick the next role. Recheck market-research.md before applying; job adverts expire."],
]


def main() -> int:
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types())
        z.writestr("_rels/.rels", root_rels())
        z.writestr("docProps/core.xml", core_props())
        z.writestr("docProps/app.xml", app_props())
        z.writestr("xl/workbook.xml", workbook())
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels())
        z.writestr("xl/styles.xml", styles())
        z.writestr("xl/worksheets/sheet1.xml",
                   sheet(APPLICATION_HEADERS, [], [13, 12, 22, 30, 40, 9, 18, 13, 28, 14, 26, 38],
                         status_dropdown=True))
        z.writestr("xl/worksheets/sheet2.xml",
                   sheet(TARGET_HEADERS, TARGET_ROWS, [40, 9, 42, 34, 26, 30, 12]))
        z.writestr("xl/worksheets/sheet3.xml",
                   sheet(GUIDE_HEADERS, GUIDE_ROWS, [8, 120]))
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
