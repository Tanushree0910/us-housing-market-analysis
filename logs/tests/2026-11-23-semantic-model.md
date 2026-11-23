# Test: Power BI semantic model loads and matches SQL

## What was tested
The Power BI Project `powerbi/us_housing_market.pbip`: the TMDL semantic model (tables `dim_metro`, `dim_month`, `fact_metro_month`, `supply_price_correlation`, `headline_measures`, two relationships, parameters `SqlServer` and `SqlDatabase`), opened, refreshed and saved in Power BI Desktop 2.159 on the owner's PC.

## How
1. Saved a blank report from Power BI Desktop as a `.pbip` in the session scratchpad, and copied its report skeleton (theme file, `report.json`, `version.json`) so the report folder uses exactly the format this version writes.
2. Opened the project. First attempt: "Unsupported Table name 'measures'" — `measures` is reserved, so the measure table is named `headline_measures`.
3. First refresh: the four Power BI queries reached SQL Server but waited on `RESOURCE_SEMAPHORE` (SQL Server's query memory had shrunk to 6 MB; the PC had about 670 MB free). The owner closed Chrome, Edge and Excel; query memory recovered to about 390 MB.
4. Second refresh: "A cyclic reference was encountered during evaluation". The M step named `Data` was renamed to `rpt_view`; the next refresh succeeded with no warnings.
5. DAX check through Power BI's own ADOMD client against the open model (`CALCULATETABLE(ROW(...), dim_metro[metro_id] = 102001)`):

| Measure | DAX result | SQL / reference |
|---|---|---|
| Home Value | 366157.15 | 366157.15 |
| Home Value YoY % | 0.011878 (1.19%) | 1.19 |
| Rent | 1931.94 | 1931.94 |
| Rent YoY % | 0.026989 (2.70%) | 2.70 |
| Rent to Price % | 0.063315 (6.33%) | 6.33 |
| Inventory YoY % | 0.025063 (2.51%) | 2.5063 |
| Days to Pending | 56 | 56 |
| Inventory vs Price r | 0.2968 | 0.2968 |
| Latest Month Label | Sep 2026 | Sep 2026 |
| Home Value Index | 187.60 | (value Sep 2026 ÷ Sep 2015) |
| Rent Index | 163.63 | (rent Sep 2026 ÷ Sep 2015) |
| rows in fact_metro_month | 240674 | 240674 |
| large metros | 99 | 99 |

6. Review Focus 5: changed `SqlServer` to `.` (Transform data → Edit parameters). Power BI asked for credentials for `.;HousingMarket`, so the parameter drives the connection. It then reported that `.` cannot use an encrypted connection (the local server has a self-signed certificate) and offered an unencrypted fallback. That was declined, because it would store a new connection permission on the owner's PC, and the change was discarded. A model query (`$SYSTEM.TMSCHEMA_EXPRESSIONS`) confirmed `SqlServer` is back to `"localhost"` and the data is still loaded.
7. Saved in Power BI (Ctrl+S). `python tools/governance_check.py`: no problems. `python -m unittest discover -s tests -t .`: OK (1 skipped on Windows).

## Result
PASS

## Bugs
None. The reserved table name, the step name and the memory wait were found and fixed during this task.
