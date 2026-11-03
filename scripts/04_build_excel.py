"""
04_build_excel.py
-----------------
Builds excel/Financial_Analysis_Workbook.xlsx — a formula-driven analysis
workbook. Every analysis figure is a live SUMIFS formula on the Data sheet, so
changing the selected year on the Inputs sheet updates the whole workbook.

Run:  python scripts/04_build_excel.py   (then recalc with LibreOffice/Excel)
"""
from pathlib import Path
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "excel" / "Financial_Analysis_Workbook.xlsx"

summary = pd.read_csv(CLEAN / "monthly_summary.csv", parse_dates=["month_start"])
acc = pd.read_csv(CLEAN / "dim_account.csv")
dept = pd.read_csv(CLEAN / "dim_department.csv")
dq = pd.read_csv(CLEAN / "data_quality_log.csv")

# ------------------------------------------------------------------ styles
F = "Arial"
NAVY = "1F3864"
title_font = Font(name=F, size=16, bold=True, color=NAVY)
sub_font = Font(name=F, size=10, italic=True, color="595959")
hdr_font = Font(name=F, size=10, bold=True, color="FFFFFF")
hdr_fill = PatternFill("solid", fgColor=NAVY)
bold = Font(name=F, size=10, bold=True)
body = Font(name=F, size=10)
blue = Font(name=F, size=10, color="0000FF", bold=True)
green = Font(name=F, size=10, color="008000")
total_fill = PatternFill("solid", fgColor="D9E1F2")
input_fill = PatternFill("solid", fgColor="FFFF00")
thin = Side(style="thin", color="BFBFBF")
top_border = Border(top=Side(style="thin", color="000000"))
NUM = '#,##0;(#,##0);"-"'
PCT = '0.0%;(0.0%);"-"'
good_fill = PatternFill("solid", fgColor="C6EFCE")
bad_fill = PatternFill("solid", fgColor="FFC7CE")

wb = Workbook()

def header_row(ws, row, labels, col=1):
    for i, h in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=h)
        c.font, c.fill = hdr_font, hdr_fill
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 30

def title(ws, text, subtitle):
    ws["A1"] = text
    ws["A1"].font = title_font
    ws["A2"] = subtitle
    ws["A2"].font = sub_font
    ws.sheet_view.showGridLines = False

def widths(ws, w):
    for i, x in enumerate(w, 1):
        ws.column_dimensions[get_column_letter(i)].width = x

def style_body(ws, r1, r2, c1, c2, fmt=None):
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            cell = ws.cell(row=r, column=c)
            if cell.font == Font():
                cell.font = body
            if fmt and c > 1 and isinstance(cell.value, (int, float, str)) and str(cell.value).startswith("="):
                cell.number_format = fmt

# ================================================================== Data sheet
data = wb.active
data.title = "Data"
cols = ["Month", "Year", "Quarter", "Account ID", "Account", "Account Type", "Category",
        "Department", "Division", "Actual (ETB)", "Budget (ETB)"]
header_row(data, 1, cols)
d = summary.copy()
d["quarter"] = "Q" + d["month_start"].dt.quarter.astype(str)
d["year"] = d["month_start"].dt.year
for r, row in enumerate(d.itertuples(index=False), start=2):
    vals = [row.month_start.to_pydatetime(), row.year, row.quarter, row.account_id, row.account_name,
            row.account_type, row.account_category, row.department_name, row.division,
            round(row.actual_amount, 2), round(row.budget_amount, 2)]
    for c, v in enumerate(vals, 1):
        cell = data.cell(row=r, column=c, value=v)
        cell.font = body
    data.cell(row=r, column=1).number_format = "mmm-yyyy"
    data.cell(row=r, column=10).number_format = NUM
    data.cell(row=r, column=11).number_format = NUM
N = len(d) + 1
data.freeze_panes = "A2"
data.auto_filter.ref = f"A1:K{N}"
widths(data, [11, 7, 8, 10, 24, 12, 20, 13, 12, 15, 15])
data["M1"] = "Source: data/clean/monthly_summary.csv (output of scripts/02_clean_data.py)"
data["M1"].font = sub_font

