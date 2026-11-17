/*
  04_home_value_growth.sql
  Question 1: which metros have grown fastest year over year?
  rpt.v_home_value_growth gives each metro-month's home value, the value 12 months earlier
  and the year-over-year change in percent (e.g. 1.19 means +1.19%).
  Safe to re-run (CREATE OR ALTER).
  Run: sqlcmd -S localhost -E -C -b -I -i sql/04_home_value_growth.sql
*/
SET NOCOUNT ON;
USE HousingMarket;
GO

-- Each month is matched to the month exactly 12 months earlier (EOMONTH(month_end, -12)) with a self-join.
-- 169 home-value series have missing months. LAG(home_value, 12) counts rows, not months, so a gap
-- inside the window makes it look 13+ months back (1,774 valid comparisons were lost that way, BUG-002).
-- The join finds the right month whatever the gaps, and gives NULL when that month has no value.
CREATE OR ALTER VIEW rpt.v_home_value_growth
AS
SELECT cur.metro_id,
       cur.month_end,
       cur.home_value,
       prev.home_value AS home_value_1y_ago,
       CAST(CASE WHEN prev.home_value > 0
                 THEN (cur.home_value / prev.home_value - 1) * 100 END AS DECIMAL(9, 4)) AS yoy_pct
FROM core.metro_month AS cur
LEFT JOIN core.metro_month AS prev
       ON prev.metro_id  = cur.metro_id
      AND prev.month_end = EOMONTH(cur.month_end, -12)
WHERE cur.home_value IS NOT NULL;
GO

-- Show the five fastest-growing large metros in the latest month as a quick check.
SELECT TOP (5) m.metro_name, g.month_end, g.home_value, g.home_value_1y_ago, g.yoy_pct
FROM rpt.v_home_value_growth AS g
JOIN core.metro AS m ON m.metro_id = g.metro_id
WHERE g.month_end = (SELECT MAX(month_end) FROM core.metro_month)
  AND m.size_rank BETWEEN 1 AND 100
ORDER BY g.yoy_pct DESC;
