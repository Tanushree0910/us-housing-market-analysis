# Test: Question 1 — year-over-year home value growth

## What was tested
`sql/04_home_value_growth.sql` (view `rpt.v_home_value_growth`) and the Task 6 checks in `sql/99_validation_checks.sql`.

## How
1. Reference numbers from a scratchpad Python script on the raw ZHVI CSV (values rounded to cents as in `core`, change = value ÷ value of the same month a year earlier − 1): U.S. Sep 2026 +1.19%; of the 100 largest metros, 97 have a change in Sep 2026, fastest Syracuse, NY +6.62%, slowest Austin, TX −4.31%; top 5 Syracuse, Bridgeport, Milwaukee, Hartford, Albany; 226,857 metro-months have a change in total.
2. Added 9 checks to `99`, ran it before the view existed: failed with `Invalid object name 'rpt.v_home_value_growth'`, exit 1.
3. First version used `LAG(home_value, 12)` as the plan said: 8 checks PASS, `rows with home value yoy` FAIL (225,083 vs 226,857). Cause traced to `LAG` counting rows across gaps (BUG-002). Rewrote the view as a self-join on the month exactly 12 months earlier.
4. `sqlcmd -S localhost -E -C -b -I -i sql/04_home_value_growth.sql` then `99`: all 39 checks PASS, exit 0. `gap months with yoy` = 0 (Review Focus 3: no change is computed when the month a year earlier has no value).

## Result
PASS

## Bugs
[BUG-002](../bugs/BUG-002-lag-misses-valid-prior-month.md)