R = lambda col: f"Data!${col}$2:${col}${N}"     # absolute data ranges
MONTH, YEAR, ACCT, TYPE, CAT, DEPT, ACT, BUD = (R("A"), R("B"), R("E"), R("F"), R("G"),
                                                R("H"), R("J"), R("K"))

# ================================================================== Inputs
inp = wb.create_sheet("Inputs", 0)
title(inp, "Inputs & Assumptions", "Blue/yellow cells are the only cells to edit. Everything else is formula-driven.")
inp["B4"], inp["C4"] = "Analysis year", 2025
inp["B5"], inp["C5"] = "Comparison (prior) year", "=C4-1"
inp["B6"], inp["C6"] = "Variance alert threshold (±)", 0.10
inp["B7"], inp["C7"] = "Currency", "ETB (Ethiopian Birr)"
for r in (4, 6):
    inp[f"C{r}"].font, inp[f"C{r}"].fill = blue, input_fill
inp["C5"].font = inp["C7"].font = body
inp["C6"].number_format = "0%"
inp["C4"].comment = Comment("Choose 2024 or 2025 — all analysis sheets update.", "Analyst")
inp["C6"].comment = Comment("Assumption: accounts with variance beyond ±10% of budget are flagged for review.", "Analyst")
dv = DataValidation(type="list", formula1='"2024,2025"', allow_blank=False)
inp.add_data_validation(dv)
dv.add("C4")
for r in range(4, 8):
    inp[f"B{r}"].font = bold
inp["B10"] = "Colour legend"
inp["B10"].font = bold
legend = [("Blue text on yellow", "Input you can change", blue, input_fill),
          ("Black text", "Formula", body, None),
          ("Green text", "Link to another sheet", green, None)]
for i, (a, b, f, fill) in enumerate(legend, start=11):
    inp[f"B{i}"], inp[f"C{i}"] = a, b
    inp[f"B{i}"].font = f
    if fill:
        inp[f"B{i}"].fill = fill
    inp[f"C{i}"].font = body
inp["B15"] = "Variance sign convention"
inp["B15"].font = bold
inp["B16"] = "Positive = favourable. Revenue: Actual − Budget. Costs: Budget − Actual."
inp["B16"].font = body
widths(inp, [3, 30, 26])
YR, PY, THR = "Inputs!$C$4", "Inputs!$C$5", "Inputs!$C$6"

# ================================================================== Income statement
pl = wb.create_sheet("Income_Statement")
title(pl, "Income Statement — Actual vs Budget vs Prior Year", "ETB. Driven by Inputs!C4 (analysis year).")
pl["A3"] = "Analysis year:"
pl["B3"] = f"={YR}"
pl["B3"].font = green
header_row(pl, 5, ["Line item", "Actual", "Budget", "Variance", "Var %", "Prior Year", "YoY %"])

def sumifs(rng, *crit):
    parts = ",".join(f"{a},{b}" for a, b in crit)
    return f"SUMIFS({rng},{parts})"

r = 6
lines = []   # (label, row, kind)
for typ, label in [("Revenue", "Revenue"), ("COGS", "Cost of Goods Sold"), ("Expense", "Operating Expenses")]:
    pl.cell(row=r, column=1, value=label).font = bold
    r += 1
    first = r
    for a in acc[acc.account_type == typ].itertuples():
        pl.cell(row=r, column=1, value=f"   {a.account_name}")
        pl.cell(row=r, column=2, value="=" + sumifs(ACT, (ACCT, f'"{a.account_name}"'), (YEAR, YR)))
        pl.cell(row=r, column=3, value="=" + sumifs(BUD, (ACCT, f'"{a.account_name}"'), (YEAR, YR)))
        pl.cell(row=r, column=6, value="=" + sumifs(ACT, (ACCT, f'"{a.account_name}"'), (YEAR, PY)))
        r += 1
    last = r - 1
    pl.cell(row=r, column=1, value=f"Total {label}").font = bold
    for c in (2, 3, 6):
        L = get_column_letter(c)
        pl.cell(row=r, column=c, value=f"=SUM({L}{first}:{L}{last})").font = bold
    for c in range(1, 8):
        pl.cell(row=r, column=c).fill = total_fill
        pl.cell(row=r, column=c).border = top_border
    lines.append((typ, first, last, r))
    r += 2

