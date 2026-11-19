
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



SELECT *
FROM dbo.dim_date
ORDER BY [Date];



SELECT
    COUNT(*) AS TotalDates,
    MIN([Date]) AS FirstDate,
    MAX([Date]) AS LastDate
FROM dbo.dim_date;