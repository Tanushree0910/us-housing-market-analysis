/* 01_load_zillow.sql - load Zillow's wide monthly CSVs into long tables in [Housing Data].

   Zillow files are wide: 5 ID columns (RegionID, SizeRank, RegionName, RegionType, StateName)
   then one column per month-end date. Each table here has one row per metro per month,
   keeping only months that have a value:
       RegionID, RegionName, RegionType, StateName, SizeRank, month_date, <value column>

   Tables (run order doesn't matter between them):
     dbo.ZHVI_HomeValue    home_value       Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv
     dbo.ZORI_Rentals      rent             Metro_zori_uc_sfrcondomfr_sm_month.csv
     dbo.Inventory_ForSale inventory        Metro_invt_fs_uc_sfrcondo_sm_month.csv
     dbo.DaysToPending     days_to_pending  Metro_mean_doz_pending_uc_sfrcondo_sm_month.csv

   Safe to re-run: a table that already has data is left exactly as it is (raw data is never
   changed - CONSTITUTION.md Article 2). ZHVI_HomeValue and ZORI_Rentals already exist in the
   owner's database, so on that database only the two new tables are created. Each table is
   created and filled in one go, so an interrupted run leaves either a full table or none
   (an empty table from an older interrupted run is reloaded).
   To reload a table from a newer download, the owner drops it by hand first.

   BEFORE RUNNING: check @data_folder below points at the repo's data folder on this computer.
   SQL Server reads the files itself. Signed in with Windows authentication (the SSMS default),
   it reads them as you, so C:\Projects\... works. Keep the path free of OneDrive folders.
   The script also leaves a helper procedure, dbo.load_zillow_wide, in the database for reuse. */

USE [Housing Data];
GO

