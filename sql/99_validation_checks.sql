/*
  99_validation_checks.sql
  Compares SQL results with reference numbers computed independently from the raw CSVs
  (Python, see logs/tests/). Lists every check, then fails the run if any check fails.
  Run: sqlcmd -S localhost -E -C -b -I -i sql/99_validation_checks.sql
*/
SET NOCOUNT ON;
USE HousingMarket;

-- One row per check; result is computed so a check can never be marked PASS by hand.
DROP TABLE IF EXISTS #check;
CREATE TABLE #check (
    check_name NVARCHAR(200) NOT NULL,
    expected   NVARCHAR(100) NOT NULL,
    actual     NVARCHAR(100) NULL,
    result AS CASE WHEN expected = actual THEN 'PASS' ELSE 'FAIL' END
);

/* ---------- Raw load (Task 4) ---------- */

-- Row counts of the four wide tables must match the CSV data rows.
INSERT #check SELECT 'raw.zhvi_wide rows', '895', (SELECT COUNT(*) FROM raw.zhvi_wide);
INSERT #check SELECT 'raw.zori_wide rows', '741', (SELECT COUNT(*) FROM raw.zori_wide);
INSERT #check SELECT 'raw.inventory_wide rows', '928', (SELECT COUNT(*) FROM raw.inventory_wide);
INSERT #check SELECT 'raw.days_to_pending_wide rows', '716', (SELECT COUNT(*) FROM raw.days_to_pending_wide);

-- Month columns must match the CSV headers (names that look like dates).
INSERT #check SELECT 'zhvi month columns', '321',
    (SELECT COUNT(*) FROM sys.columns WHERE object_id = OBJECT_ID('raw.zhvi_wide') AND name LIKE '[12][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]');
INSERT #check SELECT 'zori month columns', '141',
    (SELECT COUNT(*) FROM sys.columns WHERE object_id = OBJECT_ID('raw.zori_wide') AND name LIKE '[12][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]');
INSERT #check SELECT 'inventory month columns', '104',
    (SELECT COUNT(*) FROM sys.columns WHERE object_id = OBJECT_ID('raw.inventory_wide') AND name LIKE '[12][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]');
INSERT #check SELECT 'days_to_pending month columns', '104',
    (SELECT COUNT(*) FROM sys.columns WHERE object_id = OBJECT_ID('raw.days_to_pending_wide') AND name LIKE '[12][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]');

-- A quoted name with a comma must load as one value (Review Focus 2).
INSERT #check SELECT 'name of 394913', 'New York, NY', (SELECT RegionName FROM raw.zhvi_wide WHERE RegionID = 394913);

-- The byte-order mark must be stripped from the first header name (Review Focus 2).
INSERT #check SELECT 'first column of raw.zhvi_wide', 'RegionID',
    (SELECT name FROM sys.columns WHERE object_id = OBJECT_ID('raw.zhvi_wide') AND column_id = 1);

-- The last month column must hold no carriage return from Windows line endings (Review Focus 2).
INSERT #check SELECT 'US zhvi last month value', '366157.1523869674', (SELECT [2026-09-30] FROM raw.zhvi_wide WHERE RegionID = 102001);
INSERT #check SELECT 'US inventory last month value', '1404950.0', (SELECT [2026-10-31] FROM raw.inventory_wide WHERE RegionID = 102001);

/* ---------- Core tables (Task 5) ---------- */

-- Every region from all four files appears once.
INSERT #check SELECT 'core.metro rows', '928', (SELECT COUNT(*) FROM core.metro);

-- One row per region-month that has any value, up to the latest home-value month (decision 0004).
INSERT #check SELECT 'core.metro_month rows', '240674', (SELECT COUNT(*) FROM core.metro_month);

-- Non-empty values per measure must equal the non-empty CSV cells (supply files counted to 2026-09-30).
INSERT #check SELECT 'home_value non-null', '238029', (SELECT COUNT(home_value) FROM core.metro_month);
INSERT #check SELECT 'rent_monthly non-null', '53977', (SELECT COUNT(rent_monthly) FROM core.metro_month);
INSERT #check SELECT 'for_sale_inventory non-null', '94391', (SELECT COUNT(for_sale_inventory) FROM core.metro_month);
INSERT #check SELECT 'days_to_pending non-null', '50769', (SELECT COUNT(days_to_pending) FROM core.metro_month);