rev_t, cogs_t, opex_t = lines[0][3], lines[1][3], lines[2][3]
gp_row, np_row = r, r + 1
pl.cell(row=gp_row, column=1, value="GROSS PROFIT").font = bold
pl.cell(row=np_row, column=1, value="NET OPERATING PROFIT").font = bold
for c in (2, 3, 6):
    L = get_column_letter(c)
    pl.cell(row=gp_row, column=c, value=f"={L}{rev_t}-{L}{cogs_t}").font = bold
    pl.cell(row=np_row, column=c, value=f"={L}{gp_row}-{L}{opex_t}").font = bold
for rr in (gp_row, np_row):
    for c in range(1, 8):
        pl.cell(row=rr, column=c).fill = total_fill

# variance columns. Revenue / profit rows: actual-budget ; cost rows: budget-actual
for typ, first, last, tot in lines:
    for rr in list(range(first, last + 1)) + [tot]:
        if typ == "Revenue":
            pl.cell(row=rr, column=4, value=f"=B{rr}-C{rr}")
        else:
            pl.cell(row=rr, column=4, value=f"=C{rr}-B{rr}")
        pl.cell(row=rr, column=5, value=f"=IFERROR(D{rr}/C{rr},0)")
        pl.cell(row=rr, column=7, value=f"=IFERROR(B{rr}/F{rr}-1,0)")
for rr in (gp_row, np_row):
    pl.cell(row=rr, column=4, value=f"=B{rr}-C{rr}")
    pl.cell(row=rr, column=5, value=f"=IFERROR(D{rr}/C{rr},0)")
    pl.cell(row=rr, column=7, value=f"=IFERROR(B{rr}/F{rr}-1,0)")

m0 = np_row + 2
pl.cell(row=m0, column=1, value="Key ratios").font = bold
ratios = [("Gross margin %", f"={{c}}{gp_row}/{{c}}{rev_t}"),
          ("Net operating margin %", f"={{c}}{np_row}/{{c}}{rev_t}"),
          ("Operating expense ratio %", f"={{c}}{opex_t}/{{c}}{rev_t}"),
          ("COGS ratio %", f"={{c}}{cogs_t}/{{c}}{rev_t}")]
for i, (lab, f) in enumerate(ratios, start=m0 + 1):
    pl.cell(row=i, column=1, value=f"   {lab}")
    for c in (2, 3, 6):
        L = get_column_letter(c)
        pl.cell(row=i, column=c, value="=IFERROR(" + f.format(c=L)[1:] + ",0)").number_format = PCT
for rr in range(6, np_row + 1):
    for c in range(1, 8):
        cell = pl.cell(row=rr, column=c)
        if cell.font == Font():
            cell.font = body
        if c in (2, 3, 4, 6):
            cell.number_format = NUM
        if c in (5, 7):
            cell.number_format = PCT
for rr in range(m0 + 1, m0 + 5):
    for c in range(1, 8):
        if pl.cell(row=rr, column=c).font == Font():
            pl.cell(row=rr, column=c).font = body
pl.conditional_formatting.add(f"D6:D{np_row}", CellIsRule(operator="lessThan", formula=["0"], font=Font(color="C00000")))
pl.freeze_panes = "B6"
widths(pl, [34, 15, 15, 14, 9, 15, 9])
PL_REV, PL_GP, PL_NP, PL_OPEX = rev_t, gp_row, np_row, opex_t

