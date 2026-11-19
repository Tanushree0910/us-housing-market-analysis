/* 07_analysis.sql (was analysis.sql) - Day 19: 8 business questions on Zillow home values (ZHVI) and rents (ZORI),
   plus Q9-Q10 (added 2026-11-19) on Zillow inventory and days to pending - the README's third question.
   Uses: dbo.fact_home_values, dbo.fact_rent, dbo.fact_market, dbo.dim_metro (all views over the loaded tables).
   Conventions:
   - "Latest month" = the newest month_date in fact_home_values (2026-09-30). YoY compares to the same month a year earlier.
   - The prior-year month is found with EOMONTH(date, -12) in a join instead of LAG(12), so a metro with a missing month
     returns no YoY instead of silently comparing the wrong month.
   - dim_metro includes one 'country' row (United States, RegionID 102001) used as the national benchmark;
     all metro rankings filter RegionType = 'msa' so the US row is never ranked against metros.
   - Rent-to-price ratio = (monthly rent x 12) / home value x 100, i.e. gross annual rent as a % of home value.
   - Inventory change is YoY %; days-to-pending change is in days (latest month minus the same month a year earlier). */

USE [Housing Data];
GO

DECLARE @latest date = (SELECT MAX(month_date) FROM dbo.fact_home_values);

-- Q1: National home value and YoY % growth for each of the last 24 months (is growth speeding up or slowing down?)
WITH us AS (
    SELECT month_date, home_value FROM dbo.fact_home_values WHERE RegionID = 102001
)
SELECT cur.month_date,
       CAST(cur.home_value  AS decimal(12,0)) AS home_value,
       CAST(prev.home_value AS decimal(12,0)) AS home_value_12m_ago,
       CAST((cur.home_value / prev.home_value - 1) * 100 AS decimal(6,2)) AS yoy_pct
FROM us cur
JOIN us prev ON prev.month_date = EOMONTH(cur.month_date, -12)
WHERE cur.month_date >= EOMONTH(@latest, -23)
ORDER BY cur.month_date;

-- Q2: Top 10 metros by YoY home value growth in the latest month (where are prices rising fastest?)
WITH yoy AS (
    SELECT cur.RegionID, cur.home_value AS cur_value,
           (cur.home_value / prev.home_value - 1) * 100 AS yoy_pct
    FROM dbo.fact_home_values cur
    JOIN dbo.fact_home_values prev
      ON prev.RegionID = cur.RegionID AND prev.month_date = EOMONTH(cur.month_date, -12)
    WHERE cur.month_date = @latest
)
SELECT TOP 10 m.RegionName, m.SizeRank,
       CAST(y.cur_value AS decimal(12,0)) AS home_value,
       CAST(y.yoy_pct AS decimal(6,2)) AS yoy_pct
FROM yoy y
JOIN dbo.dim_metro m ON m.RegionID = y.RegionID
WHERE m.RegionType = 'msa'
ORDER BY y.yoy_pct DESC;

-- Q3: Bottom 10 metros by YoY home value growth in the latest month (where are prices falling fastest?)
WITH yoy AS (
    SELECT cur.RegionID, cur.home_value AS cur_value,
           (cur.home_value / prev.home_value - 1) * 100 AS yoy_pct
    FROM dbo.fact_home_values cur
    JOIN dbo.fact_home_values prev
      ON prev.RegionID = cur.RegionID AND prev.month_date = EOMONTH(cur.month_date, -12)
    WHERE cur.month_date = @latest
)
SELECT TOP 10 m.RegionName, m.SizeRank,
       CAST(y.cur_value AS decimal(12,0)) AS home_value,
       CAST(y.yoy_pct AS decimal(6,2)) AS yoy_pct
FROM yoy y
JOIN dbo.dim_metro m ON m.RegionID = y.RegionID
WHERE m.RegionType = 'msa'
ORDER BY y.yoy_pct ASC;

-- Q4: Regional trend - average metro home value per Census region per year, with YoY % (which region is growing fastest?)
-- Simple average across metros (not weighted by population); 2026 is a partial year (Jan-Sep).
WITH regional AS (
    SELECT CASE
             WHEN m.StateName IN ('CT','ME','MA','NH','RI','VT','NJ','NY','PA') THEN 'Northeast'
             WHEN m.StateName IN ('IL','IN','MI','OH','WI','IA','KS','MN','MO','NE','ND','SD') THEN 'Midwest'
             WHEN m.StateName IN ('DE','FL','GA','MD','NC','SC','VA','WV','DC','AL','KY','MS','TN','AR','LA','OK','TX') THEN 'South'
             WHEN m.StateName IN ('AZ','CO','ID','MT','NV','NM','UT','WY','AK','CA','HI','OR','WA') THEN 'West'
           END AS region,
           YEAR(f.month_date) AS yr,
           f.home_value
    FROM dbo.fact_home_values f
    JOIN dbo.dim_metro m ON m.RegionID = f.RegionID
    WHERE m.RegionType = 'msa' AND f.month_date >= '2019-01-01'
),
annual AS (
    SELECT region, yr, AVG(home_value) AS avg_value
    FROM regional
    GROUP BY region, yr
)
SELECT region, yr,
       CAST(avg_value AS decimal(12,0)) AS avg_home_value,
       CAST((avg_value / LAG(avg_value) OVER (PARTITION BY region ORDER BY yr) - 1) * 100 AS decimal(6,2)) AS yoy_pct
