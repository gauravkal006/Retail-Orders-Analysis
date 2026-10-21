"""Build the PDF report (reports/Retail_Orders_Analysis_Report.pdf).

The report is written as HTML and printed to PDF with Microsoft Edge through Playwright.
Run after src/pipeline.py:
    python src/build_report.py
"""

import base64
import json
from datetime import date

import pandas as pd
from playwright.sync_api import sync_playwright

from pipeline import CHART_DIR, KPI_JSON, ROOT, SQL_OUT

IMG_DIR = ROOT / "images"
OUT_FILE = ROOT / "reports" / "Retail_Orders_Analysis_Report.pdf"


def img(path, width="100%", cls=""):
    data = base64.b64encode(path.read_bytes()).decode()
    return f'<img class="{cls}" src="data:image/png;base64,{data}" style="width:{width}">'


def chart(name, width="100%"):
    return img(CHART_DIR / name, width)


def shot(name, width="100%"):
    return img(IMG_DIR / name, width, cls="shot")


def table(name, columns=None, money=(), pct=(), max_rows=None):
    df = pd.read_csv(SQL_OUT / f"{name}.csv")
    if columns:
        df = df[list(columns)].rename(columns=columns)
    if max_rows:
        df = df.head(max_rows)
    fmt = {c: (lambda v: f"{v:,.0f}") for c in money}
    fmt.update({c: (lambda v: f"{v:.2f}%") for c in pct})
    return df.to_html(index=False, border=0, formatters=fmt, classes="t")


def money(v):
    return f"{v:,.0f}"


CSS = """
@page { size: A4; margin: 18mm 18mm 20mm 18mm; }
body { font-family: Calibri, Arial, sans-serif; font-size: 10.5pt; color: #333; line-height: 1.4; }
.cover { background: #2F4A6D; color: #fff; padding: 22px 26px 18px 26px; border-bottom: 5px solid #D4892A; margin-bottom: 16px; }
.cover h1 { font-size: 26pt; margin: 0 0 4px 0; color: #fff; }
.cover .sub { color: #DCE4EE; font-size: 11.5pt; margin: 0; }
.cover .by { color: #fff; font-weight: bold; margin-top: 10px; }
h2 { font-size: 15pt; color: #2F4A6D; margin: 18px 0 8px 0; padding-bottom: 4px; border-bottom: 2px solid #2F4A6D; }

h3 { font-size: 12pt; color: #2F4A6D; margin: 14px 0 5px 0; }
p { margin: 4px 0 8px 0; }
code { color: #2F4A6D; }
.tiles { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 12px 0; }
.tile { flex: 0 0 calc(33.33% - 6px); box-sizing: border-box; background: #EEF2F7; border-left: 4px solid #2F4A6D; padding: 8px 12px; }
.tile .v { font-size: 17pt; font-weight: bold; color: #2F4A6D; line-height: 1.1; }
.tile .l { font-size: 9pt; color: #6B6B6B; }
.box { background: #EEF2F7; border-left: 4px solid #D4892A; padding: 8px 14px 6px 14px; margin: 8px 0 12px 0; }
.box h3 { margin-top: 4px; }
table.t, table.kpi { border-collapse: collapse; margin: 6px 0 12px 0; font-size: 9.5pt; }
table.t th, table.kpi th { text-align: left; background: #2F4A6D; color: #fff; padding: 4px 10px; font-weight: bold; }
table.t td, table.kpi td { padding: 3px 10px; }
table.t tr:nth-child(even) td, table.kpi tr:nth-child(even) td { background: #EEF2F7; }
table.t td:not(:first-child), table.t th:not(:first-child) { text-align: right; }
table.kpi td:last-child { text-align: right; }
.fig { margin: 6px 0 4px 0; page-break-inside: avoid; }
.fig img.shot { border: 1px solid #D0D7E2; }
.cap { font-size: 9pt; color: #6B6B6B; font-style: italic; margin: 0 0 10px 0; }
.break { page-break-before: always; }
ol, ul { margin: 4px 0 8px 18px; padding: 0; }
li { margin-bottom: 4px; }
li::marker { color: #D4892A; font-weight: bold; }
b { color: #2F4A6D; }
.two { display: flex; gap: 16px; }
.two > div { flex: 1; }
"""