# ================================================================== Monthly P&L
mp = wb.create_sheet("Monthly_PnL")
title(mp, "Monthly P&L Trend — Actual vs Budget", "ETB, all 24 months. YTD resets each January.")
heads = ["Month", "Year", "Revenue", "COGS", "Gross Profit", "OpEx", "Net Profit", "Net Margin %",
         "Budget Revenue", "Budget Net Profit", "NP Variance", "YTD Actual NP", "YTD Budget NP", "Revenue MoM %"]
header_row(mp, 4, heads)
months = sorted(d["month_start"].unique())
for i, m in enumerate(months):
    rr = 5 + i
    mp.cell(row=rr, column=1, value=pd.Timestamp(m).to_pydatetime()).number_format = "mmm-yyyy"
    mp.cell(row=rr, column=2, value=f"=YEAR(A{rr})")
    mp.cell(row=rr, column=3, value="=" + sumifs(ACT, (MONTH, f"$A{rr}"), (TYPE, '"Revenue"')))
    mp.cell(row=rr, column=4, value="=" + sumifs(ACT, (MONTH, f"$A{rr}"), (TYPE, '"COGS"')))
    mp.cell(row=rr, column=5, value=f"=C{rr}-D{rr}")
    mp.cell(row=rr, column=6, value="=" + sumifs(ACT, (MONTH, f"$A{rr}"), (TYPE, '"Expense"')))
    mp.cell(row=rr, column=7, value=f"=E{rr}-F{rr}")
    mp.cell(row=rr, column=8, value=f"=IFERROR(G{rr}/C{rr},0)")
    mp.cell(row=rr, column=9, value="=" + sumifs(BUD, (MONTH, f"$A{rr}"), (TYPE, '"Revenue"')))
    mp.cell(row=rr, column=10, value=f"=I{rr}-" + sumifs(BUD, (MONTH, f"$A{rr}"), (TYPE, '"<>Revenue"')))
    mp.cell(row=rr, column=11, value=f"=G{rr}-J{rr}")
    mp.cell(row=rr, column=12, value=f"=SUMIFS($G$5:G{rr},$B$5:B{rr},B{rr})")
    mp.cell(row=rr, column=13, value=f"=SUMIFS($J$5:J{rr},$B$5:B{rr},B{rr})")
    mp.cell(row=rr, column=14, value="" if i == 0 else f"=IFERROR(C{rr}/C{rr-1}-1,0)")
    for c in range(1, 15):
        cell = mp.cell(row=rr, column=c)
        cell.font = body
        if c in (3, 4, 5, 6, 7, 9, 10, 11, 12, 13):
            cell.number_format = NUM
        if c in (8, 14):
            cell.number_format = PCT
MP_LAST = 5 + len(months) - 1
mp.conditional_formatting.add(f"K5:K{MP_LAST}", CellIsRule(operator="lessThan", formula=["0"], fill=bad_fill))
mp.conditional_formatting.add(f"K5:K{MP_LAST}", CellIsRule(operator="greaterThanOrEqual", formula=["0"], fill=good_fill))
mp.freeze_panes = "B5"
widths(mp, [11, 7, 14, 14, 14, 14, 14, 10, 14, 14, 13, 14, 14, 10])

