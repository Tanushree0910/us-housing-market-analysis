/* 04_fact_home_values.sql (was SQLQuery3.sql) - fact view over Zillow home values (ZHVI): one row per metro per month.
   Run after 01_load_zillow.sql. */

USE [Housing Data];
GO

CREATE OR ALTER VIEW dbo.fact_home_values AS

SELECT
    RegionID,
    month_date,
    home_value
FROM dbo.ZHVI_HomeValue;
GO


-- Check: preview the first rows
SELECT TOP (10) *
FROM dbo.fact_home_values;
GO
