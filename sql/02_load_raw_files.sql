/*
  02_load_raw_files.sql
  Loads the four wide Zillow CSVs into raw.* tables, one column per month, values kept as text (VARCHAR).
  The table shape is not hard-coded: raw.usp_load_wide_csv reads each file's header line and
  builds a matching CREATE TABLE with dynamic SQL, so new months in a future download just work.
  Safe to re-run: each call drops and recreates its own table.
  Run: sqlcmd -S localhost -E -C -b -I -v DataDir="C:\path\to\data" -i sql/02_load_raw_files.sql
*/
SET NOCOUNT ON;
USE HousingMarket;
GO

CREATE OR ALTER PROCEDURE [raw].usp_load_wide_csv
    @file_path  NVARCHAR(400),
    @table_name SYSNAME
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @target NVARCHAR(300) = N'[raw].' + QUOTENAME(@table_name);
    DECLARE @path   NVARCHAR(800) = REPLACE(@file_path, N'''', N'''''');  -- escape for the string literal
    DECLARE @sql    NVARCHAR(MAX);
    DECLARE @header NVARCHAR(MAX);

    -- 1. Read only the header line. 0x07 (bell) never appears in the file, so the whole line lands in one column.
    CREATE TABLE #header_line (line NVARCHAR(MAX));
    SET @sql = N'BULK INSERT #header_line FROM N''' + @path + N'''
        WITH (FIELDTERMINATOR = ''0x07'', ROWTERMINATOR = ''0x0a'', LASTROW = 1, CODEPAGE = ''65001'');';
    EXEC sys.sp_executesql @sql;

    -- 2. Strip a UTF-8 byte-order mark and a Windows carriage return, if present.
    SELECT @header = line FROM #header_line;
    IF LEFT(@header, 1) = NCHAR(65279) SET @header = STUFF(@header, 1, 1, N'');
    IF RIGHT(@header, 1) = NCHAR(13)   SET @header = LEFT(@header, LEN(@header) - 1);

    -- 3. Refuse a file that is not in Zillow's wide layout, before anything is dropped.
    IF @header IS NULL OR @header NOT LIKE N'RegionID,SizeRank,RegionName,RegionType,StateName,%'
        THROW 50010, N'Unexpected header: the file does not start with RegionID,SizeRank,RegionName,RegionType,StateName.', 1;

    -- 4. Build CREATE TABLE: 5 typed key columns, then one text column per month named exactly as in the header.
    DECLARE @columns NVARCHAR(MAX);
    SELECT @columns = STRING_AGG(CAST(
               CASE s.ordinal
                   WHEN 1 THEN N'RegionID INT NOT NULL'
                   WHEN 2 THEN N'SizeRank INT NULL'
                   WHEN 3 THEN N'RegionName NVARCHAR(100) NOT NULL'
                   WHEN 4 THEN N'RegionType NVARCHAR(20) NULL'
                   WHEN 5 THEN N'StateName NVARCHAR(10) NULL'
                   ELSE QUOTENAME(s.value) + N' VARCHAR(30) NULL'  -- VARCHAR: 321 NVARCHAR columns exceed the 8,060-byte row limit
               END AS NVARCHAR(MAX)), N', ') WITHIN GROUP (ORDER BY s.ordinal)
    FROM STRING_SPLIT(@header, N',', 1) AS s;

    -- 5. Drop and recreate the table, then load all data rows. On any error the table is dropped,
    --    so a failed load never leaves a half-filled table behind (Review Focus 1).
    BEGIN TRY
        SET @sql = N'DROP TABLE IF EXISTS ' + @target + N'; CREATE TABLE ' + @target + N' (' + @columns + N');';
        EXEC sys.sp_executesql @sql;

        SET @sql = N'BULK INSERT ' + @target + N' FROM N''' + @path + N'''
            WITH (FORMAT = ''CSV'', FIRSTROW = 2, FIELDQUOTE = ''"'', FIELDTERMINATOR = '','',
                  ROWTERMINATOR = ''0x0a'', CODEPAGE = ''65001'', TABLOCK);';
        EXEC sys.sp_executesql @sql;

        -- 6. A Windows line ending leaves \r on the last column; remove it so values stay clean (Review Focus 2).
        DECLARE @last SYSNAME = (SELECT TOP (1) name FROM sys.columns
                                 WHERE object_id = OBJECT_ID(@target) ORDER BY column_id DESC);
        SET @sql = N'UPDATE ' + @target + N' SET ' + QUOTENAME(@last) + N' = NULLIF(REPLACE(' + QUOTENAME(@last)
                 + N', NCHAR(13), N''''), N'''') WHERE ' + QUOTENAME(@last) + N' LIKE N''%'' + NCHAR(13);';
        EXEC sys.sp_executesql @sql;
    END TRY
    BEGIN CATCH
        SET @sql = N'DROP TABLE IF EXISTS ' + @target + N';';
        EXEC sys.sp_executesql @sql;
        THROW;
    END CATCH;

    -- Report what was loaded.
    SET @sql = N'SELECT N''' + @target + N''' AS loaded_table, COUNT(*) AS row_count, '
             + CAST((SELECT COUNT(*) - 5 FROM sys.columns WHERE object_id = OBJECT_ID(@target)) AS NVARCHAR(10))
             + N' AS month_columns FROM ' + @target + N';';
    EXEC sys.sp_executesql @sql;
END;
GO

-- Load the four Zillow files under their original names from the DataDir folder.
EXEC [raw].usp_load_wide_csv N'$(DataDir)\Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv', N'zhvi_wide';
EXEC [raw].usp_load_wide_csv N'$(DataDir)\Metro_zori_uc_sfrcondomfr_sm_month.csv',                 N'zori_wide';
EXEC [raw].usp_load_wide_csv N'$(DataDir)\Metro_invt_fs_uc_sfrcondo_sm_month.csv',                 N'inventory_wide';
EXEC [raw].usp_load_wide_csv N'$(DataDir)\Metro_mean_doz_pending_uc_sfrcondo_sm_month.csv',        N'days_to_pending_wide';
GO
