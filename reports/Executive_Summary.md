# Executive Summary — FY2025 Financial Performance Review
**Abay Trading PLC (synthetic data)** · Prepared by: *[Your Name]*, Financial Analyst · All figures in ETB

---

## 1. Bottom line

FY2025 net operating profit was **10.7M ETB, 8.1M (43%) below budget**, even though revenue grew 10.5% year on year. The FY2026 budget needs a more realistic revenue plan, and three cost lines need tighter control.

| | FY2024 | FY2025 | FY2025 Budget | Var vs Budget |
|---|---:|---:|---:|---:|
| Revenue | 83.3M | 92.0M | 98.4M | −6.4M |
| Gross profit | 49.6M | 53.5M | 60.3M | −6.8M |
| Operating expenses | 39.2M | 42.9M | 41.5M | −1.3M |
| **Net operating profit** | **10.4M** | **10.7M** | **18.8M** | **−8.1M** |
| Net margin | 12.5% | 11.6% | 19.1% | −7.5 pp |

FY2024 beat its profit budget by 2.0M. FY2025 is the first year with a material miss.

## 2. What drove the 8.1M profit shortfall

| Driver | Impact | Comment |
|---|---:|---|
| Product Sales below budget | −4.1M | Q3 loss of a large wholesale account (−1.7M in Q3 alone) |
| Service Revenue below budget | −1.3M | Same Q3 weakness (−1.0M in Q3) |
| Subscription Revenue below budget | −1.0M | Grew 45% YoY but the budget assumed even faster growth |
| Marketing & Advertising overspend | −0.9M | 87% from a single Q2 campaign (+67% over its quarterly budget) |
| Freight & Logistics overspend | −0.7M | Fuel-driven rate increase from March 2025 (+36% per month vs 2024) |
| All other lines (net) | −0.1M | Materials 0.4M under budget offset small overruns elsewhere |

**Interpretation:** Most of the gap (79%) is revenue. Part of it was a target-setting problem: the budget assumed 18% growth on FY2024, but the business delivered 10.5%. The other part was a real Q3 setback. Cost overruns are smaller but are concentrated and controllable.

## 3. Things that went well

- **Subscription revenue +45% YoY**, now 13.6% of total revenue (10.4% in FY2024). It is recurring and predictable.
- **Materials 0.4M under budget** (1.6% favourable) despite higher volumes.
- **Q4 2025 recovered strongly**: net margin 19.0%, the best quarter in two years.
- Finance and Sales cost centres stayed within budget.

## 4. Risks and watch-points

- **Gross margin fell to 52.4% in Q3 2025**, versus ~60% normally, as revenue dropped faster than cost of sales.
- **Freight is now a structural cost.** Without action it will keep running ~1.2M a year above the 2024 level.
- **Software & IT costs +28.5% YoY.** Licences should be audited before renewal.
- **545K of FY2025 costs have no department**, so department budgets are understated.

## 5. Recommendations for FY2026

1. **Driver-based revenue budget** (customers × volume × price) with a formal mid-year re-forecast.
2. **Key-account protection**: retention plan and monthly reviews for the top 20 customers.
3. **Marketing spend gates**: business case before launch, spend released in tranches, ROI review after each campaign.
4. **Freight tender and fuel-surcharge clause**, targeting a 10–15% saving on 4.3M.
5. **Accelerate subscriptions**, the highest-growth recurring revenue line.
6. **Mandatory cost-centre coding**, plus a monthly "unassigned cost" exception report.
7. **Monthly variance pack**: any line more than ±10% off budget requires an owner's explanation (built into the Excel workbook and Power BI dashboard).

## 6. Method (one paragraph)

1,795 raw GL rows were cleaned in Python. Duplicates, test postings, mixed date formats, text amounts and missing departments were fixed, leaving 1,739 valid transactions. The clean data was modelled as a star schema and analysed with 12 SQL queries, a formula-driven Excel workbook and a Power BI dashboard. All three tools were reconciled to the same totals.