FROM annual
ORDER BY region, yr;

-- Q5: Top 10 metros by rent-to-price ratio in the latest month (where does renting out earn the most vs. the home price?)
SELECT TOP 10 m.RegionName, m.SizeRank,
       CAST(h.home_value AS decimal(12,0)) AS home_value,
       CAST(r.rent AS decimal(10,0)) AS monthly_rent,
       CAST(r.rent * 12 / h.home_value * 100 AS decimal(5,2)) AS rent_to_price_pct
FROM dbo.fact_home_values h
JOIN dbo.fact_rent r ON r.RegionID = h.RegionID AND r.month_date = h.month_date
JOIN dbo.dim_metro m ON m.RegionID = h.RegionID
WHERE h.month_date = @latest AND m.RegionType = 'msa'
ORDER BY r.rent * 12 / h.home_value DESC;

-- Q6: Bottom 10 metros by rent-to-price ratio in the latest month (where is buying priciest relative to rent?)
SELECT TOP 10 m.RegionName, m.SizeRank,
       CAST(h.home_value AS decimal(12,0)) AS home_value,
       CAST(r.rent AS decimal(10,0)) AS monthly_rent,
       CAST(r.rent * 12 / h.home_value * 100 AS decimal(5,2)) AS rent_to_price_pct
FROM dbo.fact_home_values h
JOIN dbo.fact_rent r ON r.RegionID = h.RegionID AND r.month_date = h.month_date
JOIN dbo.dim_metro m ON m.RegionID = h.RegionID
WHERE h.month_date = @latest AND m.RegionType = 'msa'
ORDER BY r.rent * 12 / h.home_value ASC;

-- Q7: How many metros beat the national YoY home value growth in the latest month? (breadth of the market vs. the headline number)
WITH yoy AS (
    SELECT cur.RegionID, (cur.home_value / prev.home_value - 1) * 100 AS yoy_pct
    FROM dbo.fact_home_values cur
    JOIN dbo.fact_home_values prev
      ON prev.RegionID = cur.RegionID AND prev.month_date = EOMONTH(cur.month_date, -12)
    WHERE cur.month_date = @latest
),
us_yoy AS (SELECT yoy_pct FROM yoy WHERE RegionID = 102001)
SELECT CAST(n.yoy_pct AS decimal(6,2)) AS national_yoy_pct,
       COUNT(*) AS metros_with_yoy,
       SUM(CASE WHEN y.yoy_pct > n.yoy_pct THEN 1 ELSE 0 END) AS metros_beating_national,
       CAST(100.0 * SUM(CASE WHEN y.yoy_pct > n.yoy_pct THEN 1 ELSE 0 END) / COUNT(*) AS decimal(5,1)) AS pct_beating_national,
       SUM(CASE WHEN y.yoy_pct < 0 THEN 1 ELSE 0 END) AS metros_with_falling_values
FROM yoy y
JOIN dbo.dim_metro m ON m.RegionID = y.RegionID AND m.RegionType = 'msa'
CROSS JOIN us_yoy n
GROUP BY n.yoy_pct;

-- Q8: Top 10 metros where rent growth is outpacing home value growth the most (YoY, latest month - rent pressure vs. price pressure)
WITH hv AS (
    SELECT cur.RegionID, (cur.home_value / prev.home_value - 1) * 100 AS home_yoy
    FROM dbo.fact_home_values cur
    JOIN dbo.fact_home_values prev
      ON prev.RegionID = cur.RegionID AND prev.month_date = EOMONTH(cur.month_date, -12)
    WHERE cur.month_date = @latest
),
rt AS (
    SELECT cur.RegionID, (cur.rent / prev.rent - 1) * 100 AS rent_yoy
    FROM dbo.fact_rent cur
    JOIN dbo.fact_rent prev
      ON prev.RegionID = cur.RegionID AND prev.month_date = EOMONTH(cur.month_date, -12)
    WHERE cur.month_date = @latest
)
SELECT TOP 10 m.RegionName, m.SizeRank,
       CAST(rt.rent_yoy AS decimal(6,2)) AS rent_yoy_pct,
       CAST(hv.home_yoy AS decimal(6,2)) AS home_value_yoy_pct,
       CAST(rt.rent_yoy - hv.home_yoy AS decimal(6,2)) AS rent_minus_home_growth