-- Spot values for the U.S. row, rounded to cents.
INSERT #check SELECT 'US home_value 2026-09', '366157.15',
    (SELECT CAST(home_value AS NVARCHAR(30)) FROM core.metro_month WHERE metro_id = 102001 AND month_end = '2026-09-30');
INSERT #check SELECT 'US rent 2026-09', '1931.94',
    (SELECT CAST(rent_monthly AS NVARCHAR(30)) FROM core.metro_month WHERE metro_id = 102001 AND month_end = '2026-09-30');
INSERT #check SELECT 'US inventory 2026-09', '1407575',
    (SELECT CAST(for_sale_inventory AS NVARCHAR(30)) FROM core.metro_month WHERE metro_id = 102001 AND month_end = '2026-09-30');
INSERT #check SELECT 'US days_to_pending 2026-09', '56',
    (SELECT CAST(days_to_pending AS NVARCHAR(30)) FROM core.metro_month WHERE metro_id = 102001 AND month_end = '2026-09-30');

-- The primary key should make duplicates impossible; check anyway.
INSERT #check SELECT 'duplicate metro_month keys', '0',
    (SELECT COUNT(*) FROM (SELECT metro_id, month_end FROM core.metro_month GROUP BY metro_id, month_end HAVING COUNT(*) > 1) AS d);

-- No month after the latest home-value month (decision 0004).
INSERT #check SELECT 'latest month_end', '2026-09-30', (SELECT CONVERT(NVARCHAR(10), MAX(month_end), 23) FROM core.metro_month);

/* ---------- Question 1: home value growth (Task 6) ---------- */

-- Year-over-year % for the U.S. and the two extremes among the 100 largest metros, Sep 2026.
INSERT #check SELECT 'US yoy 2026-09', '1.19',
    (SELECT CAST(CAST(ROUND(yoy_pct, 2) AS DECIMAL(9, 2)) AS NVARCHAR(30)) FROM rpt.v_home_value_growth WHERE metro_id = 102001 AND month_end = '2026-09-30');
INSERT #check SELECT 'Syracuse yoy 2026-09', '6.62',
    (SELECT CAST(CAST(ROUND(yoy_pct, 2) AS DECIMAL(9, 2)) AS NVARCHAR(30)) FROM rpt.v_home_value_growth WHERE metro_id = 395143 AND month_end = '2026-09-30');
INSERT #check SELECT 'Austin yoy 2026-09', '-4.31',
    (SELECT CAST(CAST(ROUND(yoy_pct, 2) AS DECIMAL(9, 2)) AS NVARCHAR(30)) FROM rpt.v_home_value_growth WHERE metro_id = 394355 AND month_end = '2026-09-30');

-- Fastest and slowest of the large metros (size_rank 1-100) in the latest month.
INSERT #check SELECT 'top large metro 2026-09', 'Syracuse, NY',
    (SELECT TOP (1) m.metro_name FROM rpt.v_home_value_growth AS g JOIN core.metro AS m ON m.metro_id = g.metro_id
     WHERE g.month_end = '2026-09-30' AND m.size_rank BETWEEN 1 AND 100 AND g.yoy_pct IS NOT NULL ORDER BY g.yoy_pct DESC);
INSERT #check SELECT 'bottom large metro 2026-09', 'Austin, TX',
    (SELECT TOP (1) m.metro_name FROM rpt.v_home_value_growth AS g JOIN core.metro AS m ON m.metro_id = g.metro_id
     WHERE g.month_end = '2026-09-30' AND m.size_rank BETWEEN 1 AND 100 AND g.yoy_pct IS NOT NULL ORDER BY g.yoy_pct ASC);
INSERT #check SELECT 'large metros with yoy 2026-09', '97',
    (SELECT COUNT(*) FROM rpt.v_home_value_growth AS g JOIN core.metro AS m ON m.metro_id = g.metro_id
     WHERE g.month_end = '2026-09-30' AND m.size_rank BETWEEN 1 AND 100 AND g.yoy_pct IS NOT NULL);

-- Rows with a yoy value, counted independently in Python (gaps must give NULL, Review Focus 3).
INSERT #check SELECT 'rows with home value yoy', '226857', (SELECT COUNT(yoy_pct) FROM rpt.v_home_value_growth);

-- No yoy value may exist where the month exactly 12 months back has no home value (Review Focus 3).
INSERT #check SELECT 'gap months with yoy', '0',
    (SELECT COUNT(*) FROM rpt.v_home_value_growth AS g
     WHERE g.yoy_pct IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM core.metro_month AS p
                       WHERE p.metro_id = g.metro_id AND p.month_end = EOMONTH(g.month_end, -12) AND p.home_value IS NOT NULL));

