/* 05_fact_rent.sql (was SQLQuery4.sql) - fact view over Zillow rents (ZORI): one row per metro per month.
   Run after 01_load_zillow.sql. */

USE [Housing Data];
GO

CREATE OR ALTER VIEW dbo.fact_rent AS

SELECT
    RegionID,
    month_date,
    rent
FROM dbo.ZORI_Rentals;
GO


-- Check: preview the first rows
SELECT TOP (10) *
FROM dbo.fact_rent;
GO
