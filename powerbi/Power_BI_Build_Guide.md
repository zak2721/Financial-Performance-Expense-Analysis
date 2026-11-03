# Power BI Build Guide — Financial Performance Dashboard

Step-by-step instructions to build `Financial_Performance_Dashboard.pbix` from the clean data.
Estimated time: 4–6 hours the first time. Build it yourself — this is the part interviewers ask about.

---

## Step 1 — Import the data

**Home → Get Data → Text/CSV**, load these files from `data/clean/`:

| File | Table name in model | Role |
|---|---|---|
| `fact_actuals.csv` | fact_actuals | Fact (one row per transaction) |
| `fact_budget.csv` | fact_budget | Fact (month × account × department) |
| `dim_account.csv` | dim_account | Dimension |
| `dim_department.csv` | dim_department | Dimension |

Do **not** import `dim_date.csv` — you will build a proper daily Date table in DAX (Step 3).
Do not import `monthly_summary.csv` — Power BI calculates that itself.

## Step 2 — Power Query (Transform Data)

Even though Python already cleaned the data, show Power Query skills here:

1. **fact_actuals**
   - Set types: `posting_date`, `month_start` → Date; `amount`, `signed_amount` → Fixed decimal; `account_id` → Whole number.
   - Remove columns that duplicate dimensions: `account_name`, `account_type`, `account_category`, `department_name`, `division`, `year`, `quarter`, `month_num` (they come from dimension tables — this keeps the model a clean star schema).
   - Rename the step names (e.g. "Removed dimension columns") — reviewers notice.
2. **fact_budget** — `month_start` → Date, `budget_amount` → Fixed decimal. Remove `department_name`.
3. **dim_account / dim_department** — check types; nothing else.
4. Close & Apply.

> Interview tip: be ready to explain *why* you removed the descriptive columns from the fact table (smaller model, single source of truth, filters flow from dimensions).

## Step 3 — Date table

**Modeling → New table**, paste the `Date` table from `DAX_Measures.dax`.
Then: **Table tools → Mark as date table → Date column = [Date]**.
Sort `Month` by `Month Num` (select column → Sort by column).

## Step 4 — Relationships (Model view)

| From (many) | To (one) | Cardinality | Filter direction |
|---|---|---|---|
| fact_actuals[posting_date] | Date[Date] | Many-to-one | Single |
| fact_budget[month_start] | Date[Date] | Many-to-one | Single |
| fact_actuals[account_id] | dim_account[account_id] | Many-to-one | Single |
| fact_budget[account_id] | dim_account[account_id] | Many-to-one | Single |
| fact_actuals[department_id] | dim_department[department_id] | Many-to-one | Single |
| fact_budget[department_id] | dim_department[department_id] | Many-to-one | Single |

Result: a **star schema with two fact tables sharing conformed dimensions**. Take a screenshot of the Model view for your README (`images/data_model.png`).

Budget is monthly while actuals are daily. Because the budget is stored on the first day of each month, it filters correctly at month, quarter and year level. Don't show budget at day level.

## Step 5 — Measures

1. Home → Enter data → name the table `_Measures` → Load. Delete its default column after adding the first measure.
2. Add every measure from `DAX_Measures.dax`. Put them into display folders (Properties pane → Display folder) using the folder names in the file.
3. Formatting: currency measures → Whole number with thousands separator; % measures → Percentage, 1 decimal.
4. Optional: **Modeling → New parameter → Numeric range** named `Variance Threshold`, 0 to 0.30, increment 0.01, default 0.10. This drives `Review Flag`.

## Step 6 — Theme

View → Themes → Browse for themes → `finance_theme.json`.

## Step 7 — Report pages

Canvas 1280 × 720. Every page has the same header band: title (left), `Selected Period` card, and slicers for **Year**, **Quarter**, **Department** (sync slicers across pages: View → Sync slicers).

