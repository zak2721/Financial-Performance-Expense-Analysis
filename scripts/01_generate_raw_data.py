"""
01_generate_raw_data.py
-----------------------
Generates a realistic (synthetic) general-ledger extract and budget file for a
mid-sized company ("Abay Trading PLC") covering FY2024–FY2025 (Jan 2024 – Dec 2025).

The raw files intentionally contain the data-quality problems you meet in real
finance extracts, so the cleaning step has real work to do:
  * mixed date formats            * amounts stored as text ("1,250.00", "(300.00)")
  * inconsistent category casing   * leading/trailing spaces
  * exact duplicate rows           * missing department / vendor values
  * a few zero-amount rows          * test transactions to exclude

Run:  python scripts/01_generate_raw_data.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

months = pd.period_range("2024-01", "2025-12", freq="M")

# ---------------------------------------------------------------- chart of accounts
accounts = pd.DataFrame([
    # id,  name,                     type,       category
    (4000, "Product Sales",          "Revenue",  "Revenue"),
    (4100, "Service Revenue",        "Revenue",  "Revenue"),
    (4200, "Subscription Revenue",   "Revenue",  "Revenue"),
    (5000, "Materials",              "COGS",     "Cost of Goods Sold"),
    (5100, "Direct Labor",           "COGS",     "Cost of Goods Sold"),
    (5200, "Freight & Logistics",    "COGS",     "Cost of Goods Sold"),
    (6000, "Salaries & Wages",       "Expense",  "Personnel"),
    (6100, "Employee Benefits",      "Expense",  "Personnel"),
    (6200, "Training & Development", "Expense",  "Personnel"),
    (6300, "Rent & Utilities",       "Expense",  "Facilities"),
    (6400, "Marketing & Advertising","Expense",  "Sales & Marketing"),
    (6500, "Travel & Entertainment", "Expense",  "Sales & Marketing"),
    (6600, "Software & IT Services", "Expense",  "Technology"),
    (6700, "Professional Fees",      "Expense",  "Administrative"),
    (6800, "Office Supplies",        "Expense",  "Administrative"),
    (6900, "Insurance",              "Expense",  "Administrative"),
    (7000, "Depreciation",           "Expense",  "Administrative"),
], columns=["account_id", "account_name", "account_type", "account_category"])

departments = pd.DataFrame([
    ("D10", "Sales",      "Commercial"),
    ("D20", "Marketing",  "Commercial"),
    ("D30", "Operations", "Operations"),
    ("D40", "IT",         "Support"),
    ("D50", "HR",         "Support"),
    ("D60", "Finance",    "Support"),
], columns=["department_id", "department_name", "division"])

# Which departments book to which accounts, with base monthly amount (ETB thousands → ETB)
# (account_id, department_id, base_monthly_amount, monthly_growth, noise_sd_pct)
plan = [
    (4000, "D10", 4_200_000, 0.012, 0.10),
    (4100, "D30", 1_350_000, 0.008, 0.12),
    (4200, "D10",   620_000, 0.030, 0.05),
    (5000, "D30", 1_780_000, 0.011, 0.08),
    (5100, "D30",   690_000, 0.006, 0.05),
    (5200, "D30",   260_000, 0.010, 0.15),
    (6000, "D10",   410_000, 0.004, 0.02),
    (6000, "D20",   220_000, 0.004, 0.02),
    (6000, "D30",   380_000, 0.004, 0.02),
    (6000, "D40",   260_000, 0.006, 0.02),
    (6000, "D50",   140_000, 0.003, 0.02),
    (6000, "D60",   190_000, 0.003, 0.02),
    (6100, "D50",   280_000, 0.004, 0.04),
    (6200, "D50",    55_000, 0.000, 0.35),
    (6300, "D30",   310_000, 0.002, 0.06),
    (6400, "D20",   330_000, 0.010, 0.18),
    (6500, "D10",    95_000, 0.006, 0.30),
    (6500, "D20",    40_000, 0.004, 0.30),
    (6600, "D40",   175_000, 0.022, 0.08),
    (6700, "D60",    85_000, 0.000, 0.25),
    (6800, "D60",    28_000, 0.000, 0.20),
    (6900, "D60",    60_000, 0.002, 0.02),
    (7000, "D60",   120_000, 0.001, 0.00),
]

vendors = {
    5000: ["Awash Raw Materials", "Habesha Supplies", "Rift Valley Inputs"],
    5200: ["Ethio Freight", "Djibouti Corridor Logistics"],
    6300: ["Bole Properties", "EEU Utilities"],
    6400: ["Addis Media Group", "Digital Reach Agency", "Meta Ads", "Google Ads"],
    6500: ["Ethiopian Airlines", "Skylight Hotel", "Hilton Addis"],
    6600: ["Microsoft", "Safaricom Business", "Ethio Telecom", "AWS"],
    6700: ["Tadesse & Partners Law", "KPMG Ethiopia", "Abebe Audit Services"],
    6800: ["Shoa Stationery", "Office Mart"],
    6900: ["Nyala Insurance", "Ethiopian Insurance Corp"],
    6200: ["Ethiopian Management Institute", "Coursera Business"],
}
customers = ["Retail Customer", "Wholesale Customer", "Government Contract", "NGO Client", "Corporate Client"]

# ------------------------------------------------------------------ business events
# The "story" hidden in the data that the analysis should uncover.
def event_multiplier(acct, dept, m: pd.Period):
    mult = 1.0
    # 1) Q4 seasonality for product sales
    if acct == 4000 and m.month in (11, 12):
        mult *= 1.18
    # 2) Revenue softness in Q3 2025 (lost a large wholesale account)
    if acct in (4000, 4100) and m.year == 2025 and m.month in (7, 8, 9):
        mult *= 0.84
    # 3) Marketing campaign overspend Apr–Jun 2025
    if acct == 6400 and m.year == 2025 and m.month in (4, 5, 6):
        mult *= 1.65
    # 4) One-off legal dispute fees in Oct 2024
    if acct == 6700 and m.year == 2024 and m.month == 10:
        mult *= 3.4
    # 5) Freight spike after fuel price increase from Mar 2025
    if acct == 5200 and (m.year == 2025 and m.month >= 3):
        mult *= 1.30
    # 6) Annual insurance renewal top-up in January
    if acct == 6900 and m.month == 1:
        mult *= 1.5
    return mult

# ------------------------------------------------------------------ actuals (transactions)
rows = []
txn = 100000
for mi, m in enumerate(months):
    for acct, dept, base, growth, sd in plan:
        target = base * (1 + growth) ** mi * event_multiplier(acct, dept, m)
        target *= max(0.6, rng.normal(1, sd))
        # split the monthly total into several transactions
        n = {4000: 14, 4100: 6, 4200: 8, 5000: 7}.get(acct, int(rng.integers(1, 4)))
        weights = rng.dirichlet(np.ones(n))
        for w in weights:
            day = int(rng.integers(1, m.days_in_month + 1))
            date = pd.Timestamp(year=m.year, month=m.month, day=day)
            amount = round(target * w, 2)
            if acct < 5000:
                party = rng.choice(customers)
            else:
                party = rng.choice(vendors.get(acct, ["Internal Payroll"]))
            txn += 1
            rows.append({
                "TransactionID": f"TXN{txn}",
                "PostingDate": date,
                "AccountCode": acct,
                "Department": departments.set_index("department_id").loc[dept, "department_name"],
                "Counterparty": party,
                "Amount": amount,
                "Currency": "ETB",
                "Description": f"{accounts.set_index('account_id').loc[acct, 'account_name']} - {m.strftime('%b %Y')}",
            })

gl = pd.DataFrame(rows)

# --------------------------------------------------------- inject data-quality problems
n = len(gl)
gl["PostingDate"] = gl["PostingDate"].astype(object)
idx = rng.choice(n, size=int(n * 0.35), replace=False)
for i in idx:  # mixed date formats
    d = gl.at[i, "PostingDate"]
    gl.at[i, "PostingDate"] = d.strftime(rng.choice(["%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y"]))
for i in set(range(n)) - set(idx):
    gl.at[i, "PostingDate"] = gl.at[i, "PostingDate"].strftime("%Y-%m-%d")

gl["Amount"] = gl["Amount"].astype(object)
for i in rng.choice(n, size=int(n * 0.25), replace=False):   # amounts as text with commas
    gl.at[i, "Amount"] = f"{float(gl.at[i, 'Amount']):,.2f}"

for i in rng.choice(n, size=int(n * 0.10), replace=False):   # messy department text
    gl.at[i, "Department"] = rng.choice([gl.at[i, "Department"].upper(),
                                         gl.at[i, "Department"].lower(),
                                         f"  {gl.at[i, 'Department']} "])

for i in rng.choice(n, size=45, replace=False):              # missing departments
    gl.at[i, "Department"] = np.nan
for i in rng.choice(n, size=30, replace=False):              # missing counterparties
    gl.at[i, "Counterparty"] = np.nan

dups = gl.sample(38, random_state=7)                          # exact duplicates
zeros = gl.sample(12, random_state=11).copy()                 # zero-value rows
zeros["Amount"] = 0
zeros["TransactionID"] = [f"TXN{900000+i}" for i in range(len(zeros))]
tests = gl.sample(6, random_state=3).copy()                   # test postings
tests["Description"] = "TEST POSTING - DO NOT USE"
tests["TransactionID"] = [f"TST{i:04d}" for i in range(len(tests))]

# reversal of an earlier posting (accounting credit shown in brackets)
rev = gl.sample(10, random_state=21).copy()
rev["TransactionID"] = [f"REV{i:04d}" for i in range(len(rev))]
rev["Amount"] = rev["Amount"].apply(lambda a: f"({float(str(a).replace(',', '')) * 0.1:,.2f})")
rev["Description"] = "Adjustment / partial reversal"

gl_raw = pd.concat([gl, dups, zeros, tests, rev]).sample(frac=1, random_state=1).reset_index(drop=True)
gl_raw.to_csv(RAW / "general_ledger_raw.csv", index=False)

# ------------------------------------------------------------------ budget
# Budget = what management planned at the start of each year (no knowledge of events).
brows = []
for mi, m in enumerate(months):
    year_start_index = 0 if m.year == 2024 else 12
    for acct, dept, base, growth, sd in plan:
        # budget assumes slightly more optimistic revenue and tighter costs
        plan_growth = growth * (1.15 if acct < 5000 else 0.90)
        b = base * (1 + plan_growth) ** mi
        if acct == 4000 and m.month in (11, 12):
            b *= 1.15
        if acct == 6900 and m.month == 1:
            b *= 1.5
        brows.append({
            "Month": m.strftime("%Y-%m"),
            "AccountCode": acct,
            "Department": departments.set_index("department_id").loc[dept, "department_name"],
            "BudgetAmount": round(b, -2),
        })
budget = pd.DataFrame(brows)
budget.to_csv(RAW / "budget_raw.csv", index=False)

accounts.to_csv(RAW / "chart_of_accounts.csv", index=False)
departments.to_csv(RAW / "departments.csv", index=False)

print(f"general_ledger_raw.csv : {len(gl_raw):,} rows")
print(f"budget_raw.csv         : {len(budget):,} rows")
print(f"chart_of_accounts.csv  : {len(accounts)} rows")
print(f"departments.csv        : {len(departments)} rows")
