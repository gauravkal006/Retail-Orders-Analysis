-- Retail Orders Analysis (SQLite)
-- Table: df_orders, created by src/pipeline.py from the cleaned pandas DataFrame.
-- Each query starts with a "-- name:" line so the pipeline and notebook can run them one by one.
-- Revenue = SUM(sale_price). Each row is one order line, and list_price is the line total.


-- ============================================================
-- Part A: business questions from the tutorial
-- ============================================================

-- name: q1_top10_revenue_products
-- Q1. Top 10 products by revenue.
SELECT product_id,
       ROUND(SUM(sale_price), 2) AS sales
FROM df_orders
GROUP BY product_id
ORDER BY sales DESC
LIMIT 10;


-- name: q2_top5_products_per_region
-- Q2. Top 5 products by revenue in each region.
WITH region_product AS (
    SELECT region,
           product_id,
           SUM(sale_price) AS sales
    FROM df_orders
    GROUP BY region, product_id
),
ranked AS (
    SELECT region,
           product_id,
           sales,
           ROW_NUMBER() OVER (PARTITION BY region ORDER BY sales DESC) AS rn
    FROM region_product
)
SELECT region, rn AS rank_in_region, product_id, ROUND(sales, 2) AS sales
FROM ranked
WHERE rn <= 5
ORDER BY region, rn;


-- name: q3_mom_sales_2022_vs_2023
-- Q3. Month-over-month sales, 2022 vs 2023.
WITH monthly AS (
    SELECT CAST(strftime('%Y', order_date) AS INTEGER) AS order_year,
           CAST(strftime('%m', order_date) AS INTEGER) AS order_month,
           SUM(sale_price) AS sales
    FROM df_orders
    GROUP BY order_year, order_month
)
SELECT order_month,
       ROUND(SUM(CASE WHEN order_year = 2022 THEN sales ELSE 0 END), 2) AS sales_2022,
       ROUND(SUM(CASE WHEN order_year = 2023 THEN sales ELSE 0 END), 2) AS sales_2023,
       ROUND(100.0 * (SUM(CASE WHEN order_year = 2023 THEN sales ELSE 0 END)
                    - SUM(CASE WHEN order_year = 2022 THEN sales ELSE 0 END))
             / SUM(CASE WHEN order_year = 2022 THEN sales ELSE 0 END), 2) AS growth_pct
FROM monthly
GROUP BY order_month
ORDER BY order_month;


-- name: q4_best_month_per_category
-- Q4. For each category, the month (year-month) with the highest sales.
WITH category_month AS (
    SELECT category,
           strftime('%Y-%m', order_date) AS order_year_month,
           SUM(sale_price) AS sales
    FROM df_orders
    GROUP BY category, order_year_month
),
ranked AS (
    SELECT category, order_year_month, sales,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY sales DESC) AS rn
    FROM category_month
)
SELECT category, order_year_month, ROUND(sales, 2) AS sales
FROM ranked
WHERE rn = 1
ORDER BY category;


-- name: q5_subcategory_profit_growth
-- Q5. Sub-categories by profit growth, 2023 vs 2022 (the first row answers the question).
WITH yearly AS (
    SELECT sub_category,
           SUM(CASE WHEN strftime('%Y', order_date) = '2022' THEN profit ELSE 0 END) AS profit_2022,
           SUM(CASE WHEN strftime('%Y', order_date) = '2023' THEN profit ELSE 0 END) AS profit_2023
    FROM df_orders
    GROUP BY sub_category
)
SELECT sub_category,
       ROUND(profit_2022, 2) AS profit_2022,
       ROUND(profit_2023, 2) AS profit_2023,
       ROUND(profit_2023 - profit_2022, 2) AS profit_growth,
       ROUND(100.0 * (profit_2023 - profit_2022) / profit_2022, 2) AS growth_pct
FROM yearly
ORDER BY profit_growth DESC;


