/* 02_dim_metro.sql (was sql/dim_metro.sql) - dim_metro v3: one row per metro, covering every metro
   in ANY of the four Zillow tables (home values, rents, inventory, days to pending).

   History:
   - v1 (SQLQuery1.sql, retired) was built from ZHVI_HomeValue only.
   - v2 added the 13 metros that exist only in ZORI_Rentals (e.g. Dayton OH, Poughkeepsie NY),
     which had rent rows with no matching metro (shown as (Blank) in Power BI). 908 rows.
   - v3 adds Inventory_ForSale and DaysToPending (loaded by 01_load_zillow.sql), which cover more
     metros: 928 in total.

   Each metro's name, type, state and rank are identical in every Zillow file (checked by
   tests/test_sql_expectations.py), so one row per RegionID is safe. If a metro appears in several
   tables, the row is taken from the first in this order: home values, rents, inventory, days to pending.
   Run after 01_load_zillow.sql. */

USE [Housing Data];
GO

CREATE OR ALTER VIEW dbo.dim_metro AS
WITH all_metros AS (
    SELECT DISTINCT RegionID, RegionName, RegionType, StateName, SizeRank, 1 AS source_order FROM dbo.ZHVI_HomeValue
    UNION ALL
    SELECT DISTINCT RegionID, RegionName, RegionType, StateName, SizeRank, 2 FROM dbo.ZORI_Rentals
    UNION ALL
    SELECT DISTINCT RegionID, RegionName, RegionType, StateName, SizeRank, 3 FROM dbo.Inventory_ForSale
    UNION ALL
    SELECT DISTINCT RegionID, RegionName, RegionType, StateName, SizeRank, 4 FROM dbo.DaysToPending
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY RegionID ORDER BY source_order) AS pick
    FROM all_metros
)
SELECT RegionID, RegionName, RegionType, StateName, SizeRank
FROM ranked
WHERE pick = 1;
GO

-- Check 1: total rows and unique keys
-- expect dim_metro_rows: 928
-- expect dim_metro_distinct_ids: 928
SELECT COUNT(*) AS row_count, COUNT(DISTINCT RegionID) AS distinct_region_ids FROM dbo.dim_metro;

-- Check 2: metros in any table without a dim_metro row
-- expect metros_missing_from_dim_metro: 0
SELECT COUNT(*) AS metros_missing_from_dim_metro
FROM (
    SELECT RegionID FROM dbo.ZHVI_HomeValue
    UNION SELECT RegionID FROM dbo.ZORI_Rentals
    UNION SELECT RegionID FROM dbo.Inventory_ForSale
    UNION SELECT RegionID FROM dbo.DaysToPending
    EXCEPT SELECT RegionID FROM dbo.dim_metro
) AS x;
GO