### Page 1 — Executive Overview
| Position | Visual | Fields |
|---|---|---|
| Top row | 5 KPI cards (new card visual) | Revenue, Gross Profit, Net Profit, Net Margin %, Budget Achievement %. Add reference label: budget value + variance %. |
| Middle-left (wide) | Line & clustered column chart | X: Date[Year Month]; Columns: Revenue; Line: Budget Revenue |
| Middle-right | Waterfall | Category: dim_account[account_type]; Breakdown: dim_account[account_name]; Y: Variance (Fav +) — shows *what explains the gap to budget profit* |
| Bottom | Line chart | X: Year Month; Net Profit YTD, Budget Net Profit YTD |
| Text box | Smart narrative or a card with `Headline Text` | — |

### Page 2 — Budget vs Actual
| Visual | Fields |
|---|---|
| Matrix | Rows: account_type → account_name; Columns: Date[Quarter]; Values: Actual Amount, Budget Amount, Variance (Fav +), Variance %. Conditional formatting: font colour on Variance using `Variance Colour` (field value). |
| Bar chart (sorted ascending) | Axis: account_name; Value: Variance (Fav +) — biggest problems on top |
| Table | account_name, Variance %, Variance Status, Review Flag |
| Gauge | Value: Revenue; Target: Budget Revenue |

### Page 3 — Expense Analysis
| Visual | Fields |
|---|---|
| Treemap or donut | Group: account_category → account_name; Value: Total Costs |
| Stacked area / line | X: Year Month; Value: Total Costs; Legend: account_category |
| Clustered bar | Axis: account_name; Values: Total Costs, Total Costs PY (filter: account_type ≠ Revenue) |
| Table "Expense spikes" | Year Month, account_name, Total Costs, Costs 3M Trailing Avg, Expense Spike %, Expense Anomaly (visual filter: Expense Anomaly is not blank) |
| Table "Top vendors" | counterparty, account_name, Total Costs, Vendor Rank (filter: Top N = 10 by Total Costs; exclude Internal Payroll/Unknown) |

### Page 4 — Department Performance
| Visual | Fields |
|---|---|
| Clustered bar | Axis: department_name; Values: Total Costs, Budget COGS + Budget OpEx (create measure `Budget Costs = [Budget COGS] + [Budget OpEx]`) |
| Matrix | Rows: division → department_name; Values: Total Costs, Budget Costs, Cost Variance, Variance % |
| Card | Unassigned Amount, Unassigned % of Costs — data-quality callout |

### (Optional) Tooltip page
Page size: Tooltip. Mini line chart of Revenue vs Budget Revenue by month. In Page information enable "Allow use as tooltip", then set it as the tooltip on Page 2's bar chart.

## Step 8 — Interactivity & polish

- **Drill-through**: create a page "Account Detail" with drill-through field `dim_account[account_name]` and a table of transactions (posting_date, counterparty, description, amount).
- **Bookmarks + buttons**: toggle on Page 1 between "vs Budget" and "vs Prior Year" views.
- Align visuals (Format → Align), consistent 16 px spacing, titles that state the insight ("Marketing overspent budget by 19% in FY2025") rather than "Sum of amount by account".
- Add alt text to every visual (accessibility).
- Turn off unused interactions (Format → Edit interactions).

## Step 9 — Validate against SQL/Excel

Check that Power BI matches the other tools before publishing:

| Check (FY2025) | Expected |
|---|---|
| Revenue | 92,031,989 |
| Budget Revenue | 98,435,800 |
| Net Profit | 10,656,645 |
| Budget Net Profit | 18,767,700 |
| Gross Margin % | 58.2% |
| Marketing & Advertising variance | (883,531) |

## Step 10 — Publish & share

1. Save as `powerbi/Financial_Performance_Dashboard.pbix`.
2. Publish to the Power BI Service (free account) → File → Embed report → **Publish to web** (only because the data is synthetic — never do this with real company data).
3. Export each page as PNG into `images/` and reference them in the README.
4. Optionally upload to NovyPro for a public portfolio link.