-- Loads one wide Zillow CSV into dbo.<@table> as a long table.
-- A table that already has data is left unchanged. An empty one (left by an interrupted load) is reloaded.
-- The table is created and filled in one transaction, so a failed load leaves nothing half-done.
CREATE OR ALTER PROCEDURE dbo.load_zillow_wide
    @file         nvarchar(400),
    @table        sysname,
    @value_column sysname
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;  -- any error undoes the whole load

    DECLARE @sql nvarchar(max), @content nvarchar(max), @header nvarchar(max), @message nvarchar(2048),
            @existing bigint,
            -- The path as a quoted SQL text literal. (QUOTENAME would return NULL for paths over 128 characters.)
            @file_literal nvarchar(1000) = N'''' + REPLACE(@file, N'''', N'''''') + N'''';

    IF OBJECT_ID(N'dbo.' + QUOTENAME(@table), N'U') IS NOT NULL
    BEGIN
        SELECT @existing = SUM(p.rows) FROM sys.partitions AS p
        WHERE p.object_id = OBJECT_ID(N'dbo.' + QUOTENAME(@table)) AND p.index_id IN (0, 1);
        IF @existing > 0
        BEGIN
            PRINT CONCAT(N'dbo.', @table, N' already has data - left unchanged.');
            RETURN;
        END;
        PRINT CONCAT(N'dbo.', @table, N' exists but is empty (an earlier load was interrupted) - reloading it.');
        SET @sql = N'DROP TABLE dbo.' + QUOTENAME(@table) + N';';  -- empty, so no data is lost
        EXEC sp_executesql @sql;
    END;

    -- 1. Read the file once to get its header line (also proves SQL Server can read the file).
    BEGIN TRY
        SET @sql = N'SELECT @content = BulkColumn FROM OPENROWSET(BULK ' + @file_literal + N', SINGLE_CLOB) AS f;';
        EXEC sp_executesql @sql, N'@content nvarchar(max) OUTPUT', @content = @content OUTPUT;
    END TRY
    BEGIN CATCH
        SET @message = CONCAT(N'SQL Server can''t read ', @file,
            N'. Check @data_folder in the "Load the four Zillow files" section of 01_load_zillow.sql, and that the file is there. ',
            N'If the details say access denied, give your Windows account read access to that folder ',
            N'(right-click the folder > Properties > Security > Edit). Details: ', ERROR_MESSAGE());
        THROW 50001, @message, 1;
    END CATCH;

    IF @content IS NULL OR LEN(@content) = 0
    BEGIN
        SET @message = CONCAT(N'The file ', @file, N' is empty or could not be read.');
        THROW 50003, @message, 1;
    END;

    SET @header = REPLACE(LEFT(@content, CHARINDEX(NCHAR(10), @content + NCHAR(10)) - 1), NCHAR(13), N'');

    -- 2. Header columns in order. Months are the columns whose name is a date.
    DECLARE @columns TABLE (ordinal int PRIMARY KEY, name nvarchar(400));
    INSERT INTO @columns (ordinal, name)
    SELECT ordinal, LTRIM(RTRIM(value)) FROM STRING_SPLIT(@header, N',', 1);

    DECLARE @col_id int   = (SELECT ordinal FROM @columns WHERE name = N'RegionID'),
            @col_rank int = (SELECT ordinal FROM @columns WHERE name = N'SizeRank'),
            @col_name int = (SELECT ordinal FROM @columns WHERE name = N'RegionName'),
            @col_type int = (SELECT ordinal FROM @columns WHERE name = N'RegionType'),
            @col_state int = (SELECT ordinal FROM @columns WHERE name = N'StateName');
    IF @col_id IS NULL OR @col_rank IS NULL OR @col_name IS NULL OR @col_type IS NULL OR @col_state IS NULL
        THROW 50002, N'The file''s header is missing one of RegionID, SizeRank, RegionName, RegionType, StateName.', 1;

    -- 3. Staging table with one text column per CSV column (c1, c2, ...), then bulk load.
    --    MAXERRORS = 0: any malformed row stops the load instead of being skipped quietly.
    DROP TABLE IF EXISTS dbo.stage_zillow_load;
    SELECT @sql = N'CREATE TABLE dbo.stage_zillow_load ('
                + STRING_AGG(CAST(CONCAT(N'c', ordinal, N' nvarchar(400) NULL') AS nvarchar(max)), N', ')
                  WITHIN GROUP (ORDER BY ordinal)
                + N');'
    FROM @columns;
    EXEC sp_executesql @sql;

    SET @sql = N'BULK INSERT dbo.stage_zillow_load FROM ' + @file_literal + N'
        WITH (FORMAT = ''CSV'', FIRSTROW = 2, FIELDQUOTE = ''"'', FIELDTERMINATOR = '','',
              ROWTERMINATOR = ''0x0a'', CODEPAGE = ''65001'', MAXERRORS = 0, TABLOCK);';
    EXEC sp_executesql @sql;

    -- 4. Create the long table and unpivot the month columns into it, skipping blank cells, in one transaction.
    --    Windows line endings leave a CHAR(13) on the last column, so it is stripped.
    DECLARE @months nvarchar(max);
    SELECT @months = STRING_AGG(CAST(CONCAT(N'(''', name, N''', s.c', ordinal, N')') AS nvarchar(max)), N', ')
                     WITHIN GROUP (ORDER BY ordinal)
    FROM @columns
    WHERE TRY_CONVERT(date, name, 23) IS NOT NULL;

    DECLARE @create nvarchar(max) = N'CREATE TABLE dbo.' + QUOTENAME(@table) + N' (
        RegionID   int           NOT NULL,
        RegionName nvarchar(200) NOT NULL,
        RegionType nvarchar(20)  NOT NULL,
        StateName  nvarchar(10)  NULL,
        SizeRank   int           NOT NULL,
        month_date date          NOT NULL,
        ' + QUOTENAME(@value_column) + N' decimal(18,4) NOT NULL,
        CONSTRAINT ' + QUOTENAME(N'PK_' + @table) + N' PRIMARY KEY (RegionID, month_date));';

    DECLARE @insert nvarchar(max) = N'INSERT INTO dbo.' + QUOTENAME(@table)
             + N' (RegionID, RegionName, RegionType, StateName, SizeRank, month_date, ' + QUOTENAME(@value_column) + N')
        SELECT CONVERT(int, s.c' + CAST(@col_id AS nvarchar(10)) + N'),
               s.c' + CAST(@col_name AS nvarchar(10)) + N',
               s.c' + CAST(@col_type AS nvarchar(10)) + N',
               NULLIF(REPLACE(s.c' + CAST(@col_state AS nvarchar(10)) + N', NCHAR(13), N''''), N''''),
               CONVERT(int, s.c' + CAST(@col_rank AS nvarchar(10)) + N'),
               CONVERT(date, m.month_name, 23),
               CONVERT(decimal(18,4), CONVERT(float, LTRIM(RTRIM(REPLACE(m.cell, NCHAR(13), N'''')))))
        FROM dbo.stage_zillow_load AS s
        CROSS APPLY (VALUES ' + @months + N') AS m(month_name, cell)
        WHERE NULLIF(LTRIM(RTRIM(REPLACE(m.cell, NCHAR(13), N''''))), N'''') IS NOT NULL;';

    BEGIN TRY
        BEGIN TRANSACTION;
        EXEC sp_executesql @create;
        EXEC sp_executesql @insert;
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;  -- also undoes the CREATE TABLE
        DROP TABLE IF EXISTS dbo.stage_zillow_load;
        THROW;
    END CATCH;

    DROP TABLE dbo.stage_zillow_load;
    DECLARE @loaded bigint = (SELECT SUM(p.rows) FROM sys.partitions AS p
                              WHERE p.object_id = OBJECT_ID(N'dbo.' + QUOTENAME(@table)) AND p.index_id IN (0, 1));
    PRINT CONCAT(N'dbo.', @table, N' loaded: ', @loaded, N' rows.');
END;
GO

-- ---------------------------------------------------------------------------------------------
-- Load the four Zillow files. Change @data_folder if the repo lives somewhere else.
DECLARE @data_folder nvarchar(300) = N'C:\Projects\us-housing-market-analysis\data\';

DECLARE @f1 nvarchar(400) = @data_folder + N'Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv',
        @f2 nvarchar(400) = @data_folder + N'Metro_zori_uc_sfrcondomfr_sm_month.csv',
        @f3 nvarchar(400) = @data_folder + N'Metro_invt_fs_uc_sfrcondo_sm_month.csv',
        @f4 nvarchar(400) = @data_folder + N'Metro_mean_doz_pending_uc_sfrcondo_sm_month.csv';

EXEC dbo.load_zillow_wide @file = @f1, @table = N'ZHVI_HomeValue',    @value_column = N'home_value';
EXEC dbo.load_zillow_wide @file = @f2, @table = N'ZORI_Rentals',      @value_column = N'rent';
EXEC dbo.load_zillow_wide @file = @f3, @table = N'Inventory_ForSale', @value_column = N'inventory';
EXEC dbo.load_zillow_wide @file = @f4, @table = N'DaysToPending',     @value_column = N'days_to_pending';
GO

-- ---------------------------------------------------------------------------------------------
-- Checks. Each expected value is recomputed from the CSVs by tests/test_sql_expectations.py.

-- Check 1: row counts (one row per metro per month that has a value)
-- expect inventory_rows: 95318
-- expect days_to_pending_rows: 51485
-- expect zhvi_rows: 238029
-- expect zori_rows: 53977
SELECT 'Inventory_ForSale' AS table_name, COUNT(*) AS row_count FROM dbo.Inventory_ForSale
UNION ALL SELECT 'DaysToPending', COUNT(*) FROM dbo.DaysToPending
UNION ALL SELECT 'ZHVI_HomeValue', COUNT(*) FROM dbo.ZHVI_HomeValue
UNION ALL SELECT 'ZORI_Rentals', COUNT(*) FROM dbo.ZORI_Rentals;

-- Check 2: the newest month loaded fully (catches a hidden line-ending character in the last column)
-- expect inventory_last_month: 2026-10-31
-- expect inventory_last_month_rows: 927
SELECT MAX(month_date) AS last_month,
       SUM(CASE WHEN month_date = (SELECT MAX(month_date) FROM dbo.Inventory_ForSale) THEN 1 ELSE 0 END) AS last_month_rows
FROM dbo.Inventory_ForSale;

-- Check 3: a metro name with a comma inside quotes loaded into one column, with the right value
-- expect atlanta_inventory_2026_09: 33948
SELECT RegionName, StateName, month_date, inventory
FROM dbo.Inventory_ForSale
WHERE RegionName = N'Atlanta, GA' AND month_date = '2026-09-30';

-- Check 4: run this script a second time - the counts in Check 1 must not change.
GO
