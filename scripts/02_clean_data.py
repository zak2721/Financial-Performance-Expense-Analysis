"""
02_clean_data.py
----------------
Cleans the raw general-ledger and budget extracts and produces analysis-ready
tables for Excel, SQL and Power BI.

Outputs (data/clean/):
  fact_actuals.csv       one row per valid transaction
  fact_budget.csv        monthly budget by account and department
  dim_account.csv        chart of accounts
  dim_department.csv     departments
  dim_date.csv           monthly calendar (FY = calendar year)
  monthly_summary.csv    actual vs budget by month/account/department
  data_quality_log.csv   what was fixed and how many rows were affected

Run:  python scripts/02_clean_data.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)

log = []
def note(step, rows, detail):
    log.append({"step": step, "rows_affected": int(rows), "detail": detail})
    print(f"  - {step:<38} {rows:>5}  {detail}")

gl = pd.read_csv(RAW / "general_ledger_raw.csv", dtype=str)
budget = pd.read_csv(RAW / "budget_raw.csv")
acc = pd.read_csv(RAW / "chart_of_accounts.csv")
dept = pd.read_csv(RAW / "departments.csv")
start_rows = len(gl)
print(f"Raw GL rows: {start_rows:,}")

# 1. Trim whitespace in every text column
for c in gl.columns:
    gl[c] = gl[c].str.strip()

# 2. Remove exact duplicate rows
d = gl.duplicated().sum()
gl = gl.drop_duplicates()
note("Remove exact duplicates", d, "identical rows exported twice")

# 3. Remove test postings
mask = gl["Description"].str.contains("TEST POSTING", case=False, na=False)
note("Remove test postings", mask.sum(), "rows labelled TEST POSTING")
gl = gl[~mask]

# 4. Parse mixed date formats
def parse_date(s):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y"):
        try:
            return pd.to_datetime(s, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.NaT
non_iso = (~gl["PostingDate"].str.match(r"^\d{4}-\d{2}-\d{2}$")).sum()
gl["PostingDate"] = gl["PostingDate"].apply(parse_date)
note("Standardise date formats", non_iso, "DD/MM/YYYY, YYYY/MM/DD, DD-Mon-YYYY → ISO date")
bad_dates = gl["PostingDate"].isna().sum()
gl = gl[gl["PostingDate"].notna()]
note("Drop unparseable dates", bad_dates, "rows with invalid dates")

# 5. Convert text amounts to numbers ("1,250.00" and "(300.00)" = -300)
txt = gl["Amount"].str.contains(r"[,()]", na=False).sum()
def to_num(s):
    s = str(s).replace(",", "")
    neg = s.startswith("(") and s.endswith(")")
    v = float(s.strip("()"))
    return -v if neg else v
gl["Amount"] = gl["Amount"].apply(to_num)
note("Convert text amounts to numbers", txt, "removed thousand separators; (x) = negative")

# 6. Remove zero-value rows
z = (gl["Amount"] == 0).sum()
gl = gl[gl["Amount"] != 0]
note("Remove zero-amount rows", z, "no financial impact")

# 7. Standardise department names
valid = dict(zip(dept["department_name"].str.lower(), dept["department_name"]))
before = gl["Department"].copy()
gl["Department"] = gl["Department"].str.lower().map(valid)
fixed_case = ((before.notna()) & (before != gl["Department"])).sum()
note("Standardise department casing", fixed_case, "e.g. 'MARKETING', 'sales' → proper names")

# 8. Fill missing departments where the account belongs to only one department
gl["AccountCode"] = gl["AccountCode"].astype(int)
acct_dept = (gl.dropna(subset=["Department"])
               .groupby("AccountCode")["Department"].agg(lambda s: s.unique().tolist()))
single = {a: d[0] for a, d in acct_dept.items() if len(d) == 1}
miss = gl["Department"].isna()
filled = gl.loc[miss, "AccountCode"].map(single)
gl.loc[miss, "Department"] = filled
note("Infer missing department from account", filled.notna().sum(),
     "account is only ever booked by one department")
still = gl["Department"].isna().sum()
gl["Department"] = gl["Department"].fillna("Unassigned")
note("Flag remaining missing departments", still, "set to 'Unassigned' for review")

# 9. Missing counterparties
mc = gl["Counterparty"].isna().sum()
gl["Counterparty"] = gl["Counterparty"].fillna("Unknown")
note("Fill missing counterparties", mc, "set to 'Unknown'")

# 10. Enrich with account attributes, sign convention and period keys
gl = gl.merge(acc, left_on="AccountCode", right_on="account_id", how="left").drop(columns="account_id")
gl = gl.merge(dept, left_on="Department", right_on="department_name", how="left").drop(columns="department_name")
gl["department_id"] = gl["department_id"].fillna("D99")
gl["division"] = gl["division"].fillna("Unassigned")
gl["MonthStart"] = gl["PostingDate"].dt.to_period("M").dt.to_timestamp()
gl["Year"] = gl["PostingDate"].dt.year
gl["MonthNum"] = gl["PostingDate"].dt.month
gl["Quarter"] = "Q" + gl["PostingDate"].dt.quarter.astype(str)
# Signed amount for P&L: revenue positive, costs negative
gl["SignedAmount"] = np.where(gl["account_type"] == "Revenue", gl["Amount"], -gl["Amount"])

fact_actuals = gl.rename(columns={
    "TransactionID": "transaction_id", "PostingDate": "posting_date", "AccountCode": "account_id",
    "Department": "department_name", "Counterparty": "counterparty", "Amount": "amount",
    "Currency": "currency", "Description": "description", "MonthStart": "month_start",
    "Year": "year", "MonthNum": "month_num", "Quarter": "quarter", "SignedAmount": "signed_amount",
})[["transaction_id", "posting_date", "month_start", "year", "quarter", "month_num",
    "account_id", "account_name", "account_type", "account_category",
    "department_id", "department_name", "division", "counterparty",
    "amount", "signed_amount", "currency", "description"]].sort_values("posting_date")
fact_actuals["posting_date"] = fact_actuals["posting_date"].dt.date
fact_actuals["month_start"] = fact_actuals["month_start"].dt.date
fact_actuals.to_csv(CLEAN / "fact_actuals.csv", index=False)

# ------------------------------------------------------------------ budget
budget["month_start"] = pd.to_datetime(budget["Month"] + "-01").dt.date
fact_budget = (budget.merge(dept, left_on="Department", right_on="department_name")
                     .rename(columns={"AccountCode": "account_id", "BudgetAmount": "budget_amount"})
               [["month_start", "account_id", "department_id", "department_name", "budget_amount"]])
fact_budget.to_csv(CLEAN / "fact_budget.csv", index=False)

# ------------------------------------------------------------------ dimensions
acc.to_csv(CLEAN / "dim_account.csv", index=False)
dept_out = pd.concat([dept, pd.DataFrame([{"department_id": "D99", "department_name": "Unassigned",
                                           "division": "Unassigned"}])])
dept_out.to_csv(CLEAN / "dim_department.csv", index=False)

cal = pd.DataFrame({"month_start": pd.date_range("2024-01-01", "2025-12-01", freq="MS")})
cal["year"] = cal["month_start"].dt.year
cal["quarter"] = "Q" + cal["month_start"].dt.quarter.astype(str)
cal["year_quarter"] = cal["year"].astype(str) + "-" + cal["quarter"]
cal["month_num"] = cal["month_start"].dt.month
cal["month_name"] = cal["month_start"].dt.strftime("%b")
cal["year_month"] = cal["month_start"].dt.strftime("%Y-%m")
cal["month_start"] = cal["month_start"].dt.date
cal.to_csv(CLEAN / "dim_date.csv", index=False)

# ------------------------------------------------------------------ monthly actual vs budget
act_m = (fact_actuals.groupby(["month_start", "account_id", "department_id"], as_index=False)["amount"]
         .sum().rename(columns={"amount": "actual_amount"}))
summary = act_m.merge(fact_budget.drop(columns="department_name"),
                      on=["month_start", "account_id", "department_id"], how="outer").fillna(
                      {"actual_amount": 0, "budget_amount": 0})
summary = summary.merge(acc, on="account_id").merge(dept_out, on="department_id")
# variance sign: favourable = positive (revenue above budget OR cost below budget)
is_rev = summary["account_type"] == "Revenue"
summary["variance"] = np.where(is_rev, summary["actual_amount"] - summary["budget_amount"],
                               summary["budget_amount"] - summary["actual_amount"])
summary["variance_pct"] = np.where(summary["budget_amount"] != 0,
                                   summary["variance"] / summary["budget_amount"], np.nan).round(4)
summary["status"] = np.where(summary["variance"] >= 0, "Favourable", "Unfavourable")
summary = summary.sort_values(["month_start", "account_id", "department_id"])
summary.to_csv(CLEAN / "monthly_summary.csv", index=False)

note("FINAL clean transactions", len(fact_actuals), f"from {start_rows:,} raw rows")
pd.DataFrame(log).to_csv(CLEAN / "data_quality_log.csv", index=False)

# quick validation checks
assert fact_actuals["transaction_id"].is_unique, "duplicate transaction IDs remain"
assert fact_actuals["amount"].notna().all()
assert fact_actuals["account_name"].notna().all()
print("Validation checks passed.")
