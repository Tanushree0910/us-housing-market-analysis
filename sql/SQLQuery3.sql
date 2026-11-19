CREATE OR ALTER VIEW dbo.fact_home_values AS

SELECT
    RegionID,
    month_date,
    home_value
FROM dbo.ZHVI_HomeValue;
GO


SELECT *
FROM dbo.fact_home_values;