def build_html():
    k = json.loads(KPI_JSON.read_text(encoding="utf-8"))
    region = pd.read_csv(SQL_OUT / "q9_region_profitability.csv").set_index("region")
    disc = pd.read_csv(SQL_OUT / "q11_discount_impact.csv").set_index("discount_percent")
    growth = pd.read_csv(SQL_OUT / "q5_subcategory_profit_growth.csv")
    best = growth.iloc[0]

    tiles = [
        ("Total sales", money(k["total_sales"])),
        ("Total profit", money(k["total_profit"])),
        ("Profit margin", f"{k['profit_margin_pct']:.2f}%"),
        ("Orders", f"{k['orders']:,}"),
        ("Average order value", f"{k['avg_order_value']:,.2f}"),
        ("Sales growth 2023 vs 2022", f"+{k['sales_growth_pct']:.2f}%"),
    ]
    kpi_html = '<div class="tiles">' + "".join(
        f'<div class="tile"><div class="v">{v}</div><div class="l">{lbl}</div></div>' for lbl, v in tiles) + "</div>"
    kpi_rows = [
        ("Period", f"{k['date_from']} to {k['date_to']}"),
        ("Products", f"{k['products']:,}"),
        ("Total discount given", money(k["total_discount"])),
        ("Sales 2022 / 2023", f"{money(k['sales_2022'])} / {money(k['sales_2023'])}"),
        ("Profit 2022 / 2023", f"{money(k['profit_2022'])} / {money(k['profit_2023'])}"),
        ("Profit growth 2023 vs 2022", f"+{k['profit_growth_pct']:.2f}%"),
    ]
    kpi_html += '<table class="kpi"><tr><th>Measure</th><th>Value</th></tr>' + "".join(
        f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in kpi_rows) + "</table>"

    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Retail Orders Analysis</title><meta name="author" content="Gaurav Kalamkhede"><style>{CSS}</style></head><body>

<div class="cover">
<h1>Retail Orders Analysis</h1>
<p class="sub">Python (pandas) and SQL (SQLite) analysis of {k['orders']:,} retail orders, 2022 to 2023</p>
<p class="by">Gaurav Kalamkhede &middot; {date.today():%B %Y}</p>
</div>

<h2>1. Summary</h2>
<p>This project cleans a raw retail orders file with pandas, loads it into SQLite and answers business questions in SQL.
It follows the flow of Ankit Bansal's tutorial <i>End to End Data Analytics Project (Python + SQL)</i>, then adds window-function analysis,
an Excel dashboard and this report.</p>
{kpi_html}

<div class="box">
<h3>Key findings</h3>
<ol>
<li>Sales grew {k['sales_growth_pct']:.2f}% in 2023 ({money(k['sales_2022'])} to {money(k['sales_2023'])}) and profit grew {k['profit_growth_pct']:.2f}%. The overall margin is {k['profit_margin_pct']:.2f}%.</li>
<li>One copier, {k['top_product']}, is the top product with {money(k['top_product_sales'])} in sales, more than twice the next product. It ranks first in three of the four regions.</li>
<li>Monthly sales are uneven: February 2023 was 42% above February 2022, but June 2023 was 27% below June 2022.</li>
<li>{best['sub_category']} had the highest profit growth (+{money(best['profit_growth'])}, +{best['growth_pct']:.0f}%). Copiers, Appliances and Tables lost the most profit.</li>
<li>The South has the best margin ({region.loc['South','margin_pct']:.2f}%) but the lowest sales. The West sells the most, but its sales fell {abs(region.loc['West','sales_growth_pct']):.1f}% in 2023.</li>
<li>Margin falls as discount rises: {disc.loc[2,'margin_pct']:.2f}% at a 2% discount, {disc.loc[5,'margin_pct']:.2f}% at 5%.</li>
<li>40% of order lines lose money because the item has no markup and still gets a discount. The total loss is small (about 3.2k), but it is easy to stop.</li>
</ol>
</div>

