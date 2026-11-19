/* fact_market: Redfin market metrics keyed to Zillow's RegionID so they share dim_metro and dim_date.
   Run after redfin_load.sql and dim_metro.sql. Expected: 127,788 rows, 907 metros (Jan 2015 - Sep 2026).
   (Before dim_metro v2 added the 13 rent-only metros it was 125,955 rows / 894 metros.) */

USE [Housing Data];
GO

-- Crosswalk from Redfin metro name to Zillow RegionID.
-- Rule: strip Redfin's " metro area" suffix, then match dim_metro.RegionName exactly (903 metros).
-- Four metros are spelled differently, so they are mapped by RegionID instead.
-- The 39 Redfin-only names (metro divisions like Oakland, CA / Fort Worth, TX, and small towns) have no Zillow match and are dropped.
CREATE OR ALTER VIEW dbo.map_redfin_metro AS
WITH redfin_names AS (
    SELECT DISTINCT region_name FROM dbo.Redfin_Market_Raw
),
overrides AS (
    SELECT * FROM (VALUES
        (N'Ca' + NCHAR(241) + N'on City, CO metro area', 394437),   -- Zillow spells it 'Ca±on City, CO'
        (N'Espa' + NCHAR(241) + N'ola, NM metro area',   394574),   -- Zillow spells it 'Espa±ola, NM'
        (N'Honolulu, HI metro area',                     753924),   -- Zillow: 'Urban Honolulu, HI'
        (N'Winston-Salem, NC metro area',                395235)    -- Zillow: 'Winston, NC'
    ) AS o(region_name, RegionID)
)
SELECT r.region_name AS redfin_name,
       COALESCE(o.RegionID, m.RegionID) AS RegionID
FROM redfin_names r
LEFT JOIN overrides o ON o.region_name = r.region_name
LEFT JOIN dbo.dim_metro m
       ON m.RegionName = REPLACE(r.region_name, N' metro area', N'')
      AND m.RegionType = 'msa'
WHERE COALESCE(o.RegionID, m.RegionID) IS NOT NULL;
GO

-- Fact table for market health: typed Redfin metrics plus % price drops, one row per metro per month.
-- month_date uses the month-end date (EOMONTH) to match fact_home_values / fact_rent and dim_date.
CREATE OR ALTER VIEW dbo.fact_market AS
SELECT
    x.RegionID,
    EOMONTH(TRY_CONVERT(date, m.period_begin))           AS month_date,
    TRY_CONVERT(int,           m.homes_sold)             AS homes_sold,
    TRY_CONVERT(decimal(12,2), m.median_sale_price)      AS median_sale_price,
    TRY_CONVERT(int,           m.median_dom)             AS median_days_on_market,
    TRY_CONVERT(decimal(6,2),  m.avg_sale_to_list)       AS avg_sale_to_list_pct,
    TRY_CONVERT(decimal(6,2),  m.pct_sold_above_list)    AS pct_sold_above_list,
    TRY_CONVERT(int,           m.new_listings)           AS new_listings,
    TRY_CONVERT(int,           m.inventory)              AS inventory,
    TRY_CONVERT(decimal(6,1),  m.months_of_supply)       AS months_of_supply,
    TRY_CONVERT(decimal(6,2),  p.pct_price_drops)        AS pct_active_with_price_drops
FROM dbo.Redfin_Market_Raw m
JOIN dbo.map_redfin_metro x
  ON x.redfin_name = m.region_name
LEFT JOIN dbo.Redfin_PriceDrops_Raw p
  ON p.region_name = m.region_name
 AND p.period_begin = m.period_begin;
GO

-- Check 1: row count, metro count, date range (expect 127,788 / 907 / 2015-01-31 to 2026-09-30)
SELECT COUNT(*) AS row_count, COUNT(DISTINCT RegionID) AS metros,
       MIN(month_date) AS first_month, MAX(month_date) AS last_month
FROM dbo.fact_market;

-- Check 2: no duplicate metro-months (expect 0 rows)
SELECT RegionID, month_date, COUNT(*) AS n
FROM dbo.fact_market
GROUP BY RegionID, month_date
HAVING COUNT(*) > 1;

-- Check 3: every month_date exists in dim_date (expect 0)
SELECT COUNT(*) AS rows_without_date
FROM dbo.fact_market f
WHERE NOT EXISTS (SELECT 1 FROM dbo.dim_date d WHERE d.[Date] = f.month_date);

-- Check 4: hand-check against the CSV, Atlanta Sep 2026
-- CSV says: homes sold 5862, median sale price 389106, DOM 61, inventory 29108, price drops 21.27
SELECT d.RegionName, f.*
FROM dbo.fact_market f
JOIN dbo.dim_metro d ON d.RegionID = f.RegionID
WHERE d.RegionName = 'Atlanta, GA' AND f.month_date = '2026-09-30';
GO
