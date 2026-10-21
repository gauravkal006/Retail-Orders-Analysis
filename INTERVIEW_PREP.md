# Interview Prep: Retail Orders Analysis

Plain-language notes so I can explain every step of this project, every query, and the numbers behind it.

---

## 1. The project in 30 seconds

> "I took a raw Kaggle file of about 10,000 retail orders from 2022 and 2023. I cleaned it in pandas: fixed missing values that were written as words, renamed the columns, calculated discount, sale price and profit, and converted the dates. Then I loaded it into SQLite and answered business questions in SQL: top products, top products per region, month-over-month growth, best month per category, and profit growth by sub-category. I added window-function queries for running totals, share of revenue, ranking, and discount impact. I found that sales grew 2.25%, that one copier dominates sales, and that 40% of order lines lose money because zero-markup items still get discounts. The results are in an Excel dashboard, a PDF report and a slide deck."

## 2. The data

- Kaggle dataset `ankitbansal06/retail-orders`, file `orders.csv`: **9,994 rows, 16 columns**.
- One row = one order. `order_id` is unique, so "orders" and "order lines" are the same count here.
- All orders are in the United States, from **2022-01-01 to 2023-12-31**.
- Main columns: order date, ship mode, segment, city, state, region, category, sub-category, product id, cost price, list price, quantity, discount percent.
- `list_price` and `cost_price` are **line totals**, not per-unit prices, so revenue = sum of sale price (no multiplying by quantity).

## 3. Each cleaning step and why it was needed

| Step | What I did | Why |
|---|---|---|
| 1 | `pd.read_csv(..., na_values=['Not Available', 'unknown'])` | Six ship modes were missing, but written as the words "Not Available" or "unknown" (and one real blank). Without this, pandas treats those words as real ship modes and they show up in counts. |
| 2 | `df.columns.str.strip().str.lower().str.replace(' ', '_')` | Headers like `Order Id` and `cost price` have spaces and mixed case. snake_case is easier to type, works with `df.column_name`, and avoids quoting in SQL. |
| 3 | `discount = list_price * discount_percent * 0.01` | The file has a discount *percentage*, but we need the discount *amount* in money. |
| 4 | `sale_price = list_price - discount` | This is the money actually received, so it is our revenue measure. |
| 5 | `profit = sale_price - cost_price` | Profit per order line. Needed for margin and growth questions. |
| 6 | `pd.to_datetime(order_date, format='%Y-%m-%d')` | It is read as text (object). Converting allows year and month extraction and correct sorting. Giving the format is faster and fails loudly on a bad value. |
| 7 | Drop `list_price`, `cost_price` | They are now captured by `sale_price`, `discount` and `profit`. The tutorial also dropped `discount_percent`; I kept it because Q11 groups by it. |
| 8 | Checks before/after | Same row count (9,994), no duplicate order ids, 6 missing ship modes, 507 zero-value lines, 3,997 negative-profit lines. |

**Why keep the 6 rows with missing ship mode?** Their sales and profit are valid; only the ship mode is unknown, and no question here groups by ship mode. Deleting them would understate revenue.

**Why keep the 507 zero-value lines?** List price and cost are both 0 (small items rounded down in the source file). They add nothing to sales or profit, so keeping them changes no totals.

**Why load into SQLite and not SQL Server like the tutorial?** SQLite is a single file and needs no server install, so anyone can clone and rerun the project. The SQL is standard apart from date functions (`strftime` instead of `YEAR()`/`MONTH()`).

**Why store dates as text in SQLite?** SQLite has no real date type. Storing `YYYY-MM-DD` text lets `strftime('%Y', order_date)` work and sorts correctly.

## 4. Each SQL query in plain language

**Q1. Top 10 products by revenue.** Add up `sale_price` for each `product_id`, sort from highest to lowest, keep 10. Answer: TEC-CO-10004722 (59,514), more than twice the second product.

**Q2. Top 5 products in each region.** First total sales per region and product (a CTE). Then number the products inside each region from highest to lowest sales with `ROW_NUMBER() OVER (PARTITION BY region ORDER BY sales DESC)`. Keep numbers 1 to 5. `PARTITION BY` restarts the numbering for each region. Answer: the same copier is No. 1 in Central, East and West; a machine (TEC-MA-10002412) leads the South.

**Q3. Month-over-month sales, 2022 vs 2023.** Total sales per year and month. Then turn years into columns with `SUM(CASE WHEN year = 2022 THEN sales ELSE 0 END)` (a manual pivot) and calculate growth %. Answer: 2023 beat 2022 in 7 of 12 months; February +42%, June -27%.

**Q4. Highest-sales month for each category.** Total sales per category and year-month, number them inside each category by sales, keep number 1. Answer: Furniture Oct 2022, Office Supplies Feb 2023, Technology Oct 2023.

**Q5. Sub-category with the highest profit growth, 2023 vs 2022.** For each sub-category, sum profit only for 2022 rows and only for 2023 rows (conditional sums), then subtract. Sort by growth. Answer: **Machines**, +3,635 (+50.19%). I used profit because that is what the question asks. Growth in sales would be a different question.

**Q6. Year-to-date running total.** Monthly sales, then `SUM(sales) OVER (PARTITION BY year ORDER BY month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)`, which adds every month so far in that year. It resets each January because of `PARTITION BY year`.

**Q7. Category share of revenue.** Sales per category divided by the grand total. `SUM(SUM(sale_price)) OVER ()` puts the grand total on every row without a subquery: the inner `SUM` is the group total, the outer `SUM ... OVER ()` adds up all groups. Technology: 36.41% of sales, 37.25% of profit.

