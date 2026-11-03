-- =====================================================================
-- 02_financial_reporting_queries.sql
-- Financial Performance, Budget Variance & Expense Analysis
-- Each query starts with a "-- [Qnn] Title" line (used by run_sql.py).
-- Skills shown: JOINs, CTEs, CASE, aggregation, window functions
-- (LAG, AVG OVER, SUM OVER, RANK), conditional aggregation.
-- Variance convention: positive = favourable
--   Revenue: actual − budget       Costs: budget − actual
-- =====================================================================


-- [Q01] Annual income statement with margins
WITH pl AS (
    SELECT year,
           SUM(CASE WHEN account_type = 'Revenue' THEN amount ELSE 0 END) AS revenue,
           SUM(CASE WHEN account_type = 'COGS'    THEN amount ELSE 0 END) AS cogs,
           SUM(CASE WHEN account_type = 'Expense' THEN amount ELSE 0 END) AS opex
    FROM fact_actuals
    GROUP BY year
)
SELECT year,
       ROUND(revenue, 0)                                   AS revenue,
       ROUND(cogs, 0)                                      AS cogs,
       ROUND(revenue - cogs, 0)                            AS gross_profit,
       ROUND(opex, 0)                                      AS operating_expenses,
       ROUND(revenue - cogs - opex, 0)                     AS net_profit,
       ROUND(100.0 * (revenue - cogs) / revenue, 1)        AS gross_margin_pct,
       ROUND(100.0 * (revenue - cogs - opex) / revenue, 1) AS net_margin_pct,
       ROUND(100.0 * opex / revenue, 1)                    AS opex_ratio_pct
FROM pl
ORDER BY year;


-- [Q02] Monthly P&L trend with month-over-month revenue growth
WITH m AS (
    SELECT month_start,
           SUM(CASE WHEN account_type = 'Revenue' THEN amount ELSE 0 END) AS revenue,
           SUM(CASE WHEN account_type <> 'Revenue' THEN amount ELSE 0 END) AS total_costs
    FROM fact_actuals
    GROUP BY month_start
)
SELECT month_start,
       ROUND(revenue, 0)               AS revenue,
       ROUND(total_costs, 0)           AS total_costs,
       ROUND(revenue - total_costs, 0) AS net_profit,
       ROUND(100.0 * (revenue - total_costs) / revenue, 1) AS net_margin_pct,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month_start))
                   / LAG(revenue) OVER (ORDER BY month_start), 1) AS revenue_mom_pct
FROM m
ORDER BY month_start;


-- [Q03] Budget vs actual by year and account type
WITH act AS (
    SELECT year, account_type, SUM(amount) AS actual
    FROM fact_actuals GROUP BY year, account_type
),
bud AS (
    SELECT CAST(strftime('%Y', b.month_start) AS INTEGER) AS year,
           a.account_type, SUM(b.budget_amount) AS budget
    FROM fact_budget b JOIN dim_account a ON a.account_id = b.account_id
    GROUP BY 1, 2
)
SELECT act.year, act.account_type,
       ROUND(actual, 0) AS actual,
       ROUND(budget, 0) AS budget,
       ROUND(CASE WHEN act.account_type = 'Revenue' THEN actual - budget
                  ELSE budget - actual END, 0) AS variance,
       ROUND(100.0 * CASE WHEN act.account_type = 'Revenue' THEN actual - budget
                          ELSE budget - actual END / budget, 1) AS variance_pct
FROM act JOIN bud ON bud.year = act.year AND bud.account_type = act.account_type
ORDER BY act.year, CASE act.account_type WHEN 'Revenue' THEN 1 WHEN 'COGS' THEN 2 ELSE 3 END;


