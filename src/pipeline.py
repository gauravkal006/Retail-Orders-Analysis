"""Retail Orders Analysis pipeline.

Steps (same order as the notebook):
    1. Clean the raw Kaggle file with pandas.
    2. Load the clean table into SQLite.
    3. Run every query in sql/analysis.sql and save the results.
    4. Work out the headline KPIs and save them as JSON.
    5. Draw the charts.

Run from the project root:
    python src/pipeline.py
"""

from pathlib import Path
import json
import re
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "orders.csv"
CLEAN_CSV = ROOT / "data" / "processed" / "orders_clean.csv"
DB_PATH = ROOT / "data" / "retail_orders.db"
SQL_FILE = ROOT / "sql" / "analysis.sql"
SQL_OUT = ROOT / "outputs" / "sql_results"
KPI_JSON = ROOT / "outputs" / "kpis.json"
CHART_DIR = ROOT / "outputs" / "charts"

# Chart colours: navy as the main colour, steel blue for comparisons,
# amber only to highlight the answer, muted red for declines.
NAVY = "#2F4A6D"
STEEL = "#8FA9C6"
AMBER = "#D4892A"
RED = "#B5533C"
BLUE_STEPS = ["#A9BCD3", "#7C97B8", "#526F96", "#2F4A6D"]  # light to dark
GREY = "#A6A6A6"
TEXT = "#333333"


# ----------------------------------------------------------------------
# 1. Cleaning
# ----------------------------------------------------------------------
def load_raw(path=RAW_CSV):
    # The file uses the words 'Not Available' and 'unknown' for a missing ship mode.
    return pd.read_csv(path, na_values=["Not Available", "unknown"])


def clean(raw):
    df = raw.copy()

    # 'Order Id' -> 'order_id', 'cost price' -> 'cost_price', and so on.
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # list_price is the line total before discount.
    df["discount"] = df["list_price"] * df["discount_percent"] * 0.01
    df["sale_price"] = df["list_price"] - df["discount"]
    df["profit"] = df["sale_price"] - df["cost_price"]

    df["order_date"] = pd.to_datetime(df["order_date"], format="%Y-%m-%d")

    # Prices are now captured by sale_price, discount and profit.
    # discount_percent is kept for the discount analysis (Q11).
    df = df.drop(columns=["list_price", "cost_price"])
    return df


