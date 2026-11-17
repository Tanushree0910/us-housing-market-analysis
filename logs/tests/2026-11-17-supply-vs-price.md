# Test: Question 3 — supply versus price

## What was tested
`sql/06_supply_vs_price.sql` (views `rpt.v_supply_vs_price` and `rpt.v_supply_price_correlation`) and the Task 8 checks in `sql/99_validation_checks.sql`.

## How
1. Reference numbers from a scratchpad Python script on the raw ZHVI, inventory and days-to-pending CSVs, using the same definitions as the SQL (values rounded as in `core`; changes against the month exactly 12 months back; percentages rounded to 4 decimals; Pearson r across the 100 largest metros that have all three changes):
   - 94,418 metro-months have inventory or days to pending (to Sep 2026); 83,188 have an inventory change.
   - U.S. Sep 2026: inventory +2.5063% over the year; days to pending 56, up 2 days.
   - Sep 2026: 97 large metros; r(inventory change, home value change) = 0.2968; r(days-to-pending change, home value change) = 0.0624.
2. Added 7 checks to `99` and ran it: failed with `Invalid object name 'rpt.v_supply_vs_price'`, exit 1.
3. `sqlcmd -S localhost -E -C -b -I -i sql/06_supply_vs_price.sql`, then `99`: all 51 checks PASS, exit 0.

## Result
PASS

## Bugs
None