# ================================================================== Budget vs Actual
bva = wb.create_sheet("Budget_vs_Actual")
title(bva, "Budget vs Actual Variance by Account", "Year from Inputs!C4. Positive variance = favourable. Flag = beyond threshold in Inputs!C6.")
bva["A3"], bva["B3"] = "Analysis year:", f"={YR}"
bva["B3"].font = green
header_row(bva, 5, ["Account", "Type", "Actual", "Budget", "Variance", "Var %", "Status", "Review flag"])
order = acc.sort_values(["account_type", "account_id"], key=lambda s: s.map({"Revenue": 0, "COGS": 1, "Expense": 2}) if s.name == "account_type" else s)
for i, a in enumerate(order.itertuples()):
    rr = 6 + i
    bva.cell(row=rr, column=1, value=a.account_name)
    bva.cell(row=rr, column=2, value=a.account_type)
    bva.cell(row=rr, column=3, value="=" + sumifs(ACT, (ACCT, f"$A{rr}"), (YEAR, YR)))
    bva.cell(row=rr, column=4, value="=" + sumifs(BUD, (ACCT, f"$A{rr}"), (YEAR, YR)))
    bva.cell(row=rr, column=5, value=f'=IF(B{rr}="Revenue",C{rr}-D{rr},D{rr}-C{rr})')
    bva.cell(row=rr, column=6, value=f"=IFERROR(E{rr}/D{rr},0)")
    bva.cell(row=rr, column=7, value=f'=IF(E{rr}>=0,"Favourable","Unfavourable")')
    bva.cell(row=rr, column=8, value=f'=IF(ABS(F{rr})>{THR},"REVIEW","")')
    for c in range(1, 9):
        cell = bva.cell(row=rr, column=c)
        cell.font = body
        if c in (3, 4, 5):
            cell.number_format = NUM
        if c == 6:
            cell.number_format = PCT
BVA_LAST = 6 + len(order) - 1
bva.conditional_formatting.add(f"G6:G{BVA_LAST}", FormulaRule(formula=[f'$G6="Unfavourable"'], fill=bad_fill))
bva.conditional_formatting.add(f"G6:G{BVA_LAST}", FormulaRule(formula=[f'$G6="Favourable"'], fill=good_fill))
bva.conditional_formatting.add(f"H6:H{BVA_LAST}", FormulaRule(formula=[f'$H6="REVIEW"'], font=Font(bold=True, color="C00000")))
tr = BVA_LAST + 2
bva.cell(row=tr, column=1, value="Accounts flagged for review").font = bold
bva.cell(row=tr, column=3, value=f'=COUNTIF(H6:H{BVA_LAST},"REVIEW")').font = bold
bva.cell(row=tr + 1, column=1, value="Unfavourable accounts").font = bold
bva.cell(row=tr + 1, column=3, value=f'=COUNTIF(G6:G{BVA_LAST},"Unfavourable")').font = bold
bva.freeze_panes = "B6"
widths(bva, [26, 10, 15, 15, 14, 9, 14, 12])

# ================================================================== Expense analysis
ex = wb.create_sheet("Expense_Analysis")
title(ex, "Cost Structure & Expense Trends", "COGS + operating expenses. Year from Inputs!C4; YoY vs Inputs!C5.")
header_row(ex, 4, ["Category", "Account", "Spend (Year)", "% of Total Costs", "Prior Year", "YoY Change", "YoY %", "% of Revenue"])
costs = acc[acc.account_type != "Revenue"].sort_values(["account_category", "account_name"])
for i, a in enumerate(costs.itertuples()):
    rr = 5 + i
    ex.cell(row=rr, column=1, value=a.account_category)
    ex.cell(row=rr, column=2, value=a.account_name)
    ex.cell(row=rr, column=3, value="=" + sumifs(ACT, (ACCT, f"$B{rr}"), (YEAR, YR)))
    ex.cell(row=rr, column=5, value="=" + sumifs(ACT, (ACCT, f"$B{rr}"), (YEAR, PY)))
    ex.cell(row=rr, column=6, value=f"=C{rr}-E{rr}")
    ex.cell(row=rr, column=7, value=f"=IFERROR(F{rr}/E{rr},0)")
EX_LAST = 5 + len(costs) - 1
EX_TOT = EX_LAST + 1
for i in range(5, EX_LAST + 1):
    ex.cell(row=i, column=4, value=f"=IFERROR(C{i}/$C${EX_TOT},0)")
    ex.cell(row=i, column=8, value=f"=IFERROR(C{i}/Income_Statement!$B${PL_REV},0)").font = green