/* ---------- Question 2: rent-to-price (Task 7) ---------- */

-- Only metro-months with both a home value and a rent appear.
INSERT #check SELECT 'rent_to_price rows', '53095', (SELECT COUNT(*) FROM rpt.v_rent_to_price);
INSERT #check SELECT 'rent_to_price rows 2026-09', '728', (SELECT COUNT(*) FROM rpt.v_rent_to_price WHERE month_end = '2026-09-30');

-- Yearly rent as a % of home value for the U.S., Sep 2026.
INSERT #check SELECT 'US rent_to_price 2026-09', '6.33',
    (SELECT CAST(CAST(ROUND(rent_to_price_pct, 2) AS DECIMAL(9, 2)) AS NVARCHAR(30)) FROM rpt.v_rent_to_price WHERE metro_id = 102001 AND month_end = '2026-09-30');

-- Highest and lowest among the 100 largest metros, Sep 2026, as "name (pct)".
INSERT #check SELECT 'highest large metro rent_to_price', 'Jackson, MS (8.31)',
    (SELECT TOP (1) m.metro_name + N' (' + CAST(CAST(ROUND(r.rent_to_price_pct, 2) AS DECIMAL(9, 2)) AS NVARCHAR(30)) + N')'
     FROM rpt.v_rent_to_price AS r JOIN core.metro AS m ON m.metro_id = r.metro_id
     WHERE r.month_end = '2026-09-30' AND m.size_rank BETWEEN 1 AND 100 ORDER BY r.rent_to_price_pct DESC);
INSERT #check SELECT 'lowest large metro rent_to_price', 'San Jose, CA (3.00)',
    (SELECT TOP (1) m.metro_name + N' (' + CAST(CAST(ROUND(r.rent_to_price_pct, 2) AS DECIMAL(9, 2)) AS NVARCHAR(30)) + N')'
     FROM rpt.v_rent_to_price AS r JOIN core.metro AS m ON m.metro_id = r.metro_id
     WHERE r.month_end = '2026-09-30' AND m.size_rank BETWEEN 1 AND 100 ORDER BY r.rent_to_price_pct ASC);

/* ---------- Question 3: supply vs price (Task 8) ---------- */

-- One row per metro-month with inventory or days to pending; yoy only where the exact month a year back exists.
INSERT #check SELECT 'supply rows', '94418', (SELECT COUNT(*) FROM rpt.v_supply_vs_price);
INSERT #check SELECT 'rows with inventory yoy', '83188', (SELECT COUNT(inventory_yoy_pct) FROM rpt.v_supply_vs_price);

-- U.S. values, Sep 2026.
INSERT #check SELECT 'US inventory_yoy 2026-09', '2.5063',
    (SELECT CAST(inventory_yoy_pct AS NVARCHAR(30)) FROM rpt.v_supply_vs_price WHERE metro_id = 102001 AND month_end = '2026-09-30');
INSERT #check SELECT 'US days_to_pending 2026-09 (change)', '56 (2)',
    (SELECT CONCAT(days_to_pending, N' (', days_to_pending_yoy_change, N')') FROM rpt.v_supply_vs_price WHERE metro_id = 102001 AND month_end = '2026-09-30');

-- Pearson correlations across large metros, Sep 2026 (computed independently in Python).
INSERT #check SELECT 'correlation metros 2026-09', '97',
    (SELECT CAST(metros AS NVARCHAR(30)) FROM rpt.v_supply_price_correlation WHERE month_end = '2026-09-30');
INSERT #check SELECT 'r inventory vs price 2026-09', '0.2968',
    (SELECT CAST(r_inventory_vs_price AS NVARCHAR(30)) FROM rpt.v_supply_price_correlation WHERE month_end = '2026-09-30');
INSERT #check SELECT 'r days vs price 2026-09', '0.0624',
    (SELECT CAST(r_days_vs_price AS NVARCHAR(30)) FROM rpt.v_supply_price_correlation WHERE month_end = '2026-09-30');

/* ---------- Report ---------- */

-- Show every check, failures first.
SELECT check_name, expected, actual, result FROM #check ORDER BY result, check_name;

-- Fail the sqlcmd run (exit code 1 with -b) if any check failed.
IF EXISTS (SELECT 1 FROM #check WHERE result = 'FAIL')
    THROW 50001, 'Validation failed', 1;
PRINT 'All validation checks passed.';
