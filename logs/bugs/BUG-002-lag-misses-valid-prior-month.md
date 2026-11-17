# BUG-002: Year-over-year missed valid comparisons when a series had a gap

## Status
Fixed

## Found
2026-11-17, agent session on the owner's PC (plan Task 6), by the check `rows with home value yoy` in `sql/99_validation_checks.sql`.

## What happened
The first version of `rpt.v_home_value_growth` found 225,083 year-over-year values; the independent Python count from the raw CSV is 226,857. 1,774 metro-months showed NULL even though the month exactly 12 months earlier had a home value (first example: metro 394297, June 2012).

## Cause
The plan said to use `LAG(home_value, 12)` and keep the result only when the lagged month equals `EOMONTH(month_end, -12)`. `LAG` counts rows, not months. When a month is missing *inside* the 12-month window, the row 12 positions back is 13 or more months back, so the guard correctly refused it — but the right month existed and was never looked at. The guard stopped wrong comparisons, but it also dropped valid ones.

## Fix
The view joins each month to the month exactly 12 months earlier (`LEFT JOIN … ON prev.month_end = EOMONTH(cur.month_end, -12)`), which finds the right month whatever the gaps and still gives NULL when that month has no value. The extremes (Syracuse +6.62%, Austin −4.31%, U.S. +1.19%) were the same before and after.

## Test log
[2026-11-17-home-value-growth.md](../tests/2026-11-17-home-value-growth.md)