# ----------------------------------------------------------------------
# 2. SQLite
# ----------------------------------------------------------------------
def load_to_sqlite(df, db_path=DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    # Store dates as 'YYYY-MM-DD' text so SQLite's strftime() works on them.
    out["order_date"] = out["order_date"].dt.strftime("%Y-%m-%d")
    with sqlite3.connect(db_path) as conn:
        out.to_sql("df_orders", conn, if_exists="replace", index=False)


def read_queries(sql_file=SQL_FILE):
    """Split analysis.sql into {name: query} using the '-- name:' markers."""
    text = Path(sql_file).read_text(encoding="utf-8")
    parts = re.split(r"^-- name:\s*(\S+)\s*$", text, flags=re.MULTILINE)
    # parts = [header, name1, body1, name2, body2, ...]
    return {name: body.strip() for name, body in zip(parts[1::2], parts[2::2])}


def run_queries(db_path=DB_PATH, out_dir=SQL_OUT):
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    with sqlite3.connect(db_path) as conn:
        for name, query in read_queries().items():
            result = pd.read_sql_query(query, conn)
            result.to_csv(out_dir / f"{name}.csv", index=False)
            results[name] = result
    return results


# ----------------------------------------------------------------------
# 3. KPIs
# ----------------------------------------------------------------------
def compute_kpis(df):
    year = df["order_date"].dt.year
    sales_by_year = df.groupby(year)["sale_price"].sum()
    profit_by_year = df.groupby(year)["profit"].sum()
    region = df.groupby("region")[["sale_price", "profit"]].sum()
    product = df.groupby("product_id")["sale_price"].sum()

    total_sales = df["sale_price"].sum()
    total_profit = df["profit"].sum()
    orders = df["order_id"].nunique()

    return {
        "order_lines": int(len(df)),
        "orders": int(orders),
        "products": int(df["product_id"].nunique()),
        "date_from": df["order_date"].min().strftime("%Y-%m-%d"),
        "date_to": df["order_date"].max().strftime("%Y-%m-%d"),
        "total_sales": round(float(total_sales), 2),
        "total_profit": round(float(total_profit), 2),
        "total_discount": round(float(df["discount"].sum()), 2),
        "profit_margin_pct": round(float(100 * total_profit / total_sales), 2),
        "avg_order_value": round(float(total_sales / orders), 2),
        "sales_2022": round(float(sales_by_year[2022]), 2),
        "sales_2023": round(float(sales_by_year[2023]), 2),
        "sales_growth_pct": round(float(100 * (sales_by_year[2023] / sales_by_year[2022] - 1)), 2),
        "profit_2022": round(float(profit_by_year[2022]), 2),
        "profit_2023": round(float(profit_by_year[2023]), 2),
        "profit_growth_pct": round(float(100 * (profit_by_year[2023] / profit_by_year[2022] - 1)), 2),
        "top_product": product.idxmax(),
        "top_product_sales": round(float(product.max()), 2),
        "top_region_by_profit": region["profit"].idxmax(),
        "missing_ship_mode": int(df["ship_mode"].isna().sum()),
    }


# ----------------------------------------------------------------------
# 4. Charts
# ----------------------------------------------------------------------
def set_style():
    plt.rcParams.update({
        "font.family": "Calibri",
        "font.size": 11,
        "axes.edgecolor": GREY,
        "axes.labelcolor": TEXT,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlecolor": NAVY,
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": "#EDEDED",
        "grid.linewidth": 0.8,
        "xtick.color": TEXT,
        "ytick.color": TEXT,
        "legend.frameon": False,
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
    })


def thousands(ax, axis="y"):
    fmt = mtick.FuncFormatter(lambda v, _: f"{v/1000:,.0f}k")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def make_charts(results, out_dir=CHART_DIR):
    set_style()
    out_dir.mkdir(parents=True, exist_ok=True)
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Monthly sales, 2022 vs 2023
    mom = results["q3_mom_sales_2022_vs_2023"]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(mom["order_month"], mom["sales_2022"], color=STEEL, lw=2, marker="o", ms=5, label="2022")
    ax.plot(mom["order_month"], mom["sales_2023"], color=NAVY, lw=2, marker="o", ms=5, label="2023")
    ax.set_xticks(range(1, 13), month_names)
    thousands(ax)
    ax.set_ylabel("Sales")
    ax.set_title("Monthly sales, 2022 vs 2023")
    ax.set_ylim(top=mom[["sales_2022", "sales_2023"]].max().max() * 1.08)
    ax.legend(loc="upper center", ncol=2)
    ax.grid(axis="x", visible=False)
    fig.savefig(out_dir / "01_monthly_sales_2022_vs_2023.png")
    plt.close(fig)

    # Top 10 products by revenue
    top10 = results["q1_top10_revenue_products"].iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    colors = [AMBER if i == len(top10) - 1 else NAVY for i in range(len(top10))]
    ax.barh(top10["product_id"], top10["sales"], color=colors, height=0.6)
    for y, v in enumerate(top10["sales"]):
        ax.text(v, y, f" {v:,.0f}", va="center", fontsize=10, color=TEXT)
    thousands(ax, "x")
    ax.set_xlabel("Sales")
    ax.set_title("Top 10 products by revenue")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, top10["sales"].max() * 1.15)
    fig.savefig(out_dir / "02_top10_products.png")
    plt.close(fig)

    # Profit growth by sub-category
    growth = results["q5_subcategory_profit_growth"].iloc[::-1]
    colors = [AMBER if i == len(growth) - 1 else (NAVY if v >= 0 else RED)
              for i, v in enumerate(growth["profit_growth"])]
    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.barh(growth["sub_category"], growth["profit_growth"], color=colors, height=0.6)
    ax.axvline(0, color=TEXT, lw=0.8)
    thousands(ax, "x")
    ax.set_xlabel("Profit 2023 minus profit 2022")
    ax.set_title("Profit growth by sub-category, 2023 vs 2022")
    ax.grid(axis="y", visible=False)
    fig.savefig(out_dir / "03_subcategory_profit_growth.png")
    plt.close(fig)

    # Category share of sales and profit
    share = results["q7_category_revenue_share"]
    x = range(len(share))
    fig, ax = plt.subplots(figsize=(8, 4.2))
    w = 0.36
    ax.bar([i - w / 2 for i in x], share["sales_share_pct"], width=w, color=STEEL, label="Share of sales")
    ax.bar([i + w / 2 for i in x], share["profit_share_pct"], width=w, color=NAVY, label="Share of profit")
    for i, (s, p) in enumerate(zip(share["sales_share_pct"], share["profit_share_pct"])):
        ax.text(i - w / 2, s, f"{s:.1f}%", ha="center", va="bottom", fontsize=10, color=TEXT)
        ax.text(i + w / 2, p, f"{p:.1f}%", ha="center", va="bottom", fontsize=10, color=TEXT)
    ax.set_xticks(list(x), share["category"])
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_title("Category share of sales and profit")
    ax.legend(loc="upper right")
    ax.grid(axis="x", visible=False)
    fig.savefig(out_dir / "04_category_share.png")
    plt.close(fig)

    # Profit margin by region
    region = results["q9_region_profitability"].sort_values("margin_pct")
    colors = [AMBER if i == len(region) - 1 else NAVY for i in range(len(region))]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.barh(region["region"], region["margin_pct"], color=colors, height=0.55)
    for y, v in enumerate(region["margin_pct"]):
        ax.text(v, y, f" {v:.2f}%", va="center", fontsize=10, color=TEXT)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_xlim(0, region["margin_pct"].max() * 1.18)
    ax.set_title("Profit margin by region")
    ax.grid(axis="y", visible=False)
    fig.savefig(out_dir / "05_region_margin.png")
    plt.close(fig)

    # Discount impact on margin
    disc = results["q11_discount_impact"]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.bar(disc["discount_percent"].astype(str) + "%", disc["margin_pct"], color=BLUE_STEPS, width=0.55)
    for i, v in enumerate(disc["margin_pct"]):
        ax.text(i, v, f"{v:.2f}%", ha="center", va="bottom", fontsize=10, color=TEXT)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_xlabel("Discount given on the order line")
    ax.set_ylabel("Profit margin")
    ax.set_title("Profit margin by discount level")
    ax.grid(axis="x", visible=False)
    fig.savefig(out_dir / "06_discount_vs_margin.png")
    plt.close(fig)

    # Running total of sales by year
    run = results["q6_running_total_sales"].copy()
    run["year"] = run["order_year_month"].str[:4]
    run["month"] = run["order_year_month"].str[5:].astype(int)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for yr, color, va in [("2022", STEEL, "top"), ("2023", NAVY, "bottom")]:
        part = run[run["year"] == yr]
        ax.plot(part["month"], part["running_total_ytd"], color=color, lw=2, label=yr)
        last = part.iloc[-1]
        ax.text(12.15, last["running_total_ytd"], f"{yr}: {last['running_total_ytd']/1e6:.2f}M",
                va=va, fontsize=10, color=TEXT)
    ax.set_xticks(range(1, 13), month_names)
    ax.set_xlim(0.7, 13.6)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v/1e6:.1f}M"))
    ax.set_ylabel("Cumulative sales")
    ax.set_title("Year-to-date running total of sales")
    ax.legend(loc="upper left")
    ax.grid(axis="x", visible=False)
    fig.savefig(out_dir / "07_running_total.png")
    plt.close(fig)


# ----------------------------------------------------------------------
def main():
    raw = load_raw()
    print(f"Raw file: {raw.shape[0]:,} rows x {raw.shape[1]} columns")

    df = clean(raw)
    CLEAN_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN_CSV, index=False, date_format="%Y-%m-%d")
    print(f"Clean file: {df.shape[0]:,} rows x {df.shape[1]} columns -> {CLEAN_CSV.relative_to(ROOT)}")

    load_to_sqlite(df)
    results = run_queries()
    print(f"Ran {len(results)} SQL queries -> {SQL_OUT.relative_to(ROOT)}")

    kpis = compute_kpis(df)
    KPI_JSON.write_text(json.dumps(kpis, indent=2), encoding="utf-8")
    print(f"KPIs -> {KPI_JSON.relative_to(ROOT)}")

    make_charts(results)
    print(f"Charts -> {CHART_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
