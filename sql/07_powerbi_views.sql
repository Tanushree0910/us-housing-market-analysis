/*
  07_powerbi_views.sql
  The star schema Power BI imports:
    rpt.dim_metro         - one row per region, with a flag for the 100 largest metros
    rpt.dim_month         - one row per month, Jan 2000 to the latest month
    rpt.fact_metro_month  - one row per region per month with every measure and change
  Safe to re-run (CREATE OR ALTER).
  Run: sqlcmd -S localhost -E -C -b -I -i sql/07_powerbi_views.sql
*/
SET NOCOUNT ON;
USE HousingMarket;
GO

-- Regions. "Large metro" = size_rank 1-100 (rank 0 is the whole U.S.).
CREATE OR ALTER VIEW rpt.dim_metro
AS
SELECT metro_id,
       metro_name,
       state_code,
       region_type,
       size_rank,
       CAST(CASE WHEN size_rank BETWEEN 1 AND 100 THEN 1 ELSE 0 END AS BIT) AS is_large_metro
FROM core.metro;
GO

-- Months: a gap-free calendar of month-ends from Jan 2000 to the latest month in the data.
-- GENERATE_SERIES needs SQL Server 2022 or later; FORMAT with 'en-US' keeps labels English on any server language.
CREATE OR ALTER VIEW rpt.dim_month
AS
SELECT d.month_end,
       YEAR(d.month_end)  AS [year],
       MONTH(d.month_end) AS month_num,
       CAST(FORMAT(d.month_end, 'MMM yyyy', 'en-US') AS NCHAR(8)) AS month_label
FROM GENERATE_SERIES(0, DATEDIFF(MONTH, '2000-01-31', (SELECT MAX(month_end) FROM core.metro_month))) AS s
CROSS APPLY (SELECT EOMONTH('2000-01-31', s.value) AS month_end) AS d;
GO

-- Facts: every core row, plus the changes and ratios from views 04-06 (LEFT JOINs keep all rows).
-- Rent change uses the same exact-12-months-back rule as home values.
CREATE OR ALTER VIEW rpt.fact_metro_month
AS
SELECT mm.metro_id,
       mm.month_end,
       mm.home_value,
       mm.rent_monthly,
       mm.for_sale_inventory,
       mm.days_to_pending,
       g.yoy_pct AS home_value_yoy_pct,
       CAST(CASE WHEN prev.rent_monthly > 0
                 THEN (mm.rent_monthly / prev.rent_monthly - 1) * 100 END AS DECIMAL(9, 4)) AS rent_yoy_pct,
       r.rent_to_price_pct,
       s.inventory_yoy_pct,
       s.days_to_pending_yoy_change
FROM core.metro_month AS mm
LEFT JOIN core.metro_month AS prev
       ON prev.metro_id = mm.metro_id AND prev.month_end = EOMONTH(mm.month_end, -12)
LEFT JOIN rpt.v_home_value_growth AS g
       ON g.metro_id = mm.metro_id AND g.month_end = mm.month_end
LEFT JOIN rpt.v_rent_to_price AS r
       ON r.metro_id = mm.metro_id AND r.month_end = mm.month_end
LEFT JOIN rpt.v_supply_vs_price AS s
       ON s.metro_id = mm.metro_id AND s.month_end = mm.month_end;
GO

-- Row counts of the three model views as a quick check.
SELECT (SELECT COUNT(*) FROM rpt.dim_metro) AS dim_metro_rows,
       (SELECT COUNT(*) FROM rpt.dim_month) AS dim_month_rows,
       (SELECT COUNT(*) FROM rpt.fact_metro_month) AS fact_rows;
