/*
  06_supply_vs_price.sql
  Question 3: how do inventory and days on market relate to price changes?
    rpt.v_supply_vs_price           - per metro-month: for-sale inventory and its 1-year % change,
                                      days to pending and its 1-year change in days, home value 1-year % change
    rpt.v_supply_price_correlation  - per month: Pearson correlation across the 100 largest metros
                                      between those supply changes and the home value change
  Year-over-year uses the same rule as 04: the month exactly 12 months back, or NULL.
  Safe to re-run (CREATE OR ALTER).
  Run: sqlcmd -S localhost -E -C -b -I -i sql/06_supply_vs_price.sql
*/
SET NOCOUNT ON;
USE HousingMarket;
GO

-- Supply measures and their 1-year changes, joined to the home value growth from 04.
CREATE OR ALTER VIEW rpt.v_supply_vs_price
AS
SELECT cur.metro_id,
       cur.month_end,
       cur.for_sale_inventory,
       CAST(CASE WHEN prev.for_sale_inventory > 0
                 THEN (CAST(cur.for_sale_inventory AS FLOAT) / prev.for_sale_inventory - 1) * 100 END
            AS DECIMAL(9, 4))                                         AS inventory_yoy_pct,
       cur.days_to_pending,
       cur.days_to_pending - prev.days_to_pending                    AS days_to_pending_yoy_change,
       g.yoy_pct                                                     AS home_value_yoy_pct
FROM core.metro_month AS cur
LEFT JOIN core.metro_month AS prev
       ON prev.metro_id  = cur.metro_id
      AND prev.month_end = EOMONTH(cur.month_end, -12)
LEFT JOIN rpt.v_home_value_growth AS g
       ON g.metro_id  = cur.metro_id
      AND g.month_end = cur.month_end
WHERE cur.for_sale_inventory IS NOT NULL
   OR cur.days_to_pending IS NOT NULL;
GO

-- Pearson r = (n·Σxy − Σx·Σy) / √((n·Σx² − (Σx)²)(n·Σy² − (Σy)²)), built from plain aggregates.
-- Only large metros (size_rank 1-100) that have all three changes in that month take part.
CREATE OR ALTER VIEW rpt.v_supply_price_correlation
AS
WITH pts AS (
    SELECT s.month_end,
           CAST(s.inventory_yoy_pct AS FLOAT)          AS x_inv,
           CAST(s.days_to_pending_yoy_change AS FLOAT) AS x_days,
           CAST(s.home_value_yoy_pct AS FLOAT)         AS y
    FROM rpt.v_supply_vs_price AS s
    JOIN core.metro AS m ON m.metro_id = s.metro_id
    WHERE m.size_rank BETWEEN 1 AND 100
      AND s.inventory_yoy_pct IS NOT NULL
      AND s.days_to_pending_yoy_change IS NOT NULL
      AND s.home_value_yoy_pct IS NOT NULL
), sums AS (
    SELECT month_end,
           COUNT(*) AS n,
           SUM(x_inv) AS sx_inv, SUM(x_inv * x_inv) AS sxx_inv, SUM(x_inv * y) AS sxy_inv,
           SUM(x_days) AS sx_days, SUM(x_days * x_days) AS sxx_days, SUM(x_days * y) AS sxy_days,
           SUM(y) AS sy, SUM(y * y) AS syy
    FROM pts
    GROUP BY month_end
)
SELECT month_end,
       n AS metros,
       CAST((n * sxy_inv - sx_inv * sy)
            / NULLIF(SQRT((n * sxx_inv - sx_inv * sx_inv) * (n * syy - sy * sy)), 0) AS DECIMAL(6, 4)) AS r_inventory_vs_price,
       CAST((n * sxy_days - sx_days * sy)
            / NULLIF(SQRT((n * sxx_days - sx_days * sx_days) * (n * syy - sy * sy)), 0) AS DECIMAL(6, 4)) AS r_days_vs_price
FROM sums
WHERE n >= 3;
GO

-- Show the last 6 months of correlations as a quick check.
SELECT TOP (6) * FROM rpt.v_supply_price_correlation ORDER BY month_end DESC;
