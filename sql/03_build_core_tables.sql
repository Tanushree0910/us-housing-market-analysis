/*
  03_build_core_tables.sql
  Reshapes the four wide raw tables into clean long tables:
    core.metro        - one row per region (union of all four files)
    core.metro_month  - one row per region per month with all four measures side by side
  The wide-to-long unpivot is generated with dynamic SQL from the month columns that exist,
  so no month is typed by hand. Months after the latest home-value month are left out (decision 0004).
  Safe to re-run: both tables are dropped and rebuilt.
  Run: sqlcmd -S localhost -E -C -b -I -i sql/03_build_core_tables.sql
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;
USE HousingMarket;

DROP TABLE IF EXISTS core.metro_month;
DROP TABLE IF EXISTS core.metro;

CREATE TABLE core.metro (
    metro_id    INT           NOT NULL CONSTRAINT pk_metro PRIMARY KEY,
    metro_name  NVARCHAR(100) NOT NULL,
    state_code  NVARCHAR(10)  NULL,
    region_type NVARCHAR(20)  NULL,
    size_rank   INT           NULL
);

CREATE TABLE core.metro_month (
    metro_id           INT            NOT NULL CONSTRAINT fk_metro_month_metro REFERENCES core.metro (metro_id),
    month_end          DATE           NOT NULL,
    home_value         DECIMAL(12, 2) NULL,
    rent_monthly       DECIMAL(10, 2) NULL,
    for_sale_inventory INT            NULL,
    days_to_pending    INT            NULL,
    CONSTRAINT pk_metro_month PRIMARY KEY (metro_id, month_end)
);

-- Regions: names, state and type come from the first file that has the region (home values first);
-- size_rank comes from the home-value file when present, otherwise the lowest rank found.
WITH src AS (
    SELECT 1 AS priority, RegionID, SizeRank, RegionName, RegionType, StateName FROM [raw].zhvi_wide
    UNION ALL SELECT 2, RegionID, SizeRank, RegionName, RegionType, StateName FROM [raw].zori_wide
    UNION ALL SELECT 3, RegionID, SizeRank, RegionName, RegionType, StateName FROM [raw].inventory_wide
    UNION ALL SELECT 4, RegionID, SizeRank, RegionName, RegionType, StateName FROM [raw].days_to_pending_wide
), ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY RegionID ORDER BY priority) AS pick,
           MIN(CASE WHEN priority = 1 THEN SizeRank END) OVER (PARTITION BY RegionID) AS zhvi_rank,
           MIN(SizeRank) OVER (PARTITION BY RegionID) AS lowest_rank
    FROM src
)
INSERT core.metro (metro_id, metro_name, state_code, region_type, size_rank)
SELECT RegionID, RegionName, NULLIF(StateName, N''), RegionType, COALESCE(zhvi_rank, lowest_rank)
FROM ranked
WHERE pick = 1;

-- Long staging table: one row per region, month and measure (1 home value, 2 rent, 3 inventory, 4 days to pending).
DROP TABLE IF EXISTS #long;
CREATE TABLE #long (metro_id INT NOT NULL, month_end DATE NOT NULL, measure TINYINT NOT NULL, value FLOAT NOT NULL);

-- Unpivot each raw table: CROSS APPLY (VALUES ('2000-01-31', [2000-01-31]), ...) built from its month columns.
DECLARE @tables TABLE (measure TINYINT, table_name SYSNAME);
INSERT @tables VALUES (1, N'zhvi_wide'), (2, N'zori_wide'), (3, N'inventory_wide'), (4, N'days_to_pending_wide');

DECLARE @measure TINYINT, @table SYSNAME, @pairs NVARCHAR(MAX), @sql NVARCHAR(MAX);
DECLARE table_cursor CURSOR LOCAL FAST_FORWARD FOR SELECT measure, table_name FROM @tables ORDER BY measure;
OPEN table_cursor;
FETCH NEXT FROM table_cursor INTO @measure, @table;
WHILE @@FETCH_STATUS = 0
BEGIN
    SELECT @pairs = STRING_AGG(CAST(N'(''' + c.name + N''', ' + QUOTENAME(c.name) + N')' AS NVARCHAR(MAX)), N', ')
                    WITHIN GROUP (ORDER BY c.column_id)
    FROM sys.columns AS c
    WHERE c.object_id = OBJECT_ID(N'[raw].' + QUOTENAME(@table))
      AND c.name LIKE N'[12][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]';

    SET @sql = N'INSERT #long (metro_id, month_end, measure, value)
        SELECT w.RegionID, CAST(v.month_end AS DATE), @measure, TRY_CAST(v.value AS FLOAT)
        FROM [raw].' + QUOTENAME(@table) + N' AS w
        CROSS APPLY (VALUES ' + @pairs + N') AS v (month_end, value)
        WHERE v.value <> '''' AND TRY_CAST(v.value AS FLOAT) IS NOT NULL;';
    EXEC sys.sp_executesql @sql, N'@measure TINYINT', @measure = @measure;

    FETCH NEXT FROM table_cursor INTO @measure, @table;
END;
CLOSE table_cursor;
DEALLOCATE table_cursor;

-- Stop at the latest month that has home values, so every measure shares one window (decision 0004).
DECLARE @latest DATE = (SELECT MAX(month_end) FROM #long WHERE measure = 1);

-- One row per region-month: pivot the four measures side by side, rounded to the column types.
-- (Grouping by region-month gives the same result as a FULL OUTER JOIN of the four measures.)
INSERT core.metro_month (metro_id, month_end, home_value, rent_monthly, for_sale_inventory, days_to_pending)
SELECT metro_id,
       month_end,
       CAST(ROUND(MAX(CASE WHEN measure = 1 THEN value END), 2) AS DECIMAL(12, 2)),
       CAST(ROUND(MAX(CASE WHEN measure = 2 THEN value END), 2) AS DECIMAL(10, 2)),
       CAST(ROUND(MAX(CASE WHEN measure = 3 THEN value END), 0) AS INT),
       CAST(ROUND(MAX(CASE WHEN measure = 4 THEN value END), 0) AS INT)
FROM #long
WHERE month_end <= @latest
GROUP BY metro_id, month_end;

-- Report the result.
SELECT (SELECT COUNT(*) FROM core.metro) AS metros,
       COUNT(*) AS metro_months,
       MIN(month_end) AS first_month,
       MAX(month_end) AS last_month
FROM core.metro_month;