-- [Q04] FY2025 budget variance by account, ranked by size of unfavourable variance
WITH act AS (
    SELECT account_id, SUM(amount) AS actual
    FROM fact_actuals WHERE year = 2025 GROUP BY account_id
),
bud AS (
    SELECT account_id, SUM(budget_amount) AS budget
    FROM fact_budget WHERE month_start BETWEEN '2025-01-01' AND '2025-12-31'
    GROUP BY account_id
),
v AS (
    SELECT a.account_name, a.account_type,
           act.actual, bud.budget,
           CASE WHEN a.account_type = 'Revenue' THEN act.actual - bud.budget
                ELSE bud.budget - act.actual END AS variance
    FROM dim_account a
    JOIN act ON act.account_id = a.account_id
    JOIN bud ON bud.account_id = a.account_id
)
SELECT RANK() OVER (ORDER BY variance) AS risk_rank,
       account_name, account_type,
       ROUND(actual, 0) AS actual, ROUND(budget, 0) AS budget,
       ROUND(variance, 0) AS variance,
       ROUND(100.0 * variance / budget, 1) AS variance_pct,
       CASE WHEN variance >= 0 THEN 'Favourable' ELSE 'Unfavourable' END AS status
FROM v
ORDER BY variance;


-- [Q05] Monthly net profit: actual vs budget, with running (YTD) totals
WITH act AS (
    SELECT month_start, SUM(signed_amount) AS actual_np
    FROM fact_actuals GROUP BY month_start
),
bud AS (
    SELECT b.month_start,
           SUM(CASE WHEN a.account_type = 'Revenue' THEN b.budget_amount ELSE -b.budget_amount END) AS budget_np
    FROM fact_budget b JOIN dim_account a ON a.account_id = b.account_id
    GROUP BY b.month_start
)
SELECT act.month_start,
       ROUND(actual_np, 0) AS actual_net_profit,
       ROUND(budget_np, 0) AS budget_net_profit,
       ROUND(actual_np - budget_np, 0) AS variance,
       ROUND(SUM(actual_np) OVER (PARTITION BY substr(act.month_start, 1, 4)
                                  ORDER BY act.month_start), 0) AS ytd_actual,
       ROUND(SUM(budget_np) OVER (PARTITION BY substr(act.month_start, 1, 4)
                                  ORDER BY act.month_start), 0) AS ytd_budget
FROM act JOIN bud ON bud.month_start = act.month_start
ORDER BY act.month_start;


-- [Q06] Operating-cost mix by category (COGS + OpEx) and share of total, FY2025
WITH c AS (
    SELECT account_category, account_name, SUM(amount) AS spend
    FROM fact_actuals
    WHERE year = 2025 AND account_type IN ('COGS', 'Expense')
    GROUP BY account_category, account_name
)
SELECT account_category, account_name,
       ROUND(spend, 0) AS spend,
       ROUND(100.0 * spend / SUM(spend) OVER (), 1) AS pct_of_total_costs,
       ROUND(100.0 * SUM(spend) OVER (ORDER BY spend DESC)
                   / SUM(spend) OVER (), 1) AS cumulative_pct
FROM c
ORDER BY spend DESC;


-- [Q07] Top 10 external vendors by spend, FY2025
SELECT counterparty AS vendor,
       account_name,
       COUNT(*)            AS invoices,
       ROUND(SUM(amount), 0) AS total_spend,
       ROUND(AVG(amount), 0) AS avg_invoice
FROM fact_actuals
WHERE year = 2025
  AND account_type IN ('COGS', 'Expense')
  AND counterparty NOT IN ('Internal Payroll', 'Unknown')
GROUP BY counterparty, account_name
ORDER BY total_spend DESC
LIMIT 10;


