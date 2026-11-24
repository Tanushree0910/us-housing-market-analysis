/*
  05_rent_to_price.sql
  Question 2: where is the rent-to-price ratio highest?
  rpt.v_rent_to_price = a year of rent as a percentage of the home value (gross rental yield).
  e.g. 6.33 means a year's rent is 6.33% of the typical home value. Higher = renting is
  expensive relative to buying (or homes are cheap relative to rents).
  Safe to re-run (CREATE OR ALTER).
  Run: sqlcmd -S localhost -E -C -b -I -i sql/05_rent_to_price.sql
*/
SET NOCOUNT ON;
USE HousingMarket;
GO

-- Only metro-months where both a home value and a rent exist; the ratio is undefined otherwise.
CREATE OR ALTER VIEW rpt.v_rent_to_price
AS
SELECT metro_id,
       month_end,
       home_value,
       rent_monthly,
       CAST(rent_monthly * 12 / home_value * 100 AS DECIMAL(9, 4)) AS rent_to_price_pct
FROM core.metro_month
WHERE home_value > 0
  AND rent_monthly IS NOT NULL;
GO

-- Rank the large metros in the latest month, highest ratio first, as a quick check.
SELECT TOP (5) m.metro_name, r.rent_monthly, r.home_value, r.rent_to_price_pct,
       RANK() OVER (ORDER BY r.rent_to_price_pct DESC) AS rank_high_to_low
FROM rpt.v_rent_to_price AS r
JOIN core.metro AS m ON m.metro_id = r.metro_id
WHERE r.month_end = (SELECT MAX(month_end) FROM core.metro_month)
  AND m.size_rank BETWEEN 1 AND 100
ORDER BY r.rent_to_price_pct DESC;