FROM hv
JOIN rt ON rt.RegionID = hv.RegionID
JOIN dbo.dim_metro m ON m.RegionID = hv.RegionID
WHERE m.RegionType = 'msa'
ORDER BY rt.rent_yoy - hv.home_yoy DESC;

-- Q9: For each metro, how did inventory and days to pending change alongside home values? (README question 3)
-- YoY in the latest home-value month. Inventory change is %, days-to-pending change is in days.
-- A metro without inventory or days-to-pending data for both months shows NULL in that column.
WITH hv AS (
    SELECT cur.RegionID, (cur.home_value / prev.home_value - 1) * 100 AS home_yoy
    FROM dbo.fact_home_values cur
    JOIN dbo.fact_home_values prev
      ON prev.RegionID = cur.RegionID AND prev.month_date = EOMONTH(cur.month_date, -12)
    WHERE cur.month_date = @latest
),
mk AS (
    SELECT cur.RegionID,
           (CAST(cur.inventory AS float) / NULLIF(prev.inventory, 0) - 1) * 100 AS inventory_yoy,
           cur.days_to_pending - prev.days_to_pending                           AS days_to_pending_change
    FROM dbo.fact_market cur
    JOIN dbo.fact_market prev
      ON prev.RegionID = cur.RegionID AND prev.month_date = EOMONTH(cur.month_date, -12)
    WHERE cur.month_date = @latest
)
SELECT m.RegionName, m.SizeRank,
       CAST(hv.home_yoy AS decimal(6,2))            AS home_value_yoy_pct,
       CAST(mk.inventory_yoy AS decimal(7,2))       AS inventory_yoy_pct,
       CAST(mk.days_to_pending_change AS decimal(6,1)) AS days_to_pending_change
FROM hv
JOIN dbo.dim_metro m ON m.RegionID = hv.RegionID
LEFT JOIN mk ON mk.RegionID = hv.RegionID
WHERE m.RegionType = 'msa'
ORDER BY hv.home_yoy DESC;

-- Q10: Across metros, do home values grow faster where inventory shrinks or homes sell faster? (README question 3)
-- Pearson correlation of each metro's home value YoY % with its inventory YoY % and with its days-to-pending change.
-- Near +1 or -1 = strong link; near 0 = little link. Each pair uses the metros that have both figures.
-- expect q10_metros_inventory: 893
-- expect q10_corr_home_vs_inventory: 0.0742
-- expect q10_metros_days: 562
-- expect q10_corr_home_vs_days: -0.0673
WITH hv AS (
    SELECT cur.RegionID, CAST((cur.home_value / prev.home_value - 1) * 100 AS float) AS home_yoy
    FROM dbo.fact_home_values cur
    JOIN dbo.fact_home_values prev
      ON prev.RegionID = cur.RegionID AND prev.month_date = EOMONTH(cur.month_date, -12)
    JOIN dbo.dim_metro m ON m.RegionID = cur.RegionID AND m.RegionType = 'msa'
    WHERE cur.month_date = @latest
),
mk AS (
    SELECT cur.RegionID,
           (CAST(cur.inventory AS float) / NULLIF(prev.inventory, 0) - 1) * 100 AS inventory_yoy,
           CAST(cur.days_to_pending - prev.days_to_pending AS float)            AS days_change
    FROM dbo.fact_market cur
    JOIN dbo.fact_market prev
      ON prev.RegionID = cur.RegionID AND prev.month_date = EOMONTH(cur.month_date, -12)
    WHERE cur.month_date = @latest
),
pairs AS (
    SELECT 'inventory YoY %' AS compared_with, hv.home_yoy AS x, mk.inventory_yoy AS y
    FROM hv JOIN mk ON mk.RegionID = hv.RegionID WHERE mk.inventory_yoy IS NOT NULL
    UNION ALL
    SELECT 'days to pending change', hv.home_yoy, mk.days_change
    FROM hv JOIN mk ON mk.RegionID = hv.RegionID WHERE mk.days_change IS NOT NULL
)
SELECT compared_with,
       COUNT(*) AS metros,
       CAST((COUNT(*) * SUM(x * y) - SUM(x) * SUM(y))
            / SQRT((COUNT(*) * SUM(x * x) - SQUARE(SUM(x))) * (COUNT(*) * SUM(y * y) - SQUARE(SUM(y))))
            AS decimal(6,4)) AS correlation_with_home_value_yoy
FROM pairs
GROUP BY compared_with;
GO
