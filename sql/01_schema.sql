-- =====================================================================
-- 01_schema.sql  |  Star schema for Financial Performance Analysis
-- Written for SQLite; runs on PostgreSQL / SQL Server with minor type changes
-- (TEXT → VARCHAR, REAL → DECIMAL(18,2), DATE stored as ISO text in SQLite).
-- =====================================================================

DROP TABLE IF EXISTS fact_actuals;
DROP TABLE IF EXISTS fact_budget;
DROP TABLE IF EXISTS dim_account;
DROP TABLE IF EXISTS dim_department;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_account (
    account_id        INTEGER PRIMARY KEY,
    account_name      TEXT NOT NULL,
    account_type      TEXT NOT NULL CHECK (account_type IN ('Revenue','COGS','Expense')),
    account_category  TEXT NOT NULL
);

CREATE TABLE dim_department (
    department_id     TEXT PRIMARY KEY,
    department_name   TEXT NOT NULL,
    division          TEXT NOT NULL
);

CREATE TABLE dim_date (
    month_start   DATE PRIMARY KEY,      -- first day of month, e.g. 2025-03-01
    year          INTEGER,
    quarter       TEXT,
    year_quarter  TEXT,
    month_num     INTEGER,
    month_name    TEXT,
    year_month    TEXT
);

CREATE TABLE fact_actuals (
    transaction_id    TEXT PRIMARY KEY,
    posting_date      DATE NOT NULL,
    month_start       DATE NOT NULL REFERENCES dim_date(month_start),
    year              INTEGER,
    quarter           TEXT,
    month_num         INTEGER,
    account_id        INTEGER NOT NULL REFERENCES dim_account(account_id),
    account_name      TEXT,
    account_type      TEXT,
    account_category  TEXT,
    department_id     TEXT REFERENCES dim_department(department_id),
    department_name   TEXT,
    division          TEXT,
    counterparty      TEXT,
    amount            REAL NOT NULL,     -- natural (unsigned) amount
    signed_amount     REAL NOT NULL,     -- revenue +, costs −  (P&L view)
    currency          TEXT,
    description       TEXT
);

CREATE TABLE fact_budget (
    month_start       DATE NOT NULL REFERENCES dim_date(month_start),
    account_id        INTEGER NOT NULL REFERENCES dim_account(account_id),
    department_id     TEXT NOT NULL REFERENCES dim_department(department_id),
    department_name   TEXT,
    budget_amount     REAL NOT NULL,
    PRIMARY KEY (month_start, account_id, department_id)
);

CREATE INDEX ix_act_month   ON fact_actuals (month_start);
CREATE INDEX ix_act_account ON fact_actuals (account_id);
CREATE INDEX ix_act_dept    ON fact_actuals (department_id);