ex.cell(row=EX_TOT, column=1, value="TOTAL COSTS").font = bold
for c, f in [(3, f"=SUM(C5:C{EX_LAST})"), (4, f"=SUM(D5:D{EX_LAST})"), (5, f"=SUM(E5:E{EX_LAST})"),
             (6, f"=C{EX_TOT}-E{EX_TOT}"), (7, f"=IFERROR(F{EX_TOT}/E{EX_TOT},0)"),
             (8, f"=IFERROR(C{EX_TOT}/Income_Statement!$B${PL_REV},0)")]:
    ex.cell(row=EX_TOT, column=c, value=f).font = bold
for rr in range(5, EX_TOT + 1):
    for c in range(1, 9):
        cell = ex.cell(row=rr, column=c)
        if cell.font == Font():
            cell.font = body
        if c in (3, 5, 6):
            cell.number_format = NUM
        if c in (4, 7, 8):
            cell.number_format = PCT
        if rr == EX_TOT:
            cell.fill, cell.border = total_fill, top_border
ex.conditional_formatting.add(f"G5:G{EX_LAST}", CellIsRule(operator="greaterThan", formula=["0.15"], fill=bad_fill))

# category summary
cs = EX_TOT + 3
ex.cell(row=cs - 1, column=1, value="Spend by category").font = bold
header_row(ex, cs, ["Category", "Spend (Year)", "% of Total Costs"])
cats = sorted(costs.account_category.unique())
for i, cat in enumerate(cats):
    rr = cs + 1 + i
    ex.cell(row=rr, column=1, value=cat).font = body
    ex.cell(row=rr, column=2, value=f"=SUMIFS($C$5:$C${EX_LAST},$A$5:$A${EX_LAST},A{rr})").number_format = NUM
    ex.cell(row=rr, column=3, value=f"=IFERROR(B{rr}/$C${EX_TOT},0)").number_format = PCT
    ex.cell(row=rr, column=2).font = body
    ex.cell(row=rr, column=3).font = body
CAT_FIRST, CAT_LAST = cs + 1, cs + len(cats)
widths(ex, [22, 26, 15, 13, 15, 14, 9, 12])

# ================================================================== Department analysis
dp = wb.create_sheet("Department_Analysis")
title(dp, "Department Cost Performance vs Budget", "Costs only (COGS + OpEx). Year from Inputs!C4.")
header_row(dp, 4, ["Department", "Division", "Actual Spend", "Budget", "Variance", "Var %", "Status"])
for i, dd in enumerate(dept.itertuples()):
    rr = 5 + i
    dp.cell(row=rr, column=1, value=dd.department_name)
    dp.cell(row=rr, column=2, value=dd.division)
    dp.cell(row=rr, column=3, value=f"=" + sumifs(ACT, (DEPT, f"$A{rr}"), (YEAR, YR), (TYPE, '"<>Revenue"')))
    dp.cell(row=rr, column=4, value=f"=" + sumifs(BUD, (DEPT, f"$A{rr}"), (YEAR, YR), (TYPE, '"<>Revenue"')))
    dp.cell(row=rr, column=5, value=f"=D{rr}-C{rr}")
    dp.cell(row=rr, column=6, value=f"=IFERROR(E{rr}/D{rr},0)")
    dp.cell(row=rr, column=7, value=f'=IF(D{rr}=0,"No budget",IF(E{rr}>=0,"Within budget","Over budget"))')
    for c in range(1, 8):
        cell = dp.cell(row=rr, column=c)
        cell.font = body
        if c in (3, 4, 5):
            cell.number_format = NUM
        if c == 6:
            cell.number_format = PCT
DP_LAST = 5 + len(dept) - 1
dp.cell(row=DP_LAST + 1, column=1, value="TOTAL").font = bold
for c in (3, 4, 5):
    L = get_column_letter(c)
    cell = dp.cell(row=DP_LAST + 1, column=c, value=f"=SUM({L}5:{L}{DP_LAST})")
    cell.font, cell.number_format = bold, NUM
for c in range(1, 8):
    dp.cell(row=DP_LAST + 1, column=c).fill = total_fill