**Q8. Rank sub-categories inside their category.** `DENSE_RANK() OVER (PARTITION BY category ORDER BY SUM(profit) DESC)`. Chairs, Storage and Phones are No. 1 in their categories.

**Q9. Regional profitability.** Sales, profit, margin and 2023 vs 2022 sales growth per region, ranked by profit with `RANK()`. West is largest but its sales fell 11.2%; South has the best margin (10.06%).

**Q10. Segment profitability.** Orders, sales, profit, margin and average order value (sales / distinct orders) per customer segment. Consumer brings about half of sales; Corporate has the best margin.

**Q11. Discount impact.** Group by discount percent (2 to 5) and compare margins. Margin falls from 10.54% at 2% to 7.63% at 5%.

### ROW_NUMBER vs RANK vs DENSE_RANK
For sales of 100, 90, 90, 80:
- `ROW_NUMBER`: 1, 2, 3, 4 (always unique; ties broken arbitrarily)
- `RANK`: 1, 2, 2, 4 (ties share a rank, then a gap)
- `DENSE_RANK`: 1, 2, 2, 3 (ties share a rank, no gap)

For "top 5 per region" I used `ROW_NUMBER` so I always get exactly five rows.

## 5. Numbers to remember

| | |
|---|---|
| Orders | 9,994 |
| Total sales | 2,215,859 |
| Total profit | 205,169 |
| Margin | 9.26% |
| Sales growth 2023 vs 2022 | +2.25% |
| Profit growth | +1.90% |
| Top product | TEC-CO-10004722, 59,514 |
| Highest profit growth | Machines, +50.19% |
| Best-margin region | South, 10.06% |
| Margin at 2% / 5% discount | 10.54% / 7.63% |
| Loss-making lines | 3,997 (40%), total -3,151 |

## 6. Ten likely interview questions

**1. Why did you clean in pandas and analyse in SQL instead of doing everything in one tool?**
pandas is better for row-level fixes like reading tricky missing values, renaming columns and creating derived columns. SQL is what most companies use to query data in a database, and window functions make questions like "top N per group" short and clear. It also reflects a real workflow: clean and load with Python, then analysts query the database.

**2. How did you handle missing values?**
The ship mode column had "Not Available" and "unknown" written as text. I told pandas to treat them as missing with `na_values` at read time. That left 6 missing ship modes. I kept those rows because their sales and profit are valid and no question depends on ship mode.

**3. How did you calculate revenue and profit?**
Discount = list price × discount % / 100. Sale price = list price − discount. Profit = sale price − cost price. Revenue is the sum of sale price. List price is already a line total, so I did not multiply by quantity.

**4. Explain how you found the top 5 products in each region.**
A CTE totals sales per region and product. Then `ROW_NUMBER() OVER (PARTITION BY region ORDER BY sales DESC)` numbers products within each region, and I keep rows where the number is 5 or less. Without `PARTITION BY` it would rank across all regions at once.

**5. What is the difference between `WHERE` and `HAVING`?**
`WHERE` filters rows before grouping; `HAVING` filters groups after aggregation. You cannot filter on a window function in either, which is why I put the window function in a CTE and filtered `rn <= 5` in the outer query.

**6. How do you know your numbers are right?**
The notebook checks that the cleaned table from the notebook is identical to the one from `src/pipeline.py`, and that total sales and profit from SQL match the pandas totals exactly. I also compared row counts before and after cleaning and checked that order ids are unique.

**7. What was the most surprising finding?**
40% of order lines lose money. When I looked closer, 3,955 of the 3,997 loss lines have a list price equal to the cost price, so they have no markup, and then a discount is applied on top. The total loss is small (about 3,151, 1.5% of profit), but it is an easy fix: don't discount zero-markup items.

**8. Sales grew 2.25%. Is that good?**
It is modest growth. Profit grew slower (1.90%), so the margin slipped slightly from 9.28% to 9.24%. The growth is also uneven: East and Central grew 11-13%, while the West, the largest region, fell 11.2%. So the headline number hides a regional problem.

**9. What would you recommend to the business?**
Stop discounting items sold at cost; review the 4-5% discount levels, which give the lowest margins; investigate why the West shrank; protect the top copier, which alone is 2.7% of sales; and look at pricing and costs for Copiers, Appliances and Tables, which lost the most profit.

**10. What are the limitations, and what would you do next?**
Only two years of data, so I cannot separate seasonality from noise. Prices are rounded to the nearest 10 in the source, which creates the zero-value and zero-markup lines. There is no customer id, so I cannot do customer-level or retention analysis. Next I would get more years of data, add customer ids for cohort analysis, and test whether discounts actually increase order volume (are discounted items selling more, or are we just giving margin away?).

## 7. Other questions to be ready for

- **What is a CTE?** A named temporary result (`WITH name AS (...)`) used inside one query. It makes long queries readable, step by step.
- **What does `SUM(...) OVER ()` do?** It calculates a total over a "window" of rows without collapsing them, so each row keeps its own values and also sees the total.
- **How long did it take / what did you add beyond the tutorial?** The tutorial covers cleaning, loading and five questions. I added six window-function queries, the validation checks, the loss-line investigation, the charts, the Excel dashboard, the report and the deck.

## 8. Credit

The flow and the five core questions come from Ankit Bansal's YouTube tutorial *End to End Data Analytics Project (Python + SQL)*. If asked, say so directly: "I followed his tutorial for the base flow, rewrote the code for SQLite, and extended it with my own analysis."