<h2 class="break">2. Data and cleaning</h2>
<p>Source: Kaggle <i>Retail Orders</i> (ankitbansal06/retail-orders), file <code>orders.csv</code>: 9,994 rows and 16 columns, all orders in the United States.
Each row is one order (order_id is unique). <code>list_price</code> is the line total before discount.</p>
<table class="t">
<tr><th>Step</th><th style="text-align:left">Why</th></tr>
<tr><td>Read with <code>na_values=['Not Available','unknown']</code></td><td style="text-align:left">Missing ship modes were written as words, so pandas would count them as real ship modes.</td></tr>
<tr><td>Rename columns to snake_case</td><td style="text-align:left">Headers had spaces and mixed case ('cost price', 'Order Id'), which are awkward in pandas and SQL.</td></tr>
<tr><td>Derive discount, sale_price, profit</td><td style="text-align:left">The file has list price, cost and discount % only. Revenue and profit must be calculated.</td></tr>
<tr><td>Convert order_date to a date</td><td style="text-align:left">It was read as text, so year and month could not be extracted reliably.</td></tr>
<tr><td>Drop list_price and cost_price</td><td style="text-align:left">They are captured by the new columns. discount_percent is kept for the discount analysis.</td></tr>
</table>
<div class="fig">{shot('nb_01_read_raw.png', '88%')}</div>
<p class="cap">Figure 1. Notebook: reading the file with na_values turns 'Not Available' and 'unknown' into NaN (6 missing ship modes).</p>
<div class="fig">{shot('nb_03_cleaning_checks.png', '72%')}</div>
<p class="cap">Figure 2. Notebook: checks before and after cleaning. No rows are lost and there are no duplicate orders.</p>

<h2 class="break">3. Business questions from the tutorial</h2>
<h3>Q1. Top 10 products by revenue</h3>
<div class="fig">{chart('02_top10_products.png', '78%')}</div>
<p>{k['top_product']} earns {money(k['top_product_sales'])}, more than twice the second product. Four of the top ten are binders, and two are machines.</p>

<h3>Q2. Top 5 products in each region</h3>
<p>The same copier leads the Central, East and West regions. The South is led by a machine (TEC-MA-10002412).</p>
{table('q2_top5_products_per_region', {'region':'Region','rank_in_region':'Rank','product_id':'Product','sales':'Sales'}, money=['Sales'])}

<h3 class="break">Q3. Month-over-month sales, 2022 vs 2023</h3>
<div class="fig">{chart('01_monthly_sales_2022_vs_2023.png', '92%')}</div>
{table('q3_mom_sales_2022_vs_2023', {'order_month':'Month','sales_2022':'Sales 2022','sales_2023':'Sales 2023','growth_pct':'Growth'}, money=['Sales 2022','Sales 2023'], pct=['Growth'])}
<p>October was the best month of 2022 and February the best of 2023. 2023 beat 2022 in 7 of 12 months; February (+42%) and April (+17%) gained most, June (-27%) and August (-16%) fell most.</p>

<h3 class="break">Q4. Highest-sales month for each category</h3>
{table('q4_best_month_per_category', {'category':'Category','order_year_month':'Best month','sales':'Sales'}, money=['Sales'])}

<h3>Q5. Sub-category with the highest profit growth, 2023 vs 2022</h3>
<div class="fig">{chart('03_subcategory_profit_growth.png', '88%')}</div>
<p><b>{best['sub_category']}</b> grew profit the most: from {money(best['profit_2022'])} to {money(best['profit_2023'])} (+{best['growth_pct']:.2f}%).
Nine sub-categories grew and eight declined. Copiers, Appliances and Tables together lost about 7.6k of profit.</p>
<div class="fig">{shot('nb_06_sql_q5_growth.png', '62%')}</div>
<p class="cap">Figure 3. Notebook: the Q5 query result from SQLite.</p>

<h2 class="break">4. Extended analysis (window functions and CTEs)</h2>
<h3>Q6. Year-to-date running total</h3>
<div class="fig">{chart('07_running_total.png', '88%')}</div>
<p>2023 was behind 2022 only in January, stayed ahead from February onwards, and finished {k['sales_growth_pct']:.2f}% higher.</p>

<h3>Q7. Category share of sales and profit</h3>
<div class="two"><div>{chart('04_category_share.png')}</div><div>
{table('q7_category_revenue_share', {'category':'Category','sales_share_pct':'Sales share','profit_share_pct':'Profit share'}, pct=['Sales share','Profit share'])}
<p>Technology is the largest category and earns a slightly larger share of profit than of sales. The three categories are close in size.</p></div></div>

