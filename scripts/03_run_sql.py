"""
03_run_sql.py
-------------
Loads the clean CSVs into a SQLite database (data/finance.db), runs every query
in sql/02_financial_reporting_queries.sql and saves each result to
reports/sql_outputs/Qnn_<title>.csv.

Run:  python scripts/03_run_sql.py
"""
from pathlib import Path
import re
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "reports" / "sql_outputs"
OUT.mkdir(parents=True, exist_ok=True)
DB = ROOT / "data" / "finance.db"

con = sqlite3.connect(DB)
con.executescript((ROOT / "sql" / "01_schema.sql").read_text())
for table in ["dim_account", "dim_department", "dim_date", "fact_actuals", "fact_budget"]:
    df = pd.read_csv(CLEAN / f"{table}.csv")
    df.to_sql(table, con, if_exists="append", index=False)
    print(f"loaded {table:<15} {len(df):>6,} rows")

sql = (ROOT / "sql" / "02_financial_reporting_queries.sql").read_text()
blocks = re.split(r"^-- \[(Q\d+)\] (.+)$", sql, flags=re.M)
# blocks = [header, id, title, body, id, title, body, ...]
for i in range(1, len(blocks), 3):
    qid, title, body = blocks[i], blocks[i + 1].strip(), blocks[i + 2]
    res = pd.read_sql_query(body, con)
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:50]
    res.to_csv(OUT / f"{qid}_{slug}.csv", index=False)
    print(f"\n[{qid}] {title}  ({len(res)} rows)")
    print(res.head(8).to_string(index=False))
con.close()
