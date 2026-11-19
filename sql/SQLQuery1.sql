USE [Housing Data];
GO

SELECT
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME IN ('ZHVI_HomeValue', 'ZORI_Rentals')
ORDER BY TABLE_NAME, ORDINAL_POSITION;


USE [Housing Data];
GO

CREATE OR ALTER VIEW dbo.dim_metro AS

SELECT DISTINCT
    RegionID,
    RegionName,
    RegionType,
    StateName,
    SizeRank
FROM dbo.ZHVI_HomeValue;


SELECT *
FROM dbo.dim_metro;