<h3 class="break">Q8. Sub-categories ranked within each category</h3>
{table('q8_subcategory_rank_within_category', {'category':'Category','sub_category':'Sub-category','sales':'Sales','profit':'Profit','margin_pct':'Margin','profit_rank':'Rank'}, money=['Sales','Profit'], pct=['Margin'])}
<p>Chairs, Storage and Phones lead their categories. Fasteners (1.66%) and Labels (5.38%) have the thinnest margins.</p>

<h3>Q9. Regional profitability</h3>
<div class="fig">{chart('05_region_margin.png', '75%')}</div>
{table('q9_region_profitability', {'region':'Region','sales':'Sales','profit':'Profit','margin_pct':'Margin','sales_growth_pct':'Sales growth','profit_rank':'Profit rank'}, money=['Sales','Profit'], pct=['Margin','Sales growth'])}

<h3 class="break">Q10. Segment profitability</h3>
{table('q10_segment_profitability', {'segment':'Segment','orders':'Orders','sales':'Sales','profit':'Profit','margin_pct':'Margin','avg_order_value':'Avg order value'}, money=['Orders','Sales','Profit'], pct=['Margin'])}
<p>Consumers bring half of all sales. Corporate customers have the best margin (9.63%) and Home Office the largest average order.</p>

<h3>Q11. Discount impact on profit</h3>
<div class="fig">{chart('06_discount_vs_margin.png', '75%')}</div>
{table('q11_discount_impact', {'discount_percent':'Discount %','order_lines':'Lines','sales':'Sales','discount_given':'Discount given','profit':'Profit','margin_pct':'Margin'}, money=['Lines','Sales','Discount given','Profit'], pct=['Margin'])}
<p>Each extra point of discount lowers the margin by roughly one point. The discount levels are spread evenly across lines, so this is not caused by a few large orders.</p>

<h2 class="break">5. Recommendations</h2>
<div class="box">
<ol>
<li><b>Stop discounting items sold at cost.</b> Almost all loss-making lines have no markup. A simple rule (no discount when list price equals cost) removes the losses.</li>
<li><b>Review the 4-5% discount levels.</b> They give about 51k of discount for a margin of 7.6-9.1%, against 10.5% at 2%.</li>
<li><b>Look into the West.</b> It is the largest region, but sales fell 11.2% in 2023 while the other regions grew.</li>
<li><b>Protect the top copier.</b> One product brings 2.7% of all sales. Keep it in stock and watch its pricing.</li>
<li><b>Investigate falling sub-categories.</b> Copiers, Appliances and Tables lost the most profit. Check pricing, cost changes and product mix.</li>
<li><b>Plan for the busy months.</b> October was one of the two best months in both years, and February and April were strong in 2023, so stock and staff can be planned ahead.</li>
</ol>
</div>

<h2>6. Method and tools</h2>
<ul>
<li>Python 3.13 with pandas for cleaning, SQLite for the SQL analysis (all queries in <code>sql/analysis.sql</code>).</li>
<li>Jupyter notebook for the walkthrough; <code>src/pipeline.py</code> reproduces every output in one run.</li>
<li>matplotlib for charts, openpyxl for the Excel dashboard, Playwright with Microsoft Edge for this PDF, python-pptx for the slides.</li>
<li>Totals were checked to match between SQL and pandas.</li>
</ul>
<div class="fig">{shot('nb_08_totals_match.png')}</div>
<p class="cap">Figure 4. Notebook: SQL and pandas totals match.</p>

<h3>Acknowledgement</h3>
<p>The project flow and the five core business questions follow Ankit Bansal's YouTube tutorial
<i>End to End Data Analytics Project (Python + SQL)</i> (youtube.com/watch?v=uL0-6kfiH3g) and his Kaggle dataset.
The code was written fresh for this project, and the extended analysis, dashboard, report and slides were added.</p>
</body></html>"""


def build():
    html = build_html()
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        page.pdf(
            path=str(OUT_FILE), format="A4", print_background=True,
            display_header_footer=True,
            header_template="<span></span>",
            footer_template=('<div style="font-family:Calibri,Arial;font-size:8pt;color:#2F4A6D;width:100%;'
                             'text-align:center;">Retail Orders Analysis &middot; page '
                             '<span class="pageNumber"></span> of <span class="totalPages"></span></div>'),
            margin={"top": "18mm", "bottom": "20mm", "left": "18mm", "right": "18mm"},
        )
        browser.close()
    print(f"Report -> {OUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
