"""
Build two workbooks:
  1) RADS_Registry_Template.xlsx  — blank, upload-ready, with Legal/Ethics + Instructions.
  2) Redport_DE_example.xlsx       — filled for a large org + computed Results.

Org-level logic (NOT per-asset payment):
  * criticality tier gates the decision;
  * an asset is self-recoverable if backup coverage >= recovery threshold;
  * if ALL affected Critical & High assets are self-recoverable -> DO NOT PAY
    (low/medium-criticality loss is treated as within tolerance);
  * otherwise compare expected cost of paying vs not paying;
  * legality + criminal-funding clause is shown up front AND with the result.
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

ARIAL       = "Arial"
BLUE        = Font(name=ARIAL, color="0000FF", size=10)          # hardcoded inputs
BLACK       = Font(name=ARIAL, color="000000", size=10)          # formulas
BOLD        = Font(name=ARIAL, bold=True, size=10)
BOLDW       = Font(name=ARIAL, bold=True, size=10, color="FFFFFF")
TITLE       = Font(name=ARIAL, bold=True, size=14)
H2          = Font(name=ARIAL, bold=True, size=11)
WRAP        = Alignment(wrap_text=True, vertical="top")
CENTER      = Alignment(horizontal="center", vertical="center")
YELLOW      = PatternFill("solid", fgColor="FFF2CC")             # cells to fill in
HEADER_FILL = PatternFill("solid", fgColor="264653")
CRIT_FILL   = PatternFill("solid", fgColor="F4CCCC")
GREEN_FILL  = PatternFill("solid", fgColor="D9EAD3")
GREY_FILL   = PatternFill("solid", fgColor="EFEFEF")
thin = Side(style="thin", color="BBBBBB")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

LEGAL_LINES = [
    ("LEGAL NOTICE — READ BEFORE ACTING", "h"),
    ("This tool provides decision SUPPORT only. It is not legal advice, and its output is "
     "not a decision to pay. A ransom payment must never be made on the basis of this "
     "workbook alone.", "p"),
    ("1. Sanctions exposure. Paying a ransom can be unlawful. Under EU restrictive measures "
     "and U.S. OFAC regulations, transferring value to a sanctioned person, group, or "
     "region may carry civil or criminal liability — in some regimes on a strict-liability "
     "basis, regardless of intent or knowledge. The identity of a ransomware operator is "
     "usually unknown at decision time, so this risk cannot be ruled out.", "p"),
    ("2. Reporting duties. In Germany, incidents may trigger notification to the BSI (BSIG / "
     "KRITIS obligations), to law enforcement (LKA/BKA), and — where personal data is "
     "affected — to the competent data-protection authority within 72 hours under GDPR "
     "Art. 33. Financial entities additionally fall under DORA (Reg. (EU) 2022/2554) major-"
     "incident reporting. Verify current obligations for your sector.", "p"),
    ("3. No guarantee. Payment does not guarantee a working decryptor, full data recovery, "
     "or that exfiltrated data will not be leaked or resold. It may also mark the "
     "organisation as a payer and invite repeat targeting.", "p"),
    ("4. Funding of criminal activity. A ransom payment directly finances criminal "
     "enterprises and the wider ransomware ecosystem, potentially enabling further attacks "
     "on this and other organisations. This is an ethical and, in some jurisdictions, a "
     "legal consideration that sits outside the economic calculation below.", "p"),
    ("Before any payment: engage legal counsel, involve law enforcement, notify your cyber-"
     "insurer, and screen the counterparty against sanctions lists. Regulatory details may "
     "have changed since this template was written — confirm the current position.", "p"),
]

def style_col_widths(ws, widths):
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

def add_legal_sheet(wb):
    ws = wb.create_sheet("Legal_Ethics")
    ws.sheet_properties.tabColor = "C00000"
    ws["A1"] = "RADS — Legal & Ethical Framework"; ws["A1"].font = TITLE
    r = 3
    for text, kind in LEGAL_LINES:
        c = ws.cell(row=r, column=1, value=text)
        c.alignment = WRAP
        c.font = H2 if kind == "h" else BLACK
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
        ws.row_dimensions[r].height = 18 if kind == "h" else 58
        r += 1
    style_col_widths(ws, {"A": 14, **{get_column_letter(i): 14 for i in range(2, 9)}})
    return ws

def add_instructions(wb):
    ws = wb.create_sheet("Instructions")
    ws["A1"] = "How to use this workbook"; ws["A1"].font = TITLE
    steps = [
        "1. Read the Legal_Ethics sheet first. It also reprints with every result.",
        "2. Fill the yellow cells on Org_Info (organisation and incident parameters).",
        "3. List every AFFECTED application on the Assets sheet, one per row. Fill the yellow "
        "columns only; the grey columns compute themselves.",
        "4. Set Criticality from the dropdown (Critical / High / Medium / Low) and Backup "
        "Coverage as a percentage (share of that asset's data restorable from backup).",
        "5. Open the Results sheet. It returns ONE organisation-level recommendation, driven "
        "by whether the Critical and High assets can be self-recovered. Low/Medium-criticality "
        "loss is treated as within tolerance.",
        "6. The recommendation is decision SUPPORT, never authorisation. Follow the legal steps.",
    ]
    r = 3
    for s in steps:
        c = ws.cell(row=r, column=1, value=s); c.alignment = WRAP; c.font = BLACK
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
        ws.row_dimensions[r].height = 44; r += 1
    ws.cell(row=r+1, column=1, value="Legend:").font = BOLD
    lg = ws.cell(row=r+2, column=1,
                 value="Yellow = you fill in.   Grey = computed, do not edit.")
    lg.font = BLACK; lg.fill = YELLOW
    style_col_widths(ws, {"A": 14, **{get_column_letter(i): 14 for i in range(2, 9)}})
    return ws

# ---- Org_Info sheet. Returns dict of cell addresses for cross-refs.
ORG_ROWS = [
    ("Organisation Name",                 "text",  None),
    ("Assessment Date",                   "text",  None),
    ("Total Applications (org-wide)",     "int",   None),
    ("Current Ransom Demand (kEUR)",      "num",   None),
    ("Ransom Doubling Period (days)",     "int",   None),
    ("Payment Deadline (days)",           "int",   None),
    ("Recovery Threshold (backup cov.)",  "pct",   "Asset is 'self-recoverable' at or above this backup coverage"),
    ("P(decryptor works if paid)",        "pct",   None),
    ("P(re-extortion after paying)",      "pct",   None),
    ("Re-extortion Cost (kEUR)",          "num",   None),
    ("P(data leaked even if paid)",       "pct",   None),
    ("P(data leaked if NOT paid)",        "pct",   None),
    ("Aggregate Leak Damage (kEUR)",      "num",   None),
    ("Prior-incident handling",           "text",  "None / Insufficient / Sufficient (reference effect)"),
    ("Criticality weight — Critical",     "num2",  "How heavily each tier's loss counts in the decision"),
    ("Criticality weight — High",         "num2",  None),
    ("Criticality weight — Medium",       "num2",  None),
    ("Criticality weight — Low",          "num2",  None),
]
def add_org_info(wb, values=None):
    ws = wb.create_sheet("Org_Info")
    ws["A1"] = "Organisation & Incident Parameters"; ws["A1"].font = TITLE
    ws["A2"] = "Fill the yellow cells."; ws["A2"].font = BLACK
    addr = {}
    r = 4
    for label, kind, note in ORG_ROWS:
        ws.cell(row=r, column=1, value=label).font = BOLD
        c = ws.cell(row=r, column=2); c.font = BLUE; c.fill = YELLOW; c.border = BORDER
        if kind == "pct":  c.number_format = "0%"
        elif kind == "num": c.number_format = "#,##0"
        elif kind == "num2": c.number_format = "0.00"
        elif kind == "int": c.number_format = "#,##0"
        if values and label in values:
            c.value = values[label]
        if note:
            n = ws.cell(row=r, column=3, value=note); n.font = Font(name=ARIAL, italic=True, size=9, color="777777")
        addr[label] = f"Org_Info!$B${r}"
        r += 1
    style_col_widths(ws, {"A": 34, "B": 16, "C": 52})
    return ws, addr

# ---- Assets sheet
ASSET_HEADERS = ["Application / Asset", "Criticality", "Affected?", "Backup Coverage",
                 "Data Value (kEUR)", "Downtime Cost (kEUR/day)", "Self-Recovery Time (days)",
                 "Crit. Weight", "Self-Recoverable?", "Exp. Recovery Loss (kEUR)",
                 "Full Loss if Unrecovered (kEUR)", "Weighted No-Pay Loss (kEUR)"]
def add_assets(wb, org_addr, rows=None, example_row=False):
    ws = wb.create_sheet("Assets")
    ws["A1"] = "Affected Applications / Assets"; ws["A1"].font = TITLE
    ws["A2"] = "Fill yellow columns (A–G). Grey columns (H–L) compute automatically."; ws["A2"].font = BLACK
    hr = 4
    for j, h in enumerate(ASSET_HEADERS, start=1):
        c = ws.cell(row=hr, column=j, value=h); c.font = BOLDW; c.fill = HEADER_FILL
        c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center"); c.border = BORDER
    ws.row_dimensions[hr].height = 40
    thr  = org_addr["Recovery Threshold (backup cov.)"]
    wC   = org_addr["Criticality weight — Critical"]
    wH   = org_addr["Criticality weight — High"]
    wM   = org_addr["Criticality weight — Medium"]
    wL   = org_addr["Criticality weight — Low"]

    def write_row(r, data=None):
        # inputs A-G
        for col in range(1, 8):
            c = ws.cell(row=r, column=col); c.border = BORDER
            c.font = BLUE; c.fill = YELLOW
            if col == 4: c.number_format = "0%"
            if col in (5, 6): c.number_format = "#,##0"
        if data:
            ws.cell(row=r, column=1, value=data["name"])
            ws.cell(row=r, column=2, value=data["tier"])
            ws.cell(row=r, column=3, value=data["affected"])
            ws.cell(row=r, column=4, value=data["cov"])
            ws.cell(row=r, column=5, value=data["value"])
            ws.cell(row=r, column=6, value=data["down"])
            ws.cell(row=r, column=7, value=data["rtime"])
        # H: criticality weight (continuous, from tier -> configurable weights)
        h = ws.cell(row=r, column=8,
                    value=(f'=IF($B{r}="Critical",{wC},IF($B{r}="High",{wH},'
                           f'IF($B{r}="Medium",{wM},IF($B{r}="Low",{wL},0))))'))
        h.font = BLACK; h.border = BORDER; h.alignment = CENTER; h.number_format = "0.00"
        # I: self-recoverable (from backups)
        i = ws.cell(row=r, column=9,
                    value=f'=IF(AND($C{r}="Yes",$D{r}>={thr}),"Yes","No")')
        i.font = BLACK; i.border = BORDER; i.alignment = CENTER
        # J: expected recovery loss (downtime + unrecovered fraction of data)
        j = ws.cell(row=r, column=10,
                    value=f'=IF($C{r}="Yes",$F{r}*$G{r}+(1-$D{r})*$E{r},0)')
        j.font = BLACK; j.border = BORDER; j.number_format = "#,##0"
        # K: full loss if unrecovered (all data + downtime)
        k = ws.cell(row=r, column=11,
                    value=f'=IF($C{r}="Yes",$E{r}+$F{r}*$G{r},0)')
        k.font = BLACK; k.border = BORDER; k.number_format = "#,##0"
        # L: criticality-weighted no-pay loss = weight * (recoverable ? recovery loss : full loss)
        l = ws.cell(row=r, column=12,
                    value=f'=IF($C{r}="Yes",$H{r}*IF($I{r}="Yes",$J{r},$K{r}),0)')
        l.font = BLACK; l.border = BORDER; l.number_format = "#,##0"

    start = hr + 1
    if rows:
        for k, d in enumerate(rows):
            write_row(start + k, d)
        end = start + len(rows) - 1
    else:
        # template: example row + blank rows
        if example_row:
            write_row(start, {"name": "e.g. SAP S/4HANA (ERP core)", "tier": "Critical",
                              "affected": "Yes", "cov": 0.9, "value": 4000, "down": 180, "rtime": 4})
            ws.cell(row=start, column=1).comment = None
        for k in range(1, 60):
            write_row(start + k)
        end = start + 59

    # dropdowns
    dv_tier = DataValidation(type="list",
                             formula1='"Critical,High,Medium,Low"', allow_blank=True)
    dv_yes  = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True)
    ws.add_data_validation(dv_tier); ws.add_data_validation(dv_yes)
    dv_tier.add(f"B{start}:B{end}"); dv_yes.add(f"C{start}:C{end}")
    style_col_widths(ws, {"A": 34, "B": 12, "C": 11, "D": 14, "E": 15, "F": 18,
                          "G": 17, "H": 11, "I": 15, "J": 18, "K": 20, "L": 20})
    return ws, (start, end)

# ---- Results sheet
def add_results(wb, org_addr, asset_range):
    ws = wb.create_sheet("Results")
    a0, a1 = asset_range
    ws["A1"] = "RADS — Organisation-Level Recommendation"; ws["A1"].font = TITLE
    # reprint short legal banner
    ws.merge_cells("A2:H3")
    b = ws["A2"]; b.value = ("DECISION SUPPORT ONLY — NOT LEGAL ADVICE AND NOT AUTHORISATION TO PAY. "
                             "A payment can breach EU/OFAC sanctions and funds criminal activity. "
                             "See the Legal_Ethics sheet and involve counsel + law enforcement before acting.")
    b.font = Font(name=ARIAL, bold=True, size=10, color="9C0006"); b.alignment = WRAP
    b.fill = PatternFill("solid", fgColor="FDE9E9")

    def kv(r, label, formula, fmt=None, bold=False, note=None):
        ws.cell(row=r, column=1, value=label).font = BOLD if bold else BLACK
        c = ws.cell(row=r, column=3, value=formula)
        c.font = BOLD if bold else BLACK
        if fmt: c.number_format = fmt
        if note:
            ws.cell(row=r, column=5, value=note).font = Font(name=ARIAL, italic=True, size=9, color="777777")
        return c

    thr = org_addr["Recovery Threshold (backup cov.)"]
    ransom = org_addr["Current Ransom Demand (kEUR)"]
    pkey = org_addr["P(decryptor works if paid)"]
    pre = org_addr["P(re-extortion after paying)"]
    cre = org_addr["Re-extortion Cost (kEUR)"]
    pleak_p = org_addr["P(data leaked even if paid)"]
    dleak = org_addr["Aggregate Leak Damage (kEUR)"]

    C = f"Assets!$C${a0}:$C${a1}"   # affected
    B = f"Assets!$B${a0}:$B${a1}"   # tier
    I = f"Assets!$I${a0}:$I${a1}"   # recoverable?
    L = f"Assets!$L${a0}:$L${a1}"   # criticality-weighted no-pay loss

    r = 5
    ws.cell(row=r, column=1, value="Portfolio summary").font = H2; r += 1
    kv(r, "Affected — Critical",  f'=COUNTIFS({C},"Yes",{B},"Critical")', "#,##0"); r += 1
    kv(r, "Affected — High",      f'=COUNTIFS({C},"Yes",{B},"High")', "#,##0"); r += 1
    kv(r, "Affected — Medium",    f'=COUNTIFS({C},"Yes",{B},"Medium")', "#,##0"); r += 1
    kv(r, "Affected — Low",       f'=COUNTIFS({C},"Yes",{B},"Low")', "#,##0"); r += 1
    # criticality-weighted exposure of assets that CANNOT be self-recovered (continuous, all tiers)
    row_strand = r
    kv(r, "Criticality-weighted stranded exposure (kEUR)",
       f'=SUMIFS({L},{I},"No",{C},"Yes")', "#,##0", bold=True,
       note="unrecoverable loss, each asset scaled by its criticality weight (all tiers count)"); r += 1

    r += 1
    ws.cell(row=r, column=1, value="Economic comparison — criticality-weighted (expected, kEUR)").font = H2; r += 1
    # Weighted cost of NOT paying = sum of per-asset weighted no-pay loss
    cost_nopay = f'SUM({L})'
    row_nopay = r
    kv(r, "Weighted cost if NOT paying", f'={cost_nopay}', "#,##0"); r += 1
    # Weighted cost of paying = ransom + (1-pkey)*weighted_nopay + pre*cre + pleak_p*dleak
    row_pay = r
    cost_pay = (f'{ransom}+(1-{pkey})*({cost_nopay})+{pre}*{cre}+{pleak_p}*{dleak}')
    kv(r, "Weighted cost if paying", f'={cost_pay}', "#,##0"); r += 1
    row_save = r
    kv(r, "Weighted saving from paying", f'=$C${row_nopay}-$C${row_pay}', "#,##0",
       note="positive = paying is cheaper once losses are criticality-weighted (before legal/ethical factors)"); r += 1

    r += 1
    ws.cell(row=r, column=1, value="RECOMMENDATION").font = H2; r += 1
    # Continuous logic: recommendation follows the criticality-weighted comparison.
    rec = (f'=IF($C${row_save}>0,'
           f'"CONSIDER PAYMENT \u2014 subject to mandatory legal & sanctions review",'
           f'"DO NOT PAY \u2014 self-recovery is cheaper on a criticality-weighted basis")')
    rc = ws.cell(row=r, column=1, value=rec)
    ws.merge_cells(start_row=r, start_column=1, end_row=r+1, end_column=8)
    rc.font = Font(name=ARIAL, bold=True, size=12); rc.alignment = WRAP
    rc.fill = GREEN_FILL; r += 3

    # driver line — explains the weighting, no on/off gate
    drv = (f'="Decision is driven by a criticality-weighted comparison: each asset\'s loss counts in "'
           f'&"proportion to its weight (Critical..Low), so high-value systems dominate and "'
           f'&"low/medium losses count but do not swamp the result. Weighted stranded exposure = "'
           f'&TEXT($C${row_strand},"#,##0")&" kEUR."')
    d = ws.cell(row=r, column=1, value=drv); ws.merge_cells(start_row=r, start_column=1, end_row=r+1, end_column=8)
    d.font = BLACK; d.alignment = WRAP; r += 3

    note = ws.cell(row=r, column=1, value=("Reminder: a 'CONSIDER PAYMENT' result is an economic signal only. "
                   "It does not resolve sanctions, reporting, or the ethical cost of funding crime — "
                   "resolve those before any payment."))
    ws.merge_cells(start_row=r, start_column=1, end_row=r+1, end_column=8)
    note.font = Font(name=ARIAL, italic=True, size=9, color="777777"); note.alignment = WRAP

    style_col_widths(ws, {"A": 40, "B": 4, "C": 18, "D": 3, "E": 40, **{get_column_letter(i): 10 for i in range(6, 9)}})
    return ws

def build(path, org_values=None, asset_rows=None, template=False):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    add_legal_sheet(wb)
    add_instructions(wb)
    _, org_addr = add_org_info(wb, org_values)
    _, arange = add_assets(wb, org_addr, rows=asset_rows, example_row=template)
    add_results(wb, org_addr, arange)
    wb.save(path)
    print("wrote", path)

# ------------------------------------------------------------------ Redport.DE data
REDPORT_ORG = {
    "Organisation Name": "Redport.DE (Redport Logistics GmbH)",
    "Assessment Date": "2026-09-11",
    "Total Applications (org-wide)": 240,
    "Current Ransom Demand (kEUR)": 7500,
    "Ransom Doubling Period (days)": 7,
    "Payment Deadline (days)": 28,
    "Recovery Threshold (backup cov.)": 0.5,
    "P(decryptor works if paid)": 0.65,
    "P(re-extortion after paying)": 0.25,
    "Re-extortion Cost (kEUR)": 3750,
    "P(data leaked even if paid)": 0.35,
    "P(data leaked if NOT paid)": 0.70,
    "Aggregate Leak Damage (kEUR)": 6000,
    "Prior-incident handling": "Insufficient",
    "Criticality weight — Critical": 1.0,
    "Criticality weight — High": 0.75,
    "Criticality weight — Medium": 0.5,
    "Criticality weight — Low": 0.25,
}
def A(name, tier, cov, value, down, rtime, affected="Yes"):
    return dict(name=name, tier=tier, affected=affected, cov=cov, value=value, down=down, rtime=rtime)

REDPORT_ASSETS = [
    # Critical (6) — mostly recoverable; Customs Gateway has a failed backup
    A("Port Operations Control System (SCADA)", "Critical", 0.90, 3200, 220, 3),
    A("Container Terminal Management System",   "Critical", 0.85, 2800, 180, 4),
    A("Customs Clearance Gateway (ATLAS)",      "Critical", 0.20, 2600, 160, 12),
    A("SAP S/4HANA (ERP core)",                 "Critical", 0.88, 4000, 200, 4),
    A("Vessel Berth Scheduling",                "Critical", 0.75, 1500, 140, 5),
    A("Gate Automation & OCR",                  "Critical", 0.80, 900,  90,  4),
    # High (10)
    A("Yard Management System",                 "High", 0.80, 800, 70, 4),
    A("Reefer (Cold-chain) Monitoring",         "High", 0.78, 700, 90, 3),
    A("EDI Integration Hub",                    "High", 0.82, 600, 60, 4),
    A("Billing & Invoicing",                    "High", 0.85, 900, 50, 5),
    A("Warehouse Management",                   "High", 0.76, 650, 55, 4),
    A("Fleet Telematics",                       "High", 0.70, 500, 45, 5),
    A("Identity / Active Directory",            "High", 0.90, 400, 120, 2),
    A("Email / Exchange",                       "High", 0.88, 350, 60, 3),
    A("Enterprise Data Warehouse",              "High", 0.72, 1200, 40, 6),
    A("Customer Portal",                        "High", 0.80, 550, 50, 4),
    # Medium (12)
    *[A(n, "Medium", cov, val, dn, rt) for n, cov, val, dn, rt in [
        ("HR Management (Workday)", 0.75, 300, 20, 4),
        ("Procurement Portal", 0.70, 260, 18, 4),
        ("Maintenance (CMMS)", 0.68, 240, 22, 5),
        ("Document Management", 0.80, 220, 12, 3),
        ("Training LMS", 0.72, 120, 8, 4),
        ("Facilities / BMS", 0.66, 180, 25, 5),
        ("Intranet / Wiki", 0.78, 90, 6, 3),
        ("Payroll", 0.82, 320, 30, 4),
        ("Expense Management", 0.74, 110, 8, 4),
        ("Contract Repository", 0.70, 200, 10, 5),
        ("BI Dashboards", 0.68, 150, 12, 5),
        ("Vendor Risk Portal", 0.72, 130, 9, 4),
    ]],
    # Low (24)
    *[A(f"{n}", "Low", 0.65, val, dn, rt) for n, val, dn, rt in [
        ("Marketing CMS", 60, 4, 3), ("Events App", 40, 3, 3), ("Cafeteria Ordering", 25, 2, 2),
        ("Visitor Sign-in", 30, 3, 2), ("Fleet Booking", 45, 4, 3), ("Meeting-room Booking", 20, 2, 2),
        ("Parking Management", 35, 3, 3), ("Survey Tool", 22, 2, 3), ("Digital Signage", 28, 3, 2),
        ("Photo Archive", 55, 2, 4), ("Newsletter Tool", 18, 1, 2), ("Idea Portal", 15, 1, 3),
        ("Sustainability Tracker", 40, 3, 4), ("Asset Label Printing", 24, 2, 3), ("Shift Swap App", 30, 3, 3),
        ("Lost & Found", 12, 1, 2), ("Bike-share", 16, 1, 2), ("Wellness App", 20, 2, 3),
        ("Feedback Kiosk", 14, 1, 2), ("Library System", 26, 2, 3), ("Charity Portal", 18, 1, 3),
        ("Press Clippings", 22, 2, 3), ("Room Sensors", 30, 3, 3), ("Guest Wi-Fi Portal", 35, 3, 2),
    ]],
]

TEMPLATE_DEFAULTS = {
    "Recovery Threshold (backup cov.)": 0.5,
    "P(decryptor works if paid)": 0.65,
    "P(re-extortion after paying)": 0.25,
    "P(data leaked even if paid)": 0.35,
    "P(data leaked if NOT paid)": 0.70,
    "Criticality weight — Critical": 1.0,
    "Criticality weight — High": 0.75,
    "Criticality weight — Medium": 0.5,
    "Criticality weight — Low": 0.25,
}

if __name__ == "__main__":
    build("/home/claude/RADS_Registry_Template.xlsx", org_values=TEMPLATE_DEFAULTS, template=True)
    build("/home/claude/Redport_DE_example.xlsx", org_values=REDPORT_ORG, asset_rows=REDPORT_ASSETS)
    print("affected assets in Redport example:", len(REDPORT_ASSETS))