dp.conditional_formatting.add(f"G5:G{DP_LAST}", FormulaRule(formula=['$G5="Over budget"'], fill=bad_fill))
dp.conditional_formatting.add(f"G5:G{DP_LAST}", FormulaRule(formula=['$G5="Within budget"'], fill=good_fill))
dp.cell(row=DP_LAST + 3, column=1,
        value="Note: 'Unassigned' holds transactions with no department in the source system (see Data_Quality_Log).").font = sub_font
widths(dp, [16, 13, 15, 15, 14, 9, 14])

# ================================================================== KPI dashboard
k = wb.create_sheet("KPI_Dashboard", 1)
title(k, "Financial KPI Dashboard", "Headline KPIs for the year selected in Inputs!C4 (ETB).")
k["A3"], k["B3"] = "Year:", f"={YR}"
k["B3"].font = green
header_row(k, 5, ["KPI", "Actual", "Budget", "Variance", "Prior Year", "YoY %"])
IS = "Income_Statement!"
kpis = [
    ("Total Revenue", f"={IS}B{PL_REV}", f"={IS}C{PL_REV}", f"={IS}F{PL_REV}", NUM),
    ("Gross Profit", f"={IS}B{PL_GP}", f"={IS}C{PL_GP}", f"={IS}F{PL_GP}", NUM),
    ("Operating Expenses", f"={IS}B{PL_OPEX}", f"={IS}C{PL_OPEX}", f"={IS}F{PL_OPEX}", NUM),
    ("Net Operating Profit", f"={IS}B{PL_NP}", f"={IS}C{PL_NP}", f"={IS}F{PL_NP}", NUM),
    ("Gross Margin %", f"=IFERROR({IS}B{PL_GP}/{IS}B{PL_REV},0)", f"=IFERROR({IS}C{PL_GP}/{IS}C{PL_REV},0)",
     f"=IFERROR({IS}F{PL_GP}/{IS}F{PL_REV},0)", PCT),
    ("Net Margin %", f"=IFERROR({IS}B{PL_NP}/{IS}B{PL_REV},0)", f"=IFERROR({IS}C{PL_NP}/{IS}C{PL_REV},0)",
     f"=IFERROR({IS}F{PL_NP}/{IS}F{PL_REV},0)", PCT),
    ("OpEx Ratio %", f"=IFERROR({IS}B{PL_OPEX}/{IS}B{PL_REV},0)", f"=IFERROR({IS}C{PL_OPEX}/{IS}C{PL_REV},0)",
     f"=IFERROR({IS}F{PL_OPEX}/{IS}F{PL_REV},0)", PCT),
]
for i, (lab, a, b, p, fmt) in enumerate(kpis):
    rr = 6 + i
    k.cell(row=rr, column=1, value=lab).font = bold
    for c, v in ((2, a), (3, b), (5, p)):
        cell = k.cell(row=rr, column=c, value=v)
        cell.font, cell.number_format = green, fmt
    if lab in ("Operating Expenses", "OpEx Ratio %"):   # lower cost = favourable
        k.cell(row=rr, column=4, value=f"=C{rr}-B{rr}")
    else:
        k.cell(row=rr, column=4, value=f"=B{rr}-C{rr}")
    k.cell(row=rr, column=4).number_format = fmt
    k.cell(row=rr, column=4).font = body
    k.cell(row=rr, column=6, value=f"=IFERROR(B{rr}/E{rr}-1,0)" if fmt == NUM else f"=B{rr}-E{rr}")
    k.cell(row=rr, column=6).number_format = PCT
    k.cell(row=rr, column=6).font = body
k.conditional_formatting.add("D6:D12", CellIsRule(operator="lessThan", formula=["0"], fill=bad_fill))
k.conditional_formatting.add("D6:D12", CellIsRule(operator="greaterThanOrEqual", formula=["0"], fill=good_fill))
k["A14"] = "Margin rows show variance and YoY in percentage points. Variance positive = favourable."
k["A14"].font = sub_font
k["A15"], k["B15"] = "Accounts flagged for review:", f"=Budget_vs_Actual!C{tr}"
k["A15"].font, k["B15"].font = bold, green
widths(k, [26, 16, 16, 15, 16, 10])

