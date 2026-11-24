# Test: Question 2 — rent-to-price ratio

## What was tested
`sql/05_rent_to_price.sql` (view `rpt.v_rent_to_price`) and the Task 7 checks in `sql/99_validation_checks.sql`.

## How
1. Reference numbers from a scratchpad Python script on the raw ZHVI and ZORI CSVs (values rounded to cents, ratio = rent × 12 ÷ home value × 100): 53,095 metro-months have both values; 728 in Sep 2026; U.S. Sep 2026 6.33%; of the 100 largest metros (97 with both values), highest Jackson, MS 8.31%, lowest San Jose, CA 3.00%.
2. Added 5 checks to `99` and ran it: failed with `Invalid object name 'rpt.v_rent_to_price'`, exit 1.
3. `sqlcmd -S localhost -E -C -b -I -i sql/05_rent_to_price.sql`, then `99`: all 44 checks PASS, exit 0. The script's own preview ranks Jackson, El Paso, Pittsburgh, Toledo and Columbia, SC highest.

## Result
PASS

## Bugs
None
