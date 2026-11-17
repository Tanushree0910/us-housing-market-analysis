/*
  01_create_database.sql
  Creates the HousingMarket database and its three schemas:
    raw  - wide copies of the Zillow CSVs, exactly as loaded
    core - clean long tables (one row per metro per month)
    rpt  - views for analysis and Power BI
  Safe to re-run: every object is created only if it is missing.
  Run: sqlcmd -S localhost -E -C -b -I -i sql/01_create_database.sql
*/
SET NOCOUNT ON;

-- Create the database once; re-runs leave existing data alone.
IF DB_ID(N'HousingMarket') IS NULL
    CREATE DATABASE HousingMarket;
GO

USE HousingMarket;
GO

-- CREATE SCHEMA must be the only statement in its batch, so it runs through EXEC.
IF SCHEMA_ID(N'raw') IS NULL  EXEC (N'CREATE SCHEMA [raw]');
IF SCHEMA_ID(N'core') IS NULL EXEC (N'CREATE SCHEMA [core]');
IF SCHEMA_ID(N'rpt') IS NULL  EXEC (N'CREATE SCHEMA [rpt]');
GO

-- Confirm the three schemas exist.
SELECT name AS schema_name FROM sys.schemas WHERE name IN (N'raw', N'core', N'rpt') ORDER BY name;
