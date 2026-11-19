/* 03_dim_date.sql (was SQLQuery2.sql) - dim_date: one row per calendar day, from Jan 1 of the first
   year to Dec 31 of the last year found in any of the four Zillow tables. Mark it as the date table
   in Power BI. Run after 01_load_zillow.sql. */
USE [Housing Data];
GO

CREATE OR ALTER VIEW dbo.dim_date AS

WITH DateRange AS
(
    SELECT
    DATEFROMPARTS(YEAR(MIN(month_date)), 1, 1)   AS MinDate,  -- Jan 1 of the first year
    DATEFROMPARTS(YEAR(MAX(month_date)), 12, 31) AS MaxDate   -- Dec 31 of the last year
    FROM
    (
        SELECT month_date FROM dbo.ZHVI_HomeValue
        UNION ALL
        SELECT month_date FROM dbo.ZORI_Rentals
        UNION ALL
        SELECT month_date FROM dbo.Inventory_ForSale
        UNION ALL
        SELECT month_date FROM dbo.DaysToPending
    ) AS AllDates
),

Numbers AS
(
    SELECT TOP (
        SELECT DATEDIFF(DAY, MinDate, MaxDate) + 1
        FROM DateRange
    )
        ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n
    FROM sys.all_objects a
    CROSS JOIN sys.all_objects b
),

Calendar AS
(
    SELECT
        DATEADD(DAY, n, MinDate) AS [Date]
    FROM DateRange
    CROSS JOIN Numbers
)

SELECT
    CONVERT(INT, CONVERT(CHAR(8), [Date], 112)) AS DateKey,
    [Date],
    YEAR([Date]) AS [Year],
    MONTH([Date]) AS MonthNumber,
    DATENAME(MONTH, [Date]) AS MonthName,
    DATEPART(QUARTER, [Date]) AS QuarterNumber,
    CONCAT('Q', DATEPART(QUARTER, [Date])) AS QuarterName
FROM Calendar;
GO



-- Check 1: first day, last day and number of days (no gaps)
-- expect dim_date_first: 2000-01-01
-- expect dim_date_last: 2026-12-31
-- expect dim_date_days: 9862
SELECT
    COUNT(*) AS TotalDates,
    MIN([Date]) AS FirstDate,
    MAX([Date]) AS LastDate
FROM dbo.dim_date;
GO