-- [Q08] Department cost performance vs budget, FY2025
WITH act AS (
    SELECT department_id, SUM(amount) AS actual
    FROM fact_actuals
    WHERE year = 2025 AND account_type IN ('COGS', 'Expense')
    GROUP BY department_id
),
bud AS (
    SELECT b.department_id, SUM(b.budget_amount) AS budget
    FROM fact_budget b JOIN dim_account a ON a.account_id = b.account_id
    WHERE b.month_start BETWEEN '2025-01-01' AND '2025-12-31'
      AND a.account_type IN ('COGS', 'Expense')
    GROUP BY b.department_id
)
SELECT d.department_name, d.division,
       ROUND(COALESCE(act.actual, 0), 0) AS actual_spend,
       ROUND(COALESCE(bud.budget, 0), 0) AS budget,
       ROUND(COALESCE(bud.budget, 0) - COALESCE(act.actual, 0), 0) AS variance,
       ROUND(100.0 * (COALESCE(bud.budget, 0) - COALESCE(act.actual, 0))
                   / NULLIF(bud.budget, 0), 1) AS variance_pct
FROM dim_department d
LEFT JOIN act ON act.department_id = d.department_id
LEFT JOIN bud ON bud.department_id = d.department_id
WHERE COALESCE(act.actual, 0) + COALESCE(bud.budget, 0) > 0
ORDER BY variance;


-- [Q09] Expense anomalies: months > 40% above the account's trailing 3-month average
WITH m AS (
    SELECT account_name, month_start, SUM(amount) AS spend
    FROM fact_actuals
    WHERE account_type IN ('COGS', 'Expense')
    GROUP BY account_name, month_start
),
w AS (
    SELECT *, AVG(spend) OVER (PARTITION BY account_name ORDER BY month_start
                               ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING) AS trailing_3m_avg,
              COUNT(*)   OVER (PARTITION BY account_name ORDER BY month_start
                               ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING) AS n_prior
    FROM m
)
SELECT account_name, month_start,
       ROUND(spend, 0) AS spend,
       ROUND(trailing_3m_avg, 0) AS trailing_3m_avg,
       ROUND(100.0 * (spend - trailing_3m_avg) / trailing_3m_avg, 1) AS pct_above_avg
FROM w
WHERE n_prior = 3 AND spend > 1.4 * trailing_3m_avg
ORDER BY pct_above_avg DESC;


-- [Q10] Year-over-year change by account (FY2025 vs FY2024)
SELECT account_type, account_name,
       ROUND(SUM(CASE WHEN year = 2024 THEN amount END), 0) AS fy2024,
       ROUND(SUM(CASE WHEN year = 2025 THEN amount END), 0) AS fy2025,
       ROUND(100.0 * (SUM(CASE WHEN year = 2025 THEN amount END)
                    - SUM(CASE WHEN year = 2024 THEN amount END))
                   / SUM(CASE WHEN year = 2024 THEN amount END), 1) AS yoy_pct
FROM fact_actuals
GROUP BY account_type, account_name
ORDER BY account_type DESC, yoy_pct DESC;


-- [Q11] Quarterly KPI scorecard
WITH q AS (
    SELECT year || '-' || quarter AS period,
           SUM(CASE WHEN account_type = 'Revenue' THEN amount ELSE 0 END) AS revenue,
           SUM(CASE WHEN account_type = 'COGS'    THEN amount ELSE 0 END) AS cogs,
           SUM(CASE WHEN account_type = 'Expense' THEN amount ELSE 0 END) AS opex
    FROM fact_actuals
    GROUP BY year, quarter
)
SELECT period,
       ROUND(revenue, 0) AS revenue,
       ROUND(revenue - cogs - opex, 0) AS net_profit,
       ROUND(100.0 * (revenue - cogs) / revenue, 1) AS gross_margin_pct,
       ROUND(100.0 * (revenue - cogs - opex) / revenue, 1) AS net_margin_pct,
       ROUND(100.0 * (revenue - LAG(revenue, 4) OVER (ORDER BY period))
                   / LAG(revenue, 4) OVER (ORDER BY period), 1) AS revenue_yoy_pct
FROM q
ORDER BY period;


-- [Q12] Data-quality check: transactions still needing department assignment
SELECT account_name,
       COUNT(*) AS transactions,
       ROUND(SUM(amount), 0) AS amount
FROM fact_actuals
WHERE department_id = 'D99'
GROUP BY account_name
ORDER BY amount DESC;
