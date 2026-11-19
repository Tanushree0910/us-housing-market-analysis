/* dim_metro v2: one row per metro, covering every metro in EITHER Zillow table.
   v1 (SQLQuery1.sql) was built from ZHVI_HomeValue only, so 13 metros that exist only in ZORI_Rentals
   (e.g. Dayton OH, Poughkeepsie NY) had rent rows with no matching metro (shown as (Blank) in Power BI).
   Check run first: the 728 metros in both tables have identical name/type/state/rank, so no duplicate RegionIDs.
   Expected: 908 rows (895 + 13), RegionID unique. */

USE [Housing Data];
GO

-- Metro dimension: all ZHVI metros, plus metros that appear only in the rent data
CREATE OR ALTER VIEW dbo.dim_metro AS
SELECT DISTINCT RegionID, RegionName, RegionType, StateName, SizeRank
FROM dbo.ZHVI_HomeValue
UNION ALL
SELECT DISTINCT RegionID, RegionName, RegionType, StateName, SizeRank
FROM dbo.ZORI_Rentals
WHERE RegionID NOT IN (SELECT RegionID FROM dbo.ZHVI_HomeValue);
GO

-- Check 1: total rows and unique keys (expect 908 rows, 908 distinct RegionIDs)
SELECT COUNT(*) AS row_count, COUNT(DISTINCT RegionID) AS distinct_region_ids FROM dbo.dim_metro;

-- Check 2: rent metros without a dim_metro row (expect 0)
SELECT COUNT(*) AS rent_ids_missing_from_dim_metro
FROM (SELECT DISTINCT RegionID FROM dbo.ZORI_Rentals EXCEPT SELECT RegionID FROM dbo.dim_metro) x;

-- Check 3: home value metros without a dim_metro row (expect 0)
SELECT COUNT(*) AS home_ids_missing_from_dim_metro
FROM (SELECT DISTINCT RegionID FROM dbo.ZHVI_HomeValue EXCEPT SELECT RegionID FROM dbo.dim_metro) x;
GO