-- ============================================================
-- Part B: extensions (window functions and CTEs)
-- ============================================================

-- name: q6_running_total_sales
-- Q6. Monthly sales with a running total that restarts each year.
WITH monthly AS (
    SELECT strftime('%Y', order_date) AS order_year,
           strftime('%Y-%m', order_date) AS order_year_month,
           SUM(sale_price) AS sales
    FROM df_orders
    GROUP BY order_year, order_year_month
)
SELECT order_year_month,
       ROUND(sales, 2) AS sales,
       ROUND(SUM(sales) OVER (PARTITION BY order_year ORDER BY order_year_month
                              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS running_total_ytd
FROM monthly
ORDER BY order_year_month;


-- name: q7_category_revenue_share
-- Q7. Each category's share of total revenue and profit.
SELECT category,
       ROUND(SUM(sale_price), 2) AS sales,
       ROUND(100.0 * SUM(sale_price) / SUM(SUM(sale_price)) OVER (), 2) AS sales_share_pct,
       ROUND(SUM(profit), 2) AS profit,
       ROUND(100.0 * SUM(profit) / SUM(SUM(profit)) OVER (), 2) AS profit_share_pct
FROM df_orders
GROUP BY category
ORDER BY sales DESC;


-- name: q8_subcategory_rank_within_category
-- Q8. Sub-categories ranked by profit inside their category.
SELECT category,
       sub_category,
       ROUND(SUM(sale_price), 2) AS sales,
       ROUND(SUM(profit), 2) AS profit,
       ROUND(100.0 * SUM(profit) / SUM(sale_price), 2) AS margin_pct,
       DENSE_RANK() OVER (PARTITION BY category ORDER BY SUM(profit) DESC) AS profit_rank
FROM df_orders
GROUP BY category, sub_category
ORDER BY category, profit_rank;


-- name: q9_region_profitability
-- Q9. Regional sales, profit and margin, with year-over-year sales growth.
WITH region_year AS (
    SELECT region,
           SUM(sale_price) AS sales,
           SUM(profit) AS profit,
           SUM(CASE WHEN strftime('%Y', order_date) = '2022' THEN sale_price ELSE 0 END) AS sales_2022,
           SUM(CASE WHEN strftime('%Y', order_date) = '2023' THEN sale_price ELSE 0 END) AS sales_2023
    FROM df_orders
    GROUP BY region
)
SELECT region,
       ROUND(sales, 2) AS sales,
       ROUND(profit, 2) AS profit,
       ROUND(100.0 * profit / sales, 2) AS margin_pct,
       ROUND(100.0 * (sales_2023 - sales_2022) / sales_2022, 2) AS sales_growth_pct,
       RANK() OVER (ORDER BY profit DESC) AS profit_rank
FROM region_year
ORDER BY profit_rank;


-- name: q10_segment_profitability
-- Q10. Customer segment sales, profit, margin and average order value.
SELECT segment,
       COUNT(DISTINCT order_id) AS orders,
       ROUND(SUM(sale_price), 2) AS sales,
       ROUND(SUM(profit), 2) AS profit,
       ROUND(100.0 * SUM(profit) / SUM(sale_price), 2) AS margin_pct,
       ROUND(SUM(sale_price) / COUNT(DISTINCT order_id), 2) AS avg_order_value
FROM df_orders
GROUP BY segment
ORDER BY sales DESC;


-- name: q11_discount_impact
-- Q11. How the discount percentage relates to profit margin.
SELECT discount_percent,
       COUNT(*) AS order_lines,
       ROUND(SUM(sale_price), 2) AS sales,
       ROUND(SUM(discount), 2) AS discount_given,
       ROUND(SUM(profit), 2) AS profit,
       ROUND(100.0 * SUM(profit) / SUM(sale_price), 2) AS margin_pct
FROM df_orders
GROUP BY discount_percent
ORDER BY discount_percent;