# charts
lc = LineChart()
lc.title = "Monthly Revenue: Actual vs Budget (ETB)"
lc.y_axis.title, lc.x_axis.title = "ETB", "Month"
lc.add_data(Reference(mp, min_col=3, min_row=4, max_row=MP_LAST), titles_from_data=True)
lc.add_data(Reference(mp, min_col=9, min_row=4, max_row=MP_LAST), titles_from_data=True)
lc.set_categories(Reference(mp, min_col=1, min_row=5, max_row=MP_LAST))
lc.x_axis.number_format = "mmm-yy"
lc.height, lc.width = 8, 18
k.add_chart(lc, "H3")

lc2 = LineChart()
lc2.title = "Monthly Net Profit: Actual vs Budget (ETB)"
lc2.add_data(Reference(mp, min_col=7, min_row=4, max_row=MP_LAST), titles_from_data=True)
lc2.add_data(Reference(mp, min_col=10, min_row=4, max_row=MP_LAST), titles_from_data=True)
lc2.set_categories(Reference(mp, min_col=1, min_row=5, max_row=MP_LAST))
lc2.x_axis.number_format = "mmm-yy"
lc2.height, lc2.width = 8, 18
k.add_chart(lc2, "H20")

bc = BarChart()
bc.type = "bar"
bc.title = "Cost Mix by Category (selected year)"
bc.add_data(Reference(ex, min_col=2, min_row=cs, max_row=CAT_LAST), titles_from_data=True)
bc.set_categories(Reference(ex, min_col=1, min_row=CAT_FIRST, max_row=CAT_LAST))
bc.legend = None
bc.height, bc.width = 8, 13
k.add_chart(bc, "A18")

# ================================================================== Data quality log
q = wb.create_sheet("Data_Quality_Log")
title(q, "Data Cleaning Log", "Produced by scripts/02_clean_data.py")
header_row(q, 4, ["Step", "Rows affected", "Detail"])
for i, row in enumerate(dq.itertuples(), start=5):
    q.cell(row=i, column=1, value=row.step).font = body
    q.cell(row=i, column=2, value=row.rows_affected).font = body
    q.cell(row=i, column=2).number_format = "#,##0"
    q.cell(row=i, column=3, value=row.detail).font = body
widths(q, [40, 14, 70])

# ================================================================== README sheet
rd = wb.create_sheet("README", 0)
title(rd, "Financial Performance, Budget Variance & Expense Analysis",
      "Abay Trading PLC (synthetic data) · FY2024–FY2025 · Currency: ETB")
guide = [
    ("Inputs", "Choose the analysis year and the variance alert threshold."),
    ("KPI_Dashboard", "Headline KPIs vs budget and prior year, with charts."),
    ("Income_Statement", "Full P&L by account: actual, budget, variance, prior year."),
    ("Monthly_PnL", "24-month trend, net profit vs budget, YTD running totals."),
    ("Budget_vs_Actual", "Variance by account with favourable/unfavourable status and review flags."),
    ("Expense_Analysis", "Cost structure, share of total, YoY growth, % of revenue."),
    ("Department_Analysis", "Department spend vs budget."),
    ("Data_Quality_Log", "Every cleaning step and the rows affected."),
    ("Data", "Clean monthly actual + budget by account and department (source for all formulas)."),
]
header_row(rd, 4, ["Sheet", "What it shows"])
for i, (a, b) in enumerate(guide, start=5):
    rd.cell(row=i, column=1, value=a).font = bold
    rd.cell(row=i, column=2, value=b).font = body
rd.cell(row=15, column=1, value="All analysis cells are formulas (SUMIFS on the Data sheet). Change Inputs!C4 to switch year.").font = sub_font
widths(rd, [24, 85])

wb.save(OUT)
print(f"Saved {OUT}")
