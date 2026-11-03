"""
05_make_charts.py
-----------------
Creates static PNG charts (images/) used in the README and executive summary.
These are Python previews of the key findings; replace or add Power BI
screenshots once the dashboard is built.

Run:  python scripts/05_make_charts.py
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN, IMG = ROOT / "data" / "clean", ROOT / "images"
IMG.mkdir(exist_ok=True)

NAVY, GREY, GOOD, BAD, INK, MUTED = "#1F3864", "#9AA3B2", "#1B7F3B", "#C0392B", "#1F1F1F", "#5F6673"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#C9CED6",
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": "#ECEEF2", "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlecolor": INK,
})
millions = mtick.FuncFormatter(lambda x, _: f"{x/1e6:,.0f}M")

s = pd.read_csv(CLEAN / "monthly_summary.csv", parse_dates=["month_start"])
s["year"] = s["month_start"].dt.year
sign = s["account_type"].map({"Revenue": 1, "COGS": -1, "Expense": -1})

# 1. Monthly revenue: actual vs budget ------------------------------------------
rev = s[s.account_type == "Revenue"].groupby("month_start")[["actual_amount", "budget_amount"]].sum()
fig, ax = plt.subplots(figsize=(10, 4.2))
ax.plot(rev.index, rev["actual_amount"], color=NAVY, lw=2, marker="o", ms=4, label="Actual revenue")
ax.plot(rev.index, rev["budget_amount"], color=GREY, lw=2, ls="--", label="Budget revenue")
q3 = (pd.Timestamp("2025-06-16"), pd.Timestamp("2025-09-15"))
ax.axvspan(*q3, color="#F6E3E1", zorder=0)
ax.text(pd.Timestamp("2025-08-01"), rev["actual_amount"].max() * 1.005, "Q3 2025\nrevenue dip",
        ha="center", va="top", color=BAD, fontsize=9)
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x/1e6:,.1f}M"))
ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %Y"))
ax.set_ylabel("ETB")
ax.set_title("Monthly revenue vs budget, Jan 2024 – Dec 2025", loc="left")
ax.legend(frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig(IMG / "01_revenue_vs_budget.png", dpi=150)
plt.close(fig)

# 2. FY2025 variance by account -----------------------------------------------------
v = (s[s.year == 2025].groupby("account_name")["variance"].sum().sort_values())
fig, ax = plt.subplots(figsize=(10, 5.6))
colors = [GOOD if x >= 0 else BAD for x in v]
bars = ax.barh(v.index, v.values, color=colors, height=0.65)
for b, x in zip(bars, v.values):
    ax.text(x + (40_000 if x >= 0 else -40_000), b.get_y() + b.get_height() / 2,
            (f"{x/1e6:+.2f}M" if abs(x) >= 1e6 else f"{x/1e3:+,.0f}K"), va="center", ha="left" if x >= 0 else "right", fontsize=8.5, color=INK)
ax.axvline(0, color="#8A909C", lw=1)
ax.xaxis.set_major_formatter(millions)
ax.set_xlim(v.min() * 1.25, max(v.max(), 0) * 1.6 + 300_000)
ax.set_title("FY2025 budget variance by account (ETB)\ngreen = favourable · red = unfavourable", loc="left")
ax.grid(axis="y", visible=False)
fig.tight_layout()
fig.savefig(IMG / "02_variance_by_account_fy2025.png", dpi=150)
plt.close(fig)

# 3. Cumulative net profit: actual vs budget (YTD) ---------------------------------
s["np_act"] = s["actual_amount"] * sign
s["np_bud"] = s["budget_amount"] * sign
npm = s.groupby(["year", "month_start"])[["np_act", "np_bud"]].sum()
ytd = npm.groupby(level=0).cumsum().reset_index()
fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for ax, y in zip(axes, (2024, 2025)):
    d = ytd[ytd.year == y]
    ax.plot(d.month_start, d.np_act, color=NAVY, lw=2, marker="o", ms=4, label="Actual YTD")
    ax.plot(d.month_start, d.np_bud, color=GREY, lw=2, ls="--", label="Budget YTD")
    gap = d.np_act.iloc[-1] - d.np_bud.iloc[-1]
    ax.set_title(f"FY{y}: {gap/1e6:+.1f}M ETB vs budget", loc="left",
                 color=GOOD if gap >= 0 else BAD)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b"))
    ax.yaxis.set_major_formatter(millions)
    ax.yaxis.set_major_locator(mtick.MultipleLocator(3e6))
axes[0].legend(frameon=False, loc="upper left")
fig.suptitle("Year-to-date net operating profit", x=0.01, ha="left", fontweight="bold", fontsize=12)
fig.tight_layout()
fig.savefig(IMG / "03_net_profit_ytd.png", dpi=150)
plt.close(fig)

# 4. FY2025 cost mix ---------------------------------------------------------------
c = (s[(s.year == 2025) & (s.account_type != "Revenue")]
     .groupby("account_name")["actual_amount"].sum().sort_values())
share = c / c.sum()
fig, ax = plt.subplots(figsize=(10, 5.2))
bars = ax.barh(c.index, c.values, color=NAVY, height=0.65)
for b, x, p in zip(bars, c.values, share.values):
    ax.text(x + 200_000, b.get_y() + b.get_height() / 2, f"{x/1e6:,.1f}M  ({p:.1%})",
            va="center", fontsize=8.5, color=INK)
ax.xaxis.set_major_formatter(millions)
ax.set_xlim(0, c.max() * 1.25)
ax.set_title("FY2025 cost structure — top 3 lines = 67% of all costs", loc="left")
ax.grid(axis="y", visible=False)
fig.tight_layout()
fig.savefig(IMG / "04_cost_structure_fy2025.png", dpi=150)
plt.close(fig)

print("Charts saved to", IMG)
