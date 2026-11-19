/* 06_fact_market.sql (was sql/fact_market.sql) - fact_market: Zillow market-health metrics,
   one row per metro per month, keyed by RegionID and month-end date like fact_home_values and fact_rent.

   Replaces the earlier Redfin version (the owner dropped Redfin on 2026-11-19). Columns:
     inventory        - Zillow for-sale inventory (Metro_invt_fs_uc_sfrcondo_sm_month.csv)
     days_to_pending  - Zillow mean days to pending, i.e. how long listings take to go under contract
                        (Metro_mean_doz_pending_uc_sfrcondo_sm_month.csv)

   Inventory covers more metros and months than days to pending, so the two are FULL JOINed:
   a metro-month with inventory but no days-to-pending figure keeps its row, with days_to_pending NULL.
   The Power BI report doesn't use the old Redfin columns, so nothing in it breaks.
   Run after 01_load_zillow.sql, 02_dim_metro.sql and 03_dim_date.sql. */

USE [Housing Data];
GO

-- Note: the old Redfin crosswalk view dbo.map_redfin_metro and the Redfin tables are left in place;
-- nothing here uses them. The owner can drop them by hand if they're no longer wanted.

CREATE OR ALTER VIEW dbo.fact_market AS
SELECT
    COALESCE(i.RegionID, d.RegionID)     AS RegionID,
    COALESCE(i.month_date, d.month_date) AS month_date,
    i.inventory,
    d.days_to_pending
FROM dbo.Inventory_ForSale AS i
FULL OUTER JOIN dbo.DaysToPending AS d
  ON d.RegionID = i.RegionID
 AND d.month_date = i.month_date;
GO

-- Check 1: row count, metro count, date range
-- expect fact_market_rows: 95346
-- expect fact_market_metros: 928
-- expect fact_market_first_month: 2018-03-31
-- expect fact_market_last_month: 2026-10-31
SELECT COUNT(*) AS row_count, COUNT(DISTINCT RegionID) AS metros,
       MIN(month_date) AS first_month, MAX(month_date) AS last_month
FROM dbo.fact_market;

-- Check 2: rows that have both figures (the rest have inventory only, or days to pending only)
-- expect fact_market_rows_with_both: 51457
SELECT COUNT(*) AS rows_with_both
FROM dbo.fact_market
WHERE inventory IS NOT NULL AND days_to_pending IS NOT NULL;

-- Check 3: no duplicate metro-months (expect 0 rows)
SELECT RegionID, month_date, COUNT(*) AS n
FROM dbo.fact_market
GROUP BY RegionID, month_date
HAVING COUNT(*) > 1;

-- Check 4: every month_date exists in dim_date and every metro in dim_metro (expect 0 and 0)
SELECT
    (SELECT COUNT(*) FROM dbo.fact_market f
     WHERE NOT EXISTS (SELECT 1 FROM dbo.dim_date d WHERE d.[Date] = f.month_date))    AS rows_without_date,
    (SELECT COUNT(*) FROM dbo.fact_market f
     WHERE NOT EXISTS (SELECT 1 FROM dbo.dim_metro m WHERE m.RegionID = f.RegionID))   AS rows_without_metro;

-- Check 5: hand-check against the CSVs, Atlanta Sep 2026
-- expect atlanta_inventory_2026_09: 33948
-- expect atlanta_days_to_pending_2026_09: 72
SELECT m.RegionName, f.*
FROM dbo.fact_market f
JOIN dbo.dim_metro m ON m.RegionID = f.RegionID
WHERE m.RegionName = N'Atlanta, GA' AND f.month_date = '2026-09-30';
GO
