# Test: Power BI model views and a full rebuild from nothing

## What was tested
`sql/07_powerbi_views.sql` (`rpt.dim_metro`, `rpt.dim_month`, `rpt.fact_metro_month`), the Task 9 checks in `sql/99_validation_checks.sql`, and a clean run of every script in order.

## How
1. Added 9 checks to `99` and ran it: failed with `Invalid object name 'rpt.fact_metro_month'`, exit 1.
2. Ran `07`: 928 metros, 321 months, 240,674 fact rows. Ran `99`: it took over 2 minutes. Timing each new check showed the orphan check written as `NOT EXISTS … OR NOT EXISTS` re-ran the calendar view per row; rewritten with `LEFT JOIN`s, `99` runs in about 14 seconds.
3. `large metros` FAILED: 99, not the plan's 100. Checked the raw files: no file has a region with size rank 33, and ranks 74 (Dayton, OH) and 86 (Poughkeepsie, NY) appear only in the supply files under new region IDs, so ranks 1–100 hold 99 regions, 97 of them with home values. The definition (`size_rank BETWEEN 1 AND 100`) was kept and the check now expects 99.
4. Full rebuild (Review Focus 4): dropped `HousingMarket` (`DB_ID` then NULL), then ran `01`–`07` and `99` in order with `sqlcmd -S localhost -E -C -b -I -v DataDir=<repo data folder>`. Every script exit 0; the whole rebuild took 7.7 seconds; all 53 checks PASS, including fact rows 240,674 with no duplicate keys and no rows missing a metro or month, dim_month 321 rows labelled `Sep 2026` for the latest month, U.S. rent change +2.70%, and the U.S. Sep 2026 fact row `366157.15 | +1.19% | 6.33% | inventory +2.5063% | days to pending +2`.

## Result
PASS

## Bugs
None. The slow check and the 100-vs-99 expectation were caught by the run itself and fixed before commit; neither affected the data.
