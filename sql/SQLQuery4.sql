CREATE OR ALTER VIEW dbo.fact_rent AS

SELECT
    RegionID,
    month_date,
    rent
FROM dbo.ZORI_Rentals;
GO


SELECT *
FROM dbo.fact_rent;